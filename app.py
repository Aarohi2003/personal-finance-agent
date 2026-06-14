import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
                max_tokens=500,
                temperature=0.7
            )
            reply = response.choices[0].message.content
            st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

if st.session_state.started:
    user_input = st.chat_input("Type your answer...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()
