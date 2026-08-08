from pathlib import Path
import re
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT=Path(__file__).resolve().parent; DATA=ROOT/"data"
st.set_page_config(page_title="Healthcare Intelligence Command Center",page_icon="✚",layout="wide",initial_sidebar_state="expanded")

NAV=["1 — CEO Early-Warning Command Center","2 — Patient Flow Digital Twin","3 — Clinical Deterioration & Rescue",
"4 — Preventable Harm & Financial Exposure","5 — Readmission Prevention","6 — Workforce-to-Outcome Intelligence",
"7 — Access Leakage & Lost Demand","8 — Operating-Room & Procedural Yield","9 — Health Equity & Geographic Opportunity",
"10 — Payer, Denial & Margin Integrity","11 — Intervention Portfolio & ROI Laboratory","12 — Methods, Governance & Confidence",
"13 — Privacy, Ethics & Responsible Analytics (CIPP)","14 — Quality Improvement & Reliability Lab (CPHQ)"]

CSS="""
<style>
:root{--navy:#082f49;--blue:#0369a1;--teal:#0f766e;--ink:#172033;--muted:#526071;--bg:#f4f8fb;--lime:#84cc16;--red:#b91c1c}
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
.kpi .label{color:#526071;font-weight:700;font-size:.86rem}.kpi .value{color:#082f49;font-size:1.8rem;font-weight:800;margin:7px 0}.kpi .note{color:#526071;font-size:.78rem}
.insight{background:#e8f5f3;border-left:6px solid #0f766e;border-radius:12px;padding:16px 18px;margin:14px 0;color:#17313a}
.warning{background:#fff4df;border-left-color:#d97706}.risk{background:#feecec;border-left-color:#b91c1c}
.sourcebar{background:#fff;border:1px solid #d8e2ea;border-radius:12px;padding:10px 14px;margin-bottom:14px;color:#445366;font-size:.82rem}
h1,h2,h3{color:#082f49!important}.stTabs [data-baseweb="tab"]{font-weight:700}
[data-testid="stDataFrame"]{border:1px solid #d8e2ea;border-radius:12px;overflow:hidden}
</style>"""
st.markdown(CSS,unsafe_allow_html=True)

@st.cache_data
def load():
    d=pd.read_csv(DATA/"daily_operations.csv.gz",parse_dates=["date"])
    e=pd.read_csv(DATA/"synthetic_encounters.csv.gz",parse_dates=["admit_date","discharge_date"])
    p=pd.read_csv(DATA/"privacy_events.csv",parse_dates=["date"])
    return d,e,p,pd.read_csv(DATA/"interventions.csv"),pd.read_csv(DATA/"source_registry.csv")
d,e,p,iv,src=load()

with st.sidebar:
    st.markdown("## ✚ GulfStar Health")
    st.caption("Clinical, Capacity & Margin Intelligence")
    page=st.selectbox("Choose Analysis Sheet",NAV)
    st.markdown("### Global Reporting Controls")
    min_d,max_d=d.date.min().date(),d.date.max().date()
    date_range=st.date_input("Reporting Date Range",(pd.Timestamp("2026-01-01").date(),max_d),min_value=min_d,max_value=max_d)
    hospitals=st.multiselect("Hospital(s)",sorted(d.hospital.unique()),default=sorted(d.hospital.unique()))
    services=st.multiselect("Service Line(s)",sorted(e.service_line.unique()),default=sorted(e.service_line.unique()))
    st.markdown("---")
    st.caption("Portfolio simulation • No PHI • Not patient-care decision support")

start,end=(pd.Timestamp(date_range[0]),pd.Timestamp(date_range[-1]))
fd=d[d.hospital.isin(hospitals)&d.date.between(start,end)].copy()
fe=e[e.hospital.isin(hospitals)&e.service_line.isin(services)&e.admit_date.between(start,end)].copy()
fp=p[p.hospital.isin(hospitals)&p.date.between(start,end)].copy()

