import streamlit as st
import pandas as pd
from crap_analyzer.parser import extract_text_from_pdf
from crap_analyzer.analyzer import (
    extract_skills_from_text,
    analyze_skills_alignment,
    filter_relevant_skills,
    generate_final_summary,
    generate_tailored_resume
)

st.set_page_config(page_title="Resume Doctor", layout="wide")

# --- Initialize Session State ---
# This is the app's "memory"
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "user_clarifications" not in st.session_state:
    st.session_state.user_clarifications = {}
if "jd_skills" not in st.session_state:
    st.session_state.jd_skills = []
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""
if "new_resume" in st.session_state and not st.session_state.analysis_complete:
    del st.session_state.new_resume
if "original_match_percentage" not in st.session_state:
    st.session_state.original_match_percentage = 0
if "new_match_percentage" not in st.session_state:
    st.session_state.new_match_percentage = None
if "new_analysis_results" not in st.session_state:
    st.session_state.new_analysis_results = None
if "tailoring_started" not in st.session_state:
    st.session_state.tailoring_started = False


# --- Header ---
st.title("Resume Doctor 🩺")
st.subheader("An intelligent, context-aware skill analysis for your job application.")

# --- Sidebar for Inputs ---
st.sidebar.header("Your Documents")

# --- Sample Data Loader ---
def load_sample_data():
    try:
        with open("sample_resume.txt", "r") as f:
            st.session_state.resume_text_from_sample = f.read()
        with open("sample_jd.txt", "r") as f:
            st.session_state.jd_text = f.read()
        st.session_state.analysis_complete = False
    except FileNotFoundError:
        st.sidebar.error("Sample files not found. Make sure 'sample_resume.txt' and 'sample_jd.txt' are in the root folder.")

st.sidebar.button("Load Sample Data 🧪", on_click=load_sample_data)
st.sidebar.markdown("---")

uploaded_resume = st.sidebar.file_uploader("Upload Your Resume (PDF)", type=["pdf"])
# --- FIXED: Removed the 'key' argument and now control the value manually ---
jd_text_input = st.sidebar.text_area("Paste the Job Description Here", height=250, value=st.session_state.jd_text)
st.session_state.jd_text = jd_text_input # Update state with user's typing

if st.sidebar.button("Run Analysis", type="primary"):
    resume_text_to_analyze = ""
    if uploaded_resume is not None:
        resume_text_to_analyze = extract_text_from_pdf(uploaded_resume)
    elif "resume_text_from_sample" in st.session_state and st.session_state.resume_text_from_sample:
        resume_text_to_analyze = st.session_state.resume_text_from_sample

    if resume_text_to_analyze and st.session_state.jd_text:
        with st.spinner("Running full analysis..."):
            # Reset state for a new run
            st.session_state.user_clarifications = {}
            st.session_state.tailoring_started = False
            st.session_state.new_match_percentage = None
            st.session_state.new_analysis_results = None
            if "new_resume" in st.session_state:
                del st.session_state.new_resume

            # Perform analysis
            st.session_state.resume_text = resume_text_to_analyze
            resume_skills = extract_skills_from_text(resume_text_to_analyze)
            jd_skills = extract_skills_from_text(st.session_state.jd_text)
            
            analysis = analyze_skills_alignment(resume_skills, jd_skills)
            
            # Save results to memory
            st.session_state.analysis_results = analysis
            st.session_state.jd_skills = jd_skills
            st.session_state.analysis_complete = True
            
    else:
        st.sidebar.error("Please provide both a resume and a job description.")

# --- Donation Section ---
st.sidebar.markdown("---")
st.sidebar.header("Support This Project")
st.sidebar.write("If you found this tool helpful, consider a small btc donation.")
# Replace with your actual QR code image URL or file path
st.sidebar.image("https://i.imgur.com/s9qF28O.png", width=150)


