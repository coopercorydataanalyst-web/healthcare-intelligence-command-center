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


def test_build_version_and_clear_answer_controls_are_visible():
    assert 'APP_BUILD = "2026.08.20-v18-quantity-aware-rankings"' in APP
    assert "Dashboard build: {APP_BUILD}" in APP
    assert "def emphasize_low_scores(text):" in APP
    assert "value < 80" in APP
    assert 'class="qa-low-score"' in APP
    assert 'score_class = " low-score"' in APP
    assert "Clear Saved Q&A Answer" in APP
    assert "Clear This Visual Answer" in APP
    assert 'why_text = display.get("why")' in APP
    assert "This interpretation follows from these displayed facts" in APP
