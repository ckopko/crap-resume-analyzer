from sentence_transformers import SentenceTransformer, util
import numpy as np
import google.generativeai as genai
import pandas as pd
import json

# --- The embedding model for comparing skills semantically ---
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# --- UPDATED: The generative model is now defined with the correct 2.5 Pro name ---
generative_model = genai.GenerativeModel('gemini-2.5-pro')

def extract_skills_from_text(text: str):
    """
    Uses the generative model to extract a list of skills from a text block.
    """
    prompt = f"""
    You are an expert technical recruiter and HR analyst. Your task is to extract all technical skills, soft skills, tools, and qualifications from the following text.
    Return a clean, JSON-formatted list of unique skills.

    Example Output: ["Python", "Data Analysis", "Team Leadership", "Project Management", "Agile Methodologies", "Tableau", "Microsoft Excel"]

    Text to Analyze:
    "{text}"

    JSON Skill List:
    """
    try:
        # Use the globally defined model
        response = generative_model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        skill_list = json.loads(cleaned_response)
        return sorted(list(set([skill.lower() for skill in skill_list])))
    except Exception as e:
        print(f"Error extracting skills: {e}")
        return []

def analyze_skills_alignment(resume_skills: list, jd_skills: list, threshold=0.70):
    """
    Analyzes the alignment between two lists of skills using semantic similarity.
    """
    if not resume_skills or not jd_skills:
        return [], [], list(jd_skills)

    resume_embeddings = embedding_model.encode(resume_skills, convert_to_tensor=True)
    jd_embeddings = embedding_model.encode(jd_skills, convert_to_tensor=True)

    similarity_matrix = util.cos_sim(resume_embeddings, jd_embeddings)

    matched_skills = []
    unmatched_resume_skills = set(resume_skills)
    unmatched_jd_skills = set(jd_skills)

    for i in range(len(resume_skills)):
        best_match_score = similarity_matrix[i].max().item()
        best_match_index = similarity_matrix[i].argmax().item()

        if best_match_score >= threshold:
            resume_skill = resume_skills[i]
            jd_skill = jd_skills[best_match_index]
            
            matched_skills.append({
                "resume_skill": resume_skill.title(),
                "jd_skill": jd_skill.title(),
                "score": f"{best_match_score:.2f}"
            })
            
            unmatched_resume_skills.discard(resume_skill)
            if jd_skill in unmatched_jd_skills:
                 unmatched_jd_skills.discard(jd_skill)

    return matched_skills, sorted(list(unmatched_resume_skills)), sorted(list(unmatched_jd_skills))

def generate_final_summary(matched_skills: list, missing_skills: list):
    """Generates a final summary and advice."""
    matched_text = ", ".join([match['resume_skill'] for match in matched_skills]) if matched_skills else "None"
    missing_text = ", ".join([skill.title() for skill in missing_skills]) if missing_skills else "None"

    prompt = f"""
    You are an expert career coach providing a final summary for a resume-to-job-description analysis.

    Here is the data:
    - Skills the candidate has that match the job: {matched_text}
    - Key skills the candidate is missing for the job: {missing_text}

    Your Task:
    Write a concise, encouraging, two-paragraph summary.
    1.  In the first paragraph, congratulate the user on their strengths, highlighting 2-3 of the most important matched skills.
    2.  In the second paragraph, identify the most critical skill gap from the missing skills list. Provide a specific, actionable suggestion on how they could address this gap (e.g., "To address the missing 'Cloud Deployment' skill, consider taking a short online course on AWS or Azure fundamentals and adding a small project to your portfolio.").
    """
    try:
        # Use the globally defined model
        response = generative_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating summary: {e}"