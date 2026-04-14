"""
tests/unit/login/test_utils.py
================================
Unit tests for app/utils.py

Coverage:
  - generate_secure_token
  - hash_token
  - verify_token_hash
"""

import pytest
import hashlib
from login.app.utils import generate_secure_token, hash_token, verify_token_hash


# ══════════════════════════════════════════════════════════════════════════════
# generate_secure_token
# ══════════════════════════════════════════════════════════════════════════════
class TestGenerateSecureToken:

    def test_returns_string(self):
        assert isinstance(generate_secure_token(), str)

    def test_default_token_is_not_empty(self):
        assert len(generate_secure_token()) > 0

    def test_default_length_produces_url_safe_string(self):
        token = generate_secure_token()
        # secrets.token_urlsafe(32) produces ~43 chars (base64url of 32 bytes)
        assert len(token) >= 32

    def test_custom_length_produces_longer_token(self):
        short  = generate_secure_token(length=16)
        long   = generate_secure_token(length=64)
        assert len(long) > len(short)

    def test_each_call_returns_unique_token(self):
        tokens = {generate_secure_token() for _ in range(50)}
        assert len(tokens) == 50  # all 50 must be unique

    def test_token_contains_only_url_safe_characters(self):
        import re
        for _ in range(20):
            token = generate_secure_token()
            # URL-safe base64 uses A-Z a-z 0-9 - _
            assert re.fullmatch(r"[A-Za-z0-9_\-]+", token), f"Non-URL-safe chars in: {token}"

    def test_length_1_still_returns_non_empty_string(self):
        token = generate_secure_token(length=1)
        assert isinstance(token, str) and len(token) > 0

    def test_length_128_works(self):
        token = generate_secure_token(length=128)
        assert isinstance(token, str) and len(token) >= 128


# ══════════════════════════════════════════════════════════════════════════════
# hash_token
# ══════════════════════════════════════════════════════════════════════════════
class TestHashToken:

    def test_returns_string(self):
        assert isinstance(hash_token("abc"), str)

    def test_returns_64_character_hex_string(self):
        # SHA-256 produces 32 bytes = 64 hex chars
        result = hash_token("any-token")
        assert len(result) == 64

    def test_output_is_lowercase_hex(self):
        result = hash_token("any-token")
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic_same_input_same_output(self):
        token = "my-reset-token-value"
        assert hash_token(token) == hash_token(token)

    def test_different_inputs_produce_different_hashes(self):
        assert hash_token("token-a") != hash_token("token-b")

    def test_case_sensitive(self):
        assert hash_token("Token") != hash_token("token")

    def test_empty_string_produces_sha256_of_empty(self):
        expected = hashlib.sha256(b"").hexdigest()
        assert hash_token("") == expected

    def test_known_sha256_vector(self):
        # SHA-256("hello") is well-known
        expected = hashlib.sha256(b"hello").hexdigest()
        assert hash_token("hello") == expected

    def test_long_token_is_hashed_correctly(self):
        long_token = "x" * 10_000
        expected = hashlib.sha256(long_token.encode()).hexdigest()
        assert hash_token(long_token) == expected

    def test_unicode_token_hashes_correctly(self):
        token = "தமிழ்-reset-token"
        expected = hashlib.sha256(token.encode()).hexdigest()
        assert hash_token(token) == expected


# ══════════════════════════════════════════════════════════════════════════════
# verify_token_hash
# ══════════════════════════════════════════════════════════════════════════════
class TestVerifyTokenHash:

    def test_returns_true_for_matching_token_and_hash(self):
        token = "valid-token-abc"
        assert verify_token_hash(token, hash_token(token)) is True

    def test_returns_false_for_wrong_token(self):
        token = "valid-token-abc"
        assert verify_token_hash("wrong-token", hash_token(token)) is False

    def test_returns_false_for_tampered_hash(self):
        token = "valid-token-abc"
        good_hash = hash_token(token)
        tampered  = good_hash[:10] + "0000000000" + good_hash[20:]
        assert verify_token_hash(token, tampered) is False

    def test_returns_false_for_empty_token_against_real_hash(self):
        real_token = "real-token"
        assert verify_token_hash("", hash_token(real_token)) is False

    def test_returns_true_for_empty_string_token_when_hash_matches(self):
        assert verify_token_hash("", hash_token("")) is True

    def test_case_sensitive_token(self):
        token = "CaseSensitive"
        assert verify_token_hash("casesensitive", hash_token(token)) is False

    def test_whitespace_difference_returns_false(self):
        token = "my-token"
        assert verify_token_hash("my-token ", hash_token(token)) is False

    def test_consistent_with_hash_token(self):
        """verify_token_hash must be equivalent to hash_token(token) == token_hash."""
        token = generate_secure_token()
        h = hash_token(token)
        assert verify_token_hash(token, h) == (hash_token(token) == h)

    def test_returns_bool_type(self):
        token = "any-token"
        result = verify_token_hash(token, hash_token(token))
        assert isinstance(result, bool)