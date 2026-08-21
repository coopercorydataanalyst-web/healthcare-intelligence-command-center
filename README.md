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

Each of the 14 analytical sheets now includes a floating **Ask this visual** control. It remains fixed at the bottom center while the dashboard scrolls, avoiding Streamlit Cloud's lower-right management badge. The closed state is a small pill that does not interrupt the page layout; clicking it opens a compact, independently scrollable popover. The user selects the visual or section currently in view and can immediately ask:

- What is this visual telling me?
- What happened on this visual?
- What should I focus on, and why?
- What can I do to improve this result?
- What are the callouts or warnings?
- How is this calculated or encoded?
- What are the limitations?

Both the floating assistant and the dedicated Q&A sheet operate under one grounded data-analyst contract. Every rendered answer uses explicit **What**, **When**, **Where**, **How**, and **Why** sections. The When and Where sections are generated from the active date, hospital, and service-line filters; How identifies the predefined calculation or documented visual logic; Why explains why the descriptive conclusion follows from the shown figures while refusing to invent an unobserved cause. A visible constraint states that only filtered dashboard values and documented logic may be used, with no outside knowledge or extrapolation.

The **Why** section is evidence-based rather than a generic caveat. Structured visual answers use their specific arithmetic, ranks, component scores, or comparison facts; other visual answers build Why from the displayed supporting points. Causal, clinical, and validation boundaries remain visible separately as limitations.

The contextual catalog covers 26 visuals and sections across all 14 analytical pages. Granular interpretation is a dashboard-wide rule: when a user names content visible in the selected visual, the assistant explains that specific KPI, axis, score, table field, modeled input, callout, or governance component rather than repeating the entire visual description. Safe data-backed measures return the current filtered value, definition, hospital variation, calculation, evidence type, and metric-specific limitation. Modeled and documented content—including priority severity/exposure, funnel stages, outcome pressure, intervention value/cost/capacity/confidence/ROI, portfolio budget selection, evidence-readiness components, source registry fields, privacy exposure/severity, control limits, Pareto counts, and PDSA stages—returns its exact deterministic visual logic and appropriate evidence label. Improvement responses are predefined validation and process-improvement options—not generated clinical recommendations. Unsupported questions are refused rather than guessed.

Improvement questions are metric- and filter-aware. A request such as **“How can I improve the ER boarding?”** recognizes ER as ED, reports the current filtered value and threshold gap, identifies the hospital with the strongest pressure, brings in related filtered guardrails, assigns the appropriate executive role, and provides a validation-first time-bounded response sequence. A general question such as **“How can we improve this visual?”** selects the weakest safely scored metric within that visual. Recommendations remain predefined operating and validation pathways; they do not assert causality or prescribe patient care.

Composite and modeled visuals use the same contract. Their component measures are exposed to the improvement router, so **“How can I improve patient experience?”** on Executive Health Score by Domain follows the Patient Experience pathway instead of returning generic composite-score advice. Non-metric content has its own deterministic pathway for priority severity/exposure, intervention assumptions, evidence readiness, source lineage, privacy exposure, governance gates, SPC limits, Pareto barriers, and PDSA learning stages.

Composite-score answers explicitly reconcile display and source scales. For example, the Patient Experience bar may display **63/100** while the underlying filtered synthetic Patient Experience KPI is **76.8%**. The answer leads with the displayed 63/100, names the 76.8% input, and explains that the modeled score normalizes the KPI between illustrative lower and favorable references; the values are not presented as interchangeable.

Questions that name an Executive Health Score domain are resolved before similarly named metric aliases. For example, **"Why is Access so low?"** explains the displayed Access score and rank, then shows the raw LWBS and Specialty Wait values, their normalized component scores, and the unweighted domain calculation. The same domain-level pathway applies to Quality & Safety, Patient Flow, Financial, Workforce, and Patient Experience.

Multiple domains can be named in one question. For example, **"Why are Access and Patient Experience so low?"** returns both displayed scores and ranks, every underlying component, each normalized calculation, their position against the other domains, and the point difference between the two named domains. The router does not stop after the first matched domain.

