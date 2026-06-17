"""Deterministic tests: the divergence is real, and the detectors catch it.

These tests require no LLM and no LibreOffice -- they assert the parser-level
divergence and that the reader-comparison defenses flag it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from poc import lying_email, lying_xlsx  # noqa: E402
from defense import detect_email, detect_xlsx  # noqa: E402


def _build(tmp, cond):
    base = os.path.join(tmp, "base.xlsx")
    out = os.path.join(tmp, f"{cond}.xlsx")
    lying_xlsx.build_covenant(base)
    return lying_xlsx.tamper(base, out, lying_xlsx.CONDITIONS[cond])


def test_xlsx_divergence(tmp_path):
    """pandas reads the fabricated cache; the human (recalc) sees the truth."""
    path = _build(str(tmp_path), "C3")
    machine = lying_xlsx.pandas_read(path)
    truth = lying_xlsx.ground_truth()
    assert machine["Debt / EBITDA (x)"] == 2.5
    assert machine["Covenant Status"] == "COMPLIANT"
    assert truth["Debt/EBITDA"] == 3.8
    assert truth["Status"] == "BREACH"


def test_xlsx_is_byte_clean(tmp_path):
    """No PUA characters, no embedded fonts -- unlike a glyph-remap attack."""
    path = _build(str(tmp_path), "C3")
    tells = lying_xlsx.has_stealth_tells(path)
    assert tells["pua_chars"] == 0
    assert tells["embedded_fonts"] == 0


def test_xlsx_detector_catches_all_tampers(tmp_path):
    """recompute-vs-cache flags every tampered condition (C1, C2, C3)."""
    for cond in ("C1", "C2", "C3"):
        path = _build(str(tmp_path), cond)
        findings = detect_xlsx.detect(path)
        refs = {ref for ref, _, _ in findings}
        assert "B7" in refs, f"{cond}: ratio tamper not detected"
        assert "B9" in refs, f"{cond}: status tamper not detected"


def test_xlsx_detector_passes_control(tmp_path):
    """The control (true caches) raises no divergence."""
    path = _build(str(tmp_path), "C0")
    assert detect_xlsx.detect(path) == []


def test_email_divergence():
    """The pipeline reading differs from the human reading."""
    raw = lying_email.build_message(*lying_email.SCENARIOS["E3_terms"])
    assert "6 weeks" in lying_email.plain_view(raw)
    assert "4 weeks" in lying_email.human_view(raw)


def test_email_detector_flags_value_and_term_divergence():
    for scenario in ("E1_wire", "E3_terms", "E2_injection"):
        raw = lying_email.build_message(*lying_email.SCENARIOS[scenario])
        assert detect_email.detect(raw)["divergent"], f"{scenario} not flagged"


def test_email_detector_passes_control():
    raw = lying_email.build_message(*lying_email.SCENARIOS["E0_control"])
    assert not detect_email.detect(raw)["divergent"]
