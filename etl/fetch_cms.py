"""Fetch official CMS hospital data and build one reproducible feature table."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "cms"
DATASETS = {
    "hospital_general": "xubh-q36u",
    "hcahps_hospital": "dgck-syfz",
    "hrrp": "9n3s-kdb3",
}
HCAHPS_STAR_MEASURES = (
    "H_COMP_1_STAR_RATING", "H_COMP_2_STAR_RATING", "H_COMP_5_STAR_RATING",
    "H_COMP_6_STAR_RATING", "H_CLEAN_STAR_RATING", "H_QUIET_STAR_RATING",
    "H_HSP_RATING_STAR_RATING", "H_RECMND_STAR_RATING", "H_STAR_RATING",
)
API = "https://data.cms.gov/provider-data/api/1"


def read_json(url, attempts=6):
    for attempt in range(attempts):
        try:
            with urlopen(url, timeout=120) as response:
                return json.load(response)
        except (HTTPError, URLError) as error:
            if attempt == attempts - 1 or isinstance(error, HTTPError) and error.code < 500:
                raise
            time.sleep(min(2 ** attempt, 16))


def fetch_dataset(identifier, page_size=500, condition=None):
    rows, offset, expected = [], 0, None
    while expected is None or offset < expected:
        parameters = {"limit": page_size, "offset": offset}
        if condition:
            property_name, value = condition
            parameters.update({
                "conditions[0][property]": property_name,
                "conditions[0][value]": value,
                "conditions[0][operator]": "=",
            })
        query = urlencode(parameters)
        payload = read_json(f"{API}/datastore/query/{identifier}/0?{query}")
        expected = int(payload["count"])
        page = payload["results"]
        if not page:
            break
        rows.extend(page)
        offset += len(page)
    if expected is None or len(rows) != expected:
        raise RuntimeError(f"CMS pagination failed for {identifier}: expected {expected}, received {len(rows)}")
    return pd.DataFrame(rows)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric(series):
    return pd.to_numeric(series.replace({"N/A": None, "Not Available": None, "Not Applicable": None, "": None}), errors="coerce")


def build_feature_table(general, hcahps, hrrp):
    general = general.copy()
    general["facility_id"] = general.facility_id.astype(str).str.zfill(6)
    retained = [
        "facility_id", "facility_name", "state", "hospital_type", "hospital_ownership",
        "emergency_services", "meets_criteria_for_birthing_friendly_designation",
    ]
    general = general[retained].drop_duplicates("facility_id")

    hcahps = hcahps.copy()
    hcahps["facility_id"] = hcahps.facility_id.astype(str).str.zfill(6)
    hcahps["star"] = numeric(hcahps.patient_survey_star_rating)
    star_rows = hcahps[hcahps.hcahps_measure_id.str.endswith("STAR_RATING", na=False) & hcahps.star.notna()]
    stars = star_rows.pivot_table(index="facility_id", columns="hcahps_measure_id", values="star", aggfunc="first")
    stars.columns = ["hcahps_" + column.lower() for column in stars.columns]
    stars = stars.reset_index()

    hrrp = hrrp.copy()
    hrrp["facility_id"] = hrrp.facility_id.astype(str).str.zfill(6)
    hrrp["excess_readmission_ratio"] = numeric(hrrp.excess_readmission_ratio)
    target = hrrp.groupby("facility_id", as_index=False).agg(
        mean_excess_readmission_ratio=("excess_readmission_ratio", "mean"),
        reported_hrrp_conditions=("excess_readmission_ratio", "count"),
    )
    target = target[target.reported_hrrp_conditions >= 2]
    target["elevated_readmission_performance"] = (target.mean_excess_readmission_ratio > 1.0).astype(int)

    features = general.merge(stars, on="facility_id", how="left", validate="one_to_one")
    features = features.merge(target, on="facility_id", how="inner", validate="one_to_one")
    return features.sort_values("facility_id").reset_index(drop=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = {"retrieved_at_utc": retrieved, "publisher": "Centers for Medicare & Medicaid Services", "sources": {}}
    frames = {}
    for name, identifier in DATASETS.items():
        metadata_url = f"{API}/metastore/schemas/dataset/items/{identifier}"
        metadata = read_json(metadata_url)
        if name == "hcahps_hospital":
            frame = pd.concat(
                [fetch_dataset(identifier, condition=("hcahps_measure_id", measure)) for measure in HCAHPS_STAR_MEASURES],
                ignore_index=True,
            )
        else:
            frame = fetch_dataset(identifier)
        path = OUT / f"{name}.csv.gz"
        frame.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
        frames[name] = frame
        manifest["sources"][name] = {
            "identifier": identifier,
            "title": metadata["title"],
            "landing_page": metadata["landingPage"],
            "metadata_url": metadata_url,
            "modified": metadata.get("modified"),
            "released": metadata.get("released"),
            "rows": int(len(frame)),
            "sha256": sha256(path),
            "local_file": str(path.relative_to(ROOT)),
        }
        if name == "hcahps_hospital":
            manifest["sources"][name]["api_filter"] = {"hcahps_measure_id": list(HCAHPS_STAR_MEASURES)}

    features = build_feature_table(frames["hospital_general"], frames["hcahps_hospital"], frames["hrrp"])
    feature_path = OUT / "cms_hospital_features.csv.gz"
    features.to_csv(feature_path, index=False, compression={"method": "gzip", "mtime": 0})
    manifest["feature_table"] = {
        "rows": int(len(features)), "columns": int(features.shape[1]),
        "sha256": sha256(feature_path), "local_file": str(feature_path.relative_to(ROOT)),
        "grain": "one row per CMS facility_id with at least two reportable HRRP conditions",
        "target": "mean reportable excess readmission ratio > 1.0",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
