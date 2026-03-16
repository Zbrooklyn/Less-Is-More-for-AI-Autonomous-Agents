"""Tests for credential broker, scanner, and CLI."""

from unittest.mock import MagicMock, patch

import keyring.errors
import pytest

from src.credentials import broker
from src.credentials.cli import main
from src.credentials.scanner import redact, scan_output


# ---------------------------------------------------------------------------
# Broker tests — keyring roundtrip with mocked backend
# ---------------------------------------------------------------------------

class TestBrokerServiceName:
    """Test the service name construction."""

    def test_global_scope(self):
        assert broker._service_name("openai") == "autonomous-agent/global/openai"

    def test_explicit_scope(self):
        assert broker._service_name("openai", "myproject") == "autonomous-agent/myproject/openai"

    def test_none_scope_is_global(self):
        assert broker._service_name("github", None) == "autonomous-agent/global/github"


class TestBrokerGet:
    """Test credential retrieval."""

    @patch("src.credentials.broker.keyring")
    def test_get_existing(self, mock_kr):
        mock_kr.get_password.return_value = "sk-test-key-123"
        result = broker.get("openai")
        mock_kr.get_password.assert_called_once_with(
            "autonomous-agent/global/openai",
            "autonomous-agent/global/openai",
        )
        assert result == "sk-test-key-123"

    @patch("src.credentials.broker.keyring")
    def test_get_nonexistent(self, mock_kr):
        mock_kr.get_password.return_value = None
        result = broker.get("nonexistent")
        assert result is None

    @patch("src.credentials.broker.keyring")
    def test_get_scoped(self, mock_kr):
        mock_kr.get_password.return_value = "scoped-value"
        result = broker.get("openai", scope="whisperclick")
        mock_kr.get_password.assert_called_once_with(
            "autonomous-agent/whisperclick/openai",
            "autonomous-agent/whisperclick/openai",
        )
        assert result == "scoped-value"


class TestBrokerSet:
    """Test credential storage."""

    @patch("src.credentials.broker.keyring")
    def test_set_global(self, mock_kr):
        broker.set("openai", "my-api-key")
        mock_kr.set_password.assert_called_once_with(
            "autonomous-agent/global/openai",
            "autonomous-agent/global/openai",
            "my-api-key",
        )

    @patch("src.credentials.broker.keyring")
    def test_set_scoped(self, mock_kr):
        broker.set("github", "ghp_token123", scope="myproject")
        mock_kr.set_password.assert_called_once_with(
            "autonomous-agent/myproject/github",
            "autonomous-agent/myproject/github",
            "ghp_token123",
        )


class TestBrokerDelete:
    """Test credential deletion."""

    @patch("src.credentials.broker.keyring")
    def test_delete_existing(self, mock_kr):
        result = broker.delete("openai")
        mock_kr.delete_password.assert_called_once()
        assert result is True

    @patch("src.credentials.broker.keyring")
    def test_delete_nonexistent(self, mock_kr):
        mock_kr.delete_password.side_effect = keyring.errors.PasswordDeleteError()
        result = broker.delete("nonexistent")
        assert result is False


class TestBrokerRoundtrip:
    """Integration-style roundtrip: set -> get -> delete."""

    @patch("src.credentials.broker.keyring")
    def test_roundtrip(self, mock_kr):
        store = {}

        def fake_set(service, username, password):
            store[(service, username)] = password

        def fake_get(service, username):
            return store.get((service, username))

        def fake_delete(service, username):
            if (service, username) in store:
                del store[(service, username)]
            else:
                raise keyring.errors.PasswordDeleteError()

        mock_kr.set_password.side_effect = fake_set
        mock_kr.get_password.side_effect = fake_get
        mock_kr.delete_password.side_effect = fake_delete

        # Set
        broker.set("openai", "sk-test123")
        # Get
        assert broker.get("openai") == "sk-test123"
        # Delete
        assert broker.delete("openai") is True
        # Get after delete
        assert broker.get("openai") is None
        # Delete again
        assert broker.delete("openai") is False

    @patch("src.credentials.broker.keyring")
    def test_scoped_vs_global_isolation(self, mock_kr):
        store = {}

        def fake_set(service, username, password):
            store[(service, username)] = password

        def fake_get(service, username):
            return store.get((service, username))

        mock_kr.set_password.side_effect = fake_set
        mock_kr.get_password.side_effect = fake_get

        broker.set("openai", "global-key")
        broker.set("openai", "project-key", scope="whisperclick")

        assert broker.get("openai") == "global-key"
        assert broker.get("openai", scope="whisperclick") == "project-key"


