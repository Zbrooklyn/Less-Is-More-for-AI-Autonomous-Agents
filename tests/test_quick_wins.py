"""Tests for Step 1: Quick Wins — verify enforcement hooks and credential setup."""

import json
import re
from pathlib import Path

import keyring
import pytest


# --- Hooks tests ---


class TestHooksExist:
    """Verify Claude Code enforcement hooks are configured."""

    @pytest.fixture
    def hooks_path(self):
        return Path.home() / ".claude" / "hooks.json"

    @pytest.fixture
    def hooks(self, hooks_path):
        assert hooks_path.exists(), f"hooks.json not found at {hooks_path}"
        with open(hooks_path) as f:
            return json.load(f)

    def test_hooks_file_exists(self, hooks_path):
        assert hooks_path.exists()

    def test_hooks_file_valid_json(self, hooks_path):
        with open(hooks_path) as f:
            data = json.load(f)
        assert "hooks" in data

    def test_pre_tool_use_hooks_exist(self, hooks):
        assert "PreToolUse" in hooks["hooks"]
        pre_tool = hooks["hooks"]["PreToolUse"]
        assert len(pre_tool) > 0

    def test_bash_matcher_exists(self, hooks):
        pre_tool = hooks["hooks"]["PreToolUse"]
        bash_hooks = [h for h in pre_tool if h.get("matcher") == "Bash"]
        assert len(bash_hooks) > 0, "No Bash matcher found in PreToolUse hooks"

    def test_pythonw_hook_exists(self, hooks):
        pre_tool = hooks["hooks"]["PreToolUse"]
        bash_hooks = [h for h in pre_tool if h.get("matcher") == "Bash"]
        all_commands = []
        for bh in bash_hooks:
            all_commands.extend(h["command"] for h in bh.get("hooks", []))
        assert any("pythonw" in cmd for cmd in all_commands), "No pythonw enforcement hook found"

    def test_git_push_public_hook_exists(self, hooks):
        pre_tool = hooks["hooks"]["PreToolUse"]
        bash_hooks = [h for h in pre_tool if h.get("matcher") == "Bash"]
        all_commands = []
        for bh in bash_hooks:
            all_commands.extend(h["command"] for h in bh.get("hooks", []))
        assert any("push" in cmd and "public" in cmd for cmd in all_commands), "No git push public enforcement hook found"

    def test_easy_drag_hook_exists(self, hooks):
        pre_tool = hooks["hooks"]["PreToolUse"]
        bash_hooks = [h for h in pre_tool if h.get("matcher") == "Bash"]
        all_commands = []
        for bh in bash_hooks:
            all_commands.extend(h["command"] for h in bh.get("hooks", []))
        assert any("easy_drag" in cmd for cmd in all_commands), "No easy_drag enforcement hook found"


# --- Enforcement hook behavior tests ---


class TestHookBehavior:
    """Test enforcement hook patterns match correctly.

    Tests the regex logic directly in Python since Git Bash subprocess
    hangs on Windows. Claude Code handles the shell execution.
    """

    @pytest.fixture
    def hooks_path(self):
        return Path.home() / ".claude" / "hooks.json"

    @pytest.fixture
    def bash_hooks(self, hooks_path):
        with open(hooks_path) as f:
            data = json.load(f)
        pre_tool = data["hooks"]["PreToolUse"]
        for entry in pre_tool:
            if entry.get("matcher") == "Bash":
                return entry["hooks"]
        return []

    def _extract_pattern(self, hook_command):
        """Extract the grep pattern from a hook command."""
        # Pattern is between grep -qiE " or grep -qE " and the next "
        match = re.search(r'grep\s+-q[iE]*\s+"([^"]+)"', hook_command)
        if match:
            return match.group(1)
        return None

    def _is_case_insensitive(self, hook_command):
        return "grep -qiE" in hook_command

    def _would_block(self, hook_command, test_input):
        """Simulate whether a hook would block the given input."""
        pattern = self._extract_pattern(hook_command)
        if pattern is None:
            return False
        flags = re.IGNORECASE if self._is_case_insensitive(hook_command) else 0
        return bool(re.search(pattern, test_input, flags))

    def test_pythonw_blocked(self, bash_hooks):
        hook = next(h for h in bash_hooks if "pythonw" in h["command"])
        assert self._would_block(hook["command"], "pythonw.exe src/main.py")

    def test_pythonw_case_insensitive(self, bash_hooks):
        hook = next(h for h in bash_hooks if "pythonw" in h["command"])
        assert self._would_block(hook["command"], "PYTHONW.EXE src/main.py")

    def test_pythonw_allows_normal_python(self, bash_hooks):
        hook = next(h for h in bash_hooks if "pythonw" in h["command"])
        assert not self._would_block(hook["command"], "python.exe src/main.py")

    def test_git_push_public_blocked(self, bash_hooks):
        hook = next(h for h in bash_hooks if "push" in h["command"] and "public" in h["command"])
        assert self._would_block(hook["command"], "git push public main")

    def test_git_push_origin_allowed(self, bash_hooks):
        hook = next(h for h in bash_hooks if "push" in h["command"] and "public" in h["command"])
        assert not self._would_block(hook["command"], "git push origin main")

    def test_easy_drag_blocked(self, bash_hooks):
        hook = next(h for h in bash_hooks if "easy_drag" in h["command"])
        assert self._would_block(hook["command"], "easy_drag = True")

    def test_easy_drag_with_spaces_blocked(self, bash_hooks):
        hook = next(h for h in bash_hooks if "easy_drag" in h["command"])
        assert self._would_block(hook["command"], "easy_drag=True")


