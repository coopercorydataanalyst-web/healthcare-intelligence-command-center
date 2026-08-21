import hashlib
import json
from pathlib import Path

import pandas as pd

from models.cms.inference import load_cms_artifacts


ROOT = Path(__file__).resolve().parent


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_cms_manifest_matches_committed_official_extracts():
    manifest = json.loads((ROOT / "data" / "cms" / "manifest.json").read_text())
    assert set(manifest["sources"]) == {"hospital_general", "hcahps_hospital", "hrrp"}
    assert manifest["feature_table"]["rows"] == 2620
    for source in manifest["sources"].values():
        path = ROOT / source["local_file"]
        assert path.exists()
        assert sha256(path) == source["sha256"]
        assert source["landing_page"].startswith("https://data.cms.gov/provider-data/dataset/")
    feature_path = ROOT / manifest["feature_table"]["local_file"]
    assert sha256(feature_path) == manifest["feature_table"]["sha256"]


def test_cms_feature_table_has_one_row_per_hospital_and_no_target_leakage_feature():
    frame = pd.read_csv(ROOT / "data" / "cms" / "cms_hospital_features.csv.gz", dtype={"facility_id": str})
    assert len(frame) == frame.facility_id.nunique() == 2620
    assert frame.facility_id.str.fullmatch(r"\d{6}").all()
    assert frame.elevated_readmission_performance.mean() > 0.45
    assert frame.elevated_readmission_performance.mean() < 0.55
    manifest = json.loads((ROOT / "models" / "cms" / "feature_manifest.json").read_text())
    assert "mean_excess_readmission_ratio" not in manifest["required_columns"]
    assert "elevated_readmission_performance" not in manifest["required_columns"]


def test_grouped_validation_keeps_each_state_in_one_outer_test_fold():
    features = pd.read_csv(ROOT / "data" / "cms" / "cms_hospital_features.csv.gz", dtype={"facility_id": str})
    predictions = pd.read_csv(ROOT / "models" / "cms" / "grouped_predictions.csv.gz")
    joined = features.reset_index(drop=True).join(predictions.set_index("row"))
    assert joined.groupby("state").fold.nunique().max() == 1
    assert joined.calibrated_probability.between(0, 1).all()


def test_cms_model_beats_prevalence_baseline_and_reports_calibration_and_subgroups():
    artifacts = load_cms_artifacts(ROOT)
    metrics = artifacts["metrics"]
    assert metrics["grouped_calibrated_brier"] < metrics["prevalence_baseline_brier"]
    assert metrics["grouped_calibrated_auc"] > 0.60
    assert len(metrics["grouped_auc_95_interval"]) == 2
    assert {"Uncalibrated", "Calibrated"} == set(artifacts["calibration"].probability_type)
    assert {"hospital_ownership", "emergency_services", "hcahps_summary_quartile", "reported_hrrp_conditions"}.issubset(set(artifacts["subgroups"].dimension))
    assert "not causal effects" in artifacts["model_card"].lower()


def test_cms_serving_loader_enforces_feature_contract_and_loads_only_artifacts():
    artifacts = load_cms_artifacts(ROOT)
    assert artifacts["model"]["pipeline"] is not None
    assert artifacts["model"]["calibrator"] is not None
    assert len(artifacts["scored"]) == 2620
    assert not artifacts["scored"].calibrated_probability.isna().any()