class TestBrokerListServices:
    """Test listing stored services."""

    @patch("src.credentials.broker.keyring")
    def test_list_returns_list(self, mock_kr):
        # With a non-Windows backend, list_services returns empty list
        mock_kr.get_keyring.return_value = MagicMock(spec=[])
        result = broker.list_services()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Scanner tests — pattern detection
# ---------------------------------------------------------------------------

class TestScannerDetection:
    """Test that known secret patterns are detected."""

    def test_openai_key(self):
        text = "my key is sk-abc123def456ghi789jklmnop"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "OpenAI API Key" for f in findings)

    def test_google_api_key(self):
        text = "google key: AIzaSyB1234567890abcdefghijklmnopqrstuv"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "Google API Key" for f in findings)

    def test_slack_token(self):
        text = "token: xoxb-123456789-abcdefghij"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "Slack Token" for f in findings)

    def test_aws_access_key(self):
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "AWS Access Key" for f in findings)

    def test_github_token(self):
        text = "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "GitHub Token" for f in findings)

    def test_gitlab_token(self):
        text = "GITLAB_TOKEN=glpat-ABCDEFGHIJKLMNOPQRSTUVwx"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "GitLab Token" for f in findings)

    def test_stripe_key(self):
        text = "stripe_key: sk_live_ABCDEFghijklmnopqrstuv"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "Stripe Key" for f in findings)

    def test_private_key_block(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow...\n-----END RSA PRIVATE KEY-----"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "PEM Private Key" for f in findings)

    def test_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6Ik"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "Bearer Token" for f in findings)

    def test_generic_secret_assignment(self):
        text = "API_KEY=abcdefghijklmnop1234567890"
        findings = scan_output(text)
        assert len(findings) >= 1
        assert any(f["pattern"] == "Generic Secret Assignment" for f in findings)

    def test_multiple_secrets(self):
        text = "key1: sk-abc123def456ghi789jklmnop and key2: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn"
        findings = scan_output(text)
        assert len(findings) >= 2

    def test_severity_levels(self):
        text = "key: sk-abc123def456ghi789jklmnop"
        findings = scan_output(text)
        assert all(f["severity"] in ("critical", "high", "medium", "low") for f in findings)


class TestScannerNoFalsePositives:
    """Test that normal text is NOT flagged."""

    def test_normal_prose(self):
        text = "The quick brown fox jumps over the lazy dog."
        findings = scan_output(text)
        assert len(findings) == 0

    def test_short_strings(self):
        text = "key=abc123"
        findings = scan_output(text)
        assert len(findings) == 0

    def test_normal_code(self):
        text = """
def hello():
    print("Hello, World!")
    x = 42
    return x + 1
"""
        findings = scan_output(text)
        assert len(findings) == 0

    def test_url_not_flagged(self):
        text = "Visit https://example.com/page?id=12345"
        findings = scan_output(text)
        assert len(findings) == 0

    def test_uuid_not_flagged(self):
        text = "id: 550e8400-e29b-41d4-a716-446655440000"
        findings = scan_output(text)
        assert len(findings) == 0

    def test_normal_base64_short(self):
        # Short base64 should not trigger
        text = "data: SGVsbG8gV29ybGQ="
        findings = scan_output(text)
        assert len(findings) == 0


class TestScannerRedact:
    """Test redaction of detected secrets."""

    def test_redact_openai_key(self):
        text = "my key is sk-abc123def456ghi789jklmnop"
        result = redact(text)
        assert "sk-abc123" not in result
        assert "[REDACTED]" in result

    def test_redact_preserves_normal_text(self):
        text = "Hello, this is normal text."
        result = redact(text)
        assert result == text

    def test_redact_multiple_secrets(self):
        text = "openai: sk-abc123def456ghi789jklmnop github: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn"
        result = redact(text)
        assert result.count("[REDACTED]") >= 2
        assert "sk-abc123" not in result
        assert "ghp_ABCDEF" not in result

    def test_redact_keeps_surrounding_text(self):
        text = "before sk-abc123def456ghi789jklmnop after"
        result = redact(text)
        assert result.startswith("before ")
        assert result.endswith(" after")


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLIGet:
    """Test cred-cli get command."""

    @patch("src.credentials.broker.keyring")
    def test_get_found(self, mock_kr, capsys):
        mock_kr.get_password.return_value = "my-secret-value"
        result = main(["get", "openai"])
        out = capsys.readouterr().out
        assert "my-secret-value" in out
        assert result == 0

    @patch("src.credentials.broker.keyring")
    def test_get_not_found(self, mock_kr, capsys):
        mock_kr.get_password.return_value = None
        result = main(["get", "openai"])
        out = capsys.readouterr().out
        assert "No credential found" in out
        assert result == 1

    @patch("src.credentials.broker.keyring")
    def test_get_with_scope(self, mock_kr, capsys):
        mock_kr.get_password.return_value = "scoped-value"
        result = main(["get", "openai", "--scope", "myproject"])
        out = capsys.readouterr().out
        assert "scoped-value" in out
        mock_kr.get_password.assert_called_once_with(
            "autonomous-agent/myproject/openai",
            "autonomous-agent/myproject/openai",
        )


class TestCLISet:
    """Test cred-cli set command."""

    @patch("src.credentials.broker.keyring")
    def test_set_with_value(self, mock_kr, capsys):
        result = main(["set", "openai", "--value", "sk-test-key"])
        out = capsys.readouterr().out
        assert "Stored credential" in out
        assert result == 0
        mock_kr.set_password.assert_called_once()

    @patch("src.credentials.broker.keyring")
    def test_set_with_scope(self, mock_kr, capsys):
        result = main(["set", "github", "--scope", "myproject", "--value", "ghp_token"])
        out = capsys.readouterr().out
        assert "myproject" in out
        assert result == 0


class TestCLIDelete:
    """Test cred-cli delete command."""

    @patch("src.credentials.broker.keyring")
    def test_delete_existing(self, mock_kr, capsys):
        result = main(["delete", "openai"])
        out = capsys.readouterr().out
        assert "Deleted credential" in out
        assert result == 0

    @patch("src.credentials.broker.keyring")
    def test_delete_nonexistent(self, mock_kr, capsys):
        mock_kr.delete_password.side_effect = keyring.errors.PasswordDeleteError()
        result = main(["delete", "nonexistent"])
        out = capsys.readouterr().out
        assert "No credential found" in out
        assert result == 1


class TestCLIList:
    """Test cred-cli list command."""

    @patch("src.credentials.broker.keyring")
    def test_list_empty(self, mock_kr, capsys):
        mock_kr.get_keyring.return_value = MagicMock(spec=[])
        result = main(["list"])
        out = capsys.readouterr().out
        assert "No credentials" in out or "Stored credentials" in out
        assert result == 0


class TestCLIScan:
    """Test cred-cli scan command."""

    def test_scan_detects_secret(self, capsys):
        result = main(["scan", "my", "key", "is", "sk-abc123def456ghi789jklmnop"])
        out = capsys.readouterr().out
        assert "OpenAI API Key" in out
        assert result == 1  # non-zero = secrets found

    def test_scan_clean_text(self, capsys):
        result = main(["scan", "hello", "world", "this", "is", "normal"])
        out = capsys.readouterr().out
        assert "No secrets detected" in out
        assert result == 0

    def test_scan_file(self, tmp_path, capsys):
        secret_file = tmp_path / "secrets.txt"
        secret_file.write_text("my key is sk-abc123def456ghi789jklmnop", encoding="utf-8")
        result = main(["scan", "--file", str(secret_file)])
        out = capsys.readouterr().out
        assert "OpenAI API Key" in out
        assert result == 1

    def test_scan_file_not_found(self, capsys):
        result = main(["scan", "--file", "/nonexistent/path.txt"])
        err = capsys.readouterr().err
        assert "File not found" in err
        assert result == 1


class TestCLIRedact:
    """Test cred-cli redact command."""

    def test_redact_text(self, capsys):
        result = main(["redact", "key:", "sk-abc123def456ghi789jklmnop"])
        out = capsys.readouterr().out
        assert "[REDACTED]" in out
        assert "sk-abc123" not in out
        assert result == 0

    def test_redact_clean_text(self, capsys):
        result = main(["redact", "hello", "world"])
        out = capsys.readouterr().out
        assert "hello world" in out
        assert result == 0

    def test_redact_file(self, tmp_path, capsys):
        f = tmp_path / "data.txt"
        f.write_text("token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn", encoding="utf-8")
        result = main(["redact", "--file", str(f)])
        out = capsys.readouterr().out
        assert "[REDACTED]" in out
        assert "ghp_" not in out
        assert result == 0


class TestCLIHelp:
    """Test help output."""

    def test_no_command_shows_help(self, capsys):
        result = main([])
        out = capsys.readouterr().out
        assert "cred-cli" in out or "usage" in out.lower()
        assert result == 1
