import streamlit as st
import pandas as pd
import hashlib
import time
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

# Google Analytics - Measurement Protocol (CSP-proof method)
GA_MEASUREMENT_ID = "G-CRNTFTMXGK"
GA_API_SECRET = "your_api_secret_here"  # You'll need to get this from GA4

# Generate a unique client ID for this session
if "client_id" not in st.session_state:
    st.session_state.client_id = hashlib.md5(str(time.time()).encode()).hexdigest()

def track_ga4_event(event_name, event_parameters=None):
    """Track events using GA4 Measurement Protocol (bypasses CSP)"""
    if event_parameters is None:
        event_parameters = {}
    
    # Use image pixel method for now (simpler, works immediately)
    client_id = st.session_state.client_id
    
    # Create tracking pixel URL
    base_url = "https://www.google-analytics.com/mp/collect"
    params = {
        'measurement_id': GA_MEASUREMENT_ID,
        'client_id': client_id,
        'events': [
            {
                'name': event_name,
                'params': event_parameters
            }
        ]
    }
    
    # For now, use the simpler Universal Analytics method (works immediately)
    ua_url = f"https://www.google-analytics.com/collect?v=1&tid={GA_MEASUREMENT_ID}&cid={client_id}&t=event&ec=engagement&ea={event_name}"
    
    st.markdown(f"""
    <img src="{ua_url}" style="display:none;" width="1" height="1" />
    """, unsafe_allow_html=True)

def track_page_view():
    """Track page view without JavaScript"""
    client_id = st.session_state.client_id
    url = f"https://www.google-analytics.com/collect?v=1&tid={GA_MEASUREMENT_ID}&cid={client_id}&t=pageview&dp=%2F&dt=Resume%20Doctor"
    
    st.markdown(f"""
    <img src="{url}" style="display:none;" width="1" height="1" />
    """, unsafe_allow_html=True)

# Track initial page view
track_page_view()

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

# Google Analytics Event Tracking Functions - Measurement Protocol version
def track_sample_data_loaded():
    track_ga4_event('sample_data_loaded', {'event_category': 'engagement', 'event_label': 'demo_usage'})

def track_analysis_started():
    track_ga4_event('resume_analysis_started', {'event_category': 'conversion', 'event_label': 'resume_upload'})

def track_improvements_generated():
    track_ga4_event('improvements_generated', {'event_category': 'conversion', 'event_label': 'personalized_plan'})

def track_clarifications_completed():
    track_ga4_event('skill_clarifications_completed', {'event_category': 'engagement', 'event_label': 'user_input'})

