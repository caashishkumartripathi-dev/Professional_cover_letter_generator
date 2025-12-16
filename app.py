import streamlit as st
import pdfplumber
import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from openai import OpenAI

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Professional Cover Letter Generator", layout="centered")
client = OpenAI()

# ---------------- KEYWORD CONFIG (EDITABLE) ----------------

KEYWORDS = {
    "core_finance": [
        "financial reporting",
        "month-end closure",
        "reconciliations",
        "accounting controls",
        "financial governance",
        "data accuracy",
        "compliance"
    ],
    "operations": [
        "Procure-to-Pay",
        "Record-to-Report",
        "transaction flows",
        "process efficiency",
        "systems exposure"
    ],
    "analysis": [
        "MIS",
        "variance analysis",
        "financial analysis",
        "decision support"
    ],
}

# ---------------- HELPERS ----------------

def extract_text(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def apply_programmatic_bolding(text, company_name):
    paragraphs = text.split("\n\n")
    used_company = False
    result = []

    for para in paragraphs:
        bolded = para

        # Bold company name once
        if not used_company and company_name.lower() in bolded.lower():
            bolded = re.sub(
                re.escape(company_name),
                f"<b>{company_name}</b>",
                bolded,
                flags=re.IGNORECASE
            )
            used_company = True

        # Collect candidate keywords
        candidates = []
        for group in KEYWORDS.values():
            for kw in group:
                if kw.lower() in bolded.lower():
                    candidates.append(kw)

        # Limit to 2–3 keywords
        for kw in candidates[:3]:
            bolded = re.sub(
                re.escape(kw),
                f"<b>{kw}</b>",
                bolded,
                flags=re.IGNORECASE
            )

        result.append(bolded)

    return "\n\n".join(result)


def generate_cover_letter(resume_text, jd_text, data, tone):
    prompt = f"""
You are a senior hiring manager and expert cover-letter writer.

CRITICAL TRUTH RULE (NON-NEGOTIABLE):
- Do NOT invent experience.
- Do NOT claim leadership or implementation unless clearly supported by resume.
- If JD skills are not directly present in resume:
  - Use derived learning from audit, reconciliations, controls, systems exposure
  - Or frame as readiness / strong foundation
- Selling is required, exaggeration is forbidden.

STRUCTURE & LENGTH:
- STRICT one A4 page
- EXACTLY 5 paragraphs
- Each paragraph ~5 lines
- No fluff, no generic phrases

PARAGRAPH ROLES:
1. Why this role at this company (contextual, specific)
2. Core CA foundation and accounting credibility (resume-backed)
3. Operational / role alignment using direct or derived experience
4. Governance, controls, cross-functional maturity
5. Forward-looking close with ownership tone

TONE:
Company type is: {tone}
Adapt language accordingly (do not mention tone explicitly).

CANDIDATE:
Name: {data['name']}
Company: {data['company']}
Role: {data['role']}

RESUME (ONLY SOURCE OF FACTUAL EXPERIENCE):
{resume_text}

JOB DESCRIPTION:
{jd_text if jd_text else "Not provided"}

OUTPUT:
Only the 5 body paragraphs.
No date. No salutation. No signature.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.25,
    )

    return response.choices[0].message.content.strip()


def create_pdf(text, data):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=56,
        leftMargin=56,
        topMargin=56,
        bottomMargin=56
    )

    styles = getSampleStyleSheet()

    body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=11.4,
        leading=14.8,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )

    header = ParagraphStyle(
        "Header",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=11.4,
        leading=14.8
    )

    elements = []

    today = datetime.today().strftime("%d %B %Y")

    elements.append(
        Paragraph(
            f"<b>{data['name'].upper()}</b><br/>"
            f"Date: {today}<br/><br/>"
            f"Dear Hiring Manager,<br/><br/>",
            header
        )
    )

    for para in text.split("\n\n"):
        elements.append(Paragraph(para, body))

    closing = f"""
Sincerely,<br/><br/>
{data['name']}<br/>
{data['mobile']}<br/>
{data['email']}<br/>
{data['linkedin']}
"""
    elements.append(Paragraph(closing, header))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ---------------- UI ----------------

st.title("📄 Professional Cover Letter Generator")
st.caption("Designed by Ashish Tripathi")

resume = st.file_uploader("Upload Resume (PDF)", type="pdf")
jd = st.file_uploader("Upload Job Description (Optional)", type="pdf")

with st.form("details_form"):
    name = st.text_input("Full Name")
    company = st.text_input("Company Name")
    role = st.text_input("Role / Position")

    tone = st.selectbox(
        "Company Tone",
        ["Startup / Growth", "Corporate / Listed", "Professional Firm"]
    )

    email = st.text_input("Email")
    mobile = st.text_input("Mobile")
    linkedin = st.text_input("LinkedIn URL")

    submit = st.form_submit_button("Generate Draft")

if submit:
    if not resume or not name or not company or not role:
        st.error("Resume, Name, Company, and Role are mandatory.")
        st.stop()

    with st.spinner("Generating high-quality draft..."):
        resume_text = extract_text(resume)
        jd_text = extract_text(jd) if jd else ""

        data = {
            "name": name,
            "company": company,
            "role": role,
            "email": email,
            "mobile": mobile,
            "linkedin": linkedin,
        }

        draft = generate_cover_letter(resume_text, jd_text, data, tone)
        draft = apply_programmatic_bolding(draft, company)

        st.session_state["draft"] = draft
        st.session_state["data"] = data

if "draft" in st.session_state:
    st.subheader("✏️ Review & Edit (Content Only)")

    edited_text = st.text_area(
        "You may edit wording below. Formatting rules are enforced automatically.",
        st.session_state["draft"],
        height=420
    )

    if st.button("⬇️ Download Final PDF"):
        final_text = apply_programmatic_bolding(edited_text, st.session_state["data"]["company"])
        pdf = create_pdf(final_text, st.session_state["data"])

        st.download_button(
            "Download PDF",
            data=pdf,
            file_name=f"{st.session_state['data']['name'].replace(' ', '_')}_Cover_Letter.pdf",
            mime="application/pdf",
        )

st.markdown("---")
st.caption("Built by Ashish Tripathi · Chartered Accountant")
