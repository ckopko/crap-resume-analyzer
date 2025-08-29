import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
from sentence_transformers import SentenceTransformer, util
from .schemas import ParsedResume # Import from the same directory

# --- Configure the Gemini client and define models ---
import os

try:
    # Try to get from environment variable first (for Render)
    api_key = os.getenv("GOOGLE_API_KEY")
    
    # If not found, try Streamlit secrets (for local development)
    if not api_key:
        api_key = st.secrets["GOOGLE_API_KEY"]
    
    genai.configure(api_key=api_key)
except (KeyError, Exception):
    st.error("🚨 Gemini API key not found. Please set GOOGLE_API_KEY environment variable or add to secrets.toml.", icon="🔥")
    st.stop()

# Define our models once at the top
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
generative_model = genai.GenerativeModel('gemini-1.5-pro-latest')

# --- Enhanced extraction with categorization ---

@st.cache_data
def extract_and_categorize_requirements(text: str, is_job_description: bool = True):
    """
    Extracts requirements/skills and categorizes them using AI.
    Returns a structured dictionary with categories.
    """
    doc_type = "job description" if is_job_description else "resume"
    
    prompt = f"""
    You are an expert in analyzing {doc_type}s. Extract and categorize ALL requirements, skills, and qualifications.

    Text to analyze:
    "{text}"

    Categorize everything into these 4 categories:

    1. **Education & Certifications**: Degrees, certifications, licenses, specific coursework
    2. **Professional Skills**: Job-specific hard skills, tools, software, methodologies, technical knowledge
    3. **Soft Skills**: Communication, leadership, teamwork, problem-solving, interpersonal abilities
    4. **Experience**: Years of experience, industry background, role levels, specific experience types

    Return a clean JSON object with this structure:
    {{
        "education_certifications": ["Bachelor's degree", "PMP certification"],
        "professional_skills": ["SQL", "Python", "Project management"],
        "soft_skills": ["Leadership", "Communication", "Problem solving"],
        "experience": ["3+ years experience", "Healthcare industry", "Team lead experience"]
    }}

    Be thorough and extract everything, even if implied.
    """
    
    try:
        response = generative_model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        categorized_data = json.loads(cleaned_response)
        
        # Normalize to lowercase for consistency
        for category in categorized_data:
            categorized_data[category] = [item.lower() for item in categorized_data[category]]
        
        return categorized_data
    except Exception as e:
        print(f"Error extracting and categorizing: {e}")
        return {
            "education_certifications": [],
            "professional_skills": [],
            "soft_skills": [],
            "experience": []
        }

@st.cache_data
def analyze_categorized_alignment(resume_categories: dict, jd_categories: dict, threshold=0.65):
    """
    Analyzes alignment between resume and JD across all categories using semantic similarity.
    """
    results = {}
    
    for category in ["education_certifications", "professional_skills", "soft_skills", "experience"]:
        resume_items = resume_categories.get(category, [])
        jd_items = jd_categories.get(category, [])
        
        if not resume_items or not jd_items:
            results[category] = {
                "matched": [],
                "missing": jd_items,
                "unique": resume_items,
                "match_percentage": 0.0
            }
            continue
        
        # Get embeddings
        resume_embeddings = embedding_model.encode(resume_items, convert_to_tensor=True)
        jd_embeddings = embedding_model.encode(jd_items, convert_to_tensor=True)
        
        # Calculate similarity matrix
        similarity_matrix = util.cos_sim(resume_embeddings, jd_embeddings)
        
        # Find matches and missing items
        missing_items = []
        matched_jd_indices = set()
        
        for jd_idx, jd_item in enumerate(jd_items):
            best_match_score = similarity_matrix[:, jd_idx].max().item()
            if best_match_score < threshold:
                missing_items.append(jd_item)
            else:
                matched_jd_indices.add(jd_idx)
        
        # Find matched and unique resume items
        matched_items = []
        unique_items = []
        
        for resume_idx, resume_item in enumerate(resume_items):
            best_match_score = similarity_matrix[resume_idx].max().item()
            if best_match_score >= threshold:
                jd_idx = similarity_matrix[resume_idx].argmax().item()
                if jd_idx in matched_jd_indices:
                    matched_items.append({
                        "resume_item": resume_item.title(),
                        "jd_item": jd_items[jd_idx].title(),
                        "similarity": best_match_score
                    })
                else:
                    unique_items.append(resume_item)
            else:
                unique_items.append(resume_item)
        
        # Calculate match percentage
        match_percentage = (len(jd_items) - len(missing_items)) / len(jd_items) if jd_items else 0
        
        results[category] = {
            "matched": matched_items,
            "missing": sorted(list(set(missing_items))),
            "unique": sorted(list(set(unique_items))),
            "match_percentage": max(0, match_percentage)
        }
    
    return results

