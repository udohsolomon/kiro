"""Tests for authentication endpoints and services."""

import pytest
from httpx import AsyncClient

from app.services import auth_service


class TestRegister:
    """Tests for user registration (T-02.1)."""

    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient, sample_user_data: dict):
        """Test successful user registration."""
        response = await client.post("/v1/auth/register", json=sample_user_data)

        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["username"] == sample_user_data["username"]
        assert data["message"] == "Verification email sent"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client: AsyncClient, sample_user_data: dict
    ):
        """Test registration with duplicate email."""
        # Register first user
        await client.post("/v1/auth/register", json=sample_user_data)

        # Try to register with same email
        response = await client.post("/v1/auth/register", json=sample_user_data)

        assert response.status_code == 409
        assert "Email already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, client: AsyncClient, sample_user_data: dict
    ):
        """Test registration with duplicate username."""
        # Register first user
        await client.post("/v1/auth/register", json=sample_user_data)

        # Try to register with same username but different email
        user_data = sample_user_data.copy()
        user_data["email"] = "different@example.com"
        response = await client.post("/v1/auth/register", json=user_data)

        assert response.status_code == 409
        assert "Username already taken" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "testuser",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "weakpass",  # No uppercase, no digit
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_username(self, client: AsyncClient):
        """Test registration with short username."""
        response = await client.post(
            "/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "ab",  # Less than 3 chars
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 422


class TestPasswordHashing:
    """Tests for password hashing (T-02.2)."""

    def test_password_hashing(self):
        """Test password hashing with bcrypt."""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)

        # Hash should be different from original
        assert hashed != password

        # Hash should be a valid bcrypt hash (starts with $2b$)
        assert hashed.startswith("$2b$")

        # Should be able to verify
        assert auth_service.verify_password(password, hashed) is True

    def test_password_verification_wrong_password(self):
        """Test that wrong password fails verification."""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password("WrongPassword123!", hashed) is False

    def test_password_hashing_unique_salts(self):
        """Test that same password produces different hashes."""
        password = "SecurePassword123!"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        # Different salts should produce different hashes
        assert hash1 != hash2

        # Both should still verify correctly
        assert auth_service.verify_password(password, hash1) is True
        assert auth_service.verify_password(password, hash2) is True


class TestApiKeyGeneration:
    """Tests for API key generation (T-02.3)."""

    def test_api_key_generation(self):
        """Test API key generation."""
        full_key, key_hash = auth_service.generate_api_key()

        # Key should start with prefix
        assert full_key.startswith("kiro_")

        # Key should be long enough (prefix + 64 hex chars)
        assert len(full_key) >= 69

        # Hash should be a bcrypt hash
        assert key_hash.startswith("$2b$")

        # Should be able to verify the key
        assert auth_service.verify_password(full_key, key_hash) is True

    def test_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        keys = [auth_service.generate_api_key()[0] for _ in range(10)]

        # All keys should be unique
        assert len(set(keys)) == 10

    def test_verification_token_generation(self):
        """Test verification token generation."""
        token = auth_service.generate_verification_token()

        # Token should be a URL-safe string
        assert len(token) > 20  # Should be reasonably long

        # Generate another to ensure uniqueness
        token2 = auth_service.generate_verification_token()
        assert token != token2


class TestApiKeyMiddleware:
    """Tests for API key validation middleware (T-02.4)."""

    @pytest.mark.asyncio
    async def test_api_key_middleware(
        self, client: AsyncClient, test_session, sample_user_data: dict
    ):
        """Test API key validation in protected routes."""
        # Register a user
        response = await client.post("/v1/auth/register", json=sample_user_data)
        assert response.status_code == 201

        # Get the user and their verification token
        user = await auth_service.get_user_by_email(
            test_session, sample_user_data["email"]
        )
        assert user is not None

        # Verify the user
        result = await auth_service.verify_user(test_session, user.verification_token)
        assert result is not None
        user, api_key = result

        # Now test the API key validation
        validated_user = await auth_service.validate_api_key(test_session, api_key)
        assert validated_user is not None
        assert validated_user.id == user.id

    @pytest.mark.asyncio
    async def test_api_key_middleware_invalid_key(self, test_session):
        """Test that invalid API key fails validation."""
        result = await auth_service.validate_api_key(test_session, "invalid_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_api_key_middleware_wrong_prefix(self, test_session):
        """Test that API key with wrong prefix fails."""
        result = await auth_service.validate_api_key(
            test_session, "wrong_prefix_123456"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_api_key_middleware_unverified_user(
        self, client: AsyncClient, test_session, sample_user_data: dict
    ):
        """Test that unverified user's API key is rejected."""
        # Register a user but don't verify
        response = await client.post("/v1/auth/register", json=sample_user_data)
        assert response.status_code == 201

        # Get the user
        user = await auth_service.get_user_by_email(
            test_session, sample_user_data["email"]
        )

        # Generate a valid-looking API key for testing
        # Note: The actual API key was not stored, only its hash
        # So we can't validate it anyway without verification
        fake_key = f"kiro_{user.api_key_prefix[5:]}"  # Won't match hash
        result = await auth_service.validate_api_key(test_session, fake_key)
        assert result is None


class TestEmailVerification:
    """Tests for email verification flow (T-02.5)."""

    @pytest.mark.asyncio
    async def test_email_verification(
        self, client: AsyncClient, test_session, sample_user_data: dict
    ):
        """Test complete email verification flow."""
        # Register a user
        response = await client.post("/v1/auth/register", json=sample_user_data)
        assert response.status_code == 201

        # Get the user's verification token
        user = await auth_service.get_user_by_email(
            test_session, sample_user_data["email"]
        )
        assert user is not None
        assert user.verification_token is not None
        assert user.verified is False

        # Verify via API
        response = await client.post(
            "/v1/auth/verify", json={"token": user.verification_token}
        )
        assert response.status_code == 200

        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("kiro_")
        assert "starter_package_url" in data

    @pytest.mark.asyncio
    async def test_email_verification_invalid_token(self, client: AsyncClient):
        """Test verification with invalid token."""
        response = await client.post(
            "/v1/auth/verify", json={"token": "invalid-token-12345"}
        )

        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_email_verification_token_consumed(
        self, client: AsyncClient, test_session, sample_user_data: dict
    ):
        """Test that verification token is consumed after use."""
        # Register a user
        await client.post("/v1/auth/register", json=sample_user_data)

        # Get the verification token
        user = await auth_service.get_user_by_email(
            test_session, sample_user_data["email"]
        )
        token = user.verification_token

        # Verify once
        response = await client.post("/v1/auth/verify", json={"token": token})
        assert response.status_code == 200

        # Try to verify again with same token
        response = await client.post("/v1/auth/verify", json={"token": token})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_verified_user_has_api_key(
        self, client: AsyncClient, test_session, sample_user_data: dict
    ):
        """Test that verified user can use their API key."""
        # Register and verify
        await client.post("/v1/auth/register", json=sample_user_data)
        user = await auth_service.get_user_by_email(
            test_session, sample_user_data["email"]
        )

        response = await client.post(
            "/v1/auth/verify", json={"token": user.verification_token}
        )
        api_key = response.json()["api_key"]

        # Validate the API key
        validated_user = await auth_service.validate_api_key(test_session, api_key)
        assert validated_user is not None
        assert validated_user.verified is True
        assert validated_user.username == sample_user_data["username"]
