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

# Google Analytics - EXACTLY as Google provided it, but injected properly for Streamlit
st.components.v1.html("""
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-CRNTFTMXGK"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-CRNTFTMXGK');
  
  // Send a test event to confirm it's working
  gtag('event', 'page_view', {
    page_title: 'Resume Doctor',
    page_location: window.location.href
  });
  
  console.log('Google Analytics loaded successfully');
  
  // Make gtag available to parent window (this might help with CSP)
  if (window.parent && window.parent !== window) {
    window.parent.gtag = gtag;
  }
</script>
""", height=0)

# Simple event tracking functions using st.components.v1.html
def track_event(event_name, parameters=None):
    if parameters is None:
        parameters = {}
    
    # Convert parameters to JavaScript object string
    params_js = ", ".join([f"'{k}': '{v}'" for k, v in parameters.items()])
    
    st.components.v1.html(f"""
    <script>
    if (typeof gtag !== 'undefined') {{
        gtag('event', '{event_name}', {{{params_js}}});
        console.log('Event tracked: {event_name}');
    }} else if (window.parent && typeof window.parent.gtag !== 'undefined') {{
        window.parent.gtag('event', '{event_name}', {{{params_js}}});
        console.log('Event tracked via parent: {event_name}');
    }} else {{
        console.warn('gtag not available for event: {event_name}');
    }}
    </script>
    """, height=0)

def track_sample_data_loaded():
    track_event('sample_data_loaded', {'event_category': 'engagement', 'event_label': 'demo_usage'})

def track_analysis_started():
    track_event('resume_analysis_started', {'event_category': 'conversion', 'event_label': 'resume_upload'})

def track_improvements_generated():
    track_event('improvements_generated', {'event_category': 'conversion', 'event_label': 'personalized_plan'})

def track_clarifications_completed():
    track_event('skill_clarifications_completed', {'event_category': 'engagement', 'event_label': 'user_input'})

def track_download_action_plan():
    track_event('download_action_plan', {'event_category': 'conversion', 'event_label': 'file_download'})

# Add SEO meta tags and structured data
st.markdown("""
<link rel="canonical" href="https://www.resumedoctor.us/">
<meta name="description" content="Free AI resume analyzer that compares your resume to job descriptions across key categories. Get personalized improvement suggestions and increase your job match score.">
<meta name="keywords" content="resume analyzer, AI resume checker, job match tool, resume optimization, ATS resume scanner, free resume analysis">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication", 
  "name": "Resume Doctor",
  "description": "Free AI-powered resume analyzer and job matching tool",
  "url": "https://www.resumedoctor.us",
  "applicationCategory": "BusinessApplication",
  "offers": {
    "@type": "Offer",
    "price": "0"
  }
}
</script>
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
        # Don't artificially inflate by removing X'd skills from denominator
        original_total = len(category_data.get("missing", [])) + len(category_data.get("matched", []))
        current_matched = len(matched_skills)
        
        if original_total > 0:
            updated_data["match_percentage"] = current_matched / original_total
        else:
            updated_data["match_percentage"] = category_data.get("match_percentage", 0.0)  # Keep original if no requirements
        
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

# --- RED BAR AT THE VERY TOP ---
if not st.session_state.analysis_complete:
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; margin: -1rem -1rem 2rem -1rem;">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: bold;">🚀 Ready to Get 3X More Interviews?</h1>
        <p style="font-size: 1.3rem; margin: 1rem 0;">Upload your resume in the sidebar and see your match score instantly!</p>
        <p style="font-size: 1rem; opacity: 0.9; margin: 0;">⬅️ Click "Load Sample Data" to try it first • <a href="https://www.jobscan.co/" target="_blank" style="color: white; text-decoration: underline;">Research shows 3X improvement</a></p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; margin: -1rem -1rem 1rem -1rem;">
        <h2 style="margin: 0;">✅ Your Resume Analysis Results</h2>
    </div>
    """, unsafe_allow_html=True)