def money(x): return f"${x:,.0f}"
def pct(x): return f"{100*x:.1f}%"
def title_label(value):
    """Professional title case for short UI labels while preserving key acronyms."""
    text=str(value).replace("_"," ").strip()
    keep={"ED","OR","ICU","CMS","AHRQ","CDC","HRSA","HHS","OCR","PHI","CIPP","CPHQ","PDSA","ROI","SVI","LWBS","Q4","UCL","LCL","HAI"}
    minor={"and","or","to","by","of","the","in","per","versus","with"}
    output=[]; word_count=0; after_dash=False
    for token in re.split(r"(\s+|—)",text):
        if not token: continue
        if token.isspace(): output.append(token); continue
        if token=="—": output.append(token); after_dash=True; continue
        pieces=re.split(r"([/-])",token)
        styled=[]
        for piece in pieces:
            if piece in {"/","-"}: styled.append(piece); continue
            bare=piece.strip("(),:;")
            prefix=piece[:len(piece)-len(piece.lstrip("("))]
            suffix=piece[len(piece.rstrip("),:;")):]
            if bare.upper() in keep: core=bare.upper()
            elif bare.lower() in minor and word_count>0 and not after_dash: core=bare.lower()
            else: core=bare[:1].upper()+bare[1:]
            styled.append(prefix+core+suffix); word_count+=1; after_dash=False
        output.append("".join(styled))
    return "".join(output)
def hero(title,sub): st.markdown(f'<div class="hero"><h1>{title}</h1><p>{sub}</p></div>',unsafe_allow_html=True)
def evidence():
    st.markdown('<div class="sourcebar"><span class="badge">PUBLIC BENCHMARK</span><span class="badge synthetic">SYNTHETIC RESULT</span><span class="badge model">MODELED ESTIMATE</span><span class="badge validate">VALIDATION REQUIRED</span> Selected Range: <b>'+start.strftime('%b %d, %Y')+'–'+end.strftime('%b %d, %Y')+'</b></div>',unsafe_allow_html=True)
def cards(items):
    cs=st.columns(len(items))
    for c,(label,value,note) in zip(cs,items):
        c.markdown(f'<div class="kpi"><div class="label">{title_label(label)}</div><div class="value">{value}</div><div class="note">{title_label(note)}</div></div>',unsafe_allow_html=True)
def callout(title,text,kind=""):
    st.markdown(f'<div class="insight {kind}"><b>{title_label(title)}</b><br>{text}</div>',unsafe_allow_html=True)
def plot(fig):
    for trace in fig.data:
        if getattr(trace,"name",None): trace.name=title_label(trace.name)
        if getattr(trace,"legendgroup",None): trace.legendgroup=title_label(trace.legendgroup)
    for axis in [fig.layout.xaxis,fig.layout.yaxis]:
        if axis.title and axis.title.text: axis.title.text=title_label(axis.title.text)
    if fig.layout.coloraxis and fig.layout.coloraxis.colorbar and fig.layout.coloraxis.colorbar.title and fig.layout.coloraxis.colorbar.title.text:
        fig.layout.coloraxis.colorbar.title.text=title_label(fig.layout.coloraxis.colorbar.title.text)
    fig.update_layout(template="plotly_white",font=dict(color="#172033"),title_font=dict(color="#082f49"),margin=dict(l=20,r=20,t=55,b=20),legend_title_text="")
    st.plotly_chart(fig,use_container_width=True)
def table(df):
    shown=df.rename(columns={c:title_label(c) for c in df.columns})
    st.dataframe(shown,use_container_width=True,hide_index=True,column_config={c:st.column_config.NumberColumn(format="%.1f") for c in shown.select_dtypes("number").columns})
