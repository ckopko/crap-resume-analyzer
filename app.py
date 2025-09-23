import streamlit as st
import pandas as pd
from crap_analyzer.parser import extract_text_from_pdf
from crap_analyzer.analyzer import (
    extract_and_categorize_requirements,
    analyze_categorized_alignment,
    get_category_insights,
    generate_targeted_improvements
)

# SEO-optimized page config
st.set_page_config(
    page_title="Resume Doctor - Free AI Resume Analyzer & Job Match Tool",
    page_icon="🩺",
    layout="wide",
    menu_items={
        'About': "Free AI-powered resume analysis tool that helps you match your resume to any job description."
    }
)

# Google Analytics - Direct injection into page header
# This is the most direct way and should bypass all CSP issues
st.markdown("""
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-CRNTFTMXGK"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-CRNTFTMXGK');
  
  console.log('Google Analytics loaded directly');
  
  // Track page view immediately
  gtag('event', 'page_view', {
    page_title: 'Resume Doctor',
    page_location: window.location.href
  });
</script>
</head>
""", unsafe_allow_html=True)

# Alternative: Add to body if head doesn't work
st.markdown("""
<!-- Google tag (gtag.js) - Body injection -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-CRNTFTMXGK"></script>
<script>
  if (typeof window.dataLayer === 'undefined') {
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-CRNTFTMXGK');
    
    console.log('Google Analytics loaded in body');
  }
</script>
""", unsafe_allow_html=True)

# Manual tracking functions
def track_event_direct(event_name, parameters=None):
    if parameters is None:
        parameters = {}
    
    # Convert parameters to JavaScript
    params_str = ", ".join([f"'{k}': '{v}'" for k, v in parameters.items()])
    
    st.markdown(f"""
    <script>
    // Wait a moment for gtag to load, then fire event
    setTimeout(function() {{
        if (typeof gtag !== 'undefined') {{
            gtag('event', '{event_name}', {{{params_str}}});
            console.log('✅ Event tracked: {event_name}');
        }} else {{
            console.warn('❌ gtag still not available for: {event_name}');
            
            // Try to load gtag manually if it's not there
            if (!document.querySelector('script[src*="gtag"]')) {{
                var script = document.createElement('script');
                script.async = true;
                script.src = 'https://www.googletagmanager.com/gtag/js?id=G-CRNTFTMXGK';
                document.head.appendChild(script);
                
                script.onload = function() {{
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){{dataLayer.push(arguments);}}
                    gtag('js', new Date());
                    gtag('config', 'G-CRNTFTMXGK');
                    gtag('event', '{event_name}', {{{params_str}}});
                    console.log('✅ Late-loaded and tracked: {event_name}');
                }};
            }}
        }}
    }}, 1000);
    </script>
    """, unsafe_allow_html=True)

# Debug button - let's see what's happening
if st.sidebar.button("🔍 Debug GA Status"):
    st.markdown("""
    <script>
    console.log('=== GA DEBUG INFO ===');
    console.log('gtag function available:', typeof gtag !== 'undefined');
    console.log('dataLayer exists:', typeof dataLayer !== 'undefined');
    console.log('dataLayer contents:', dataLayer);
    console.log('GA scripts in page:', document.querySelectorAll('script[src*="gtag"]').length);
    console.log('All scripts:', Array.from(document.scripts).map(s => s.src).filter(s => s.includes('google')));
    
    // Try to send a test event
    if (typeof gtag !== 'undefined') {
        gtag('event', 'debug_test', {
            'debug_from': 'streamlit_button'
        });
        console.log('✅ Debug event sent successfully');
    } else {
        console.log('❌ gtag not available for debug test');
    }
    </script>
    """, unsafe_allow_html=True)
    
    st.sidebar.success("Debug info logged to console - check F12!")

# Simple tracking functions
def track_sample_data_loaded():
    track_event_direct('sample_data_loaded', {'event_category': 'engagement'})

