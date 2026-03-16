"""Reasoning backend — calls LLM APIs for complex daemon decisions.

Provides a pluggable interface for the daemon loop to reason about events
that can't be handled by simple rules. Supports multiple backends.
"""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ReasoningResult:
    """Result of an LLM reasoning call."""
    decision: str        # The action to take
    confidence: float    # 0.0-1.0
    reasoning: str       # Explanation of why
    model: str           # Which model was used
    cost: float = 0.0    # Estimated cost in dollars


class ReasoningBackend:
    """Pluggable reasoning backend for the daemon.

    Register handlers for different complexity levels:
    - "local" — rule-based, no API calls (default)
    - "fast" — cheap/fast model (e.g., Haiku)
    - "smart" — capable model (e.g., Sonnet/Opus)

    The daemon selects the backend based on event priority and cost budget.
    """

    def __init__(self):
        self._backends: dict[str, Callable] = {
            "local": _local_reasoning,
        }

    def register(self, name: str, fn: Callable[[str, dict], ReasoningResult]):
        """Register a reasoning backend.

        fn receives (question: str, context: dict) and returns ReasoningResult.
        """
        self._backends[name] = fn

    def reason(
        self,
        question: str,
        context: dict,
        backend: str = "local",
    ) -> ReasoningResult:
        """Ask a reasoning backend to make a decision."""
        fn = self._backends.get(backend)
        if not fn:
            return ReasoningResult(
                decision="unknown",
                confidence=0.0,
                reasoning=f"Backend '{backend}' not registered",
                model="none",
            )

        return fn(question, context)

    @property
    def available_backends(self) -> list[str]:
        return list(self._backends.keys())


def _local_reasoning(question: str, context: dict) -> ReasoningResult:
    """Local rule-based reasoning — no API calls."""
    lower = question.lower()

    # Simple keyword-based decisions
    if any(kw in lower for kw in ["test", "check", "verify", "lint"]):
        return ReasoningResult(
            decision="run_tests",
            confidence=0.8,
            reasoning="Question involves testing/verification — run tests",
            model="local-rules",
        )

    if any(kw in lower for kw in ["deploy", "production", "release"]):
        return ReasoningResult(
            decision="alert_user",
            confidence=0.9,
            reasoning="Production-related — requires human approval",
            model="local-rules",
        )

    if any(kw in lower for kw in ["clean", "delete", "remove", "prune"]):
        return ReasoningResult(
            decision="propose",
            confidence=0.6,
            reasoning="Destructive action — propose and wait for approval",
            model="local-rules",
        )

    if any(kw in lower for kw in ["update", "fix", "patch", "format"]):
        return ReasoningResult(
            decision="execute",
            confidence=0.7,
            reasoning="Routine maintenance — safe to execute",
            model="local-rules",
        )

    return ReasoningResult(
        decision="propose",
        confidence=0.3,
        reasoning="Uncertain — defaulting to propose and wait",
        model="local-rules",
    )


def create_anthropic_backend(api_key: str, model: str = "claude-haiku-4-5-20251001") -> Callable:
    """Create an Anthropic API reasoning backend.

    Returns a callable that can be registered with ReasoningBackend.register().

    Usage:
        backend = ReasoningBackend()
        backend.register("fast", create_anthropic_backend(key, "claude-haiku-4-5-20251001"))
        backend.register("smart", create_anthropic_backend(key, "claude-sonnet-4-6"))
    """
    def _reason(question: str, context: dict) -> ReasoningResult:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            ctx_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            prompt = f"Context:\n{ctx_str}\n\nQuestion: {question}\n\nRespond with a JSON object: {{\"decision\": \"<action>\", \"confidence\": <0-1>, \"reasoning\": \"<why>\"}}"

            response = client.messages.create(
                model=model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )

            import json
            text = response.content[0].text
            data = json.loads(text)

            return ReasoningResult(
                decision=data.get("decision", "unknown"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                model=model,
                cost=0.01 if "haiku" in model else 0.05,
            )
        except ImportError:
            return ReasoningResult(
                decision="unknown",
                confidence=0.0,
                reasoning="anthropic SDK not installed: pip install anthropic",
                model="none",
            )
        except Exception as e:
            return ReasoningResult(
                decision="unknown",
                confidence=0.0,
                reasoning=f"API error: {e}",
                model=model,
            )

    return _reason
