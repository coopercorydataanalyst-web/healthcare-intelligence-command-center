# Ask GulfStar Intelligence — Implementation Notes

## Design

The Q&A feature is a deterministic, read-only semantic layer. It does not call an LLM, send data off-device, execute generated code, or accept arbitrary dataframe expressions. `qa_engine.py` maps known phrases to a fixed metric dictionary and a fixed set of pandas aggregations.

The UI is Analysis Sheet 15 in `app.py`. It passes only the currently filtered operational and encounter frames, the dashboard's comparable prior-period frames, the intervention scenario table, and the existing priority queue into the query engine.

## Supported intents

- Compare selected hospitals on one or more supported measures
- Explain the dashboard, its scope, major analysis areas, Q&A behavior, and guardrails
- Answer overview/help language such as “Tell me about this dashboard” and “What can I ask?” without pretending a metric calculation occurred
- Rank hospitals by highest/lowest (and metric-aware best/worst)
- Return current-period values for a named hospital
- Compare the active period with its immediately preceding equal-length period
- Compare the latest N days with the preceding N days, bounded by the active filter
- Rank intervention scenarios by modeled ROI
- Explain the mechanical reason for the #1 executive priority without claiming causality
- Identify the highest or lowest modeled priority exposure
- Summarize positive changes and leadership wins
- Summarize negative changes and leadership concerns
- Produce an executive summary of leading improvements, concerns, stable signals, and the #1 modeled portfolio priority
- Produce a recent trend summary from broad language such as “What changed this month?”
- Refuse unsupported or ambiguous questions and suggest answerable examples

Broad executive questions default to the latest 30 days versus the preceding 30 days within the active filter. An explicit “last N days” request uses two equal N-day windows. Each supporting row displays the current value, prior value, change, direction, and metric calculation. Cross-metric ordering uses proportional movement so unlike units are not ranked by raw magnitude.

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

## Contextual visual Q&A

Every analytical sheet includes a fixed bottom-center **Ask this visual** launcher. The centered placement avoids Streamlit Cloud's lower-right management badge. It stays available while the page scrolls and opens a compact popover on demand, preventing the full Q&A form from taking permanent dashboard space. A required visual/section selector removes ambiguity when a sheet contains multiple charts, cards, tables, funnels, or governance sections. The catalog currently covers 26 visual contexts across Sheets 1–14.

Within a multi-metric visual, the assistant now gives precedence to an explicitly named KPI. A question such as **“What does Patient Experience: 76.8% mean?”** receives a metric-level explanation rather than a generic summary of all Executive KPI Cards. The response includes the filtered value, metric definition, illustrative threshold relationship and modeled component score where available, selected-hospital high/low context, calculation, evidence label, and metric-specific limitation.

This precedence rule now applies across every analytical page and every cataloged visual. The semantic layer covers displayed capacity, flow, quality, harm, workforce, access, procedural, equity, financial, and encounter measures, plus documented modeled/governance content that is not a directly observed metric. The assistant never converts a modeled field or governance component into an observed result.

The global service-line filter now applies to the synthetic hospital-day operating layer through a deterministic service-line allocation. Q&A receives the same filtered and rolled-up operations frame as the visuals, so its answers reconcile with the selected service-line KPI cards. All-line selection reproduces original totals. Subset selection is labeled as a modeled allocation. Privacy, registry/governance, and intervention assumptions remain explicitly outside service-line attribution.

Improvement intent now uses a shared metric-specific executive response framework. It includes current result, active service-line/hospital/date scope, illustrative threshold gap, worst hospital concentration, related guardrail metrics, accountable executive role, validation checklist, bounded improvement options, monitoring plan, and a non-causal limitation. ER/ED language is normalized. When no metric is named, the assistant chooses the weakest safely scored metric mapped to the selected visual rather than returning generic advice.

The desktop popover is capped at 430 pixels wide and 76% of viewport height with independent vertical scrolling. The closed launcher is a small pill, and mobile screens use reduced edge spacing. The dedicated Sheet 15 remains unchanged for cross-dashboard questions.

The launcher is intentionally translucent while idle (`rgba` background plus backdrop blur), becomes slightly stronger on hover, and turns fully solid when clicked/focused or when Streamlit reports the popover as open.

Supported visual-question intents are:

- Meaning and “what happened”
- Current filtered signal, where a direct safe metric mapping exists
- What deserves attention and why
- Predefined improvement or validation response
- Callout/warning explanation
- Calculation, axes, legend, or encoding logic
- Limitations and appropriate trust

One question may combine several intents. The answer labels each requested part. Improvement guidance remains process- and validation-oriented, never a patient-care recommendation, and no visual relationship is described as causal.

### Flexible language handling

The deterministic parser uses local normalization, a bounded healthcare-dashboard vocabulary, common variant aliases, and cautious typo matching. It accepts natural shorthand and misspellings without sending text to an LLM. It recognizes families of meaning, positive movement, negative movement, action, focus/importance, callout, calculation, and limitation/trust language. Low-confidence or unsafe requests still use the refusal path.

For visuals with safely mapped metrics, positive and negative output questions compare the latest 30 filtered days with the preceding 30 filtered days. For visuals without a direct mapping, the assistant explains that it cannot safely label a movement positive or negative and directs the user to the documented focus and required validation.

### Closest-match suggestions

If no supported intent is sufficiently identified, the response shows the keywords extracted from the user's wording and the three closest supported questions. Ranking combines normalized token overlap, character-level phrase similarity, typo normalization, and additional weight for shared dashboard-domain concepts. All candidates come from fixed safe allowlists.

The user selects a candidate and explicitly clicks **Ask Selected Suggestion** or **Ask Selected Visual Suggestion**. Nothing is silently rewritten or run. This preserves human control while turning an uncertain request into an easy recovery path.

## Validation

- Python compilation passes for `app.py` and `qa_engine.py`.
- All 15 Streamlit analysis sheets execute without exceptions in the runtime harness, including contextual panels on Sheets 1–14.
- The Q&A submission form renders a hospital-ranking answer without exceptions.
- Focused tests cover all required example questions, every metric in the allowlist, unsupported-question refusal, filtered-out hospitals, ROI, priority, exposure, all 26 visual contexts, core visual questions, and combined visual intents.
