# career_model_trainer.py
# =======================
# Trains a career recommendation model on the Kaggle "Career Recommendation Dataset"
# (breejeshdhar/career-recommendation-dataset) and saves it as career_model.pkl.

# Run once:
#     python career_model_trainer.py

# The saved model is then loaded by chatbot_logic.py at runtime.

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline

# ─────────────────────────────────────────────────────────────────────────────
# GCTU CAREER → PROGRAMME MAPPING
# Maps dataset career labels to actual GCTU programmes and departments.
# Edit this dict whenever GCTU updates its programme offerings.
# ─────────────────────────────────────────────────────────────────────────────
GCTU_CAREER_MAP = {
    # ── Computing & IT ────────────────────────────────────────────────────────
    "Software Developer": {
        "programmes": [
            "BSc. Computer Science",
            "BSc. Software Engineering",
            "MSc Computer Science",
            "MPhil Computer Science",
        ],
        "faculty": "Faculty of Computing & Information Systems (FoCIS)",
        "career_outlook": "Software developers are in high demand across Ghana's growing fintech and tech sector.",
        "key_skills": ["Python", "Java", "JavaScript", "Algorithms", "Databases"],
    },
    "Data Scientist": {
        "programmes": [
            "BSc. Data Science and Analytics",
            "MSc Information Technology",
            "MSc Internet of Things and Big Data",
            "MPhil Internet of Things and Big Data",
        ],
        "faculty": "Faculty of Computing & Information Systems (FoCIS)",
        "career_outlook": "Data science roles are growing rapidly in banking, telecoms, and government in Ghana.",
        "key_skills": ["Python", "R", "Machine Learning", "Statistics", "SQL"],
    },
    "Network Engineer": {
        "programmes": [
            "BSc. Network and System Administration",
            "BSc. Telecommunications Engineering",
            "MSc Information Technology",
            "MSc Information Technology for Management",
        ],
        "faculty": "Faculty of Engineering (FoE) / FoCIS",
        "career_outlook": "Network engineers are essential to Ghana's expanding telecoms infrastructure.",
        "key_skills": ["Networking", "Linux", "Cisco", "Security", "Cloud"],
    },
    "Cybersecurity Analyst": {
        "programmes": [
            "BSc. Computer Science (Cyber Security)",
            "Diploma in Cyber Security",
            "MSc Computer Science",
            "Certificate in Cyber Security and Information Systems Auditing (Professional)",
        ],
        "faculty": "Faculty of Computing & Information Systems (FoCIS)",
        "career_outlook": "Cybersecurity is one of the fastest-growing fields in Ghana and Africa broadly.",
        "key_skills": ["Ethical Hacking", "Firewalls", "Python", "Risk Assessment", "Digital Forensics"],
    },
    "Database Administrator": {
        "programmes": [
            "BSc. Information Systems",
            "BSc. Computer Science",
            "MSc Information Technology",
            "MSc Management Information Systems",
        ],
        "faculty": "Faculty of Computing & Information Systems (FoCIS)",
        "career_outlook": "DBAs are in steady demand in banking, healthcare, and public sector in Ghana.",
        "key_skills": ["SQL", "Oracle", "MySQL", "Data Modelling", "Backup & Recovery"],
    },
    "Business Analyst": {
        "programmes": [
            "BSc. Information Systems",
            "BSc. Business Administration",
            "MSc Business Decision Management",
            "MBA International Trade",
            "Post Graduate Certificate in Management Information Systems (MIS)",
        ],
        "faculty": "FoCIS / GCTU Business School",
        "career_outlook": "Business analysts bridge tech and business — highly valued in Ghana's corporate sector.",
        "key_skills": ["Excel", "Data Analysis", "Communication", "Process Modelling", "Power BI"],
    },
    "Mobile Developer": {
        "programmes": [
            "BSc. Mobile Computing",
            "BSc. Software Engineering",
            "Diploma in Web Application Development",
        ],
        "faculty": "Faculty of Computing & Information Systems (FoCIS)",
        "career_outlook": "Mobile development is booming in Ghana given high smartphone penetration.",
        "key_skills": ["Android", "iOS", "React Native", "Flutter", "APIs"],
    },
    "Web Developer": {
        "programmes": [
            "BSc. Software Engineering",
            "Diploma in Web Application Development",
            "BSc. Computer Science",
            "Certificate in Website Design (Accelerated)",
        ],
        "faculty": "Faculty of Computing & Information Systems (FoCIS)",
        "career_outlook": "Web development skills are needed in every industry across Ghana.",
        "key_skills": ["HTML/CSS", "JavaScript", "React", "Node.js", "PHP"],
    },
    "AI/ML Engineer": {
        "programmes": [
            "MSc Computer Science",
            "MPhil Computer Science",
            "BSc. Data Science and Analytics",
            "MSc Internet of Things and Big Data",
            "PhD Computer Science",
        ],
        "faculty": "Faculty of Computing & Information Systems (FoCIS)",
        "career_outlook": "AI/ML engineering is an emerging high-salary field in Ghana's tech ecosystem.",
        "key_skills": ["Python", "TensorFlow", "PyTorch", "Mathematics", "Cloud AI"],
    },
    "IT Project Manager": {
        "programmes": [
            "BSc. Information Technology",
            "MSc Information Technology for Management",
            "Engineering Project Management",
            "MBA International Trade",
            "IT Project Management (Professional Short Course)",
        ],
        "faculty": "FoCIS / GCTU Business School",
        "career_outlook": "IT project management is highly valued in Ghana's growing ICT sector and NGOs.",
        "key_skills": ["PMP", "Agile", "Scrum", "Leadership", "Risk Management"],
    },
    "IoT Engineer": {
        "programmes": [
            "BSc. Computer Engineering",
            "MSc Internet of Things and Big Data",
            "MPhil Internet of Things and Big Data",
            "BSc. Telecommunications Engineering",
            "BSc. Electrical and Electronic Engineering",
        ],
        "faculty": "Faculty of Engineering (FoE)",
        "career_outlook": "IoT is growing in agriculture, health, and smart city projects across Ghana.",
        "key_skills": ["Embedded Systems", "Python", "Sensors", "Cloud IoT", "Networking"],
    },
    "Cloud Architect": {
        "programmes": [
            "BSc. Network and System Administration",
            "MSc Computer Science",
            "MSc Information Technology",
            "Certificate in Computer Network Security (Accelerated)",
        ],
        "faculty": "Faculty of Computing & Information Systems (FoCIS)",
        "career_outlook": "Cloud skills are increasingly demanded by Ghanaian enterprises moving to cloud infrastructure.",
        "key_skills": ["AWS", "Azure", "GCP", "DevOps", "Linux"],
    },
    # ── Business & Finance ────────────────────────────────────────────────────
    "Financial Analyst": {
        "programmes": [
            "BSc. Accounting with Computing",
            "BSc. Banking and Finance",
            "BSc. Financial Technology",
            "MBA Finance",
            "MSc Forensic Accounting",
        ],
        "faculty": "GCTU Business School",
        "career_outlook": "Financial analysis skills are critical in Ghana's banking and fintech industries.",
        "key_skills": ["Excel", "Financial Modelling", "Accounting", "Risk Analysis", "Power BI"],
    },
    "Digital Marketer": {
        "programmes": [
            "BSc. E-Commerce and Marketing Management",
            "MSc. Digital Marketing (1 year)",
            "MPhil Digital Marketing (2 years)",
            "MA E-Business and Marketing Strategy",
        ],
        "faculty": "GCTU Business School",
        "career_outlook": "Digital marketing is rapidly expanding across Ghana's e-commerce and media sectors.",
        "key_skills": ["SEO", "Social Media", "Google Ads", "Analytics", "Content Strategy"],
    },
    "Supply Chain / Logistics Manager": {
        "programmes": [
            "BSc. Procurement and Logistics",
            "MBA Logistics",
            "Supply Chain Management (Postgraduate)",
            "MSc Procurement and Logistics (Distance Learning)",
            "MSc Procurement and Supply Chain (Distance Learning)",
            "MSc Procurement and Logistics Management — 1 year (Distance Learning)",
            "Advanced Certificate in Supply Chain Management (Professional)",
        ],
        "faculty": "GCTU Business School",
        "career_outlook": "Supply chain roles are critical to Ghana's port, oil & gas, and manufacturing sectors.",
        "key_skills": ["Logistics", "ERP Systems", "Negotiation", "Procurement", "CIPS"],
    },
    "Human Resource Manager": {
        "programmes": [
            "BSc. Business Administration (Human Resource Management option)",
            "MSc Human Resource Management with Informatics (Distance Learning)",
            "Advanced Strategic Human Resource Management and Leadership Training (Professional)",
        ],
        "faculty": "GCTU Business School",
        "career_outlook": "HR management skills are in consistent demand across public and private sectors in Ghana.",
        "key_skills": ["People Management", "Labour Law", "HR Analytics", "Communication", "Leadership"],
    },
    # ── Engineering & Science ─────────────────────────────────────────────────
    "Actuary": {
        "programmes": [
            "BSc. Actuarial Science with Data Analytics",
            "BSc. Computational Statistics",
            "Diploma in Computational Statistics",
        ],
        "faculty": "Faculty of Engineering (FoE)",
        "career_outlook": "Actuaries are well-compensated in Ghana's insurance and financial services industries.",
        "key_skills": ["Statistics", "Mathematics", "Risk Modelling", "Excel", "R"],
    },
    "Electrical / Electronics Engineer": {
        "programmes": [
            "BSc. Electrical and Electronic Engineering",
            "BSc. Computer Engineering",
            "Engineering and Management (Postgraduate)",
            "Level 3 Diploma in Electrical and Electronic Engineering — City & Guilds (Professional)",
        ],
        "faculty": "Faculty of Engineering (FoE)",
        "career_outlook": "Electrical engineers are needed for Ghana's energy transition and infrastructure projects.",
        "key_skills": ["Circuit Design", "PLC", "AutoCAD", "Power Systems", "Embedded Systems"],
    },
    "Oil & Gas Professional": {
        "programmes": [
            "Oil and Gas Management (Postgraduate)",
            "BSc. Electrical and Electronic Engineering",
            "BSc. Telecommunications Engineering",
            "Occupational Safety, Health and Environmental Management (Professional Certificate)",
        ],
        "faculty": "Faculty of Engineering (FoE) / GCTU Business School",
        "career_outlook": "Ghana's oil and gas industry continues to create professional opportunities along the Western coast.",
        "key_skills": ["HSE", "Project Management", "Engineering Principles", "Risk Management"],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE DEFINITIONS
# These match the column names in the Kaggle career recommendation dataset.
# Adjust if your CSV has different column names.
# ─────────────────────────────────────────────────────────────────────────────
SKILL_FEATURES = [
    "python_yn", "r_yn", "spark_yn", "mongodb_yn", "tableau_yn",
    "power_bi_yn", "hadoop_yn", "sql_yn", "excel_yn", "java_yn",
    "tensorflow_yn", "keras_yn", "pytorch_yn", "hadoop_yn",
    "communication_skills", "analytical_skills", "problem_solving",
    "creativity", "teamwork", "leadership",
]

NUMERIC_FEATURES = [
    "gpa", "experience_years",
]

TARGET_COLUMN = "career_recommendation"  # label column in dataset


def load_and_preprocess(csv_path: str):
    """Load CSV, clean, and return features X and labels y."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Keep only columns that exist in this dataset
    available_skills = [c for c in SKILL_FEATURES if c in df.columns]
    available_numeric = [c for c in NUMERIC_FEATURES if c in df.columns]

    feature_cols = available_skills + available_numeric
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not found. Available: {list(df.columns)}")

    df = df.dropna(subset=[TARGET_COLUMN])
    X = df[feature_cols].fillna(0)
    y = df[TARGET_COLUMN].str.strip()

    return X, y, feature_cols


def train_model(csv_path: str, output_path: str = "career_model.pkl"):
    """Train Random Forest on career dataset and save model bundle."""
    print(f"Loading dataset from: {csv_path}")
    X, y, feature_cols = load_and_preprocess(csv_path)

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=3,
            random_state=42,
            n_jobs=-1,
        )),
    ])

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {acc:.2%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # Save bundle
    bundle = {
        "pipeline": pipeline,
        "label_encoder": le,
        "feature_cols": feature_cols,
        "gctu_career_map": GCTU_CAREER_MAP,
        "accuracy": acc,
    }
    with open(output_path, "wb") as f:
        pickle.dump(bundle, f)

    print(f"\nModel saved to: {output_path}")
    return bundle


def create_demo_model(output_path: str = "career_model.pkl"):
    """
    Create a demo model using synthetic data when the Kaggle CSV is not available.
    This is useful for development/testing before you download the real dataset.
    The demo model uses the same feature structure as the real model.
    """
    print("Creating demo model with synthetic data...")

    np.random.seed(42)
    n_samples = 1500
    careers = list(GCTU_CAREER_MAP.keys())

    # Synthetic skill profiles per career (rough archetype)
    # Columns: python,r,spark,mongodb,tableau,power_bi,hadoop,sql,excel,java,
    #          tensorflow,keras,pytorch,hadoop2,
    #          comm,analytical,problem_solving,creativity,teamwork,leadership
    career_profiles = {
        "Software Developer":               [0,0,0,0,0, 0,0,1,0,1, 0,0,0,0, 3,2,3,2,2,2],
        "Data Scientist":                   [1,1,1,0,1, 1,1,1,0,0, 1,1,1,1, 2,3,3,2,2,1],
        "Network Engineer":                 [0,0,0,0,0, 0,0,1,0,0, 0,0,0,0, 2,2,3,1,2,2],
        "Cybersecurity Analyst":            [1,0,0,0,0, 0,0,1,0,1, 0,0,0,0, 2,3,3,1,2,2],
        "Database Administrator":           [0,0,0,1,0, 0,0,1,1,0, 0,0,0,0, 2,3,3,1,2,1],
        "Business Analyst":                 [0,0,0,0,1, 1,0,1,1,0, 0,0,0,0, 3,3,2,2,3,2],
        "Mobile Developer":                 [1,0,0,0,0, 0,0,0,0,1, 0,0,0,0, 2,2,3,3,2,1],
        "Web Developer":                    [1,0,0,0,0, 0,0,1,0,1, 0,0,0,0, 2,2,3,3,2,1],
        "AI/ML Engineer":                   [1,1,0,0,0, 0,0,1,0,0, 1,1,1,0, 2,3,3,3,2,1],
        "IT Project Manager":               [0,0,0,0,0, 1,0,0,1,0, 0,0,0,0, 3,2,2,2,3,3],
        "IoT Engineer":                     [1,0,0,0,0, 0,0,1,0,0, 0,0,0,0, 2,3,3,2,2,2],
        "Cloud Architect":                  [1,0,0,0,0, 0,1,1,0,0, 0,0,0,0, 2,3,3,1,2,2],
        "Financial Analyst":                [0,0,0,0,1, 1,0,1,1,0, 0,0,0,0, 3,3,2,1,2,2],
        "Digital Marketer":                 [0,0,0,0,1, 1,0,0,1,0, 0,0,0,0, 3,2,2,3,2,2],
        "Supply Chain / Logistics Manager": [0,0,0,0,0, 1,0,1,1,0, 0,0,0,0, 3,2,2,1,3,3],
        "Human Resource Manager":           [0,0,0,0,0, 0,0,0,1,0, 0,0,0,0, 4,2,2,2,3,3],
        "Actuary":                          [0,1,0,0,0, 0,0,0,1,0, 0,0,0,0, 2,3,2,1,2,1],
        "Electrical / Electronics Engineer":[0,0,0,0,0, 0,0,0,0,0, 0,0,0,0, 2,3,3,2,2,2],
        "Oil & Gas Professional":           [0,0,0,0,0, 0,0,0,0,0, 0,0,0,0, 3,2,3,1,2,3],
    }

    skill_cols = [
        "python_yn","r_yn","spark_yn","mongodb_yn","tableau_yn",
        "power_bi_yn","hadoop_yn","sql_yn","excel_yn","java_yn",
        "tensorflow_yn","keras_yn","pytorch_yn","hadoop_yn2",
        "communication_skills","analytical_skills","problem_solving",
        "creativity","teamwork","leadership",
    ]
    numeric_cols = ["gpa", "experience_years"]
    all_cols = skill_cols + numeric_cols

    rows, labels = [], []
    per_career = n_samples // len(careers)

    for career in careers:
        base = career_profiles[career]
        for _ in range(per_career):
            noise = [max(0, b + np.random.randint(-1, 2)) for b in base]
            # Binary clamp for skill flags
            noise_clamped = [min(1, v) if i < 14 else min(4, max(1, v)) for i, v in enumerate(noise)]
            gpa = round(np.random.uniform(2.0, 4.0), 2)
            exp = max(0, int(np.random.normal(2, 2)))
            rows.append(noise_clamped + [gpa, exp])
            labels.append(career)

    df = pd.DataFrame(rows, columns=all_cols)
    y = pd.Series(labels)

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(df, y_enc, test_size=0.2, random_state=42)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)),
    ])
    pipeline.fit(X_train, y_train)

    acc = accuracy_score(y_test, pipeline.predict(X_test))
    print(f"Demo model accuracy: {acc:.2%}")

    bundle = {
        "pipeline": pipeline,
        "label_encoder": le,
        "feature_cols": all_cols,
        "gctu_career_map": GCTU_CAREER_MAP,
        "accuracy": acc,
    }
    with open(output_path, "wb") as f:
        pickle.dump(bundle, f)

    print(f"Demo model saved to: {output_path}")
    return bundle


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        train_model(sys.argv[1])
    else:
        print("No CSV path provided — creating demo model.")
        print("Usage with real data: python career_model_trainer.py career_dataset.csv")
        create_demo_model()
