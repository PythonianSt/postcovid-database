import streamlit as st
import pandas as pd
import os
import requests
import base64
from openai import OpenAI
from datetime import datetime

# ======================
# LOAD SECRETS
# ======================
api_key = st.secrets["OPENAI_API_KEY"]
github_token = st.secrets["GITHUB_TOKEN"]
github_repo = st.secrets["GITHUB_REPO"]

client = OpenAI(api_key=api_key)

# ======================
# PAGE CONFIG
# ======================
st.set_page_config(
    page_title="แบบประเมิน Post-COVID มหาวิทยาลัย 2569",
    layout="wide"
)

st.title("🏥 แบบคัดกรองสุขภาพหลังโควิด (Post-COVID Screening 2569)")
st.title("สำหรับบุคลากรมหาวิทยาลัยเกษตรศาสตร์ วิทยาเขตกำแพงแสน")
st.markdown("จัดทำโดยสถานพยาบาล KU KPS")

# ======================
# FORM
# ======================
with st.form("postcovid_form"):

    st.subheader("ข้อมูลพื้นฐาน")

    emp_id = st.text_input("เลขบัตรประชาชน (13 หลัก)")

    willing = st.radio(
        "ท่านยินดีเข้าร่วมโครงการติดตามสุขภาพหลังโควิดหรือไม่",
        ["Y", "N", "Not sure"]
    )

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

    work_decline = st.slider("ประสิทธิภาพการทำงานลดลง (%)",0,100,0)

    submitted = st.form_submit_button("ประเมินความเสี่ยง")

# ======================
# RISK CALCULATION
# ======================
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

    score += sum(symptoms)*2
    score += work_decline/20

    if score < 5:
        return "LOW","green"
    elif score < 12:
        return "MODERATE","orange"
    else:
        return "HIGH","red"

# ======================
# GPT RECOMMENDATION
# ======================
def gpt_recommendation(risk):

    prompt = f"""
    คุณคือแพทย์อาชีวเวชศาสตร์มหาวิทยาลัย
    ระดับความเสี่ยง Post-COVID คือ {risk}
    กรุณาแนะนำโปรแกรมสุขภาพที่เหมาะสมแบบสั้น กระชับ ภาษาไทย
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content


# ======================
# GITHUB PUSH FUNCTION
# ======================
def github_push(filename):

    url = f"https://api.github.com/repos/{github_repo}/contents/{filename}"

    with open(filename,"rb") as f:
        content = base64.b64encode(f.read()).decode()

    headers={
        "Authorization":f"token {github_token}",
        "Accept":"application/vnd.github+json"
    }

    # get existing file sha
    r = requests.get(url,headers=headers)

    sha=None
    if r.status_code==200:
        sha=r.json()["sha"]

    data={
        "message":"Update Post COVID data",
        "content":content,
        "branch":"main"
    }

    if sha:
        data["sha"]=sha

    response=requests.put(url,headers=headers,json=data)

    # debug output
    st.write("GitHub response:",response.status_code)


# ======================
# SAVE CSV + PUSH
# ======================
def save_csv(data):

    filename="Post_COVID2026.csv"

    df=pd.DataFrame([data])

    if os.path.exists(filename):
        df.to_csv(filename,mode="a",header=False,index=False)
    else:
        df.to_csv(filename,index=False)

    github_push(filename)


# ======================
# RESULT SECTION
# ======================
if submitted:

    if len(emp_id)!=13:
        st.error("เลขบัตรประชาชนต้อง 13 หลัก")
        st.stop()

    if willing=="Y" and email=="":
        st.error("กรุณากรอก Email")
        st.stop()

    risk,color=calculate_risk()

    st.subheader("📊 ผลการประเมิน")

    st.markdown(
        f"<h2 style='color:{color};'>ระดับความเสี่ยง : {risk}</h2>",
        unsafe_allow_html=True
    )

    with st.spinner("AI กำลังวิเคราะห์โปรแกรมที่เหมาะสม..."):
        recommendation=gpt_recommendation(risk)

    st.success("โปรแกรมแนะนำ")
    st.write(recommendation)

    data={
        "timestamp":datetime.now(),
        "ID":emp_id,
        "email":email,
        "willing_program":willing,
        "risk_level":risk,
        "programs_recommended":recommendation
    }

    save_csv(data)

    st.success("✅ บันทึกข้อมูลเรียบร้อย")

    save_csv(data)

    st.success("✅ บันทึกข้อมูลเรียบร้อย")
