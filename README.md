# Clinical, Capacity, and Margin Intelligence Command Center

An executive healthcare analytics portfolio built for a fictional three-hospital Houston health system. The application connects quality, capacity, workforce, access, margin, equity, privacy, and intervention economics in one auditable Streamlit decision-support product.

## Why this is different

Most hospital dashboards report what already happened. This command center emphasizes what leadership should investigate next, which operational lever may change the result, how confident the evidence is, and what must be validated before action.

The application contains 14 analysis sheets, including dedicated demonstrations of:

- CIPP-informed privacy governance, minimum-necessary analytics, vendor risk, individual rights, and responsible analytics.
- CPHQ-informed statistical process control, Pareto prioritization, PDSA learning cycles, and reliability management.
- A CEO early-warning system linking clinical quality, capacity, and financial exposure.
- A patient-flow digital twin and intervention ROI laboratory.

## Evidence model

Every dashboard conclusion is identified as one of four types:

- **Public benchmark:** authoritative source or metric definition.
- **Synthetic result:** reproducible fictional hospital or encounter data.
- **Modeled estimate:** scenario calculation, not an observed outcome.
- **Validation required:** a decision that needs operational, clinical, financial, legal, privacy, or equity review.

The fictional system and synthetic records prevent disclosure of protected health information. This portfolio is not patient-care decision support.

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

The generated data use a fixed random seed, making the portfolio reproducible. The included compressed data allow fast Streamlit Community Cloud startup without a live API dependency.

## Limitations

- No real patient, claims, staffing, contract, or protected health information is included.
- Synthetic relationships demonstrate analytical workflow and should not be interpreted as causal estimates.
- Financial values are illustrative and do not represent a real health system.
- Public sources are used for definitions and context; the current packaged results are not direct hospital rankings.
- Production use would require enterprise data lineage, measure certification, prospective validation, bias review, security assessment, privacy review, and accountable clinical ownership.
