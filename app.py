import streamlit as st
from groq import Groq
import plotly.graph_objects as go
import plotly.express as px
import re, json

# ─── CONFIG ──────────────────────────────────────────────────────────────────
api_key = st.secrets["GROQ_API_KEY"]
client  = Groq(api_key=api_key)

SYSTEM_PROMPT = """
You are a friendly Personal Finance Decision Agent for 18-22 year olds in India.

You already know:
- Monthly Income: provided by user
- Monthly Spending: provided by user (total)

YOUR CONVERSATION FLOW — ask ONE question at a time in this exact order:

1. Ask: "What are your main spending categories? (e.g., rent, food, transport, entertainment, subscriptions) Give rough ₹ amounts for each."

2. After they share categories:
   - If spending >= income:
     Say: "Oops! Your expenses (₹X) meet or exceed your income (₹Y). Let's fix this."
     Ask: "Which expense can you reduce first?"
   - If spending < income:
     Say "Great! You have ₹Z left. Let's put it to work."

3. Ask: "Do you have an emergency fund? (Ideally 3-6 months of expenses saved)"

4. Ask: "What's your risk tolerance? (low / medium / high)"

5. Ask: "Do you have health or life insurance?"

6. Ask: "What's your main financial goal? (e.g., build savings, invest, buy something, pay debt)"
   Also ask: "By when do you want to achieve this goal? (e.g., 6 months, 1 year, 3 years)"
   And: "Target amount for the goal? (₹)"

AFTER all questions, reply in this EXACT format (no deviation):

---
📊 YOUR FINANCIAL SNAPSHOT
- Income: ₹X/month
- Total Expenses: ₹Y/month
- Available to Save/Invest: ₹Z/month

💡 YOUR PLAN
[recommendation]

✅ WHY THIS WORKS
[2-3 lines]

🚀 ACTION STEPS
1. [Step 1]
2. [Step 2]
3. [Step 3]

📦 SPENDING_JSON: {"rent":X,"food":X,"transport":X,"entertainment":X,"subscriptions":X,"other":X}
🎯 GOAL_JSON: {"goal":"description","target_amount":X,"months":X,"monthly_needed":X}
🏷️ TAGS: emergency_fund,sip,insurance
---

SPENDING_JSON must contain only the categories user mentioned (use "other" for remainder).
GOAL_JSON monthly_needed = target_amount / months.
Be warm, short, encouraging. One question at a time.
"""

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="FinanceIQ", page_icon="💰", layout="wide")

