import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
from sentence_transformers import SentenceTransformer, util
from .schemas import ParsedResume # Import from the same directory

# --- Configure the Gemini client and define models ---
# This block correctly loads your key from secrets.toml
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except (KeyError, Exception):
    st.error("🚨 Gemini API key not found in secrets.toml.", icon="🔥")
    st.stop()

# Define our models once at the top
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
generative_model = genai.GenerativeModel('gemini-1.5-pro-latest') # Updated model name

# --- All of your original, powerful functions remain ---

@st.cache_data
def extract_skills_from_text(text: str):
    """Uses the generative model to extract a list of skills."""
    prompt = f"""
    You are an expert in parsing job descriptions and resumes.
    Your task is to meticulously extract every distinct skill, qualification, technology, and certification from the provided text.
    Return a clean, JSON-formatted list of unique skills.

    Text to Analyze:
    "{text}"

    JSON Skill List:
    """
    try:
        response = generative_model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        skill_list = json.loads(cleaned_response)
        return sorted(list(set([skill.lower() for skill in skill_list])))
    except Exception as e:
        print(f"Error extracting skills: {e}")
        return []

@st.cache_data
def analyze_skills_alignment(resume_skills: list, jd_skills: list, threshold=0.65):
    """Analyzes skill alignment using semantic similarity scores."""
    if not resume_skills or not jd_skills:
        return {"matched_skills": [], "missing_skills": jd_skills, "unique_skills": resume_skills}

    resume_embeddings = embedding_model.encode(resume_skills, convert_to_tensor=True)
    jd_embeddings = embedding_model.encode(jd_skills, convert_to_tensor=True)
    
    similarity_matrix = util.cos_sim(resume_embeddings, jd_embeddings)

    missing_skills = []
    jd_matched_indices = set()
    for jd_idx, jd_skill in enumerate(jd_skills):
        best_match_score = similarity_matrix[:, jd_idx].max().item()
        if best_match_score < threshold:
            missing_skills.append(jd_skill)
        else:
            jd_matched_indices.add(jd_idx)

    matched_skills = []
    unique_skills = []
    for resume_idx, resume_skill in enumerate(resume_skills):
        best_match_score = similarity_matrix[resume_idx].max().item()
        if best_match_score >= threshold:
            jd_idx = similarity_matrix[resume_idx].argmax().item()
            if jd_idx in jd_matched_indices:
                 matched_skills.append({
                    "Your Skill": resume_skill.title(),
                    "Required Skill": jd_skills[jd_idx].title()
                })
            else:
                 unique_skills.append(resume_skill)
        else:
            unique_skills.append(resume_skill)

    return {
        "matched_skills": matched_skills,
        "missing_skills": sorted(list(set(missing_skills))),
        "unique_skills": sorted(list(set(unique_skills)))
    }


@st.cache_data
def filter_relevant_skills(unique_skills: list, jd_text: str):
    """Evaluates unique skills and returns only those professionally relevant to the job."""
    if not unique_skills:
        return []
        
    prompt = f"""
    You are an expert career coach. A candidate has the following unique skills that are NOT explicitly required by the job description: {unique_skills}.
    The job description context is: "{jd_text[:1500]}"

    Your task is to identify which of these unique skills are still professionally relevant as transferable skills for this role.
    Filter out skills that are irrelevant. For a Nursing role, a unique skill like 'Project Management' is relevant, but 'AS400 System' is not.
    Return a clean, JSON-formatted list of only the professionally RELEVANT skills.
    """
    try:
        response = generative_model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Error filtering unique skills: {e}")
        return []

@st.cache_data
def generate_final_summary(analysis_result: dict, match_percentage: float):
    """Generates a detailed, multi-part summary with a tone adapted to the match score."""
    matched_text = ", ".join([match['Your Skill'] for match in analysis_result.get("matched_skills", [])])
    missing_text = ", ".join([skill.title() for skill in analysis_result.get("missing_skills", [])])
    unique_text = ", ".join([skill.title() for skill in analysis_result.get("relevant_unique_skills", [])])

    tone_instruction = ""
    if match_percentage < 0.4:
        tone_instruction = "Your tone should be realistic and direct. Acknowledge this is a poor match. State clearly that substantial work is needed."
    elif match_percentage < 0.7:
        tone_instruction = "Your tone should be encouraging but realistic. Acknowledge the foundational skills, but be clear about the specific gaps."
    else:
        tone_instruction = "Your tone should be very positive and congratulatory. Focus on leveraging their strong alignment."

    prompt = f"""
    You are an expert career coach. Generate a comprehensive coaching report in Markdown.

    Data:
    - MATCH SCORE: {match_percentage:.0%}
    - MATCHED SKILLS: {matched_text or "None"}
    - MISSING SKILLS: {missing_text or "None"}
    - RELEVANT UNIQUE SKILLS: {unique_text or "None"}

    **Tone:** {tone_instruction}

    Generate the report with these sections:

    ### Overall Summary
    Write a concise summary based on your assigned tone.

    ### Action Plan for Missing Skills
    For the top 3 most critical missing skills, create a bulleted list with the skill, a realistic time to acquire it, and a suggestion for how.

    ### Leveraging Your Unique Strengths
    Provide 2-3 pointers on how to strategically mention the 'RELEVANT UNIQUE SKILLS' in an interview.
    """
    try:
        response = generative_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating summary: {e}"

@st.cache_data
def generate_tailored_resume(original_resume_text: str, jd_text: str, user_clarifications: dict):
    """Generates a new, tailored resume based on user feedback."""
    clarifications_text = "\n".join([f"- {skill}: {details}" for skill, details in user_clarifications.items()])
    prompt = f"""
    You are an expert resume writer. Rewrite and enhance the original resume based on the job description and user clarifications.

    **1. Original Resume:**
    ---
    {original_resume_text}
    ---
    **2. Target Job Description:**
    ---
    {jd_text}
    ---
    **3. User Clarifications on Missing Skills:**
    ---
    {clarifications_text}
    ---
    **Instructions:**
    - Rewrite the original resume, preserving personal identifying information.
    - For each clarification, create a SINGLE, strong bullet point and add it to the most relevant work experience entry.
    - Emphasize relevant skills and de-emphasize irrelevant ones.
    - Return only the full text of the new resume.
    """
    try:
        response = generative_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating the new resume: {e}"