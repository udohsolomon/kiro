"""Authentication service for user management."""

import secrets
import uuid
from typing import Optional

import bcrypt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.config import get_settings
from app.models.user import User

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key.

    Returns:
        Tuple of (full_api_key, api_key_hash)
    """
    # Generate random token
    token = secrets.token_hex(32)
    full_key = f"{settings.api_key_prefix}{token}"

    # Hash the key for storage
    key_hash = hash_password(full_key)

    return full_key, key_hash


def generate_verification_token() -> str:
    """Generate a verification token for email verification."""
    return secrets.token_urlsafe(32)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get a user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get a user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_api_key_prefix(
    db: AsyncSession, api_key_prefix: str
) -> Optional[User]:
    """Get a user by API key prefix."""
    result = await db.execute(
        select(User).where(User.api_key_prefix == api_key_prefix)
    )
    return result.scalar_one_or_none()


async def get_user_by_verification_token(
    db: AsyncSession, token: str
) -> Optional[User]:
    """Get a user by verification token."""
    result = await db.execute(
        select(User).where(User.verification_token == token)
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    username: str,
    password: str,
) -> tuple[User, str]:
    """Create a new user.

    Returns:
        Tuple of (user, api_key)
    """
    # Hash password
    password_hash = hash_password(password)

    # Generate API key
    api_key, api_key_hash = generate_api_key()

    # Generate verification token
    verification_token = generate_verification_token()

    # Create user
    user = User(
        email=email,
        username=username,
        password_hash=password_hash,
        api_key_hash=api_key_hash,
        api_key_prefix=api_key[:20],  # Store prefix for lookup
        verification_token=verification_token,
        verified=False,
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user, api_key


async def verify_user(db: AsyncSession, token: str) -> Optional[tuple[User, str]]:
    """Verify a user's email and return their API key.

    Returns:
        Tuple of (user, api_key) if successful, None otherwise
    """
    user = await get_user_by_verification_token(db, token)
    if not user:
        return None

    # Generate new API key (the original was only stored as hash)
    api_key, api_key_hash = generate_api_key()

    # Update user
    user.verified = True
    user.verification_token = None
    user.api_key_hash = api_key_hash
    user.api_key_prefix = api_key[:20]

    await db.flush()
    await db.refresh(user)

    return user, api_key


async def validate_api_key(db: AsyncSession, api_key: str) -> Optional[User]:
    """Validate an API key and return the user if valid."""
    if not api_key.startswith(settings.api_key_prefix):
        return None

    # Find user by prefix
    prefix = api_key[:20]
    user = await get_user_by_api_key_prefix(db, prefix)

    if not user:
        return None

    # Verify the full key
    if not verify_password(api_key, user.api_key_hash):
        return None

    # Check if verified
    if not user.verified:
        return None

    return user


async def verify_google_token(token: str) -> Optional[dict]:
    """Verify Google ID token and return user info."""
    try:
        id_info = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.google_client_id,
            clock_skew_in_seconds=10
        )
        return id_info
    except ValueError:
        return None


async def get_or_create_google_user(
    db: AsyncSession,
    email: str,
    name: str = "",
    regenerate_api_key: bool = False,
) -> tuple[User, str]:
    """Get existing user or create a new one from Google info.
    
    Args:
        db: Database session
        email: User's email from Google
        name: User's name from Google
        regenerate_api_key: If True, generates a new API key for existing users.
                           Default False to preserve existing API keys.
    
    Returns:
        Tuple of (user, api_key). For existing users with regenerate_api_key=False,
        returns a placeholder indicating they should use their existing key.
    """
    user = await get_user_by_email(db, email)
    
    if user:
        # Ensure verified if coming from Google
        if not user.verified:
            user.verified = True
            user.verification_token = None
            await db.flush()
            await db.refresh(user)
        
        # Only regenerate API key if explicitly requested
        if regenerate_api_key:
            api_key, api_key_hash = generate_api_key()
            user.api_key_hash = api_key_hash
            user.api_key_prefix = api_key[:20]
            await db.flush()
            await db.refresh(user)
            return user, api_key
        
        # Return existing user without changing API key
        # The caller should handle this case appropriately
        return user, "EXISTING_USER_API_KEY_UNCHANGED"

    # Create new user
    # Username: derive from email or name, make unique
    base_username = name.replace(" ", "") if name else email.split("@")[0]
    # Filter alphanumeric
    base_username = "".join(c for c in base_username if c.isalnum())[:15]
    if not base_username:
        base_username = "user"
        
    username = base_username
    counter = 1
    # Check for username collision
    while await get_user_by_username(db, username):
        username = f"{base_username}{counter}"
        counter += 1
        
    # Random password for Google users
    password = secrets.token_urlsafe(32)
    password_hash = hash_password(password)

    # Generate API key
    api_key, api_key_hash = generate_api_key()

    # Create user (auto-verified)
    user = User(
        email=email,
        username=username,
        password_hash=password_hash,
        api_key_hash=api_key_hash,
        api_key_prefix=api_key[:20],
        verified=True,
        verification_token=None,
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user, api_key


async def regenerate_user_api_key(db: AsyncSession, user: User) -> str:
    """Regenerate API key for a user.
    
    Use this when user explicitly requests a new API key.
    
    Args:
        db: Database session
        user: User to regenerate key for
        
    Returns:
        The new API key
    """
    api_key, api_key_hash = generate_api_key()
    user.api_key_hash = api_key_hash
    user.api_key_prefix = api_key[:20]
    await db.flush()
    await db.refresh(user)
    return api_key
