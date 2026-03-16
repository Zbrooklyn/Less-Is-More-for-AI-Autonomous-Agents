#!/usr/bin/env bash
# Pre-commit hook: scan staged files for potential secrets
# Install: cp scripts/scan-secrets.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

PATTERNS=(
    'sk-[a-zA-Z0-9]{20,}'          # OpenAI keys
    'AKIA[0-9A-Z]{16}'             # AWS access keys
    'ghp_[a-zA-Z0-9]{36}'          # GitHub personal tokens
    'gho_[a-zA-Z0-9]{36}'          # GitHub OAuth tokens
    'AIza[0-9A-Za-z\-_]{35}'       # Google API keys
    'xox[bpoas]-[0-9a-zA-Z]{10,}'  # Slack tokens
    'PRIVATE KEY-----'              # Private keys
    'password\s*=\s*["\x27][^"\x27]{8,}' # Hardcoded passwords
)

FOUND=0
for pattern in "${PATTERNS[@]}"; do
    matches=$(git diff --cached --diff-filter=d -U0 | grep -E "^\+" | grep -v "^+++" | grep -iE "$pattern" 2>/dev/null)
    if [ -n "$matches" ]; then
        echo "SECRET DETECTED: Pattern '$pattern' found in staged changes:" >&2
        echo "$matches" >&2
        FOUND=1
    fi
done

if [ $FOUND -eq 1 ]; then
    echo "" >&2
    echo "Commit blocked: potential secrets detected in staged files." >&2
    echo "If this is a false positive, use: git commit --no-verify" >&2
    exit 1
fi

exit 0
