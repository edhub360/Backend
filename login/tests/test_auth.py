"""Authentication tests."""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, AuthCredential


class TestGoogleAuth:
    """Test Google authentication flow."""
    
    @patch('app.auth.verify_google_token')
    async def test_google_signin_new_user(self, mock_verify, client: AsyncClient):
        """Test Google sign-in with new user."""
        # Mock Google token verification
        mock_verify.return_value = {
            'google_id': '123456789',
            'email': 'test@example.com',
            'name': 'Test User',
            'picture': 'https://example.com/photo.jpg'
        }
        
        response = await client.post(
            "/auth/google",
            json={"token": "mock_google_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"
    
    @patch('app.auth.verify_google_token')
    async def test_google_signin_existing_user(self, mock_verify, client: AsyncClient, db_session: AsyncSession):
        """Test Google sign-in with existing user."""
        # Create existing user
        user = User(email="test@example.com", name="Old Name")
        db_session.add(user)
        await db_session.commit()
        
        # Mock Google token verification
        mock_verify.return_value = {
            'google_id': '123456789',
            'email': 'test@example.com',
            'name': 'Updated Name',
            'picture': 'https://example.com/photo.jpg'
        }
        
        response = await client.post(
            "/auth/google",
            json={"token": "mock_google_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["name"] == "Updated Name"  # Name should be updated
    
    @patch('app.auth.verify_google_token')
    async def test_google_signin_invalid_token(self, mock_verify, client: AsyncClient):
        """Test Google sign-in with invalid token."""
        from fastapi import HTTPException
        
        mock_verify.side_effect = HTTPException(status_code=400, detail="Invalid Google token")
        
        response = await client.post(
            "/auth/google",
            json={"token": "invalid_token"}
        )
        
        assert response.status_code == 400


class TestEmailAuth:
    """Test email/password authentication."""
    
    async def test_register_success(self, client: AsyncClient):
        """Test successful registration."""
        response = await client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "StrongPass123",
                "name": "New User"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "newuser@example.com"
    
    async def test_register_duplicate_email(self, client: AsyncClient, db_session: AsyncSession):
        """Test registration with duplicate email."""
        # Create existing user
        user = User(email="existing@example.com")
        db_session.add(user)
        await db_session.commit()
        
        response = await client.post(
            "/auth/register",
            json={
                "email": "existing@example.com",
                "password": "StrongPass123"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        response = await client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_login_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful login."""
        from app.auth import hash_password
        
        # Create user with credentials
        user = User(email="login@example.com")
        db_session.add(user)
        await db_session.flush()
        
        auth_cred = AuthCredential(
            user_id=user.user_id,
            provider="email",
            password_hash=hash_password("TestPass123")
        )
        db_session.add(auth_cred)
        await db_session.commit()
        
        response = await client.post(
            "/auth/login",
            json={
                "email": "login@example.com",
                "password": "TestPass123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        response = await client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpass"
            }
        )
        
        assert response.status_code == 401


class TestTokenManagement:
    """Test token refresh and logout."""
    
    async def test_refresh_token(self, client: AsyncClient, db_session: AsyncSession):
        """Test token refresh."""
        from app.auth import hash_password
        
        # Create user and login
        user = User(email="refresh@example.com")
        db_session.add(user)
        await db_session.flush()
        
        auth_cred = AuthCredential(
            user_id=user.user_id,
            provider="email",
            password_hash=hash_password("TestPass123")
        )
        db_session.add(auth_cred)
        await db_session.commit()
        
        # Login to get tokens
        login_response = await client.post(
            "/auth/login",
            json={
                "email": "refresh@example.com",
                "password": "TestPass123"
            }
        )
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Test refresh
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["refresh_token"] != refresh_token  # Token rotation
    
    async def test_logout(self, client: AsyncClient, db_session: AsyncSession):
        """Test logout functionality."""
        from app.auth import hash_password
        
        # Create user and login
        user = User(email="logout@example.com")
        db_session.add(user)
        await db_session.flush()
        
        auth_cred = AuthCredential(
            user_id=user.user_id,
            provider="email",
            password_hash=hash_password("TestPass123")
        )
        db_session.add(auth_cred)
        await db_session.commit()
        
        # Login to get tokens
        login_response = await client.post(
            "/auth/login",
            json={
                "email": "logout@example.com",
                "password": "TestPass123"
            }
        )
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Test logout
        response = await client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        
        # Try to use refresh token again (should fail)
        refresh_response = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 401


class TestProtectedEndpoints:
    """Test protected endpoint access."""
    
    async def test_me_endpoint_authenticated(self, client: AsyncClient, db_session: AsyncSession):
        """Test /me endpoint with valid token."""
        from app.auth import hash_password
        
        # Create user and login
        user = User(email="me@example.com", name="Me User")
        db_session.add(user)
        await db_session.flush()
        
        auth_cred = AuthCredential(
            user_id=user.user_id,
            provider="email",
            password_hash=hash_password("TestPass123")
        )
        db_session.add(auth_cred)
        await db_session.commit()
        
        # Login to get token
        login_response = await client.post(
            "/auth/login",
            json={
                "email": "me@example.com",
                "password": "TestPass123"
            }
        )
        
        access_token = login_response.json()["access_token"]
        
        # Test protected endpoint
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@example.com"
    
    async def test_me_endpoint_unauthenticated(self, client: AsyncClient):
        """Test /me endpoint without token."""
        response = await client.get("/auth/me")
        
        assert response.status_code == 401
