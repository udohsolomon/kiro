"""Authentication routes."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, CurrentUser
from app.config import get_settings
from app.schemas.user import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserVerifyRequest,
    UserVerifyResponse,
    GoogleLoginRequest,
    UserProfileResponse,
)
from app.services import auth_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: UserRegisterRequest,
    db: DbSession,
) -> UserRegisterResponse:
    """Register a new user.

    Creates a new user account and sends a verification email.
    """
    # Check if email already exists
    existing = await auth_service.get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check if username already exists
    existing = await auth_service.get_user_by_username(db, request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Create user
    user, api_key = await auth_service.create_user(
        db=db,
        email=request.email,
        username=request.username,
        password=request.password,
    )

    # In debug mode, auto-verify and return API key immediately
    if settings.debug:
        result = await auth_service.verify_user(db, user.verification_token)
        if result:
            user, api_key = result
            logger.info(f"User auto-verified (debug mode): {user.username}")
            return UserRegisterResponse(
                user_id=user.id,
                username=user.username,
                message="Account created and verified (debug mode)",
                api_key=api_key,
            )

    # Production: Send verification email
    logger.info(f"Verification email sent to {user.email} (token: {user.verification_token[:8]}...)")

    return UserRegisterResponse(
        user_id=user.id,
        username=user.username,
        message="Verification email sent. Check your email for the verification link.",
    )


@router.post(
    "/verify",
    response_model=UserVerifyResponse,
)
async def verify_email(
    request: UserVerifyRequest,
    db: DbSession,
) -> UserVerifyResponse:
    """Verify user email with token.

    Returns the API key after successful verification.
    """
    result = await auth_service.verify_user(db, request.token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user, api_key = result

    return UserVerifyResponse(
        api_key=api_key,
        starter_package_url="/downloads/starter-package.zip",
    )


@router.post(
    "/google",
    response_model=UserVerifyResponse,
)
async def google_login(
    request: GoogleLoginRequest,
    db: DbSession,
) -> UserVerifyResponse:
    """Login or register with Google.

    For new users: Creates account and returns a new API key.
    For existing users: Returns a message to use their existing API key,
    unless regenerate_key=true is passed, in which case a new API key is generated.
    """
    # Verify token
    id_info = await auth_service.verify_google_token(request.token)
    if not id_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google token",
        )

    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing email",
        )

    # Get or create user (optionally regenerate API key for existing users)
    user, api_key = await auth_service.get_or_create_google_user(
        db, email, id_info.get("name", ""),
        regenerate_api_key=request.regenerate_key
    )

    # For existing users who didn't request regeneration
    if api_key == "EXISTING_USER_API_KEY_UNCHANGED":
        return UserVerifyResponse(
            api_key="Use your existing API key. Request /auth/regenerate-key if you need a new one.",
            starter_package_url="/downloads/starter-package.zip",
            message="Welcome back! Your existing API key is still valid.",
        )

    # New user or regenerated key
    if request.regenerate_key:
        logger.info(f"API key regenerated via Google OAuth for user {user.username}")
        return UserVerifyResponse(
            api_key=api_key,
            starter_package_url="/downloads/starter-package.zip",
            message="API key regenerated successfully! Your old key is now invalid.",
        )

    return UserVerifyResponse(
        api_key=api_key,
        starter_package_url="/downloads/starter-package.zip",
        message="Account created successfully!",
    )


@router.post(
    "/regenerate-key",
    response_model=UserVerifyResponse,
)
async def regenerate_api_key(
    db: DbSession,
    user: CurrentUser,
) -> UserVerifyResponse:
    """Regenerate API key for the authenticated user.

    This invalidates the previous API key. Use this if your key was
    compromised or you want a fresh key.

    Requires authentication with your current API key.
    """
    new_api_key = await auth_service.regenerate_user_api_key(db, user)

    logger.info(f"API key regenerated for user {user.username}")

    return UserVerifyResponse(
        api_key=new_api_key,
        starter_package_url="/downloads/starter-package.zip",
        message="API key regenerated successfully. Your old key is now invalid.",
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
)
async def get_current_user_profile(
    user: CurrentUser,
) -> UserProfileResponse:
    """Get the current authenticated user's profile.

    Returns user info including API key prefix (first 20 chars).
    The full API key cannot be retrieved from the server - it's only
    shown once at creation. Use /auth/regenerate-key to get a new key.
    """
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        api_key_prefix=user.api_key_prefix,
        verified=user.verified,
        created_at=user.created_at,
    )
