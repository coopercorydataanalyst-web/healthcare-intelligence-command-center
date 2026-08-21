from pathlib import Path

import pandas as pd

from qa_engine import METRICS, answer_question


ROOT = Path(__file__).resolve().parent
daily = pd.read_csv(ROOT / "data/daily_operations.csv.gz", parse_dates=["date"])
encounters = pd.read_csv(ROOT / "data/synthetic_encounters.csv.gz", parse_dates=["admit_date", "discharge_date"], keep_default_na=False)
interventions = pd.read_csv(ROOT / "data/interventions.csv")
priority = pd.DataFrame([
    {"hospital": "GulfStar Medical Center", "domain": "Patient Flow", "severity_score": 71.0,
     "modeled_exposure": 1000000.0, "accountable_owner": "COO"},
    {"hospital": "GulfStar North", "domain": "Workforce", "severity_score": 60.0,
     "modeled_exposure": 1200000.0, "accountable_owner": "CNO"},
])
hospitals = sorted(daily.hospital.unique())


def ask(question, selected_daily=daily, selected_encounters=encounters):
    return answer_question(
        question, selected_daily, selected_encounters,
        daily.iloc[0:0], encounters.iloc[0:0], interventions, priority,
        all_hospitals=hospitals,
    )


def test_required_example_questions_are_supported():
    questions = [
        "Which hospital has the highest readmission rate?",
        "What changed in ED boarding over the last 90 days?",
        "Which hospital has the highest RN vacancy?",
        "Why is GulfStar Medical Center the top priority?",
        "Which intervention has the highest modeled ROI?",
        "Compare hospitals on operating margin and patient experience.",
    ]
    for question in questions:
        result = ask(question)
        assert result["calculation"] != "No calculation run.", question
        assert result["evidence"] in {"Synthetic Result", "Modeled Estimate"}


def test_every_documented_metric_has_a_safe_current_query():
    for metric in METRICS:
        result = ask(f"Compare hospitals on {metric.aliases[0]}")
        assert result["data"] is not None, metric.key
        assert metric.label in result["data"].columns, metric.key


def test_unsupported_question_refuses_to_guess():
    result = ask("What caused the cardiology strategy to fail?")
    assert result["evidence"] == "Validation Required"
    assert result["calculation"].startswith("No calculation")
    assert len(result["suggestions"]) == 3


def test_filtered_out_hospital_is_reported():
    selected_daily = daily[daily.hospital == hospitals[0]]
    selected_encounters = encounters[encounters.hospital == hospitals[0]]
    excluded = hospitals[-1]
    result = ask(f"What is {excluded}'s operating margin?", selected_daily, selected_encounters)
    assert "excluded by the current Hospital filter" in result["answer"]


def test_priority_and_exposure_intents_are_distinct():
    top = ask("What is the top priority?")
    exposure = ask("Which item has the highest modeled exposure?")
    assert "#1 filtered priority" in top["answer"]
    assert "highest modeled-exposure item" in exposure["answer"]
    assert "GulfStar North" in exposure["answer"]


def test_six_reviewer_regressions_are_fixed():
    reviewer_priority = pd.DataFrame([
        {"hospital": "GulfStar North", "domain": "Patient Experience", "severity_score": 90.0,
         "modeled_exposure": 0.0, "accountable_owner": "Chief Experience Officer"},
        {"hospital": "GulfStar Medical Center", "domain": "Patient Flow", "severity_score": 14.3,
         "modeled_exposure": 55_911_946.0, "accountable_owner": "COO"},
    ])
    def reviewer_ask(question):
        return answer_question(
            question, daily, encounters, daily.iloc[0:0], encounters.iloc[0:0],
            interventions, reviewer_priority, all_hospitals=hospitals,
        )

    exposure = reviewer_ask("Which priority has the highest modeled exposure?")
    assert "$55,911,946" in exposure["answer"]
    assert "GulfStar Medical Center" in exposure["answer"]

    readmission = reviewer_ask("Which hospital has the worst readmission rate?")
    assert "trend summary" not in readmission["answer"].lower()
    assert "readmission" in readmission["answer"].lower()

    wait = reviewer_ask("Which hospital has the longest specialty wait?")
    assert "has the highest Access / Specialty Wait" in wait["answer"] or "tied for the highest Access / Specialty Wait" in wait["answer"]

    top = reviewer_ask("What is the top executive priority?")
    assert "#1 filtered priority" in top["answer"]

    mortality = reviewer_ask("Which hospital has the highest mortality rate?")
    displayed = []
    for hospital, group in daily.groupby("hospital"):
        displayed.append((hospital, f"{100 * group.mortality_rate.mean():.1f}%"))
    winning = max(value for _, value in displayed)
    tied_names = [hospital for hospital, value in displayed if value == winning]
    if len(tied_names) > 1:
        assert "tied" in mortality["answer"].lower()
        assert all(name in mortality["answer"] for name in tied_names)

    unsupported = reviewer_ask("Is the chair rail broken?")
    assert unsupported["evidence"] == "Validation Required"
    assert "HAI" not in unsupported["answer"]


