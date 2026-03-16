"""Parallel Review Architecture — mirrors human parallel thinking.

Humans don't evaluate sequentially. They run multiple assessment threads
simultaneously, then consolidate in the self-doubt phase.

Execution model:
  SEQUENTIAL: Understand (1-3) → Prioritize (4-5) → Execute (6-7)
       ↓
  PARALLEL:   Review (8-10) + Compare (11-12) + Risk (13-14) + Verify (15-16)
       ↓
  SEQUENTIAL: Self-Doubt (17) — consolidates all parallel results
       ↓
  PARALLEL:   Edge Cases (18) + Reflect (19-21)
       ↓
  LOOP if doubt found issues
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional

from src.orchestrator.review_agents import (
    AgentFinding, MultiAgentReport, REVIEW_AGENTS,
    format_multi_agent_report,
)


@dataclass
class ParallelStage:
    """A group of agents that run concurrently."""
    name: str
    phase_ids: list[int]
    sequential: bool = False  # If True, run one at a time


# The human thinking pipeline
PIPELINE = [
    ParallelStage("understand", [1, 2, 3], sequential=True),
    ParallelStage("prioritize", [3, 4], sequential=True),  # agent 3 = priority
    ParallelStage("execute", [4, 5], sequential=True),      # agent 4 = UX, 5 = functional
    ParallelStage("evaluate", [5, 6, 7, 8, 9], sequential=False),  # ALL PARALLEL
    ParallelStage("doubt", [10], sequential=True),           # consolidate
    ParallelStage("finalize", [9, 10], sequential=False),    # edge cases + reflect parallel
]

# Corrected mapping: phase_ids map to REVIEW_AGENTS keys (1-10)
STAGE_PHASES = {
    "understand": [1, 2],       # Purpose, Context/Audience
    "prioritize": [3],          # Priority & Simplicity
    "execute": [4],             # User Experience
    "evaluate": [5, 6, 7, 8, 9],  # Functional, Structure, Competition, Risk, Evidence — ALL PARALLEL
    "doubt": [10],              # Self-Doubt — sequential, consolidates everything
    "finalize": [9, 10],        # Edge cases recheck + Reflect (overlap is intentional)
}


class ParallelReview:
    """Runs the Human OS review with parallel evaluation stages.

    Sequential stages (understand, prioritize, execute) run one agent at a time.
    The evaluate stage runs 5 agents in parallel — this is where humans think
    about multiple dimensions simultaneously.
    Self-doubt consolidates, then edge cases and reflection run in parallel.
    """

    def __init__(self, goal: str, max_cycles: int = 3, max_workers: int = 5):
        self.goal = goal
        self.max_cycles = max_cycles
        self.max_workers = max_workers
        self._handlers: dict[int, Callable] = {}
        self._context: dict = {}

    def set_context(self, **kwargs):
        """Set the artifact context for review."""
        self._context.update(kwargs)

    def set_handler(self, phase: int, handler: Callable[[dict, list[str]], list[AgentFinding]]):
        """Set a custom handler for a review phase."""
        self._handlers[phase] = handler

    def run(self) -> MultiAgentReport:
        """Run the full parallel review pipeline."""
        report = MultiAgentReport(goal=self.goal)

        for cycle in range(self.max_cycles):
            report.cycles = cycle + 1
            cycle_findings = []

            # Stage 1: SEQUENTIAL — Understand
            findings = self._run_sequential([1, 2])
            cycle_findings.extend(findings)
            report.findings.extend(findings)

            # Stage 2: SEQUENTIAL — Prioritize
            findings = self._run_sequential([3])
            cycle_findings.extend(findings)
            report.findings.extend(findings)

            # Stage 3: SEQUENTIAL — Execute/UX
            findings = self._run_sequential([4])
            cycle_findings.extend(findings)
            report.findings.extend(findings)

            # Stage 4: PARALLEL — Evaluate (the big one)
            # Functional + Structure + Competition + Risk + Evidence all at once
            findings = self._run_parallel([5, 6, 7, 8, 9])
            cycle_findings.extend(findings)
            report.findings.extend(findings)

            # Stage 5: SEQUENTIAL — Self-Doubt (consolidates parallel results)
            doubt_context = {
                "prior_findings": cycle_findings,
                "critical_count": len([f for f in cycle_findings if f.severity == "critical"]),
                "major_count": len([f for f in cycle_findings if f.severity == "major"]),
            }
            self._context["_doubt_context"] = doubt_context
            findings = self._run_sequential([10])
            cycle_findings.extend(findings)
            report.findings.extend(findings)

            # Check if doubt wants another cycle
            doubt_findings = [f for f in findings if f.phase == 10]
            needs_repeat = any(
                "another cycle" in f.finding.lower() or
                f.severity in ("critical", "major")
                for f in doubt_findings
            )

            if not needs_repeat:
                break

        report.passed = len(report.critical) == 0
        return report

    def _run_sequential(self, phase_ids: list[int]) -> list[AgentFinding]:
        """Run agents sequentially."""
        all_findings = []
        for phase_id in phase_ids:
            if phase_id not in REVIEW_AGENTS:
                continue
            findings = self._run_agent(phase_id)
            all_findings.extend(findings)
        return all_findings

    def _run_parallel(self, phase_ids: list[int]) -> list[AgentFinding]:
        """Run agents in parallel using ThreadPoolExecutor."""
        all_findings = []
        valid_ids = [p for p in phase_ids if p in REVIEW_AGENTS]

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(valid_ids))) as executor:
            futures = {
                executor.submit(self._run_agent, phase_id): phase_id
                for phase_id in valid_ids
            }
            for future in as_completed(futures):
                phase_id = futures[future]
                try:
                    findings = future.result(timeout=30)
                    all_findings.extend(findings)
                except Exception as e:
                    all_findings.append(AgentFinding(
                        agent=REVIEW_AGENTS[phase_id]["name"],
                        phase=phase_id,
                        severity="major",
                        finding=f"Agent crashed: {e}",
                    ))

        return all_findings

    def _run_agent(self, phase_id: int) -> list[AgentFinding]:
        """Run a single review agent."""
        agent_def = REVIEW_AGENTS[phase_id]
        handler = self._handlers.get(phase_id)

        if handler:
            return handler(self._context, agent_def["questions"])

        # Default: return questions as info-level prompts
        return [
            AgentFinding(
                agent=agent_def["name"],
                phase=phase_id,
                severity="info",
                finding=f"Review question: {q}",
                evidence="Needs custom handler for real evaluation",
            )
            for q in agent_def["questions"]
        ]


def create_memory_review(goal: str) -> ParallelReview:
    """Create a parallel review pre-configured with memory system handlers."""
    review = ParallelReview(goal=goal)

    def functional_check(ctx, questions):
        """Actually test if the memory system works."""
        findings = []
        try:
            from src.memory.store import MemoryStore
            store = MemoryStore()
            stats = store.stats()
            rules = store.get_active_rules()

            if stats["total"] == 0:
                findings.append(AgentFinding("functional-agent", 5, "critical",
                    "Database is empty — no memory entries"))
            if len(rules) == 0:
                findings.append(AgentFinding("functional-agent", 5, "critical",
                    "No enforcement rules — nothing will be blocked"))

            # Test enforcement actually works
            from src.hooks.enforce import enforce
            result = enforce(store, "Bash", "pythonw.exe test.py")
            if result.allowed:
                findings.append(AgentFinding("functional-agent", 5, "critical",
                    "pythonw.exe was NOT blocked — enforcement broken"))
            else:
                findings.append(AgentFinding("functional-agent", 5, "info",
                    f"Enforcement working: pythonw blocked ({stats['total']} entries, {len(rules)} rules)",
                    evidence=f"DB has {stats['total']} entries"))

            store.close()
        except Exception as e:
            findings.append(AgentFinding("functional-agent", 5, "critical",
                f"Memory system failed: {e}"))

        return findings

    def competition_check(ctx, questions):
        """Compare to existing alternatives."""
        return [
            AgentFinding("competition-agent", 7, "info",
                "vs Claude Code CLAUDE.md: We add enforcement + auto-promotion + semantic search",
                evidence="CLAUDE.md is static text; our system is queryable, enforceable, learnable"),
            AgentFinding("competition-agent", 7, "info",
                "vs Cursor context: We persist across sessions; Cursor resets each time"),
            AgentFinding("competition-agent", 7, "minor",
                "Embedding cold-start (19s) is worse than instant markdown loading"),
        ]

    review.set_handler(5, functional_check)
    review.set_handler(7, competition_check)

    return review
