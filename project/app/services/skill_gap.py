"""
skill_gap.py — HireU Skill Gap Analysis Service

This module provides:
- compute_skill_gap(): Compares JD skills vs candidate skills and returns
  matched/missing skills with a compatibility percentage.
- generate_ai_hiring_insight(): Uses Gemini to produce a recruiter-style
  natural language summary of the candidate's fit.
- get_hire_threshold_label(): Maps a skill match % to a recommendation label.
"""

from typing import List, Dict, Any
from app.models.candidate import Candidate
from app.models.jd import JobDescription
from app.services.semantic_matcher import match_skills
from app.utils.config import settings


# ---------------------------------------------------------------------------
# Threshold Mapping
# ---------------------------------------------------------------------------

def get_hire_threshold_label(match_percentage: float) -> str:
    """
    Maps a skill match percentage to a hiring recommendation label.

    Thresholds:
        85%+   → Strong Hire
        70–84% → Hire
        50–69% → Consider
        <50%   → Reject
    """
    if match_percentage >= 85:
        return "Strong Hire"
    elif match_percentage >= 70:
        return "Hire"
    elif match_percentage >= 50:
        return "Consider"
    else:
        return "Reject"


# ---------------------------------------------------------------------------
# Skill Gap Computation
# ---------------------------------------------------------------------------

def compute_skill_gap(jd: JobDescription, candidate: Candidate) -> Dict[str, Any]:
    """
    Computes the skill gap between a Job Description and a Candidate.

    Steps:
    1. Normalize all skills (lowercase + strip whitespace) for fair comparison.
    2. Combine JD required + preferred skills into a single list.
    3. Call the existing semantic match_skills() engine (cosine similarity).
    4. Return a structured dict with matched skills, missing skills,
       full skill lists, match %, and threshold label.

    Returns:
        {
            "match_percentage": float,
            "threshold_label": str,
            "matched": [{"jd_skill": str, "candidate_skill": str, "score": float}],
            "missing": [str],
            "jd_skills": [str],
            "candidate_skills": [str]
        }
    """
    # Normalize: lowercase + strip to reduce false mismatches
    jd_skills = [s.lower().strip() for s in (jd.required_skills + jd.preferred_skills) if s]
    candidate_skills = [s.lower().strip() for s in candidate.skills if s]

    # Use the existing semantic matcher to get matched/missing/percentage
    match_result = match_skills(jd_skills, candidate_skills)

    threshold_label = get_hire_threshold_label(match_result["match_percentage"])

    return {
        "match_percentage": round(match_result["match_percentage"], 1),
        "threshold_label": threshold_label,
        "matched": match_result["matched"],
        "missing": match_result["missing"],
        "jd_skills": jd_skills,
        "candidate_skills": candidate_skills,
    }


# ---------------------------------------------------------------------------
# AI Hiring Insight Generation
# ---------------------------------------------------------------------------

def generate_ai_hiring_insight(
    jd: JobDescription,
    candidate: Candidate,
    skill_gap_result: Dict[str, Any],
) -> str:
    """
    Generates a concise recruiter-style hiring insight using Gemini.

    The insight includes:
    - Candidate's key strengths relative to the JD.
    - Most critical missing skills the candidate lacks.
    - An overall hiring recommendation.
    - A clear yes/no decision on whether to proceed to interview.

    Args:
        jd: The parsed Job Description.
        candidate: The parsed Candidate profile.
        skill_gap_result: Output of compute_skill_gap().

    Returns:
        A 3–5 sentence natural language string formatted for a recruiter.
    """
    if not settings.GOOGLE_API_KEY:
        return "AI Insight unavailable: GOOGLE_API_KEY is not set."

    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.3,  # Slight creativity for natural phrasing
    )

    matched_skills = [m["jd_skill"] for m in skill_gap_result.get("matched", [])]
    missing_skills = skill_gap_result.get("missing", [])
    match_pct = skill_gap_result.get("match_percentage", 0)
    threshold = skill_gap_result.get("threshold_label", "Unknown")

    prompt = f"""
You are a senior HR recruiter writing a concise hiring assessment for a colleague.

Job Role: {jd.role}
Candidate Name: {candidate.name}
Skill Match: {match_pct}% ({threshold})
Matched Skills: {', '.join(matched_skills) if matched_skills else 'None'}
Missing Skills: {', '.join(missing_skills) if missing_skills else 'None'}
Total Experience: {candidate.total_experience_years} years
Education: {[e.degree for e in candidate.education]}

Write a 3–5 sentence recruiter-style summary covering:
1. The candidate's key strengths for this role.
2. The most important skills they are missing.
3. An overall hiring recommendation ({threshold}).
4. A clear final statement: should they proceed to interview? Yes or No, and why.

Keep it professional, direct, and actionable. Do NOT use bullet points — write in flowing prose.
"""

    response = llm.invoke(prompt)
    # Extract string content from LangChain message object
    return response.content.strip()
