from sentence_transformers import SentenceTransformer, util
import numpy as np
import google.generativeai as genai
import pandas as pd

# This line downloads a pre-trained model to your computer the first time you run it.
model = SentenceTransformer('all-MiniLM-L6-v2')

# --- THIS FUNCTION WAS LIKELY MISSING ---
def split_text_into_chunks(text, chunk_size=256, overlap=32):
    """Splits text into smaller, overlapping chunks for more granular comparison."""
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size - overlap)]

def get_embeddings(text_chunks):
    """Converts a list of text chunks into a list of numerical vectors."""
    return model.encode(text_chunks, convert_to_tensor=True)

def calculate_similarity_matrix(resume_embeddings, jd_embeddings):
    """Calculates the cosine similarity between all resume and JD chunks."""
    return util.cos_sim(resume_embeddings, jd_embeddings)

def generate_feedback(analysis_df: pd.DataFrame):
    """Asks a generative AI for feedback based on the analysis."""

    # Convert the DataFrame to a more readable format for the AI
    analysis_text = ""
    for index, row in analysis_df.iterrows():
        analysis_text += f"- Resume Section: \"{row['Resume Section']}\"\n"
        analysis_text += f"  - Best JD Match: \"{row['Most Relevant JD Section']}\"\n"
        analysis_text += f"  - Match Score: {row['Match Score']}\n\n"

    # Set up the generative model
    model = genai.GenerativeModel('gemini-1.5-pro-latest')

    # This is the prompt that instructs the AI
    prompt = f"""
    You are an expert career coach and resume writer reviewing a candidate's resume against a job description.
    Based on the following semantic analysis data, provide actionable feedback. The data shows sections from a candidate's resume and the corresponding best-matching section from the job description, along with a match score (0.0 to 1.0).

    Analysis Data:
    {analysis_text}

    Your Task:
    1.  Start with a one-sentence summary of the overall alignment (good, average, poor).
    2.  Identify the top 2-3 strengths where the resume strongly aligns with the job description (high match scores).
    3.  Identify the most significant 2-3 gaps or weaknesses where the resume is poorly aligned (low match scores).
    4.  Provide a bulleted list of 3-5 specific, actionable suggestions for the candidate to improve their resume for this specific job. For example, "Consider adding a project that demonstrates your experience with 'data visualization', as this is a key requirement in the job description." or "Rephrase your experience with 'team collaboration' to use keywords like 'agile' and 'scrum' mentioned in the job description."

    Please format your response using markdown.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error communicating with the AI model: {e}"