def monthly():
    return fd.set_index("date").resample("MS").agg(revenue=("revenue","sum"),cost=("cost","sum"),admissions=("admissions","sum"),ed=("ed_arrivals","sum"),census=("census","mean"),readmission=("readmission_rate","mean"),mortality=("mortality_rate","mean"),boarding=("boarding_hours","mean"),overtime=("overtime_hours","sum"),denials=("denials","sum"),falls=("falls","sum"),hai=("hai","sum")).reset_index()

if page.startswith("1 —"):
    hero("CEO Early-Warning Command Center","The next 30 days of operational, clinical, financial, and privacy risk—translated into executive action."); evidence()
    margin=(fd.revenue.sum()-fd.cost.sum())/max(fd.revenue.sum(),1); occ=fd.census.sum()/max(fd.staffed_beds.sum(),1)
    risk=int(np.clip(38+120*(occ-.78)+150*(fd.readmission_rate.mean()-.12)+3*fd.boarding_hours.mean(),0,100))
    integrity=int(np.clip(88-10*(len(fe)<100)-6*(len(hospitals)<2),0,100))
    cards([("Enterprise Risk Signal",f"{risk}/100","Modeled Composite; Higher Means More Intervention Urgency"),("Operating Margin",pct(margin),"Synthetic Result; Before Capital Allocation"),("Average Occupancy",pct(occ),"Staffed-Bed Utilization"),("Decision Integrity",f"{integrity}/100","Evidence, Completeness, Freshness, and Validation Score")])
    m=monthly(); c1,c2=st.columns([1.5,1])
    with c1:
        fig=go.Figure(); fig.add_bar(x=m.date,y=m.revenue-m.cost,name="Operating Contribution",marker_color="#0f766e"); fig.add_scatter(x=m.date,y=m.boarding*100000,name="Boarding Pressure (Indexed)",line=dict(color="#d97706",width=3)); fig.update_layout(title="Margin and Flow Pressure by Month",yaxis_title="Dollars / Indexed Pressure"); plot(fig)
    with c2:
        drivers=pd.DataFrame({"Driver":["ED Boarding","Readmission Exposure","Denial Leakage","Overtime","Preventable Harm"],"Impact":[fd.boarding_hours.mean()*240000,fe.readmission_30d.mean()*1800000,fd.denials.sum()/max((end-start).days/30,1),fd.overtime_hours.sum()*38/max((end-start).days/30,1),(fe.harm.sum()*28000)]}).sort_values("Impact")
        plot(px.bar(drivers,x="Impact",y="Driver",orientation="h",title="Modeled Monthly Opportunity by Driver",color="Impact",color_continuous_scale="Teal"))
    callout("CEO Call",f"Flow is the dominant near-term constraint: average boarding is {fd.boarding_hours.mean():.1f} hours while occupancy is {pct(occ)}. Launch a 30-day discharge reliability sprint at the highest-pressure hospital; pair it with denial prevention so capacity gains convert to margin. Confidence: {integrity}/100.")

elif page.startswith("2 —"):
    hero("Patient Flow Digital Twin","See where beds, discharges, and ED demand create bottlenecks—and test the capacity released by operational changes."); evidence()
    discharge_gain=st.slider("What-if: discharge delay reduction",0,30,12,1,format="%d%%")
    released=int(fd.census.mean()*discharge_gain/100*365); cards([("Average Daily Census",f"{fd.census.mean():,.0f}","Synthetic result"),("ED Boarding",f"{fd.boarding_hours.mean():.1f} hrs","Arrival-to-bed pressure"),("Annualized Bed-Days Released",f"{released:,}","Modeled what-if"),("LWBS Rate",pct(fd.lwbs_rate.mean()),"Patients leaving before service")])
    h=fd.groupby("hospital").agg(occupancy=("census","sum"),capacity=("staffed_beds","sum"),boarding=("boarding_hours","mean"),discharges=("discharges","sum")).reset_index(); h["occupancy"]=h.occupancy/h.capacity
    c1,c2=st.columns(2)
    with c1: plot(px.bar(h,x="hospital",y="occupancy",color="boarding",title="Occupancy and Boarding by Hospital",labels={"occupancy":"Occupancy"},text_auto=".1%"))
    with c2: plot(px.scatter(fd,x="census",y="boarding_hours",color="hospital",trendline="ols",title="Census-to-Boarding Response",labels={"census":"Daily census","boarding_hours":"Boarding hours"}))
    callout("Operational call",f"A {discharge_gain}% reduction in discharge delay is modeled to release {released:,} annualized bed-days. Validate discharge timestamps and post-acute placement constraints before setting the target.")

