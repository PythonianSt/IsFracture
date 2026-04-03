import streamlit as st
import base64
from openai import OpenAI
from PIL import Image
import io

# -----------------------
# GPT Setup
# -----------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Ottawa Assistant", layout="centered")

# -----------------------
# Session State
# -----------------------
if "step" not in st.session_state:
    st.session_state.step = 1

if "photos" not in st.session_state:
    st.session_state.photos = {}

# -----------------------
# Image Encode (Mobile Safe)
# -----------------------
def encode(img):

    image = Image.open(img)
    image.thumbnail((1024,1024))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)

    return base64.b64encode(buffer.getvalue()).decode()

# -----------------------
# Joint Detection
# -----------------------
def detect_joint():

    f = encode(st.session_state.photos["front"])
    s = encode(st.session_state.photos["side"])
    o = encode(st.session_state.photos["oblique"])

    prompt = """
ภาพเป็นข้ออะไร ตอบเพียงคำเดียว:
มือ / เท้า / เข่า / ข้อศอก
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role":"user",
            "content":[
                {"type":"text","text":prompt},
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{f}" }},
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{s}" }},
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{o}" }}
            ]
        }],
        temperature=0
    )

    return response.choices[0].message.content.strip()

# -----------------------
# Fracture Analysis
# -----------------------
def analyze_fracture():

    f = encode(st.session_state.photos["front"])
    s = encode(st.session_state.photos["side"])
    o = encode(st.session_state.photos["oblique"])

    prompt = """
ประเมินระดับความสงสัยว่ากระดูกบาดเจ็บหรือหัก (%)
ตอบเฉพาะตัวเลข เช่น 45
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role":"user",
            "content":[
                {"type":"text","text":prompt},
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{f}" }},
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{s}" }},
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{o}" }}
            ]
        }],
        temperature=0
    )

    return int(response.choices[0].message.content.strip())

# -----------------------
# Reanalysis
# -----------------------
def reanalyze(joint, score, answers):

    prompt = f"""
ข้อ: {joint}
AI suspicion เดิม {score}%

คำตอบ clinical rule:
{answers}

ปรับระดับความสงสัยใหม่ (%)
ตอบตัวเลขเท่านั้น
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0
    )

    return int(response.choices[0].message.content.strip())

# =====================================================
# UI
# =====================================================

st.title("🩺 AI Fracture Assistant")

# ---------------- STEP 1 ----------------
if st.session_state.step == 1:

    st.subheader("📸 ถ่ายภาพด้านหน้า")
    img = st.camera_input("Front view")

    if img:
        st.session_state.photos["front"] = img
        st.session_state.step = 2
        st.rerun()

# ---------------- STEP 2 ----------------
elif st.session_state.step == 2:

    st.subheader("📸 ถ่ายภาพด้านข้าง")
    img = st.camera_input("Side view")

    if img:
        st.session_state.photos["side"] = img
        st.session_state.step = 3
        st.rerun()

# ---------------- STEP 3 ----------------
elif st.session_state.step == 3:

    st.subheader("📸 ถ่ายภาพเฉียง")
    img = st.camera_input("Oblique view")

    if img:
        st.session_state.photos["oblique"] = img

        with st.spinner("AI ตรวจสอบชนิดข้อ..."):
            st.session_state.joint = detect_joint()

        st.session_state.step = 4
        st.rerun()

# ---------------- STEP 4 ----------------
elif st.session_state.step == 4:

    st.success(f"เป็นภาพถ่ายของข้อ: **{st.session_state.joint}**")

    agree = st.radio("ถูกต้องหรือไม่?", ["Y","N"])

    if agree == "N":
        st.warning("โปรดถ่ายภาพข้อตามความเป็นจริง")

        st.session_state.photos = {}
        st.session_state.step = 1
        st.session_state.pop("suspicion", None)
        st.rerun()

    if agree == "Y":

        if "suspicion" not in st.session_state:
            with st.spinner("AI วิเคราะห์ความเสี่ยงกระดูกหัก..."):
                st.session_state.suspicion = analyze_fracture()

        st.metric(
            "ระดับความสงสัยว่ากระดูกบาดเจ็บหรือหัก",
            f"{st.session_state.suspicion}%"
        )

        jt = st.session_state.joint

        if "เท้า" in jt:
            joint_type = "ankle"
        elif "เข่า" in jt:
            joint_type = "knee"
        elif "ข้อศอก" in jt:
            joint_type = "elbow"
        else:
            joint_type = "wrist"

# ---------------- Questionnaire ----------------
        if st.session_state.suspicion < 60:

            st.subheader("🔎 Clinical Questions")

            if joint_type == "ankle":
                q1 = st.radio("ลงน้ำหนักไม่ได้ 4 ก้าว?", ["ไม่ใช่","ใช่"])
                q2 = st.radio("กดเจ็บตาตุ่มหรือ midfoot?", ["ไม่ใช่","ใช่"])

            elif joint_type == "knee":
                q1 = st.radio("อายุ ≥55 ปี?", ["ไม่ใช่","ใช่"])
                q2 = st.radio("งอเข่าไม่ได้ 90°?", ["ไม่ใช่","ใช่"])

            elif joint_type == "elbow":
                q1 = st.radio("เหยียดข้อศอกสุดไม่ได้?", ["ไม่ใช่","ใช่"])
                q2 = st.radio("กดเจ็บบริเวณ radial head/olecranon?", ["ไม่ใช่","ใช่"])

            else:
                q1 = st.radio("กดเจ็บ distal radius หรือ scaphoid?", ["ไม่ใช่","ใช่"])
                q2 = st.radio("บวม/ผิดรูป?", ["ไม่ใช่","ใช่"])

            if st.button("🧠 วิเคราะห์ใหม่"):

                answers = f"""
Q1: {q1}
Q2: {q2}
"""

                new_score = reanalyze(
                    joint_type,
                    st.session_state.suspicion,
                    answers
                )

                st.session_state.suspicion = new_score

                st.success(
                    f"ระดับความสงสัยใหม่: {new_score}%"
                )

# ---------------- Final Advice ----------------
        if st.session_state.suspicion >= 60:
            st.error("🔴 แนะนำถ่าย X-ray ทันที")

        elif st.session_state.suspicion >= 30:
            st.warning("🟡 พิจารณาพบแพทย์หากอาการไม่ดีขึ้น")

        else:
            st.success("🟢 ความเสี่ยงต่ำ เฝ้าดูอาการได้")

# ---------------- References ----------------
st.markdown("""
---
**References**

- Ottawa Ankle Rules — Stiell IG, Ann Emerg Med  
- Ottawa Knee Rule — JAMA  
- Elbow Extension Test — Appelboam A, BMJ  
""")
