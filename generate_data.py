from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
rng = np.random.default_rng(105)

hospitals = {
    "GulfStar Medical Center": {"staffed": 310, "licensed": 340, "scale": 1.25, "vacancy_base": .085},
    "GulfStar North": {"staffed": 190, "licensed": 215, "scale": .78, "vacancy_base": .105},
    "GulfStar Community": {"staffed": 135, "licensed": 150, "scale": .55, "vacancy_base": .075},
}
dates = pd.date_range("2025-01-01", "2026-08-07", freq="D")
daily = []

for hospital, cfg in hospitals.items():
    beds, licensed, scale = cfg["staffed"], cfg["licensed"], cfg["scale"]
    for d in dates:
        winter = 1 + 0.10 * np.cos(2 * np.pi * (d.dayofyear - 20) / 365)
        weekday = 1.06 if d.dayofweek in [0, 1] else 0.97 if d.dayofweek >= 5 else 1.0
        admissions = max(8, int(rng.normal(58 * scale * winter * weekday, 7)))
        ed = max(12, int(rng.normal(116 * scale * winter, 14)))
        census = int(np.clip(rng.normal(beds * (0.80 + 0.05 * winter), beds * .035), beds * .55, beds * .98))
        occupancy = census / beds
        discharges = max(7, int(admissions + rng.normal(0, 5)))
        expected_discharges = max(6, int(discharges + rng.normal(2, 4)))
        boarding = max(0.2, rng.normal(7.0 * occupancy, 1.4))
        pending_admissions = max(0, int(rng.normal(max(2, admissions * (.05 + boarding / 55)), 3)))
        ed_to_provider = max(8, rng.normal(23 + boarding * 5.2, 8))
        discharge_order_to_exit = max(.4, rng.normal(1.5 + max(0, occupancy-.76)*8.5, .65))
        lwbs = np.clip(rng.normal(0.027 + boarding / 800, .006), .005, .08)
        readm = np.clip(rng.normal(.126 + .01 * winter, .012), .08, .19)
        mortality = np.clip(rng.normal(.021 + .004 * winter, .003), .012, .035)
        falls = rng.poisson(max(.05, census / 900))
        hai = rng.poisson(max(.03, census / 1450))
        rn_vacancy = np.clip(rng.normal(cfg["vacancy_base"] + max(0, occupancy-.84)*.22, .012), .035, .20)
        staff_hours = census * rng.normal(7.1, .35)
        overtime = max(0, staff_hours * rng.normal(.065 + max(0, occupancy-.86) + rn_vacancy*.15, .018))
        agency_hours = max(0, staff_hours * rng.normal(.012 + rn_vacancy*.26, .009))
        patient_experience = np.clip(rng.normal(.83 - boarding*.006 - rn_vacancy*.16 - lwbs*.35, .018), .62, .92)
        or_cases = max(0, int(rng.normal(28 * scale if d.dayofweek < 5 else 5 * scale, 4)))
        or_util = np.clip(rng.normal(.72 if d.dayofweek < 5 else .43, .08), .25, .94)
        revenue = admissions * rng.normal(17300, 900) + or_cases * rng.normal(7400, 700)
        cost = revenue * rng.normal(.91, .035) + overtime * 38 + agency_hours * 76
        denials = revenue * np.clip(rng.normal(.047, .007), .025, .075)

        daily.append([
            d, hospital, licensed, beds, admissions, ed, discharges, expected_discharges, pending_admissions,
            census, boarding, ed_to_provider, discharge_order_to_exit, lwbs, readm, mortality, falls, hai,
            rn_vacancy, staff_hours, overtime, agency_hours, patient_experience, or_cases, or_util,
            revenue, cost, denials, max(1, rng.normal(15 - 3 * scale, 2.5)), rng.poisson(.16)
        ])

cols = [
    "date","hospital","licensed_beds","staffed_beds","admissions","ed_arrivals","discharges",
    "expected_discharges","pending_admissions","census","boarding_hours","ed_to_provider_minutes",
    "discharge_order_to_exit_hours","lwbs_rate","readmission_rate","mortality_rate","falls","hai",
    "rn_vacancy_rate","staff_hours","overtime_hours","agency_hours","patient_experience","or_cases",
    "or_utilization","revenue","cost","denials","specialty_wait_days","privacy_events"
]
pd.DataFrame(daily, columns=cols).to_csv(DATA / "daily_operations.csv.gz", index=False, compression="gzip")

enc = []
dxs = ["Heart Failure", "Sepsis", "COPD", "Diabetes", "Joint Replacement", "Maternal Care"]
payers = ["Medicare", "Medicaid", "Commercial", "Self-Pay"]
races = ["Black", "Hispanic", "White", "Asian", "Other / Unknown"]
barriers = ["None", "Transportation", "Medication Access", "Housing", "Caregiver", "Language"]

