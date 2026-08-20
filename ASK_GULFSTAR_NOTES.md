# Ask GulfStar Intelligence — Implementation Notes

## Design

The Q&A feature is a deterministic, read-only semantic layer. It does not call an LLM, send data off-device, execute generated code, or accept arbitrary dataframe expressions. `qa_engine.py` maps known phrases to a fixed metric dictionary and a fixed set of pandas aggregations.

The UI is Analysis Sheet 15 in `app.py`. It passes only the currently filtered operational and encounter frames, the dashboard's comparable prior-period frames, the intervention scenario table, and the existing priority queue into the query engine.

## Supported intents

- Compare selected hospitals on one or more supported measures
- Rank hospitals by highest/lowest (and metric-aware best/worst)
- Return current-period values for a named hospital
- Compare the active period with its immediately preceding equal-length period
- Compare the latest N days with the preceding N days, bounded by the active filter
- Rank intervention scenarios by modeled ROI
- Explain the mechanical reason for the #1 executive priority without claiming causality
- Identify the highest or lowest modeled priority exposure
- Refuse unsupported or ambiguous questions and suggest answerable examples

## Supported measures

30-day readmission, mortality, falls, HAI, ED boarding, ED-to-provider time, LWBS, staffed-bed utilization, available staffed beds, RN vacancy, agency labor share, patient experience, operating margin, denial exposure, denial rate, OR utilization, and specialty wait.

## Evidence and guardrails

- Hospital performance answers are labeled **Synthetic Result**.
- Intervention ROI, priority, and exposure answers are labeled **Modeled Estimate**.
- Unsupported, unavailable, or out-of-filter requests are labeled **Validation Required**.
- Every answer reports its calculation and limitation.
- The engine never provides causal explanations; priority explanations describe sorting and scoring mechanics only.
- The UI keeps **Synthetic data only**, **No PHI**, and **Not patient-care decision support** visible.
- Intervention scenarios are system-level modeled inputs and are explicitly disclosed as unaffected by operational filters.

## Filter behavior

- Hospital and reporting-date filters apply to all hospital-performance questions.
- Service-line filters apply to encounter-based 30-day readmission questions.
- Last-N-day comparisons stay inside the selected date range.
- A named hospital excluded by the global filter is reported as excluded instead of being silently ignored.
- System-level intervention scenarios do not change with hospital, date, or service-line filters.

## Validation

- Python compilation passes for `app.py` and `qa_engine.py`.
- All 15 Streamlit analysis sheets execute without exceptions in the runtime harness.
- The Q&A submission form renders a hospital-ranking answer without exceptions.
- Focused tests cover all required example questions, every metric in the allowlist, unsupported-question refusal, filtered-out hospitals, ROI, priority, and exposure.
