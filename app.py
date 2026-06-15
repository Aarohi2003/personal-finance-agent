import streamlit as st
from groq import Groq

api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)

SYSTEM_PROMPT = """
You are a friendly Personal Finance Decision Agent for 18-22 year olds in India.

You already know:
- Monthly Income: provided by user
- Monthly Spending: provided by user (total)

YOUR CONVERSATION FLOW — ask ONE question at a time in this exact order:

1. Ask: "What are your main spending categories? (e.g., rent, food, transport, entertainment, subscriptions, etc.) Give rough amounts for each."

2. After they share categories:
   - Internally sum the spending.
   - If spending >= income:
     Say: "Oops! Your expenses (₹X) are meeting or exceeding your income (₹Y). That leaves ₹0 or negative for savings. Let's fix this together."
     Ask: "Which of these expenses do you think you could reduce? (e.g., eating out less, cancelling subscriptions)"
   - If spending < income:
     Say "Great! You have ₹Z left after expenses. Let's make it work harder for you."
     Then proceed.

3. Ask: "Do you have an emergency fund? (Ideally 3-6 months of expenses saved)"

4. Ask: "What's your risk tolerance? (low / medium / high)"

5. Ask: "Do you have any health or life insurance?"

6. Ask: "What's your main financial goal right now? (e.g., build savings, invest, buy something, pay debt)"

AFTER all 6 questions, give a FINAL RECOMMENDATION in this EXACT format:

---
📊 YOUR FINANCIAL SNAPSHOT
- Income: ₹X/month
- Total Expenses: ₹Y/month
- Available to Save/Invest: ₹Z/month

💡 YOUR PLAN
[One clear recommendation: Emergency Fund / SIP / Insurance / combination]

✅ WHY THIS WORKS
[2-3 lines explaining why this suits their situation]

🚀 ACTION STEPS
1. [Step 1]
2. [Step 2]
3. [Step 3]

🏷️ TAGS: [comma-separated list of relevant tags from: emergency_fund, sip, insurance, debt, overspending, savings, investing]
---

Be short, warm, and encouraging. Never lecture. One question at a time only.
"""

st.set_page_config(page_title="Finance Agent", page_icon="💰")
st.title("💰 Personal Finance Agent")
st.caption("Smart financial guide for 18-22 year olds")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.started = False
    st.session_state.income = 0
    st.session_state.spending = 0
    st.session_state.show_dashboard = False
    st.session_state.final_reply = ""

def extract_dashboard_data(reply, income, spending):
    """Parse the final reply to extract structured dashboard data."""
    tags = []
    if "TAGS:" in reply:
        tag_line = reply.split("TAGS:")[-1].strip().split("\n")[0]
        tags = [t.strip() for t in tag_line.replace("---","").split(",") if t.strip()]

    savings = max(income - spending, 0)
    return {
        "income": income,
        "spending": spending,
        "savings": savings,
        "tags": tags,
        "reply": reply
    }

