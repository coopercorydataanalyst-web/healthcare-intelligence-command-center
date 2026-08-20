# Healthcare Dashboard Update Notes

## Files to replace
- `app.py`
- `qa_engine.py`
- `visual_qa.py`
- `language_utils.py`
- `test_qa_engine.py`
- `test_visual_qa.py`
- `ASK_GULFSTAR_NOTES.md`
- `generate_data.py`
- `data/daily_operations.csv.gz`
- `data/synthetic_encounters.csv.gz`
- `data/privacy_events.csv`
- `data/interventions.csv`
- `data/source_registry.csv`

You can also replace the repository README with `README_UPDATED.md` (rename it to `README.md`).

## Main changes
1. Rebuilt Analysis Sheet 1 as the CEO Executive Command Center.
2. Added an Executive Health Score with transparent portfolio weighting.
3. Added comparable prior-period change detection and an automated executive briefing.
4. Added a hospital/domain Executive Priority Queue with severity, accountable owner, and modeled exposure.
5. Added licensed vs staffed capacity, available staffed beds, RN vacancy, agency labor, and synthetic patient experience.
6. Rebuilt Analysis Sheet 2 as Patient Flow & Capacity Command Center.
7. Added pending admissions, expected discharges, ED-to-provider time, discharge-order-to-exit time, and capacity operating matrix.
8. Added a clearly labeled modeled patient-flow funnel.
9. Strengthened equity language so group differences are not automatically labeled disparities.
10. Preserved the remaining clinical, financial, governance, privacy, ROI, SPC, Pareto, and PDSA analysis sheets.
11. CEO-page polish: effectively-zero displayed changes now read as stable, priority cards render row-wise (#1/#2, #3/#4, #5), and the #1 item receives a stronger executive-priority treatment.
12. Sidebar accessibility polish: date, search, and multiselect entry fields now use the same high-contrast green background and white text as selected hospital and service-line chips.
13. Date-range repair: the control now defaults to the complete dataset range, resets stale out-of-range session values, remains bounded by the loaded data, and displays the available minimum and maximum dates.
14. Sidebar control repair: outer select and multiselect surfaces now use dark green with white text/icons on every page.
15. Streamlit Cloud compatibility repair: directly styles the newer `stDateInputField` control, restores white sidebar headings/captions, and versions the date widget key so an older browser-side selection cannot override the full-range default.
16. Added Analysis Sheet 15, **Ask GulfStar Intelligence**, with a deterministic local semantic/query layer and no external LLM or API-key requirement.
17. Added safe allowlisted hospital comparisons, highest/lowest queries, current values, prior/change queries, intervention ROI, executive priority rationale, and modeled exposure queries.
18. Added calculation transparency, evidence labels, limitations, unsupported-question refusal, filter-scope disclosure, and visible synthetic/no-PHI/not-patient-care guardrails.
19. Added focused automated tests for required example questions, every supported metric, filter exclusions, refusal behavior, and distinct priority/exposure logic.
20. Added executive-language intents: `positive_change`, `negative_change`, `executive_summary`, and `trend_summary`.
21. Added auditable 30-day default summaries and explicit last-N-day comparisons, with current/prior values, directional classification, metric calculations, evidence labels, and non-causal limitations.
22. Added proportional cross-metric ranking so unlike units are never compared by raw magnitude, plus stable-at-displayed-precision handling.
23. Made executive intent recognition tolerant of conversational tense and grammar variants, including the exact end-user wording `what has happen positively in last 30 days`.
24. Added a dashboard overview/help intent for questions such as `tell me about this dashboard`, `what does this dashboard do`, `what can I ask`, and `how does this dashboard work`.
25. Added an in-context **Ask About This Sheet** panel to every one of the 14 analytical sheets, while preserving the dedicated Ask GulfStar page.
26. Added deterministic coverage for 26 visuals and sections: meaning, current filtered signal, focus/importance, improvement response, callouts, calculation/encoding, and limitations.
27. Added multi-intent visual answers so one question can request explanation, focus, and improvement guidance together.
28. Added visual-context tests across every sheet, every cataloged visual, all core question types, combined questions, and unsupported-question refusal.
29. Added deterministic flexible-language normalization for common typos, tense changes, shorthand, chart synonyms, and executive paraphrases without an external model.
30. Added visual-level positive/negative movement interpretation using equal 30-day filtered windows when a safe metric mapping exists.
31. Distinguished retrospective improvement questions from forward-looking action questions and expanded support for “red flags,” “what is not working,” “why should I care,” “what stands out,” calculation, and trust language.
32. Replaced unsupported-question dead ends with keyword extraction and three similarity-ranked safe suggestions on both the dedicated Q&A page and contextual visual panels.
33. Added user-controlled **Ask Selected Suggestion** actions so the dashboard never silently rewrites or executes an uncertain interpretation.
34. Added dashboard-domain weighting to keep workforce, margin, quality, flow, access, privacy, equity, ROI, callout, calculation, and limitation suggestions relevant.
35. Replaced the full-width contextual Q&A section with a fixed lower-right **Ask this visual** launcher on all 14 analytical sheets.
36. Added a compact 430-pixel-wide, independently scrollable popover so users can ask while keeping the selected visual substantially visible; added responsive mobile positioning.
37. Visually verified fixed positioning, compact dimensions, popover scrolling, and non-expanded page layout in the running Streamlit application.

## Validation completed
- Python syntax compilation: passed.
- Streamlit runtime smoke-test harness: all 15 analysis sheets executed without exceptions.
- CEO-page assertions: priority ranks render in #1–#5 sequence, the #1 emphasis class is present, stable wording is present, and no directional `0.0` language is rendered.
- Q&A unit tests: all required examples, documented metrics, refusal paths, filter exclusions, modeled intents, executive-language summaries, and insufficient-window guardrails passed.
- Q&A form runtime: a submitted hospital-ranking question rendered an answer without exceptions.
- Contextual visual Q&A runtime: all 15 sheets executed without exceptions, and a submitted CEO-sheet visual question rendered current filtered signals.
