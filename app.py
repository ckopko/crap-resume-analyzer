import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai # NEW
from crap_analyzer.parser import extract_text_from_pdf
# --- UPDATED: Import the new AI function ---
from crap_analyzer.analyzer import split_text_into_chunks, get_embeddings, calculate_similarity_matrix, generate_feedback

# --- NEW: Configure the Gemini API Key from secrets ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error("Error configuring the Google API. Did you set up your secrets.toml file?")


st.set_page_config(page_title="C.R.A.P.", layout="wide")

# --- Header ---
st.title("Candidate Review & Analysis Protocol (C.R.A.P.) 💩")
st.subheader("Stop throwing your resume into the abyss. Get some real feedback.")

# --- Sidebar for Inputs ---
st.sidebar.header("Your Documents")
uploaded_resume = st.sidebar.file_uploader("Upload Your Resume (PDF)", type=["pdf"])
jd_text = st.sidebar.text_area("Paste the Job Description Here")
analyze_button = st.sidebar.button("Run the C.R.A.P. Analysis", type="primary")

# Main analysis logic
if analyze_button:
    if uploaded_resume is not None and jd_text:
        # --- Step 1: Parsing ---
        st.subheader("Step 1: C.R.A.P. Ingestion Report")
        with st.expander("See the raw text extracted from your resume"):
            resume_text = extract_text_from_pdf(uploaded_resume)
            st.text_area("Resume Text", resume_text, height=250, disabled=True)
        st.markdown("---")
        
        # --- Step 2: AI Analysis ---
        st.subheader("Step 2: AI Semantic Analysis")
        with st.spinner("The AI is 'reading' your documents..."):
            resume_chunks = split_text_into_chunks(resume_text)
            jd_chunks = split_text_into_chunks(jd_text)
            resume_embeddings = get_embeddings(resume_chunks)
            jd_embeddings = get_embeddings(jd_chunks)
            similarity_matrix = calculate_similarity_matrix(resume_embeddings, jd_embeddings)
            
            matches = []
            for i in range(len(resume_chunks)):
                best_match_score = similarity_matrix[i].max().item()
                best_match_index = similarity_matrix[i].argmax().item()
                matches.append({
                    "Resume Section": resume_chunks[i],
                    "Most Relevant JD Section": jd_chunks[best_match_index],
                    "Match Score": f"{best_match_score:.2f}"
                })
            match_df = pd.DataFrame(matches)

        st.info("The AI compares the *meaning* of each section of your resume to the job description.")
        st.dataframe(match_df, use_container_width=True, hide_index=True)
        st.markdown("---")
        
        # --- Step 3: Final Score ---
        st.subheader("Step 3: Final C.R.A.P. Rating")
        average_score = np.mean([float(match["Match Score"]) for match in matches])
        match_percentage = int(average_score * 100)
        st.metric(label="Overall Match Score", value=f"{match_percentage}%")
        st.progress(average_score)
        st.markdown("---")
        
        # --- NEW: Step 4: Generative Feedback ---
        st.subheader("Step 4: AI Coach Feedback")
        with st.spinner("Your AI Coach is formulating some advice..."):
            feedback = generate_feedback(match_df)
            st.markdown(feedback)
        # --- END NEW ---
    else:
        st.error("Please provide a resume and a job description to analyze.")