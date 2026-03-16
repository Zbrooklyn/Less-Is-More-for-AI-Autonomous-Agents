"""Output scanner — detect and redact leaked secrets in text."""

import re
from typing import TypedDict


class Finding(TypedDict):
    pattern: str
    match: str
    severity: str


# Each tuple: (pattern_name, regex, severity)
# Order matters — more specific patterns first to avoid shadowing.
_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # PEM private keys
    ("PEM Private Key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "critical"),

    # OpenAI API keys (sk-...)
    ("OpenAI API Key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "critical"),

    # Google API keys (AIza...)
    ("Google API Key", re.compile(r"\bAIza[A-Za-z0-9_-]{30,}"), "high"),

    # Slack tokens (xox[bpras]-...)
    ("Slack Token", re.compile(r"\bxox[bpras]-[A-Za-z0-9-]{10,}"), "high"),

    # AWS Access Key IDs (AKIA...)
    ("AWS Access Key", re.compile(r"\bAKIA[A-Z0-9]{16}\b"), "critical"),

    # AWS Secret Keys (40-char base64-ish after common assignment patterns)
    ("AWS Secret Key", re.compile(r"(?:aws_secret_access_key|AWS_SECRET)\s*[=:]\s*[A-Za-z0-9/+=]{40}"), "critical"),

    # GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_)
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}"), "high"),

    # GitLab tokens (glpat-)
    ("GitLab Token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"), "high"),

    # Stripe keys (sk_live_, sk_test_, pk_live_, pk_test_)
    ("Stripe Key", re.compile(r"\b[sp]k_(?:live|test)_[A-Za-z0-9]{20,}"), "high"),

    # Azure subscription keys
    ("Azure Key", re.compile(r"\b[a-f0-9]{32}\b(?=.*(?:Ocp-Apim|api[_-]?key))", re.IGNORECASE), "medium"),

    # Supabase service role keys (eyJ... JWT-like)
    ("JWT/Supabase Key", re.compile(r"\beyJ[A-Za-z0-9_-]{50,}\.[A-Za-z0-9_-]{50,}\.[A-Za-z0-9_-]{20,}"), "high"),

    # Generic "Bearer" tokens in headers
    ("Bearer Token", re.compile(r"Bearer\s+[A-Za-z0-9_\-./+=]{20,}"), "medium"),

    # Generic long hex strings that look like secrets (API_KEY=..., SECRET=..., TOKEN=...)
    ("Generic Secret Assignment", re.compile(
        r"(?:API_?KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL)\s*[=:]\s*['\"]?[A-Za-z0-9_\-./+=]{16,}",
        re.IGNORECASE,
    ), "medium"),

    # Long base64 strings (>40 chars) that look like keys — lower priority
    ("Suspicious Base64", re.compile(r"(?<![A-Za-z0-9_/+=])[A-Za-z0-9+/]{40,}={0,3}(?![A-Za-z0-9_/+=])"), "low"),
]


def scan_output(text: str) -> list[Finding]:
    """Scan text for patterns that look like API keys or secrets.

    Args:
        text: The text to scan (command output, log, etc.).

    Returns:
        List of findings, each with pattern name, matched text, and severity.
    """
    findings: list[Finding] = []
    seen: set[str] = set()  # deduplicate by matched text

    for name, regex, severity in _PATTERNS:
        for m in regex.finditer(text):
            matched = m.group(0)
            if matched not in seen:
                seen.add(matched)
                findings.append({
                    "pattern": name,
                    "match": matched,
                    "severity": severity,
                })

    return findings


def redact(text: str) -> str:
    """Replace detected secrets with [REDACTED].

    Args:
        text: The text to redact.

    Returns:
        Text with all detected secrets replaced by [REDACTED].
    """
    result = text
    findings = scan_output(text)

    # Sort by match length descending to replace longer matches first
    # (avoids partial replacements)
    findings.sort(key=lambda f: len(f["match"]), reverse=True)

    for finding in findings:
        result = result.replace(finding["match"], "[REDACTED]")

    return result