elif page.startswith("3 —"):
    hero("Clinical Deterioration & Rescue Reliability","Move from retrospective mortality reporting to early rescue-system surveillance."); evidence()
    rate=fe.deterioration.mean(); rescue=1-fe[fe.deterioration].harm.mean() if fe.deterioration.any() else 1
    cards([("Deterioration Signal",pct(rate),"Synthetic encounter result"),("Rescue Reliability",pct(rescue),"No recorded harm after deterioration"),("Observed Mortality",pct(fd.mortality_rate.mean()),"Synthetic operational result"),("Sepsis Cohort",f"{(fe.service_line=='Sepsis').sum():,}","Selected encounters")])
    g=fe.groupby(["hospital","service_line"]).agg(encounters=("encounter_id","count"),deterioration=("deterioration","mean"),harm=("harm","mean")).reset_index()
    plot(px.scatter(g,x="deterioration",y="harm",size="encounters",color="hospital",hover_name="service_line",title="Deterioration-to-Harm Reliability Matrix",labels={"deterioration":"Deterioration rate","harm":"Harm rate"}))
    callout("Clinical call","Focus validation on high-deterioration, high-harm service lines. The model is for surveillance prioritization only; bedside escalation must remain governed by validated clinical protocols.","risk")

elif page.startswith("4 —"):
    hero("Preventable Harm & Financial Exposure","Translate safety events into patient impact, capacity loss, and avoidable cost without reducing quality to dollars alone."); evidence()
    harm=fe.harm.sum(); exposure=harm*28000+fd.hai.sum()*47000+fd.falls.sum()*18000
    cards([("Patients with Harm Signal",f"{harm:,}","Synthetic encounters"),("Hospital-Acquired Infections",f"{fd.hai.sum():,}","Synthetic event count"),("Falls",f"{fd.falls.sum():,}","Synthetic event count"),("Modeled Financial Exposure",money(exposure),"Illustrative—not booked loss")])
    by=fe.groupby("service_line").agg(encounters=("encounter_id","count"),harm=("harm","sum"),cost=("cost","sum")).reset_index(); by["harm_rate"]=by.harm/by.encounters
    plot(px.bar(by.sort_values("harm_rate"),x="harm_rate",y="service_line",orientation="h",color="cost",title="Harm Signal by Service Line",labels={"harm_rate":"Harm rate"}))
    callout("Quality call","Prioritize the service line with the largest combination of harm rate and volume, then verify event definitions and denominator integrity before assigning accountability.")

elif page.startswith("5 —"):
    hero("Readmission Prevention & Transition Command Center","Identify transition failures that create avoidable returns—and the patients most likely to benefit from intervention."); evidence()
    r=fe.readmission_30d.mean(); gap=fe.groupby("svi_quartile").readmission_30d.mean(); equity=(gap.max()-gap.min()) if len(gap)>1 else 0
    cards([("30-Day Readmission",pct(r),"Synthetic selected cohort"),("Follow-Up Booked",pct(fe.followup_booked.mean()),"Transition reliability"),("Equity Gap",f"{100*equity:.1f} pts","Highest vs lowest SVI quartile"),("Modeled Avoidable Cost",money(fe.readmission_30d.sum()*14500),"Illustrative exposure")])
    g=fe.groupby(["service_line","discharge_barrier"]).agg(n=("encounter_id","count"),readmission=("readmission_30d","mean")).reset_index()
    plot(px.scatter(g,x="n",y="readmission",size="n",color="discharge_barrier",facet_col="service_line",facet_col_wrap=3,title="Readmission Risk by Service Line and Discharge Barrier"))
    callout("Transition call","Route high-risk heart failure and COPD discharges with transportation, medication, or caregiver barriers to a transition nurse and confirmed follow-up. Validate risk calibration prospectively.")

