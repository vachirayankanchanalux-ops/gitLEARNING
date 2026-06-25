from __future__ import annotations
import os
import tempfile
from typing import Optional, Dict, Any

import streamlit as st
from jamaibase import JamAI, types as t

# ==============================
# Configuration
# ==============================
PROJECT_ID = "proj_36b6557d09f312fa59d3cd19"
PAT = "jamai_pat_5a0fb5a76e772a8a51c64294fff4440f1519bfb6cdebdca2"

# ตารางหลักที่ใช้จัดการข้อมูลทั้งหมด
CAREER_TABLE_ID = "Project_resume"

# ตั้งชื่อ ID คอลัมน์ให้ตรงกับที่ตั้งไว้ใน JamAI Base (Case-sensitive)
IN_PROFILE_IMAGE = "profile_image"
IN_MY_PROFILE_DATA = "my_profile_data"
IN_RESUME_TECH = "resume_tech"

OUT_EXTRACT_SKILL = "extract_skill"
OUT_GAP_ANALYZE = "gap_analyze"
OUT_GEN_QUESTION = "gen_question"

st.set_page_config(page_title="💼 AI Career Analyzer & Interview Prep", page_icon="💼", layout="wide")

# ==============================
# Helpers
# ==============================

def get_client() -> JamAI:
    if not PROJECT_ID or not PAT:
        raise RuntimeError("Please set PROJECT_ID and PAT at the top of this file.")
    return JamAI(project_id=PROJECT_ID, token=PAT)


