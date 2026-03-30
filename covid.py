import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

# ----------------------
# Load ENV + GPT
# ----------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------
# Page Config
# ----------------------
st.set_page_config(
    page_title="แบบประเมิน Post-COVID มหาวิทยาลัย 2569",
    layout="wide"
)

st.title("🏥 แบบคัดกรองสุขภาพหลังโควิด (Post-COVID Screening 2569)")
st.title("สำหรับบุคลากรมหาวิทยาลัยเกษตรศาสตร์ วิทยาเขตกำแพงแสน")
st.markdown("จัดทำโดยสถานพยาบาล KU KPS")
# ----------------------
# FORM
# ----------------------
with st.form("postcovid_form"):

    st.subheader("ข้อมูลพื้นฐาน")

    emp_id = st.text_input("เลขบัตรประชาชน (13 หลัก)")

    willing = st.radio(
        "ท่านยินดีเข้าร่วมโครงการติดตามสุขภาพหลังโควิดหรือไม่",
        ["Y", "N", "Not sure"]
    )

    # ⭐ Show email ONLY when Y selected
    email = ""

    if willing == "Y":
        email = st.text_input("Email สำหรับการนัดหมาย")

    st.subheader("ประวัติการติดเชื้อ COVID")

    infected = st.radio("เคยติด COVID หรือไม่", ["ไม่เคย", "เคย"])

    times = st.number_input("จำนวนครั้งที่ติด", 0, 10, 0)

    hospitalized = st.radio(
        "เคยนอนโรงพยาบาลหรือใช้ออกซิเจน",
        ["ไม่เคย", "เคย"]
    )

    st.subheader("อาการต่อเนื่อง (>12 สัปดาห์)")

    fatigue = st.checkbox("เหนื่อยล้าเรื้อรัง")
    dyspnea = st.checkbox("หอบ เหนื่อยง่าย")
    brainfog = st.checkbox("สมองล้า ความจำลด")
    chestpain = st.checkbox("เจ็บหน้าอก ใจสั่น")
    insomnia = st.checkbox("นอนไม่หลับ")
    anxiety = st.checkbox("เครียด วิตกกังวล")

    st.subheader("ความสามารถในการทำงาน")

    work_decline = st.slider(
        "ประสิทธิภาพการทำงานลดลง (%)",
        0,100,0
    )

    submitted = st.form_submit_button("ประเมินความเสี่ยง")

# ----------------------
# Risk Calculation
# ----------------------
def calculate_risk():
    score = 0

    if infected == "เคย":
        score += 2

    score += times

    if hospitalized == "เคย":
        score += 4

    symptoms = [
        fatigue, dyspnea, brainfog,
        chestpain, insomnia, anxiety
    ]

    score += sum(symptoms) * 2
    score += work_decline/20

    if score < 5:
        return "LOW", "green"
    elif score < 12:
        return "MODERATE", "orange"
    else:
        return "HIGH", "red"

# ----------------------
# GPT Recommendation
# ----------------------
def gpt_recommendation(risk):

    prompt = f"""
    คุณคือแพทย์อาชีวเวชศาสตร์มหาวิทยาลัย
    ระดับความเสี่ยง Post-COVID ของบุคลากรคือ {risk}

    กรุณาแนะนำโปรแกรมสุขภาพที่เหมาะสม
    เขียนภาษาไทย กระชับ
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content

# ----------------------
# SAVE CSV
# ----------------------
def save_csv(data):

    file = "Post_COVID2026.csv"

    df = pd.DataFrame([data])

    if os.path.exists(file):
        df.to_csv(file, mode="a", header=False, index=False)
    else:
        df.to_csv(file, index=False)

# ----------------------
# RESULT
# ----------------------
if submitted:

    if len(emp_id) != 13:
        st.error("เลขบัตรประชาชนต้อง 13 หลัก")
        st.stop()

    # ⭐ Require email only when consent = Y
    if willing == "Y" and email == "":
        st.error("กรุณากรอก Email สำหรับการติดต่อ")
        st.stop()
    risk, color = calculate_risk()

    st.subheader("📊 ผลการประเมิน")

    st.markdown(
        f"""
        <h2 style='color:{color};'>
        ระดับความเสี่ยง : {risk}
        </h2>
        """,
        unsafe_allow_html=True
    )

    with st.spinner("AI กำลังวิเคราะห์โปรแกรมที่เหมาะสม..."):
        recommendation = gpt_recommendation(risk)

    st.success("โปรแกรมแนะนำ")
    st.write(recommendation)

    data = {
        "timestamp": datetime.now(),
        "ID": emp_id,
        "email": email,
        "willing_program": willing,
        "risk_level": risk,
        "programs_recommended": recommendation
    }

    save_csv(data)

    st.success("✅ บันทึกข้อมูลเรียบร้อย")