"""Multi-Agent Review Architecture — Each cognitive phase is a specialized agent.

The supervisor runs the Human Operating System loop. Each phase is a worker
agent with domain-specific review questions. Self-doubt agent (#8) decides
whether to trigger another cycle.

Usage:
    review = MultiAgentReview(goal="Build a memory system")
    review.set_artifact(code_path="src/memory/", test_path="tests/")
    report = review.run()
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from src.orchestrator.context import SharedContext
from src.orchestrator.worker import Worker, WorkerTask
from src.orchestrator.supervisor import Supervisor


@dataclass
class AgentFinding:
    """A finding from a review agent."""
    agent: str
    phase: int
    severity: str  # "critical", "major", "minor", "info"
    finding: str
    evidence: str = ""


@dataclass
class MultiAgentReport:
    """Combined report from all review agents."""
    goal: str
    findings: list[AgentFinding] = field(default_factory=list)
    cycles: int = 0
    passed: bool = False

    @property
    def critical(self) -> list[AgentFinding]:
        return [f for f in self.findings if f.severity == "critical"]

    @property
    def by_phase(self) -> dict[int, list[AgentFinding]]:
        result = {}
        for f in self.findings:
            result.setdefault(f.phase, []).append(f)
        return result


# Phase definitions with agent names and review questions
REVIEW_AGENTS = {
    1: {
        "name": "purpose-agent",
        "title": "Purpose & Goal Alignment",
        "questions": [
            "What is the actual goal?",
            "Is the solution aligned with the original intent?",
            "Is anything included that does not serve the goal?",
            "Is anything critical missing?",
        ],
    },
    2: {
        "name": "context-agent",
        "title": "Context & Audience",
        "questions": [
            "Where will this be used?",
            "Does this match the environment's standards?",
            "Who is the audience and what do they expect?",
        ],
    },
    3: {
        "name": "priority-agent",
        "title": "Priority & Simplicity",
        "questions": [
            "What is the most important part?",
            "Is there a simpler approach?",
            "Does the effort justify the value?",
        ],
    },
    4: {
        "name": "ux-agent",
        "title": "User Experience",
        "questions": [
            "What would a user notice first?",
            "Where would they get confused?",
            "Does it feel trustworthy and professional?",
        ],
    },
    5: {
        "name": "functional-agent",
        "title": "Functional Reality",
        "questions": [
            "Does it actually work when you run it?",
            "What happens if something goes wrong?",
            "Can it be broken deliberately?",
        ],
    },
    6: {
        "name": "structure-agent",
        "title": "Structure & Completeness",
        "questions": [
            "Is the structure clear and balanced?",
            "Is anything missing or unfinished?",
            "Are edge cases handled?",
        ],
    },
    7: {
        "name": "competition-agent",
        "title": "Competitive Analysis",
        "questions": [
            "What do alternatives do better?",
            "Does this meet modern standards?",
            "Would a user switch to something else?",
        ],
    },
    8: {
        "name": "risk-agent",
        "title": "Risk & Sustainability",
        "questions": [
            "What goes wrong after launch?",
            "What will users complain about?",
            "Is this maintainable long-term?",
        ],
    },
    9: {
        "name": "evidence-agent",
        "title": "Evidence & Verification",
        "questions": [
            "Was this tested or assumed?",
            "What evidence supports this working?",
            "Are we repeating a known mistake?",
        ],
    },
    10: {
        "name": "doubt-agent",
        "title": "Self-Doubt Audit",
        "questions": [
            "What did we miss?",
            "What assumptions are we making?",
            "What would a stricter reviewer find?",
            "What part of this makes us uneasy?",
            "Should we run another cycle?",
        ],
    },
}


class MultiAgentReview:
    """Orchestrates multiple specialized review agents through the Human OS loop."""

    def __init__(self, goal: str, max_cycles: int = 3, db_path=None):
        self.goal = goal
        self.max_cycles = max_cycles
        self._handlers: dict[int, Callable] = {}
        self._artifact_context: dict = {}
        self._db_path = db_path

    def set_artifact(self, **kwargs):
        """Set the artifact being reviewed (code paths, URLs, files, etc.)."""
        self._artifact_context.update(kwargs)

    def set_handler(self, phase: int, handler: Callable[[dict, list[str]], list[AgentFinding]]):
        """Set a custom handler for a phase.

        handler receives (artifact_context, questions) and returns findings.
        """
        self._handlers[phase] = handler

    def run(self) -> MultiAgentReport:
        """Run the full multi-agent review loop."""
        import tempfile
        from pathlib import Path

        tmp = tempfile.mkdtemp()
        ctx = SharedContext(Path(tmp) / "review.db")
        report = MultiAgentReport(goal=self.goal)

        for cycle in range(self.max_cycles):
            report.cycles = cycle + 1
            cycle_findings = []

            for phase_num, agent_def in sorted(REVIEW_AGENTS.items()):
                handler = self._handlers.get(phase_num)

                if handler:
                    findings = handler(self._artifact_context, agent_def["questions"])
                else:
                    findings = self._default_handler(phase_num, agent_def)

                cycle_findings.extend(findings)
                report.findings.extend(findings)

                # Log to shared context
                ctx.set(
                    f"cycle:{cycle}:phase:{phase_num}:findings",
                    str(len(findings)),
                    owner=agent_def["name"],
                )

            # Check if doubt-agent wants another cycle
            doubt_findings = [f for f in cycle_findings if f.phase == 10]
            needs_repeat = any("another cycle" in f.finding.lower() or
                              f.severity in ("critical", "major")
                              for f in doubt_findings)

            if not needs_repeat:
                break

        ctx.close()

        # Determine pass/fail
        report.passed = len(report.critical) == 0

        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass

        return report

    def _default_handler(self, phase: int, agent_def: dict) -> list[AgentFinding]:
        """Default handler that returns the questions as info-level findings."""
        return [
            AgentFinding(
                agent=agent_def["name"],
                phase=phase,
                severity="info",
                finding=f"Review question: {q}",
                evidence="No custom handler — manual review needed",
            )
            for q in agent_def["questions"]
        ]


def format_multi_agent_report(report: MultiAgentReport) -> str:
    """Format a multi-agent review report."""
    lines = [
        f"## Multi-Agent Review: {report.goal}",
        f"Cycles: {report.cycles} | Passed: {report.passed}",
        f"Findings: {len(report.findings)} ({len(report.critical)} critical)",
        "",
    ]

    for phase_num, findings in sorted(report.by_phase.items()):
        agent_name = REVIEW_AGENTS.get(phase_num, {}).get("title", f"Phase {phase_num}")
        lines.append(f"### Phase {phase_num}: {agent_name}")
        for f in findings:
            icon = {"critical": "!!!", "major": "!!", "minor": "!", "info": "."}[f.severity]
            lines.append(f"  [{icon}] {f.finding}")
            if f.evidence and f.evidence != "No custom handler — manual review needed":
                lines.append(f"       Evidence: {f.evidence}")
        lines.append("")

    return "\n".join(lines)
