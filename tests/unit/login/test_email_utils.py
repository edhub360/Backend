"""
tests/unit/login/test_email_utils.py
======================================
Unit tests for app/email_utils.py

Coverage:
  - send_reset_password_email
      - SMTP connection setup (host, port, starttls, login)
      - Email headers (subject, from, to)
      - Email body contains reset URL
      - Silently swallows SMTP exceptions (does NOT re-raise)
      - Logs on success and failure
"""

import pytest
import smtplib
from unittest.mock import MagicMock, patch, call
from login.app.email_utils import send_reset_password_email


TO_EMAIL  = "user@example.com"
RESET_URL = "http://localhost:3000/reset-password?token=abc123"


def _make_smtp_mock():
    """Returns a mock SMTP context manager instance."""
    smtp_instance = MagicMock()
    smtp_instance.__enter__ = MagicMock(return_value=smtp_instance)
    smtp_instance.__exit__ = MagicMock(return_value=False)
    return smtp_instance


# ══════════════════════════════════════════════════════════════════════════════
# Happy path — successful email send
# ══════════════════════════════════════════════════════════════════════════════
class TestSendResetPasswordEmailSuccess:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.smtp_mock = _make_smtp_mock()
        self.smtp_patcher = patch("smtplib.SMTP", return_value=self.smtp_mock)
        self.mock_smtp_cls = self.smtp_patcher.start()
        yield
        self.smtp_patcher.stop()

    def test_does_not_raise_on_success(self):
        send_reset_password_email(TO_EMAIL, RESET_URL)  # must not raise

    def test_smtp_opened_with_correct_host(self):
        from login.app.config import settings
        send_reset_password_email(TO_EMAIL, RESET_URL)
        args = self.mock_smtp_cls.call_args[0]
        assert args[0] == settings.smtp_host

    def test_smtp_opened_with_correct_port(self):
        from login.app.config import settings
        send_reset_password_email(TO_EMAIL, RESET_URL)
        args = self.mock_smtp_cls.call_args[0]
        assert args[1] == settings.smtp_port

    def test_starttls_called(self):
        send_reset_password_email(TO_EMAIL, RESET_URL)
        self.smtp_mock.starttls.assert_called_once()

    def test_login_called_with_credentials(self):
        from login.app.config import settings
        send_reset_password_email(TO_EMAIL, RESET_URL)
        self.smtp_mock.login.assert_called_once_with(
            settings.smtp_username, settings.smtp_password
        )

    def test_sendmail_called_once(self):
        send_reset_password_email(TO_EMAIL, RESET_URL)
        self.smtp_mock.sendmail.assert_called_once()

    def test_sendmail_recipient_is_to_email(self):
        send_reset_password_email(TO_EMAIL, RESET_URL)
        _, recipients, _ = self.smtp_mock.sendmail.call_args[0]
        assert TO_EMAIL in recipients

    def test_sendmail_from_is_configured_address(self):
        from login.app.config import settings
        send_reset_password_email(TO_EMAIL, RESET_URL)
        from_addr, _, _ = self.smtp_mock.sendmail.call_args[0]
        assert from_addr == settings.smtp_from_email

    def test_email_body_contains_reset_url(self):
        send_reset_password_email(TO_EMAIL, RESET_URL)
        _, _, message_str = self.smtp_mock.sendmail.call_args[0]
        assert RESET_URL in message_str

    def test_email_body_contains_password_reset_subject(self):
        send_reset_password_email(TO_EMAIL, RESET_URL)
        _, _, message_str = self.smtp_mock.sendmail.call_args[0]
        assert "Reset" in message_str or "reset" in message_str

    def test_email_body_contains_edhub360_brand(self):
        send_reset_password_email(TO_EMAIL, RESET_URL)
        _, _, message_str = self.smtp_mock.sendmail.call_args[0]
        assert "EdHub360" in message_str or "edhub" in message_str.lower()

    def test_email_to_header_matches_recipient(self):
        send_reset_password_email(TO_EMAIL, RESET_URL)
        _, _, message_str = self.smtp_mock.sendmail.call_args[0]
        assert TO_EMAIL in message_str

    def test_email_subject_set_correctly(self):
        send_reset_password_email(TO_EMAIL, RESET_URL)
        _, _, message_str = self.smtp_mock.sendmail.call_args[0]
        assert "Reset" in message_str

    def test_starttls_called_before_login(self):
        """Security: TLS must be established before credentials are sent."""
        call_order = []
        self.smtp_mock.starttls.side_effect = lambda: call_order.append("starttls")
        self.smtp_mock.login.side_effect = lambda *a: call_order.append("login")
        send_reset_password_email(TO_EMAIL, RESET_URL)
        assert call_order.index("starttls") < call_order.index("login")

    def test_login_called_before_sendmail(self):
        call_order = []
        self.smtp_mock.login.side_effect = lambda *a: call_order.append("login")
        self.smtp_mock.sendmail.side_effect = lambda *a: call_order.append("sendmail")
        send_reset_password_email(TO_EMAIL, RESET_URL)
        assert call_order.index("login") < call_order.index("sendmail")

    def test_success_logged(self):
        with patch("app.email_utils.logger") as mock_logger:
            send_reset_password_email(TO_EMAIL, RESET_URL)
        mock_logger.info.assert_called_once()
        assert TO_EMAIL in mock_logger.info.call_args[0][0]


