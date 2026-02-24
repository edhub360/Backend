import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from login.app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing functions"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "secure_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > len(password)
    
    def test_verify_password_correct(self):
        """Test verifying correct password"""
        password = "secure_password_123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        password = "secure_password_123"
        hashed = hash_password(password)
        
        assert verify_password("wrong_password", hashed) is False
    
    def test_bcrypt_72_byte_limit(self):
        """Test handling of passwords longer than 72 bytes"""
        long_password = "a" * 100
        hashed = hash_password(long_password)
        
        # Should verify because we truncate at 72 bytes
        assert verify_password(long_password, hashed) is True


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and verification"""
    
    def test_create_access_token(self, mock_settings):
        """Test creating access token"""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self, mock_settings):
        """Test decoding valid token"""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        decoded = decode_jwt_token(token)
        assert decoded["sub"] == "user@example.com"
        assert decoded["user_id"] == "123"
    
    def test_decode_expired_token(self, mock_settings):
        """Test decoding expired token"""
        from freezegun import freeze_time
        
        data = {"sub": "user@example.com"}
        token = create_access_token(data)
        
        # Freeze time and move forward beyond token expiry
        with freeze_time("2099-01-01"):
            with pytest.raises(Exception):  # JWT will be expired
                decode_jwt_token(token)
    
    def test_create_refresh_token(self):
        """Test creating refresh token"""
        token, token_hash = create_refresh_token()
        
        assert isinstance(token, str)
        assert isinstance(token_hash, str)
        assert token != token_hash
        assert len(token) > 0
