from pathlib import Path
import re
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

st.set_page_config(
    page_title="Healthcare Intelligence Command Center",
    page_icon="✚",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAV = [
    "1 — CEO Executive Command Center",
    "2 — Patient Flow & Capacity Command Center",
    "3 — Clinical Deterioration & Rescue",
    "4 — Preventable Harm & Financial Exposure",
    "5 — Readmission Prevention",
    "6 — Workforce-to-Outcome Intelligence",
    "7 — Access Leakage & Lost Demand",
    "8 — Operating-Room & Procedural Yield",
    "9 — Health Equity & Geographic Opportunity",
    "10 — Payer, Denial & Margin Integrity",
    "11 — Intervention Portfolio & ROI Laboratory",
    "12 — Methods, Governance & Confidence",
    "13 — Privacy, Ethics & Responsible Analytics (CIPP)",
    "14 — Quality Improvement & Reliability Lab (CPHQ)",
]

CSS = """
<style>
:root{--navy:#082f49;--blue:#0369a1;--teal:#0f766e;--ink:#172033;--muted:#526071;--bg:#f4f8fb;--red:#b91c1c;--amber:#b45309}
.stApp{background:var(--bg);color:var(--ink)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#082f49,#123c55)}
[data-testid="stSidebar"] *{color:#fff}
[data-testid="stSidebar"] input,[data-testid="stSidebar"] textarea{color:#172033!important;background:#fff!important}
[data-testid="stSidebar"] [data-baseweb="select"]>div{background:#fff!important;color:#172033!important}
[data-testid="stSidebar"] [data-baseweb="select"] *{color:#172033!important}
[data-testid="stSidebar"] [data-baseweb="tag"]{background:#0f766e!important}
[data-testid="stSidebar"] [data-baseweb="tag"] *{color:#fff!important}
[data-testid="stSidebar"] [data-baseweb="tag"] svg{fill:#fff!important;color:#fff!important}
.hero{padding:28px 34px;border-radius:22px;background:linear-gradient(120deg,#082f49,#0369a1 68%,#0f766e);color:#fff;margin-bottom:18px}
.hero h1{font-size:2.15rem;margin:0 0 8px}.hero p{font-size:1.02rem;margin:0;color:#e8f6fb}
.badge{display:inline-block;padding:5px 10px;border-radius:99px;background:#dff5ef;color:#07594f;font-weight:700;font-size:.75rem;margin:4px 5px 4px 0}
.badge.synthetic{background:#fff1cc;color:#704b00}.badge.model{background:#e7e9ff;color:#3730a3}.badge.validate{background:#fee2e2;color:#991b1b}
.kpi{background:#fff;border:1px solid #d8e2ea;border-radius:16px;padding:18px;min-height:130px;box-shadow:0 5px 18px rgba(8,47,73,.06)}
.kpi .label{color:#526071;font-weight:700;font-size:.84rem}.kpi .value{color:#082f49;font-size:1.7rem;font-weight:800;margin:7px 0}.kpi .note{color:#526071;font-size:.76rem}
.insight{background:#e8f5f3;border-left:6px solid #0f766e;border-radius:12px;padding:16px 18px;margin:14px 0;color:#17313a}
.warning{background:#fff4df;border-left-color:#d97706}.risk{background:#feecec;border-left-color:#b91c1c}
.sourcebar{background:#fff;border:1px solid #d8e2ea;border-radius:12px;padding:10px 14px;margin-bottom:14px;color:#445366;font-size:.82rem}
.brief{background:#fff;border:1px solid #d8e2ea;border-radius:16px;padding:18px 20px;margin:10px 0 16px;box-shadow:0 4px 14px rgba(8,47,73,.05)}
.priority{background:#fff;border:1px solid #d8e2ea;border-radius:14px;padding:14px 16px;margin:8px 0}
.priority .rank{font-size:.75rem;font-weight:800;color:#526071}.priority .name{font-size:1.02rem;font-weight:800;color:#082f49}
.priority .meta{font-size:.80rem;color:#526071;margin-top:5px}
h1,h2,h3{color:#082f49!important}.stTabs [data-baseweb="tab"]{font-weight:700}
[data-testid="stDataFrame"]{border:1px solid #d8e2ea;border-radius:12px;overflow:hidden}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data
def load():
    d = pd.read_csv(DATA / "daily_operations.csv.gz", parse_dates=["date"])
    e = pd.read_csv(DATA / "synthetic_encounters.csv.gz", parse_dates=["admit_date", "discharge_date"])
    p = pd.read_csv(DATA / "privacy_events.csv", parse_dates=["date"])
    return d, e, p, pd.read_csv(DATA / "interventions.csv"), pd.read_csv(DATA / "source_registry.csv")


d, e, p, iv, src = load()

with st.sidebar:
    st.markdown("## ✚ GulfStar Health")
    st.caption("Clinical, Capacity & Margin Intelligence")
    page = st.selectbox("Choose Analysis Sheet", NAV)
    st.markdown("### Global Reporting Controls")
    min_d, max_d = d.date.min().date(), d.date.max().date()
    default_start = max(pd.Timestamp(min_d), pd.Timestamp("2026-01-01")).date()
    date_range = st.date_input(
        "Reporting Date Range",
        (default_start, max_d),
        min_value=min_d,
        max_value=max_d,
    )
    hospitals = st.multiselect("Hospital(s)", sorted(d.hospital.unique()), default=sorted(d.hospital.unique()))
    services = st.multiselect("Service Line(s)", sorted(e.service_line.unique()), default=sorted(e.service_line.unique()))
    st.markdown("---")
    st.caption("Portfolio simulation • No PHI • Not patient-care decision support")

if not hospitals or not services:
    st.warning("Select at least one hospital and one service line to continue.")
    st.stop()

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start = end = pd.Timestamp(date_range)

fd = d[d.hospital.isin(hospitals) & d.date.between(start, end)].copy()
fe = e[e.hospital.isin(hospitals) & e.service_line.isin(services) & e.admit_date.between(start, end)].copy()
fp = p[p.hospital.isin(hospitals) & p.date.between(start, end)].copy()

period_days = max((end - start).days + 1, 1)
prior_end = start - pd.Timedelta(days=1)
prior_start = prior_end - pd.Timedelta(days=period_days - 1)
pdaily = d[d.hospital.isin(hospitals) & d.date.between(prior_start, prior_end)].copy()
penc = e[e.hospital.isin(hospitals) & e.service_line.isin(services) & e.admit_date.between(prior_start, prior_end)].copy()


def money(x):
    return f"${x:,.0f}"


def pct(x):
    return f"{100*x:.1f}%"


def delta_pts(current, prior):
    if prior is None or pd.isna(prior):
        return "n/a"
    return f"{100*(current-prior):+.1f} pts"


def title_label(value):
    text = str(value).replace("_", " ").strip()
    keep = {"ED","OR","ICU","CMS","AHRQ","CDC","HRSA","HHS","OCR","PHI","CIPP","CPHQ","PDSA","ROI","SVI","LWBS","Q4","UCL","LCL","HAI","RN"}
    minor = {"and","or","to","by","of","the","in","per","versus","with"}
    output, word_count, after_dash = [], 0, False
    for token in re.split(r"(\s+|—)", text):
        if not token:
            continue
        if token.isspace():
            output.append(token)
            continue
        if token == "—":
            output.append(token)
            after_dash = True
            continue
        pieces = re.split(r"([/-])", token)
        styled = []
        for piece in pieces:
            if piece in {"/", "-"}:
                styled.append(piece)
                continue
            bare = piece.strip("(),:;")
            prefix = piece[:len(piece)-len(piece.lstrip("("))]
            suffix = piece[len(piece.rstrip("),:;")):]
            if bare.upper() in keep:
                core = bare.upper()
            elif bare.lower() in minor and word_count > 0 and not after_dash:
                core = bare.lower()
            else:
                core = bare[:1].upper() + bare[1:]
            styled.append(prefix + core + suffix)
            word_count += 1
            after_dash = False
        output.append("".join(styled))
    return "".join(output)


def hero(title, sub):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


def evidence():
    st.markdown(
        '<div class="sourcebar">'
        '<span class="badge">PUBLIC BENCHMARK</span>'
        '<span class="badge synthetic">SYNTHETIC RESULT</span>'
        '<span class="badge model">MODELED ESTIMATE</span>'
        '<span class="badge validate">VALIDATION REQUIRED</span>'
        f' Selected Range: <b>{start.strftime("%b %d, %Y")}–{end.strftime("%b %d, %Y")}</b>'
        '</div>',
        unsafe_allow_html=True,
    )


def cards(items):
    cols = st.columns(len(items))
    for c, (label, value, note) in zip(cols, items):
        c.markdown(
            f'<div class="kpi"><div class="label">{title_label(label)}</div>'
            f'<div class="value">{value}</div><div class="note">{title_label(note)}</div></div>',
            unsafe_allow_html=True,
        )


def callout(title, text, kind=""):
    st.markdown(f'<div class="insight {kind}"><b>{title_label(title)}</b><br>{text}</div>', unsafe_allow_html=True)


def plot(fig):
    for trace in fig.data:
        if getattr(trace, "name", None):
            trace.name = title_label(trace.name)
        if getattr(trace, "legendgroup", None):
            trace.legendgroup = title_label(trace.legendgroup)
    for axis in [fig.layout.xaxis, fig.layout.yaxis]:
        if axis.title and axis.title.text:
            axis.title.text = title_label(axis.title.text)
    fig.update_layout(
        template="plotly_white",
        font=dict(color="#172033"),
        title_font=dict(color="#082f49"),
        margin=dict(l=20, r=20, t=55, b=20),
        legend_title_text="",
    )
    st.plotly_chart(fig, use_container_width=True)


def table(df):
    shown = df.rename(columns={c: title_label(c) for c in df.columns})
    configs = {
        c: st.column_config.NumberColumn(format="%.1f")
        for c in shown.select_dtypes("number").columns
    }
    st.dataframe(shown, use_container_width=True, hide_index=True, column_config=configs)


def monthly(frame=None):
    x = fd if frame is None else frame
    if x.empty:
        return pd.DataFrame()
    agg = {
        "revenue":"sum","cost":"sum","admissions":"sum","ed_arrivals":"sum","census":"mean",
        "readmission_rate":"mean","mortality_rate":"mean","boarding_hours":"mean",
        "overtime_hours":"sum","denials":"sum","falls":"sum","hai":"sum"
    }
    return x.set_index("date").resample("MS").agg(agg).rename(columns={"ed_arrivals":"ed"}).reset_index()


def lower_is_better(value, target, bad):
    if pd.isna(value):
        return 50.0
    if value <= target:
        return 100.0
    if value >= bad:
        return 0.0
    return 100.0 * (bad - value) / (bad - target)


def higher_is_better(value, target, bad):
    if pd.isna(value):
        return 50.0
    if value >= target:
        return 100.0
    if value <= bad:
        return 0.0
    return 100.0 * (value - bad) / (target - bad)


def summarize(frame, encounters):
    if frame.empty:
        return {}
    revenue = frame.revenue.sum()
    cost = frame.cost.sum()
    staff = max(frame.staff_hours.sum(), 1)
    out = {
        "margin": (revenue-cost)/max(revenue,1),
        "occupancy": frame.census.sum()/max(frame.staffed_beds.sum(),1),
        "boarding": frame.boarding_hours.mean(),
        "readmission": frame.readmission_rate.mean(),
        "mortality": frame.mortality_rate.mean(),
        "overtime_share": frame.overtime_hours.sum()/staff,
        "denial_rate": frame.denials.sum()/max(revenue,1),
        "lwbs": frame.lwbs_rate.mean(),
        "wait": frame.specialty_wait_days.mean(),
        "experience": frame.patient_experience.mean() if "patient_experience" in frame else np.nan,
        "vacancy": frame.rn_vacancy_rate.mean() if "rn_vacancy_rate" in frame else np.nan,
        "agency_share": frame.agency_hours.sum()/staff if "agency_hours" in frame else np.nan,
        "discharge_delay": frame.discharge_order_to_exit_hours.mean() if "discharge_order_to_exit_hours" in frame else np.nan,
        "harm": encounters.harm.mean() if not encounters.empty else np.nan,
    }
    return out


def executive_domain_scores(summary):
    quality = np.mean([
        lower_is_better(summary["readmission"], .12, .18),
        lower_is_better(summary["mortality"], .020, .035),
        lower_is_better(summary["harm"], .020, .060),
    ])
    flow = np.mean([
        lower_is_better(summary["boarding"], 4.0, 10.0),
        lower_is_better(summary["occupancy"], .85, .98),
        lower_is_better(summary["discharge_delay"], 2.0, 5.0),
    ])
    finance = np.mean([
        higher_is_better(summary["margin"], .05, -.02),
        lower_is_better(summary["denial_rate"], .040, .075),
    ])
    workforce = np.mean([
        lower_is_better(summary["vacancy"], .08, .18),
        lower_is_better(summary["overtime_share"], .07, .16),
        lower_is_better(summary["agency_share"], .04, .10),
    ])
    access = np.mean([
        lower_is_better(summary["lwbs"], .02, .07),
        lower_is_better(summary["wait"], 10.0, 24.0),
    ])
    experience = higher_is_better(summary["experience"], .82, .68)
    return {
        "Quality & Safety": quality,
        "Patient Flow": flow,
        "Financial": finance,
        "Workforce": workforce,
        "Access": access,
        "Patient Experience": experience,
    }


def priority_queue():
    rows = []
    encounter_by_h = {h: g for h, g in fe.groupby("hospital")} if not fe.empty else {}
    for hospital, g in fd.groupby("hospital"):
        eg = encounter_by_h.get(hospital, pd.DataFrame())
        s = summarize(g, eg)
        rev = g.revenue.sum()
        staff = max(g.staff_hours.sum(), 1)
        readmission_count = int(eg.readmission_30d.sum()) if not eg.empty else 0
        harm_count = int(eg.harm.sum()) if not eg.empty else 0

        items = [
            ("Patient Flow", "COO", np.mean([
                100-lower_is_better(s["boarding"],4.0,10.0),
                100-lower_is_better(s["occupancy"],.85,.98),
                100-lower_is_better(s["discharge_delay"],2.0,5.0)
            ]), g.boarding_hours.mean()*g.admissions.sum()*220),
            ("Clinical Quality", "CMO / CNO", np.mean([
                100-lower_is_better(s["readmission"],.12,.18),
                100-lower_is_better(s["mortality"],.020,.035),
                100-lower_is_better(s["harm"],.020,.060)
            ]), readmission_count*14500 + harm_count*28000),
            ("Workforce", "CNO", np.mean([
                100-lower_is_better(s["vacancy"],.08,.18),
                100-lower_is_better(s["overtime_share"],.07,.16),
                100-lower_is_better(s["agency_share"],.04,.10)
            ]), g.overtime_hours.sum()*38 + (g.agency_hours.sum()*76 if "agency_hours" in g else 0)),
            ("Margin Integrity", "CFO", np.mean([
                100-higher_is_better(s["margin"],.05,-.02),
                100-lower_is_better(s["denial_rate"],.04,.075)
            ]), g.denials.sum()),
            ("Access", "COO / CMO", np.mean([
                100-lower_is_better(s["lwbs"],.02,.07),
                100-lower_is_better(s["wait"],10,24)
            ]), g.ed_arrivals.sum()*g.lwbs_rate.mean()*780),
            ("Patient Experience", "Chief Experience Officer", 100-higher_is_better(s["experience"],.82,.68), 0),
        ]
        for domain, owner, sev, exposure in items:
            urgency = "Critical" if sev >= 70 else "High" if sev >= 50 else "Watch" if sev >= 30 else "Stable"
            rows.append({
                "hospital": hospital,
                "domain": domain,
                "severity_score": round(float(sev),1),
                "urgency": urgency,
                "accountable_owner": owner,
                "modeled_exposure": round(float(exposure),0),
            })
    q = pd.DataFrame(rows).sort_values(["severity_score","modeled_exposure"], ascending=[False,False])
    q["rank"] = np.arange(1, len(q)+1)
    return q


def change_brief(current, prior):
    if not prior:
        return ["Prior-period comparison is unavailable for the selected range."]
    specs = [
        ("Operating margin", current["margin"], prior["margin"], True, "percentage points"),
        ("ED boarding", current["boarding"], prior["boarding"], False, "hours"),
        ("Readmission rate", current["readmission"], prior["readmission"], False, "percentage points"),
        ("RN vacancy", current["vacancy"], prior["vacancy"], False, "percentage points"),
        ("Patient experience", current["experience"], prior["experience"], True, "percentage points"),
        ("Denial rate", current["denial_rate"], prior["denial_rate"], False, "percentage points"),
    ]
    changes = []
    for label, cur, old, higher_good, unit in specs:
        if pd.isna(cur) or pd.isna(old):
            continue
        raw = cur-old
        display = raw if unit == "hours" else raw*100
        worsened = (raw < 0) if higher_good else (raw > 0)
        changes.append((abs(display), worsened, label, display, unit))
    if not changes:
        return ["No comparable prior-period signals are available."]
    worsening = sorted([x for x in changes if x[1]], reverse=True)[:2]
    improving = sorted([x for x in changes if not x[1] and x[0] > 0], reverse=True)[:2]
    lines = []
    if worsening:
        bits = [f"{x[2]} {'increased' if x[3] > 0 else 'decreased'} by {abs(x[3]):.1f} {x[4]}" for x in worsening]
        lines.append("Deteriorating: " + "; ".join(bits) + ".")
    if improving:
        bits = [f"{x[2]} {'increased' if x[3] > 0 else 'decreased'} by {abs(x[3]):.1f} {x[4]}" for x in improving]
        lines.append("Improving: " + "; ".join(bits) + ".")
    return lines or ["Signals were essentially stable versus the comparable prior period."]


# ---------------------------------------------------------------------
# 1 — CEO EXECUTIVE COMMAND CENTER
# ---------------------------------------------------------------------
if page.startswith("1 —"):
    hero(
        "CEO Executive Command Center",
        "A health-system operating view that answers what changed, where risk is concentrated, who owns the response, and what leadership should investigate next."
    )
    evidence()

    current = summarize(fd, fe)
    prior = summarize(pdaily, penc) if not pdaily.empty else {}
    domain_scores = executive_domain_scores(current)
    weights = {
        "Quality & Safety": .25,
        "Patient Flow": .20,
        "Financial": .20,
        "Workforce": .15,
        "Access": .10,
        "Patient Experience": .10,
    }
    health_score = int(round(sum(domain_scores[k]*weights[k] for k in weights)))
    integrity = int(np.clip(90 - 10*(len(fe)<100) - 6*(len(hospitals)<2) - 8*(period_days<30), 0, 100))
    staffed = fd.groupby(["date","hospital"]).staffed_beds.max().groupby("date").sum().mean()
    licensed = fd.groupby(["date","hospital"]).licensed_beds.max().groupby("date").sum().mean() if "licensed_beds" in fd else staffed
    available = max(staffed - fd.groupby("date").census.sum().mean(), 0)

    cards([
        ("Executive Health Score", f"{health_score}/100", "Modeled composite; portfolio weights"),
        ("Operating Margin", pct(current["margin"]), f"Prior period {pct(prior['margin']) if prior else 'n/a'}"),
        ("Staffed-Bed Utilization", pct(current["occupancy"]), f"{available:,.0f} average staffed beds available"),
        ("ED Boarding", f"{current['boarding']:.1f} hrs", f"Prior period {prior['boarding']:.1f} hrs" if prior else "No prior comparison"),
        ("Decision Integrity", f"{integrity}/100", "Evidence completeness and validation readiness"),
    ])

    cards([
        ("30-Day Readmission", pct(current["readmission"]), f"Prior {pct(prior['readmission'])}" if prior else "Synthetic result"),
        ("RN Vacancy", pct(current["vacancy"]), f"Prior {pct(prior['vacancy'])}" if prior else "Synthetic workforce signal"),
        ("Agency Labor Share", pct(current["agency_share"]), "Agency hours / productive hours"),
        ("Patient Experience", pct(current["experience"]), "Synthetic experience composite; not official HCAHPS"),
        ("Effective Capacity", f"{staffed:,.0f} / {licensed:,.0f}", "Average staffed / licensed beds"),
    ])

    q = priority_queue()
    topq = q.head(5)

    st.subheader("Executive Briefing — What Changed?")
    brief_lines = change_brief(current, prior)
    top = topq.iloc[0]
    action_line = (
        f"Highest current priority: {top['domain']} at {top['hospital']} "
        f"(severity {top['severity_score']:.0f}/100; accountable owner: {top['accountable_owner']})."
    )
    st.markdown(
        '<div class="brief"><b>Leadership readout</b><br>' +
        "<br>".join(brief_lines + [action_line]) +
        "<br><br><span class='badge model'>MODELED ESTIMATE</span> "
        "Priority scores rank synthetic portfolio signals; they are not clinical risk scores or validated forecasts.</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1.15, 1])
    with c1:
        score_df = pd.DataFrame({"domain":domain_scores.keys(),"score":domain_scores.values()}).sort_values("score")
        plot(px.bar(
            score_df, x="score", y="domain", orientation="h", range_x=[0,100],
            title="Executive Health Score by Domain", text_auto=".0f",
            color="score", color_continuous_scale="RdYlGn"
        ))
    with c2:
        m = monthly()
        fig = go.Figure()
        fig.add_bar(x=m.date, y=m.revenue-m.cost, name="Operating Contribution", marker_color="#0f766e")
        fig.add_scatter(x=m.date, y=m.boarding_hours*100000, name="Boarding Pressure (Indexed)", line=dict(color="#d97706",width=3))
        fig.update_layout(title="Margin and Flow Pressure by Month", yaxis_title="Dollars / Indexed Pressure")
        plot(fig)

    st.subheader("Executive Priority Queue")
    pq_cols = st.columns([1,1])
    for idx, (_, row) in enumerate(topq.iterrows()):
        with pq_cols[idx % 2]:
            st.markdown(
                f'<div class="priority"><div class="rank">PRIORITY #{int(row["rank"])} • {row["urgency"].upper()}</div>'
                f'<div class="name">{row["domain"]} — {row["hospital"]}</div>'
                f'<div class="meta">Severity: <b>{row["severity_score"]:.0f}/100</b> • Owner: <b>{row["accountable_owner"]}</b> '
                f'• Modeled exposure: <b>{money(row["modeled_exposure"])}</b></div></div>',
                unsafe_allow_html=True,
            )

    with st.expander("View full priority queue and scoring assumptions"):
        table(q[["rank","hospital","domain","severity_score","urgency","accountable_owner","modeled_exposure"]])
        st.caption(
            "Portfolio targets used for prioritization are illustrative, not external clinical benchmarks. "
            "The score combines currently available synthetic signals. Production deployment would require "
            "certified metric definitions, clinical/operational ownership, prospective validation, and local targets."
        )

    callout(
        "CEO Action",
        f"Start with {top['domain']} at {top['hospital']}. Assign {top['accountable_owner']} as the executive owner, "
        "validate the underlying timestamps/denominators and operating context, then move the intervention into a time-bounded PDSA cycle. "
        f"Current decision-integrity score: {integrity}/100.",
        "warning" if top["severity_score"] < 70 else "risk",
    )

# ---------------------------------------------------------------------
# 2 — PATIENT FLOW & CAPACITY
# ---------------------------------------------------------------------
elif page.startswith("2 —"):
    hero(
        "Patient Flow & Capacity Command Center",
        "Follow demand from ED arrival through admission and discharge, quantify effective staffed capacity, and test how throughput changes release bed-days."
    )
    evidence()

    discharge_gain = st.slider("What-if: reduction in discharge-order-to-exit delay", 0, 30, 12, 1, format="%d%%")
    staffed = fd.groupby(["date","hospital"]).staffed_beds.max().groupby("date").sum().mean()
    licensed = fd.groupby(["date","hospital"]).licensed_beds.max().groupby("date").sum().mean() if "licensed_beds" in fd else staffed
    census = fd.groupby("date").census.sum().mean()
    available = max(staffed-census,0)
    released = int(census * discharge_gain/100 * 365)
    pending = fd.pending_admissions.mean() if "pending_admissions" in fd else np.nan
    discharge_delay = fd.discharge_order_to_exit_hours.mean() if "discharge_order_to_exit_hours" in fd else np.nan

    cards([
        ("Average Daily Census", f"{census:,.0f}", "Synthetic result"),
        ("Effective Staffed Capacity", f"{staffed:,.0f}", f"{licensed:,.0f} licensed beds"),
        ("Available Staffed Beds", f"{available:,.0f}", "Average staffed beds minus census"),
        ("ED Boarding", f"{fd.boarding_hours.mean():.1f} hrs", "Arrival-to-bed pressure"),
        ("Pending Admissions", f"{pending:,.1f}", "Synthetic daily queue"),
    ])
    cards([
        ("ED-to-Provider", f"{fd.ed_to_provider_minutes.mean():.0f} min" if "ed_to_provider_minutes" in fd else "n/a", "Synthetic operational interval"),
        ("Discharge Order-to-Exit", f"{discharge_delay:.1f} hrs", "Synthetic throughput interval"),
        ("Expected Discharges", f"{fd.expected_discharges.mean():,.0f}" if "expected_discharges" in fd else "n/a", "Synthetic daily estimate"),
        ("Annualized Bed-Days Released", f"{released:,}", "Modeled what-if"),
        ("LWBS Rate", pct(fd.lwbs_rate.mean()), "Patients leaving before service"),
    ])

    h = fd.groupby("hospital").agg(
        census=("census","mean"),
        staffed_beds=("staffed_beds","mean"),
        licensed_beds=("licensed_beds","mean"),
        boarding_hours=("boarding_hours","mean"),
        ed_arrivals=("ed_arrivals","sum"),
        admissions=("admissions","sum"),
        discharges=("discharges","sum"),
        expected_discharges=("expected_discharges","mean"),
        pending_admissions=("pending_admissions","mean"),
        discharge_delay=("discharge_order_to_exit_hours","mean"),
    ).reset_index()
    h["occupancy"] = h.census/h.staffed_beds
    h["available_staffed_beds"] = h.staffed_beds-h.census
    h["discharge_reliability"] = h.discharges/np.maximum(h.admissions,1)

    c1, c2 = st.columns(2)
    with c1:
        plot(px.bar(
            h, x="hospital", y="occupancy", color="boarding_hours",
            title="Occupancy and Boarding by Hospital", text_auto=".1%",
            labels={"occupancy":"Staffed-bed occupancy","boarding_hours":"Boarding hours"}
        ))
    with c2:
        plot(px.scatter(
            h, x="discharge_delay", y="boarding_hours", size="ed_arrivals", color="hospital",
            title="Discharge Delay and ED Boarding",
            labels={"discharge_delay":"Discharge order-to-exit hours","boarding_hours":"ED boarding hours"}
        ))

    st.subheader("Patient-Flow Operating Matrix")
    flow_table = h[[
        "hospital","staffed_beds","licensed_beds","census","available_staffed_beds","occupancy",
        "pending_admissions","boarding_hours","discharge_delay","discharge_reliability"
    ]].copy()
    table(flow_table)

    # A modeled funnel: delayed placement is explicitly estimated, not claimed as observed.
    admissions = int(fd.admissions.sum())
    delayed_share = np.clip((fd.boarding_hours.mean()-4)/8, 0, .55)
    delayed = int(admissions*delayed_share)
    within_target = admissions-delayed
    funnel = pd.DataFrame({
        "stage":["ED arrivals","Admissions","Bed placement within portfolio target","Modeled delayed placements","Discharges"],
        "count":[int(fd.ed_arrivals.sum()),admissions,within_target,delayed,int(fd.discharges.sum())],
        "evidence":["Synthetic","Synthetic","Modeled estimate","Modeled estimate","Synthetic"],
    })
    plot(px.funnel(funnel, x="count", y="stage", title="System Patient-Flow Funnel (Modeled Placement Split)"))

    callout(
        "Operational Action",
        f"A {discharge_gain}% reduction in discharge-order-to-exit delay is modeled to release {released:,} annualized bed-days. "
        "The placement split in the funnel is a scenario estimate derived from average boarding pressure—not an observed timestamp measure. "
        "Validate encounter-level bed request, bed-ready, placement, discharge-order, and exit timestamps before setting operational targets.",
        "warning",
    )

elif page.startswith("3 —"):
    hero("Clinical Deterioration & Rescue Reliability","Move from retrospective mortality reporting to early rescue-system surveillance."); evidence()
    rate=fe.deterioration.mean(); rescue=1-fe[fe.deterioration].harm.mean() if fe.deterioration.any() else 1
    cards([("Deterioration Signal",pct(rate),"Synthetic encounter result"),("Rescue Reliability",pct(rescue),"No recorded harm after deterioration"),("Observed Mortality",pct(fd.mortality_rate.mean()),"Synthetic operational result"),("Sepsis Cohort",f"{(fe.service_line=='Sepsis').sum():,}","Selected encounters")])
    g=fe.groupby(["hospital","service_line"]).agg(encounters=("encounter_id","count"),deterioration=("deterioration","mean"),harm=("harm","mean")).reset_index()
    plot(px.scatter(g,x="deterioration",y="harm",size="encounters",color="hospital",hover_name="service_line",title="Deterioration-to-Harm Reliability Matrix",labels={"deterioration":"Deterioration rate","harm":"Harm rate"}))
    callout("Clinical Action","Focus validation on high-deterioration, high-harm service lines. The model is for surveillance prioritization only; bedside escalation must remain governed by validated clinical protocols.","risk")

elif page.startswith("4 —"):
    hero("Preventable Harm & Financial Exposure","Translate safety events into patient impact, capacity loss, and avoidable cost without reducing quality to dollars alone."); evidence()
    harm=fe.harm.sum(); exposure=harm*28000+fd.hai.sum()*47000+fd.falls.sum()*18000
    cards([("Patients with Harm Signal",f"{harm:,}","Synthetic encounters"),("Hospital-Acquired Infections",f"{fd.hai.sum():,}","Synthetic event count"),("Falls",f"{fd.falls.sum():,}","Synthetic event count"),("Modeled Financial Exposure",money(exposure),"Illustrative—not booked loss")])
    by=fe.groupby("service_line").agg(encounters=("encounter_id","count"),harm=("harm","sum"),cost=("cost","sum")).reset_index(); by["harm_rate"]=by.harm/by.encounters
    plot(px.bar(by.sort_values("harm_rate"),x="harm_rate",y="service_line",orientation="h",color="cost",title="Harm Signal by Service Line",labels={"harm_rate":"Harm rate"}))
    callout("Quality Action","Prioritize the service line with the largest combination of harm rate and volume, then verify event definitions and denominator integrity before assigning accountability.")

elif page.startswith("5 —"):
    hero("Readmission Prevention & Transition Command Center","Identify transition failures that create avoidable returns—and the patients most likely to benefit from intervention."); evidence()
    r=fe.readmission_30d.mean(); gap=fe.groupby("svi_quartile").readmission_30d.mean(); equity=(gap.max()-gap.min()) if len(gap)>1 else 0
    cards([("30-Day Readmission",pct(r),"Synthetic selected cohort"),("Follow-Up Booked",pct(fe.followup_booked.mean()),"Transition reliability"),("Observed Difference",f"{100*equity:.1f} pts","Highest vs lowest SVI quartile"),("Modeled Avoidable Cost",money(fe.readmission_30d.sum()*14500),"Illustrative exposure")])
    g=fe.groupby(["service_line","discharge_barrier"]).agg(n=("encounter_id","count"),readmission=("readmission_30d","mean")).reset_index()
    plot(px.scatter(g,x="n",y="readmission",size="n",color="discharge_barrier",facet_col="service_line",facet_col_wrap=3,title="Readmission Risk by Service Line and Discharge Barrier"))
    callout("Transition Action","Route high-risk heart failure and COPD discharges with transportation, medication, or caregiver barriers to a transition nurse and confirmed follow-up. Treat group differences as observed differences until statistical and operational review supports an equity conclusion.")

elif page.startswith("6 —"):
    hero("Workforce-to-Outcome Intelligence","Connect labor deployment to outcomes and throughput—without treating staffing as a simple cost-cutting exercise."); evidence()
    fd["hours_per_patient_day"]=fd.staff_hours/fd.census
    fd["outcome_pressure"]=fd.readmission_rate+fd.mortality_rate+fd.falls/np.maximum(fd.census,1)
    agency_share=fd.agency_hours.sum()/max(fd.staff_hours.sum(),1) if "agency_hours" in fd else np.nan
    cards([("Hours per Patient Day",f"{fd.hours_per_patient_day.mean():.1f}","Synthetic staffing result"),("RN Vacancy",pct(fd.rn_vacancy_rate.mean()) if "rn_vacancy_rate" in fd else "n/a","Synthetic workforce signal"),("Agency Share",pct(agency_share),"Agency / productive hours"),("Overtime Share",pct(fd.overtime_hours.sum()/fd.staff_hours.sum()),"Overtime / productive hours"),("Labor Cost Proxy",money(fd.staff_hours.sum()*58 + (fd.agency_hours.sum()*76 if "agency_hours" in fd else 0)),"Modeled loaded labor cost")])
    plot(px.scatter(fd,x="hours_per_patient_day",y="outcome_pressure",color="hospital",trendline="ols",title="Staffing Intensity Versus Composite Outcome Pressure",labels={"hours_per_patient_day":"Hours per patient day","outcome_pressure":"Outcome pressure index"}))
    callout("Workforce Action","Use the relationship to identify where staffing redesign may help; do not infer causality or reduce staffing solely from the trend. Acuity, skill mix, contract labor, vacancies, and unit-level assignments require validation.","warning")

elif page.startswith("7 —"):
    hero("Access Leakage & Lost Patient Demand","Quantify when demand is lost before care begins—and where capacity or navigation can recover it."); evidence()
    lost=int(fd.ed_arrivals.sum()*fd.lwbs_rate.mean()); value=lost*780
    cards([("ED Arrivals",f"{fd.ed_arrivals.sum():,}","Synthetic demand"),("Left Without Being Seen",f"{lost:,}","Modeled from daily rate"),("Specialty Wait",f"{fd.specialty_wait_days.mean():.1f} days","Synthetic access result"),("Recoverable Value",money(value),"Illustrative gross revenue")])
    g=fd.groupby("hospital").agg(arrivals=("ed_arrivals","sum"),lwbs=("lwbs_rate","mean"),wait=("specialty_wait_days","mean"),boarding=("boarding_hours","mean")).reset_index()
    plot(px.bar(g,x="hospital",y=["lwbs","wait"],barmode="group",title="Access Leakage Signals by Hospital"))
    callout("Access Action","Start with ED fast track and centralized specialty scheduling at the hospital with the highest combined LWBS, boarding, and wait-day signal.")

elif page.startswith("8 —"):
    hero("Operating-Room & Procedural Yield","Protect high-value procedural capacity by separating schedule volume, utilization, and contribution."); evidence()
    value=fd.or_cases.sum()*7400; unused=(1-fd.or_utilization.mean())*fd.or_cases.sum()*7400
    cards([("Procedural Cases",f"{fd.or_cases.sum():,}","Synthetic operations"),("OR Utilization",pct(fd.or_utilization.mean()),"Scheduled-room proxy"),("Gross Procedural Value",money(value),"Modeled contribution input"),("Unused Capacity Signal",money(unused),"Illustrative—not fully recoverable")])
    g=fd.groupby(["hospital",fd.date.dt.day_name()]).agg(cases=("or_cases","sum"),util=("or_utilization","mean")).reset_index(names=["hospital","day"])
    plot(px.scatter(g,x="cases",y="util",color="hospital",text="day",title="Procedural Volume and Utilization by Day"))
    callout("Procedural Action","Improve first-case-on-time reliability and rebalance low-utilization blocks before adding rooms. Surgeon availability and block ownership are not included.")

elif page.startswith("9 —"):
    hero("Health Equity & Geographic Opportunity","Reveal where barriers—not clinical need alone—shape outcomes and access."); evidence()
    eq=fe.groupby("svi_quartile").agg(encounters=("encounter_id","count"),readmission=("readmission_30d","mean"),followup=("followup_booked","mean"),cost=("cost","mean")).reset_index()
    q4=eq[eq.svi_quartile==4]
    cards([("High-Vulnerability Encounters",f"{(fe.svi_quartile==4).sum():,}","Synthetic, SVI-calibrated"),("Q4 Follow-Up",pct(q4.followup.mean()),"Highest vulnerability quartile"),("Q4 Readmission",pct(q4.readmission.mean()),"Synthetic result"),("Equity Evidence","68/100","No patient-level geocoding")])
    plot(px.bar(eq,x="svi_quartile",y=["readmission","followup"],barmode="group",title="Outcomes by Social Vulnerability Quartile"))
    callout("Equity Action","Pair navigation, transportation support, and language access with high-vulnerability transition pathways. Group-level differences are screening signals; do not use SVI to deny or deprioritize individual care.")

elif page.startswith("10 —"):
    hero("Payer, Denial & Margin Integrity","Show where earned revenue fails to become cash—and which clinical volumes carry unsustainable economics."); evidence()
    margin=fe.groupby(["payer","service_line"]).agg(revenue=("revenue","sum"),cost=("cost","sum"),encounters=("encounter_id","count")).reset_index(); margin["contribution"]=margin.revenue-margin.cost
    cards([("Gross Revenue",money(fd.revenue.sum()),"Synthetic operations"),("Denial Exposure",money(fd.denials.sum()),"Synthetic result"),("Denial Rate",pct(fd.denials.sum()/fd.revenue.sum()),"Denied / gross revenue"),("Encounter Contribution",money(fe.revenue.sum()-fe.cost.sum()),"Synthetic cohort")])
    plot(px.bar(margin,x="service_line",y="contribution",color="payer",barmode="group",title="Contribution by Service Line and Payer"))
    callout("Margin Action","Prioritize front-end authorization and documentation in negative-contribution payer/service combinations; validate contract terms and final adjudication before action.")

elif page.startswith("11 —"):
    hero("Intervention Portfolio & ROI Laboratory","Rank initiatives by value, feasibility, capacity release, confidence, and strategic fit—not ROI alone."); evidence()
    budget=st.slider("Available Annual Investment",100000,2000000,900000,50000,format="$%d")
    iv2=iv.copy(); iv2["net_value"]=iv2.annual_value-iv2.annual_cost; iv2["roi"]=iv2.net_value/iv2.annual_cost; iv2["priority_score"]=iv2.roi*iv2.confidence/100+iv2.capacity_days/3000
    chosen=iv2.sort_values("priority_score",ascending=False); chosen["cumulative_cost"]=chosen.annual_cost.cumsum(); selected=chosen[chosen.cumulative_cost<=budget]
    cards([("Portfolio Investment",money(selected.annual_cost.sum()),"Within selected budget"),("Modeled Annual Value",money(selected.annual_value.sum()),"Not guaranteed"),("Net Value",money(selected.net_value.sum()),"Value less program cost"),("Capacity Days",f"{selected.capacity_days.sum():,.0f}","Modeled release")])
    plot(px.scatter(iv2,x="annual_cost",y="annual_value",size="capacity_days",color="confidence",text="intervention",title="Intervention Value Frontier"))
    table(selected[["intervention","domain","annual_cost","annual_value","net_value","roi","confidence"]])
    callout("Portfolio Action",f"At a {money(budget)} ceiling, fund {len(selected)} initiatives as a staged portfolio. Release funding by milestone and re-estimate benefits after 90 days.")

elif page.startswith("12 —"):
    hero("Methods, Governance & Confidence","Make every executive conclusion auditable: source, lineage, metric definition, uncertainty, limitation, and validation status."); evidence()
    components={"Source authority":84,"Data completeness":90,"Metric definition":91,"Timeliness":82,"Causal confidence":54,"External validity":61}
    score=int(np.mean(list(components.values())))
    cards([("Decision Integrity Score",f"{score}/100","Composite—not model accuracy"),("Public Sources",f"{(src.evidence_type.str.contains('Public')).sum()}","Authoritative source registry"),("Synthetic Records",f"{len(fe):,}","Selected encounter simulation"),("Validation Gates","5","Clinical, finance, privacy, operations, equity")])
    plot(px.bar(pd.DataFrame({"component":components.keys(),"score":components.values()}),x="score",y="component",orientation="h",range_x=[0,100],title="Decision Integrity Components",color="score",color_continuous_scale="Teal"))
    st.subheader("Source and Evidence Registry"); table(src)
    callout("Governance Action","No recommendation should move from portfolio evidence to production decision support until source lineage, definitions, bias, prospective validation, security, and accountable ownership are approved.","warning")

elif page.startswith("13 —"):
    hero("Privacy, Ethics & Responsible Analytics — CIPP Lens","Operationalize privacy by design across access, analytics, vendors, incident response, and responsible AI."); evidence()
    minimum=st.slider("What-if: reduction in unnecessary access",0,80,35,5,format="%d%%")
    high=(fp.severity=="High").sum(); exposed=fp.records_affected.sum(); prevent=int(exposed*minimum/100)
    cards([("Privacy Events",f"{len(fp):,}","Synthetic operational events"),("High-Severity",f"{high:,}","Synthetic result"),("Records Affected",f"{exposed:,}","Not reportable-breach count"),("Preventable Exposure",f"{prevent:,}","Modeled what-if")])
    g=fp.groupby(["event_type","severity"]).records_affected.sum().reset_index()
    plot(px.bar(g,x="records_affected",y="event_type",color="severity",orientation="h",title="Privacy Risk by Event Type and Severity",color_discrete_map={"High":"#b91c1c","Moderate":"#d97706","Low":"#0f766e"}))
    st.subheader("CIPP-Informed Governance Gates")
    table(pd.DataFrame([
        ["Purpose limitation","Is the use consistent with the stated care or operational purpose?","Privacy Officer"],
        ["Minimum necessary","Are fields, users, and retention limited to what is required?","Data Owner"],
        ["Individual rights","Can access, correction, restriction, and accounting requests be supported?","Health Information Management"],
        ["Vendor governance","Are BAAs, subprocessors, security controls, and return/destruction terms verified?","Legal / Procurement"],
        ["Responsible analytics","Have bias, explainability, monitoring, and human override been designed?","Model Governance Committee"],
    ],columns=["gate","executive_question","accountable_owner"]))
    callout("Privacy Action",f"A {minimum}% reduction in unnecessary access is modeled to prevent exposure of {prevent:,} records. This is a scenario, not a breach determination; legal and privacy review remains required.")

else:
    hero("Quality Improvement & Reliability Lab — CPHQ Lens","Turn variation into disciplined improvement using control charts, Pareto prioritization, PDSA governance, and sustainment evidence."); evidence()
    measure=st.selectbox("Quality Measure",["readmission","mortality","boarding","falls","hai"],format_func=title_label)
    m=monthly()
    y=m[{"readmission":"readmission_rate","mortality":"mortality_rate","boarding":"boarding_hours","falls":"falls","hai":"hai"}[measure]].astype(float)
    mean=y.mean(); sd=y.std(ddof=1) if len(y)>1 else 0.0; sd=0.0 if pd.isna(sd) else sd; ucl=mean+3*sd; lcl=max(0,mean-3*sd)
    cards([("Selected Measure",measure.replace("_"," ").title(),"Synthetic result"),("Center Line",f"{mean:.3f}","Selected-range mean"),("Upper Control Limit",f"{ucl:.3f}","Three-sigma analytic limit"),("Special-Cause Months",f"{((y>ucl)|(y<lcl)).sum()}","Screening signal")])
    fig=go.Figure(); fig.add_scatter(x=m.date,y=y,mode="lines+markers",name=measure,line=dict(color="#0369a1",width=3)); fig.add_hline(y=mean,line_color="#0f766e",annotation_text="Center line"); fig.add_hline(y=ucl,line_dash="dash",line_color="#b91c1c",annotation_text="UCL"); fig.add_hline(y=lcl,line_dash="dash",line_color="#b91c1c",annotation_text="LCL"); fig.update_layout(title=f"Statistical Process Control: {measure.title()}"); plot(fig)
    pareto=fe.groupby("discharge_barrier").size().sort_values(ascending=False).reset_index(name="count"); pareto["cumulative_pct"]=pareto["count"].cumsum()/pareto["count"].sum()
    c1,c2=st.columns(2)
    with c1: plot(px.bar(pareto,x="discharge_barrier",y="count",title="Pareto: Discharge Barriers"))
    with c2:
        st.subheader("PDSA Learning System")
        table(pd.DataFrame([["Plan","Define aim, population, measure, prediction"],["Do","Test on small scale; document deviations"],["Study","Compare result with prediction; examine variation"],["Act","Adopt, adapt, or abandon; define next cycle"]],columns=["phase","evidence_required"]))
    callout("Quality Action","Treat points beyond limits as investigation signals, not proof of performance failure. Confirm denominator stability, coding changes, seasonality, and workflow context before intervention.")

st.markdown("---")
st.caption(
    "GulfStar Health System is fictional. Operational and patient-level results are synthetic and reproducible. "
    "Public agencies provide benchmark definitions and context. Portfolio targets and composite scores are illustrative. "
    "This portfolio demonstrates healthcare analytics leadership; it is not clinical, legal, privacy, or financial advice."
)
