# Credential and Secret Management

## Definition

A secure system for storing, retrieving, scoping, rotating, and auditing the credentials an AI agent uses to access external services. The agent never sees raw credentials — the system injects them into operations transparently, enforces least-privilege access per task, automatically rotates tokens, scans all output for accidental leaks, and logs every credential access with full context.

## Purpose

A fully autonomous agent interacts with external services constantly — GitHub, cloud providers, databases, email, Slack, CI/CD, payment processors. Every one of these requires credentials. Currently, those credentials live in `.env` files (plaintext on disk), environment variables (visible to any process), or get pasted into conversations (stored in logs and history).

The more capable the agent becomes — especially with daemon mode running 24/7 with standing access to services — the higher the stakes. An always-running agent with GitHub, AWS, Slack, and database access stored in plaintext `.env` files is a honey pot. Proper credential management is the difference between a powerful tool and a security disaster.

## Status: PRIMITIVE

`.env` files and environment variables are the standard. OS keychains (Windows Credential Manager, macOS Keychain, Linux secret-service) exist with proper encryption but no AI agent framework integrates with them. Enterprise tools (HashiCorp Vault, AWS Secrets Manager, 1Password CLI) exist but are designed for servers and CI/CD, not for an AI agent on a developer's laptop.

## Key Insight

The fundamental principle is **the AI should never see credentials**. It should say "push to GitHub" and the system handles authentication transparently — retrieving the encrypted token, decrypting in memory, injecting into the git command, and wiping from memory when done. This isn't just more secure; it eliminates entire categories of accidental leakage (logging credentials, including them in commit messages, exposing them in error output).

---

## What Exists Today

**Environment variables and plaintext.** When the AI needs an API key, it's either in a `.env` file, an environment variable, or the user pastes it into the conversation. None of these are secure:

- **`.env` files** — plaintext on disk. Anyone (or any process) with file access can read them. If the AI accidentally commits one to git, the key is leaked forever.
- **Environment variables** — visible to any process running as the same user. `printenv` dumps all of them. Better than a file but not actually secure.
- **Pasted into conversation** — now the key is in the conversation history, in API logs, potentially in training data. The worst option.
- **Hardcoded in source** — exists in codebases everywhere. The AI might even suggest it. Terrible practice.

**What kind-of exists:**
- **System keychains** (Windows Credential Manager, macOS Keychain, Linux secret-service) — proper encrypted storage, but no AI agent framework integrates with them natively
- **HashiCorp Vault, AWS Secrets Manager, 1Password CLI** — enterprise-grade secret management, but designed for servers and CI/CD, not for an AI agent on a developer's laptop
- **`git-crypt`, `sops`** — encrypt secrets in repos, but require manual setup and key management

## Why This Matters

A fully autonomous agent interacts with external services constantly:

| Service | What It Needs | What Happens If Leaked |
|---------|--------------|----------------------|
| GitHub | PAT or SSH key | Full access to all repos, ability to push malicious code |
| Cloud providers (AWS/GCP/Azure) | API keys / service account credentials | Bill runs up, data exposed, infrastructure compromised |
| Databases | Connection strings with passwords | All data exposed |
| Email/Slack/Discord | OAuth tokens or API keys | Can send messages as you, read all conversations |
| Payment processors (Stripe, etc.) | Secret keys | Financial access |
| CI/CD (GitHub Actions, etc.) | Tokens | Can modify build pipelines, inject code |
| Docker registries | Auth tokens | Push malicious images |

The more capable the agent becomes — especially with daemon mode — the more services it needs access to. And every additional credential is another thing that can be leaked, stolen, or misused.

The daemon scenario makes this critical: an always-running agent that has standing access to GitHub, AWS, Slack, and your database is an incredibly high-value target. If its credential storage is `.env` files, you've built a honey pot.

## The Six Capabilities

### 1. Encrypted at Rest, Decrypted on Demand

Secrets are stored encrypted. The AI never sees the raw credential until the moment it needs to use it, and it's decrypted in memory only for the duration of the API call. It's not stored in a variable, not logged, not cached.

```
AI: "I need to push to GitHub"
System: Retrieves encrypted PAT → decrypts in memory → injects into git command → wipes from memory
AI never sees the token. It just says "push" and the system handles auth.
```

### 2. Scoped Access

Not every task needs every credential. The AI gets access to only what it needs for the current task:

- Working on the frontend repo? GitHub access only, no AWS.
- Running database migrations? Database credentials, no email.
- Daemon monitoring logs? Read-only log access, no write credentials.

