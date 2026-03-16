"""Review Engine — Structured decision tree implementing the Human Operating System.

Forces the agent through all 10 phases / 21 categories. Each phase gates the next.
Self-doubt (phase 8) can trigger a repeat cycle.

Usage:
    engine = ReviewEngine(goal="Build a memory system that persists corrections")
    engine.phase_understand(purpose="...", audience="...", context="...")
    engine.phase_prioritize(priorities=["..."], simplification="...")
    engine.phase_execute(ux_findings=["..."], emotional="...")
    engine.phase_review(functional=True, structural=True, complete=True)
    engine.phase_compare(competitors=["..."], meets_standards=True)
    engine.phase_risk(risks=["..."], maintainable=True)
    engine.phase_verify(evidence=["..."], patterns=["..."])
    engine.phase_doubt(missed=["..."], uneasy="...")
    engine.phase_edge_cases(edges=["..."])
    engine.phase_reflect(went_well="...", went_wrong="...", lesson="...")
    report = engine.finalize()
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class PhaseResult:
    """Result of one review phase."""
    phase: int
    name: str
    status: str  # "pass", "fail", "warn", "skip"
    findings: list[str] = field(default_factory=list)
    evidence: str = ""
    blocking: bool = False  # If True, stops the pipeline


@dataclass
class ReviewResult:
    """Complete review across all phases."""
    goal: str
    phases: list[PhaseResult] = field(default_factory=list)
    cycles: int = 1
    passed: bool = False
    core_answer: str = ""  # Answer to "Is this the right thing...?"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def failures(self) -> list[PhaseResult]:
        return [p for p in self.phases if p.status == "fail"]

    @property
    def warnings(self) -> list[PhaseResult]:
        return [p for p in self.phases if p.status == "warn"]

    @property
    def all_findings(self) -> list[str]:
        findings = []
        for p in self.phases:
            for f in p.findings:
                findings.append(f"[P{p.phase} {p.name}] {f}")
        return findings


class ReviewEngine:
    """Structured decision tree implementing the Human Operating System.

    Each phase must be completed before the next. Self-doubt can trigger
    a repeat. The engine tracks evidence and findings across all phases.
    """

    PHASES = [
        (1, "understand"),
        (2, "prioritize"),
        (3, "execute"),
        (4, "review"),
        (5, "compare"),
        (6, "risk"),
        (7, "verify"),
        (8, "doubt"),
        (9, "edge_cases"),
        (10, "reflect"),
    ]

    def __init__(self, goal: str, max_cycles: int = 3):
        self.goal = goal
        self.max_cycles = max_cycles
        self._results: list[PhaseResult] = []
        self._current_phase = 0
        self._cycle = 1
        self._needs_repeat = False

    def _add_result(self, phase_num: int, name: str, status: str,
                    findings: list[str] = None, evidence: str = "",
                    blocking: bool = False):
        result = PhaseResult(
            phase=phase_num, name=name, status=status,
            findings=findings or [], evidence=evidence, blocking=blocking,
        )
        self._results.append(result)
        self._current_phase = phase_num
        return result

    # --- Phase 1: Understanding ---

    def phase_understand(
        self,
        purpose: str,
        audience: str,
        context: str = "",
        success_criteria: str = "",
        failure_criteria: str = "",
        unnecessary: list[str] = None,
        missing: list[str] = None,
    ) -> PhaseResult:
        """Phase 1: Purpose, Context, Audience understanding."""
        findings = []
        if not purpose:
            findings.append("No clear purpose defined")
        if not audience:
            findings.append("No target audience identified")
        if missing:
            findings.extend(f"Missing: {m}" for m in missing)
        if unnecessary:
            findings.extend(f"Unnecessary: {u}" for u in unnecessary)

        status = "fail" if findings else "pass"
        return self._add_result(1, "understand", status, findings,
                                evidence=f"Purpose: {purpose[:100]}, Audience: {audience[:50]}")

    # --- Phase 2: Prioritization ---

    def phase_prioritize(
        self,
        priorities: list[str],
        simplification: str = "",
        effort_justified: bool = True,
    ) -> PhaseResult:
        findings = []
        if not priorities:
            findings.append("No priorities identified")
        if not effort_justified:
            findings.append("Effort may not justify the value")
        if simplification:
            findings.append(f"Simpler approach available: {simplification}")

        status = "warn" if findings else "pass"
        return self._add_result(2, "prioritize", status, findings,
                                evidence=f"Top priority: {priorities[0] if priorities else 'none'}")

    # --- Phase 3: Execution ---

    def phase_execute(
        self,
        ux_findings: list[str] = None,
        emotional: str = "",
        feels_trustworthy: bool = True,
        feels_professional: bool = True,
    ) -> PhaseResult:
        findings = ux_findings or []
        if not feels_trustworthy:
            findings.append("Does not feel trustworthy")
        if not feels_professional:
            findings.append("Does not feel professional")

        status = "fail" if any("not" in f.lower() for f in findings) else "pass"
        return self._add_result(3, "execute", status, findings,
                                evidence=f"UX: {len(findings)} findings, Emotion: {emotional[:50]}")

    # --- Phase 4: Review ---

    def phase_review(
        self,
        functional: bool = True,
        functional_evidence: str = "",
        structural: bool = True,
        structural_findings: list[str] = None,
        complete: bool = True,
        missing_items: list[str] = None,
    ) -> PhaseResult:
        findings = structural_findings or []
        if not functional:
            findings.append(f"Not functional: {functional_evidence}")
        if not complete:
            findings.extend(f"Missing: {m}" for m in (missing_items or ["unspecified"]))

        status = "fail" if not functional or not complete else ("warn" if findings else "pass")
        blocking = not functional
        return self._add_result(4, "review", status, findings,
                                evidence=f"Functional: {functional}, Complete: {complete}",
                                blocking=blocking)

    # --- Phase 5: Compare ---

    def phase_compare(
        self,
        competitors: list[str] = None,
        better_than: list[str] = None,
        worse_than: list[str] = None,
        meets_standards: bool = True,
    ) -> PhaseResult:
        findings = []
        if worse_than:
            findings.extend(f"Competitor does better: {w}" for w in worse_than)
        if not meets_standards:
            findings.append("Does not meet modern standards")

        status = "warn" if findings else "pass"
        return self._add_result(5, "compare", status, findings,
                                evidence=f"vs {len(competitors or [])} competitors")

    # --- Phase 6: Risk ---

    def phase_risk(
        self,
        risks: list[str] = None,
        complaints: list[str] = None,
        maintainable: bool = True,
        tech_debt: list[str] = None,
    ) -> PhaseResult:
        findings = []
        if risks:
            findings.extend(f"Risk: {r}" for r in risks)
        if complaints:
            findings.extend(f"Users will complain: {c}" for c in complaints)
        if not maintainable:
            findings.append("Not maintainable long-term")
        if tech_debt:
            findings.extend(f"Tech debt: {t}" for t in tech_debt)

        status = "warn" if findings else "pass"
        return self._add_result(6, "risk", status, findings,
                                evidence=f"{len(findings)} risks identified")

    # --- Phase 7: Verify ---

    def phase_verify(
        self,
        evidence: list[str] = None,
        assumptions: list[str] = None,
        patterns: list[str] = None,
        uncertain: list[str] = None,
    ) -> PhaseResult:
        findings = []
        if assumptions:
            findings.extend(f"Assumption: {a}" for a in assumptions)
        if uncertain:
            findings.extend(f"Uncertain: {u}" for u in uncertain)
        if patterns:
            findings.extend(f"Known pattern: {p}" for p in patterns)

        status = "warn" if uncertain else "pass"
        return self._add_result(7, "verify", status, findings,
                                evidence=f"{len(evidence or [])} pieces of evidence")

    # --- Phase 8: Self-Doubt ---

    def phase_doubt(
        self,
        missed: list[str] = None,
        assumptions: list[str] = None,
        not_tested: list[str] = None,
        uneasy: str = "",
        needs_another_cycle: bool = False,
    ) -> PhaseResult:
        findings = []
        if missed:
            findings.extend(f"Missed: {m}" for m in missed)
        if assumptions:
            findings.extend(f"Untested assumption: {a}" for a in assumptions)
        if not_tested:
            findings.extend(f"Not tested: {t}" for t in not_tested)
        if uneasy:
            findings.append(f"Uneasy about: {uneasy}")

        self._needs_repeat = needs_another_cycle or len(findings) > 0
        status = "warn" if findings else "pass"
        return self._add_result(8, "doubt", status, findings,
                                evidence=f"Triggers repeat: {self._needs_repeat}")

    # --- Phase 9: Edge Cases ---

    def phase_edge_cases(
        self,
        edges: list[str] = None,
        unhandled: list[str] = None,
    ) -> PhaseResult:
        findings = []
        if unhandled:
            findings.extend(f"Unhandled edge case: {e}" for e in unhandled)

        status = "warn" if findings else "pass"
        return self._add_result(9, "edge_cases", status, findings,
                                evidence=f"Checked {len(edges or [])} edge cases")

    # --- Phase 10: Reflect ---

    def phase_reflect(
        self,
        went_well: str = "",
        went_wrong: str = "",
        lesson: str = "",
        change_next_time: str = "",
        higher_standards: bool = False,
    ) -> PhaseResult:
        findings = []
        if went_wrong:
            findings.append(f"Went wrong: {went_wrong}")
        if lesson:
            findings.append(f"Lesson: {lesson}")
        if change_next_time:
            findings.append(f"Change: {change_next_time}")
        if higher_standards:
            findings.append("Standards should be higher next time")

        return self._add_result(10, "reflect", "pass", findings,
                                evidence=f"Well: {went_well[:50]}")

    # --- Finalize ---

    def finalize(self) -> ReviewResult:
        """Finalize the review. Checks if all phases were completed."""
        completed_phases = {r.phase for r in self._results}
        required = {p[0] for p in self.PHASES}
        missing = required - completed_phases

        if missing:
            phase_names = {p[0]: p[1] for p in self.PHASES}
            for m in missing:
                self._add_result(m, phase_names.get(m, "unknown"), "skip",
                                 findings=[f"Phase {m} was skipped"],
                                 evidence="Not completed")

        all_passed = all(r.status in ("pass", "warn") for r in self._results)
        has_blockers = any(r.blocking for r in self._results)

        result = ReviewResult(
            goal=self.goal,
            phases=self._results,
            cycles=self._cycle,
            passed=all_passed and not has_blockers,
        )

        if result.passed:
            result.core_answer = (
                "Yes — this is the right thing, for the right people, "
                "in the right way, with identified risks managed."
            )
        else:
            failures = result.failures
            result.core_answer = (
                f"Not yet — {len(failures)} phase(s) failed: "
                + ", ".join(f.name for f in failures)
            )

        return result

    @property
    def should_repeat(self) -> bool:
        """Whether self-doubt triggered another cycle."""
        return self._needs_repeat and self._cycle < self.max_cycles


def format_review(result: ReviewResult) -> str:
    """Format a review result for display."""
    lines = [
        f"## Review: {result.goal}",
        f"Cycles: {result.cycles} | Passed: {result.passed}",
        "",
    ]

    for p in result.phases:
        icon = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "skip": "SKIP"}[p.status]
        lines.append(f"  [{icon}] Phase {p.phase} ({p.name}): {p.evidence}")
        for f in p.findings:
            lines.append(f"         - {f}")

    lines.append("")
    lines.append(f"Core Answer: {result.core_answer}")

    if result.all_findings:
        lines.append(f"\nTotal findings: {len(result.all_findings)}")

    return "\n".join(lines)
