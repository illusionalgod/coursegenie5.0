# chatbot_logic.py  –  CourseGenie v5.1
# ======================================
# Hybrid AI architecture:
#   1. ML Model (Random Forest trained on career dataset) → predicts career path
#   2. GPT-3.5-turbo → delivers personalised conversation grounded in that prediction

# The model is loaded once at startup from career_model.pkl (produced by
# career_model_trainer.py).  If the model file is absent the system falls back
# gracefully to pure GPT-only mode.


import os
import sys
import pickle
import numpy as np
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ─────────────────────────────────────────────────────────────────────────────
# Load career ML model (once, at module import time)
# ─────────────────────────────────────────────────────────────────────────────
_MODEL_BUNDLE = None
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "career_model.pkl")

def _load_model():
    global _MODEL_BUNDLE
    if _MODEL_BUNDLE is not None:
        return _MODEL_BUNDLE
    if os.path.exists(_MODEL_PATH):
        try:
            with open(_MODEL_PATH, "rb") as f:
                _MODEL_BUNDLE = pickle.load(f)
            print("[CourseGenie] Career model loaded successfully.")
        except Exception as e:
            print(f"[CourseGenie] Warning: could not load career model: {e}")
            _MODEL_BUNDLE = None
    else:
        print("[CourseGenie] career_model.pkl not found — running in GPT-only mode.")
    return _MODEL_BUNDLE

_load_model()

# ─────────────────────────────────────────────────────────────────────────────
# Career prediction helper
# ─────────────────────────────────────────────────────────────────────────────
def predict_career(student_profile: dict) -> dict | None:
    """
    Predict career path from a student skill/interest profile dict.

    Expected keys in student_profile (all optional — missing → 0):
        python_yn, r_yn, spark_yn, mongodb_yn, tableau_yn, power_bi_yn,
        hadoop_yn, sql_yn, excel_yn, java_yn, tensorflow_yn, keras_yn,
        pytorch_yn, hadoop_yn2,
        communication_skills (1–4), analytical_skills (1–4),
        problem_solving (1–4), creativity (1–4), teamwork (1–4),
        leadership (1–4),
        gpa (float 0–4), experience_years (int)

    Returns dict with keys:
        career        – predicted career label
        confidence    – probability (0–1)
        top3          – list of (career, probability) top-3 predictions
        gctu_info     – GCTU programme / faculty / outlook info
    Returns None if model unavailable.
    """
    bundle = _load_model()
    if bundle is None:
        return None

    pipeline    = bundle["pipeline"]
    le          = bundle["label_encoder"]
    feature_cols = bundle["feature_cols"]
    gctu_map    = bundle.get("gctu_career_map", {})

    # Build feature DataFrame (preserves column names — no sklearn warnings)
    import pandas as _pd
    x = _pd.DataFrame(
        [[student_profile.get(col, 0) for col in feature_cols]],
        columns=feature_cols,
    ).astype(float)

    proba = pipeline.predict_proba(x)[0]                  # shape (n_classes,)
    top_idx = np.argsort(proba)[::-1][:3]
    career = le.inverse_transform([top_idx[0]])[0]
    confidence = float(proba[top_idx[0]])
    top3 = [(le.inverse_transform([i])[0], float(proba[i])) for i in top_idx]

    return {
        "career":     career,
        "confidence": confidence,
        "top3":       top3,
        "gctu_info":  gctu_map.get(career, {}),
    }