def track_analysis_started():
    track_event_direct('resume_analysis_started', {'event_category': 'conversion'})

def track_improvements_generated():
    track_event_direct('improvements_generated', {'event_category': 'conversion'})

def track_clarifications_completed():
    track_event_direct('skill_clarifications_completed', {'event_category': 'engagement'})

def track_download_action_plan():
    track_event_direct('download_action_plan', {'event_category': 'conversion'})

# Add SEO meta tags
st.markdown("""
<link rel="canonical" href="https://www.resumedoctor.us/">
<meta name="description" content="Free AI resume analyzer that compares your resume to job descriptions across key categories. Get personalized improvement suggestions and increase your job match score.">
<meta name="keywords" content="resume analyzer, AI resume checker, job match tool, resume optimization, ATS resume scanner, free resume analysis">
""", unsafe_allow_html=True)

def update_analysis_with_clarifications(original_analysis: dict, user_clarifications: dict):
    """
    Updates the analysis results by moving clarified skills from 'missing' to 'matched',
    and removing skills the user X'd out as irrelevant.
    """
    updated_analysis = {}
    
    # Get removed skills from session state
    removed_skills = getattr(st.session_state, 'removed_skills', set())
    
    for category_key, category_data in original_analysis.items():
        updated_data = category_data.copy()
        
        # Start with original missing skills
        missing_skills = updated_data.get("missing", []).copy()
        matched_skills = updated_data.get("matched", []).copy()
        
        # Remove skills that user X'd out (they're not relevant)
        skills_to_remove = []
        for skill in missing_skills:
            skill_key = f"{category_key}_{skill}"
            if skill_key in removed_skills:
                skills_to_remove.append(skill)
        
        for skill in skills_to_remove:
            missing_skills.remove(skill)
        
        # Move clarified skills from missing to matched
        if category_key in user_clarifications:
            clarified_skills = user_clarifications[category_key]
            
            for skill, experience in clarified_skills.items():
                if skill in missing_skills:
                    missing_skills.remove(skill)
                    # Add to matched with user's experience
                    matched_skills.append({
                        "resume_item": experience,
                        "jd_item": skill.title(),
                        "similarity": 1.0  # Perfect match since user confirmed
                    })
        
        updated_data["missing"] = missing_skills
        updated_data["matched"] = matched_skills
        
        # FIXED: Keep the original match percentage calculation
        original_total = len(category_data.get("missing", [])) + len(category_data.get("matched", []))
        current_matched = len(matched_skills)
        
        if original_total > 0:
            updated_data["match_percentage"] = current_matched / original_total
        else:
            updated_data["match_percentage"] = category_data.get("match_percentage", 0.0)
        
        updated_analysis[category_key] = updated_data
    
    return updated_analysis

# --- Initialize Session State ---
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""
if "categorized_analysis" not in st.session_state:
    st.session_state.categorized_analysis = {}
if "improvements_generated" not in st.session_state:
    st.session_state.improvements_generated = False
if "skill_clarifications_complete" not in st.session_state:
    st.session_state.skill_clarifications_complete = False
if "all_missing_skills" not in st.session_state:
    st.session_state.all_missing_skills = {}

# --- Sidebar for Inputs ---
st.sidebar.header("Your Documents")

# Test button with immediate feedback
if st.sidebar.button("🧪 Test GA Tracking"):
    track_event_direct('manual_test', {'source': 'sidebar_button'})
    st.sidebar.success("Test event sent! Check console and Real-Time reports.")

# --- Sample Data Loader ---
def load_sample_data():
    try:
        with open("sample_resume.txt", "r") as f:
            st.session_state.resume_text_from_sample = f.read()
        with open("sample_jd.txt", "r") as f:
            st.session_state.jd_text = f.read()
        st.session_state.analysis_complete = False
        st.session_state.skill_clarifications_complete = False
        st.session_state.all_missing_skills = {}
        track_sample_data_loaded()  # Track this event
    except FileNotFoundError:
        st.sidebar.error("Sample files not found.")

