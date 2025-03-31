from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import get_current_user, get_db, get_tenant_id
from virtualstack.core.exceptions import NotFoundException, ValidationError
from virtualstack.models.iam.user import User
from virtualstack.schemas.iam.invitation import (
    InvitationCreate,
    InvitationDetailResponse,
    InvitationResponse,
    InvitationSendResponse,
    InvitationTokenResponse,
    InvitationUpdate
)
from virtualstack.services.iam.invitation import invitation_service


router = APIRouter()


@router.post(
    "/",
    response_model=InvitationSendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and send an invitation",
    description="Create a new invitation and generate an invitation link to send to the user."
)
async def create_invitation(
    invitation: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id)
) -> Any:
    """
    Create a new invitation.
    """
    try:
        db_obj, token = await invitation_service.create_invitation(
            db=db,
            email=invitation.email,
            tenant_id=tenant_id,
            inviter_id=current_user.id,
            role_id=invitation.role_id,
            expires_in_days=invitation.expires_in_days or 7
        )
        
        # Generate invitation link
        invitation_link = invitation_service.generate_invitation_link(token)
        
        return {
            "id": db_obj.id,
            "email": db_obj.email,
            "invitation_link": invitation_link,
            "expires_at": db_obj.expires_at
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=List[InvitationResponse],
    summary="List pending invitations",
    description="Get a list of all pending invitations for the current tenant."
)
async def list_pending_invitations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id)
) -> Any:
    """
    List all pending invitations for the tenant.
    """
    invitations = await invitation_service.get_pending_by_tenant(
        db=db,
        tenant_id=tenant_id,
        skip=skip,
        limit=limit
    )
    return invitations


@router.get(
    "/{invitation_id}",
    response_model=InvitationDetailResponse,
    summary="Get invitation details",
    description="Get detailed information about a specific invitation."
)
async def get_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id)
) -> Any:
    """
    Get a specific invitation by ID.
    """
    invitation = await invitation_service.get_invitation_with_details(
        db=db,
        invitation_id=invitation_id
    )
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
        
    # Check if invitation belongs to the current tenant
    if invitation["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
        
    return invitation


@router.put(
    "/{invitation_id}",
    response_model=InvitationResponse,
    summary="Update invitation",
    description="Update an existing invitation's properties."
)
async def update_invitation(
    invitation_id: UUID,
    data: InvitationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id)
) -> Any:
    """
    Update an invitation's properties.
    """
    # First check if invitation exists and belongs to this tenant
    invitation = await invitation_service.get(db, id=invitation_id)
    if not invitation or invitation.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    
    # Handle expires_in_days if provided
    if "expires_in_days" in update_data and update_data["expires_in_days"]:
        from datetime import datetime, timedelta
        invitation.expires_at = datetime.utcnow() + timedelta(days=update_data["expires_in_days"])
        del update_data["expires_in_days"]
    
    # Update other fields
    for field, value in update_data.items():
        setattr(invitation, field, value)
    
    await db.commit()
    await db.refresh(invitation)
    
    return invitation


@router.delete(
    "/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke invitation",
    description="Revoke an invitation so it can no longer be used."
)
async def revoke_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id)
) -> Any:
    """
    Revoke an invitation.
    """
    # First check if invitation exists and belongs to this tenant
    invitation = await invitation_service.get(db, id=invitation_id)
    if not invitation or invitation.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    await invitation_service.revoke_invitation(
        db=db,
        invitation_id=invitation_id
    )
    
    return None


@router.post(
    "/verify",
    response_model=InvitationTokenResponse,
    summary="Verify invitation token",
    description="Verify if an invitation token is valid and return information about it."
)
async def verify_invitation_token(
    token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Verify if an invitation token is valid and return information about it.
    """
    invitation = await invitation_service.verify_token(db=db, token=token)
    
    if not invitation:
        return {
            "valid": False,
            "token": token
        }
        
    # Get tenant and inviter information
    from sqlalchemy import select
    from virtualstack.models.iam.tenant import Tenant
    from virtualstack.models.iam.user import User
    
    tenant_stmt = select(Tenant).where(Tenant.id == invitation.tenant_id)
    tenant_result = await db.execute(tenant_stmt)
    tenant = tenant_result.scalars().first()
    
    inviter_stmt = select(User).where(User.id == invitation.inviter_id)
    inviter_result = await db.execute(inviter_stmt)
    inviter = inviter_result.scalars().first()
    
    return {
        "valid": True,
        "email": invitation.email,
        "tenant_id": invitation.tenant_id,
        "tenant_name": tenant.name if tenant else None,
        "inviter_email": inviter.email if inviter else None,
        "expires_at": invitation.expires_at,
        "role_id": invitation.role_id,
        "token": token
    } 