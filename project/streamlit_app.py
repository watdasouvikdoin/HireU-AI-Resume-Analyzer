"""
streamlit_app.py — HireU AI Resume Intelligence Platform
Frontend for the HireU AI Resume Analyzer.
Communicates with the FastAPI backend at http://127.0.0.1:8000/api/v1.
"""

import streamlit as st
import requests
import json
import pandas as pd

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="HireU — AI Resume Intelligence Platform", layout="wide")


# ---------------------------------------------------------------------------
# Custom CSS — Dark modern HireU theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ── Global ── */
    [data-testid="stAppViewContainer"] {
        background-color: #0e0e10;
        color: #e8e8e8;
    }
    [data-testid="stSidebar"] {
        background-color: #141418;
        border-right: 1px solid #2a2a35;
    }

    /* ── Header ── */
    .hireu-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a78bfa, #6366f1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hireu-sub {
        color: #888;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    /* ── Skill Gap Section ── */
    .sg-container {
        background: #1a1a24;
        border: 1px solid #2e2e42;
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        margin-top: 1.2rem;
    }
    .sg-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #a78bfa;
        margin-bottom: 0.8rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    .sg-pct-label {
        font-size: 1.6rem;
        font-weight: 800;
        margin-bottom: 0.1rem;
    }

    /* ── Skill Chips ── */
    .chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 0.5rem;
        margin-bottom: 0.8rem;
    }
    .chip-green {
        background: rgba(52, 211, 153, 0.15);
        border: 1px solid rgba(52, 211, 153, 0.45);
        color: #34d399;
        border-radius: 999px;
        padding: 4px 14px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }
    .chip-red {
        background: rgba(248, 113, 113, 0.12);
        border: 1px solid rgba(248, 113, 113, 0.40);
        color: #f87171;
        border-radius: 999px;
        padding: 4px 14px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }
    .chip-label {
        font-size: 0.78rem;
        font-weight: 700;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
        margin-top: 0.6rem;
    }

    /* ── Progress Bar ── */
    .sg-bar-bg {
        background: #2a2a38;
        border-radius: 999px;
        height: 12px;
        margin-top: 0.4rem;
        margin-bottom: 0.5rem;
        overflow: hidden;
    }
    .sg-bar-fill {
        height: 100%;
        border-radius: 999px;
        transition: width 0.4s ease;
    }

    /* ── Threshold Badge ── */
    .badge {
        display: inline-block;
        border-radius: 999px;
        padding: 3px 14px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-left: 10px;
        vertical-align: middle;
    }
    .badge-strong  { background: rgba(52,211,153,0.18); color: #34d399; border: 1px solid #34d399; }
    .badge-hire    { background: rgba(96,165,250,0.18); color: #60a5fa; border: 1px solid #60a5fa; }
    .badge-consider{ background: rgba(251,191,36,0.18); color: #fbbf24; border: 1px solid #fbbf24; }
    .badge-reject  { background: rgba(248,113,113,0.18); color: #f87171; border: 1px solid #f87171; }

    /* ── AI Insight Card ── */
    .ai-card {
        background: linear-gradient(135deg, #1e1b2e, #1a1a28);
        border: 1px solid #3b3660;
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin-top: 1rem;
    }
    .ai-card-title {
        font-size: 0.8rem;
        font-weight: 700;
        color: #a78bfa;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 0.5rem;
    }
    .ai-card-body {
        font-size: 0.92rem;
        color: #d0cfdf;
        line-height: 1.7;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------
st.markdown('<p class="hireu-header">HireU</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hireu-sub">HireU — AI Resume Intelligence Platform &nbsp;·&nbsp; '
    'Upload a Job Description and candidate resumes to get an AI-scored shortlist.</p>',
    unsafe_allow_html=True
)


# ---------------------------------------------------------------------------
# Helper: Render Skill Gap Analysis block
# ---------------------------------------------------------------------------
def render_skill_gap(skill_gap: dict, ai_insight: str):
    """
    Renders the full Skill Gap Analysis UI block for one candidate.
    Broken into multiple st.markdown() calls to avoid Streamlit's
    HTML sanitizer breaking large single-block HTML strings.
    """
    match_pct = skill_gap.get("match_percentage", 0)
    matched = skill_gap.get("matched", [])
    missing = skill_gap.get("missing", [])
    threshold = skill_gap.get("threshold_label", "Unknown")

    # Determine colors based on threshold
    if match_pct >= 85:
        bar_color, pct_color, badge_cls = "#34d399", "#34d399", "badge-strong"
    elif match_pct >= 70:
        bar_color, pct_color, badge_cls = "#60a5fa", "#60a5fa", "badge-hire"
    elif match_pct >= 50:
        bar_color, pct_color, badge_cls = "#fbbf24", "#fbbf24", "badge-consider"
    else:
        bar_color, pct_color, badge_cls = "#f87171", "#f87171", "badge-reject"

    # ── Section header + progress bar ──
    st.markdown(f"""
<div class="sg-container">
<div class="sg-title">🔬 Skill Gap Analysis</div>
<div>
<span class="sg-pct-label" style="color:{pct_color}">{match_pct}%</span>
<span class="badge {badge_cls}">{threshold}</span>
<span style="color:#666;font-size:0.82rem;margin-left:8px;">Skill Compatibility</span>
</div>
<div class="sg-bar-bg"><div class="sg-bar-fill" style="width:{match_pct}%;background:{bar_color};"></div></div>
</div>
""", unsafe_allow_html=True)

    # ── Matched skill chips ──
    matched_chips = "".join(
        f'<span class="chip-green">✓ {m.get("jd_skill","").title()}</span>'
        for m in matched
    ) or '<span style="color:#555;font-size:0.82rem;">No matched skills found</span>'

    st.markdown(f"""
<div class="sg-container" style="border-top:none;padding-top:0.6rem;margin-top:-6px;">
<div class="chip-label">✅ Matched Skills ({len(matched)})</div>
<div class="chip-row">{matched_chips}</div>
</div>
""", unsafe_allow_html=True)

    # ── Missing skill chips ──
    missing_chips = "".join(
        f'<span class="chip-red">✗ {s.title()}</span>'
        for s in missing
    ) or '<span style="color:#555;font-size:0.82rem;">No missing skills — great match!</span>'

    st.markdown(f"""
<div class="sg-container" style="border-top:none;padding-top:0.6rem;margin-top:-6px;">
<div class="chip-label">❌ Missing Skills ({len(missing)})</div>
<div class="chip-row">{missing_chips}</div>
</div>
""", unsafe_allow_html=True)

    # ── AI Hiring Insight card ──
    insight_text = ai_insight if ai_insight else "AI insight not available for this candidate."
    st.markdown(f"""
<div class="ai-card">
<div class="ai-card-title">🤖 AI Hiring Insight</div>
<div class="ai-card-body">{insight_text}</div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — Job Description Input
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("1. Job Description")
    jd_input_method = st.radio("Provide JD via:", ["Text", "File (.txt, .pdf)"])
    raw_jd_text = ""

    if jd_input_method == "Text":
        raw_jd_text = st.text_area("Paste Job Description Here", height=300)
    else:
        jd_file = st.file_uploader("Upload JD File", type=["txt", "pdf"])
        if jd_file:
            if jd_file.name.endswith(".pdf"):
                import fitz
                doc = fitz.open(stream=jd_file.read(), filetype="pdf")
                for page in doc:
                    raw_jd_text += page.get_text()
            else:
                raw_jd_text = jd_file.read().decode("utf-8")

    if st.button("Parse JD"):
        if not raw_jd_text:
            st.warning("Please provide a Job Description.")
        else:
            with st.spinner("Parsing JD with AI..."):
                try:
                    res = requests.post(f"{API_BASE_URL}/parse_jd", json={"raw_text": raw_jd_text})
                    if res.status_code == 200:
                        st.session_state["jd"] = res.json()
                        st.success("JD Parsed Successfully!")
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Failed to connect to API: {e}")

if "jd" in st.session_state:
    with st.expander("Parsed Job Description Profile", expanded=False):
        st.json(st.session_state["jd"])


# ---------------------------------------------------------------------------
# Main Area — Candidate Upload
# ---------------------------------------------------------------------------
st.header("2. Upload Candidates")
candidate_files = st.file_uploader(
    "Upload Candidate Resumes or LinkedIn Profiles",
    type=["pdf", "docx", "json"],
    accept_multiple_files=True
)

if st.button("Analyze Candidates"):
    if "jd" not in st.session_state:
        st.error("Please parse the Job Description first.")
    elif not candidate_files:
        st.error("Please upload at least one candidate file.")
    else:
        # Step 1: Upload and extract candidates
        with st.spinner(f"Extracting profiles from {len(candidate_files)} files..."):
            files_payload = []
            for file in candidate_files:
                files_payload.append(("files", (file.name, file.getvalue(), file.type)))

            upload_res = requests.post(f"{API_BASE_URL}/upload_resumes", files=files_payload)

            if upload_res.status_code == 200:
                candidates_data = upload_res.json()["candidates"]
                st.success(f"Successfully extracted {len(candidates_data)} candidates.")
            else:
                st.error(f"Error extracting resumes: {upload_res.text}")
                st.stop()

        # Step 2: Analyze Candidates against JD (includes skill gap + AI insight)
        with st.spinner("Scoring, ranking, and generating Skill Gap insights..."):
            analysis_payload = {
                "jd": st.session_state["jd"],
                "candidates_data": candidates_data
            }

            analyze_res = requests.post(f"{API_BASE_URL}/analyze_candidates", json=analysis_payload)

            if analyze_res.status_code == 200:
                results = analyze_res.json()["results"]
                st.session_state["results"] = results
                st.success("Analysis Complete!")
            else:
                st.error(f"Error analyzing candidates: {analyze_res.text}")


# ---------------------------------------------------------------------------
# Results — Ranked Shortlist + Skill Gap Analysis
# ---------------------------------------------------------------------------
if "results" in st.session_state:
    st.markdown("---")
    st.header("3. Ranked Shortlist")
    results = st.session_state["results"]

    # Summary metrics
    if len(results) > 0:
        top_cand = results[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Candidates Scored", len(results))
        col2.metric("Top Candidate", top_cand["candidate_name"])
        col3.metric("Top Score", f"{top_cand['final_score']} / 100")

    # Dataframe
    df_data = []
    for r in results:
        df_data.append({
            "Candidate ID": r["candidate_id"],
            "Name": r["candidate_name"],
            "Final Score": r["final_score"],
            "Recommendation": r["recommendation"],
            "Skill Match %": r.get("skill_gap", {}).get("match_percentage", "N/A"),
        })
    df = pd.DataFrame(df_data)
    st.dataframe(df.style.highlight_max(subset=["Final Score"], color="lightgreen"), use_container_width=True)

    # Report Export
    st.markdown("### Export Results")
    if st.button("📄 Generate Downloadable Reports (PDF & HTML)", use_container_width=True):
        with st.spinner("Generating Reports..."):
            requests.post(f"{API_BASE_URL}/generate_report", json={"format": "html", "results": results})
            pdf_res = requests.post(f"{API_BASE_URL}/generate_report", json={"format": "pdf", "results": results})
            st.success(f"Reports saved to local 'outputs' directory! (See {pdf_res.json().get('path')})")

    # ---------------------------------------------------------------------------
    # Detailed Candidate Expanders — includes Skill Gap Analysis
    # ---------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔍 Detailed Scoring, Skill Gap & Human Override")

    for idx, r in enumerate(results):
        with st.expander(f"🏅 {r['candidate_name']} — Score: {r['final_score']} ({r['recommendation']})"):
            st.caption(f"Candidate ID: `{r['candidate_id']}`")

            # ── Dimension Scores (existing) ──
            dims = r["dimensions"]
            cols = st.columns(len(dims))
            for i, (dim_name, dim_data) in enumerate(dims.items()):
                with cols[i]:
                    st.metric(
                        label=f"{dim_name.title()} ({dim_data['weight']*100:.0f}%)",
                        value=f"{dim_data['score']}/10"
                    )
                    st.caption(f"_{dim_data['justification']}_")

            st.divider()

            # ── Skill Gap Analysis (NEW) ──
            skill_gap = r.get("skill_gap")
            ai_insight = r.get("ai_insight", "")
            if skill_gap:
                render_skill_gap(skill_gap, ai_insight)
            else:
                st.info("Skill Gap data not available for this candidate.")

            st.divider()

            # ── Human-in-the-Loop Override (existing) ──
            st.markdown("#### ⚖️ Human-in-the-Loop Override")
            col_o1, col_o2 = st.columns([1, 2])
            with col_o1:
                new_score = st.number_input(
                    "New Score (0-100)", min_value=0.0, max_value=100.0,
                    value=float(r["final_score"]), step=1.0, key=f"score_{idx}"
                )
            with col_o2:
                override_reason = st.text_input(
                    "Reason for override", key=f"reason_{idx}",
                    placeholder="E.g. Strong cultural fit after interview"
                )

            if st.button("Apply Override", key=f"btn_{idx}"):
                if not override_reason:
                    st.error("Please provide a reason for the override.")
                else:
                    try:
                        override_res = requests.post(
                            f"{API_BASE_URL}/override_score",
                            params={
                                "candidate_id": r["candidate_id"],
                                "new_score": new_score,
                                "reason": override_reason
                            }
                        )
                        if override_res.status_code == 200:
                            st.success(f"Override recorded! {r['candidate_name']}'s score changed to {new_score}.")
                        else:
                            st.error("Failed to record override.")
                    except Exception as e:
                        st.error(f"API Error: {e}")
