# src/virtualstack/api/v1/endpoints/invitations.py
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct

from virtualstack.api import deps
from virtualstack.core.permissions import Permission
from virtualstack.models.iam.user import User as UserModel
from virtualstack.schemas.iam.invitation import (
    InvitationAccept, InvitationCreate, InvitationUpdate, InvitationVerify,
    InvitationResponse, InvitationDetailResponse, InvitationCreateResponse,
    InvitationTokenResponse,
    InvitationStatus,
)
from virtualstack.schemas.iam.user import UserCreate, User
from virtualstack.services.iam import invitation_service, user_service
from virtualstack.core.exceptions import (
    NotFoundError,
    AuthorizationError,
    http_bad_request_error
)
from virtualstack.models.iam.user_tenant_role import user_tenant_roles_table
from virtualstack.models.iam.role_permissions import role_permissions_table


router = APIRouter()
logger = logging.getLogger(__name__)

# TODO: Add permission checks (e.g., TENANT_MANAGE_INVITATIONS) to all endpoints

@router.post(
    "/",
    response_model=InvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(deps.require_permission(Permission.TENANT_MANAGE_INVITATIONS))]
)
async def create_invitation(
    *,
    invitation_in: InvitationCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> InvitationCreateResponse:
    """Create a new invitation.
    Requires TENANT_MANAGE_INVITATIONS permission.
    """
    logger.info(f"User {current_user.id} attempting to create invitation: {invitation_in.email} for tenant {invitation_in.tenant_id}")

    # TODO: Add validation: Does the current_user belong to the target tenant_id?
    # This might be better handled within the permission dependency or service layer.
    # For now, assume the permission check implies tenant access.

    try:
        # Call the service to create the invitation
        invitation, token = await invitation_service.create_invitation(
            db=db,
            email=invitation_in.email,
            tenant_id=invitation_in.tenant_id,
            inviter_id=current_user.id,
            role_id=invitation_in.role_id, # Pass role_id from input
            expires_in_days=invitation_in.expires_in_days
        )

        # Prepare the response using the model_validate method for Pydantic v2
        response_data = InvitationCreateResponse.model_validate(invitation).model_dump()
        # Add the token to the response dictionary
        response_data['token'] = token

        # Return the combined data
        # FastAPI will automatically convert the dict back to the response_model if needed,
        # but returning the validated model instance is often preferred.
        # Let's stick to returning the dictionary here as we manually added the token.
        # Or, better, create the response object directly:
        response_obj = InvitationCreateResponse(**response_data)

        logger.info(f"Invitation created successfully with ID: {invitation.id}")
        return response_obj # Return the Pydantic object

    except NotFoundError as e:
        # Use NotFoundError
        logger.warning(f"Failed to create invitation due to non-existent resource: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    # Use http_bad_request_error factory for Bad Request exceptions from service
    # Assuming the service might raise a generic Exception or a specific one we map here
    except ValueError as e: # Catch potential ValueErrors from service for bad requests
         logger.warning(f"Failed to create invitation due to bad request: {e}")
         raise http_bad_request_error(detail=str(e))
    except AuthorizationError as e:
        # Use AuthorizationError
        logger.warning(f"Permission denied for user {current_user.id} to create invitation: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating invitation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the invitation.",
        )


@router.get(
    "/",
    response_model=List[InvitationResponse],
    # Permission check now needs to consider the tenant_id from query
    # dependencies=[Depends(deps.require_permission(Permission.TENANT_MANAGE_INVITATIONS))] # Modify/replace this
)
async def list_invitations(
    *,
    # Remove request: Request
    db: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Query(..., description="Tenant ID to list invitations for"), # Required Query param
    status_filter: Optional[InvitationStatus] = Query(None, alias="status", description="Filter invitations by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: UserModel = Depends(deps.get_current_active_user), # Inject user for manual check
) -> List[InvitationResponse]:
    """List invitations for a specific tenant.
    Requires TENANT_MANAGE_INVITATIONS permission for the specified tenant.
    Allows filtering by status.
    """
    # TODO: Manually check permission for the given tenant_id and current_user
    # This bypasses the standard dependency for now.
    has_permission = await check_user_permission_for_tenant(
        db, current_user.id, tenant_id, Permission.TENANT_MANAGE_INVITATIONS
    )
    if not has_permission and not current_user.is_superuser:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions to manage invitations for tenant {tenant_id}"
        )

    logger.info(f"Listing invitations for tenant {tenant_id} with status filter '{status_filter}'")
    try:
        if status_filter:
            # TODO: Implement get_by_tenant_and_status in service if needed, or filter here
            # For now, get all by tenant and filter in code (less efficient for large datasets)
            invitations = await invitation_service.get_multi_by_tenant(
                 db=db, tenant_id=tenant_id, skip=0, limit=1000 # Fetch more to filter
             )
            filtered_invitations = [inv for inv in invitations if inv.status == status_filter]
            # Apply pagination manually after filtering
            paginated_invitations = filtered_invitations[skip : skip + limit]
            # Validate each item (Pydantic v2 automatically validates list items if response_model is List[...])
            return paginated_invitations
        else:
            invitations = await invitation_service.get_multi_by_tenant(
                db=db, tenant_id=tenant_id, skip=skip, limit=limit
            )
            # Validate each item
            return invitations

    except Exception as e:
        logger.error(f"Unexpected error listing invitations for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing invitations.",
        )

# Helper function (ideally live in deps or a permissions utility module)
async def check_user_permission_for_tenant(db: AsyncSession, user_id: UUID, tenant_id: UUID, permission: Permission) -> bool:
    from virtualstack.services.iam import permission_service # Local import
    required_perm_obj = await permission_service.get_by_code(db, code=permission.value)
    if not required_perm_obj:
        logger.error(f"Permission code '{permission.value}' not found in database during manual check.")
        return False # Or raise internal error
    required_permission_id = required_perm_obj.id
    
    stmt = (
        select(distinct(role_permissions_table.c.permission_id))
        .select_from(user_tenant_roles_table)
        .join(role_permissions_table, user_tenant_roles_table.c.role_id == role_permissions_table.c.role_id)
        .where(
            (user_tenant_roles_table.c.user_id == user_id) &
            (user_tenant_roles_table.c.tenant_id == tenant_id) &
            (role_permissions_table.c.permission_id == required_permission_id)
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None

# Endpoint required by test_verify_invalid_token and test_verify_invitation_token
@router.post("/verify", response_model=InvitationTokenResponse)
async def verify_invitation_token(
    *,
    verification_data: InvitationVerify,
    db: AsyncSession = Depends(deps.get_db),
) -> InvitationTokenResponse:
    """Verify an invitation token and return details if valid (public endpoint)."""
    logger.info(f"Verifying invitation token: {verification_data.token[:8]}...")
    try:
        invitation = await invitation_service.verify_token(db=db, token=verification_data.token)
        if not invitation:
            # If verify_token returns None, it means token is invalid or expired
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation token is invalid or expired."
            )

        # Token is valid, return details
        # Fetch related details if needed by the response schema
        details = await invitation_service.get_invitation_with_details(db=db, invitation_id=invitation.id)
        
        # Construct the InvitationTokenResponse
        response_data = {
            "valid": True,
            "email": details.get("email"),
            "tenant_id": details.get("tenant_id"),
            "tenant_name": details.get("tenant_name"),
            "inviter_email": details.get("inviter_email"),
            "expires_at": details.get("expires_at"),
            "role_id": details.get("role_id"),
            "token": verification_data.token # Return original token for convenience
        }
        # Return the correct schema instance
        return InvitationTokenResponse(**response_data)

    except HTTPException as e:
         raise e # Re-raise explicit HTTP exceptions
    except Exception as e:
        logger.error(f"Unexpected error verifying invitation token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while verifying the invitation token.",
        )


@router.get(
    "/{invitation_id}",
    response_model=InvitationDetailResponse, # Use DetailResponse to include extra info
    dependencies=[Depends(deps.require_permission(Permission.TENANT_MANAGE_INVITATIONS))] # TODO: Revisit permission?
)
async def read_invitation(
    *,
    invitation_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    # tenant_id: UUID = Depends(deps.require_tenant_context), # Tenant context checked by permission dep
    current_user: UserModel = Depends(deps.get_current_user), # Included in permission dep
) -> InvitationDetailResponse:
    """Get details of a specific invitation by ID.
    Requires TENANT_MANAGE_INVITATIONS permission within the tenant context.
    """
    logger.info(f"User {current_user.id} reading invitation {invitation_id}")
    try:
        # Use the service method that fetches related details
        details = await invitation_service.get_invitation_with_details(db=db, invitation_id=invitation_id)
        if not details:
            raise NotFoundError("Invitation not found")

        # Manual permission check based on fetched details
        # Note: The dependency check already happened, but this adds layer of safety if dep fails
        # or if permissions are more granular than just TENANT_MANAGE_INVITATIONS.
        if not current_user.is_superuser:
            # Fetch tenant_id from details AFTER ensuring details is not None
            invitation_tenant_id = details.get("tenant_id")
            if not invitation_tenant_id:
                 logger.error(f"Could not determine tenant_id for invitation {invitation_id} during read operation.")
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal configuration error.")

            has_permission = await check_user_permission_for_tenant(
                db, current_user.id, invitation_tenant_id, Permission.TENANT_MANAGE_INVITATIONS
            )
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to view this invitation"
                )

        # Validate the details against the response schema
        # The service returns a dict, so we validate it here
        return InvitationDetailResponse.model_validate(details)

    except NotFoundError as e:
        logger.warning(f"Invitation {invitation_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error reading invitation {invitation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while reading the invitation.",
        )

# @router.put("/{invitation_id}", response_model=Invitation) # Update likely not needed, use revoke
# async def update_invitation(
#     ...
# ) -> Invitation:
#     pass # Placeholder

# Changed from DELETE to POST /{id}/revoke to avoid ambiguity with DELETE /{id}
# Although DELETE /{id} might be more RESTful for the concept of revoking/deleting.
# Let's stick to the test structure for now which uses POST /revoke.
@router.post(
    "/{invitation_id}/revoke",
    response_model=InvitationResponse, # Return the revoked invitation status
    status_code=status.HTTP_200_OK, # Return 200 OK on success
    dependencies=[Depends(deps.require_permission(Permission.TENANT_MANAGE_INVITATIONS))]
)
async def revoke_invitation(
    *,
    invitation_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    # tenant_id: UUID = Depends(deps.require_tenant_context), # Checked by permission dep
    current_user: UserModel = Depends(deps.get_current_user), # Checked by permission dep
) -> InvitationResponse:
    """Revoke an invitation by ID.
    Requires TENANT_MANAGE_INVITATIONS permission.
    Returns the updated invitation status.
    """
    logger.info(f"User {current_user.id} attempting to revoke invitation {invitation_id}")
    try:
        # Use record_id instead of id for the base service get method
        invitation = await invitation_service.get(db=db, record_id=invitation_id)
        if not invitation:
            raise NotFoundError("Invitation not found")

        # Manual permission check (redundant if dependency works, but safe)
        if not current_user.is_superuser:
            has_permission = await check_user_permission_for_tenant(
                db, current_user.id, invitation.tenant_id, Permission.TENANT_MANAGE_INVITATIONS
            )
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to revoke this invitation"
                )

        # Revoke using the service
        revoked_invitation = await invitation_service.revoke_invitation(db=db, invitation_id=invitation_id)
        
        if not revoked_invitation: # Should not happen if get() succeeded, but check anyway
             raise NotFoundError("Invitation could not be revoked (not found after initial check)")

        logger.info(f"Invitation {invitation_id} revoked successfully by user {current_user.id}.")
        return InvitationResponse.model_validate(revoked_invitation)

    except NotFoundError as e:
        logger.warning(f"Attempt to revoke non-existent invitation {invitation_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AuthorizationError as e: # Catch potential auth errors from manual check
        logger.warning(f"Permission denied for user {current_user.id} to revoke invitation {invitation_id}: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error revoking invitation {invitation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while revoking the invitation.",
        )

# Public endpoint for accepting an invitation
@router.post("/accept", response_model=User)
async def accept_invitation(
    *,
    db: AsyncSession = Depends(deps.get_db),
    payload: InvitationAccept = Body(...),
) -> User:
    logger.info(f"Attempting to accept invitation with token: {payload.token[:8]}...")
    try:
        # 1. Verify token and get invitation details
        invitation = await invitation_service.verify_token(db, token=payload.token)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation token is invalid or expired.",
            )

        # 2. Create User
        user_in_dict = {
            "email": invitation.email,
            "password": payload.password,
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "is_active": True,
            "is_superuser": False,
            "tenant_id": invitation.tenant_id,
        }
        new_user = None
        try:
            # Convert dict to Pydantic model before passing to service
            user_create_schema = UserCreate(**user_in_dict)
            logger.info(f"Creating new user for accepted invitation: {invitation.email}")
            # Pass the schema object to the service
            new_user = await user_service.create(db=db, obj_in=user_create_schema)
            logger.info(f"Successfully created user {new_user.id} for invitation {invitation.id}")
        except ValueError as val_err: # Catch Pydantic validation errors specifically
            logger.warning(f"Validation error creating user during invitation accept: {val_err}")
            raise http_bad_request_error(detail=f"Invalid user data provided: {val_err}")
        except Exception as e: # Catch other potential errors (e.g., DB constraint)
            # TODO: More specific error handling, e.g., if user email already exists
            logger.error(
                f"Failed to create user for invitation {invitation.id} (email: {invitation.email}): {e}",
                exc_info=True
            )
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create associated user account."
            )

        # 3. Mark invitation as accepted and assign role (within service)
        accepted_invitation = await invitation_service.accept_invitation(
            db=db, token=payload.token, user_id=new_user.id
        )
        
        if not accepted_invitation:
             logger.error(f"Acceptance failed *after* user creation for token {payload.token[:8]}...")
             await db.rollback() # Rollback user creation
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail="Failed to finalize invitation acceptance.",
             )

        logger.info(f"Invitation {accepted_invitation.id} accepted successfully by new user {new_user.id}.")

        # Re-fetch the user to ensure latest state, although current UserResponse doesn't require it
        # Use correct keyword argument 'record_id' for the base service get method
        final_user = await user_service.get(db, record_id=new_user.id)
        if not final_user:
             logger.error(f"Could not find user {new_user.id} right after creation during acceptance.")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error finding newly created user.")

        return User.model_validate(final_user)

    except HTTPException as e:
        raise e # Re-raise HTTP exceptions
    except ValueError as e: # Catch validation errors from InvitationAccept schema
        logger.warning(f"Validation error accepting invitation (payload): {e}")
        raise http_bad_request_error(detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error accepting invitation: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while accepting the invitation.",
        )

# Note: Removed PUT /update endpoint as revoking via DELETE is more common.
# Added basic logging and placeholder logic/responses to endpoints.
# Added placeholder /verify endpoint.
# Updated accept endpoint path and input schema.
# Added required schemas InvitationVerify, InvitationDetailResponse to imports.
