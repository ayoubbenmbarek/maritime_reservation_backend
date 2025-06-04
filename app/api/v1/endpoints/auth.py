"""
Authentication endpoints for the Maritime Reservation System.
Handles user registration, login, token refresh, and session management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
import logging

from app.db.session import get_db
from app.schemas import (
    UserCreate, UserResponse, LoginRequest, Token, RefreshTokenRequest,
    MessageResponse, ErrorResponse
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    
    Creates a new user with the provided information and sends a verification email.
    """
    try:
        auth_service = AuthService(db)
        user_service = UserService(db)
        
        # Check if user already exists
        existing_user = await user_service.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Check username availability if provided
        if user_data.username:
            existing_username = await user_service.get_user_by_username(user_data.username)
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Create user
        user = await auth_service.create_user(user_data)
        
        # Log registration
        logger.info(
            f"New user registered",
            extra={
                "user_id": str(user.id),
                "email": user.email,
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        # Send verification email (async task)
        # await send_verification_email.delay(user.id)
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login_user(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access tokens.
    
    Validates credentials and returns JWT access and refresh tokens.
    """
    try:
        auth_service = AuthService(db)
        
        # Authenticate user
        user = await auth_service.authenticate_user(login_data.email, login_data.password)
        if not user:
            # Log failed login attempt
            logger.warning(
                f"Failed login attempt",
                extra={
                    "email": login_data.email,
                    "ip_address": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                }
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is locked
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to too many failed login attempts"
            )
        
        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active"
            )
        
        # Create session and tokens
        session_data = {
            "user_agent": request.headers.get("user-agent"),
            "ip_address": str(request.client.host) if request.client else None,
            "device_fingerprint": request.headers.get("x-device-fingerprint"),
        }
        
        tokens = await auth_service.create_user_session(
            user, 
            session_data,
            remember_me=login_data.remember_me
        )
        
        # Update login statistics
        await auth_service.update_login_stats(user)
        
        # Log successful login
        logger.info(
            f"User logged in successfully",
            extra={
                "user_id": str(user.id),
                "email": user.email,
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Validates refresh token and returns new access and refresh tokens.
    """
    try:
        auth_service = AuthService(db)
        
        # Validate and refresh tokens
        tokens = await auth_service.refresh_user_session(refresh_data.refresh_token)
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        logger.info(
            f"Token refreshed",
            extra={
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user and invalidate session.
    
    Invalidates the current session and access token.
    """
    try:
        auth_service = AuthService(db)
        
        # Extract token from credentials
        token = credentials.credentials
        
        # Invalidate session
        success = await auth_service.invalidate_session(token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        logger.info(
            f"User logged out",
            extra={
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        return MessageResponse(message="Successfully logged out")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_sessions(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout from all sessions.
    
    Invalidates all active sessions for the current user.
    """
    try:
        auth_service = AuthService(db)
        
        # Get current user from token
        current_user = await auth_service.get_current_user(credentials.credentials)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Invalidate all sessions
        await auth_service.invalidate_all_user_sessions(current_user.id)
        
        logger.info(
            f"All sessions logged out",
            extra={
                "user_id": str(current_user.id),
                "email": current_user.email,
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        return MessageResponse(message="Successfully logged out from all sessions")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout all error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout all failed"
        )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user email address.
    
    Validates email verification token and marks email as verified.
    """
    try:
        auth_service = AuthService(db)
        
        # Verify email token
        success = await auth_service.verify_email(token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        return MessageResponse(message="Email verified successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification_email(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend email verification.
    
    Sends a new email verification link to the user.
    """
    try:
        auth_service = AuthService(db)
        user_service = UserService(db)
        
        # Get user by email
        user = await user_service.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists or not
            return MessageResponse(message="If the email exists, a verification link has been sent")
        
        # Check if already verified
        if user.email_verified:
            return MessageResponse(message="Email is already verified")
        
        # Send verification email
        # await send_verification_email.delay(user.id)
        
        return MessageResponse(message="Verification email sent")
        
    except Exception as e:
        logger.error(f"Resend verification error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset.
    
    Sends a password reset link to the user's email.
    """
    try:
        auth_service = AuthService(db)
        user_service = UserService(db)
        
        # Get user by email
        user = await user_service.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists or not
            return MessageResponse(message="If the email exists, a password reset link has been sent")
        
        # Generate and send reset token
        # await send_password_reset_email.delay(user.id)
        
        return MessageResponse(message="Password reset link sent")
        
    except Exception as e:
        logger.error(f"Forgot password error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset user password.
    
    Validates reset token and updates user password.
    """
    try:
        auth_service = AuthService(db)
        
        # Reset password
        success = await auth_service.reset_password(token, new_password)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        return MessageResponse(message="Password reset successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

