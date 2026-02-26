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

## The Six Capabilities

1. **Encrypted at rest, decrypted on demand** — credentials stored encrypted, decrypted in memory only for the duration of use, never cached or logged
2. **Scoped access** — each task gets only the credentials it needs (least privilege), limiting blast radius if compromised
3. **Automatic rotation** — short-lived tokens, automatic renewal, immediate rotation on suspected compromise
4. **Audit trail** — every credential access logged with who requested it, for what purpose, how long it was used, and whether it was properly cleaned up
5. **User approval for new credentials** — first access to a new service requires explicit approval through a secure channel, future uses within scope are automatic
6. **Isolation between contexts** — production credentials never leak into dev sandboxes, Client A's credentials invisible when working on Client B

## What It Covers

- Secure storage of API keys, tokens, SSH keys, and passwords
- Transparent auth injection into git, API calls, database connections, and service interactions
- Per-task credential scoping — only what's needed, nothing more
- Automatic token rotation and renewal
- Output scanning to catch accidental credential exposure before it reaches any output channel
- Compromise recovery — automatic revocation, rotation, audit on suspected breach
- Cross-project and cross-environment credential isolation