elif page.startswith("6 —"):
    hero("Workforce-to-Outcome Intelligence","Connect labor deployment to outcomes and throughput—without treating staffing as a simple cost-cutting exercise."); evidence()
    fd["hours_per_patient_day"]=fd.staff_hours/fd.census; fd["outcome_pressure"]=fd.readmission_rate+fd.mortality_rate+fd.falls/fd.census
    cards([("Hours per Patient Day",f"{fd.hours_per_patient_day.mean():.1f}","Synthetic staffing result"),("Overtime Share",pct(fd.overtime_hours.sum()/fd.staff_hours.sum()),"Overtime / productive hours"),("Labor Cost Proxy",money(fd.staff_hours.sum()*58),"Modeled loaded hourly cost"),("Staffing Confidence","62/100","Skill mix and vacancies unavailable")])
    plot(px.scatter(fd,x="hours_per_patient_day",y="outcome_pressure",color="hospital",trendline="ols",title="Staffing Intensity Versus Composite Outcome Pressure",labels={"hours_per_patient_day":"Hours per patient day","outcome_pressure":"Outcome pressure index"}))
    callout("Workforce call","Use this relationship to identify where staffing redesign may help; do not infer causality or reduce staffing solely from the trend. Skill mix, acuity, vacancies, and agency use require validation.","warning")

elif page.startswith("7 —"):
    hero("Access Leakage & Lost Patient Demand","Quantify when demand is lost before care begins—and where capacity or navigation can recover it."); evidence()
    lost=int(fd.ed_arrivals.sum()*fd.lwbs_rate.mean()); value=lost*780
    cards([("ED Arrivals",f"{fd.ed_arrivals.sum():,}","Synthetic demand"),("Left Without Being Seen",f"{lost:,}","Modeled from daily rate"),("Specialty Wait",f"{fd.specialty_wait_days.mean():.1f} days","Synthetic access result"),("Recoverable Value",money(value),"Illustrative gross revenue")])
    g=fd.groupby("hospital").agg(arrivals=("ed_arrivals","sum"),lwbs=("lwbs_rate","mean"),wait=("specialty_wait_days","mean"),boarding=("boarding_hours","mean")).reset_index()
    plot(px.bar(g,x="hospital",y=["lwbs","wait"],barmode="group",title="Access Leakage Signals by Hospital"))
    callout("Access call","Start with ED fast track and centralized specialty scheduling at the hospital with the highest combined LWBS, boarding, and wait-day signal.")

elif page.startswith("8 —"):
    hero("Operating-Room & Procedural Yield","Protect high-value procedural capacity by separating schedule volume, utilization, and contribution."); evidence()
    value=fd.or_cases.sum()*7400; unused=(1-fd.or_utilization.mean())*fd.or_cases.sum()*7400
    cards([("Procedural Cases",f"{fd.or_cases.sum():,}","Synthetic operations"),("OR Utilization",pct(fd.or_utilization.mean()),"Scheduled-room proxy"),("Gross Procedural Value",money(value),"Modeled contribution input"),("Unused Capacity Signal",money(unused),"Illustrative—not fully recoverable")])
    g=fd.groupby(["hospital",fd.date.dt.day_name()]).agg(cases=("or_cases","sum"),util=("or_utilization","mean")).reset_index(names=["hospital","day"])
    plot(px.scatter(g,x="cases",y="util",color="hospital",text="day",title="Procedural Volume and Utilization by Day"))
    callout("Procedural call","Improve first-case-on-time reliability and rebalance low-utilization blocks before adding rooms. Surgeon availability and block ownership are not included.")