def _upload_file(client: JamAI, uploaded_file) -> Optional[str]:
    """อัปโหลดไฟล์รูปภาพเข้า JamAI เพื่อแปลงเป็น URI สำหรับใช้งานในระบบ"""
    if not uploaded_file:
        return None
    suffix = os.path.splitext(uploaded_file.name)[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    try:
        resp = client.file.upload_file(tmp_path)
        return getattr(resp, "uri", None)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def _safe_text(cell: Any) -> str:
    try:
        return getattr(cell, "text", "") or ""
    except Exception:
        return ""


def run_career_pipeline(
    client: JamAI, 
    image_uri: Optional[str], 
    profile_data: str, 
    resume_tech: str
) -> Dict[str, str]:
    """
    ส่ง Input ทั้งหมดเข้า Action Table และรันกระบวนการดึงข้อมูลทักษะ, 
    วิเคราะห์ช่องว่าง (RAG กับ resumeresujai) และสร้างคำถามสัมภาษณ์
    """
    # เตรียมข้อมูลสำหรับส่งเข้าตาราง
    row_data = {
        IN_MY_PROFILE_DATA: profile_data,
        IN_RESUME_TECH: resume_tech
    }
    if image_uri:
        row_data[IN_PROFILE_IMAGE] = image_uri

    req = t.MultiRowAddRequest(
        table_id=CAREER_TABLE_ID,
        data=[row_data],
        stream=False,  # สามารถตั้งเป็น True ได้ถ้าต้องการดึงข้อมูลแบบ Stream แบบโค้ดเดิม
    )
    
    res = client.table.add_table_rows(t.TableType.ACTION, req)
    row0 = res.rows[0] if getattr(res, "rows", None) else None
    cols = getattr(row0, "columns", {}) if row0 else {}
    
    return {
        "extract_skill": _safe_text(cols.get(OUT_EXTRACT_SKILL)),
        "gap_analyze": _safe_text(cols.get(OUT_GAP_ANALYZE)),
        "gen_question": _safe_text(cols.get(OUT_GEN_QUESTION)),
    }

# ==============================
# UI
# ==============================

st.title("💼 AI Career Analyzer & Interview Prep")
st.caption("วิเคราะห์ประวัติ ค้นหาทักษะที่ขาดด้วยข้อมูลจาก Job Description และจำลองคำถามสัมภาษณ์งาน")

# Sidebar สำหรับปรับเปลี่ยนการตั้งค่า
with st.sidebar:
    st.subheader("⚙️ Settings")
    PROJECT_ID = st.text_input("Project ID", value=PROJECT_ID)
    PAT = st.text_input("PAT", value=PAT, type="password")
    CAREER_TABLE_ID = st.text_input("Action Table ID", value=CAREER_TABLE_ID)

# การจัด Layout หน้าจอรับข้อมูล
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("1) ข้อมูลโปรไฟล์ปัจจุบันของคุณ")
    uploaded_img = st.file_uploader("อัปโหลดรูปภาพโปรไฟล์ (ถ้ามี)", type=["jpg", "jpeg", "png", "webp"])
    if uploaded_img:
        st.image(uploaded_img, caption="ตัวอย่างภาพโปรไฟล์ที่อัปโหลด", width=250)
        
    profile_text = st.text_area(
        "ข้อมูลเกี่ยวกับสายงานเดิม / ประสบการณ์ที่มีทั้งหมด", 
        placeholder="ตัวอย่างเช่น: ทำงานเป็น Junior Frontend Dev มา 1 ปี ถนัด HTML, CSS, React..."
    )

with right_col:
    st.subheader("2) เป้าหมายในอนาคต")
    resume_tech_text = st.text_area(
        "สายงานอาชีพที่ต้องการเข้าในอนาคต (Resume Tech / Target Role)", 
        placeholder="ตัวอย่างเช่น: อยากย้ายสายงานไปเป็น Data Engineer หรือ Senior Full-stack Developer..."
    )

st.markdown("---")
submit_btn = st.button("เริ่มทำการวิเคราะห์โปรไฟล์แบบ End‑to‑end", type="primary")

# ส่วนแสดงผลลัพธ์
if submit_btn:
    if not profile_text or not resume_tech_text:
        st.warning("กรุณากรอกข้อมูลโปรไฟล์ปัจจุบันและสายงานในอนาคตที่ต้องการวิเคราะห์")
        st.stop()
        
    try:
        client = get_client()
    except Exception as e:
        st.error(f"การเชื่อมต่อล้มเหลว: {e}")
        st.stop()

    # ขั้นตอนการประมวลผล
    with st.status("🔮 กำลังประมวลผลข้อมูลโปรไฟล์ของคุณ...", expanded=True) as status:
        
        st.write("1. กำลังอัปโหลดรูปภาพและวิเคราะห์ทักษะปัจจุบัน...")
        img_uri = _upload_file(client, uploaded_img) if uploaded_img else None
        
        st.write("2. ดึงข้อมูลประวัติ ร่วมกับค้นหา Job Description ในคลังความรู้ (resumeresujai)...")
        # รัน Pipeline ทั้งหมดในตารางเดียว
        results = run_career_pipeline(client, img_uri, profile_text, resume_tech_text)
        
        status.update(label="วิเคราะห์ข้อมูลเสร็จสิ้น!", state="complete", expanded=False)

    # แสดงผลลัพธ์แบ่งตามหัวข้อที่คุณต้องการ
    st.success("✨ ประมวลผลเสร็จสมบูรณ์! ผลลัพธ์ของคุณอยู่ด้านล่างนี้:")
    
    tab1, tab2, tab3 = st.tabs(["📊 ทักษะความสามารถ (Extract Skill)", "🔍 สิ่งที่ต้องปรับปรุง (Gap Analysis)", "❓ คำถามฝึกสัมภาษณ์ (Generated Questions)"])
    
    with tab1:
        st.subheader("ผลการวิเคราะห์ทักษะปัจจุบัน")
        st.markdown(results.get("extract_skill") or "*ไม่มีข้อมูลออกมาจากโมเดล กรุณาตรวจสอบ Prompt ในระบบ JamAI*")
        
    with tab2:
        st.subheader("ตารางเปรียบเทียบข้อแตกต่างและสิ่งที่คุณต้องศึกษาเพิ่ม")
        st.info("💡 ข้อมูลนี้มีการเปรียบเทียบร่วมกับ Job Description จากคลังความรู้ 'resumeresujai' เรียบร้อยแล้ว")
        st.markdown(results.get("gap_analyze") or "*ไม่มีข้อมูลออกมาจากโมเดล*")
        
    with tab3:
        st.subheader("คำถามทดสอบสำหรับเตรียมตัวสัมภาษณ์งาน")
        st.markdown(results.get("gen_question") or "*ไม่มีข้อมูลออกมาจากโมเดล*")

    # ปุ่มสำหรับดาวน์โหลดรายงานรวมกลับไปอ่าน
    report_data = f"""# รายงานสรุปเส้นทางอาชีพและเตรียมความพร้อมสัมภาษณ์งาน
## 1. ทักษะปัจจุบันของคุณ (Extract Skill):
{results.get('extract_skill')}

## 2. การวิเคราะห์จุดที่ต้องพัฒนา (Gap Analysis):
{results.get('gap_analyze')}

## 3. คำถามจำลองเพื่อเตรียมสัมภาษณ์ (Generated Questions):
{results.get('gen_question')}
"""
    st.download_button(
        label="📥 ดาวน์โหลดรายงานฉบับเต็ม (.txt)",
        data=report_data,
        file_name="career_report.txt",
        mime="text/plain"
    )