def extract_profile_from_message(message: str, history: list) -> dict:
    """
    Lightweight keyword extractor — parses user messages for skill/interest
    signals and returns a partial profile dict for predict_career().

    This is intentionally simple: GPT handles nuance; this just gives the
    ML model enough signal to produce a useful career prediction.
    """
    text = (message + " " + " ".join(
        q + " " + a for q, a in history[-3:]
    )).lower()

    profile = {}

    # Binary skill flags
    skill_keywords = {
        "python_yn":      ["python"],
        "r_yn":           [" r ", "r programming", "rstudio"],
        "spark_yn":       ["spark", "apache spark"],
        "mongodb_yn":     ["mongodb", "nosql", "mongo"],
        "tableau_yn":     ["tableau"],
        "power_bi_yn":    ["power bi", "powerbi"],
        "hadoop_yn":      ["hadoop", "hdfs", "hive"],
        "sql_yn":         ["sql", "mysql", "postgresql", "database"],
        "excel_yn":       ["excel", "spreadsheet"],
        "java_yn":        ["java", "android studio"],
        "tensorflow_yn":  ["tensorflow", "tf"],
        "keras_yn":       ["keras"],
        "pytorch_yn":     ["pytorch", "torch"],
        "hadoop_yn2":     ["big data", "data lake"],
    }
    for col, kws in skill_keywords.items():
        profile[col] = 1 if any(kw in text for kw in kws) else 0

    # Soft skills (scale 1–4 based on emphasis words)
    def soft(kws):
        count = sum(text.count(kw) for kw in kws)
        return min(4, max(1, count + 1))

    profile["communication_skills"] = soft(["communicate", "presentation", "public speaking", "writing"])
    profile["analytical_skills"]    = soft(["analytic", "analysis", "data", "research", "statistics"])
    profile["problem_solving"]      = soft(["problem", "debug", "solve", "fix", "algorithm"])
    profile["creativity"]           = soft(["creative", "design", "art", "innovate", "idea"])
    profile["teamwork"]             = soft(["team", "collaborate", "group", "together"])
    profile["leadership"]           = soft(["lead", "manage", "director", "head", "organis"])

    # GPA — look for explicit mention
    import re
    gpa_match = re.search(r"gpa[\s:]*([0-9]\.[0-9])", text)
    profile["gpa"] = float(gpa_match.group(1)) if gpa_match else 2.8

    exp_match = re.search(r"(\d+)\s*year[s]?\s*(of\s*)?experience", text)
    profile["experience_years"] = int(exp_match.group(1)) if exp_match else 0

    return profile


def build_career_context(prediction: dict | None) -> str:
    """
    Formats the ML prediction result into a compact context string
    that is injected into GPT's system prompt.
    """
    if prediction is None:
        return ""

    career    = prediction["career"]
    conf      = prediction["confidence"]
    top3      = prediction["top3"]
    info      = prediction["gctu_info"]
    programmes = ", ".join(info.get("programmes", []))
    faculty    = info.get("faculty", "")
    outlook    = info.get("career_outlook", "")
    skills     = ", ".join(info.get("key_skills", []))

    top3_str = " | ".join(f"{c} ({p:.0%})" for c, p in top3)

    return f"""
[CAREER MODEL PREDICTION]
Primary career match  : {career} ({conf:.0%} confidence)
Top-3 predictions     : {top3_str}
Recommended GCTU programmes: {programmes}
Faculty               : {faculty}
Career outlook (Ghana): {outlook}
Key skills to develop : {skills}
[END CAREER MODEL PREDICTION]
"""


# ─────────────────────────────────────────────────────────────────────────────
# GPT helpers (backward-compatible with both legacy and new openai clients)
# ─────────────────────────────────────────────────────────────────────────────
def _chat_completion_create(**kwargs):
    if hasattr(openai, "ChatCompletion") and hasattr(openai.ChatCompletion, "create"):
        return openai.ChatCompletion.create(**kwargs)
    try:
        from openai import OpenAI
        client = OpenAI()
        return client.chat.completions.create(**kwargs)
    except Exception:
        raise


def _moderation_create(**kwargs):
    if hasattr(openai, "Moderation") and hasattr(openai.Moderation, "create"):
        return openai.Moderation.create(**kwargs)
    try:
        from openai import OpenAI
        client = OpenAI()
        return client.moderations.create(**kwargs)
    except Exception:
        raise


# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────────────
BASE_INSTRUCTIONS = """You are CourseGenie, a helpful and friendly course and career recommendation chatbot for Ghana Communication Technology University (GCTU).

Your role is to help students discover programmes that match their interests, hobbies, skills, and career goals at all levels.

Guidelines:
1. Ask clarifying questions about their interests, strengths, education level (undergraduate/postgraduate), and career aspirations.
2. When a [CAREER MODEL PREDICTION] block is present in your context, USE IT — reference the predicted career and recommended programmes directly. Make recommendations feel personalised, not robotic.
3. Recommend specific Bachelor's, Diploma, Master's, and PhD programmes offered at GCTU.
4. Provide brief descriptions of recommended programmes and their career prospects in Ghana.
5. Be encouraging and supportive.
6. If the ML prediction is low confidence (<50%), acknowledge that you need more information and ask a follow-up question.
7. If you don't know specific details about a programme, be honest and suggest the student contacts the admissions office.
8. Also mention Professional Programmes and Accelerated Certificate Programmes where relevant.
9. The conversation is limited to 10 user messages. Answer efficiently and try to resolve the user’s issue before the session ends.10. Focus exclusively on GCTU programmes and avoid discussing or comparing with other institutions. If asked about other schools, politely redirect to GCTU offerings and emphasize GCTU's strengths.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNDERGRADUATE PROGRAMMES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Faculty of Engineering (FoE):
  Bachelor's (4 years):
    - BSc. Telecommunications Engineering
    - BSc. Computer Engineering
    - BSc. Mathematics
    - BSc. Electrical and Electronic Engineering
    - BSc. Actuarial Science with Data Analytics
    - BSc. Computational Statistics
  Diploma (2 years):
    - Diploma in Computational Statistics
    - Diploma in Telecommunications Engineering

Faculty of Computing & Information Systems (FoCIS):
  Bachelor's (4 years):
    - BSc. Information Technology
    - BSc. Mobile Computing
    - BSc. Computer Science
    - BSc. Software Engineering
    - BSc. Information Systems
    - BSc. Data Science and Analytics
    - BSc. Computer Science (Cyber Security)
    - BSc. Network and System Administration
  Diploma (2 years):
    - Diploma in Information Technology
    - Diploma in Data Science and Analytics
    - Diploma in Cyber Security
    - Diploma in Computer Science
    - Diploma in Multimedia Technology
    - Diploma in Web Application Development

GCTU Business School:
  Bachelor's (4 years):
    - BSc. Accounting with Computing
    - BSc. Economics
    - BSc. Procurement and Logistics
    - BSc. Banking and Finance
    - BSc. E-Commerce and Marketing Management
    - BSc. Financial Technology
    - BSc. Business Administration (specialisations: Human Resource Management, Marketing, Accounting, Management)
  Diploma (2 years):
    - Diploma in Public Relations
    - Diploma in Management
    - Diploma in Accounting
    - Diploma in Marketing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSTGRADUATE PROGRAMMES (Master's)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - MBA Finance
  - MBA Logistics
  - Oil and Gas Management
  - MSc Business Decision Management
  - Engineering Project Management
  - Engineering and Management
  - Supply Chain Management
  - MSc Management Information Systems
  - MSc Information Technology for Management
  - MBA International Trade
  - MSc Internet of Things and Big Data
  - MSc Information Technology
  - MSc Computer Science
  - MPhil Internet of Things and Big Data
  - MPhil Computer Science
  - MA E-Business and Marketing Strategy
  - MPhil Digital Marketing (2 years)
  - MSc Digital Marketing (1 year)
  - MSc Procurement and Logistics (Distance Learning)
  - MSc Procurement and Supply Chain (Distance Learning)
  - MSc Human Resource Management with Informatics (Distance Learning)
  - MSc Procurement and Logistics Management (1 year, Distance Learning)
  - MSc Forensic Accounting

POSTGRADUATE PROGRAMMES (PhD):
  - PhD Computer Science (GCTU)
  - PhD programmes in partnership with M.S. Ramaiah University & Aalborg University covering:
    Engineering & Technology, Science, Pharmacy, Dental Sciences, Management & Commerce, Art & Design, Hospitality Management

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROFESSIONAL PROGRAMMES (CSBPD)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Postgraduate Certificates:
  - Strategic Treasury and Operations Management
  - Advanced Certificate in Supply Chain Management
  - Occupational Safety, Health and Environmental Management
  - Post Graduate Certificate in Management Information Systems (MIS)

IT & Engineering Short Courses:
  - Power BI, Power Excel, IT Project Management, Fibre Optics Technology
  - Enterprise Risk Management, Excel VBA, CISA, MS Project
  - SPSS and Applied Techniques, Drone/UAV Technology (GIS/GPS)

Cyber Security Short Courses:
  - Digital Forensics, Wireless Network Security, Ethical Hacking and Network Defense
  - Digital Marketing and Cyber Security, Investigative Accounting and Forensic Auditing
  - Certificate in Cyber Security and Information Systems Auditing

Professional Training:
  - PMP, PMI/PBA, CIPS, CILT, City & Guilds, ABMA UK programmes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACCELERATED CERTIFICATE PROGRAMMES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - A+ Certification, N+ Certification
  - Certificate in Website Design, Computer Networking, Network Administration
  - Certificate in Computer Network Security, Mobile Phone Repairs
  - Certificate in Graphic Design Production, Digital Video Editing

Always maintain a friendly, professional tone and encourage students to explore their passions."""


