import streamlit as st
import subprocess
import sys
import time
import os

st.set_page_config(page_title="NIT KKR Attendance System", layout="wide")

st.title("🚀 NIT KKR Attendance System")

# Flask ko background mein chalane ka logic
if 'flask_process' not in st.session_state:
    with st.spinner("Starting Backend Engine..."):
        # Port 5000 par Flask chalate hain (standard)
        proc = subprocess.Popen([sys.executable, "app.py"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.STDOUT)
        st.session_state.flask_process = proc
        time.sleep(12) # Wait for Flask to boot

st.success("Backend is Active!")

# Yahan '0.0.0.0' use karenge cloud environment ke liye
st.components.v1.iframe("http://0.0.0.0:5000", height=800, scrolling=True)

st.warning("⚠️ Agar login page nahi dikh raha, toh refresh karein ya logs check karein.")