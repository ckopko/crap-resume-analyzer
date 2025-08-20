import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
from sentence_transformers import SentenceTransformer, util

# --- Define our models once at the top ---
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
# --- UPDATED: Using the gemini-2.5-pro model ---
generative_model = genai.GenerativeModel('gemini-2.5-pro')

@st.cache_data
def extract_skills_from_text(text: str):
    """Uses the generative model to extract a list of skills."""
    prompt = f"""
    You are an expert in parsing job descriptions across ALL industries.
    Your task is to meticulously extract every distinct skill, qualification, certification, and required experience from the provided text.
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
    for i in range(len(jd_skills)):
        best_resume_match_score = similarity_matrix[:, i].max().item()
        if best_resume_match_score < threshold:
            missing_skills.append(jd_skills[i])

    matched_skills = []
    matched_jd_indices = set()
    for i in range(len(resume_skills)):
        best_jd_match_score = similarity_matrix[i].max().item()
        if best_jd_match_score >= threshold:
            jd_index = similarity_matrix[i].argmax().item()
            if jd_index not in matched_jd_indices:
                matched_skills.append({
                    "Your Skill": resume_skills[i].title(),
                    "Required Skill": jd_skills[jd_index].title()
                })
                matched_jd_indices.add(jd_index)
    
    matched_resume_skills = {match['Your Skill'].lower() for match in matched_skills}
    unique_skills = [skill for skill in resume_skills if skill.lower() not in matched_resume_skills]

    return {
        "matched_skills": matched_skills,
        "missing_skills": sorted(missing_skills),
        "unique_skills": sorted(unique_skills)
    }

@st.cache_data
def filter_relevant_skills(unique_skills: list, jd_text: str):
    """Evaluates unique skills and returns only those professionally relevant to the job."""
    if not unique_skills:
        return []
        
    prompt = f"""
    You are an expert career coach and hiring manager. A candidate has the following unique skills that are NOT explicitly required by the job description: {unique_skills}.
    The job description context is as follows: "{jd_text[:1500]}"

    Your task is to identify which of these unique skills are still professionally relevant and valuable as transferable skills for this type of role.
    Filter out skills that are completely irrelevant. For example, for a Nursing role, a unique skill like 'Project Management' could be relevant for a charge nurse, but 'AS400 System' is not. For an analyst role, 'Public Speaking' is relevant, but 'Baking Bread' is not.
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
        tone_instruction = "Your tone should be realistic and direct. Acknowledge that this is a poor match or a significant career pivot. DO NOT congratulate the user on their foundation. State clearly that substantial work is needed to bridge the gap."
    elif match_percentage < 0.7:
        tone_instruction = "Your tone should be encouraging but realistic. Acknowledge the foundational skills the user has, but be clear about the specific gaps that need to be addressed to become a strong candidate."
    else:
        tone_instruction = "Your tone should be very positive and congratulatory. Focus on how the user can leverage their strong alignment to secure an interview."

    prompt = f"""
    You are an expert, realistic, and strategic career coach. Your task is to generate a comprehensive, multi-section coaching report in Markdown format.

    Here is the data for your analysis:
    - OVERALL MATCH SCORE: {match_percentage:.0%}
    - MATCHED SKILLS: {matched_text if matched_text else "None"}
    - MISSING SKILLS: {missing_text if missing_text else "None"}
    - RELEVANT UNIQUE SKILLS: {unique_text if unique_text else "None"}

    **Your Tone:** {tone_instruction}

    Please generate the report with the following sections:

    ### Overall Summary
    Based on your assigned tone, write a concise, two-paragraph summary. Address the overall alignment and the most critical gap or strength.

    ### Action Plan for Missing Skills
    Analyze the 'MISSING SKILLS' list. For the top 3 most critical missing skills or qualifications, create a bulleted list. Each bullet must include the skill, a realistic estimated time to acquire it, and a brief suggestion for how to acquire it.

    ### Leveraging Your Unique Strengths
    Analyze the 'RELEVANT UNIQUE SKILLS' list. Provide a bulleted list of 2-3 pointers on how the candidate can strategically mention these skills in an interview to stand out.
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
    You are an expert professional resume writer with a talent for tailoring documents to specific job descriptions.
    Your task is to rewrite and enhance an original resume based on a job description and specific clarifications provided by the user about their skills.

    **1. The User's Original Resume:**
    ---
    {original_resume_text}
    ---

    **2. The Target Job Description:**
    ---
    {jd_text}
    ---

    **3. User's Clarifications on Missing Skills:**
    (This is new information you must integrate into the new resume)
    ---
    {clarifications_text}
    ---

    **Instructions:**
    - Rewrite the original resume. Do not just summarize.
    - **Crucially, ensure any personal identifying information from the original resume, such as the person's name, email, and phone number, is preserved and present in the new version.**
    - Maintain a professional tone and the overall structure (Summary, Experience, Skills, etc.).
    - For each user clarification, create a SINGLE, strong bullet point. Find the most relevant work experience entry in the original resume and add this new bullet point there. DO NOT add these clarified skills to the general 'Skills' section unless they were already present.
    - Emphasize skills and experiences from the original resume that are highly relevant to the job description.
    - De-emphasize or remove experiences from the original resume that are not relevant to the job description.
    - Return only the full text of the newly written, tailored resume. Do not include any of your own commentary before or after the resume text.
    """
    try:
        response = generative_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating the new resume: {e}"
