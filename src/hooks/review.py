"""Human Operating System Review — THE canonical review module.

Single source of truth for the 21-category cognitive framework.
Supports sequential and parallel execution.

Usage:
    # Quick sequential review
    review = Review("Is the memory system working?")
    review.check("goal", passed=True, evidence="Aligned with user needs")
    review.check("functional", passed=True, evidence="508 tests pass")
    review.check("doubt", passed=False, findings=["Threading not tested"])
    report = review.finalize()

    # Full parallel review (evaluation phases run concurrently)
    review = Review("Full project review", parallel=True)
    review.set_handler("functional", my_functional_test)
    report = review.run()
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional


# ============================================================
# SINGLE SOURCE OF TRUTH: The 21 categories
# ============================================================

CATEGORIES = {
    # Phase 1: Understanding
    "purpose": {
        "phase": 1, "name": "Purpose & Goal Alignment",
        "questions": [
            "What problem is being solved?",
            "What is the objective?",
            "Who is this for?",
            "What outcome defines success?",
            "What outcome defines failure?",
            "Are we solving the correct problem?",
            "Is anything here unnecessary?",
            "Is anything critical missing?",
        ],
    },
    "context": {
        "phase": 1, "name": "Context & Environmental Fit",
        "questions": [
            "Where will this be used?",
            "What expectations exist in this space?",
            "Does this match the tone and standards of its environment?",
            "Does this align with the brand or identity it represents?",
            "Does anything feel out of place?",
        ],
    },
    "audience": {
        "phase": 1, "name": "Audience Understanding",
        "questions": [
            "Who is the intended audience?",
            "What are their expectations?",
            "What knowledge do they already have?",
            "What assumptions will they make?",
            "What might they misunderstand?",
        ],
    },
    # Phase 2: Prioritization
    "priority": {
        "phase": 2, "name": "Priority Assessment",
        "questions": [
            "What is the most important part of this?",
            "What is urgent versus important?",
            "What creates the biggest impact?",
            "What risk deserves the most attention?",
        ],
    },
    "simplicity": {
        "phase": 2, "name": "Effort vs Value Judgment",
        "questions": [
            "Is this solution overly complicated?",
            "Is there a simpler approach?",
            "Are we adding complexity without value?",
            "Does the result justify the effort?",
        ],
    },
    # Phase 3: Execution
    "ux": {
        "phase": 3, "name": "User Experience Simulation",
        "questions": [
            "What will the user notice first?",
            "Would they understand what to do?",
            "Where might they get confused?",
            "What would frustrate them?",
            "What feels smooth versus awkward?",
        ],
    },
    "emotion": {
        "phase": 3, "name": "Emotional & Psychological Response",
        "questions": [
            "Does this feel trustworthy?",
            "Does this feel professional?",
            "Does this feel satisfying?",
            "Does this create hesitation or confidence?",
        ],
    },
    # Phase 4: Review
    "functional": {
        "phase": 4, "name": "Functional Reality",
        "questions": [
            "Does the system function correctly?",
            "What happens if something goes wrong?",
            "What assumptions are being made?",
            "Can this be broken deliberately?",
        ],
    },
    "structure": {
        "phase": 4, "name": "Structural & Visual Quality",
        "questions": [
            "Does anything look uneven or inconsistent?",
            "Is the hierarchy clear?",
            "Does the sequence of steps make sense?",
            "Does the layout feel balanced?",
        ],
    },
    "completeness": {
        "phase": 4, "name": "Completeness",
        "questions": [
            "Is anything unfinished?",
            "Are important elements missing?",
            "Are edge cases accounted for?",
            "Are there placeholder elements?",
            "Is the experience complete from start to finish?",
        ],
        "auto_checks": ["placeholder_scan"],  # Run placeholder detection automatically
    },
    # Phase 5: Comparison
    "competition": {
        "phase": 5, "name": "Competitive Benchmarking",
        "questions": [
            "What do competitors do better?",
            "What do they do worse?",
            "What expectations exist because of competitors?",
            "Does this meet modern standards?",
            "Would a user switch to something else?",
        ],
        "requirement": "MANDATORY: Before building creative work, research 3+ competitor/reference "
                       "examples. Document what they do well. Set a quality bar BEFORE building.",
    },
    "trust": {
        "phase": 5, "name": "Trust & Credibility Signals",
        "questions": [
            "Does this look legitimate?",
            "Are there inconsistencies or mistakes?",
            "Would a user trust this quickly?",
        ],
    },
    # Phase 6: Risk
    "risk": {
        "phase": 6, "name": "Risk Forecasting",
        "questions": [
            "What could go wrong after launch?",
            "What will users complain about?",
            "What problems will appear at scale?",
        ],
    },
    "maintainability": {
        "phase": 6, "name": "Maintainability",
        "questions": [
            "Will this be easy to maintain?",
            "Will it create technical debt?",
            "Can someone else understand this later?",
        ],
    },
    # Phase 7: Verification
    "evidence": {
        "phase": 7, "name": "Evidence & Verification",
        "questions": [
            "Was this tested or assumed?",
            "What evidence supports this conclusion?",
            "What remains uncertain?",
        ],
    },
    "patterns": {
        "phase": 7, "name": "Pattern Recognition",
        "questions": [
            "Does this resemble a past success or failure?",
            "Are we repeating a known mistake?",
        ],
    },
    # Phase 8: Self-Audit
    "doubt": {
        "phase": 8, "name": "Self-Doubt Loop",
        "questions": [
            "What did I miss?",
            "What assumptions am I making?",
            "What did I not verify?",
            "What did I not test?",
            "What would a stricter reviewer criticize?",
            "If someone audits this, what will they catch?",
            "What part of this makes me uneasy?",
        ],
    },
    # Phase 9: Edge Cases
    "edge_cases": {
        "phase": 9, "name": "Edge Case Awareness",
        "questions": [
            "What happens outside the normal scenario?",
            "What if the user behaves unexpectedly?",
            "What rare situation could cause failure?",
        ],
    },
    # Phase 10: Reflection
    "reflection": {
        "phase": 10, "name": "Reflection",
        "questions": [
            "What went well?",
            "What went wrong?",
            "What surprised me?",
            "Did reality match my expectations?",
        ],
    },
    "learning": {
        "phase": 10, "name": "Learning Extraction",
        "questions": [
            "What principle did this reinforce?",
            "What mistake should not happen again?",
            "What process improvement comes from this?",
        ],
    },
    "recalibration": {
        "phase": 10, "name": "Recalibration",
        "questions": [
            "Should I change my approach next time?",
            "Do I need better checkpoints?",
            "Should my standards be higher?",
        ],
    },
}

# Which categories run in parallel (the "thinking about multiple things at once" stage)
PARALLEL_CATEGORIES = {"functional", "structure", "completeness", "competition",
                        "trust", "risk", "maintainability", "evidence", "patterns"}

# Sequential before parallel
SEQUENTIAL_BEFORE = ["purpose", "context", "audience", "priority", "simplicity", "ux", "emotion"]
# Sequential after parallel (consolidation)
SEQUENTIAL_AFTER = ["doubt", "edge_cases", "reflection", "learning", "recalibration"]


@dataclass
class Finding:
    """A single review finding."""
    category: str
    phase: int
    severity: str  # "critical", "major", "minor", "info"
    finding: str
    evidence: str = ""


@dataclass
class CheckResult:
    """Result of checking one category."""
    category: str
    passed: bool
    findings: list[str] = field(default_factory=list)
    evidence: str = ""


@dataclass
class ReviewReport:
    """Complete review report."""
    goal: str
    checks: list[CheckResult] = field(default_factory=list)
    cycles: int = 1
    passed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    @property
    def all_findings(self) -> list[str]:
        out = []
        for c in self.checks:
            for f in c.findings:
                out.append(f"[{c.category}] {f}")
        return out

    @property
    def core_answer(self) -> str:
        if self.passed:
            return ("Yes — this is the right thing, for the right people, "
                    "in the right way, with identified risks managed.")
        failures = self.failures
        return (f"Not yet — {len(failures)} check(s) failed: "
                + ", ".join(c.category for c in failures))


class Review:
    """The Human Operating System review engine.

    One class. Sequential or parallel. Single source of truth.
    """

    def __init__(self, goal: str, parallel: bool = False, max_cycles: int = 3, max_workers: int = 5):
        self.goal = goal
        self.parallel = parallel
        self.max_cycles = max_cycles
        self.max_workers = max_workers
        self._checks: dict[str, CheckResult] = {}
        self._handlers: dict[str, Callable] = {}
        self._context: dict = {}
        self._quality_gate_result = None

    def set_context(self, **kwargs):
        """Set artifact context for handlers.

        Special keys:
        - content: The artifact content (HTML, code, etc.) — triggers auto quality gate
        - test_content: Test file content (for code gate)
        - competitors_researched: list of competitor URLs studied (for competition check)
        """
        self._context.update(kwargs)

    def set_handler(self, category: str, handler: Callable[[dict, list[str]], CheckResult]):
        """Set a custom handler for a category.
        handler(context, questions) -> CheckResult
        """
        self._handlers[category] = handler

    def check(self, category: str, passed: bool = True, evidence: str = "",
              findings: list[str] = None) -> CheckResult:
        """Manually record a check result for a category."""
        result = CheckResult(category=category, passed=passed,
                             evidence=evidence, findings=findings or [])
        self._checks[category] = result
        return result

    def run(self) -> ReviewReport:
        """Run the full review loop. Uses handlers for unchecked categories."""
        report = ReviewReport(goal=self.goal)

        # Auto-run quality gate if content is provided
        content = self._context.get("content", "")
        if content:
            from src.hooks.quality_gates import run_gate, check_placeholders
            gate_result = run_gate(content)
            self._quality_gate_result = gate_result
            if gate_result:
                # Inject gate findings into completeness check
                if not gate_result.passed:
                    self._checks["completeness"] = CheckResult(
                        category="completeness",
                        passed=False,
                        findings=gate_result.findings,
                        evidence=f"Quality gate '{gate_result.gate_name}': "
                                 f"{gate_result.checks_passed} passed, {gate_result.checks_failed} failed",
                    )

            # Always check for placeholders
            placeholders = check_placeholders(content)
            if placeholders:
                existing = self._checks.get("completeness")
                if existing and not existing.passed:
                    existing.findings.extend(placeholders[:5])
                else:
                    self._checks["completeness"] = CheckResult(
                        category="completeness",
                        passed=False,
                        findings=placeholders[:5],
                        evidence="Placeholder content detected",
                    )

        # Check competitive research requirement
        competitors = self._context.get("competitors_researched", [])
        if not competitors and content:
            self._checks["competition"] = CheckResult(
                category="competition",
                passed=False,
                findings=["No competitor research documented. MANDATORY: study 3+ reference "
                          "examples before creative work. Set context(competitors_researched=[...])"],
                evidence="Competitors not researched",
            )

        for cycle in range(self.max_cycles):
            report.cycles = cycle + 1

            # Don't clear auto-set checks on first cycle
            if cycle > 0:
                # Keep quality gate findings across cycles
                gate_checks = {k: v for k, v in self._checks.items()
                               if k in ("completeness",) and not v.passed}
                self._checks.clear()
                self._checks.update(gate_checks)

            if self.parallel:
                self._run_parallel()
            else:
                self._run_sequential()

            report.checks = list(self._checks.values())

            # Check if doubt wants another cycle
            doubt = self._checks.get("doubt")
            if doubt and doubt.passed:
                break
            if doubt and not doubt.findings:
                break

        report.passed = all(c.passed for c in report.checks)
        return report

    def _run_sequential(self):
        """Run all categories sequentially."""
        for cat_id in list(CATEGORIES.keys()):
            if cat_id not in self._checks:
                self._run_category(cat_id)

    def _run_parallel(self):
        """Run sequential-before, then parallel evaluation, then sequential-after."""
        # Sequential: understand + prioritize + execute
        for cat_id in SEQUENTIAL_BEFORE:
            if cat_id not in self._checks:
                self._run_category(cat_id)

        # Parallel: all evaluation categories at once
        parallel_cats = [c for c in PARALLEL_CATEGORIES if c not in self._checks]
        if parallel_cats:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self._run_category, c): c for c in parallel_cats}
                for future in as_completed(futures):
                    try:
                        future.result(timeout=30)
                    except Exception as e:
                        cat = futures[future]
                        self._checks[cat] = CheckResult(
                            category=cat, passed=False,
                            findings=[f"Agent crashed: {e}"],
                        )

        # Sequential: doubt + edge cases + reflection
        for cat_id in SEQUENTIAL_AFTER:
            if cat_id not in self._checks:
                self._run_category(cat_id)

    def _run_category(self, cat_id: str) -> CheckResult:
        """Run a single category using its handler or default."""
        cat_def = CATEGORIES.get(cat_id)
        if not cat_def:
            result = CheckResult(category=cat_id, passed=True, evidence="Unknown category")
            self._checks[cat_id] = result
            return result

        handler = self._handlers.get(cat_id)
        if handler:
            try:
                result = handler(self._context, cat_def["questions"])
                result.category = cat_id
            except Exception as e:
                result = CheckResult(category=cat_id, passed=False,
                                     findings=[f"Handler error: {e}"])
        else:
            # Default: pass with questions as info
            result = CheckResult(
                category=cat_id, passed=True,
                evidence=f"{len(cat_def['questions'])} questions (no custom handler)",
            )

        self._checks[cat_id] = result
        return result

    def finalize(self) -> ReviewReport:
        """Finalize — only checks categories that were explicitly checked."""
        report = ReviewReport(goal=self.goal)
        report.checks = list(self._checks.values())
        report.passed = all(c.passed for c in report.checks) if report.checks else False
        return report


def format_report(report: ReviewReport) -> str:
    """Format a review report for display."""
    lines = [
        f"## Review: {report.goal}",
        f"Cycles: {report.cycles} | Passed: {report.passed}",
        "",
    ]

    # Group by phase
    by_phase: dict[int, list[CheckResult]] = {}
    for c in report.checks:
        cat_def = CATEGORIES.get(c.category, {})
        phase = cat_def.get("phase", 0)
        by_phase.setdefault(phase, []).append(c)

    phase_names = {
        1: "Understanding", 2: "Prioritization", 3: "Execution",
        4: "Review", 5: "Comparison", 6: "Risk", 7: "Verification",
        8: "Self-Audit", 9: "Edge Cases", 10: "Reflection",
    }

    for phase_num in sorted(by_phase.keys()):
        lines.append(f"### Phase {phase_num}: {phase_names.get(phase_num, 'Other')}")
        for c in by_phase[phase_num]:
            icon = "PASS" if c.passed else "FAIL"
            lines.append(f"  [{icon}] {c.category}: {c.evidence}")
            for f in c.findings:
                lines.append(f"         - {f}")
        lines.append("")

    lines.append(f"**{report.core_answer}**")
    return "\n".join(lines)