elif page.startswith("9 —"):
    hero("Health Equity & Geographic Opportunity","Reveal where barriers—not clinical need alone—shape outcomes and access."); evidence()
    eq=fe.groupby("svi_quartile").agg(encounters=("encounter_id","count"),readmission=("readmission_30d","mean"),followup=("followup_booked","mean"),cost=("cost","mean")).reset_index()
    cards([("High-Vulnerability Encounters",f"{(fe.svi_quartile==4).sum():,}","Synthetic, SVI-calibrated"),("Q4 Follow-Up",pct(eq.loc[eq.svi_quartile==4,"followup"].mean()),"Highest vulnerability quartile"),("Q4 Readmission",pct(eq.loc[eq.svi_quartile==4,"readmission"].mean()),"Synthetic result"),("Equity Evidence","68/100","No patient-level geocoding")])
    plot(px.bar(eq,x="svi_quartile",y=["readmission","followup"],barmode="group",title="Outcomes by Social Vulnerability Quartile"))
    callout("Equity call","Pair navigation, transportation support, and language access with high-vulnerability transition pathways. Do not use SVI to deny or deprioritize individual care.")

elif page.startswith("10 —"):
    hero("Payer, Denial & Margin Integrity","Show where earned revenue fails to become cash—and which clinical volumes carry unsustainable economics."); evidence()
    margin=fe.groupby(["payer","service_line"]).agg(revenue=("revenue","sum"),cost=("cost","sum"),encounters=("encounter_id","count")).reset_index(); margin["contribution"]=margin.revenue-margin.cost
    cards([("Gross Revenue",money(fd.revenue.sum()),"Synthetic operations"),("Denial Exposure",money(fd.denials.sum()),"Synthetic result"),("Denial Rate",pct(fd.denials.sum()/fd.revenue.sum()),"Denied / gross revenue"),("Encounter Contribution",money(fe.revenue.sum()-fe.cost.sum()),"Synthetic cohort")])
    plot(px.bar(margin,x="service_line",y="contribution",color="payer",barmode="group",title="Contribution by Service Line and Payer"))
    callout("Margin call","Prioritize front-end authorization and documentation in negative-contribution payer/service combinations; validate contract terms and final adjudication before action.")

elif page.startswith("11 —"):
    hero("Intervention Portfolio & ROI Laboratory","Rank initiatives by value, feasibility, capacity release, confidence, and strategic fit—not ROI alone."); evidence()
    budget=st.slider("Available Annual Investment",100000,2000000,900000,50000,format="$%d")
    iv2=iv.copy(); iv2["net_value"]=iv2.annual_value-iv2.annual_cost; iv2["roi"]=iv2.net_value/iv2.annual_cost; iv2["priority_score"]=iv2.roi*iv2.confidence/100+iv2.capacity_days/3000
    chosen=iv2.sort_values("priority_score",ascending=False); chosen["cumulative_cost"]=chosen.annual_cost.cumsum(); selected=chosen[chosen.cumulative_cost<=budget]
    cards([("Portfolio Investment",money(selected.annual_cost.sum()),"Within selected budget"),("Modeled Annual Value",money(selected.annual_value.sum()),"Not guaranteed"),("Net Value",money(selected.net_value.sum()),"Value less program cost"),("Capacity Days",f"{selected.capacity_days.sum():,.0f}","Modeled release")])
    plot(px.scatter(iv2,x="annual_cost",y="annual_value",size="capacity_days",color="confidence",text="intervention",title="Intervention Value Frontier"))
    table(selected[["intervention","domain","annual_cost","annual_value","net_value","roi","confidence"]])
    callout("Portfolio call",f"At a {money(budget)} ceiling, fund {len(selected)} initiatives as a staged portfolio. Release funding by milestone and re-estimate benefits after 90 days.")

