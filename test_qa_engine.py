from pathlib import Path

import pandas as pd

from qa_engine import METRICS, answer_question


ROOT = Path(__file__).resolve().parent
daily = pd.read_csv(ROOT / "data/daily_operations.csv.gz", parse_dates=["date"])
encounters = pd.read_csv(ROOT / "data/synthetic_encounters.csv.gz", parse_dates=["admit_date", "discharge_date"])
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