def show_dashboard(data):
    st.divider()
    st.header("📊 Your Financial Dashboard")

    income = data["income"]
    spending = data["spending"]
    savings = data["savings"]

    # Metrics row
    col1, col2, col3 = st.columns(3)
    col1.metric("💵 Monthly Income", f"₹{income:,}")
    col2.metric("🛒 Monthly Expenses", f"₹{spending:,}",
                delta=f"-₹{spending:,}", delta_color="inverse")
    col3.metric("💰 Available to Save", f"₹{savings:,}",
                delta=f"{'⚠️ Overspending!' if savings <= 0 else 'Healthy'}")

    st.divider()

    # Budget health bar
    st.subheader("📉 Budget Health")
    if income > 0:
        spend_pct = min(spending / income, 1.0)
        save_pct = max(1 - spend_pct, 0)
        if spend_pct >= 1.0:
            st.error(f"⚠️ You're spending 100%+ of your income! Expenses: ₹{spending:,} | Income: ₹{income:,}")
        elif spend_pct > 0.8:
            st.warning(f"🟠 High spending: {spend_pct*100:.0f}% of income going to expenses.")
        else:
            st.success(f"🟢 Good balance! Spending {spend_pct*100:.0f}% and saving {save_pct*100:.0f}%.")
        st.progress(spend_pct)
        st.caption(f"Expenses ({spend_pct*100:.0f}%) vs Income")

    st.divider()

    # Recommended allocation
    st.subheader("🗂️ Recommended Monthly Allocation")
    tags = data.get("tags", [])

    if savings > 0:
        alloc = {}
        remaining = savings

        if "emergency_fund" in tags:
            ef = round(min(remaining * 0.5, remaining), 2)
            alloc["🛡️ Emergency Fund"] = ef
            remaining -= ef

        if "insurance" in tags and remaining > 0:
            ins = round(min(remaining * 0.2, remaining), 2)
            alloc["🏥 Insurance Premium"] = ins
            remaining -= ins

        if "sip" in tags and remaining > 0:
            alloc["📈 Mutual Fund SIP"] = round(remaining, 2)
            remaining = 0

        if not alloc:
            alloc["💸 General Savings"] = savings

        for label, amt in alloc.items():
            col_l, col_r = st.columns([3, 1])
            col_l.write(label)
            col_r.write(f"**₹{amt:,}**")
    else:
        st.error("⚠️ No savings available for allocation. Focus on reducing expenses first.")

    st.divider()

    # Focus areas
    st.subheader("🏷️ Your Focus Areas")
    tag_labels = {
        "emergency_fund": "🛡️ Build Emergency Fund",
        "sip": "📈 Start SIP / Investing",
        "insurance": "🏥 Get Insurance",
        "debt": "💳 Pay Off Debt",
        "overspending": "✂️ Cut Overspending",
        "savings": "💰 Build Savings",
        "investing": "📊 Start Investing",
    }
    if tags:
        cols = st.columns(min(len(tags), 3))
        for i, tag in enumerate(tags):
            cols[i % 3].success(tag_labels.get(tag, f"✅ {tag}"))
    else:
        st.info("No specific focus tags detected.")

    st.divider()

    # Full plan
    with st.expander("📋 View Full Recommendation", expanded=True):
        # Strip the TAGS line for cleaner display
        clean_reply = data["reply"]
        if "TAGS:" in clean_reply:
            clean_reply = clean_reply[:clean_reply.rfind("TAGS:")].strip().rstrip("-").strip()
        st.markdown(clean_reply)


# Sidebar
with st.sidebar:
    st.header("📊 Enter Details")
    income = st.number_input("Monthly Income (₹)", min_value=0, step=500)
    spending = st.number_input("Monthly Spending (₹)", min_value=0, step=500)

    if st.button("🚀 Start", use_container_width=True):
        if income > 0:
            st.session_state.income = income
            st.session_state.spending = spending
            st.session_state.show_dashboard = False
            st.session_state.final_reply = ""
            msg = f"My monthly income is ₹{income} and I spend ₹{spending} per month. Help me plan my finances."
            st.session_state.messages.append({"role": "user", "content": msg})
            st.session_state.started = True
            st.rerun()
        else:
            st.warning("Enter income first!")

    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.messages = []
        st.session_state.started = False
        st.session_state.income = 0
        st.session_state.spending = 0
        st.session_state.show_dashboard = False
        st.session_state.final_reply = ""
        st.rerun()

# Main area
if not st.session_state.started:
    st.info("👈 Enter income & spending in sidebar, then click Start")

# Show conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Auto-reply when last message is from user
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *st.session_state.messages
                ],
                max_tokens=700,
                temperature=0.7
            )
            reply = response.choices[0].message.content
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # Detect if this is the final recommendation
    if "YOUR PLAN" in reply and "ACTION STEPS" in reply:
        st.session_state.show_dashboard = True
        st.session_state.final_reply = reply
        st.rerun()

# Dashboard after conversation ends
if st.session_state.show_dashboard and st.session_state.final_reply:
    data = extract_dashboard_data(
        st.session_state.final_reply,
        st.session_state.income,
        st.session_state.spending
    )
    show_dashboard(data)

# Chat input
if st.session_state.started and not st.session_state.show_dashboard:
    user_input = st.chat_input("Type your answer...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()
