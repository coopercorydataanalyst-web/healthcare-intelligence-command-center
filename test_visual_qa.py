from pathlib import Path

import pandas as pd

from visual_qa import VISUALS, answer_visual_question, resolve_visual, visual_options


ROOT = Path(__file__).resolve().parent
daily = pd.read_csv(ROOT / "data/daily_operations.csv.gz", parse_dates=["date"])
encounters = pd.read_csv(ROOT / "data/synthetic_encounters.csv.gz", parse_dates=["admit_date", "discharge_date"])


def test_every_analysis_sheet_has_visual_context():
    assert set(VISUALS) == {str(number) for number in range(1, 15)}
    for number in range(1, 15):
        assert visual_options(f"{number} — Sheet")


def test_every_visual_answers_core_contextual_questions():
    questions = [
        "What is this visual telling me?",
        "What happened on this visual?",
        "What should I be most interested in and why?",
        "What can I do to improve the output?",
        "What are the callouts on this visual?",
        "How is this calculated?",
        "What are the limitations?",
    ]
    for page_number, visuals in VISUALS.items():
        for visual in visuals:
            for question in questions:
                result = answer_visual_question(page_number, visual, question, daily, encounters)
                assert not result["answer"].startswith("I can explain"), (page_number, visual, question)
                assert result["calculation"]
                assert "does not establish cause" in result["limitation"]


def test_unsupported_visual_question_refuses_to_guess():
    visual = visual_options("1 — CEO")[0]
    result = answer_visual_question("1 — CEO", visual, "Predict next year's exact result", daily, encounters)
    assert result["evidence"] == "Validation Required"
    assert "No supported visual-question intent" in result["calculation"]
    assert len(result["suggestions"]) == 3
    assert result["keywords"]


def test_combined_visual_question_answers_each_requested_part():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "What is this visual telling me, what should I focus on, and what can I do to improve it?",
        daily, encounters,
    )
    assert "What it shows:" in result["answer"]
    assert "What to focus on:" in result["answer"]
    assert "Possible improvement response:" in result["answer"]


def test_human_variance_typos_and_paraphrases_are_understood():
    visual = "Executive KPI Cards"
    expectations = {
        "wht is this vizual tryin to tel me": "What it shows:",
        "anything gud or positve in these outputs": "Positive movement:",
        "where are we doing well": "Positive movement:",
        "what is bad or negatve here": "Negative movement:",
        "what is not working": "Negative movement:",
        "any red flags or worrying results": "Negative movement:",
        "how can we make this better": "Possible improvement response:",
        "what could be improvde": "Possible improvement response:",
        "what should we do next": "Possible improvement response:",
        "why should i care about this": "What to focus on:",
        "what stands out": "What to focus on:",
        "how did you get this number": "How it is calculated or encoded:",
        "can i trust this chart": "Limitation:",
    }
    for question, expected in expectations.items():
        result = answer_visual_question("1 — CEO", visual, question, daily, encounters)
        assert expected in result["answer"], (question, result["answer"])


def test_visual_suggestions_use_extracted_keywords_and_close_intent():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "forecast the exact future chart outcome", daily, encounters,
    )
    assert len(result["suggestions"]) == 3
    assert "visual" in result["keywords"]
    assert any("visual" in suggestion.lower() for suggestion in result["suggestions"])


def test_explicit_visual_name_overrides_stale_dropdown_selection():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "what does executive health score by domain mean", daily, encounters,
    )
    assert result["resolved_visual"] == "Executive Health Score by Domain"
    assert "used that visual instead" in result["selection_note"]
    assert "Financial 90; Workforce 90; Patient Flow 86; Quality & Safety 80; Access 77; Patient Experience 63" in result["answer"]
    assert "Patient Experience is lowest at 63" in result["answer"]
    assert "each domain is the unweighted mean of its components" in result["calculation"]
    assert result["evidence"] == "Synthetic Result / Modeled Estimate"


def test_generic_this_visual_keeps_dropdown_selection():
    resolved, _ = resolve_visual("1 — CEO", "Executive KPI Cards", "what is this visual telling me")
    assert resolved == "Executive KPI Cards"
