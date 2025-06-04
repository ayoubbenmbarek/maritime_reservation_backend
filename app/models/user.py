"""
User model for the Maritime Reservation System.
Handles user authentication, profiles, and session management.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Date, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.db.session import Base


class User(Base):
    """User model with comprehensive authentication and profile management."""
    
    __tablename__ = "users"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    nationality = Column(String(3), nullable=True)  # ISO 3166-1 alpha-3
    
    # Preferences
    preferred_language = Column(String(5), default="en", nullable=False)  # ISO 639-1
    preferred_currency = Column(String(3), default="EUR", nullable=False)  # ISO 4217
    
    # Verification status
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    
    # Account status and security
    account_status = Column(String(20), default="active", nullable=False)  # active, suspended, deleted
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    
    # Legal compliance
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    privacy_policy_accepted_at = Column(DateTime(timezone=True), nullable=True)
    marketing_consent = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, name={self.first_name} {self.last_name})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.account_status == "active"
    
    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until
    
    @property
    def is_verified(self) -> bool:
        """Check if user is fully verified."""
        return self.email_verified and self.phone_verified


class UserProfile(Base):
    """Extended user profile information."""
    
    __tablename__ = "user_profiles"
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    
    # Extended personal information
    title = Column(String(10), nullable=True)  # Mr, Mrs, Ms, Dr, etc.
    middle_name = Column(String(100), nullable=True)
    
    # Travel documents
    passport_number = Column(String(50), nullable=True)
    passport_expiry = Column(Date, nullable=True)
    passport_country = Column(String(3), nullable=True)  # ISO 3166-1 alpha-3
    
    # Emergency contact
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)
    
    # Special requirements
    dietary_restrictions = Column(ARRAY(Text), nullable=True)
    accessibility_requirements = Column(ARRAY(Text), nullable=True)
    
    # Preferences and settings
    travel_preferences = Column(JSON, nullable=True)
    notification_preferences = Column(JSON, nullable=True)
    
    # Profile customization
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Business information
    company_name = Column(String(200), nullable=True)
    company_vat_number = Column(String(50), nullable=True)
    
    # Addresses
    billing_address = Column(JSON, nullable=True)
    shipping_address = Column(JSON, nullable=True)
    
    # Loyalty program
    loyalty_points = Column(Integer, default=0, nullable=False)
    loyalty_tier = Column(String(20), default="bronze", nullable=False)
    
    # Referral system
    referral_code = Column(String(20), unique=True, nullable=True)
    referred_by_code = Column(String(20), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id}, loyalty_tier={self.loyalty_tier})>"


class UserSession(Base):
    """User session management with security tracking."""
    
    __tablename__ = "user_sessions"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    
    # Session tokens
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)
    
    # Device and security information
    device_fingerprint = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(INET, nullable=True)
    location_country = Column(String(3), nullable=True)
    location_city = Column(String(100), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if session is valid and active."""
        return self.is_active and not self.is_expired

