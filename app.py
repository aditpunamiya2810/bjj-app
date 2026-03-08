import os
import tempfile
import threading
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Import our custom modules
from backend import analyze_video_with_gemini
from stats import generate_interval_csv, generate_pdf_report

# --- STRICT AUTHENTICATION FIX ---
# This prevents the "Google Cloud SDK" quota warning by forcing the API key
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("Google API Key missing. Please set GOOGLE_API_KEY in your .env file.")
    st.stop()

# --- UI Config & Custom CSS ---
st.set_page_config(page_title="BJJ AI COACH", page_icon="🥋", layout="wide")
st.markdown("""
<style>
    .score-container { text-align: center; padding: 20px; background-color: #1E1E2E; border-radius: 10px; margin-bottom: 20px;}
    .big-score { font-size: 64px; font-weight: bold; color: #8A2BE2; margin: 0; line-height: 1;}
    .perf-label { font-size: 18px; color: #A0A0B0; letter-spacing: 2px; text-transform: uppercase;}
    .grade-pill { display: inline-block; padding: 5px 15px; border-radius: 20px; background-color: #5D5D81; color: white; margin: 0 10px; font-weight: bold;}
    .strength-card { background-color: #1A3A2A; border-left: 5px solid #28A745; padding: 15px; margin-bottom: 10px; border-radius: 5px; color: #E8F5E9;}
    .weakness-card { background-color: #3A1A1A; border-left: 5px solid #DC3545; padding: 15px; margin-bottom: 10px; border-radius: 5px; color: #FFEBEE;}
    .coach-card { background-color: #1E1E2E; padding: 20px; border-radius: 10px; border-left: 5px solid #8A2BE2; margin-top: 20px;}
    div.stButton > button:first-child { background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%); color: white; border: none; width: 100%; height: 50px; font-size: 18px; font-weight: bold;}
    .live-timer { font-size: 24px; font-weight: bold; color: #F39C12; text-align: center; margin-bottom: 15px;}
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("<h1 style='text-align: center;'>🥋 BJJ AI COACH 🔗</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Advanced Performance Analysis Powered by AI</p>", unsafe_allow_html=True)
st.markdown("---")

# --- Configuration Layout ---
col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("📹 UPLOAD VIDEO")
    uploaded_file = st.file_uploader("Select sparring footage (Max 1.5 mins)", type=["mp4", "mov", "avi"])

with col_right:
    st.subheader("⚙️ MATCH CONFIGURATION")
    user_desc = st.text_input("👤 Your Description", "Player with black jersey and long hair")
    opp_desc = st.text_input("🥊 Opponent Description", "Player with green jersey")
    activity_type = st.selectbox("Activity Type", ["Brazilian Jiu-Jitsu", "Submission Grappling"])
    
    c1, c2 = st.columns(2)
    user_belt = c1.selectbox("Your Belt", ["white", "blue", "purple", "brown", "black"])
    opp_belt = c2.selectbox("Opponent Belt", ["unknown", "white", "blue", "purple", "brown", "black"])

# --- Main Execution ---
if st.button("🚀 START ANALYSIS"):
    if not uploaded_file:
        st.error("Please upload a video file first.")
        st.stop()

    # Create empty placeholders in the UI to update live
    st.markdown("---")
    timer_card = st.empty()
    status_card = st.empty()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_video_path = tmp_file.name

    # Threading variables to pass data between background task and main UI
    result_container = {}
    exception_container = {}
    shared_status = {"msg": "Initializing analysis..."}

    # Define the background worker
    def run_backend():
        try:
            result_container['data'] = analyze_video_with_gemini(
                tmp_video_path, user_desc, user_belt, opp_desc, opp_belt, API_KEY,
                status_callback=lambda msg: shared_status.update({"msg": msg})
            )
        except Exception as e:
            exception_container['error'] = e

    # Start the backend process in a separate thread
    t = threading.Thread(target=run_backend)
    t.start()

    start_time = time.time()
    
    # UI updating loop: runs as long as the backend thread is alive
    while t.is_alive():
        elapsed = int(time.time() - start_time)
        timer_card.markdown(f"<p class='live-timer'>⏱️ Elapsed Time: {elapsed} seconds</p>", unsafe_allow_html=True)
        status_card.info(f"🔄 **Current Action:** {shared_status['msg']}")
        time.sleep(0.5)  # Refresh UI every half second

    # Clean up the loading cards once finished
    timer_card.empty()
    status_card.empty()

    if 'error' in exception_container:
        st.error(exception_container['error'])
        if os.path.exists(tmp_video_path): 
            try: 
                time.sleep(1)
                os.remove(tmp_video_path) 
            except: pass
        st.stop()

    result = result_container['data']

    # Safely delete original upload
    if os.path.exists(tmp_video_path):
        try:
            time.sleep(1)
            os.remove(tmp_video_path)
        except Exception as e:
            print(f"Cleanup Warning (Safe to ignore): {e}")

    # --- UI Rendering Results ---
    st.markdown("<div class='score-container'>", unsafe_allow_html=True)
    st.markdown("<p class='perf-label'>OVERALL PERFORMANCE</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='big-score'>{result.get('overall_score', 0)}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-weight:bold; margin-top:10px;'>{result.get('performance_label', '')}</p>", unsafe_allow_html=True)
    
    g = result.get('grades', {})
    st.markdown(f"""
        <div style='margin-top:15px;'>
            <span class='grade-pill'>🛡️ DEFENSE: {g.get('defense', 'N/A')}</span>
            <span class='grade-pill'>⚔️ OFFENSE: {g.get('offense', 'N/A')}</span>
            <span class='grade-pill'>📍 CONTROL: {g.get('control', 'N/A')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 PLAYSTYLE COMPARISON")
    stat_col1, stat_col2 = st.columns(2)
    
    u_stats = result.get('user_stats', {})
    with stat_col1:
        st.markdown(f"**Your Stats (Belt: {user_belt.capitalize()})**")
        st.progress(u_stats.get('offense', 0)/100, text=f"⚔️ Offense: {u_stats.get('offense', 0)}%")
        st.progress(u_stats.get('defense', 0)/100, text=f"🛡️ Defense: {u_stats.get('defense', 0)}%")
        st.progress(u_stats.get('guard', 0)/100, text=f"🔒 Guard: {u_stats.get('guard', 0)}%")
        st.progress(u_stats.get('passing', 0)/100, text=f"🏃 Passing: {u_stats.get('passing', 0)}%")
        
    o_stats = result.get('opponent_stats', {})
    with stat_col2:
        st.markdown(f"**Opponent Stats (Belt: {opp_belt.capitalize()})**")
        st.progress(o_stats.get('offense', 0)/100, text=f"⚔️ Offense: {o_stats.get('offense', 0)}%")
        st.progress(o_stats.get('defense', 0)/100, text=f"🛡️ Defense: {o_stats.get('defense', 0)}%")
        st.progress(o_stats.get('guard', 0)/100, text=f"🔒 Guard: {o_stats.get('guard', 0)}%")
        st.progress(o_stats.get('passing', 0)/100, text=f"🏃 Passing: {o_stats.get('passing', 0)}%")

    st.markdown("### ⏱️ 5-SECOND INTERVAL BREAKDOWN")
    df_intervals = pd.DataFrame(result.get("interval_breakdown", []))
    if not df_intervals.empty:
        st.dataframe(df_intervals, use_container_width=True, hide_index=True)

    st.markdown("### ✅ STRENGTHS & ⚠️ WEAKNESSES")
    tab1, tab2 = st.tabs(["Your Stats", "Opponent Stats"])
    
    with tab1:
        s_col, w_col = st.columns(2)
        with s_col:
            st.markdown("#### ✅ YOUR STRENGTHS")
            for s in result.get("user_strengths", []): st.markdown(f"<div class='strength-card'>✓ {s}</div>", unsafe_allow_html=True)
        with w_col:
            st.markdown("#### ⚠️ YOUR WEAKNESSES")
            for w in result.get("user_weaknesses", []): st.markdown(f"<div class='weakness-card'>X {w}</div>", unsafe_allow_html=True)
            
    with tab2:
        s_col2, w_col2 = st.columns(2)
        with s_col2:
            st.markdown("#### ✅ OPPONENT STRENGTHS")
            for s in result.get("opponent_strengths", []): st.markdown(f"<div class='strength-card'>✓ {s}</div>", unsafe_allow_html=True)
        with w_col2:
            st.markdown("#### ⚠️ OPPONENT WEAKNESSES")
            for w in result.get("opponent_weaknesses", []): st.markdown(f"<div class='weakness-card'>X {w}</div>", unsafe_allow_html=True)

    st.markdown("### 💡 OPPORTUNITIES MISSED")
    for opp in result.get("missed_opportunities", []):
        st.info(f"**{opp.get('time')} | {opp.get('category')} - {opp.get('title')}**: {opp.get('description')}")

    st.markdown("### ⭐ KEY MOMENTS")
    for km in result.get("key_moments", []):
        with st.expander(f"⏱️ {km.get('time')} - {km.get('title')}"):
            st.write(km.get('description'))

    st.markdown("### 🧑‍🏫 COACH'S INSIGHTS")
    st.markdown(f"<div class='coach-card'>{result.get('coach_notes', '')}</div>", unsafe_allow_html=True)

    st.markdown("---")
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        csv_data = generate_interval_csv(result.get("interval_breakdown", []))
        st.download_button("📊 Download 5-Sec Interval CSV", data=csv_data, file_name="bjj_intervals.csv", mime="text/csv", use_container_width=True)
    with dl_col2:
        # Pass the filename to the generator
        pdf_bytes = generate_pdf_report(result, filename=uploaded_file.name)
        
        # Make the downloaded file name dynamic too!
        safe_name = uploaded_file.name.split('.')[0]
        st.download_button("📄 Download Full PDF Report", data=pdf_bytes, file_name=f"Report_{safe_name}.pdf", mime="application/pdf", use_container_width=True)