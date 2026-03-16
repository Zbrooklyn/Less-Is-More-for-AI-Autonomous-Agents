"""Tests for the review engine and multi-agent review architecture."""

import pytest

from src.hooks.review_engine import ReviewEngine, format_review
from src.orchestrator.review_agents import (
    MultiAgentReview, MultiAgentReport, AgentFinding,
    format_multi_agent_report, REVIEW_AGENTS,
)


# === Review Engine (Decision Tree) ===

class TestReviewEngine:
    def test_all_phases_pass(self):
        engine = ReviewEngine(goal="Test project")
        engine.phase_understand(purpose="Test", audience="Developers")
        engine.phase_prioritize(priorities=["Quality"])
        engine.phase_execute(feels_trustworthy=True)
        engine.phase_review(functional=True, complete=True)
        engine.phase_compare(meets_standards=True)
        engine.phase_risk(maintainable=True)
        engine.phase_verify(evidence=["Tests pass"])
        engine.phase_doubt()
        engine.phase_edge_cases(edges=["Empty input"])
        engine.phase_reflect(went_well="Everything worked")

        result = engine.finalize()
        assert result.passed
        assert "right thing" in result.core_answer

    def test_functional_failure_blocks(self):
        engine = ReviewEngine(goal="Broken project")
        engine.phase_understand(purpose="Test", audience="Users")
        engine.phase_prioritize(priorities=["Fix"])
        engine.phase_execute()
        engine.phase_review(functional=False, functional_evidence="Crashes on startup")

        result = engine.finalize()
        assert not result.passed
        assert any(f.blocking for f in result.phases)

    def test_missing_phases_detected(self):
        engine = ReviewEngine(goal="Incomplete review")
        engine.phase_understand(purpose="Test", audience="Users")
        # Skip all other phases

        result = engine.finalize()
        skipped = [p for p in result.phases if p.status == "skip"]
        assert len(skipped) >= 8  # Most phases skipped

    def test_doubt_triggers_repeat_flag(self):
        engine = ReviewEngine(goal="Doubtful project")
        engine.phase_understand(purpose="Test", audience="Users")
        engine.phase_doubt(missed=["Error handling"], uneasy="Threading safety")

        assert engine.should_repeat

    def test_doubt_clean_no_repeat(self):
        engine = ReviewEngine(goal="Clean project")
        engine.phase_understand(purpose="Test", audience="Users")
        engine.phase_doubt()

        assert not engine.should_repeat

    def test_findings_collected(self):
        engine = ReviewEngine(goal="Project with issues")
        engine.phase_understand(purpose="Test", audience="Users", missing=["Docs", "Tests"])
        engine.phase_risk(risks=["Data loss"], complaints=["Slow performance"])

        result = engine.finalize()
        assert len(result.all_findings) >= 4

    def test_format_review(self):
        engine = ReviewEngine(goal="Test")
        engine.phase_understand(purpose="Test", audience="Users")
        engine.phase_review(functional=True, complete=True)
        result = engine.finalize()

        text = format_review(result)
        assert "Review: Test" in text
        assert "PASS" in text

    def test_competitive_warnings(self):
        engine = ReviewEngine(goal="Weak product")
        engine.phase_compare(
            competitors=["Competitor A"],
            worse_than=["Better UI", "Faster performance"],
            meets_standards=False,
        )

        result = engine.finalize()
        compare_phase = [p for p in result.phases if p.name == "compare"][0]
        assert compare_phase.status == "warn"
        assert len(compare_phase.findings) >= 3


# === Multi-Agent Review ===

class TestMultiAgentReview:
    def test_default_run_produces_report(self):
        review = MultiAgentReview(goal="Test review")
        report = review.run()

        assert report.goal == "Test review"
        assert report.cycles >= 1
        assert len(report.findings) > 0

    def test_custom_handler(self):
        review = MultiAgentReview(goal="Custom review")

        def custom_purpose(ctx, questions):
            return [AgentFinding(
                agent="purpose-agent", phase=1,
                severity="major", finding="Goal is unclear",
            )]

        review.set_handler(1, custom_purpose)
        report = review.run()

        purpose_findings = [f for f in report.findings if f.phase == 1]
        assert any("unclear" in f.finding for f in purpose_findings)

    def test_critical_finding_fails_review(self):
        review = MultiAgentReview(goal="Critical issue")

        def critical_handler(ctx, questions):
            return [AgentFinding(
                agent="functional-agent", phase=5,
                severity="critical", finding="System crashes on startup",
            )]

        review.set_handler(5, critical_handler)
        report = review.run()

        assert not report.passed
        assert len(report.critical) >= 1

    def test_doubt_agent_triggers_repeat(self):
        call_count = {"n": 0}

        review = MultiAgentReview(goal="Doubtful", max_cycles=2)

        def doubt_handler(ctx, questions):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return [AgentFinding(
                    agent="doubt-agent", phase=10,
                    severity="major", finding="Need another cycle — missed error handling",
                )]
            return [AgentFinding(
                agent="doubt-agent", phase=10,
                severity="info", finding="Second pass looks clean",
            )]

        review.set_handler(10, doubt_handler)
        report = review.run()

        assert report.cycles == 2
        assert call_count["n"] == 2

    def test_all_10_agents_defined(self):
        assert len(REVIEW_AGENTS) == 10
        for i in range(1, 11):
            assert i in REVIEW_AGENTS
            assert "name" in REVIEW_AGENTS[i]
            assert "questions" in REVIEW_AGENTS[i]

    def test_artifact_context_passed(self):
        review = MultiAgentReview(goal="Context test")
        review.set_artifact(code_path="src/", test_path="tests/")

        received_ctx = {}

        def handler(ctx, questions):
            received_ctx.update(ctx)
            return []

        review.set_handler(1, handler)
        review.run()

        assert received_ctx.get("code_path") == "src/"
        assert received_ctx.get("test_path") == "tests/"

    def test_format_report(self):
        report = MultiAgentReport(goal="Test", findings=[
            AgentFinding("test-agent", 1, "critical", "Big problem"),
            AgentFinding("test-agent", 2, "info", "Looks fine"),
        ])
        text = format_multi_agent_report(report)
        assert "Big problem" in text
        assert "!!!" in text  # critical icon
