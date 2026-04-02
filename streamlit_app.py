import streamlit as st
import subprocess
import sys
import time

st.set_page_config(page_title="NIT KKR Attendance System", layout="wide")

st.title("🚀 NIT KKR Attendance System")

# Flask ko background mein chalane ka logic
if 'flask_process' not in st.session_state:
    with st.spinner("Starting Backend Engine..."):
        proc = subprocess.Popen([sys.executable, "app.py"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.STDOUT)
        st.session_state.flask_process = proc
        time.sleep(10) # Server ko fully load hone dein

# SABSE ZAROORI: Flask app ko Streamlit ke andar dikhana
st.success("Backend is Active!")
st.write("Checking connection...")

# Ye line aapke Flask app (port 8501 ya 5000) ko iframe mein load karegi
st.components.v1.iframe("http://localhost:8501", height=800, scrolling=True)

st.info("Agar upar page load nahi ho raha, toh ye aapke local port par chal raha hai. Deploy link check karein.")