for i in range(18000):
    hospital = rng.choice(list(hospitals), p=[.49,.30,.21])
    admit = rng.choice(dates)
    diagnosis = rng.choice(dxs, p=[.18,.16,.17,.19,.18,.12])
    svi = int(rng.integers(1,5))
    barrier = rng.choice(barriers, p=[.55,.11,.10,.08,.10,.06])
    los = int(max(1, rng.gamma(2.0, 1.5)))
    followup = rng.random() < (.83 - .07*(svi-1) - .10*(barrier != "None"))
    readmit_p = .075 + .025*(svi-1) + .045*(barrier != "None") + .05*(diagnosis in ["Heart Failure","COPD"])
    deteriorate = rng.random() < (.045 + .045*(diagnosis == "Sepsis"))
    harm = rng.random() < (.018 + .018*deteriorate)
    base_cost = {
        "Heart Failure":17000,"Sepsis":29000,"COPD":13500,"Diabetes":11000,
        "Joint Replacement":24000,"Maternal Care":14500
    }[diagnosis]
    cost = max(2500, rng.normal(base_cost * (1 + .16*(los-3)), base_cost*.18))
    revenue = cost * rng.normal(1.08, .12)
    enc.append([
        f"SYN-{i+1:06d}",hospital,admit,admit+pd.Timedelta(days=los),diagnosis,
        int(rng.integers(18,91)),rng.choice(["Female","Male"],p=[.53,.47]),rng.choice(races),
        rng.choice(payers,p=[.39,.24,.33,.04]),svi,barrier,followup,rng.random()<readmit_p,
        deteriorate,harm,los,cost,revenue
    ])

ecols = [
    "encounter_id","hospital","admit_date","discharge_date","service_line","age","sex","race_ethnicity",
    "payer","svi_quartile","discharge_barrier","followup_booked","readmission_30d","deterioration",
    "harm","los","cost","revenue"
]
pd.DataFrame(enc,columns=ecols).to_csv(DATA/"synthetic_encounters.csv.gz",index=False,compression="gzip")

privacy_types = ["Excess Access","Misdirected Communication","Minimum Necessary","Unencrypted Device","Third-Party Risk"]
priv = []
for i in range(420):
    d = rng.choice(dates)
    h = rng.choice(list(hospitals))
    typ = rng.choice(privacy_types,p=[.38,.23,.18,.08,.13])
    priv.append([
        d,h,typ,int(rng.integers(1,350)),
        rng.choice(["Low","Moderate","High"],p=[.55,.34,.11]),
        rng.choice(["Closed","Monitoring","Remediation Open"],p=[.71,.18,.11])
    ])
pd.DataFrame(priv,columns=["date","hospital","event_type","records_affected","severity","status"]).to_csv(DATA/"privacy_events.csv",index=False)

interventions = pd.DataFrame([
    ["Discharge-before-noon reliability","Flow",360000,1250000,1200,75],
    ["High-risk transition nurse","Readmissions",540000,1180000,420,78],
    ["Sepsis rescue bundle","Quality",410000,1640000,95,84],
    ["ED fast-track redesign","Access",290000,910000,870,73],
    ["Denial prevention work queue","Margin",240000,1320000,0,81],
    ["OR first-case-on-time program","Procedural",180000,780000,0,76],
    ["Minimum-necessary access controls","Privacy",210000,520000,0,69],
    ["Language-access navigation","Equity",260000,640000,310,67],
], columns=["intervention","domain","annual_cost","annual_value","capacity_days","confidence"])
interventions.to_csv(DATA/"interventions.csv",index=False)

sources = pd.DataFrame([
    ["CMS Provider Data Catalog","Quality, HCAHPS, readmissions, payment benchmarks","Public benchmark source","Quarterly / annual","https://data.cms.gov/provider-data/topics/hospitals"],
    ["AHRQ Quality Indicators","Patient safety and quality methods","Public methodology","Versioned","https://qualityindicators.ahrq.gov/"],
    ["CDC/ATSDR Social Vulnerability Index","Community vulnerability context","Public benchmark source","Periodic","https://www.atsdr.cdc.gov/place-health/php/svi/"],
    ["HRSA Area Health Resources Files","Workforce and community context","Public benchmark source","Annual","https://data.hrsa.gov/topics/health-workforce/ahrf"],
    ["HHS OCR Breach Portal","Privacy breach benchmark categories","Public benchmark source","Rolling","https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf"],
    ["GulfStar Synthetic Operations","Operations, finance, encounters, staffing","Synthetic portfolio data","Through 2026-08-07","Generated with fixed seed; no PHI"],
],columns=["source","use","evidence_type","freshness","url"])
sources.to_csv(DATA/"source_registry.csv",index=False)
print("Generated healthcare portfolio data in", DATA)