This is the principle of least privilege, applied to AI agents. If the agent is compromised or makes a mistake, the blast radius is limited to what it could access.

### 3. Automatic Rotation

Credentials expire and rotate automatically:
- Short-lived tokens (hours, not months) for routine operations
- Automatic renewal before expiration
- If a credential might be compromised (appeared in logs, used in a failed sandbox), automatically rotate it and invalidate the old one
- The AI never manages rotation manually — the system handles it

### 4. Audit Trail

Every credential access is logged:
```
[2026-02-26 14:22:01] CREDENTIAL ACCESS: github-pat
    Requested by: daemon (CI failure handler)
    Scope: repo:push (whisperclick-dev)
    Duration: 3.2 seconds
    Result: success (commit pushed)
    Credential wiped from memory: confirmed
```

If a credential is misused, the audit trail shows exactly when, by what process, for what purpose, and whether it was properly cleaned up.

### 5. User Approval for New Credentials

The first time the agent needs access to a new service:
- It requests access explicitly: "I need GitHub push access to fix this CI failure"
- The user approves and provides the credential through a secure channel (not pasted into chat)
- The credential is stored encrypted with a defined scope and expiration
- Future uses within that scope are automatic; expanded scope requires new approval

No credential is ever silently added. The user always knows what the agent can access.

### 6. Isolation Between Contexts

Credentials for different projects, environments, and purposes are strictly separated:
- Production credentials never leak into development sandboxes
- Client A's credentials are invisible when working on Client B
- Daemon credentials are separate from interactive session credentials
- A compromised sandbox can't access production secrets

## The Hard Problems

**1. Bootstrapping trust.** How does the AI get its first credential? Someone has to provide it, and that initial handoff is inherently vulnerable. The system needs a secure onboarding flow — ideally using the OS keychain or a hardware token, not copy-paste.

**2. Cross-platform storage.** Windows Credential Manager, macOS Keychain, and Linux secret-service all have different APIs. Building a unified abstraction that uses the right native secure storage on each platform is real engineering work.

**3. Daemon mode credentials.** An always-running agent needs standing credentials. But long-lived credentials are exactly what security best practices say to avoid. The tension between "the daemon needs to act at 3 AM without asking" and "credentials should be short-lived" requires careful architecture — probably a local credential broker that refreshes tokens automatically.

**4. Preventing accidental leakage.** The AI might inadvertently include a credential in a log message, a commit message, an error report, or a conversation response. The system needs output scanning that catches credentials before they reach any output channel. Think of it as a reverse firewall — not blocking incoming threats, but blocking outgoing secrets.

**5. Recovery from compromise.** When (not if) a credential is suspected compromised, the system needs to: immediately revoke it, rotate to a new one, audit what was accessed with the old one, and notify the user. All automatically, all within seconds.

## The Difference

| | Current State | Proper Credential Management |
|---|--------------|------------------------------|
| Storage | `.env` files, plaintext | Encrypted vault, OS-native secure storage |
| Access | AI sees raw credentials | AI never sees credentials — system injects them |
| Scope | All-or-nothing | Least privilege per task |
| Rotation | Manual, infrequent | Automatic, short-lived tokens |
| Leakage prevention | Honor system — "don't log the key" | Output scanning catches leaks before they happen |
| Compromise recovery | Manual panic | Automatic revocation, rotation, audit |
| Audit | None | Full access log with context |

## What Would Need to Be Built

1. **A credential vault** — encrypted local storage using OS-native secure storage (Credential Manager, Keychain, secret-service)
2. **A credential broker** — sits between the AI and external services, handles auth injection, token refresh, and scoping
3. **An output scanner** — monitors all AI output channels (terminal, files, logs, conversation) for accidental credential exposure
4. **A scope/policy engine** — defines which credentials are available for which tasks, enforced by the system, not the AI's judgment
5. **An audit logger** — records every credential access with full context
6. **A rotation manager** — automatically rotates credentials on schedule and on suspected compromise

## What It Covers

- Secure storage of API keys, tokens, SSH keys, and passwords
- Transparent auth injection into git, API calls, database connections, and service interactions
- Per-task credential scoping — only what's needed, nothing more
- Automatic token rotation and renewal
- Output scanning to catch accidental credential exposure before it reaches any output channel
- Compromise recovery — automatic revocation, rotation, audit on suspected breach
- Cross-project and cross-environment credential isolation
