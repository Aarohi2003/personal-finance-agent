"""
FinanceIQ – Enhanced Personal Finance Agent
All 14 improvements applied:
  1.  CSV bank statement upload + auto-parsing
  2.  Expense breakdown by category
  3.  Interactive charts (monthly trends, pie, bar)
  4.  Financial Health Score
  5.  Budget Planner with monthly limits
  6.  Personalized savings recommendations
  7.  Expense forecasting (3-month projection)
  8.  Chat history section
  9.  Download financial reports as PDF / CSV
  10. PDF upload + Q&A (RAG-style)
  11. Investment guidance (SIP, emergency fund)
  12. Sample prompts for first-time users
  13. Disclaimer banner
  14. Professional dashboard layout
"""

import streamlit as st
from groq import Groq
import plotly.graph_objects as go
import plotly.express as px
import re, json, io, csv, base64
from datetime import datetime, timedelta
import pandas as pd

# ─── API CLIENT ───────────────────────────────────────────────────────────────
api_key = st.secrets["GROQ_API_KEY"]
client  = Groq(api_key=api_key)
MODEL   = "llama-3.3-70b-versatile"

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are FinanceIQ — a highly professional, warm, and motivating personal finance advisor for young adults (18-25) in India.

You follow these four pillars rigorously:
1. BUDGETING: 50% Needs / 30% Wants / 20% Savings & Debt
2. AUTOMATION: Automate savings the day salary arrives
3. DEBT STRATEGY: Avalanche method (highest interest first), protect credit score
4. INVESTING: Emergency fund → debt → index funds / SIP / tax-advantaged accounts

CONVERSATION FLOW (one question at a time, strictly):

Step 1: "What are your main monthly expenses? Break them into:
- Needs (rent, groceries, transport, utilities, insurance)
- Wants (eating out, subscriptions, entertainment, shopping)
Give ₹ amounts for each category."

Step 2 (after expenses shared):
- Calculate needs%, wants%, savings% of income
- If income is very low (savings% negative or near zero):
  Give strong, warm motivation: "Your income is tight right now, and that's okay — many successful people started exactly where you are. Let's find small wins together."
  Give 2-3 actionable tips to earn more / cut costs
- If overspending in Needs (>50%): give specific suggestions to cut
- If overspending in Wants (>30%): suggest which wants to trim
- Always show the 50/30/20 ideal vs their actual
Then ask: "Do you have any debts? (credit card, personal loan, student loan — include interest rate if known)"

Step 3: "Do you have an emergency fund? How many months of expenses is it covering?"

Step 4: "What's your risk tolerance for investing? (conservative / moderate / aggressive)"

Step 5: "What is your #1 financial goal right now, and what's your target amount and timeframe?"

Step 6: "Do you have any investments currently? (SIP, stocks, FD, PPF, etc.)"

After all steps, output EXACTLY this format:

---
💡 YOUR PLAN
[2-3 sentence personalized recommendation covering all 4 pillars]

✅ WHY THIS WORKS
[2-3 lines]

🚀 ACTION STEPS
1. [Specific step with ₹ amount]
2. [Specific step]
3. [Specific step]
4. [Specific step]
5. [Specific step]

💬 MOTIVATION
[2-3 sentences of genuine, specific motivation based on their situation. If income is low, be extra encouraging. Reference their goal specifically.]

📦 SPENDING_JSON: {"needs": X, "wants": X, "savings_debt": X, "categories": {"rent": X, "food": X, "transport": X, "entertainment": X, "subscriptions": X, "other_needs": X, "other_wants": X}}
🎯 GOAL_JSON: {"goal": "description", "target_amount": X, "months": X, "monthly_needed": X}
💳 DEBT_JSON: {"has_debt": true/false, "total_debt": X, "monthly_payment": X, "strategy": "avalanche/none"}
🏷️ TAGS: emergency_fund,sip,insurance,debt,overspending,savings,investing,needs_reduction,wants_reduction,motivation
---

Rules:
- Always reference the 50/30/20 rule with their actual numbers
- Always suggest automation of savings
- If they have debt, always mention avalanche method
- If income < expenses, MOTIVATE and give income-boosting tips (freelancing, upskilling, side income)
- Never be harsh. Always be warm, specific, and actionable.
- One question at a time only.
"""

PDF_QA_PROMPT = """You are a financial document analyst. The user has uploaded a financial PDF document.
Answer questions about it clearly and concisely. Focus on:
- Key financial figures, dates, amounts
- Important terms or conditions
- Actionable insights for a young Indian adult