# ─── CUSTOM CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global */
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #1a1d27; border-right: 1px solid #2d3148; }
h1,h2,h3 { color: #e2e8f0 !important; }

/* Slide cards */
.slide-card {
    background: #1e2130;
    border: 1px solid #2d3148;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
    animation: fadeUp 0.4s ease;
}
@keyframes fadeUp {
    from { opacity:0; transform:translateY(12px); }
    to   { opacity:1; transform:translateY(0); }
}

/* Metric chips */
.metric-chip {
    background: #252840;
    border: 1px solid #3d4270;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
}
.metric-chip .label { color:#8892b0; font-size:13px; margin-bottom:4px; }
.metric-chip .value { color:#e2e8f0; font-size:22px; font-weight:700; }
.metric-chip .sub   { font-size:11px; margin-top:4px; }

/* Tag pills */
.tag-pill {
    display:inline-block;
    background: #1d3557;
    color: #90cdf4;
    border: 1px solid #2b4c7e;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 13px;
    margin: 4px;
}

/* Goal bar */
.goal-bar-wrap {
    background: #252840;
    border-radius: 10px;
    height: 12px;
    overflow: hidden;
    margin: 8px 0;
}
.goal-bar-fill {
    height: 12px;
    border-radius: 10px;
    background: linear-gradient(90deg,#667eea,#764ba2);
    transition: width 0.6s ease;
}

/* Section title */
.section-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #667eea;
    font-weight: 600;
    margin-bottom: 16px;
}

/* Slide nav dots */
.nav-dot { display:inline-block; width:10px; height:10px;
           border-radius:50%; background:#2d3148; margin:0 4px; cursor:pointer; }
.nav-dot.active { background:#667eea; }

/* Action step */
.action-step {
    display:flex; align-items:flex-start; gap:12px;
    background:#252840; border-radius:10px; padding:12px 16px; margin:8px 0;
}
.step-num {
    background:#667eea; color:#fff; border-radius:50%;
    width:26px; height:26px; display:flex; align-items:center;
    justify-content:center; font-size:12px; font-weight:700; flex-shrink:0;
}
.step-text { color:#cbd5e0; font-size:14px; line-height:1.5; }

/* Alloc row */
.alloc-row {
    display:flex; justify-content:space-between; align-items:center;
    background:#252840; border-radius:10px; padding:12px 16px; margin:6px 0;
    border-left: 3px solid #667eea;
}
.alloc-label { color:#cbd5e0; font-size:14px; }
.alloc-amt   { color:#90cdf4; font-weight:700; font-size:15px; }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
defaults = {
    "messages": [], "started": False, "income": 0, "spending": 0,
    "show_dashboard": False, "final_reply": "",
    "spending_cats": {}, "goal_data": {}, "tags": [],
    "active_slide": 0,
    "goal_saved": 0,   # user-adjustable current saved amount
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

def parse_action_steps(reply):
    steps = []
    for line in reply.split("\n"):
        m = re.match(r"^\s*\d+\.\s+(.+)", line)
        if m:
            steps.append(m.group(1).strip())
    return steps

def parse_plan(reply):
    m = re.search(r"💡 YOUR PLAN\n(.+?)(\n\n|✅)", reply, re.DOTALL)
    return m.group(1).strip() if m else ""

def parse_why(reply):
    m = re.search(r"✅ WHY THIS WORKS\n(.+?)(\n\n|🚀)", reply, re.DOTALL)
    return m.group(1).strip() if m else ""

# ─── CHART HELPERS ───────────────────────────────────────────────────────────
def spending_pie(cats):
    if not cats:
        return None
    labels = [k.title() for k in cats.keys()]
    values = list(cats.values())
    colors = ["#667eea","#764ba2","#f093fb","#4facfe","#00f2fe","#43e97b","#fa709a"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors[:len(labels)], line=dict(color="#0f1117", width=2)),
        textinfo="label+percent",
        textfont=dict(color="#e2e8f0", size=12),
        hovertemplate="<b>%{label}</b><br>₹%{value:,}<br>%{percent}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=10,r=10),
        showlegend=True,
        legend=dict(font=dict(color="#8892b0", size=11), bgcolor="rgba(0,0,0,0)"),
        height=280
    )
    return fig

def alloc_bar(alloc_dict, income):
    labels = list(alloc_dict.keys())
    values = list(alloc_dict.values())
    pcts   = [v/income*100 for v in values]
    colors = ["#667eea","#43e97b","#f093fb","#fa709a","#4facfe"]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors[:len(labels)], line=dict(width=0)),
        text=[f"₹{v:,} ({p:.0f}%)" for v,p in zip(values,pcts)],
        textposition="outside", textfont=dict(color="#e2e8f0", size=12),
        hovertemplate="<b>%{y}</b>: ₹%{x:,}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                   color="#8892b0"),
        yaxis=dict(showgrid=False, color="#cbd5e0", tickfont=dict(size=13)),
        margin=dict(t=10,b=10,l=10,r=80), height=max(160, 55*len(labels))
    )
    return fig

def goal_projection_chart(monthly_needed, months, target):
    x = list(range(0, months+1))
    y = [min(monthly_needed * m, target) for m in x]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers",
        line=dict(color="#667eea", width=2),
        marker=dict(color="#764ba2", size=5),
        fill="tozeroy", fillcolor="rgba(102,126,234,0.12)",
        hovertemplate="Month %{x}: ₹%{y:,}<extra></extra>",
        name="Projected savings"
    ))
    fig.add_hline(y=target, line_dash="dash", line_color="#43e97b",
                  annotation_text=f"Target ₹{target:,}", annotation_font_color="#43e97b")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Months", color="#8892b0", gridcolor="#1e2130"),
        yaxis=dict(title="₹ Saved", color="#8892b0", gridcolor="#1e2130"),
        margin=dict(t=10,b=40,l=60,r=20), height=240,
        showlegend=False
    )
    return fig

# ─── DASHBOARD ───────────────────────────────────────────────────────────────
TAG_LABELS = {
    "emergency_fund": "🛡️ Emergency Fund",
    "sip":            "📈 Mutual Fund SIP",
    "insurance":      "🏥 Insurance",
    "debt":           "💳 Pay Debt First",
    "overspending":   "✂️ Cut Spending",
    "savings":        "💰 Build Savings",
    "investing":      "📊 Invest",
}

def show_dashboard():
    income   = st.session_state.income
    spending = st.session_state.spending
    savings  = max(income - spending, 0)
    cats     = st.session_state.spending_cats
    goal     = st.session_state.goal_data
    tags     = st.session_state.tags
    reply    = st.session_state.final_reply

    plan  = parse_plan(reply)
    why   = parse_why(reply)
    steps = parse_action_steps(reply)

    spend_pct = min(spending / income, 1.0) if income else 0

    # Allocation split
    alloc = {}
    rem = savings
    if "emergency_fund" in tags and rem > 0:
        ef = round(rem * 0.5); alloc["🛡️ Emergency Fund"] = ef; rem -= ef
    if "insurance" in tags and rem > 0:
        ins = round(rem * 0.2); alloc["🏥 Insurance"] = ins; rem -= ins
    if ("sip" in tags or "investing" in tags) and rem > 0:
        alloc["📈 SIP / Invest"] = rem; rem = 0
    if not alloc and savings > 0:
        alloc["💸 Savings"] = savings

    # ── SLIDE NAV ──────────────────────────────────────────────────────────
    slide_names = ["📊 Overview", "🍩 Spending", "🗂️ Allocation", "🎯 Goal Tracker", "🚀 Action Plan"]
    n = len(slide_names)

    # Prev / dot nav / Next in one row
    nav_cols = st.columns([1, 6, 1])
    with nav_cols[0]:
        if st.button("◀", use_container_width=True):
            st.session_state.active_slide = (st.session_state.active_slide - 1) % n
            st.rerun()
    with nav_cols[1]:
        # Dot buttons via selectbox (clean & adjustable)
        chosen = st.radio("", slide_names, index=st.session_state.active_slide,
                          horizontal=True, label_visibility="collapsed",
                          key="slide_radio")
        st.session_state.active_slide = slide_names.index(chosen)
    with nav_cols[2]:
        if st.button("▶", use_container_width=True):
            st.session_state.active_slide = (st.session_state.active_slide + 1) % n
            st.rerun()

    slide = st.session_state.active_slide

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 0 — OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    if slide == 0:
        st.markdown('<div class="slide-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Financial Snapshot</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        def chip(col, label, value, sub, sub_color="#43e97b"):
            col.markdown(f"""
            <div class="metric-chip">
              <div class="label">{label}</div>
              <div class="value">{value}</div>
              <div class="sub" style="color:{sub_color}">{sub}</div>
            </div>""", unsafe_allow_html=True)

        chip(c1, "Monthly Income", f"₹{income:,}", "100% base")
        chip(c2, "Total Expenses", f"₹{spending:,}",
             f"{spend_pct*100:.0f}% of income",
             "#fa709a" if spend_pct > 0.8 else "#43e97b")
        chip(c3, "Available to Save", f"₹{savings:,}",
             "⚠️ Overspending!" if savings <= 0 else f"{(savings/income*100):.0f}% surplus",
             "#fa709a" if savings <= 0 else "#43e97b")

        st.markdown("<br>", unsafe_allow_html=True)

        # Health bar
        st.markdown('<div class="section-title">Budget Health</div>', unsafe_allow_html=True)
        bar_color = "#43e97b" if spend_pct < 0.7 else ("#f6ad55" if spend_pct < 0.9 else "#fc8181")
        st.markdown(f"""
        <div class="goal-bar-wrap">
          <div class="goal-bar-fill" style="width:{spend_pct*100:.1f}%;background:{bar_color}"></div>
        </div>
        <div style="display:flex;justify-content:space-between;color:#8892b0;font-size:12px;margin-top:4px;">
          <span>Expenses {spend_pct*100:.0f}%</span>
          <span>Savings {(1-spend_pct)*100:.0f}%</span>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Tags
        st.markdown('<div class="section-title">Your Focus Areas</div>', unsafe_allow_html=True)
        pills = " ".join(f'<span class="tag-pill">{TAG_LABELS.get(t, t)}</span>' for t in tags)
        st.markdown(pills, unsafe_allow_html=True)

        # Plan summary
        if plan:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">AI Recommendation</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="color:#cbd5e0;font-size:15px;line-height:1.7">{plan}</div>',
                        unsafe_allow_html=True)
        if why:
            st.markdown(f'<div style="color:#8892b0;font-size:13px;margin-top:10px;font-style:italic">{why}</div>',
                        unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 1 — SPENDING BREAKDOWN
    # ══════════════════════════════════════════════════════════════════════════
    elif slide == 1:
        st.markdown('<div class="slide-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Spending Breakdown</div>', unsafe_allow_html=True)

        if cats:
            fig = spending_pie(cats)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            st.markdown('<div class="section-title" style="margin-top:16px">Category Details</div>',
                        unsafe_allow_html=True)
            for cat, amt in sorted(cats.items(), key=lambda x: -x[1]):
                pct = amt / spending * 100 if spending else 0
                st.markdown(f"""
                <div class="alloc-row">
                  <span class="alloc-label">🔸 {cat.title()}</span>
                  <span class="alloc-amt">₹{amt:,} &nbsp;<span style="color:#8892b0;font-size:12px">({pct:.0f}%)</span></span>
                </div>""", unsafe_allow_html=True)

            # Adjustable: user can tweak category amounts live
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("✏️ Adjust spending categories"):
                new_cats = {}
                for cat, amt in cats.items():
                    new_val = st.slider(cat.title(), 0, income, int(amt), step=100, key=f"cat_{cat}")
                    new_cats[cat] = new_val
                if st.button("🔄 Recalculate"):
                    st.session_state.spending_cats = new_cats
                    st.session_state.spending = sum(new_cats.values())
                    st.rerun()
        else:
            st.info("No spending categories detected. Make sure to list them during the chat.")

        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 2 — ALLOCATION
    # ══════════════════════════════════════════════════════════════════════════
    elif slide == 2:
        st.markdown('<div class="slide-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Monthly Savings Allocation</div>', unsafe_allow_html=True)

        if savings > 0:
            # Adjustable sliders for allocation
            st.markdown("**Drag to adjust your allocation split:**")
            adj = {}
            rem2 = savings

            if "emergency_fund" in tags:
                ef_pct = st.slider("🛡️ Emergency Fund %", 0, 100, 50, key="ef_pct")
                ef_amt = round(savings * ef_pct / 100)
                adj["🛡️ Emergency Fund"] = ef_amt
                rem2 -= ef_amt
            if "insurance" in tags and rem2 > 0:
                ins_pct = st.slider("🏥 Insurance %", 0, 100, 20, key="ins_pct")
                ins_amt = round(savings * ins_pct / 100)
                adj["🏥 Insurance"] = min(ins_amt, rem2)
                rem2 -= adj["🏥 Insurance"]
            if rem2 > 0:
                adj["📈 SIP / Invest"] = rem2

            # Bar chart
            fig2 = alloc_bar(adj, income)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

            # Rows
            for label, amt in adj.items():
                st.markdown(f"""
                <div class="alloc-row">
                  <span class="alloc-label">{label}</span>
                  <span class="alloc-amt">₹{amt:,}/mo</span>
                </div>""", unsafe_allow_html=True)

            st.markdown(f"""<div style="color:#8892b0;font-size:12px;margin-top:12px;text-align:right">
                Total allocated: ₹{sum(adj.values()):,} / ₹{savings:,} surplus</div>""",
                unsafe_allow_html=True)
        else:
            st.error("⚠️ No surplus to allocate. Reduce expenses first.")

        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 3 — GOAL TRACKER
    # ══════════════════════════════════════════════════════════════════════════
    elif slide == 3:
        st.markdown('<div class="slide-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Goal Tracker</div>', unsafe_allow_html=True)

        target  = goal.get("target_amount", 0)
        months  = goal.get("months", 12)
        monthly = goal.get("monthly_needed", savings)
        g_name  = goal.get("goal", "Financial Goal")

        # Adjustable inputs
        col_a, col_b = st.columns(2)
        with col_a:
            target  = st.number_input("🎯 Goal Amount (₹)", min_value=0, value=int(target) or 50000, step=1000)
            months  = st.number_input("⏳ Timeframe (months)", min_value=1, value=int(months) or 12, step=1)
        with col_b:
            already = st.number_input("💼 Already Saved (₹)", min_value=0,
                                      value=int(st.session_state.goal_saved), step=500)
            st.session_state.goal_saved = already
            monthly = st.number_input("📅 Monthly Contribution (₹)", min_value=0,
                                      value=int(monthly) or int(savings), step=500)

        remaining_goal = max(target - already, 0)
        months_needed  = (remaining_goal / monthly) if monthly > 0 else float("inf")
        pct_done       = min(already / target * 100, 100) if target > 0 else 0

        st.markdown(f"""
        <div style="margin-top:16px">
          <div style="display:flex;justify-content:space-between;color:#8892b0;font-size:13px;margin-bottom:6px">
            <span>Progress toward: <b style="color:#e2e8f0">{g_name.title()}</b></span>
            <span style="color:#667eea">{pct_done:.1f}% done</span>
          </div>
          <div class="goal-bar-wrap">
            <div class="goal-bar-fill" style="width:{pct_done:.1f}%"></div>
          </div>
          <div style="display:flex;justify-content:space-between;color:#8892b0;font-size:11px;margin-top:4px">
            <span>₹{already:,} saved</span><span>₹{target:,} target</span>
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.markdown(f"""<div class="metric-chip">
          <div class="label">Still Needed</div>
          <div class="value">₹{remaining_goal:,}</div>
        </div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class="metric-chip">
          <div class="label">Months to Goal</div>
          <div class="value">{'∞' if months_needed == float('inf') else f'{months_needed:.1f}'}</div>
          <div class="sub" style="color:#8892b0">at ₹{monthly:,}/mo</div>
        </div>""", unsafe_allow_html=True)

        # Projection chart
        if monthly > 0 and target > 0:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">Savings Projection</div>', unsafe_allow_html=True)
            horizon = max(months, int(months_needed) + 1) if months_needed != float("inf") else months
            x = list(range(0, horizon + 1))
            y = [min(already + monthly * m, target) for m in x]
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=x, y=y, mode="lines+markers",
                line=dict(color="#667eea", width=2),
                marker=dict(color="#764ba2", size=4),
                fill="tozeroy", fillcolor="rgba(102,126,234,0.1)",
                hovertemplate="Month %{x}: ₹%{y:,.0f}<extra></extra>"
            ))
            fig3.add_hline(y=target, line_dash="dash", line_color="#43e97b",
                           annotation_text=f"Target ₹{target:,}",
                           annotation_font_color="#43e97b")
            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="Months", color="#8892b0", gridcolor="#1e2130"),
                yaxis=dict(title="₹ Saved", color="#8892b0", gridcolor="#1e2130"),
                margin=dict(t=10,b=40,l=60,r=20), height=220, showlegend=False
            )
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SLIDE 4 — ACTION PLAN
    # ══════════════════════════════════════════════════════════════════════════
    elif slide == 4:
        st.markdown('<div class="slide-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Your Action Plan</div>', unsafe_allow_html=True)

        if steps:
            for i, step in enumerate(steps, 1):
                st.markdown(f"""
                <div class="action-step">
                  <div class="step-num">{i}</div>
                  <div class="step-text">{step}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No action steps found.")

        if why:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">Why This Works</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="color:#cbd5e0;font-size:14px;line-height:1.8">{why}</div>',
                        unsafe_allow_html=True)

        # Quick finance tips based on tags
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Quick Tips</div>', unsafe_allow_html=True)
        tips = {
            "emergency_fund": "💡 Even ₹500/month toward an emergency fund is a great start.",
            "sip":            "💡 SIPs as low as ₹100/month are available on Zerodha Coin, Groww.",
            "insurance":      "💡 Term insurance at 22 can cost as little as ₹500/month.",
            "debt":           "💡 Pay highest-interest debt first (avalanche method).",
            "overspending":   "💡 Try the 50-30-20 rule: 50% needs, 30% wants, 20% savings.",
        }
        for tag in tags:
            if tag in tips:
                st.markdown(f'<div class="alloc-row"><span class="alloc-label">{tips[tag]}</span></div>',
                            unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💰 FinanceIQ")
    st.caption("Smart finance guide for 18-22 year olds")
    st.divider()
    income  = st.number_input("Monthly Income (₹)", min_value=0, step=500)
    spending = st.number_input("Monthly Spending (₹)", min_value=0, step=500)

    if st.button("🚀 Start", use_container_width=True, type="primary"):
        if income > 0:
            for k, v in defaults.items():
                st.session_state[k] = v
            st.session_state.income   = income
            st.session_state.spending = spending
            msg = f"My monthly income is ₹{income} and I spend about ₹{spending}/month. Help me plan my finances."
            st.session_state.messages.append({"role": "user", "content": msg})
            st.session_state.started = True
            st.rerun()
        else:
            st.warning("Enter your income first!")

    if st.button("🔄 Reset", use_container_width=True):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()

    if st.session_state.show_dashboard:
        st.divider()
        st.markdown("### 📌 Jump to Slide")
        slide_names = ["📊 Overview","🍩 Spending","🗂️ Allocation","🎯 Goal Tracker","🚀 Action Plan"]
        for i, name in enumerate(slide_names):
            if st.button(name, key=f"sb_{i}", use_container_width=True):
                st.session_state.active_slide = i
                st.rerun()

# ─── MAIN ────────────────────────────────────────────────────────────────────
st.markdown("## 💰 FinanceIQ &nbsp;<span style='font-size:14px;color:#667eea'>Personal Finance Agent</span>",
            unsafe_allow_html=True)
st.caption("AI-powered financial planning for 18-22 year olds · Powered by Groq + LLaMA 3.3")

if not st.session_state.started:
    st.markdown("""
    <div class="slide-card" style="text-align:center;padding:40px">
      <div style="font-size:48px;margin-bottom:16px">💸</div>
      <div style="color:#e2e8f0;font-size:20px;font-weight:600;margin-bottom:8px">
        Take control of your money
      </div>
      <div style="color:#8892b0;font-size:14px;line-height:1.7">
        Enter your income & spending in the sidebar,<br>
        then chat with your AI finance advisor.<br>
        Get a personalized dashboard with charts, goal tracker & action plan.
      </div>
    </div>""", unsafe_allow_html=True)

elif not st.session_state.show_dashboard:
    # Chat view
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        *st.session_state.messages
                    ],
                    max_tokens=800, temperature=0.7
                )
                reply = response.choices[0].message.content
                st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})

        if "YOUR PLAN" in reply and "ACTION STEPS" in reply:
            st.session_state.final_reply    = reply
            st.session_state.spending_cats  = parse_json_block(reply, "📦 SPENDING_JSON:")
            st.session_state.goal_data      = parse_json_block(reply, "🎯 GOAL_JSON:")
            st.session_state.tags           = parse_tags(reply)
            st.session_state.show_dashboard = True
            st.rerun()

    user_input = st.chat_input("Type your answer...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

else:
    show_dashboard()