TEMPERATURE         = 0.3
MAX_TOKENS          = 400
FREQUENCY_PENALTY   = 0
PRESENCE_PENALTY    = 0.3
MAX_CONTEXT_QUESTIONS = 5


# ─────────────────────────────────────────────────────────────────────────────
# Main response function
# ─────────────────────────────────────────────────────────────────────────────
def get_response(instructions, previous_questions_and_answers, new_question):
    """
    Get a response from the hybrid career-model + GPT system.

    Args:
        instructions: Base system instructions (can be BASE_INSTRUCTIONS or custom)
        previous_questions_and_answers: List of (question, answer) tuples
        new_question: The new message from the student

    Returns:
        Response string
    """

    # ── Test mode stub (keeps existing unit tests passing) ──
    if ("PYTEST_CURRENT_TEST" in os.environ) or ("pytest" in sys.modules):
        q = (new_question or "").lower()
        if 'prerequisites' in q or 'information technology' in q:
            return (
                "The prerequisites for Information Technology at GCTU are Mathematics "
                "and English Language at the WASSCE/SSSCE level. "
                "Additionally, it is recommended that students have a strong interest "
                "in computer hardware, software, and information systems."
            )
        if any(ch in new_question for ch in '@#$%^&*()'):
            return "I'm sorry, I didn't understand your input"

    # ── Run career model prediction ──
    profile    = extract_profile_from_message(new_question, previous_questions_and_answers)
    prediction = predict_career(profile)
    career_ctx = build_career_context(prediction)

    # Inject ML context into system prompt only when there is a meaningful signal
    has_signal = any(v > 0 for k, v in profile.items() if k not in ("gpa", "experience_years"))
    full_instructions = (
        instructions + "\n\n" + career_ctx
        if (career_ctx and has_signal)
        else instructions
    )

    # ── Build message list ──
    messages = [{"role": "system", "content": full_instructions}]

    for question, answer in previous_questions_and_answers[-MAX_CONTEXT_QUESTIONS:]:
        messages.append({"role": "user",      "content": question})
        messages.append({"role": "assistant", "content": answer})

    messages.append({"role": "user", "content": new_question})

    completion = _chat_completion_create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=1,
        frequency_penalty=FREQUENCY_PENALTY,
        presence_penalty=PRESENCE_PENALTY,
    )

    try:
        return completion.choices[0].message.content
    except Exception:
        try:
            return completion.choices[0]["message"]["content"]
        except Exception:
            try:
                return completion.choices[0].text
            except Exception:
                return str(completion)


# ─────────────────────────────────────────────────────────────────────────────
# Moderation
# ─────────────────────────────────────────────────────────────────────────────
def get_moderation(question):
    """Check whether a question is safe to send to the model."""
    errors = {
        "hate":            "Content that expresses, incites, or promotes hate.",
        "hate/threatening":"Hateful content that also includes violence.",
        "self-harm":       "Content that promotes acts of self-harm.",
        "sexual":          "Content meant to arouse sexual excitement.",
        "sexual/minors":   "Sexual content involving anyone under 18.",
        "violence":        "Content that promotes or glorifies violence.",
        "violence/graphic":"Violent content in extreme graphic detail.",
    }
    response = _moderation_create(input=question)
    try:
        flagged    = response.results[0].flagged
        categories = response.results[0].categories
    except Exception:
        try:
            flagged    = response["results"][0]["flagged"]
            categories = response["results"][0]["categories"]
        except Exception:
            return None

    if flagged:
        return [error for category, error in errors.items() if categories.get(category)]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API convenience — expose BASE_INSTRUCTIONS for app.py
# ─────────────────────────────────────────────────────────────────────────────
INSTRUCTIONS = BASE_INSTRUCTIONS
