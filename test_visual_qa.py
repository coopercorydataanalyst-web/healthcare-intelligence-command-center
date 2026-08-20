from pathlib import Path

import pandas as pd

from qa_engine import METRICS
from visual_qa import DOCUMENTED_CONTENT, DOCUMENTED_IMPROVEMENTS, VISUALS, answer_visual_question, resolve_visual, visual_options


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


def test_named_kpi_inside_visual_gets_granular_data_aware_explanation():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "what does Patient Experience: 76.8% mean", daily, encounters,
    )
    assert "Patient Experience of 76.8%" in result["answer"]
    assert "mean synthetic patient-experience composite" in result["answer"]
    assert "5.2 percentage points below the favorable threshold" in result["answer"]
    assert "63/100" in result["answer"]
    assert "Across the selected hospitals" in result["answer"]
    assert "mean synthetic patient_experience composite" in result["calculation"]
    assert result["evidence"] == "Synthetic Result / Modeled Estimate"
    assert "not an official HCAHPS score" in result["limitation"]
    assert "Operating Margin:" not in result["answer"]


def test_other_named_kpi_inside_visual_uses_its_own_definition():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "Can you explain what the RN vacancy number means?", daily, encounters,
    )
    assert "RN Vacancy of" in result["answer"]
    assert "mean synthetic RN vacancy rate" in result["answer"]
    assert "unit-level skill mix" in result["limitation"]


def test_every_mapped_metric_on_every_visual_gets_metric_level_answer():
    by_key = {metric.key: metric for metric in METRICS}
    for page, visuals in VISUALS.items():
        for visual, spec in visuals.items():
            for key in spec["metrics"]:
                metric = by_key[key]
                question = f"What does {metric.aliases[0]} mean on this visual?"
                result = answer_visual_question(page, visual, question, daily, encounters)
                assert f"{metric.label} of" in result["answer"], (page, visual, key, result["answer"])
                assert result["calculation"]
                assert result["evidence"] != "Validation Required — Visual Documentation"


def test_documented_modeled_and_governance_content_is_explained_specifically():
    for visual, entries in DOCUMENTED_CONTENT.items():
        page = next(page for page, visuals in VISUALS.items() if visual in visuals)
        alias = entries[0][0][0]
        result = answer_visual_question(page, visual, f"What does {alias} mean?", daily, encounters)
        assert result["answer"] == entries[0][1], (visual, alias, result["answer"])
        assert result["calculation"] == entries[0][2]
        assert "operational validation" in result["limitation"]


def test_er_boarding_improvement_is_metric_filter_and_hospital_aware():
    copd_daily = daily.copy()
    copd_encounters = encounters[encounters.service_line == "COPD"].copy()
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "how can I improve the er boarding", copd_daily, copd_encounters,
    )
    assert "Improvement opportunity — ED Boarding" in result["answer"]
    assert "COPD" in result["answer"]
    assert "Strongest pressure:" in result["answer"]
    assert "Staffed-Bed Utilization" in result["answer"]
    assert "Discharge-Order-to-Exit Time" in result["answer"]
    assert "Chief Operating Officer" in result["answer"]
    assert "does not claim" in result["answer"]
    assert "Validate the underlying denominator" not in result["answer"]


def test_generic_improvement_question_uses_weakest_mapped_metric():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "what should we do to improve this visual", daily, encounters,
    )
    assert "Improvement opportunity —" in result["answer"]
    assert "current filtered result" in result["answer"]
    assert "Leadership response:" in result["answer"]


def test_domain_score_patient_experience_improvement_uses_metric_path():
    result = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "how can I improve patient experience", daily, encounters,
    )
    assert "Improvement opportunity — Patient Experience" in result["answer"]
    assert "Chief Experience Officer" in result["answer"]
    assert "Related filtered signals:" in result["answer"]
    assert "Review the component metrics behind the weakest domain" not in result["answer"]


def test_every_metric_backed_visual_has_filter_aware_generic_improvement():
    for page, visuals in VISUALS.items():
        for visual, spec in visuals.items():
            if not spec["metrics"]:
                continue
            result = answer_visual_question(page, visual, "how can we improve this visual", daily, encounters)
            assert "Improvement opportunity —" in result["answer"], (page, visual, result["answer"])
            assert "current filtered result" in result["answer"]
            assert "Leadership response:" in result["answer"]


def test_every_documented_improvement_family_has_specific_action():
    for visual, entries in DOCUMENTED_IMPROVEMENTS.items():
        page = next(page for page, visuals in VISUALS.items() if visual in visuals)
        alias = entries[0][0][0]
        result = answer_visual_question(page, visual, f"how can we improve {alias}", daily, encounters)
        assert entries[0][1] in result["answer"], (visual, alias, result["answer"])
        assert "not a causal or patient-care recommendation" in result["answer"]