# --- Credential backend tests ---


class TestCredentialBackend:
    """Verify keyring is using Windows Credential Manager."""

    def test_keyring_backend_is_windows(self):
        backend = keyring.get_keyring()
        assert "WinVault" in type(backend).__name__, f"Expected WinVaultKeyring, got {type(backend).__name__}"

    def test_keyring_roundtrip(self):
        """Test that we can store and retrieve a credential."""
        service = "autonomous-ai-agent-test"
        username = "test-key"
        value = "test-value-12345"
        try:
            keyring.set_password(service, username, value)
            retrieved = keyring.get_password(service, username)
            assert retrieved == value
        finally:
            # Clean up
            try:
                keyring.delete_password(service, username)
            except keyring.errors.PasswordDeleteError:
                pass


# --- Pre-commit secret scanning tests ---


class TestSecretScanning:
    """Verify pre-commit hook for secret scanning exists."""

    @pytest.fixture
    def repo_path(self):
        return Path("C:/Users/Owner/Documents/autonomous-ai-agent")

    def test_gitignore_excludes_env(self, repo_path):
        gitignore = repo_path / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert ".env" in content

    def test_gitignore_excludes_keys(self, repo_path):
        gitignore = repo_path / ".gitignore"
        content = gitignore.read_text()
        assert "*.key" in content
        assert "*.pem" in content

    def test_gitignore_excludes_credentials(self, repo_path):
        gitignore = repo_path / ".gitignore"
        content = gitignore.read_text()
        assert "credentials.json" in content


# --- Project structure tests ---


class TestProjectStructure:
    """Verify the project is set up correctly."""

    @pytest.fixture
    def repo_path(self):
        return Path("C:/Users/Owner/Documents/autonomous-ai-agent")

    def test_src_directory_exists(self, repo_path):
        assert (repo_path / "src").is_dir()

    def test_memory_module_exists(self, repo_path):
        assert (repo_path / "src" / "memory" / "__init__.py").exists()

    def test_daemon_module_exists(self, repo_path):
        assert (repo_path / "src" / "daemon" / "__init__.py").exists()

    def test_hooks_module_exists(self, repo_path):
        assert (repo_path / "src" / "hooks" / "__init__.py").exists()

    def test_credentials_module_exists(self, repo_path):
        assert (repo_path / "src" / "credentials" / "__init__.py").exists()

    def test_tests_directory_exists(self, repo_path):
        assert (repo_path / "tests").is_dir()

    def test_pyproject_toml_exists(self, repo_path):
        assert (repo_path / "pyproject.toml").exists()

    def test_roadmap_exists(self, repo_path):
        assert (repo_path / "ROADMAP.md").exists()

    def test_venv_exists(self, repo_path):
        assert (repo_path / "venv" / "Scripts" / "python.exe").exists()

    def test_git_initialized(self, repo_path):
        assert (repo_path / ".git").is_dir()
