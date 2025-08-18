import streamlit as st
import pandas as pd
from crap_analyzer.parser import extract_text_from_pdf
from crap_analyzer.analyzer import extract_skills_from_text, analyze_skills_alignment, generate_final_summary

st.set_page_config(page_title="C.R.A.P.", layout="wide")

# --- Header ---
st.title("Candidate Review & Analysis Protocol (C.R.A.P.) 💩")
st.subheader("A skills-first approach to resume and job description alignment.")

# --- Sidebar for Inputs ---
st.sidebar.header("Your Documents")
uploaded_resume = st.sidebar.file_uploader("Upload Your Resume (PDF)", type=["pdf"])
jd_text = st.sidebar.text_area("Paste the Job Description Here")
analyze_button = st.sidebar.button("Run the C.R.A.P. Analysis", type="primary")

# Main analysis logic
if analyze_button:
    if uploaded_resume is not None and jd_text:
        # --- 1. Extraction Phase ---
        with st.spinner("Step 1/3: Extracting skills from documents..."):
            resume_text = extract_text_from_pdf(uploaded_resume)
            resume_skills = extract_skills_from_text(resume_text)
            jd_skills = extract_skills_from_text(jd_text)

        # --- 2. Analysis Phase ---
        with st.spinner("Step 2/3: Analyzing skills alignment..."):
            matched, resume_only, missing = analyze_skills_alignment(resume_skills, jd_skills)

        # --- 3. Reporting Phase ---
        st.header("🔬 C.R.A.P. Analysis Report")

        # --- Overall Score ---
        if jd_skills:
            # Calculate the percentage of required skills that are matched
            match_percentage = len(matched) / len(jd_skills) if jd_skills else 0
        else:
            match_percentage = 0
        
        st.metric(label="Overall Skill Alignment with Job Description", value=f"{match_percentage:.0%}")
        st.progress(match_percentage)
        st.markdown("---")

        # --- Create Columns for the Report ---
        col1, col2, col3 = st.columns(3)

        with col1:
            st.success("✅ Matched Skills")
            if matched:
                match_df = pd.DataFrame(matched)
                match_df.rename(columns={'resume_skill': 'Your Skill', 'jd_skill': 'Required Skill', 'score': 'Similarity'}, inplace=True)
                st.dataframe(match_df, use_container_width=True, hide_index=True)
            else:
                st.write("No strong skill matches found.")

        with col2:
            st.warning("❌ Missing Key Skills")
            if missing:
                missing_df = pd.DataFrame({'Skill Required by Job': [skill.title() for skill in missing]})
                st.dataframe(missing_df, use_container_width=True, hide_index=True)
            else:
                st.write("Great news! You don't appear to be missing any key skills.")
        
        with col3:
            st.info("💡 Your Unique Skills")
            st.write("(Skills you have that are not listed in the job description)")
            if resume_only:
                resume_only_df = pd.DataFrame({'Your Skill': [skill.title() for skill in resume_only]})
                st.dataframe(resume_only_df, use_container_width=True, hide_index=True)
            else:
                st.write("No unique skills identified.")

        st.markdown("---")

        # --- 4. Final Summary ---
        with st.spinner("Step 3/3: Generating AI Coach Summary..."):
            st.header("🧑‍🏫 AI Coach Summary")
            final_summary = generate_final_summary(matched, missing)
            st.markdown(final_summary)

    else:
        st.error("Please provide a resume and a job description to analyze.")