def test_encounter_none_categories_are_preserved_as_values():
    assert len(encounters) == 18_000
    assert encounters.discharge_barrier.isna().sum() == 0
    assert (encounters.discharge_barrier == "None").sum() == 9_979


def test_executive_language_intents_return_auditable_summaries():
    questions = {
        "What has happened positively in the last 30 days?": "Positive changes",
        "what has happen positively in last 30 days": "Positive changes",
        "What is happening positively over the last 30 days?": "Positive changes",
        "What has improved in the last 30 days?": "Positive changes",
        "What got worse in the last 30 days?": "Negative changes",
        "What has gotten worse over the last 30 days?": "Negative changes",
        "Give me the executive summary": "Executive trend summary",
        "What changed this month?": "Executive trend summary",
        "What should leadership celebrate?": "Positive changes",
        "What concerns should leadership know about?": "Negative changes",
    }
    for question, expected in questions.items():
        result = ask(question)
        assert expected in result["answer"], question
        assert result["calculation"] != "No calculation run.", question
        assert result["data"] is not None and not result["data"].empty, question
        assert {"Metric", "Current", "Prior", "Change", "Direction", "Calculation"}.issubset(result["data"].columns)
        assert "do not establish why" in result["limitation"]


def test_executive_summary_requires_two_complete_filtered_windows():
    last_ten = daily[daily.date > daily.date.max() - pd.Timedelta(days=10)]
    last_ten_encounters = encounters[encounters.admit_date > daily.date.max() - pd.Timedelta(days=10)]
    result = ask("What improved in the last 30 days?", last_ten, last_ten_encounters)
    assert result["evidence"] == "Validation Required"
    assert "two complete comparison windows" in result["answer"]


def test_dashboard_overview_and_help_language_is_supported():
    questions = [
        "tell me about this dashboard",
        "What does this dashboard do?",
        "Explain the dashboard",
        "Give me a dashboard overview",
        "Help me understand this dashboard",
        "What can I ask?",
        "How does this dashboard work?",
    ]
    for question in questions:
        result = ask(question)
        assert result["answer"].startswith("GulfStar Intelligence is a 17-sheet"), question
        assert result["evidence"] == "Validation Required — Dashboard Documentation"
        assert "no performance metric aggregation" in result["calculation"]
        assert result["data"] is not None and len(result["data"]) == 6


def test_executive_summary_understands_informal_positive_and_negative_language():
    questions = {
        "anything gud or positve lately": "Positive changes",
        "where are we doing well": "Positive changes",
        "give me the wins": "Positive changes",
        "anything negatve or worrying": "Negative changes",
        "what is not working": "Negative changes",
        "show me the red flags": "Negative changes",
    }
    for question, expected in questions.items():
        result = ask(question)
        assert expected in result["answer"], (question, result["answer"])


def test_main_suggestions_pull_keywords_and_rank_close_safe_question():
    result = ask("can you predict the exact future nurse staffing outcome")
    assert result["evidence"] == "Validation Required"
    assert "workforce" in result["keywords"]
    assert len(result["suggestions"]) == 3
    assert any("RN vacancy" in suggestion or "agency labor" in suggestion for suggestion in result["suggestions"])