def track_download_action_plan():
    track_ga4_event('download_action_plan', {'event_category': 'conversion', 'event_label': 'file_download'})

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
    
    # Immediate value proposition
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin: 1rem 0; color: white;">
        <h2 style="margin: 0; font-size: 1.8rem;">⚡ Stop Sending Resumes Into the Black Hole</h2>
        <p style="font-size: 1.2rem; margin: 0.5rem 0 0 0;">Get your exact match score in 30 seconds and see precisely what's missing</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Problem/Solution hook with research backing
    st.markdown("""
    ### 🎯 Only 2-3% of Resumes Get Interviews - Here's Why
    
    Most resumes fail because they don't align with what employers actually want. The data is clear:
    """)
    
    # Visual comparison - CONDENSED
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div style="background-color: #fff5f5; padding: 1rem; border-radius: 8px; border-left: 4px solid #f56565;">
        <h4 style="color: #c53030; margin-top: 0;">❌ What You're Doing Now</h4>
        <ul style="margin-bottom: 0;">
        <li>"Use action words"</li>
        <li>"Keep it to one page"</li>  
        <li>"Tailor it somehow"</li>
        </ul>
        <p style="margin: 0.5rem 0 0 0;"><strong>Result: Still no interviews</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background-color: #f0fff4; padding: 1rem; border-radius: 8px; border-left: 4px solid #48bb78;">
        <h4 style="color: #2d7d32; margin-top: 0;">✅ What Resume Doctor Shows You</h4>
        <ul style="margin-bottom: 0;">
        <li>"Add 'SQL' to your skills section"</li>
        <li>"Emphasize 'team leadership' in role #2"</li>
        <li>"Missing: 'Agile methodology' experience"</li>
        </ul>
        <p style="margin: 0.5rem 0 0 0;"><strong>Result: Specific, actionable fixes</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Add clear separation
    st.markdown("---")
    st.markdown("### 🎯 What You'll Get")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **📊 Your Exact Results:**
        - See your % alignment across all key areas
        - Compare your skills vs. job requirements  
        - Identify your strongest selling points
        - Specific skills the job wants that you're missing
        - Experience gaps to address
        - Skills that match perfectly
        - Hidden strengths to emphasize
        """)
    
    with col2:
        st.markdown("""
        **🎯 Exact Fix Instructions:**  
        - "Add this to line 3 of your experience"
        - "Move SQL to top of skills list"
        - "Emphasize leadership in role #2"
        - Simple process: Upload → Paste → Analyze → Fix
        - 30-second AI analysis across all areas
        - No generic advice - specific editing instructions
        """)
    
    # Updated trust indicators - removed privacy claim
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**📊 Research-Backed**<br><a href='https://enhancv.com/blog/resume-statistics/' target='_blank'>83% of recruiters prefer tailored resumes</a>", unsafe_allow_html=True)
    with col2:
        st.markdown("**⚡ 30 Second Analysis**<br>Instant results across all key areas", unsafe_allow_html=True) 
    with col3:
        st.markdown("**🆓 Completely Free**<br>No account or payments required", unsafe_allow_html=True)

# --- Main Display (Analysis Results) ---
if st.session_state.analysis_complete:
    analysis = st.session_state.categorized_analysis
    
    # Calculate overall score
    category_scores = [data["match_percentage"] for data in analysis.values()]
    overall_score = sum(category_scores) / len(category_scores) if category_scores else 0
    
    # --- Overall Score Display ---
    st.header("🔬 Resume Analysis Results")
    st.metric(label="Overall Alignment Score", value=f"{overall_score:.0%}")
    st.progress(overall_score)
    st.markdown("---")
    
    # --- Category Breakdown ---
    st.header("📊 Detailed Category Analysis")
    
    # Create tabs for each category
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Education & Certs", "💼 Professional Skills", "🤝 Soft Skills", "⏱️ Experience"])
    
    category_configs = {
        "education_certifications": {
            "tab": tab1,
            "title": "Education & Certifications",
            "icon": "📚",
            "description": "Degrees, certifications, licenses, and coursework"
        },
        "professional_skills": {
            "tab": tab2, 
            "title": "Professional Skills",
            "icon": "💼",
            "description": "Job-specific skills, tools, software, and methodologies"
        },
        "soft_skills": {
            "tab": tab3,
            "title": "Soft Skills", 
            "icon": "🤝",
            "description": "Communication, leadership, teamwork, and interpersonal abilities"
        },
        "experience": {
            "tab": tab4,
            "title": "Experience",
            "icon": "⏱️", 
            "description": "Years of experience, industry background, and role levels"
        }
    }
    
    # Generate insights for all categories
    with st.spinner("Generating category insights..."):
        category_insights = get_category_insights(analysis, st.session_state.jd_text)
    
    for category_key, config in category_configs.items():
        with config["tab"]:
            data = analysis.get(category_key, {})
            match_pct = data.get("match_percentage", 0)
            matched = data.get("matched", [])
            missing = data.get("missing", [])
            unique = data.get("unique", [])
            
            # Score and insight
            st.subheader(f"{config['icon']} {config['title']}")
            col_score, col_insight = st.columns([1, 2])
            
            with col_score:
                st.metric(label="Match Score", value=f"{match_pct:.0%}")
                
            with col_insight:
                insight = category_insights.get(category_key, "No insights available")
                st.info(f"💡 **Insight:** {insight}")
            
            st.markdown("---")
            
            # Data display
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.success("✅ **Matched**")
                if matched:
                    matched_df = pd.DataFrame([
                        {"Your Item": m["resume_item"], "Matches": m["jd_item"]} 
                        for m in matched
                    ])
                    st.dataframe(matched_df, use_container_width=True, hide_index=True)
                else:
                    st.write("No matches found")
            
            with col2:
                st.warning("❌ **Missing**")
                if missing:
                    missing_df = pd.DataFrame({"Required": [item.title() for item in missing]})
                    st.dataframe(missing_df, use_container_width=True, hide_index=True)
                else:
                    st.write("Nothing missing!")
            
            with col3:
                st.info("💎 **Your Unique Items**")
                if unique:
                    unique_df = pd.DataFrame({"Your Assets": [item.title() for item in unique]})
                    st.dataframe(unique_df, use_container_width=True, hide_index=True)
                else:
                    st.write("No unique items found")
    
    st.markdown("---")
    
    # --- Collect All Missing Skills for Clarification ---
    # Gather all missing skills from all categories
    all_missing_skills = {}
    for category_key, data in analysis.items():
        missing = data.get("missing", [])
        if missing:
            category_name = category_key.replace("_", " ").title()
            all_missing_skills[category_key] = {
                "category_name": category_name,
                "skills": missing
            }
    
    st.session_state.all_missing_skills = all_missing_skills
    
    # --- Interactive Skill Clarification Section ---
    if all_missing_skills and not st.session_state.skill_clarifications_complete:
        st.header("🔍 Skill Clarification")
        st.info("The AI identified these as 'missing' skills. ✅ if you have it (and add details) or ❌ to remove irrelevant items.")
        
        # Initialize removed skills and confirmed skills tracking
        if "removed_skills" not in st.session_state:
            st.session_state.removed_skills = set()
        if "confirmed_skills" not in st.session_state:
            st.session_state.confirmed_skills = set()
        
        # Debug: Show current state
        if st.session_state.removed_skills:
            st.sidebar.write(f"Debug - Removed: {len(st.session_state.removed_skills)} skills")
        
        user_clarifications = {}
        
        for category_key, category_data in all_missing_skills.items():
            # Filter out removed skills for this category
            remaining_skills = [skill for skill in category_data['skills'] 
                              if f"{category_key}_{skill}" not in st.session_state.removed_skills]
            
            if remaining_skills:  # Only show category if it has remaining skills
                with st.expander(f"📋 **{category_data['category_name']}** ({len(remaining_skills)} skills to review)", expanded=True):
                    category_clarifications = {}
                    
                    for skill in remaining_skills:
                        skill_key = f"{category_key}_{skill}"
                        
                        col1, col2, col3 = st.columns([2, 1, 3])
                        
                        with col1:
                            st.write(f"**{skill.title()}**")
                        
                        with col2:
                            # Create two buttons side by side
                            btn_col1, btn_col2 = st.columns(2)
                            
                            with btn_col1:
                                if st.button("❌", key=f"remove_{skill_key}", help="Remove this skill"):
                                    st.session_state.removed_skills.add(skill_key)
                                    if skill_key in st.session_state.confirmed_skills:
                                        st.session_state.confirmed_skills.remove(skill_key)
                                    st.rerun()  # Always rerun to immediately update the display
                            
                            with btn_col2:
                                # Show different button state based on confirmation
                                if skill_key in st.session_state.confirmed_skills:
                                    st.button("✅", key=f"confirmed_{skill_key}", disabled=True, help="Confirmed - add details below")
                                else:
                                    if st.button("✅", key=f"confirm_{skill_key}", help="I have this skill"):
                                        st.session_state.confirmed_skills.add(skill_key)
                                        st.rerun()
                        
                        with col3:
                            # Show text input if skill is confirmed
                            if skill_key in st.session_state.confirmed_skills:
                                experience = st.text_input(
                                    "Brief example of your experience:",
                                    key=f"exp_{skill_key}",
                                    placeholder=f"e.g., Used {skill} in my previous role to...",
                                    label_visibility="collapsed"
                                )
                                if experience.strip():
                                    category_clarifications[skill] = experience
                    
                    if category_clarifications:
                        user_clarifications[category_key] = category_clarifications
        
        # Show summary of actions taken
        if st.session_state.removed_skills:
            with st.expander(f"🗑️ Removed Skills ({len(st.session_state.removed_skills)})"):
                removed_by_category = {}
                for removed_key in st.session_state.removed_skills:
                    category, skill = removed_key.split('_', 1)
                    if category not in removed_by_category:
                        removed_by_category[category] = []
                    removed_by_category[category].append(skill)
                
                for category, skills in removed_by_category.items():
                    category_name = category.replace("_", " ").title()
                    st.write(f"**{category_name}:** {', '.join([s.title() for s in skills])}")
                
                if st.button("🔄 Reset All Removals"):
                    st.session_state.removed_skills = set()
                    st.rerun()
        
        if st.button("Apply My Clarifications", type="primary"):
            st.session_state.user_clarifications = user_clarifications
            st.session_state.skill_clarifications_complete = True
            track_clarifications_completed()  # Track this event
            st.rerun()
    
    elif st.session_state.skill_clarifications_complete:
        # Show updated analysis with user clarifications
        st.header("📊 Updated Analysis (With Your Input)")
        
        clarifications = st.session_state.get("user_clarifications", {})
        
        if clarifications:
            st.success(f"✅ You've clarified {sum(len(skills) for skills in clarifications.values())} skills across {len(clarifications)} categories!")
            
            # Show what was clarified
            with st.expander("🔄 **Skills You've Added Back**"):
                for category_key, skills in clarifications.items():
                    category_name = all_missing_skills[category_key]["category_name"]
                    st.write(f"**{category_name}:**")
                    for skill, experience in skills.items():
                        st.write(f"• {skill.title()}: {experience}")
        
        # Update the analysis results with user clarifications
        updated_analysis = update_analysis_with_clarifications(
            st.session_state.categorized_analysis, 
            clarifications
        )
        
        # Show updated category scores
        col1, col2, col3, col4 = st.columns(4)
        
        category_configs = {
            "education_certifications": {"col": col1, "icon": "📚", "name": "Education"},
            "professional_skills": {"col": col2, "icon": "💼", "name": "Professional"}, 
            "soft_skills": {"col": col3, "icon": "🤝", "name": "Soft Skills"},
            "experience": {"col": col4, "icon": "⏱️", "name": "Experience"}
        }
        
        for category_key, config in category_configs.items():
            with config["col"]:
                old_score = analysis[category_key]["match_percentage"]
                new_score = updated_analysis[category_key]["match_percentage"]
                delta = new_score - old_score
                
                st.metric(
                    label=f"{config['icon']} {config['name']}",
                    value=f"{new_score:.0%}",
                    delta=f"{delta:.0%}" if delta != 0 else None
                )
    
    # --- Improvement Suggestions (only after clarifications) ---
    if st.session_state.skill_clarifications_complete:
        st.header("🎯 Personalized Improvements")
        
        if st.button("Generate My Personalized Action Plan", type="primary"):
            with st.spinner("Creating your personalized improvements based on your clarifications..."):
                # Use the updated analysis that includes user clarifications
                updated_analysis = update_analysis_with_clarifications(
                    st.session_state.categorized_analysis, 
                    st.session_state.get("user_clarifications", {})
                )
                
                improvements = generate_targeted_improvements(
                    st.session_state.resume_text,
                    st.session_state.jd_text, 
                    updated_analysis,  # Use updated analysis here!
                    st.session_state.get("user_clarifications", {})
                )
                st.session_state.improvements = improvements
                st.session_state.improvements_generated = True
                track_improvements_generated()  # Track this event
                st.rerun()
        
        if st.session_state.improvements_generated:
            improvements = st.session_state.improvements.get("improvements", [])
            
            st.subheader("📝 Your Personalized Action Plan")
            
            for i, improvement in enumerate(improvements, 1):
                with st.expander(f"**{i}. {improvement.get('type', 'Improvement').replace('_', ' ').title()}** - {improvement.get('section', 'General')}"):
                    st.write(f"**Action:** {improvement.get('instruction', 'N/A')}")
                    
                    if improvement.get('suggested_text'):
                        st.code(improvement['suggested_text'], language=None)
                    
                    if improvement.get('original'):
                        st.write(f"**Replace this:** {improvement['original']}")
                    
                    st.write(f"**Why:** {improvement.get('reason', 'No reason provided')}")
            
            # Download improvements
            improvements_text = "\n\n".join([
                f"{i}. {imp.get('instruction', '')}\n   Action: {imp.get('suggested_text', '')}\n   Reason: {imp.get('reason', '')}" 
                for i, imp in enumerate(improvements, 1)
            ])
            
            if st.download_button(
                "Download Personalized Action Plan",
                improvements_text,
                file_name="personalized_resume_plan.txt",
                mime="text/plain"
            ):
                track_download_action_plan()  # Track download event
    
    else:
        # If no missing skills, skip directly to improvements
        if not all_missing_skills:
            st.header("🎯 Targeted Improvements")
            st.success("Great news! No missing skills were identified across any category.")
            
            if st.button("Generate Optimization Suggestions", type="primary"):
                with st.spinner("Generating optimization suggestions..."):
                    improvements = generate_targeted_improvements(
                        st.session_state.resume_text,
                        st.session_state.jd_text, 
                        st.session_state.categorized_analysis,
                        {}
                    )
                    st.session_state.improvements = improvements
                    st.session_state.improvements_generated = True
                    st.session_state.skill_clarifications_complete = True
                    track_improvements_generated()  # Track this event
                    st.rerun()

# --- FAQ Section for SEO ---
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