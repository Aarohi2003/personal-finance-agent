import streamlit as st
from groq import Groq

# Get API key from Streamlit secrets
api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)

SYSTEM_PROMPT = """
You are a friendly Personal Finance Decision Agent for 18-22 year olds.

Your job:
1. Ask clarifying questions ONE AT A TIME:
   - Do they have an emergency fund?
   - What is their risk tolerance? (low/medium/high)
   - Do they have insurance?
   - What is their main financial goal?

2. Then give final recommendation from:
   - Emergency Fund
   - Mutual Funds (SIP)
   - Insurance

Rules:
- Be short and friendly
- Ask ONE question at a time
- End with 🎯 YOUR PLAN, 💡 WHY THIS WORKS, 📋 ACTION STEPS
"""

st.set_page_config(page_title="Finance Agent", page_icon="💰")
st.title("💰 Personal Finance Agent")
st.caption("Smart financial guide for 18-22 year olds")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.started = False

with st.sidebar:
    st.header("📊 Enter Details")
    income = st.number_input("Monthly Income (₹)", min_value=0, step=500)
    spending = st.number_input("Monthly Spending (₹)", min_value=0, step=500)

    if st.button("🚀 Start", use_container_width=True):
        if income > 0:
            msg = f"My monthly income is ₹{income} and I spend ₹{spending}. Help me."
            st.session_state.messages.append({"role": "user", "content": msg})
            st.session_state.started = True
            st.rerun()
        else:
            st.warning("Enter income first!")

    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.messages = []
        st.session_state.started = False
        st.rerun()

if not st.session_state.started:
    st.info("👈 Enter income & spending in sidebar, then click Start")

for msg in st.session_state.messages:
    with