@st.cache_data
def get_category_insights(analysis_results: dict, jd_text: str):
    """
    Generates AI-powered insights for each category with specific, actionable recommendations.
    """
    insights = {}
    
    for category, data in analysis_results.items():
        match_pct = data["match_percentage"]
        missing_count = len(data["missing"])
        matched_count = len(data["matched"])
        
        category_name = category.replace("_", " ").title()
        
        prompt = f"""
        You are an expert career coach analyzing a candidate's {category_name} alignment with a job.

        Analysis Data:
        - Match Percentage: {match_pct:.0%}
        - Matched Items: {matched_count}
        - Missing Items: {missing_count}
        - Missing: {', '.join(data['missing'][:5])}
        - Matched: {[m['resume_item'] for m in data['matched'][:3]]}

        Job Context: {jd_text[:500]}

        Provide a brief, actionable insight (2-3 sentences max) with specific next steps.
        Focus on what the candidate should DO, not just what they're missing.
        
        Format: Return just the insight text, no extra formatting.
        """
        
        try:
            response = generative_model.generate_content(prompt)
            insights[category] = response.text.strip()
        except Exception as e:
            insights[category] = f"Unable to generate insights for {category_name}"
    
    return insights

@st.cache_data  
def generate_targeted_improvements(original_resume_text: str, jd_text: str, analysis_results: dict, user_clarifications: dict = None):
    """
    Generates specific, targeted improvements rather than a full resume rewrite.
    Returns actionable editing instructions.
    
    Args:
        original_resume_text: The user's original resume text
        jd_text: The job description text
        analysis_results: Results from analyze_categorized_alignment()
        user_clarifications: Dict of skills the user clarified they have
    """
    
    # Find the most critical gaps across all categories (excluding clarified skills)
    critical_gaps = []
    clarified_skills = set()
    
    # Collect all clarified skills across categories
    if user_clarifications:
        for category_clarifications in user_clarifications.values():
            clarified_skills.update(category_clarifications.keys())
    
    for category, data in analysis_results.items():
        if data["missing"] and data["match_percentage"] < 0.7:
            # Only include gaps that weren't clarified by the user
            unclarified_gaps = [skill for skill in data["missing"] if skill not in clarified_skills]
            critical_gaps.extend(unclarified_gaps[:2])  # Top 2 missing items per weak category
    
    # Include user clarifications in the prompt context
    clarifications_context = ""
    if user_clarifications:
        clarifications_text = []
        for category, skills in user_clarifications.items():
            category_name = category.replace("_", " ").title()
            for skill, experience in skills.items():
                clarifications_text.append(f"- {skill} ({category_name}): {experience}")
        
        if clarifications_text:
            clarifications_context = f"""
            
    User has clarified they possess these skills (incorporate these into recommendations):
    {chr(10).join(clarifications_text)}
    """
    
    prompt = f"""
    You are an expert resume editor. Analyze this resume and provide specific, actionable editing instructions.

    Original Resume:
    ---
    {original_resume_text[:1500]}
    ---
    
    Target Job:
    ---
    {jd_text[:1000]}
    ---
    
    Critical Gaps to Address: {', '.join(critical_gaps[:5])}
    {clarifications_context}

    Provide 5 specific editing instructions. Return ONLY valid JSON with no extra text or formatting:

    {{
        "improvements": [
            {{
                "type": "add_bullet",
                "section": "Experience Section",
                "instruction": "Add bullet about data visualization experience",
                "suggested_text": "Created interactive dashboards using Tableau",
                "reason": "Addresses missing Tableau requirement"
            }},
            {{
                "type": "emphasize",
                "section": "Skills Section", 
                "instruction": "Move SQL to top of technical skills list",
                "reason": "SQL is heavily emphasized in job description"
            }}
        ]
    }}

    CRITICAL: 
    - Return only the JSON object, no extra text
    - Escape all quotes properly in strings
    - Keep suggested_text short and simple
    - Avoid complex punctuation in JSON strings
    - If user clarified skills, suggest ways to better highlight those existing skills rather than adding them
    """
    
    try:
        response = generative_model.generate_content(prompt)
        cleaned_response = response.text.strip()
        
        # More aggressive cleaning
        cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
        
        # Find JSON object boundaries
        start_idx = cleaned_response.find('{')
        end_idx = cleaned_response.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = cleaned_response[start_idx:end_idx]
        else:
            json_str = cleaned_response
            
        parsed_json = json.loads(json_str)
        
        # Validate structure
        if "improvements" not in parsed_json or not isinstance(parsed_json["improvements"], list):
            raise ValueError("Invalid JSON structure")
            
        return parsed_json
        
    except json.JSONDecodeError as je:
        print(f"JSON decode error: {je}")
        # Fallback to simple improvements
        return generate_simple_improvements(critical_gaps)
    except Exception as e:
        print(f"General error: {e}")
        return generate_simple_improvements(critical_gaps)

