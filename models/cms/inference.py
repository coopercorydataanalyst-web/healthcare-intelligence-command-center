"""Deployment-safe loader for the committed CMS model and feature contract."""

import json
from pathlib import Path

import joblib
import pandas as pd


def load_cms_artifacts(root: Path):
    model_dir = Path(root) / "models" / "cms"
    data_path = Path(root) / "data" / "cms" / "cms_hospital_features.csv.gz"
    feature_manifest = json.loads((model_dir / "feature_manifest.json").read_text())
    features = pd.read_csv(data_path, dtype={"facility_id": str})
    missing = set(feature_manifest["required_columns"]) - set(features)
    if missing:
        raise ValueError(f"CMS feature contract failed; missing columns: {sorted(missing)}")
    model = joblib.load(model_dir / "model.joblib")
    metrics = json.loads((model_dir / "metrics.json").read_text())
    predictions = pd.read_csv(model_dir / "grouped_predictions.csv.gz")
    scored = features.reset_index(drop=True).join(predictions.set_index("row"), how="left")
    return {
        "model": model, "metrics": metrics, "features": features, "scored": scored,
        "calibration": pd.read_csv(model_dir / "calibration.csv"),
        "subgroups": pd.read_csv(model_dir / "subgroup_audit.csv"),
        "explanations": pd.read_parquet(model_dir / "association_explanations.parquet"),
        "feature_manifest": feature_manifest,
        "source_manifest": json.loads((Path(root) / "data" / "cms" / "manifest.json").read_text()),
        "model_card": (model_dir / "model_card.md").read_text(),
    }