# ══════════════════════════════════════════════════════════════════════════════
# Error handling — SMTP exceptions must be swallowed
# ══════════════════════════════════════════════════════════════════════════════
class TestSendResetPasswordEmailErrorHandling:

    def test_does_not_raise_when_smtp_connection_fails(self):
        with patch("smtplib.SMTP", side_effect=smtplib.SMTPConnectError(421, "Cannot connect")):
            send_reset_password_email(TO_EMAIL, RESET_URL)  # must not raise

    def test_does_not_raise_when_login_fails(self):
        smtp_mock = _make_smtp_mock()
        smtp_mock.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Bad credentials")
        with patch("smtplib.SMTP", return_value=smtp_mock):
            send_reset_password_email(TO_EMAIL, RESET_URL)  # must not raise

    def test_does_not_raise_when_sendmail_fails(self):
        smtp_mock = _make_smtp_mock()
        smtp_mock.sendmail.side_effect = smtplib.SMTPRecipientsRefused({TO_EMAIL: (550, b"User unknown")})
        with patch("smtplib.SMTP", return_value=smtp_mock):
            send_reset_password_email(TO_EMAIL, RESET_URL)  # must not raise

    def test_does_not_raise_on_generic_exception(self):
        with patch("smtplib.SMTP", side_effect=Exception("Network error")):
            send_reset_password_email(TO_EMAIL, RESET_URL)  # must not raise

    def test_error_logged_when_smtp_fails(self):
        with patch("smtplib.SMTP", side_effect=Exception("Network error")), \
             patch("app.email_utils.logger") as mock_logger:
            send_reset_password_email(TO_EMAIL, RESET_URL)
        mock_logger.error.assert_called_once()

    def test_error_log_contains_recipient_email(self):
        with patch("smtplib.SMTP", side_effect=Exception("fail")), \
             patch("app.email_utils.logger") as mock_logger:
            send_reset_password_email(TO_EMAIL, RESET_URL)
        assert TO_EMAIL in mock_logger.error.call_args[0][0]

    def test_returns_none_on_success(self):
        smtp_mock = _make_smtp_mock()
        with patch("smtplib.SMTP", return_value=smtp_mock):
            result = send_reset_password_email(TO_EMAIL, RESET_URL)
        assert result is None

    def test_returns_none_on_failure(self):
        with patch("smtplib.SMTP", side_effect=Exception("fail")):
            result = send_reset_password_email(TO_EMAIL, RESET_URL)
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════════════════════════════════
class TestSendResetPasswordEmailEdgeCases:

    def test_different_recipients_use_correct_to_address(self):
        smtp_mock = _make_smtp_mock()
        other_email = "another@example.com"
        with patch("smtplib.SMTP", return_value=smtp_mock):
            send_reset_password_email(other_email, RESET_URL)
        _, recipients, _ = smtp_mock.sendmail.call_args[0]
        assert other_email in recipients

    def test_reset_url_with_special_characters_sent_correctly(self):
        smtp_mock = _make_smtp_mock()
        special_url = "http://localhost:3000/reset?token=abc%2Fxyz%3D%3D"
        with patch("smtplib.SMTP", return_value=smtp_mock):
            send_reset_password_email(TO_EMAIL, special_url)
        _, _, message_str = smtp_mock.sendmail.call_args[0]
        assert special_url in message_str

    def test_long_reset_url_sent_without_truncation(self):
        smtp_mock = _make_smtp_mock()
        long_url = "http://localhost:3000/reset?token=" + "a" * 256
        with patch("smtplib.SMTP", return_value=smtp_mock):
            send_reset_password_email(TO_EMAIL, long_url)
        _, _, message_str = smtp_mock.sendmail.call_args[0]
        assert long_url in message_str