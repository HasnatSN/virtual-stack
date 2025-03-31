import secrets
import uuid
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.config import settings
from virtualstack.models.iam.invitation import Invitation, InvitationStatus
from virtualstack.models.iam.tenant import Tenant
from virtualstack.models.iam.user import User
from virtualstack.services.base import CRUDBase


class InvitationService(CRUDBase[Invitation, Dict[str, Any], Dict[str, Any]]):
    """
    Service for invitation management.
    """
    
    async def create_invitation(
        self,
        db: AsyncSession,
        *,
        email: str,
        tenant_id: UUID,
        inviter_id: UUID,
        role_id: Optional[UUID] = None,
        expires_in_days: int = 7,
    ) -> Tuple[Invitation, str]:
        """
        Create a new invitation and return both the model and the token.
        
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
                self.model.expires_at > datetime.utcnow()
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
            expires_at=expires_at
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        return db_obj, token
    
    async def get_by_token(
        self,
        db: AsyncSession,
        *,
        token: str
    ) -> Optional[Invitation]:
        """
        Get an invitation by token.
        
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
        self,
        db: AsyncSession,
        *,
        email: str,
        tenant_id: UUID
    ) -> List[Invitation]:
        """
        Get invitations by email and tenant.
        
        Args:
            db: Database session
            email: Email address
            tenant_id: Tenant ID
            
        Returns:
            List of invitations
        """
        stmt = select(self.model).where(
            and_(
                self.model.email == email,
                self.model.tenant_id == tenant_id
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_pending_by_tenant(
        self,
        db: AsyncSession,
        *,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invitation]:
        """
        Get pending invitations for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of pending invitations
        """
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.status == InvitationStatus.PENDING,
                self.model.expires_at > datetime.utcnow()
            )
        ).order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def verify_token(
        self,
        db: AsyncSession,
        *,
        token: str
    ) -> Optional[Invitation]:
        """
        Verify an invitation token.
        
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
        self,
        db: AsyncSession,
        *,
        token: str,
        user_id: UUID
    ) -> Optional[Invitation]:
        """
        Accept an invitation and associate it with a user.
        
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
            
        # Update invitation
        invitation.status = InvitationStatus.ACCEPTED
        invitation.user_id = user_id
        invitation.accepted_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(invitation)
        
        return invitation
    
    async def revoke_invitation(
        self,
        db: AsyncSession,
        *,
        invitation_id: UUID
    ) -> Optional[Invitation]:
        """
        Revoke an invitation.
        
        Args:
            db: Database session
            invitation_id: Invitation ID
            
        Returns:
            Updated invitation or None if not found
        """
        invitation = await self.get(db, id=invitation_id)
        
        if not invitation:
            return None
            
        # Update invitation status
        invitation.status = InvitationStatus.REVOKED
        
        await db.commit()
        await db.refresh(invitation)
        
        return invitation
    
    async def get_invitation_with_details(
        self,
        db: AsyncSession,
        *,
        invitation_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get an invitation with tenant and inviter details.
        
        Args:
            db: Database session
            invitation_id: Invitation ID
            
        Returns:
            Invitation with details or None
        """
        invitation = await self.get(db, id=invitation_id)
        
        if not invitation:
            return None
            
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
        """
        Generate a frontend URL for the invitation.
        
        Args:
            token: Invitation token
            
        Returns:
            URL for the invitation
        """
        return f"{settings.FRONTEND_URL}/accept-invitation?token={token}"


# Create a singleton instance
invitation_service = InvitationService(Invitation) 