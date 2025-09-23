# Add this at the very top of your app.py (after imports, before page config)

import streamlit as st
import pandas as pd
import hashlib
import time
import requests
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

# DEBUG: Test GA tracking with visible confirmation
GA_MEASUREMENT_ID = "G-CRNTFTMXGK"

# Generate a unique client ID for this session
if "client_id" not in st.session_state:
    st.session_state.client_id = hashlib.md5(str(time.time()).encode()).hexdigest()

# DEBUG: Show tracking info
st.sidebar.markdown("---")
st.sidebar.markdown("**🔍 Debug Info:**")
st.sidebar.write(f"Client ID: {st.session_state.client_id[:8]}...")
st.sidebar.write(f"GA ID: {GA_MEASUREMENT_ID}")

def track_ga4_event_debug(event_name, event_parameters=None):
    """Track events with visible debugging"""
    if event_parameters is None:
        event_parameters = {}
    
    client_id = st.session_state.client_id
    
    # Create the tracking URL
    ua_url = f"https://www.google-analytics.com/collect?v=1&tid={GA_MEASUREMENT_ID}&cid={client_id}&t=event&ec=engagement&ea={event_name}"
    
    # Method 1: Image pixel
    st.markdown(f"""
    <img src="{ua_url}" style="display:none;" width="1" height="1" alt="GA Pixel" />
    <script>console.log('GA tracking fired: {event_name}');</script>
    """, unsafe_allow_html=True)
    
    # Method 2: Try server-side request as backup
    try:
        response = requests.get(ua_url, timeout=1)
        st.sidebar.success(f"✅ Tracked: {event_name}")
        st.sidebar.write(f"Status: {response.status_code}")
    except Exception as e:
        st.sidebar.error(f"❌ Error: {event_name}")
        st.sidebar.write(f"Error: {str(e)[:50]}...")

def track_page_view_debug():
    """Track page view with debugging"""
    client_id = st.session_state.client_id
    url = f"https://www.google-analytics.com/collect?v=1&tid={GA_MEASUREMENT_ID}&cid={client_id}&t=pageview&dp=%2F&dt=Resume%20Doctor"
    
    # Method 1: Image pixel
    st.markdown(f"""
    <img src="{url}" style="display:none;" width="1" height="1" alt="GA Page View" />
    <script>console.log('GA page view fired');</script>
    """, unsafe_allow_html=True)
    
    # Method 2: Server-side backup
    try:
        response = requests.get(url, timeout=1)
        st.sidebar.success("✅ Page view tracked")
        st.sidebar.write(f"Status: {response.status_code}")
    except Exception as e:
        st.sidebar.error("❌ Page view failed")
        st.sidebar.write(f"Error: {str(e)[:50]}...")

# Track page view immediately
track_page_view_debug()

# Manual test button
if st.sidebar.button("🧪 Test GA Tracking"):
    track_ga4_event_debug('manual_test', {'test': 'true'})
    st.sidebar.write("Check Real-Time reports now!")

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

# Simplified tracking functions for the rest of the app
def track_sample_data_loaded():
    track_ga4_event_debug('sample_data_loaded')

def track_analysis_started():
    track_ga4_event_debug('resume_analysis_started')

def track_improvements_generated():
    track_ga4_event_debug('improvements_generated')

def track_clarifications_completed():
    track_ga4_event_debug('skill_clarifications_completed')

def track_download_action_plan():
    track_ga4_event_debug('download_action_plan')

# Rest of your app code continues here...
# (I'll just include the essential parts to keep this focused)

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

# Initialize Session State and continue with rest of app...
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""

# Main content
st.header("🩺 Resume Doctor")
st.write("Upload your resume and paste a job description to get started!")

# Sample data loader
def load_sample_data():
    try:
        with open("sample_resume.txt", "r") as f:
            st.session_state.resume_text_from_sample = f.read()
        with open("sample_jd.txt", "r") as f:
            st.session_state.jd_text = f.read()
        track_sample_data_loaded()  # Track this event
    except FileNotFoundError:
        st.sidebar.error("Sample files not found.")

if st.sidebar.button("Load Sample Data 🧪", on_click=load_sample_data):
    pass

# The rest of your existing app code would continue here...
# For brevity, I'm focusing on just the tracking debug functionality