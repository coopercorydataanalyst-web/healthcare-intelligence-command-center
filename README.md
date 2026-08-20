# Healthcare Intelligence Command Center

An executive healthcare analytics portfolio built for a fictional three-hospital Houston health system. The application connects clinical quality, patient flow, effective capacity, workforce, access, margin, equity, privacy, quality improvement, and intervention economics in one auditable Streamlit decision-support product.

## Executive-first architecture

The first two analysis sheets are designed as operating command centers rather than traditional reporting pages:

1. **CEO Executive Command Center**
   - Executive Health Score with transparent portfolio weights
   - Current vs comparable prior-period "What Changed?" briefing
   - Hospital/domain Executive Priority Queue
   - Accountable executive ownership (COO, CNO, CMO, CFO, etc.)
   - Modeled financial exposure paired with evidence labels
   - Effective staffed capacity, RN vacancy, agency labor, and patient-experience signals
   - Explicit distinction between synthetic results, modeled estimates, and validation-required conclusions

2. **Patient Flow & Capacity Command Center**
   - Licensed vs staffed vs occupied capacity
   - Available staffed beds
   - ED boarding and ED-to-provider intervals
   - Pending admissions and expected discharges
   - Discharge-order-to-exit delay
   - Hospital operating matrix
   - Modeled patient-flow funnel
   - What-if bed-day release scenario

The application contains 14 analysis sheets in total, including dedicated demonstrations of:

- Clinical deterioration and rescue surveillance
- Preventable harm and modeled financial exposure
- Readmission prevention and transition reliability
- Workforce-to-outcome analytics
- Access leakage and lost demand
- OR and procedural yield
- Health equity screening and geographic opportunity
- Payer, denial, and margin integrity
- Intervention prioritization and ROI modeling
- Methods, governance, evidence confidence, and lineage
- CIPP-informed privacy governance and responsible analytics
- CPHQ-informed statistical process control, Pareto prioritization, PDSA learning cycles, and reliability management

## Evidence model

Every dashboard conclusion is identified as one of four types:

- **Public benchmark:** authoritative source or metric definition.
- **Synthetic result:** reproducible fictional hospital or encounter data.
- **Modeled estimate:** scenario calculation, not an observed outcome.
- **Validation required:** a decision that needs operational, clinical, financial, legal, privacy, or equity review.

The fictional system and synthetic records prevent disclosure of protected health information. This portfolio is not patient-care decision support.

### Important scoring note

The Executive Health Score, priority severity scores, and portfolio targets are **illustrative decision-support constructs**, not validated clinical scores or external performance benchmarks. A production implementation would require locally approved target definitions, certified measures, prospective validation, governance approval, and accountable executive/clinical ownership.

## Synthetic operating signals

The fixed-seed generator includes:

- Licensed and staffed beds
- Census, admissions, discharges, expected discharges, and pending admissions
- ED arrivals, boarding, ED-to-provider time, LWBS, and specialty wait
- Discharge-order-to-exit delay
- Readmission, mortality, falls, and HAI signals
- RN vacancy, productive hours, overtime, and agency hours
- Synthetic patient-experience composite
- OR cases and utilization
- Revenue, cost, and denials
- Synthetic encounters, transition barriers, SVI quartiles, deterioration, harm, and payer mix
- Synthetic privacy events

## Authoritative sources

- [CMS Provider Data Catalog](https://data.cms.gov/provider-data/topics/hospitals)
- [AHRQ Quality Indicators](https://qualityindicators.ahrq.gov/)
- [CDC/ATSDR Social Vulnerability Index](https://www.atsdr.cdc.gov/place-health/php/svi/)
- [HRSA Area Health Resources Files](https://data.hrsa.gov/topics/health-workforce/ahrf)
- [HHS OCR Breach Portal](https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf)

## Run locally

```bash
python generate_data.py
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The generated data use a fixed random seed, making the portfolio reproducible. The compressed data can be committed to the repository for fast Streamlit Community Cloud startup without a live API dependency.

## Limitations

- No real patient, claims, staffing, contract, or protected health information is included.
- Synthetic relationships demonstrate analytical workflow and should not be interpreted as causal estimates.
- Financial values are illustrative and do not represent a real health system.
- The patient-experience field is a synthetic portfolio composite and is **not an official HCAHPS score**.
- The modeled patient-flow funnel does not represent observed encounter-level timestamp transitions.
- Public sources are used for definitions and context; the packaged results are not direct hospital rankings.
- Production use would require enterprise data lineage, measure certification, prospective validation, bias review, security assessment, privacy review, and accountable clinical ownership.