if st.sidebar.button("Load Sample Data 🧪", on_click=load_sample_data):
    pass

st.sidebar.markdown("---")

uploaded_resume = st.sidebar.file_uploader("Upload Your Resume (PDF)", type=["pdf"])
jd_text_input = st.sidebar.text_area("Paste the Job Description Here", height=250, value=st.session_state.jd_text)
st.session_state.jd_text = jd_text_input

if st.sidebar.button("Analyze Resume", type="primary"):
    resume_text_to_analyze = ""
    if uploaded_resume is not None:
        resume_text_to_analyze = extract_text_from_pdf(uploaded_resume)
    elif "resume_text_from_sample" in st.session_state and st.session_state.resume_text_from_sample:
        resume_text_to_analyze = st.session_state.resume_text_from_sample

    if resume_text_to_analyze and st.session_state.jd_text:
        track_analysis_started()  # Track this event
        
        with st.spinner("Analyzing your resume across multiple categories..."):
            # Reset state
            st.session_state.improvements_generated = False
            st.session_state.skill_clarifications_complete = False
            st.session_state.all_missing_skills = {}
            st.session_state.resume_text = resume_text_to_analyze
            
            # Extract and categorize both documents
            resume_categories = extract_and_categorize_requirements(resume_text_to_analyze, is_job_description=False)
            jd_categories = extract_and_categorize_requirements(st.session_state.jd_text, is_job_description=True)
            
            # Perform categorized analysis
            analysis_results = analyze_categorized_alignment(resume_categories, jd_categories)
            
            # Store results
            st.session_state.categorized_analysis = analysis_results
            st.session_state.resume_categories = resume_categories
            st.session_state.jd_categories = jd_categories
            st.session_state.analysis_complete = True
            
    else:
        st.sidebar.error("Please provide both a resume and a job description.")

# --- Main Content ---
if not st.session_state.analysis_complete:
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; margin: -1rem -1rem 2rem -1rem;">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: bold;">🚀 Ready to Get 3X More Interviews?</h1>
        <p style="font-size: 1.3rem; margin: 1rem 0;">Upload your resume in the sidebar and see your match score instantly!</p>
        <p style="font-size: 1rem; opacity: 0.9; margin: 0;">⬅️ Click "Load Sample Data" to try it first</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Research-backed stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 Tailored Resume Success", "83%", help="83% of recruiters prefer tailored resumes")
    with col2:
        st.metric("⚡ Analysis Time", "30s", help="Get results in under 30 seconds")
    with col3:
        st.metric("📈 Interview Improvement", "40%", help="Tailored resumes are 40% more likely to land interviews")
    with col4:
        st.metric("💰 Cost", "FREE", help="No hidden fees or sign-ups required")

else:
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; margin: -1rem -1rem 1rem -1rem;">
        <h2 style="margin: 0;">✅ Your Resume Analysis Results</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Show basic analysis results
    analysis = st.session_state.categorized_analysis
    category_scores = [data["match_percentage"] for data in analysis.values()]
    overall_score = sum(category_scores) / len(category_scores) if category_scores else 0
    
    st.header("🔬 Resume Analysis Results")
    st.metric(label="Overall Alignment Score", value=f"{overall_score:.0%}")
    st.progress(overall_score)

# --- FAQ Section ---
st.markdown("---")
st.subheader("Frequently Asked Questions")

with st.expander("How accurate is the AI resume analysis?"):
    st.write("Our AI uses advanced semantic matching to understand the meaning behind skills and requirements, not just keyword matching.")

with st.expander("What file formats do you support?"):
    st.write("Currently, we support PDF resume uploads. You can also use our sample data to test the tool.")

with st.expander("How is this different from other ATS checkers?"):
    st.write("Unlike simple keyword matchers, we provide categorized analysis across key areas and give you specific, actionable editing instructions.")