# --- Sidebar for Inputs ---
st.sidebar.header("Your Documents")

# Test button
if st.sidebar.button("🧪 Test Analytics"):
    track_event('manual_test', {'test': 'sidebar_button'})
    st.sidebar.success("Test event sent! Check Real-Time reports.")

# --- Legal Disclaimer ---
st.sidebar.markdown("---")
with st.sidebar.expander("⚠️ **Data Usage Disclaimer**"):
    st.markdown("""
    **Important:** By using this tool, you acknowledge:
    
    - All uploaded resumes and job descriptions are processed and may be stored for service improvement
    - You are responsible for ensuring you have the right to share any content you upload
    - Do not upload confidential, proprietary, or sensitive information belonging to others
    - We are not liable for any misuse of information you choose to submit
    - By clicking "Analyze Resume" you consent to these terms
    """)
st.sidebar.markdown("---")

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

# --- Sidebar donation section ---
st.sidebar.markdown("---")
st.sidebar.header("Support This Project")
st.sidebar.write("If you found this tool helpful, consider a small BTC donation.")
st.sidebar.image("https://i.imgur.com/s9qF28O.png", width=150)

# --- Main Content ---
if not st.session_state.analysis_complete:
    # Research-backed stats with sources
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 Tailored Resume Success", "83%", help="83% of recruiters prefer tailored resumes (Jobvite)")
    with col2:
        st.metric("⚡ Analysis Time", "30s", help="Get results in under 30 seconds")
    with col3:
        st.metric("📈 Interview Improvement", "40%", help="Tailored resumes are 40% more likely to land interviews (Journal of Applied Psychology)")
    with col4:
        st.metric("💰 Cost", "FREE", help="No hidden fees or sign-ups required")
    
    # Add credibility section with linked sources
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background-color: #f8f9fa; border-radius: 10px; margin: 1rem 0; border-left: 4px solid #007bff;">
        <h4 style="color: #007bff; margin-top: 0;">📈 Research Shows Tailored Resumes Work</h4>
        <p style="margin-bottom: 0;">
            <a href="https://enhancv.com/blog/resume-statistics/" target="_blank" style="color: #007bff;">Studies show</a> tailored resumes are 
            <strong>40% more likely to land interviews</strong> and <strong>83% of recruiters prefer them</strong>. 
            <a href="https://www.jobscan.co/" target="_blank" style="color: #007bff;">Tools like ours</a> help users land 
            <strong>3X more interviews</strong> by optimizing resume-job matching.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Continue with rest of your existing content...
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin: 1rem 0; color: white;">
        <h2 style="margin: 0; font-size: 1.8rem;">⚡ Stop Sending Resumes Into the Black Hole</h2>
        <p style="font-size: 1.2rem; margin: 0.5rem 0 0 0;">Get your exact match score in 30 seconds and see precisely what's missing</p>
    </div>
    """, unsafe_allow_html=True)

# Add rest of your existing app logic here...
# For brevity, I'm focusing on the Google Analytics implementation

st.markdown("---")
st.subheader("Frequently Asked Questions")

with st.expander("How accurate is the AI resume analysis?"):
    st.write("Our AI uses advanced semantic matching to understand the meaning behind skills and requirements, not just keyword matching. However, we also provide an interactive clarification step where you can correct any AI mistakes.")

with st.expander("What happens to my resume data?"):
    st.write("Your resume data is processed by our AI and may be stored for service improvement purposes. Please review our complete data usage disclaimer in the sidebar for full details on how we handle your information.")

with st.expander("What file formats do you support?"):
    st.write("Currently, we support PDF resume uploads. You can also use our sample data to test the tool.")

with st.expander("How is this different from other ATS checkers?"):
    st.write("Unlike simple keyword matchers, we provide categorized analysis across key areas and give you specific, actionable editing instructions rather than just a score.")