The visual catalog also serves as an executable semantic contract. Every visual title is tested with punctuation and natural wording variants; every mapped metric is tested through all registered aliases wherever it appears; and every documented modeled or governance term is tested through all of its visible-name variants. Exact content documented for the selected visual takes precedence over broad dashboard synonyms, preventing a phrase such as **financial exposure** on the Priority Queue from being interpreted as Operating Margin. Every registered visual must include purpose, focus, action, callout, calculation, limitation, and a metric or documented-content mapping.

Contextual answers use an executive-readable layout rather than a dense paragraph. Improvement results show a short direct answer, a **What matters** bullet list, a numbered **What leadership should do** list, and one concise caution. Active filters are not repeated in the narrative because they remain visible on the dashboard. Evidence type, calculation, and the full limitation are available in a collapsed **Evidence, calculation, and limitations** section.

The selected scope appears once as a compact bold **Filters:** line. Full selections are summarized as **All Hospitals** and **All Service Lines**; subsets list only the selected values. Every bullet and numbered action is rendered on its own line with sentence capitalization for CEO-level scanning.

Named-entity position questions are data-aware. A question such as **“Why is GulfStar North so low?”** identifies the hospital in the selected visual, reports its actual plotted values and rank/comparison, explains size or encoding where supported, and separates the descriptive position from causal explanation. The assistant states what the chart shows, what leadership should validate, and what the available data cannot establish.

High, low, average, comparison, and outlier language is handled consistently across metric-backed visuals. On multi-axis charts, each axis is ranked independently, so a hospital can correctly be highest on one measure and in the middle on another. Multi-hospital questions return side-by-side current values and positions. Outlier questions identify relative separation within the selected peer group but do not call a point a statistically confirmed anomaly when the peer set is too small. “Why” answers describe the measured difference and provide validation steps without inventing an operational cause.

General explanation questions on hospital-comparison visuals also enumerate every selected hospital instead of returning only a portfolio average. The Deterioration-to-Harm Reliability Matrix additionally explains both axes and bubble size, reports hospital-level deterioration, harm, and encounter volume, and identifies each hospital's highest combined-pressure service line for validation-first follow-up.

Contextual Q&A state is versioned for Streamlit Cloud deployments. Browser sessions holding older widget or result structures are migrated automatically so a redeploy cannot fail with a stale `visual_qa` key or incompatible saved-result shape.

The footer displays the active dashboard build identifier, allowing the deployed Streamlit instance to be reconciled with the expected release. Both Q&A surfaces include a clear-answer control so a user can discard a persisted response immediately after a semantic or formatting update.

Modeled funnel-stage questions use the actual selected scenario math. Questions about Modeled Delayed Placements report the count, share of admissions, complementary within-target count, boarding-pressure input, formula, and the fact that discharges are a separate operating total rather than the next patient-level subset.

Every displayed funnel stage now has its own interpretation: ED Arrivals, Admissions, Bed Placement Within Portfolio Target, Modeled Delayed Placements, and Discharges. High/low/why questions use the correct count, denominator, evidence label, stage relationship, and cohort limitation instead of returning generic focus guidance.

### Service-line filter behavior

The service-line control now recalculates the operational dashboard, not only encounter-based readmission results. Because the source operations table is hospital-day grain, the app uses a deterministic synthetic allocation layer for service-line capacity, demand, census, flow intervals, quality events, staffing, labor, experience, procedural activity, revenue, cost, and denials. Selecting all service lines reconciles exactly to the original hospital-day portfolio; selecting a subset rolls only those modeled service-line components back into the KPI cards and visuals. The evidence bar labels this scope as a **Modeled Estimate**. Privacy events, source-governance facts, and intervention assumptions do not contain defensible service-line attribution and are explicitly labeled as not applicable rather than being silently changed.

The floating interaction is responsive: desktop popovers are capped at 430 pixels wide and 76% of viewport height, while the launcher uses tighter mobile spacing. The dedicated Ask GulfStar sheet remains available for broader cross-dashboard questions.

The closed launcher uses a translucent, blurred glass treatment so underlying visuals remain visible. Hovering increases contrast slightly, and opening the popover changes the launcher to solid green to communicate its active state.

Visual explanations are data-aware where a deterministic interpretation is defined. For example, the Executive Health Score by Domain answer reads the six current bars, names the leaders and weakest domain, quantifies the point gap, connects the scores to current filtered component metrics, and explains that the 0–100 value is a normalized modeled distance—not a percent success or failure.

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