elif page.startswith("12 —"):
    hero("Methods, Governance & Confidence","Make every executive conclusion auditable: source, lineage, metric definition, uncertainty, limitation, and validation status."); evidence()
    components={"Source authority":84,"Data completeness":88,"Metric definition":91,"Timeliness":82,"Causal confidence":54,"External validity":61}
    score=int(np.mean(list(components.values())))
    cards([("Decision Integrity Score",f"{score}/100","Composite—not model accuracy"),("Public Sources",f"{(src.evidence_type.str.contains('Public')).sum()}","Authoritative source registry"),("Synthetic Records",f"{len(fe):,}","Selected encounter simulation"),("Validation Gates","5","Clinical, finance, privacy, operations, equity")])
    plot(px.bar(pd.DataFrame({"component":components.keys(),"score":components.values()}),x="score",y="component",orientation="h",range_x=[0,100],title="Decision Integrity Components",color="score",color_continuous_scale="Teal"))
    st.subheader("Source and Evidence Registry"); table(src)
    callout("Governance call","No recommendation should move from portfolio evidence to production decision support until source lineage, definitions, bias, prospective validation, security, and accountable ownership are approved.","warning")

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
    callout("Privacy call",f"A {minimum}% reduction in unnecessary access is modeled to prevent exposure of {prevent:,} records. This is a scenario, not a breach determination; legal and privacy review remains required.")

else:
    hero("Quality Improvement & Reliability Lab — CPHQ Lens","Turn variation into disciplined improvement using control charts, Pareto prioritization, PDSA governance, and sustainment evidence."); evidence()
    measure=st.selectbox("Quality Measure",["readmission","mortality","boarding","falls","hai"],format_func=title_label)
    m=monthly(); y=m[measure].astype(float); mean=y.mean(); sd=y.std(ddof=1); ucl=mean+3*sd; lcl=max(0,mean-3*sd)
    cards([("Selected Measure",measure.replace("_"," ").title(),"Synthetic result"),("Center Line",f"{mean:.3f}","Selected-range mean"),("Upper Control Limit",f"{ucl:.3f}","Three-sigma analytic limit"),("Special-Cause Months",f"{((y>ucl)|(y<lcl)).sum()}","Screening signal")])
    fig=go.Figure(); fig.add_scatter(x=m.date,y=y,mode="lines+markers",name=measure,line=dict(color="#0369a1",width=3)); fig.add_hline(y=mean,line_color="#0f766e",annotation_text="Center line"); fig.add_hline(y=ucl,line_dash="dash",line_color="#b91c1c",annotation_text="UCL"); fig.add_hline(y=lcl,line_dash="dash",line_color="#b91c1c",annotation_text="LCL"); fig.update_layout(title=f"Statistical Process Control: {measure.title()}"); plot(fig)
    pareto=fe.groupby("discharge_barrier").size().sort_values(ascending=False).reset_index(name="count"); pareto["cumulative_pct"]=pareto["count"].cumsum()/pareto["count"].sum()
    c1,c2=st.columns(2)
    with c1: plot(px.bar(pareto,x="discharge_barrier",y="count",title="Pareto: Discharge Barriers"))
    with c2:
        st.subheader("PDSA Learning System")
        table(pd.DataFrame([["Plan","Define aim, population, measure, prediction"],["Do","Test on small scale; document deviations"],["Study","Compare result with prediction; examine variation"],["Act","Adopt, adapt, or abandon; define next cycle"]],columns=["phase","evidence_required"]))
    callout("Quality call","Treat points beyond limits as investigation signals, not proof of performance failure. Confirm denominator stability, coding changes, seasonality, and workflow context before intervention.")

st.markdown("---")
st.caption("GulfStar Health System is fictional. Operational and patient-level results are synthetic and reproducible. Public agencies provide benchmark definitions and context. This portfolio demonstrates healthcare analytics leadership; it is not clinical, legal, privacy, or financial advice.")
