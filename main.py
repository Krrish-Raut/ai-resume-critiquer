import streamlit as st
import PyPDF2
import io
import os
import time
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try importing Gemini
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Load API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if genai and GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# -------------------- PAGE SETUP --------------------
st.set_page_config(
    page_title="AI Resume Critiquer",
    page_icon="📃",
    layout="centered"
)

st.title("AI Resume Critiquer 📃")
st.markdown("Upload your resume and get ATS scoring + AI-powered professional feedback")

# -------------------- UI INPUTS --------------------
uploaded_file = st.file_uploader("Upload your resume (PDF or TXT)", type=["pdf", "txt"])
job_role = st.text_input("Enter the job role you're targeting (Optional)")

st.subheader("⚙️ Settings")

ai_provider = st.selectbox(
    "Choose Mode",
    ["Demo Mode", "Google Gemini (AI)"]
)

st.caption("Use Demo Mode if you don't have an API key")

analyze = st.button("Analyze Resume")

# -------------------- SESSION STATE --------------------
if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0

if "last_file_hash" not in st.session_state:
    st.session_state.last_file_hash = None

if "cached_response" not in st.session_state:
    st.session_state.cached_response = None

# -------------------- FUNCTIONS --------------------
def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def extract_text_from_file(file):
    if not file:
        return ""

    filename = file.name.lower()

    if filename.endswith(".pdf"):
        return extract_text_from_pdf(io.BytesIO(file.read()))
    else:
        return file.read().decode("utf-8")

def file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

def ats_score(text, job_role):
    if not job_role:
        return 0

    keywords = job_role.lower().split()
    text = text.lower()
    hits = sum(1 for k in keywords if k in text)
    return min(100, int((hits / max(1, len(keywords))) * 100))

# -------------------- MAIN LOGIC --------------------
if analyze:
    if not uploaded_file:
        st.warning("Please upload a resume file first.")
        st.stop()

    current_time = time.time()

    if current_time - st.session_state.last_request_time < 10:
        st.warning("⏳ Please wait a few seconds before analyzing again.")
        st.stop()

    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    current_hash = file_hash(file_bytes)

    if st.session_state.last_file_hash == current_hash:
        st.markdown("## 🧠 Resume Analysis (Cached)")
        st.markdown(st.session_state.cached_response)
        st.stop()

    st.session_state.last_request_time = current_time

    with st.spinner("Analyzing your resume..."):
        try:
            file_content = extract_text_from_file(uploaded_file)

            if not file_content.strip():
                st.error("The uploaded file is empty.")
                st.stop()

            # ---------------- WORD COUNT ----------------
            word_count = len(file_content.split())
            st.caption(f"📄 Resume length: {word_count} words")

            # ---------------- ATS SCORE ----------------
            score = ats_score(file_content, job_role)
            st.markdown("### 📊 ATS Compatibility Score")
            st.progress(score)
            st.caption(f"Your resume matches {score}% of the job role keywords")

            if score < 40:
                st.warning("Low ATS match — add more role-specific keywords")
            elif score < 70:
                st.info("Moderate ATS match — small improvements recommended")
            else:
                st.success("Strong ATS match — well optimized!")

            # ---------------- PROMPT ----------------
            prompt = f"""
You are a professional career coach and resume expert.

Analyze this resume and provide structured, actionable feedback.

Focus on:
1. Content clarity and impact
2. Skills relevance
3. Experience quality
4. Formatting & ATS optimization
5. Suggestions for this role: {job_role if job_role else "General job applications"}

Resume:
{file_content}

Respond in clear bullet points with section headings.
"""

            # ---------------- AI LOGIC ----------------
            if ai_provider == "Demo Mode":
                output_text = """
## Resume Feedback (Demo Mode)

• Add a strong professional summary at the top
• Use measurable achievements instead of responsibilities
• Improve keyword alignment with your job role
• Group technical skills into categories
• Keep bullet points under 2 lines for readability
"""

            elif ai_provider == "Google Gemini (AI)":
                if not genai or not GOOGLE_API_KEY:
                    st.error("Google Gemini not available. Install google-generativeai and set GOOGLE_API_KEY")
                    st.stop()

                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                output_text = response.text

            # ---------------- CACHE + DISPLAY ----------------
            st.session_state.last_file_hash = current_hash
            st.session_state.cached_response = output_text

            st.success("🧠 Resume Analysis Complete")
            st.markdown("## Professional Resume Feedback")
            st.markdown(output_text)

        except Exception as e:
            st.error(f"Error: {e}")
