"""Quality gates — domain-specific checklists that MUST pass before work ships.

Each gate is a list of checks. Every check is a function that examines content
and returns (passed: bool, finding: str). Gates run automatically when the
review module detects the work type.
"""

import re
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class GateResult:
    """Result of running a quality gate."""
    gate_name: str
    passed: bool
    checks_passed: int
    checks_failed: int
    findings: list[str] = field(default_factory=list)


# ============================================================
# Placeholder Detection (applies to ALL work)
# ============================================================

# Case-SENSITIVE patterns (must be exact case)
PLACEHOLDER_PATTERNS_SENSITIVE = [
    r"\bYOUR\s+[A-Z][A-Z]+\b",   # YOUR HERO, YOUR NAME (YOUR + uppercase word)
    r"\bTODO\b",                  # TODO (uppercase only)
    r"\bFIXME\b",                 # FIXME
    r"\bPLACEHOLDER\b",          # PLACEHOLDER
    r"\bTBD\b",                   # TBD
    r"\bXXX\b",                   # XXX
]

# Case-INSENSITIVE patterns
PLACEHOLDER_PATTERNS_INSENSITIVE = [
    r"\bLorem\s+ipsum\b",        # Lorem ipsum
    r"\bexample\.com\b",         # example.com (unless in tests)
    r"\$\{.*?\}",                # ${VARIABLE} unreplaced template vars
    r"\{\{.*?\}\}",              # {{VARIABLE}} unreplaced template vars
]


def check_placeholders(content: str, allow_patterns: list[str] = None) -> list[str]:
    """Scan content for placeholder text. Returns list of found placeholders."""
    findings = []
    allow = allow_patterns or []

    def _check(match_text):
        if not any(re.search(a, match_text, re.IGNORECASE) for a in allow):
            findings.append(f"Placeholder detected: '{match_text}'")

    # Case-sensitive
    for pattern in PLACEHOLDER_PATTERNS_SENSITIVE:
        for match in re.findall(pattern, content):
            _check(match)

    # Case-insensitive
    for pattern in PLACEHOLDER_PATTERNS_INSENSITIVE:
        for match in re.findall(pattern, content, re.IGNORECASE):
            _check(match)

    return findings


# ============================================================
# Commercial Page Gate (agency sites, landing pages, product pages)
# ============================================================

