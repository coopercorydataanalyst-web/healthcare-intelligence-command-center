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

The application contains 15 analysis sheets in total, including dedicated demonstrations of:

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
- **Ask GulfStar Intelligence**, a deterministic natural-language Q&A layer over the active dashboard filters

## Ask GulfStar Intelligence

Analysis Sheet 15 lets an end user ask supported plain-language questions without an external LLM, paid API, or API key. The local query layer maps intent and metric synonyms to an allowlist of pandas aggregations. Every answer displays:

- The direct answer and supporting hospital values
- The calculation or metric definition used
- The evidence type (Synthetic Result, Modeled Estimate, or Validation Required)
- A limitation statement and visible synthetic/no-PHI/not-patient-care guardrails

Supported intents include dashboard overview/help, hospital comparisons, highest/lowest metrics, current-period values, comparable prior-period changes, last-N-day changes within the selected date range, intervention ROI, executive priority rationale, modeled priority exposure, positive-change summaries, negative-change summaries, executive summaries, and trend summaries. Executive language includes “Tell me about this dashboard,” “What can I ask?”, “What improved?”, “What got worse?”, “Give me the good news,” “What changed this month?”, “What should the CEO know?”, and “What should leadership celebrate?” Supported measures include readmission, mortality, falls, HAI, ED boarding, ED-to-provider time, LWBS, staffed-bed utilization, available staffed beds, RN vacancy, agency labor share, patient experience, operating margin, denials and denial rate, OR utilization, and specialty wait.

Broad executive summaries default to the latest 30 filtered days compared with the preceding 30 filtered days. Explicit “last N days” questions use two equal N-day windows. Direction is determined from each metric’s documented higher/lower-is-better rule; values that round to no displayed change are labeled stable. Because dollars, counts, hours, days, and rates cannot be ranked directly, cross-metric summaries rank movements by proportional change.

Hospital and date filters apply to all Q&A results. The service-line filter applies to encounter-based readmission answers. Intervention scenarios are system-level modeled inputs and therefore do not change with hospital, service-line, or date filters. Unsupported or ambiguous questions are refused with examples rather than guessed.

### Contextual visual Q&A on every sheet

Each of the 14 analytical sheets now includes a floating **Ask this visual** control. It remains fixed in the lower-right corner while the dashboard scrolls. The closed state is a small pill that does not interrupt the page layout; clicking it opens a compact, independently scrollable popover. The user selects the visual or section currently in view and can immediately ask:

- What is this visual telling me?
- What happened on this visual?
- What should I focus on, and why?
- What can I do to improve this result?
- What are the callouts or warnings?
- How is this calculated or encoded?
- What are the limitations?

The contextual catalog covers 26 visuals and sections. Answers can combine multiple requested parts, use current filtered metric values where the selected visual has a direct safe metric mapping, and otherwise explain the documented visual logic. Improvement responses are predefined validation and process-improvement options—not generated clinical recommendations. Unsupported questions are refused rather than guessed.

The floating interaction is responsive: desktop popovers are capped at 430 pixels wide and 76% of viewport height, while the launcher uses tighter mobile spacing. The dedicated Ask GulfStar sheet remains available for broader cross-dashboard questions.

The local language layer normalizes conversational variants, common misspellings, shorthand, tense changes, and chart synonyms without an external model. For example, “anything gud or positve,” “what is not working,” “any red flags,” “how can we make this better,” “why should I care,” “what stands out,” and “how did you get this number” map to distinct safe intents. Retrospective positive/negative questions use the latest 30 filtered days versus the preceding 30 days when the selected visual has a direct metric mapping; forward-looking improvement questions return predefined process and validation options.

When intent remains uncertain, the dashboard no longer stops at a generic refusal. It displays the meaningful keywords it extracted, ranks three close supported questions from a safe allowlist, and provides an **Ask Selected Suggestion** control. The end user—not the parser—chooses whether to run the proposed interpretation. Suggestions are ranked by normalized token overlap, cautious typo handling, phrase similarity, and shared dashboard-domain concepts; they never create arbitrary executable queries.

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
