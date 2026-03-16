"""Human Review Loops — 8-mode cognitive review cycle.

Replicates the internal review loops humans run subconsciously.
Forces the agent through 8 distinct thinking modes before claiming done.

Usage:
    reviewer = HumanReviewLoop()
    reviewer.set_goal("Build a memory system that persists corrections between sessions")
    reviewer.add_mode("goal", lambda: check_goal_alignment())
    reviewer.add_mode("user", lambda: simulate_user_experience())
    reviewer.add_mode("break", lambda: try_to_break_it())
    reviewer.add_mode("structure", lambda: check_structural_balance())
    reviewer.add_mode("completeness", lambda: check_nothing_missing())
    reviewer.add_mode("competition", lambda: compare_to_alternatives())
    reviewer.add_mode("risk", lambda: predict_future_problems())
    reviewer.add_mode("doubt", lambda: what_did_i_miss())
    report = reviewer.run()
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


# The 8 cognitive modes and their default questions
MODE_QUESTIONS = {
    "goal": [
        "What is the actual goal?",
        "Is the solution aligned with the original intent?",
        "Is anything included that does not serve the goal?",
        "Is anything missing that is required for the goal?",
    ],
    "user": [
        "If I were the user, what would I notice first?",
        "Would anything confuse me?",
        "What friction would I encounter?",
        "Does the experience feel trustworthy and professional?",
    ],
    "break": [
        "How could this fail?",
        "What is the weakest part of this system?",
        "What assumptions might be wrong?",
        "What happens if inputs are incorrect or unexpected?",
    ],
    "structure": [
        "Does the structure make sense?",
        "Is the hierarchy clear?",
        "Is anything off, uneven, or misplaced?",
    ],
    "completeness": [
        "Are there missing components?",
        "Are there unfinished sections or placeholders?",
        "Is the experience complete from start to finish?",
        "Are edge cases handled?",
    ],
    "competition": [
        "What do alternatives do better?",
        "Does this meet modern standards?",
        "Would a user switch to something else?",
    ],
    "risk": [
        "What will go wrong after launch?",
        "What will users complain about?",
        "What misunderstandings will happen?",
    ],
    "doubt": [
        "What did I miss?",
        "What assumptions am I making?",
        "What did I not verify?",
        "What would a stricter reviewer criticize?",
        "What part of this makes me uneasy?",
    ],
}


@dataclass
class ModeResult:
    """Result of running one cognitive mode."""
    mode: str
    passed: bool
    findings: list[str] = field(default_factory=list)
    evidence: str = ""


@dataclass
class ReviewReport:
    """Complete review across all 8 modes."""
    goal: str = ""
    modes: list[ModeResult] = field(default_factory=list)
    cycles: int = 0
    overall_pass: bool = False
    summary: str = ""

    @property
    def failed_modes(self) -> list[ModeResult]:
        return [m for m in self.modes if not m.passed]

    @property
    def all_findings(self) -> list[str]:
        findings = []
        for m in self.modes:
            for f in m.findings:
                findings.append(f"[{m.mode}] {f}")
        return findings


class HumanReviewLoop:
    """8-mode cognitive review cycle that mirrors human review patterns.

    Modes run in order: goal → user → break → structure → completeness →
    competition → risk → doubt. If doubt finds issues, the cycle repeats.
    """

    def __init__(self, max_cycles: int = 3):
        self._goal = ""
        self._checks: dict[str, Callable[[], ModeResult]] = {}
        self._max_cycles = max_cycles

    def set_goal(self, goal: str):
        """Set the goal/intent for this review."""
        self._goal = goal

    def add_mode(self, mode: str, check_fn: Callable[[], ModeResult]):
        """Register a check function for a cognitive mode."""
        self._checks[mode] = check_fn

    def run(self) -> ReviewReport:
        """Run the full review loop. Repeats if self-doubt finds issues."""
        report = ReviewReport(goal=self._goal)
        mode_order = ["goal", "user", "break", "structure", "completeness",
                       "competition", "risk", "doubt"]

        for cycle in range(self._max_cycles):
            report.cycles = cycle + 1
            cycle_clean = True

            for mode in mode_order:
                if mode not in self._checks:
                    continue

                try:
                    result = self._checks[mode]()
                    result.mode = mode
                    report.modes.append(result)

                    if not result.passed:
                        cycle_clean = False

                except Exception as e:
                    report.modes.append(ModeResult(
                        mode=mode,
                        passed=False,
                        findings=[f"Mode crashed: {e}"],
                        evidence=str(e),
                    ))
                    cycle_clean = False

            # If self-doubt found nothing, we're done
            doubt_results = [m for m in report.modes if m.mode == "doubt" and m.passed]
            if cycle_clean or (doubt_results and doubt_results[-1].passed):
                break

        report.overall_pass = all(m.passed for m in report.modes)

        if report.overall_pass:
            report.summary = f"All modes passed after {report.cycles} cycle(s)."
        else:
            failed = report.failed_modes
            report.summary = (
                f"{len(failed)} mode(s) found issues after {report.cycles} cycle(s): "
                + ", ".join(m.mode for m in failed)
            )

        return report


def format_review(report: ReviewReport) -> str:
    """Format a review report for display."""
    lines = [
        f"## Review Report: {report.goal}",
        f"Cycles: {report.cycles}",
        "",
    ]

    for m in report.modes:
        icon = "PASS" if m.passed else "FAIL"
        lines.append(f"  [{icon}] {m.mode}: {m.evidence}")
        for f in m.findings:
            lines.append(f"         - {f}")

    lines.append("")
    lines.append(f"Overall: {report.summary}")

    if report.all_findings:
        lines.append("")
        lines.append(f"Total findings: {len(report.all_findings)}")

    return "\n".join(lines)


def quick_review(
    goal: str,
    run_fn: Callable[[], str],
    break_fn: Optional[Callable[[], list[str]]] = None,
) -> ReviewReport:
    """Quick review with minimal setup — runs goal, functional, and doubt checks."""
    reviewer = HumanReviewLoop(max_cycles=2)
    reviewer.set_goal(goal)

    reviewer.add_mode("goal", lambda: ModeResult(
        mode="goal", passed=True, evidence=f"Goal: {goal}",
    ))

    def functional_check():
        try:
            evidence = run_fn()
            return ModeResult(mode="user", passed=True, evidence=evidence)
        except Exception as e:
            return ModeResult(mode="user", passed=False,
                              findings=[str(e)], evidence=f"Failed: {e}")

    reviewer.add_mode("user", functional_check)

    if break_fn:
        def break_check():
            issues = break_fn()
            return ModeResult(
                mode="break", passed=len(issues) == 0,
                findings=issues, evidence=f"{len(issues)} issues found",
            )
        reviewer.add_mode("break", break_check)

    reviewer.add_mode("doubt", lambda: ModeResult(
        mode="doubt", passed=True, evidence="Quick review — full doubt loop not configured",
    ))

    return reviewer.run()