def generate_simple_improvements(critical_gaps: list):
    """
    Fallback function that generates simple improvements without AI when JSON parsing fails.
    """
    improvements = []
    
    for i, gap in enumerate(critical_gaps[:5]):
        improvements.append({
            "type": "add_skill",
            "section": "Skills or Experience",
            "instruction": f"Add evidence of '{gap.title()}' experience to your resume",
            "suggested_text": f"Include specific examples where you used {gap.title()}",
            "reason": f"This skill was required in the job description but missing from your resume"
        })
    
    if not improvements:
        improvements = [{
            "type": "general",
            "section": "Overall Resume",
            "instruction": "Review your resume to better highlight relevant experience",
            "suggested_text": "Use keywords from the job description throughout your resume",
            "reason": "Improve alignment with job requirements"
        }]
    
    return {"improvements": improvements}

# Keep existing functions for backward compatibility, but mark as deprecated
@st.cache_data
def extract_skills_from_text(text: str):
    """DEPRECATED: Use extract_and_categorize_requirements instead"""
    return extract_and_categorize_requirements(text, is_job_description=True)

@st.cache_data 
def analyze_skills_alignment(resume_skills, jd_skills, threshold=0.65):
    """DEPRECATED: Use analyze_categorized_alignment instead"""
    # Convert old format to new format for backward compatibility
    if isinstance(resume_skills, list):
        resume_skills = {"professional_skills": resume_skills}
    if isinstance(jd_skills, list):  
        jd_skills = {"professional_skills": jd_skills}
    
    results = analyze_categorized_alignment(resume_skills, jd_skills, threshold)
    
    # Return in old format for backward compatibility
    prof_results = results.get("professional_skills", {})
    return {
        "matched_skills": prof_results.get("matched", []),
        "missing_skills": prof_results.get("missing", []),
        "unique_skills": prof_results.get("unique", [])
    }