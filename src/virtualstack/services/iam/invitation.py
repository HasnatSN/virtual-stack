from datetime import datetime, timedelta
import secrets
from typing import Any, Optional
from uuid import UUID

import logging
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.config import settings
from virtualstack.models.iam.invitation import Invitation, InvitationStatus
from virtualstack.models.iam.tenant import Tenant
from virtualstack.models.iam.user import User
from virtualstack.services.base import CRUDBase

logger = logging.getLogger(__name__)


class InvitationService(CRUDBase[Invitation, dict[str, Any], dict[str, Any]]):
    """Service for invitation management."""

    async def create_invitation(
        self,
        db: AsyncSession,
        *,
        email: str,
        tenant_id: UUID,
        inviter_id: UUID,
        role_id: Optional[UUID] = None,
        expires_in_days: int = 7,
    ) -> tuple[Invitation, str]:
        """Create a new invitation and return both the model and the token.

        Args:
            db: Database session
            email: Email address of the invitee
            tenant_id: Tenant ID
            inviter_id: User ID of the inviter
            role_id: Optional role ID to assign on acceptance
            expires_in_days: Number of days until the invitation expires

        Returns:
            A tuple containing (invitation_model, token)
        """
        # Check if an active invitation already exists for this email and tenant
        stmt = select(self.model).where(
            and_(
                self.model.email == email,
                self.model.tenant_id == tenant_id,
                self.model.status == InvitationStatus.PENDING,
                self.model.expires_at > datetime.utcnow(),
            )
        )
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            # Return existing invitation
            return existing, existing.token

        # Generate token
        token = secrets.token_urlsafe(32)

        # Calculate expiration date
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create invitation
        db_obj = self.model(
            email=email,
            tenant_id=tenant_id,
            inviter_id=inviter_id,
            role_id=role_id,
            token=token,
            status=InvitationStatus.PENDING,
            expires_at=expires_at,
        )

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj, token

    async def get_by_token(self, db: AsyncSession, *, token: str) -> Optional[Invitation]:
        """Get an invitation by token.

        Args:
            db: Database session
            token: Invitation token

        Returns:
            Invitation or None
        """
        stmt = select(self.model).where(self.model.token == token)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_email_and_tenant(
        self, db: AsyncSession, *, email: str, tenant_id: UUID
    ) -> list[Invitation]:
        """Get invitations by email and tenant.

        Args:
            db: Database session
            email: Email address
            tenant_id: Tenant ID

        Returns:
            List of invitations
        """
        stmt = select(self.model).where(
            and_(self.model.email == email, self.model.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_by_tenant(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Invitation]:
        """Get pending invitations for a tenant.

        Args:
            db: Database session
            tenant_id: Tenant ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of pending invitations
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.tenant_id == tenant_id,
                    self.model.status == InvitationStatus.PENDING,
                    self.model.expires_at > datetime.utcnow(),
                )
            )
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def verify_token(self, db: AsyncSession, *, token: str) -> Optional[Invitation]:
        """Verify an invitation token.

        Args:
            db: Database session
            token: Invitation token

        Returns:
            Valid invitation or None
        """
        invitation = await self.get_by_token(db, token=token)

        if not invitation:
            return None

        # Check if expired
        if invitation.expires_at < datetime.utcnow():
            invitation.status = InvitationStatus.EXPIRED
            await db.commit()
            return None

        # Check if pending
        if invitation.status != InvitationStatus.PENDING:
            return None

        return invitation

    async def accept_invitation(
        self, db: AsyncSession, *, token: str, user_id: UUID
    ) -> Optional[Invitation]:
        """Accept an invitation and associate it with a user. Assigns role if specified.

        Args:
            db: Database session
            token: Invitation token
            user_id: User ID to associate with the invitation

        Returns:
            Updated invitation or None if invalid
        """
        invitation = await self.verify_token(db, token=token)

        if not invitation:
            return None

        # Update invitation status and user association
        invitation.status = InvitationStatus.ACCEPTED
        invitation.user_id = user_id
        invitation.accepted_at = datetime.utcnow()

        # --- Assign Role if specified --- TODO: Add tests for this logic
        assigned_role_id = None
        if invitation.role_id:
            # Import user_service locally to avoid circular dependency
            from virtualstack.services.iam import user_service
            try:
                logger.info(
                    f"Attempting to assign role {invitation.role_id} to user {user_id} "
                    f"in tenant {invitation.tenant_id} upon invitation acceptance."
                )

                # TODO: Consider potential race conditions or if user already has the role.
                # user_service.assign_role_to_user_in_tenant should handle duplicates gracefully.
                await user_service.assign_role_to_user_in_tenant(
                    db=db,
                    user_id=user_id,
                    tenant_id=invitation.tenant_id,
                    role_id=invitation.role_id,
                )
                assigned_role_id = invitation.role_id
                logger.info(
                    f"Successfully assigned role {invitation.role_id} to user {user_id} "
                    f"in tenant {invitation.tenant_id}."
                )
            except Exception as e:
                # Log an error if role assignment fails, but don't prevent invitation acceptance
                logger.error(
                    f"Failed to assign role {invitation.role_id} to user {user_id} "
                    f"in tenant {invitation.tenant_id} during invitation acceptance: {e}",
                    exc_info=True, # Include stack trace
                )
                # TODO: Decide on error handling strategy. Should acceptance fail if role assignment fails?
                # For now, we proceed with acceptance but log the error.

        # Commit changes (invitation status, user_id, accepted_at)
        await db.commit()
        await db.refresh(invitation) # Refresh to get updated state

        # Return the updated invitation model
        # The assigned_role_id is not part of the return model, just logged.
        return invitation

    async def revoke_invitation(
        self, db: AsyncSession, *, invitation_id: UUID
    ) -> Optional[Invitation]:
        """Revoke an invitation.

        Args:
            db: Database session
            invitation_id: Invitation ID

        Returns:
            Updated invitation or None if not found
        """
        # Use record_id for the base get method
        invitation = await self.get(db, record_id=invitation_id)

        if not invitation:
            logger.warning(f"Attempted to revoke non-existent invitation: {invitation_id}")
            return None

        # Check if already revoked or expired or accepted
        if invitation.status != InvitationStatus.PENDING:
            logger.warning(
                f"Attempted to revoke invitation {invitation_id} which is already in status: {invitation.status}"
            )
            # Return the invitation as is, as it's not pending anymore
            return invitation

        # Update status to REVOKED
        invitation.status = InvitationStatus.REVOKED
        await db.commit()
        await db.refresh(invitation)

        logger.info(f"Invitation {invitation_id} revoked successfully.")
        return invitation

    async def get_invitation_with_details(
        self, db: AsyncSession, *, invitation_id: UUID
    ) -> Optional[dict[str, Any]]:
        """Get invitation details including related tenant and inviter info."""
        # TODO: Optimize this query if needed, potentially joining tables
        # Use the correct argument name 'record_id' for the base get method
        invitation = await self.get(db, record_id=invitation_id)
        if not invitation:
            return None

        # Fetch related objects (assuming eager loading isn't configured or needed)
        # Get tenant and inviter details
        tenant_stmt = select(Tenant).where(Tenant.id == invitation.tenant_id)
        tenant_result = await db.execute(tenant_stmt)
        tenant = tenant_result.scalars().first()

        inviter_stmt = select(User).where(User.id == invitation.inviter_id)
        inviter_result = await db.execute(inviter_stmt)
        inviter = inviter_result.scalars().first()

        invitation_dict = jsonable_encoder(invitation)

        # Add additional details
        invitation_dict["tenant_name"] = tenant.name if tenant else None
        invitation_dict["inviter_email"] = inviter.email if inviter else None
        invitation_dict["is_expired"] = invitation.is_expired
        invitation_dict["is_pending"] = invitation.is_pending

        return invitation_dict

    def generate_invitation_link(self, token: str) -> str:
        """Generate a frontend URL for the invitation.

        Args:
            token: Invitation token

        Returns:
            URL for the invitation
        """
        return f"{settings.FRONTEND_URL}/accept-invitation?token={token}"

    # TODO: Implement get_multi_by_tenant method
    async def get_multi_by_tenant(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Invitation]:
        """Get multiple invitations for a specific tenant.

        Args:
            db: Database session
            tenant_id: Tenant ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of invitations for the tenant.
        """
        logger.debug(f"Fetching invitations for tenant_id={tenant_id} with skip={skip}, limit={limit}")
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == tenant_id)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        invitations = list(result.scalars().all())
        logger.debug(f"Found {len(invitations)} invitations for tenant_id={tenant_id}")
        return invitations


# Create a singleton instance
invitation_service = InvitationService(Invitation)