# --- Main App Display ---
if st.session_state.analysis_complete:
    analysis_data = st.session_state.analysis_results
    jd_skills = st.session_state.jd_skills
    matched = analysis_data.get("matched_skills", [])
    missing = analysis_data.get("missing_skills", [])
    unique = analysis_data.get("unique_skills", [])
    
    # --- 1. Display The Static Report ---
    st.header("🔬 Original Resume Analysis Report")
    
    score = (len(jd_skills) - len(missing)) / len(jd_skills) if jd_skills else 0
    st.session_state.original_match_percentage = max(0, score)
    
    st.metric(label="Overall Skill Alignment", value=f"{st.session_state.original_match_percentage:.0%}")
    st.progress(st.session_state.original_match_percentage)
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("✅ Matched Skills")
        if matched:
            st.dataframe(pd.DataFrame(matched), use_container_width=True, hide_index=True)
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
        with st.spinner("Filtering unique skills..."):
             relevant_unique_skills = filter_relevant_skills(unique, st.session_state.jd_text)
        st.info("💡 Your Relevant Unique Skills")
        if relevant_unique_skills:
            resume_only_df = pd.DataFrame({'Your Skill': [skill.title() for skill in relevant_unique_skills]})
            st.dataframe(resume_only_df, use_container_width=True, hide_index=True)
        else:
            st.write("No unique skills with professional relevance were identified.")

    st.markdown("---")

    # --- 2. Display the AI Coach Summary ---
    if not st.session_state.tailoring_started:
        st.header("🧑‍🏫 AI Coach Summary")
        with st.spinner("Generating initial summary..."):
            summary_analysis_data = {
                "matched_skills": matched,
                "missing_skills": missing,
                "relevant_unique_skills": relevant_unique_skills
            }
            final_summary = generate_final_summary(summary_analysis_data, st.session_state.original_match_percentage)
            st.markdown(final_summary)
        st.markdown("---")

    # --- 3. Conditionally Display Interactive Section or Button to Start It ---
    if not st.session_state.tailoring_started:
        if st.button("Start Interactive Resume Tailoring 📝", type="primary"):
            st.session_state.tailoring_started = True
            st.rerun()
    
    # --- 4. Display the Interactive Table ---
    if st.session_state.tailoring_started:
        st.header("📝 Interactive Tailoring Session")
        st.info("For any 'missing' skills you actually have, switch the toggle to 'Yes' and provide a brief example of your experience.")
        
        clarifications = {}
        if missing:
            for skill in missing:
                col_skill, col_toggle, col_exp = st.columns([0.3, 0.2, 0.5])
                with col_skill:
                    st.write(f"**{skill.title()}**")
                with col_toggle:
                    has_skill = st.radio("Do you have this skill?", ["Yes", "No"], index=1, key=f"radio_{skill}", horizontal=True, label_visibility="collapsed")
                with col_exp:
                    experience_details = st.text_input(
                        "Briefly describe your experience:", 
                        key=f"exp_{skill}", 
                        placeholder="e.g., Used CTEs to analyze user funnels...",
                        disabled=(has_skill == "No")
                    )
                    if has_skill == "Yes" and experience_details:
                        clarifications[skill] = experience_details
        else:
            st.success("No missing skills were identified to clarify!")

        if st.button("Generate Tailored Resume ✨", type="primary"):
            with st.spinner("Your new resume is being crafted by the AI Coach... This can take a moment."):
                st.session_state.user_clarifications = clarifications
                new_resume_text = generate_tailored_resume(
                    original_resume_text=st.session_state.resume_text,
                    jd_text=st.session_state.jd_text,
                    user_clarifications=st.session_state.user_clarifications
                )
                st.session_state.new_resume = new_resume_text
                st.rerun()

    # --- 5. Display the generated resume ---
    if "new_resume" in st.session_state:
        st.header("📄 Your New, Tailored Resume")
        st.text_area("Generated Resume", st.session_state.new_resume, height=500)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.download_button(
                "Download as .txt", 
                st.session_state.new_resume, 
                file_name="Resume_Doctor_tailored_resume.txt"
            )
        with col_btn2:
            if st.button("Analyze New Resume 🔬"):
                with st.spinner("Analyzing your new resume..."):
                    new_resume_skills = extract_skills_from_text(st.session_state.new_resume)
                    new_analysis = analyze_skills_alignment(new_resume_skills, st.session_state.jd_skills)
                    
                    st.session_state.new_analysis_results = new_analysis
                    
                    new_missing_count = len(new_analysis.get("missing_skills", []))
                    new_score = (len(st.session_state.jd_skills) - new_missing_count) / len(st.session_state.jd_skills) if st.session_state.jd_skills else 0
                    st.session_state.new_match_percentage = max(0, new_score)
                    st.rerun()

    # --- 6. Display the "After" report if it exists ---
    if st.session_state.new_analysis_results:
        st.markdown("---")
        st.header("🔬 Tailored Resume Analysis Report")
        
        # Display new score metric
        new_score_val = st.session_state.new_match_percentage
        delta_val = new_score_val - st.session_state.original_match_percentage
        st.metric(
            label="New Skill Alignment", 
            value=f"{new_score_val:.0%}", 
            delta=f"{delta_val:.0%} Improvement"
        )
        st.progress(new_score_val)
        st.markdown("---")

        new_analysis_data = st.session_state.new_analysis_results
        new_matched = new_analysis_data.get("matched_skills", [])
        new_missing = new_analysis_data.get("missing_skills", [])
        new_unique = new_analysis_data.get("unique_skills", [])

        col1_new, col2_new, col3_new = st.columns(3)
        with col1_new:
            st.success("✅ Matched Skills")
            if new_matched:
                st.dataframe(pd.DataFrame(new_matched), use_container_width=True, hide_index=True)
            else:
                st.write("No strong skill matches found.")
        with col2_new:
            st.warning("❌ Missing Key Skills")
            if new_missing:
                missing_df = pd.DataFrame({'Skill Required by Job': [skill.title() for skill in new_missing]})
                st.dataframe(missing_df, use_container_width=True, hide_index=True)
            else:
                st.write("Great news! You don't appear to be missing any key skills.")
        with col3_new:
            with st.spinner("Filtering unique skills..."):
                 relevant_unique_skills = filter_relevant_skills(new_unique, st.session_state.jd_text)
            st.info("💡 Your Relevant Unique Skills")
            if relevant_unique_skills:
                resume_only_df = pd.DataFrame({'Your Skill': [skill.title() for skill in relevant_unique_skills]})
                st.dataframe(resume_only_df, use_container_width=True, hide_index=True)
            else:
                st.write("No unique skills with professional relevance were identified.")