def gate_commercial_page(html: str) -> GateResult:
    """Quality gate for commercial/marketing pages."""
    checks = []

    # 1. Social proof present
    social_proof_patterns = [
        r"testimonial|review|case\s+study|client\s+said|customer\s+quote",
        r"\d+%\s+(increase|growth|improvement|reduction)",
        r"\d+x\s+(return|growth|revenue)",
        r"trusted\s+by|used\s+by|partnered\s+with",
    ]
    has_social_proof = any(re.search(p, html, re.IGNORECASE) for p in social_proof_patterns)
    checks.append(("Social proof present", has_social_proof,
                    "No testimonials, case studies, or results found" if not has_social_proof else ""))

    # 2. Call to action present
    cta_patterns = [r"book\s+a\s+call|get\s+started|contact\s+us|schedule|free\s+audit|sign\s+up"]
    has_cta = any(re.search(p, html, re.IGNORECASE) for p in cta_patterns)
    checks.append(("Call to action present", has_cta,
                    "No clear CTA found" if not has_cta else ""))

    # 3. Contact info present
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", html))
    has_phone = bool(re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", html))
    has_contact = has_email or has_phone
    checks.append(("Contact information present", has_contact,
                    "No email or phone found" if not has_contact else ""))

    # 4. No placeholders
    placeholders = check_placeholders(html, allow_patterns=[r"example\.com.*test"])
    has_no_placeholders = len(placeholders) == 0
    checks.append(("No placeholder content", has_no_placeholders,
                    "; ".join(placeholders[:3]) if placeholders else ""))

    # 5. Images or visual content
    img_count = len(re.findall(r"<img\s", html, re.IGNORECASE))
    svg_count = len(re.findall(r"<svg\s", html, re.IGNORECASE))
    video_count = len(re.findall(r"<video\s", html, re.IGNORECASE))
    visual_count = img_count + svg_count + video_count
    has_visuals = visual_count >= 3
    checks.append(("Sufficient visual content", has_visuals,
                    f"Only {visual_count} visual elements (need 3+)" if not has_visuals else f"{visual_count} visuals"))

    # 6. Mobile responsive indicators
    has_viewport = bool(re.search(r"viewport", html, re.IGNORECASE))
    has_responsive = bool(re.search(r"(md:|lg:|sm:|responsive|@media|max-width)", html, re.IGNORECASE))
    is_responsive = has_viewport and has_responsive
    checks.append(("Mobile responsive", is_responsive,
                    "Missing viewport meta or responsive CSS" if not is_responsive else ""))

    # 7. Page has substantial content
    # Strip tags and check word count
    text_only = re.sub(r"<[^>]+>", " ", html)
    text_only = re.sub(r"\s+", " ", text_only).strip()
    word_count = len(text_only.split())
    has_content = word_count >= 200
    checks.append(("Substantial content", has_content,
                    f"Only {word_count} words (need 200+)" if not has_content else f"{word_count} words"))

    # 8. Hero section has visual element (not just text)
    hero_section = html[:3000]  # First ~3000 chars likely contains hero
    hero_has_visual = bool(re.search(r"<(img|svg|video|canvas)", hero_section, re.IGNORECASE))
    hero_has_bg = bool(re.search(r"(background-image|bg-\[|hero.*img|hero.*video)", hero_section, re.IGNORECASE))
    hero_visual = hero_has_visual or hero_has_bg
    checks.append(("Hero has visual element", hero_visual,
                    "Hero section is text-only — add imagery, video, or background" if not hero_visual else ""))

    # Build result
    passed_count = sum(1 for _, p, _ in checks if p)
    failed_count = sum(1 for _, p, _ in checks if not p)
    findings = [f"[FAIL] {name}: {msg}" for name, p, msg in checks if not p and msg]

    return GateResult(
        gate_name="commercial_page",
        passed=failed_count == 0,
        checks_passed=passed_count,
        checks_failed=failed_count,
        findings=findings,
    )


# ============================================================
# Code Quality Gate (Python modules, scripts)
# ============================================================

def gate_code_quality(source: str, test_source: str = "") -> GateResult:
    """Quality gate for code."""
    checks = []

    # 1. Has docstrings
    has_module_doc = source.strip().startswith('"""') or source.strip().startswith("'''")
    checks.append(("Module docstring", has_module_doc,
                    "Missing module-level docstring" if not has_module_doc else ""))

    # 2. No debug prints left
    debug_patterns = [r"print\(.*debug", r"print\(.*TODO", r"breakpoint\(\)", r"import\s+pdb"]
    debug_found = [p for p in debug_patterns if re.search(p, source, re.IGNORECASE)]
    checks.append(("No debug code", len(debug_found) == 0,
                    f"Debug code found: {debug_found}" if debug_found else ""))

    # 3. Has error handling
    has_try = "try:" in source
    has_except = "except" in source
    checks.append(("Error handling present", has_try and has_except,
                    "No try/except blocks" if not (has_try and has_except) else ""))

    # 4. Tests exist and cover the module
    has_tests = len(test_source) > 100
    checks.append(("Tests exist", has_tests,
                    "No test file or test file is empty" if not has_tests else ""))

    # 5. No placeholders
    placeholders = check_placeholders(source)
    checks.append(("No placeholders", len(placeholders) == 0,
                    "; ".join(placeholders[:3]) if placeholders else ""))

    passed_count = sum(1 for _, p, _ in checks if p)
    failed_count = sum(1 for _, p, _ in checks if not p)
    findings = [f"[FAIL] {name}: {msg}" for name, p, msg in checks if not p and msg]

    return GateResult(
        gate_name="code_quality",
        passed=failed_count == 0,
        checks_passed=passed_count,
        checks_failed=failed_count,
        findings=findings,
    )


# ============================================================
# Gate Registry
# ============================================================

GATES = {
    "commercial_page": gate_commercial_page,
    "code_quality": gate_code_quality,
}


def detect_work_type(content: str) -> str:
    """Auto-detect what type of work this is."""
    if "<html" in content.lower() or "<!doctype" in content.lower():
        # Check if it's a commercial page
        if any(kw in content.lower() for kw in ["pricing", "contact", "services", "testimonial", "cta", "book a call"]):
            return "commercial_page"
        return "html_page"
    if "def " in content or "class " in content or "import " in content:
        return "code_quality"
    return "unknown"


def run_gate(content: str, gate_name: str = None) -> Optional[GateResult]:
    """Run the appropriate quality gate for the content."""
    if gate_name is None:
        gate_name = detect_work_type(content)

    gate_fn = GATES.get(gate_name)
    if gate_fn:
        return gate_fn(content)
    return None
