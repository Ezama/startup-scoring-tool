import streamlit as st
import requests
import pandas as pd
import time
import altair as alt

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from selenium import webdriver
from altair import Chart
from reportlab.platypus import Image  # Add this to your import section if not there

import io
import datetime
import os


st.set_page_config(page_title="Startup Scoring Tool", layout="centered")
st.title("Startup Scoring Tool")

st.markdown(
    """
Welcome to the **Startup Scoring Tool** — a lightweight app that helps you quickly evaluate and compare startups based on public data like industry, employee size, and email confidence.

You can:
- 🔍 Analyze a single domain to get an instant score
- 📤 Upload a CSV of multiple domains for batch analysis
- 📈 View and download a visual scoring report with insights

Ideal for early-stage VC workflows, due diligence, or tech scouting.
"""
)

# Input
single_domain = st.text_input(
    "Enter a company domain below to analyze and score it based on key attributes.",
    placeholder="e.g. stripe.com",
)
# api_key = st.secrets["api"]["api_key"]

# Safe access to secrets
api_key = st.secrets["api"].get("api_key") if "api" in st.secrets else None

if not api_key:
    st.error("API key not found. Please check your `.streamlit/secrets.toml` file.")
    st.stop()  # stop the app if the key is critical


# ---- Scoring Function ----
def score_startup(data):
    score = 0
    org = data.get("organization", data.get("domain", "N/A"))
    industry = data.get("industry", "")
    email_count = data.get("emails_count", 0)
    employees = data.get("employees", 0)

    # Score logic
    if email_count:
        score += min(30, email_count * 10)
    if industry and industry.lower() in ["software", "technology", "saas"]:
        score += 10
    if employees and employees > 10:
        score += 20
    if data.get("webmail"):
        score += 10

    for email in data.get("emails", []):
        if email["type"] in ["generic", "personal"]:
            if email.get("confidence", 0) >= 80:
                score += 10
            if email.get("position") and email["position"].lower() in [
                "ceo",
                "founder",
                "cto",
            ]:
                score += 5

    return {
        "organization": org,
        "domain": data.get("domain"),
        "industry": industry or "N/A",
        "emails_found": email_count,
        "employees": employees or "N/A",
        "score": score,
    }


if st.button("Analyze"):
    if not single_domain:
        st.warning("Please enter a domain.")
    else:
        with st.spinner("Looking up domain..."):
            url = f"https://api.hunter.io/v2/domain-search?domain={single_domain}&api_key={api_key}"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json().get("data", {})
                result = score_startup(data)
                st.success(
                    f"✅ {result['organization']} scored **{result['score']}/100**"
                )

                st.markdown("### 🧾 Details")
                st.json(result)
            else:
                st.error("❌ Failed to fetch data. Check domain or API usage.")


# ---- File Upload UI ----
st.sidebar.header("📤 Upload CSV of Domains")
st.sidebar.markdown(
    """
Upload a **CSV file** containing a list of startup domains you want to analyze.

**PS:** Make sure your file has a column labeled `domain`.
"""
)
uploaded_file = st.sidebar.file_uploader("Upload your CSV file", type="csv")

st.markdown(
    """
<style>
/* Increase sidebar width */
section[data-testid="stSidebar"] {
    width: 350px !important;
}

section[data-testid="stSidebar"] > div {
    width: 350px !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---- Process CSV ----
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if "domain" not in df.columns:
        st.error("CSV must have a 'domain' column.")
    else:
        st.success("✅ File uploaded successfully!")
        results = []

        with st.spinner("🔍 Scoring startups..."):
            for domain in df["domain"]:
                try:
                    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
                    response = requests.get(url)
                    if response.status_code == 200:
                        data = response.json()["data"]
                        result = score_startup(data)
                        results.append(result)
                    else:
                        results.append(
                            {
                                "organization": "N/A",
                                "domain": domain,
                                "industry": "N/A",
                                "emails_found": 0,
                                "employees": "N/A",
                                "score": 0,
                            }
                        )
                except:
                    results.append(
                        {
                            "organization": "N/A",
                            "domain": domain,
                            "industry": "N/A",
                            "emails_found": 0,
                            "employees": "N/A",
                            "score": 0,
                        }
                    )
                time.sleep(1.1)  # To avoid rate limit (Free API has 30–50 calls/day)

        results_df = pd.DataFrame(results).sort_values(by="score", ascending=False)

        # ---- Add Score Grouping ----
        def classify_score(score):
            if score >= 75:
                return "High"
            elif score >= 40:
                return "Mid"
            else:
                return "Low"

        results_df["score_group"] = results_df["score"].apply(classify_score)

        results_df = pd.DataFrame(results).sort_values(by="score", ascending=False)

        # ---- Dashboard ----
        st.markdown("### 📈 Top 10 Scoring Startups")

        top10 = results_df.head(10)
        top10["score_group"] = top10["score"].apply(classify_score)
        top10["score_group"] = top10["score_group"].astype(str)

        chart = (
            alt.Chart(top10)
            .mark_bar()
            .encode(
                x=alt.X("domain:N", sort="-y", title="Startup Domain"),
                y=alt.Y("score:Q", title="Score"),
                color=alt.Color(
                    "score_group:N",
                    scale=alt.Scale(
                        domain=["High", "Mid", "Low"],
                        range=["#2ECC71", "#F1C40F", "#E74C3C"],
                    ),
                    legend=alt.Legend(title="Score Tier"),
                ),
                tooltip=["organization", "score", "score_group", "industry"],
            )
            .properties(width=700, height=400)
        )

        # ---- Save Chart as PNG (Now works with vl-convert-python) ----
        chart_filename = "score_chart.png"
        try:
            chart.save(chart_filename)
        except Exception as e:
            st.error(f"❌ Failed to save chart: {e}")
            chart_filename = None

        # ---- Show Table in App
        st.markdown("### 📋 Full Results Table")
        st.dataframe(results_df, use_container_width=True)

        # ---- Show chart on Streamlit
        st.altair_chart(chart, use_container_width=True)

        # ---- Generate PDF with Chart and Table ----
        def generate_pdf_with_chart(df, chart_path):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []

            styles = getSampleStyleSheet()
            date_str = datetime.datetime.now().strftime("%B %d, %Y")
            elements.append(Paragraph("📊 Startup Scoring Report", styles["Title"]))
            elements.append(Paragraph(f"Generated on {date_str}", styles["Normal"]))
            elements.append(Spacer(1, 12))

            if chart_path and os.path.exists(chart_path):
                elements.append(Image(chart_path, width=500, height=300))
                elements.append(Spacer(1, 20))

            data = [df.columns.tolist()] + df.values.tolist()
            table = Table(data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ]
                )
            )
            elements.append(table)

            doc.build(elements)
            pdf = buffer.getvalue()
            buffer.close()
            return pdf

        # ---- Download Button for PDF ----
        pdf_bytes = generate_pdf_with_chart(results_df, chart_filename)

        st.download_button(
            label="📄 Download Full Report as PDF",
            data=pdf_bytes,
            file_name="startup_scores_report.pdf",
            mime="application/pdf",
        )

        csv = results_df.to_csv(index=False).encode("utf-8")

        # ---- Download Button for CSV ----
        st.download_button(
            label="📥 Download Scores as CSV",
            data=csv,
            file_name="startup_scores.csv",
            mime="text/csv",
        )