Be helpful, precise, and always mention if something requires professional advice."""

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="FinanceIQ", page_icon="💰", layout="wide")

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }
[data-testid="stAppViewContainer"] { background: #0a0d14; }
[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #1e2433;
}
[data-testid="stSidebar"] * { color: #cbd5e0; }

.card {
    background: linear-gradient(135deg, #111827, #1a2035);
    border: 1px solid #1e2d4a;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    animation: fadeUp .35s ease;
}
.card-accent { border-left: 3px solid #667eea; }
.card-green  { border-left: 3px solid #48bb78; }
.card-amber  { border-left: 3px solid #f6ad55; }
.card-red    { border-left: 3px solid #fc8181; }
.card-purple { border-left: 3px solid #b794f4; }
.card-teal   { border-left: 3px solid #4fd1c5; }

@keyframes fadeUp {
    from { opacity:0; transform:translateY(10px); }
    to   { opacity:1; transform:translateY(0); }
}

.slabel {
    font-size: 10px; text-transform: uppercase;
    letter-spacing: 2.5px; color: #667eea;
    font-weight: 700; margin-bottom: 14px;
}

.mchip {
    background: #131929;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    height: 100%;
}
.mchip .mv { color:#e2e8f0; font-size:20px; font-weight:700; line-height:1.2; }
.mchip .ml { color:#8892b0; font-size:11px; margin-top:4px; }
.mchip .ms { font-size:11px; margin-top:3px; }

.row-item {
    display:flex; justify-content:space-between; align-items:center;
    padding: 11px 16px; margin: 5px 0;
    background: #131929; border-radius: 10px;
    border-left: 3px solid #667eea;
}
.row-label { color:#cbd5e0; font-size:13.5px; }
.row-val   { color:#90cdf4; font-weight:600; font-size:14px; }

.rule-bar-wrap {
    background:#131929; border-radius:8px;
    height:10px; overflow:hidden; margin:6px 0;
}
.rule-bar-fill { height:10px; border-radius:8px; }

.astep {
    display:flex; gap:12px; align-items:flex-start;
    background:#131929; border-radius:10px;
    padding:12px 14px; margin:6px 0;
}
.astep-num {
    background: linear-gradient(135deg,#667eea,#764ba2);
    color:#fff; border-radius:50%;
    width:26px; height:26px; min-width:26px;
    display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:700;
}
.astep-text { color:#cbd5e0; font-size:13.5px; line-height:1.6; }

.tpill {
    display:inline-block;
    background:#1a2744; color:#90cdf4;
    border:1px solid #2b4c7e; border-radius:20px;
    padding:4px 13px; font-size:12px; margin:3px;
}

.motiv-card {
    background: linear-gradient(135deg,#1a1f35,#1d2845);
    border: 1px solid #2d3a6b;
    border-radius: 14px; padding:20px 22px;
    margin-top:8px;
}
.motiv-text { color:#c3dafe; font-size:14px; line-height:1.8; }

.disclaimer-banner {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 1px solid #2d3a6b;
    border-left: 4px solid #f6ad55;
    border-radius: 10px;
    padding: 12px 18px;
    margin-bottom: 16px;
    color: #f6ad55;
    font-size: 12px;
    line-height: 1.6;
}

.health-score-ring {
    text-align: center;
    padding: 20px;
}

.sample-prompt {
    background: #131929;
    border: 1px solid #1e2d4a;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 4px 0;
    color: #90cdf4;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
}
.sample-prompt:hover {
    border-color: #667eea;
    background: #1a2035;
}

.chat-history-item {
    background: #131929;
    border-radius: 10px;
    padding: 12px 16px;
    margin: 6px 0;
    border-left: 3px solid #1e2d4a;
}
.chat-history-date { color: #667eea; font-size: 11px; margin-bottom: 4px; }
.chat-history-preview { color: #8892b0; font-size: 12.5px; }

[data-testid="stSidebar"] .stNumberInput input {
    background: #131929 !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] label { color: #8892b0 !important; font-size:12px !important; }

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#667eea,#764ba2) !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; color: #fff !important;
    box-shadow: 0 4px 15px rgba(102,126,234,.3) !important;
}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
    background: #131929 !important; color: #8892b0 !important;
    border: 1px solid #1e2d4a !important; border-radius: 10px !important;
}

.stButton > button { border-radius: 8px !important; }

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: #0d1117;
    border-bottom: 1px solid #1e2433;
}
.stTabs [data-baseweb="tab"] {
    color: #8892b0 !important;
}
.stTabs [aria-selected="true"] {
    color: #667eea !important;
}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
defaults = {
    "messages": [], "started": False, "income": 0, "spending": 0,
    "show_dashboard": False, "final_reply": "",
    "spending_cats": {}, "needs": 0, "wants": 0,
    "goal_data": {}, "debt_data": {}, "tags": [],
    "active_slide": 0, "goal_saved": 0,
    # New state
    "chat_sessions": [],          # list of {date, preview, messages}
    "csv_data": None,             # parsed DataFrame from CSV upload
    "budget_limits": {},          # {category: limit_amount}
    "pdf_doc_text": "",           # extracted text from uploaded PDF
    "pdf_qa_messages": [],        # Q&A conversation for PDF
    "active_tab": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── PARSERS ─────────────────────────────────────────────────────────────────
def parse_json_block(reply, key):
    pattern = rf"{re.escape(key)}\s*(\{{.*?\}})"
    m = re.search(pattern, reply, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    return {}

def parse_tags(reply):
    if "TAGS:" in reply:
        line = reply.split("TAGS:")[-1].strip().split("\n")[0]
        return [t.strip().lower() for t in line.replace("---","").split(",") if t.strip()]
    return []

def parse_section(reply, emoji_key, stop_emoji):
    pattern = rf"{re.escape(emoji_key)}\n(.+?)(?={re.escape(stop_emoji)}|\Z)"
    m = re.search(pattern, reply, re.DOTALL)
    return m.group(1).strip() if m else ""

def parse_action_steps(reply):
    steps = []
    in_section = False
    for line in reply.split("\n"):
        if "ACTION STEPS" in line: in_section = True; continue
        if in_section:
            if line.strip().startswith(("💬","📦","🎯","💳","🏷️","---")): break
            m = re.match(r"^\s*\d+\.\s+(.+)", line)
            if m: steps.append(m.group(1).strip())
    return steps

def parse_motivation(reply):
    if "💬 MOTIVATION" in reply:
        part = reply.split("💬 MOTIVATION")[-1]
        lines = []
        for line in part.split("\n"):
            if line.strip().startswith(("📦","🎯","💳","🏷️","---")): break
            if line.strip(): lines.append(line.strip())
        return " ".join(lines)
    return ""

def parse_plan(reply):
    return parse_section(reply, "💡 YOUR PLAN", "✅")

def parse_why(reply):
    return parse_section(reply, "✅ WHY THIS WORKS", "🚀")

# ─── CSV PARSER ───────────────────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "food":          ["zomato","swiggy","restaurant","food","grocery","bigbasket","blinkit","cafe","coffee","lunch","dinner","breakfast"],
    "transport":     ["uber","ola","metro","bus","fuel","petrol","rapido","cab","taxi","train","flight"],
    "rent":          ["rent","housing","pg","hostel","accommodation","maintenance"],
    "utilities":     ["electricity","water","gas","wifi","internet","broadband","mobile","phone","recharge"],
    "entertainment": ["netflix","spotify","prime","hotstar","zee5","movie","game","concert","pub","bar"],
    "subscriptions": ["youtube","apple","adobe","linkedin","coursera","udemy","notion"],
    "shopping":      ["amazon","flipkart","myntra","ajio","meesho","h&m","zara","cloth","fashion"],
    "health":        ["pharmacy","hospital","doctor","gym","fitness","medicine","apollo","medplus"],
    "insurance":     ["lic","insurance","premium","policy"],
    "education":     ["school","college","tuition","course","books"],
}

def categorize_transaction(description: str) -> str:
    desc_lower = description.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return cat
    return "other"

def parse_csv_statement(file) -> pd.DataFrame:
    """Try to parse common bank CSV formats."""
    try:
        df = pd.read_csv(file)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Detect amount column
        amt_col = next((c for c in df.columns if any(k in c for k in ["debit","amount","withdrawal","dr"])), None)
        desc_col = next((c for c in df.columns if any(k in c for k in ["description","narration","particulars","details","remarks"])), None)
        date_col = next((c for c in df.columns if "date" in c), None)

        if amt_col is None or desc_col is None:
            return None

        df["amount"] = pd.to_numeric(df[amt_col].astype(str).str.replace(",","").str.replace("₹",""), errors="coerce").fillna(0)
        df["description"] = df[desc_col].astype(str)
        df["category"] = df["description"].apply(categorize_transaction)
        if date_col:
            df["date"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        else:
            df["date"] = pd.NaT

        return df[df["amount"] > 0][["date","description","amount","category"]].copy()
    except Exception:
        return None

# ─── FINANCIAL HEALTH SCORE ───────────────────────────────────────────────────
def compute_health_score(income, needs, wants, savings, has_debt, has_emergency, has_investment):
    score = 0
    if income > 0:
        needs_pct    = needs / income * 100
        wants_pct    = wants / income * 100
        savings_pct  = savings / income * 100

        if needs_pct  <= 50: score += 25
        elif needs_pct <= 60: score += 15
        else: score += 5

        if wants_pct  <= 30: score += 20
        elif wants_pct <= 40: score += 10
        else: score += 3

        if savings_pct >= 20: score += 25
        elif savings_pct >= 10: score += 15
        elif savings_pct > 0: score += 5

    if not has_debt:   score += 15
    else:              score += 5
    if has_emergency:  score += 10
    if has_investment: score += 5

    return min(score, 100)

def health_grade(score):
    if score >= 85: return "Excellent 🌟", "#48bb78"
    if score >= 70: return "Good 👍",       "#4fd1c5"
    if score >= 50: return "Fair ⚠️",       "#f6ad55"
    return "Needs Work 🔴", "#fc8181"

# ─── EXPENSE FORECASTING ──────────────────────────────────────────────────────
def forecast_expenses(df: pd.DataFrame, months_ahead=3):
    """Simple linear trend forecast from CSV data."""
    if df is None or df.empty or df["date"].isna().all():
        return None
    df = df.dropna(subset=["date"])
    df["month"] = df["date"].dt.to_period("M")
    monthly = df.groupby("month")["amount"].sum().reset_index()
    monthly["month_num"] = range(len(monthly))
    if len(monthly) < 2:
        return None
    # Simple linear regression
    x = monthly["month_num"].values
    y = monthly["amount"].values
    slope = (len(x)*sum(x*y) - sum(x)*sum(y)) / (len(x)*sum(x**2) - sum(x)**2 + 1e-9)
    intercept = (sum(y) - slope*sum(x)) / len(x)
    last_idx = x[-1]
    future_months = []
    future_vals = []
    last_period = monthly["month"].iloc[-1]
    for i in range(1, months_ahead+1):
        future_months.append(str(last_period + i))
        future_vals.append(max(0, intercept + slope*(last_idx+i)))
    return {
        "historical_months": [str(m) for m in monthly["month"]],
        "historical_vals":   monthly["amount"].tolist(),
        "forecast_months":   future_months,
        "forecast_vals":     future_vals,
    }

# ─── CHART HELPERS ───────────────────────────────────────────────────────────
COLORS = ["#667eea","#48bb78","#f6ad55","#fc8181","#b794f4","#4facfe","#f093fb","#43e97b","#4fd1c5","#fbb6ce"]

def donut_chart(labels, values, title=""):
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.6,
        marker=dict(colors=COLORS[:len(labels)], line=dict(color="#0a0d14", width=2)),
        textinfo="label+percent",
        textfont=dict(color="#e2e8f0", size=11),
        hovertemplate="<b>%{label}</b><br>₹%{value:,}<br>%{percent}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0), height=260,
        showlegend=True,
        legend=dict(font=dict(color="#8892b0",size=11), bgcolor="rgba(0,0,0,0)",
                    orientation="v", x=1, y=0.5),
        annotations=[dict(text=title, x=0.5, y=0.5, font_size=13,
                          font_color="#e2e8f0", showarrow=False)] if title else []
    )
    return fig

def hbar_chart(labels, values, colors=None):
    c = colors or COLORS[:len(labels)]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=c, line=dict(width=0)),
        text=[f"₹{v:,.0f}" for v in values],
        textposition="outside", textfont=dict(color="#e2e8f0", size=11),
        hovertemplate="<b>%{y}</b>: ₹%{x:,}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, color="#cbd5e0", tickfont=dict(size=12)),
        margin=dict(t=5,b=5,l=0,r=90),
        height=max(140, 50*len(labels))
    )
    return fig

def line_chart(x, y, target, already):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines",
        line=dict(color="#667eea", width=2.5),
        fill="tozeroy", fillcolor="rgba(102,126,234,0.08)",
        hovertemplate="Month %{x}: ₹%{y:,.0f}<extra></extra>"
    ))
    if already > 0:
        fig.add_hline(y=already, line_dash="dot", line_color="#48bb78",
                      annotation_text="Current savings", annotation_font_color="#48bb78",
                      annotation_position="bottom right")
    fig.add_hline(y=target, line_dash="dash", line_color="#f6ad55",
                  annotation_text=f"Goal ₹{target:,}", annotation_font_color="#f6ad55")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Months", color="#8892b0", gridcolor="#131929", tickfont=dict(size=11)),
        yaxis=dict(title="₹ Saved", color="#8892b0", gridcolor="#131929", tickfont=dict(size=11)),
        margin=dict(t=10,b=40,l=60,r=10), height=230, showlegend=False
    )
    return fig

def forecast_chart(fdata):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=fdata["historical_months"], y=fdata["historical_vals"],
        name="Historical", marker_color="#667eea",
        hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=fdata["forecast_months"], y=fdata["forecast_vals"],
        name="Forecast", marker_color="#f6ad55",
        hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        barmode="group",
        xaxis=dict(color="#8892b0", tickfont=dict(size=11)),
        yaxis=dict(color="#8892b0", gridcolor="#131929"),
        legend=dict(font=dict(color="#8892b0"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=10,b=40,l=60,r=10), height=250
    )
    return fig

def gauge_chart(value, max_val, color, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=dict(prefix="₹", font=dict(color="#e2e8f0", size=20)),
        title=dict(text=title, font=dict(color="#8892b0", size=12)),
        gauge=dict(
            axis=dict(range=[0, max_val], tickcolor="#8892b0"),
            bar=dict(color=color),
            bgcolor="#131929",
            bordercolor="#1e2d4a",
            steps=[dict(range=[0, max_val], color="#0a0d14")]
        )
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30,b=10,l=20,r=20), height=180
    )
    return fig

def health_gauge(score):
    _, color = health_grade(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(suffix="/100", font=dict(color="#e2e8f0", size=28)),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor="#8892b0"),
            bar=dict(color=color, thickness=0.3),
            bgcolor="#131929",
            bordercolor="#1e2d4a",
            steps=[
                dict(range=[0,50],  color="#1a0a0a"),
                dict(range=[50,70], color="#1a1500"),
                dict(range=[70,85], color="#001a0a"),
                dict(range=[85,100],color="#001020"),
            ],
            threshold=dict(line=dict(color=color, width=4), thickness=0.75, value=score)
        )
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20,b=0,l=20,r=20), height=200
    )
    return fig

# ─── 50/30/20 ANALYSIS ───────────────────────────────────────────────────────
def analyze_5030(income, needs, wants):
    savings = max(income - needs - wants, 0)
    ideal_needs   = income * 0.5
    ideal_wants   = income * 0.3
    ideal_savings = income * 0.2
    needs_pct     = needs   / income * 100 if income else 0
    wants_pct     = wants   / income * 100 if income else 0
    savings_pct   = savings / income * 100 if income else 0
    return {
        "needs": needs, "wants": wants, "savings": savings,
        "needs_pct": needs_pct, "wants_pct": wants_pct, "savings_pct": savings_pct,
        "ideal_needs": ideal_needs, "ideal_wants": ideal_wants, "ideal_savings": ideal_savings,
        "needs_ok":   needs_pct  <= 50,
        "wants_ok":   wants_pct  <= 30,
        "savings_ok": savings_pct >= 20,
    }

# ─── SAVINGS RECOMMENDATIONS ─────────────────────────────────────────────────
def savings_recommendations(ana, income, tags, debt):
    recs = []
    if not ana["savings_ok"]:
        gap = ana["ideal_savings"] - ana["savings"]
        recs.append({
            "icon": "💰", "color": "#667eea",
            "title": "Boost Your Savings Rate",
            "text": f"You need ₹{gap:,.0f}/month more savings. Try automating ₹{max(500,int(gap*0.5)):,} immediately and build up gradually."
        })
    if "sip" not in tags and income > 5000:
        recs.append({
            "icon": "📈", "color": "#48bb78",
            "title": "Start a SIP Today",
            "text": f"Invest ₹{max(500, int(ana['ideal_savings']*0.5)):,}/month in a Nifty 50 index fund via Zerodha Coin or Groww. Even ₹500/month compounding at 12% = ₹{int(500*((1.01**120-1)/0.01)):,} in 10 years."
        })
    if "emergency_fund" not in tags:
        months_cover = 6
        target_ef = st.session_state.spending * months_cover
        recs.append({
            "icon": "🛡️", "color": "#4fd1c5",
            "title": "Build Your Emergency Fund",
            "text": f"Target ₹{target_ef:,.0f} (6 months of expenses). Park it in a liquid fund or FD with SBI/HDFC. Don't invest until this is ready."
        })
    if debt.get("has_debt"):
        recs.append({
            "icon": "💳", "color": "#fc8181",
            "title": "Avalanche Debt Attack",
            "text": "List all debts by interest rate (highest first). Pay minimum on all, throw every extra rupee at the top one. This saves the most interest."
        })
    if not recs:
        recs.append({
            "icon": "🌟", "color": "#f6ad55",
            "title": "Great Financial Health!",
            "text": "You're on track. Consider increasing SIP contributions by ₹500/month every 6 months as your income grows."
        })
    return recs

# ─── INVESTMENT GUIDANCE ─────────────────────────────────────────────────────
INVESTMENT_GUIDE = {
    "conservative": {
        "allocation": [("FD / RD", 50), ("Liquid Mutual Fund", 30), ("PPF", 15), ("Gold ETF", 5)],
        "tip": "Your priority: 6-month emergency fund in FD, then PPF for tax benefit (₹1.5L/year limit under 80C)."
    },
    "moderate": {
        "allocation": [("Nifty 50 Index SIP", 40), ("FD / Debt Fund", 30), ("PPF", 20), ("Gold ETF", 10)],
        "tip": "Balance growth + safety. Start ₹500/month SIP in UTI Nifty 50, top up every 6 months."
    },
    "aggressive": {
        "allocation": [("Equity SIP (Index)", 60), ("Mid/Small Cap", 20), ("PPF / NPS", 15), ("Gold", 5)],
        "tip": "Young age = time to ride volatility. Stay invested through market dips. Never invest money you need in <3 years."
    }
}

# ─── REPORT GENERATORS ───────────────────────────────────────────────────────
def generate_csv_report(income, ana, cats, goal, debt, tags):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["FinanceIQ – Financial Report", datetime.now().strftime("%d %b %Y")])
    writer.writerow([])
    writer.writerow(["INCOME & BUDGET"])
    writer.writerow(["Monthly Income (₹)", income])
    writer.writerow(["Needs (₹)", ana["needs"], f"{ana['needs_pct']:.1f}%"])
    writer.writerow(["Wants (₹)", ana["wants"], f"{ana['wants_pct']:.1f}%"])
    writer.writerow(["Savings (₹)", ana["savings"], f"{ana['savings_pct']:.1f}%"])
    writer.writerow([])
    writer.writerow(["CATEGORY BREAKDOWN"])
    for cat, amt in cats.get("categories", {}).items():
        writer.writerow([cat.replace("_"," ").title(), f"₹{amt:,}"])
    writer.writerow([])
    writer.writerow(["GOAL"])
    writer.writerow(["Goal", goal.get("goal","—")])
    writer.writerow(["Target (₹)", goal.get("target_amount", 0)])
    writer.writerow(["Timeframe (months)", goal.get("months", 0)])
    writer.writerow(["Monthly Needed (₹)", goal.get("monthly_needed", 0)])
    writer.writerow([])
    writer.writerow(["DEBT"])
    writer.writerow(["Has Debt", "Yes" if debt.get("has_debt") else "No"])
    writer.writerow(["Total Debt (₹)", debt.get("total_debt", 0)])
    writer.writerow(["Monthly Payment (₹)", debt.get("monthly_payment", 0)])
    writer.writerow([])
    writer.writerow(["FOCUS TAGS", ", ".join(tags)])
    writer.writerow([])
    writer.writerow(["Disclaimer", "This report is for educational purposes only and does not constitute professional financial advice."])
    return output.getvalue()

# ─── DISCLAIMER ──────────────────────────────────────────────────────────────
def show_disclaimer():
    st.markdown("""<div class="disclaimer-banner">
      ⚠️ <strong>Disclaimer:</strong> FinanceIQ provides <strong>educational guidance only</strong> and does not constitute professional financial, investment, or tax advice.
      All recommendations are based on general financial principles (50/30/20 rule, etc.) and may not suit your individual circumstances.
      Please consult a SEBI-registered financial advisor for personalized investment advice.
    </div>""", unsafe_allow_html=True)

# ─── SAMPLE PROMPTS ──────────────────────────────────────────────────────────
SAMPLE_PROMPTS = [
    "I earn ₹25,000/month and spend ₹18,000. How do I start investing?",
    "I have a ₹50,000 credit card debt at 36% interest. What should I do?",
    "I want to save ₹2 lakhs for a Europe trip in 18 months. Is it possible?",
    "How do I start a SIP with just ₹500/month?",
    "I'm fresh out of college earning ₹30,000. What's my priority?",
]

# ─── TAG MAP ─────────────────────────────────────────────────────────────────
TAG_MAP = {
    "emergency_fund": "🛡️ Emergency Fund",
    "sip":            "📈 SIP / Invest",
    "insurance":      "🏥 Insurance",
    "debt":           "💳 Pay Debt",
    "overspending":   "✂️ Cut Spending",
    "savings":        "💰 Build Savings",
    "investing":      "📊 Investing",
    "needs_reduction":"🏠 Trim Needs",
    "wants_reduction":"🎯 Trim Wants",
    "motivation":     "💪 Stay Motivated",
}

# ─── PDF Q&A ─────────────────────────────────────────────────────────────────
def answer_pdf_question(question, doc_text, history):
    messages = []
    for h in history[-6:]:  # keep last 6 turns for context
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": f"Document content:\n{doc_text[:8000]}\n\nQuestion: {question}"})
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": PDF_QA_PROMPT}] + messages,
        max_tokens=600, temperature=0.4
    )
    return resp.choices[0].message.content

# ─── MAIN DASHBOARD ──────────────────────────────────────────────────────────
def show_dashboard():
    income   = st.session_state.income
    spending = st.session_state.spending
    cats     = st.session_state.spending_cats
    goal     = st.session_state.goal_data
    debt     = st.session_state.debt_data
    tags     = st.session_state.tags
    reply    = st.session_state.final_reply
    csv_df   = st.session_state.csv_data
    budgets  = st.session_state.budget_limits

    needs  = cats.get("needs",  spending * 0.6)
    wants  = cats.get("wants",  spending * 0.3)
    ana    = analyze_5030(income, needs, wants)
    savings = ana["savings"]

    plan  = parse_plan(reply)
    why   = parse_why(reply)
    steps = parse_action_steps(reply)
    motiv = parse_motivation(reply)

    has_debt       = debt.get("has_debt", False)
    has_emergency  = "emergency_fund" in tags
    has_investment = "sip" in tags or "investing" in tags
    score = compute_health_score(income, needs, wants, savings, has_debt, has_emergency, has_investment)
    grade, grade_color = health_grade(score)

    show_disclaimer()

    # ── SLIDE NAV ─────────────────────────────────────────────────────────
    SLIDES = ["📊 Overview", "📐 50/30/20", "🍩 Spending", "🎯 Goal", "🚀 Action Plan",
              "💡 Savings", "📈 Investments", "🔮 Forecast", "📄 Reports"]
    n = len(SLIDES)

    nav = st.columns([1, 10, 1])
    with nav[0]:
        if st.button("◀", use_container_width=True):
            st.session_state.active_slide = (st.session_state.active_slide - 1) % n
            st.rerun()
    with nav[1]:
        chosen = st.radio("", SLIDES, index=st.session_state.active_slide,
                          horizontal=True, label_visibility="collapsed", key="snav")
        st.session_state.active_slide = SLIDES.index(chosen)
    with nav[2]:
        if st.button("▶", use_container_width=True):
            st.session_state.active_slide = (st.session_state.active_slide + 1) % n
            st.rerun()

    s = st.session_state.active_slide

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 0 — OVERVIEW
    # ══════════════════════════════════════════════════════════════════════
    if s == 0:
        # Top KPI chips
        c1, c2, c3, c4, c5 = st.columns(5)
        def mchip(col, label, val, sub, sc="#48bb78"):
            col.markdown(f"""<div class="mchip">
              <div class="mv">{val}</div>
              <div class="ml">{label}</div>
              <div class="ms" style="color:{sc}">{sub}</div>
            </div>""", unsafe_allow_html=True)

        mchip(c1, "Monthly Income", f"₹{income:,}", "Your base")
        mchip(c2, "Total Expenses", f"₹{spending:,}",
              f"{spending/income*100:.0f}% of income" if income else "—",
              "#fc8181" if spending > income*0.8 else "#48bb78")
        mchip(c3, "Monthly Savings", f"₹{savings:,}",
              "⚠️ Deficit!" if savings < 0 else f"{ana['savings_pct']:.0f}% saved",
              "#fc8181" if savings < 0 else "#48bb78")
        mchip(c4, "Savings Target", f"₹{ana['ideal_savings']:,.0f}", "20% rule goal", "#667eea")
        mchip(c5, "Health Score", f"{score}/100", grade, grade_color)

        st.markdown("<br>", unsafe_allow_html=True)
        col_l, col_r = st.columns([3, 2])

        with col_l:
            if plan:
                st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
                st.markdown('<div class="slabel">AI Financial Plan</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="color:#cbd5e0;font-size:14px;line-height:1.8">{plan}</div>',
                            unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            if motiv or "motivation" in tags:
                st.markdown('<div class="motiv-card">', unsafe_allow_html=True)
                st.markdown('<div class="slabel" style="color:#b794f4">💪 Your Motivation</div>',
                            unsafe_allow_html=True)
                st.markdown(f'<div class="motiv-text">{motiv or "You are on the right track. Every step counts!"}</div>',
                            unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            # Health Score gauge
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="slabel">Financial Health Score</div>', unsafe_allow_html=True)
            st.plotly_chart(health_gauge(score), use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div style="text-align:center;color:{grade_color};font-weight:700;font-size:16px">{grade}</div>',
                        unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Focus tags
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="slabel">Focus Areas</div>', unsafe_allow_html=True)
            pills = " ".join(f'<span class="tpill">{TAG_MAP.get(t,t)}</span>' for t in tags)
            st.markdown(pills or "<span style='color:#8892b0'>—</span>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown('<div class="slabel">Budget Health</div>', unsafe_allow_html=True)
            for label, ok, val in [
                ("Needs ≤ 50%", ana["needs_ok"],   f"{ana['needs_pct']:.0f}%"),
                ("Wants ≤ 30%", ana["wants_ok"],   f"{ana['wants_pct']:.0f}%"),
                ("Saving ≥ 20%", ana["savings_ok"], f"{ana['savings_pct']:.0f}%"),
            ]:
                icon  = "✅" if ok else "⚠️"
                color = "#48bb78" if ok else "#f6ad55"
                st.markdown(f"""<div class="row-item" style="border-left-color:{color}">
                  <span class="row-label">{icon} {label}</span>
                  <span class="row-val" style="color:{color}">{val}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 1 — 50/30/20 BREAKDOWN
    # ══════════════════════════════════════════════════════════════════════
    elif s == 1:
        st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
        st.markdown('<div class="slabel">50/30/20 Rule — Your Actual vs Ideal</div>', unsafe_allow_html=True)

        rows = [
            ("🏠 Needs",          ana["needs"],   ana["ideal_needs"],   50, ana["needs_ok"],  "#667eea"),
            ("🎉 Wants",          ana["wants"],   ana["ideal_wants"],   30, ana["wants_ok"],  "#f6ad55"),
            ("💰 Savings & Debt", ana["savings"], ana["ideal_savings"], 20, ana["savings_ok"],"#48bb78"),
        ]
        for label, actual, ideal, rule_pct, ok, color in rows:
            actual_pct = actual / income * 100 if income else 0
            bar_col    = color if ok else "#fc8181"
            status     = "✅ On track" if ok else f"⚠️ {'Over' if actual > ideal else 'Under'} by ₹{abs(actual-ideal):,.0f}"
            st.markdown(f"""<div style="margin-bottom:20px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="color:#e2e8f0;font-size:14px;font-weight:600">{label}</span>
                <span style="color:{bar_col};font-size:13px">{status}</span>
              </div>
              <div style="display:flex;justify-content:space-between;color:#8892b0;font-size:12px;margin-bottom:5px">
                <span>Ideal: ₹{ideal:,.0f} ({rule_pct}%)</span>
                <span>Actual: ₹{actual:,.0f} ({actual_pct:.0f}%)</span>
              </div>
              <div class="rule-bar-wrap">
                <div class="rule-bar-fill" style="width:{min(actual_pct/rule_pct*100,100):.1f}%;background:{bar_col}"></div>
              </div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Suggestions
        suggestions = []
        if not ana["needs_ok"]:
            over = ana["needs"] - ana["ideal_needs"]
            suggestions.append(("🏠 Needs Overspend",
                f"Your needs exceed 50% by ₹{over:,.0f}/month. Consider: cheaper rent/roommates, cooking at home, public transport.", "#fc8181"))
        if not ana["wants_ok"]:
            over = ana["wants"] - ana["ideal_wants"]
            suggestions.append(("🎉 Wants Overspend",
                f"Your wants exceed 30% by ₹{over:,.0f}/month. Try: cancelling unused subscriptions, 30-day no-spend challenge.", "#f6ad55"))
        if not ana["savings_ok"] and income > 0:
            suggestions.append(("💰 Savings Gap",
                f"Saving {ana['savings_pct']:.0f}% vs ideal 20%. Auto-transfer ₹{max(income*0.05,500):,.0f}/month on salary day.", "#667eea"))
        if income <= spending:
            suggestions.append(("💪 Income Boost Ideas",
                "Expenses meet/exceed income. Try freelancing on Fiverr/Upwork, tutoring, selling on Meesho. Even ₹2,000 extra/month changes everything.", "#b794f4"))

        for title, text, color in suggestions:
            st.markdown(f"""<div class="card" style="border-left:3px solid {color}">
              <div class="slabel" style="color:{color}">{title}</div>
              <div style="color:#cbd5e0;font-size:13.5px;line-height:1.7">{text}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""<div class="card card-green">
          <div class="slabel" style="color:#48bb78">⚡ Automate Your Savings</div>
          <div style="color:#cbd5e0;font-size:13.5px;line-height:1.7">
            Set up an auto-transfer of <b style="color:#48bb78">₹{max(ana['ideal_savings'],500):,.0f}/month</b>
            to a separate savings/investment account the day your salary arrives.
            Treat it like a non-negotiable bill — pay yourself first.
          </div>
        </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 2 — SPENDING BREAKDOWN
    # ══════════════════════════════════════════════════════════════════════
    elif s == 2:
        col_l, col_r = st.columns([1, 1])

        with col_l:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="slabel">Spending Split</div>', unsafe_allow_html=True)
            donut_labels = ["🏠 Needs", "🎉 Wants", "💰 Savings"]
            donut_vals   = [max(needs,0), max(wants,0), max(savings,0)]
            if any(v > 0 for v in donut_vals):
                st.plotly_chart(donut_chart(donut_labels, donut_vals, "Budget"),
                                use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            detail_cats = cats.get("categories", {})
            if detail_cats:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="slabel">Category Detail</div>', unsafe_allow_html=True)
                sorted_cats = sorted(detail_cats.items(), key=lambda x: -x[1])
                labels_ = [k.replace("_"," ").title() for k,v in sorted_cats]
                vals_   = [v for k,v in sorted_cats]
                if vals_:
                    st.plotly_chart(hbar_chart(labels_, vals_),
                                    use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

        # CSV-based category breakdown
        if csv_df is not None and not csv_df.empty:
            st.markdown('<div class="card card-teal">', unsafe_allow_html=True)
            st.markdown('<div class="slabel" style="color:#4fd1c5">📂 From Your Bank Statement</div>',
                        unsafe_allow_html=True)
            by_cat = csv_df.groupby("category")["amount"].sum().sort_values(ascending=False)
            fig = go.Figure(go.Pie(
                labels=by_cat.index.str.title().tolist(),
                values=by_cat.values.tolist(),
                hole=0.5,
                marker=dict(colors=COLORS[:len(by_cat)], line=dict(color="#0a0d14", width=2)),
                textinfo="label+percent",
                textfont=dict(color="#e2e8f0", size=11),
            ))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              margin=dict(t=5,b=5,l=0,r=0), height=260,
                              legend=dict(font=dict(color="#8892b0",size=11), bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        # Budget Planner
        detail_cats = cats.get("categories", {})
        if detail_cats:
            st.markdown('<div class="card card-amber">', unsafe_allow_html=True)
            st.markdown('<div class="slabel" style="color:#f6ad55">🎯 Budget Planner — Set Monthly Limits</div>',
                        unsafe_allow_html=True)
            st.caption("Set a budget limit for each category. Red = over budget.")
            cols = st.columns(3)
            new_budgets = {}
            for i, (cat, amt) in enumerate(detail_cats.items()):
                with cols[i % 3]:
                    label  = cat.replace("_"," ").title()
                    limit  = budgets.get(cat, int(amt * 1.1))
                    limit  = st.number_input(f"{label} limit (₹)", 0, income, limit, step=100, key=f"bl_{cat}")
                    new_budgets[cat] = limit
                    over   = amt > limit
                    color  = "#fc8181" if over else "#48bb78"
                    icon   = "🔴" if over else "✅"
                    st.markdown(f'<div style="color:{color};font-size:12px">{icon} Actual: ₹{amt:,} / Limit: ₹{limit:,}</div>',
                                unsafe_allow_html=True)
            if st.button("💾 Save Budget Limits", use_container_width=True):
                st.session_state.budget_limits = new_budgets
                st.success("Budget limits saved!")
            st.markdown('</div>', unsafe_allow_html=True)

        # Adjustable categories
        if detail_cats:
            with st.expander("✏️ Adjust & Recalculate Spending"):
                new_cats = {}
                cols = st.columns(3)
                for i, (cat, amt) in enumerate(detail_cats.items()):
                    with cols[i % 3]:
                        new_cats[cat] = st.number_input(
                            cat.replace("_"," ").title(), 0, income, int(amt), step=100, key=f"dc_{cat}")
                if st.button("🔄 Recalculate Dashboard"):
                    updated = dict(st.session_state.spending_cats)
                    updated["categories"] = new_cats
                    needs_new = sum(v for k,v in new_cats.items() if "need" in k or k in ["rent","food","transport","utilities","insurance","other_needs"])
                    wants_new = sum(v for k,v in new_cats.items() if "want" in k or k in ["entertainment","subscriptions","dining","shopping","other_wants"])
                    updated["needs"] = needs_new
                    updated["wants"] = wants_new
                    st.session_state.spending_cats = updated
                    st.session_state.spending = sum(new_cats.values())
                    st.rerun()

        # Debt section
        if debt.get("has_debt"):
            st.markdown('<div class="card card-red">', unsafe_allow_html=True)
            st.markdown('<div class="slabel" style="color:#fc8181">💳 Debt — Avalanche Strategy</div>',
                        unsafe_allow_html=True)
            total_d = debt.get("total_debt", 0)
            monthly_d = debt.get("monthly_payment", 0)
            st.markdown(f"""<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
              <div class="mchip"><div class="mv">₹{total_d:,}</div><div class="ml">Total Debt</div></div>
              <div class="mchip"><div class="mv">₹{monthly_d:,}</div><div class="ml">Monthly Payment</div></div>
            </div>
            <div style="color:#cbd5e0;font-size:13.5px;line-height:1.7">
              <b>Avalanche Method:</b> Pay minimums on all debts, then throw every extra rupee at the highest-interest debt first.
            </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 3 — GOAL TRACKER
    # ══════════════════════════════════════════════════════════════════════
    elif s == 3:
        target  = int(goal.get("target_amount", 50000))
        months  = int(goal.get("months", 12))
        monthly = int(goal.get("monthly_needed", max(savings, 500)))
        g_name  = goal.get("goal", "Financial Goal")

        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="slabel">Adjust Your Goal</div>', unsafe_allow_html=True)
            target  = st.number_input("🎯 Target Amount (₹)", 0, 10000000, target, 1000)
            months  = st.number_input("⏳ Timeframe (months)", 1, 360, months, 1)
            already = st.number_input("💼 Already Saved (₹)", 0, target, int(st.session_state.goal_saved), 500)
            monthly = st.number_input("📅 Monthly Contribution (₹)", 0, income, monthly, 500)
            st.session_state.goal_saved = already
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            remaining     = max(target - already, 0)
            months_needed = (remaining / monthly) if monthly > 0 else float("inf")
            pct = min(already / target * 100, 100) if target > 0 else 0
            on_track = months_needed <= months if monthly > 0 else False
            status_color = "#48bb78" if on_track else "#f6ad55"
            status_text  = "✅ On track!" if on_track else f"⚠️ Need ₹{int(remaining/months):,}/mo to hit deadline"

            st.markdown(f"""<div class="card">
              <div class="slabel">Goal: {g_name.title()}</div>
              <div style="display:flex;justify-content:space-between;color:#8892b0;font-size:12px;margin-bottom:6px">
                <span>₹{already:,} saved</span>
                <span style="color:{status_color}">{pct:.1f}%</span>
              </div>
              <div class="rule-bar-wrap" style="height:14px">
                <div class="rule-bar-fill" style="width:{pct:.1f}%;height:14px;background:linear-gradient(90deg,#667eea,#48bb78)"></div>
              </div>
              <div style="display:flex;justify-content:space-between;color:#8892b0;font-size:11px;margin-top:4px">
                <span>Start</span><span>₹{target:,} goal</span>
              </div>
              <div style="margin-top:16px;display:grid;grid-template-columns:1fr 1fr;gap:10px">
                <div class="mchip"><div class="mv">₹{remaining:,}</div><div class="ml">Still needed</div></div>
                <div class="mchip">
                  <div class="mv" style="color:{status_color}">
                    {'∞' if months_needed == float('inf') else f'{months_needed:.1f}'}
                  </div>
                  <div class="ml">Months to goal</div>
                  <div class="ms" style="color:#8892b0">at ₹{monthly:,}/mo</div>
                </div>
              </div>
              <div style="margin-top:12px;background:#131929;border-radius:8px;padding:10px 14px;
                          color:{status_color};font-size:13px">{status_text}</div>
            </div>""", unsafe_allow_html=True)

        if monthly > 0 and target > 0:
            horizon = max(months, min(int(months_needed)+2, 120)) if months_needed != float("inf") else months
            x = list(range(0, horizon+1))
            y = [min(already + monthly*m, target) for m in x]
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="slabel">Savings Projection</div>', unsafe_allow_html=True)
            st.plotly_chart(line_chart(x, y, target, already),
                            use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f"""<div class="card card-purple">
          <div class="slabel" style="color:#b794f4">📈 Invest Your Surplus</div>
          <div style="color:#cbd5e0;font-size:13.5px;line-height:1.7">
            Once your emergency fund covers 3-6 months of expenses (₹{int(spending*3):,}–₹{int(spending*6):,}),
            put your surplus into low-cost index funds or SIPs. ₹{monthly:,}/month at 12% annual returns
            grows to <b style="color:#b794f4">₹{int(monthly*((1.01**months-1)/0.01)):,}</b> in {months} months.
          </div>
          <div style="margin-top:12px;font-size:12.5px;color:#8892b0">
            📘 Start early — compound growth is your biggest wealth-building tool.
          </div>
        </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 4 — ACTION PLAN
    # ══════════════════════════════════════════════════════════════════════
    elif s == 4:
        col_l, col_r = st.columns([3, 2])

        with col_l:
            st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
            st.markdown('<div class="slabel">Your 5-Step Action Plan</div>', unsafe_allow_html=True)
            if steps:
                for i, step in enumerate(steps[:5], 1):
                    st.markdown(f"""<div class="astep">
                      <div class="astep-num">{i}</div>
                      <div class="astep-text">{step}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("Complete the chat to generate your action plan.")
            st.markdown('</div>', unsafe_allow_html=True)

            if why:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="slabel">Why This Works</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="color:#cbd5e0;font-size:13.5px;line-height:1.8">{why}</div>',
                            unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="slabel">4 Pillars Checklist</div>', unsafe_allow_html=True)
            pillars = [
                ("📋 Budget (50/30/20)", ana["needs_ok"] and ana["wants_ok"]),
                ("⚡ Automate Savings",  ana["savings_ok"]),
                ("💳 Debt Strategy",     not has_debt or "debt" in tags),
                ("📈 Investing",         has_investment),
            ]
            for label, done in pillars:
                color = "#48bb78" if done else "#f6ad55"
                icon  = "✅" if done else "⬜"
                st.markdown(f"""<div class="row-item" style="border-left-color:{color}">
                  <span class="row-label">{icon} {label}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            all_tips = {
                "emergency_fund": "🛡️ Keep emergency fund in a high-yield savings account (SBI/HDFC Flexi).",
                "sip":            "📈 Start SIP on Zerodha Coin or Groww — minimum ₹100/month.",
                "insurance":      "🏥 Term insurance at your age costs ~₹500/month for ₹1Cr cover.",
                "debt":           "💳 Avalanche: highest interest rate debt first. Always.",
                "overspending":   "✂️ 50/30/20 rule: track every ₹ for 30 days using Walnut or YNAB.",
                "motivation":     "💪 Automate ₹500/month today. Future you will thank you.",
            }
            st.markdown('<div class="card card-green">', unsafe_allow_html=True)
            st.markdown('<div class="slabel" style="color:#48bb78">💡 Pro Tips</div>', unsafe_allow_html=True)
            shown = 0
            for tag in tags:
                if tag in all_tips and shown < 4:
                    st.markdown(f'<div class="row-item" style="border-left-color:#48bb78;margin:4px 0">'
                                f'<span class="row-label" style="font-size:12.5px">{all_tips[tag]}</span>'
                                f'</div>', unsafe_allow_html=True)
                    shown += 1
            st.markdown('</div>', unsafe_allow_html=True)

            if motiv:
                st.markdown('<div class="motiv-card">', unsafe_allow_html=True)
                st.markdown('<div class="slabel" style="color:#b794f4">💪 Remember</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="motiv-text" style="font-size:13px">{motiv}</div>',
                            unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 5 — SAVINGS RECOMMENDATIONS
    # ══════════════════════════════════════════════════════════════════════
    elif s == 5:
        st.markdown('<div class="slabel" style="font-size:12px;color:#667eea;margin-bottom:16px">PERSONALIZED SAVINGS RECOMMENDATIONS</div>',
                    unsafe_allow_html=True)
        recs = savings_recommendations(ana, income, tags, debt)
        for rec in recs:
            st.markdown(f"""<div class="card" style="border-left:3px solid {rec['color']}">
              <div style="font-size:22px;margin-bottom:8px">{rec['icon']}</div>
              <div class="slabel" style="color:{rec['color']}">{rec['title']}</div>
              <div style="color:#cbd5e0;font-size:13.5px;line-height:1.7">{rec['text']}</div>
            </div>""", unsafe_allow_html=True)

        # SIP calculator
        st.markdown('<div class="card card-green">', unsafe_allow_html=True)
        st.markdown('<div class="slabel" style="color:#48bb78">🧮 SIP Returns Calculator</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            sip_amt = st.number_input("Monthly SIP (₹)", 500, 100000, max(500, int(ana["ideal_savings"]*0.5)), 500)
        with col2:
            sip_rate = st.slider("Annual Return (%)", 6, 20, 12)
        with col3:
            sip_years = st.slider("Duration (years)", 1, 30, 10)
        monthly_rate = sip_rate / 100 / 12
        months_sip   = sip_years * 12
        future_val   = sip_amt * ((1 + monthly_rate)**months_sip - 1) / monthly_rate * (1 + monthly_rate)
        invested     = sip_amt * months_sip
        gain         = future_val - invested
        col_a, col_b, col_c = st.columns(3)
        for col, label, val, color in [
            (col_a, "Amount Invested", f"₹{invested:,.0f}", "#8892b0"),
            (col_b, "Estimated Returns", f"₹{gain:,.0f}", "#48bb78"),
            (col_c, "Total Value", f"₹{future_val:,.0f}", "#667eea"),
        ]:
            col.markdown(f'<div class="mchip"><div class="mv" style="color:{color}">{val}</div><div class="ml">{label}</div></div>',
                         unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 6 — INVESTMENT GUIDANCE
    # ══════════════════════════════════════════════════════════════════════
    elif s == 6:
        st.markdown('<div class="card card-purple">', unsafe_allow_html=True)
        st.markdown('<div class="slabel" style="color:#b794f4">📈 Investment Guidance</div>', unsafe_allow_html=True)

        risk = st.radio("Your risk tolerance:", ["conservative","moderate","aggressive"],
                        index=1, horizontal=True)
        guide = INVESTMENT_GUIDE[risk]

        st.markdown(f'<div style="color:#cbd5e0;font-size:13.5px;line-height:1.7;margin:12px 0">{guide["tip"]}</div>',
                    unsafe_allow_html=True)

        alloc_labels = [a[0] for a in guide["allocation"]]
        alloc_vals   = [a[1] for a in guide["allocation"]]
        alloc_fig = go.Figure(go.Pie(
            labels=alloc_labels, values=alloc_vals, hole=0.5,
            marker=dict(colors=COLORS[:len(alloc_labels)], line=dict(color="#0a0d14", width=2)),
            textinfo="label+percent", textfont=dict(color="#e2e8f0", size=12),
        ))
        alloc_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=10,b=10,l=0,r=0), height=250,
                                legend=dict(font=dict(color="#8892b0",size=11), bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(alloc_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

        # Emergency fund guide
        ef_target = spending * 6
        st.markdown(f"""<div class="card card-teal">
          <div class="slabel" style="color:#4fd1c5">🛡️ Emergency Fund Roadmap</div>
          <div style="color:#cbd5e0;font-size:13.5px;line-height:1.7">
            <b>Target:</b> ₹{ef_target:,.0f} (6 months × ₹{spending:,} monthly expenses)<br>
            <b>Where to park it:</b> SBI Liquid Fund, HDFC Flexi Savings FD, or Paytm Money Liquid Fund<br>
            <b>Monthly build-up:</b> If you save ₹{max(500,int(ef_target/12)):,}/month, you'll have it in 12 months.<br>
            <b>Rule:</b> Never invest in equity until your emergency fund is complete.
          </div>
        </div>""", unsafe_allow_html=True)

        # Investment platforms
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="slabel">🏦 Recommended Platforms for India</div>', unsafe_allow_html=True)
        platforms = [
            ("Zerodha Coin", "Direct mutual funds, zero commission", "#667eea"),
            ("Groww", "SIP, stocks, FD — beginner-friendly", "#48bb78"),
            ("INDmoney", "SIP + US stocks + portfolio tracker", "#b794f4"),
            ("PPF (Post Office / Bank)", "₹1.5L/year tax-free, 7.1% guaranteed", "#f6ad55"),
            ("NPS (National Pension)", "Extra ₹50K deduction under 80CCD(1B)", "#4fd1c5"),
        ]
        for name, desc, color in platforms:
            st.markdown(f'<div class="row-item" style="border-left-color:{color}">'
                        f'<span class="row-label"><b style="color:{color}">{name}</b> — {desc}</span>'
                        f'</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 7 — EXPENSE FORECASTING
    # ══════════════════════════════════════════════════════════════════════
    elif s == 7:
        st.markdown('<div class="slabel" style="font-size:12px;color:#667eea;margin-bottom:12px">EXPENSE FORECASTING</div>',
                    unsafe_allow_html=True)

        fdata = forecast_expenses(csv_df)
        if fdata:
            st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
            st.markdown('<div class="slabel">Monthly Spending Trend + 3-Month Forecast</div>', unsafe_allow_html=True)
            st.plotly_chart(forecast_chart(fdata), use_container_width=True, config={"displayModeBar": False})
            avg_forecast = sum(fdata["forecast_vals"]) / len(fdata["forecast_vals"])
            st.markdown(f'<div style="color:#f6ad55;font-size:13.5px">📊 Estimated avg monthly spending next 3 months: <b>₹{avg_forecast:,.0f}</b></div>',
                        unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card card-amber">', unsafe_allow_html=True)
            st.markdown('<div class="slabel" style="color:#f6ad55">⚠️ Upload Bank CSV for Forecasting</div>',
                        unsafe_allow_html=True)
            st.markdown('<div style="color:#cbd5e0;font-size:13.5px">Upload your bank statement CSV in the sidebar to see monthly trends and 3-month expense forecasts.</div>',
                        unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # AI-based simple monthly projection
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="slabel">📅 Manual 3-Month Spending Forecast</div>', unsafe_allow_html=True)
        st.caption("Based on your current spending pattern + estimated growth")
        growth = st.slider("Expected monthly spending growth (%)", -5, 20, 3)
        months_proj = [1, 2, 3]
        proj_vals   = [spending * ((1 + growth/100)**m) for m in months_proj]
        from_now = datetime.now()
        proj_labels = [(from_now + timedelta(days=30*m)).strftime("%b %Y") for m in months_proj]
        proj_fig = go.Figure(go.Bar(
            x=proj_labels, y=proj_vals,
            marker=dict(color=["#667eea","#b794f4","#f6ad55"]),
            text=[f"₹{v:,.0f}" for v in proj_vals],
            textposition="outside", textfont=dict(color="#e2e8f0"),
        ))
        proj_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               yaxis=dict(color="#8892b0",gridcolor="#131929"),
                               xaxis=dict(color="#8892b0"), margin=dict(t=30,b=10,l=50,r=10), height=220)
        st.plotly_chart(proj_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 8 — REPORTS (Download PDF/CSV)
    # ══════════════════════════════════════════════════════════════════════
    elif s == 8:
        st.markdown('<div class="slabel" style="font-size:12px;color:#667eea;margin-bottom:16px">DOWNLOAD FINANCIAL REPORTS</div>',
                    unsafe_allow_html=True)
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown('<div class="card card-green">', unsafe_allow_html=True)
            st.markdown('<div class="slabel" style="color:#48bb78">📊 CSV Report</div>', unsafe_allow_html=True)
            st.markdown('<div style="color:#cbd5e0;font-size:13.5px">Download your complete financial snapshot as a CSV file — income, expenses, goals, debt, and focus areas.</div>',
                        unsafe_allow_html=True)
            csv_report = generate_csv_report(income, ana, cats, goal, debt, tags)
            st.download_button(
                "⬇️ Download CSV Report",
                csv_report,
                file_name=f"FinanceIQ_Report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # CSV bank statement data download
            if csv_df is not None:
                st.markdown('<div class="card card-teal">', unsafe_allow_html=True)
                st.markdown('<div class="slabel" style="color:#4fd1c5">📂 Categorized Bank Transactions</div>',
                            unsafe_allow_html=True)
                csv_tx = csv_df.to_csv(index=False)
                st.download_button(
                    "⬇️ Download Categorized Transactions",
                    csv_tx,
                    file_name=f"FinanceIQ_Transactions_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
            st.markdown('<div class="slabel">📋 Chat Summary Export</div>', unsafe_allow_html=True)
            st.markdown('<div style="color:#cbd5e0;font-size:13.5px">Export your complete chat conversation with FinanceIQ as a text file.</div>',
                        unsafe_allow_html=True)
            chat_text = "\n\n".join(
                f"[{m['role'].upper()}]\n{m['content']}"
                for m in st.session_state.messages
            )
            chat_text = f"FinanceIQ Chat — {datetime.now().strftime('%d %b %Y')}\n{'='*50}\n\n" + chat_text
            chat_text += "\n\n" + "="*50 + "\n⚠️ Disclaimer: Educational guidance only. Not professional financial advice."
            st.download_button(
                "⬇️ Download Chat Transcript",
                chat_text,
                file_name=f"FinanceIQ_Chat_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # JSON data export
            st.markdown('<div class="card card-purple">', unsafe_allow_html=True)
            st.markdown('<div class="slabel" style="color:#b794f4">🗂️ Full Data (JSON)</div>', unsafe_allow_html=True)
            export_data = {
                "income": income, "spending": spending,
                "analysis": {k: round(v,2) if isinstance(v, float) else v for k,v in ana.items()},
                "categories": cats.get("categories",{}),
                "goal": goal, "debt": debt, "tags": tags,
                "health_score": score,
                "exported_at": datetime.now().isoformat(),
                "disclaimer": "Educational guidance only. Not professional financial advice."
            }
            st.download_button(
                "⬇️ Download JSON Data",
                json.dumps(export_data, indent=2),
                file_name=f"FinanceIQ_Data_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💰 FinanceIQ")
    st.caption("Smart finance guide for 18-25 year olds")
    st.divider()

    income   = st.number_input("Monthly Income (₹)", min_value=0, step=500)
    spending = st.number_input("Estimated Monthly Spending (₹)", min_value=0, step=500)

    if st.button("🚀 Start My Plan", use_container_width=True, type="primary"):
        if income > 0:
            for k, v in defaults.items():
                st.session_state[k] = v
            st.session_state.income   = income
            st.session_state.spending = spending
            msg = f"My monthly income is ₹{income} and I spend about ₹{spending}/month. Help me build a solid financial plan."
            st.session_state.messages.append({"role": "user", "content": msg})
            st.session_state.started = True
            st.rerun()
        else:
            st.warning("Enter your income first!")

    if st.button("🔄 Reset", use_container_width=True):
        # Save current session to history before reset
        if st.session_state.messages:
            preview = next((m["content"][:80] for m in st.session_state.messages if m["role"] == "assistant"), "Session")
            st.session_state.chat_sessions.append({
                "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                "preview": preview,
                "messages": list(st.session_state.messages)
            })
        for k, v in defaults.items():
            if k != "chat_sessions":
                st.session_state[k] = v
        st.rerun()

    # ── CSV Upload ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("**📂 Bank Statement (CSV)**")
    uploaded_csv = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
    if uploaded_csv:
        df = parse_csv_statement(uploaded_csv)
        if df is not None and not df.empty:
            st.session_state.csv_data = df
            st.success(f"✅ {len(df)} transactions loaded")
        else:
            st.warning("Couldn't parse this CSV. Try exporting from your bank app.")

    # ── PDF Upload + Q&A ─────────────────────────────────────────────────
    st.divider()
    st.markdown("**📄 Financial PDF Q&A**")
    uploaded_pdf = st.file_uploader("Upload PDF (statement, policy, etc.)", type=["pdf"],
                                    label_visibility="collapsed")
    if uploaded_pdf:
        try:
            import pdfplumber
            with pdfplumber.open(uploaded_pdf) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages[:10])
            st.session_state.pdf_doc_text = text
            st.success(f"✅ PDF loaded ({len(text)} chars)")
        except ImportError:
            # Fallback: read raw bytes and encode
            raw = uploaded_pdf.read()
            st.session_state.pdf_doc_text = f"[PDF binary — {len(raw)} bytes. pdfplumber not installed.]"
            st.info("Install pdfplumber for better PDF reading: pip install pdfplumber")

    if st.session_state.pdf_doc_text and not st.session_state.pdf_doc_text.startswith("[PDF binary"):
        pdf_q = st.text_input("Ask about the PDF...", placeholder="What is my policy premium?",
                              key="pdf_q_input")
        if pdf_q and st.button("Ask", key="pdf_ask"):
            with st.spinner("Reading PDF..."):
                answer = answer_pdf_question(pdf_q, st.session_state.pdf_doc_text,
                                             st.session_state.pdf_qa_messages)
            st.session_state.pdf_qa_messages.append({"role": "user",    "content": pdf_q})
            st.session_state.pdf_qa_messages.append({"role": "assistant","content": answer})
            st.rerun()

        if st.session_state.pdf_qa_messages:
            for msg in st.session_state.pdf_qa_messages[-4:]:
                role_icon = "🙋" if msg["role"] == "user" else "🤖"
                st.markdown(f'<div style="font-size:12px;color:#8892b0;margin:4px 0">{role_icon} {msg["content"][:200]}</div>',
                            unsafe_allow_html=True)

    # ── Slide navigation (when dashboard is shown) ───────────────────────
    if st.session_state.show_dashboard:
        st.divider()
        st.markdown("**Jump to slide:**")
        SLIDES = ["📊 Overview","📐 50/30/20","🍩 Spending","🎯 Goal","🚀 Action Plan",
                  "💡 Savings","📈 Investments","🔮 Forecast","📄 Reports"]
        for i, name in enumerate(SLIDES):
            if st.button(name, key=f"sb_{i}", use_container_width=True):
                st.session_state.active_slide = i
                st.rerun()

    # ── Chat History ─────────────────────────────────────────────────────
    if st.session_state.chat_sessions:
        st.divider()
        st.markdown("**🕘 Previous Sessions**")
        for i, sess in enumerate(reversed(st.session_state.chat_sessions[-5:])):
            st.markdown(f"""<div class="chat-history-item">
              <div class="chat-history-date">{sess['date']}</div>
              <div class="chat-history-preview">{sess['preview'][:90]}…</div>
            </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("""<div style='color:#3d4270;font-size:11px;text-align:center'>
    Powered by Groq · LLaMA 3.3<br>
    Built with ❤️ for young India
    </div>""", unsafe_allow_html=True)


# ─── MAIN AREA ───────────────────────────────────────────────────────────────
st.markdown("""<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
  <span style="font-size:28px">💰</span>
  <div>
    <span style="color:#e2e8f0;font-size:22px;font-weight:700">FinanceIQ</span>
    <span style="color:#667eea;font-size:13px;margin-left:10px">Personal Finance Agent</span>
  </div>
</div>""", unsafe_allow_html=True)
st.caption("AI-powered · 50/30/20 Rule · Debt Strategy · Goal Tracking · Powered by Groq + LLaMA 3.3")

show_disclaimer()

if not st.session_state.started:
    # Welcome + Sample Prompts
    st.markdown("""<div class="card" style="text-align:center;padding:48px 32px;margin-top:20px">
      <div style="font-size:52px;margin-bottom:16px">💸</div>
      <div style="color:#e2e8f0;font-size:22px;font-weight:700;margin-bottom:10px">
        Your money. Your future. Your plan.
      </div>
      <div style="color:#8892b0;font-size:14px;line-height:1.9;max-width:500px;margin:0 auto">
        Chat with your AI finance advisor →<br>
        Get a personalized 50/30/20 budget, debt strategy,<br>
        goal tracker & investing roadmap — all in one dashboard.
      </div>
      <div style="display:flex;justify-content:center;gap:20px;margin-top:24px;flex-wrap:wrap">
        <span class="tpill">📋 50/30/20 Budget</span>
        <span class="tpill">⚡ Automation</span>
        <span class="tpill">💳 Debt Strategy</span>
        <span class="tpill">📈 Investing</span>
        <span class="tpill">🏥 Insurance</span>
        <span class="tpill">🛡️ Emergency Fund</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # Sample prompts
    st.markdown('<div class="slabel" style="margin-top:24px">💬 TRY THESE SAMPLE QUESTIONS</div>',
                unsafe_allow_html=True)
    for prompt in SAMPLE_PROMPTS:
        if st.button(f"➤ {prompt}", key=f"sp_{prompt[:20]}", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            # Try to parse income from prompt
            m = re.search(r"₹([\d,]+)", prompt)
            if m:
                inc = int(m.group(1).replace(",",""))
                st.session_state.income = inc
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.started = True
            st.rerun()

elif not st.session_state.show_dashboard:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        *st.session_state.messages
                    ],
                    max_tokens=900, temperature=0.7
                )
                reply = response.choices[0].message.content
                st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})

        if "YOUR PLAN" in reply and "ACTION STEPS" in reply:
            st.session_state.final_reply   = reply
            sc = parse_json_block(reply, "📦 SPENDING_JSON:")
            st.session_state.spending_cats = sc
            st.session_state.needs         = sc.get("needs", 0)
            st.session_state.wants         = sc.get("wants", 0)
            st.session_state.goal_data     = parse_json_block(reply, "🎯 GOAL_JSON:")
            st.session_state.debt_data     = parse_json_block(reply, "💳 DEBT_JSON:")
            st.session_state.tags          = parse_tags(reply)
            st.session_state.show_dashboard= True
            st.rerun()

    user_input = st.chat_input("Type your answer...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

else:
    show_dashboard()
