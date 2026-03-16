"""Credential broker — secure credential storage via keyring (Windows Credential Manager)."""

import keyring
from keyring.errors import PasswordDeleteError

# Prefix for all credentials managed by this agent
_PREFIX = "autonomous-agent"


def _service_name(service: str, scope: str | None = None) -> str:
    """Build the namespaced service name: autonomous-agent/{scope}/{service}."""
    scope = scope or "global"
    return f"{_PREFIX}/{scope}/{service}"


def get(service: str, scope: str | None = None) -> str | None:
    """Retrieve a credential from the system keyring.

    Args:
        service: The service name (e.g., 'openai', 'github').
        scope: Optional project scope. Defaults to 'global'.

    Returns:
        The credential value, or None if not found.
    """
    name = _service_name(service, scope)
    return keyring.get_password(name, name)


def set(service: str, value: str, scope: str | None = None) -> None:
    """Store a credential in the system keyring.

    Args:
        service: The service name (e.g., 'openai', 'github').
        value: The credential value (API key, token, etc.).
        scope: Optional project scope. Defaults to 'global'.
    """
    name = _service_name(service, scope)
    keyring.set_password(name, name, value)


def delete(service: str, scope: str | None = None) -> bool:
    """Delete a credential from the system keyring.

    Args:
        service: The service name.
        scope: Optional project scope. Defaults to 'global'.

    Returns:
        True if deleted, False if not found.
    """
    name = _service_name(service, scope)
    try:
        keyring.delete_password(name, name)
        return True
    except PasswordDeleteError:
        return False


def list_services() -> list[str]:
    """List all stored service names.

    Uses the keyring backend's credential enumeration if available
    (Windows Credential Manager supports this). Returns display names
    like 'global/openai' stripped of the autonomous-agent/ prefix.
    """
    backend = keyring.get_keyring()

    # Windows Credential Manager and some backends support get_credential
    # but not enumeration. We use the WinVaultKeyring internal API if available.
    if hasattr(backend, "get_credential"):
        try:
            # Try the win32 enumeration approach
            import ctypes
            import ctypes.wintypes

            _CRED_TYPE_GENERIC = 1
            _CRED_ENUMERATE_ALL_CREDENTIALS = 1

            class CREDENTIAL(ctypes.Structure):
                _fields_ = [
                    ("Flags", ctypes.wintypes.DWORD),
                    ("Type", ctypes.wintypes.DWORD),
                    ("TargetName", ctypes.wintypes.LPWSTR),
                    ("Comment", ctypes.wintypes.LPWSTR),
                    ("LastWritten", ctypes.wintypes.FILETIME),
                    ("CredentialBlobSize", ctypes.wintypes.DWORD),
                    ("CredentialBlob", ctypes.POINTER(ctypes.c_char)),
                    ("Persist", ctypes.wintypes.DWORD),
                    ("AttributeCount", ctypes.wintypes.DWORD),
                    ("Attributes", ctypes.c_void_p),
                    ("TargetAlias", ctypes.wintypes.LPWSTR),
                    ("UserName", ctypes.wintypes.LPWSTR),
                ]

            advapi32 = ctypes.windll.advapi32
            count = ctypes.wintypes.DWORD()
            creds_ptr = ctypes.POINTER(ctypes.POINTER(CREDENTIAL))()

            prefix_filter = f"{_PREFIX}/*"
            if advapi32.CredEnumerateW(
                prefix_filter, 0, ctypes.byref(count), ctypes.byref(creds_ptr)
            ):
                services = []
                for i in range(count.value):
                    target = creds_ptr[i].contents.TargetName
                    if target and target.startswith(f"{_PREFIX}/"):
                        display = target[len(f"{_PREFIX}/"):]
                        services.append(display)
                advapi32.CredFree(creds_ptr)
                return sorted(services)
        except (OSError, ImportError, AttributeError):
            pass

    # Fallback: no enumeration available
    return []
