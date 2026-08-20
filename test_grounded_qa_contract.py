from pathlib import Path


APP = (Path(__file__).resolve().parent / "app.py").read_text()


def test_grounded_contract_has_required_executive_sections():
    for heading in ("What", "When", "Where", "How", "Why"):
        assert f'st.markdown("##### {heading}")' in APP
    assert "Visible filtered data and documented dashboard logic only" in APP
    assert "No extrapolation or outside knowledge" in APP


def test_grounded_contract_is_used_on_both_qa_surfaces():
    # One definition plus calls for the dedicated Q&A sheet and both contextual
    # visual result paths (structured and fallback).
    assert APP.count("render_grounded_contract(") >= 4
    assert "Grounded data-analyst role" in APP
    assert "Grounded data-analyst mode applies on every sheet" in APP
