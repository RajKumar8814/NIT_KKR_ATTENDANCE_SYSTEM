import streamlit as st
import subprocess
import sys
import time

st.title("NIT KKR Attendance System - Server")
st.write("Flask server is starting...")

# Flask app ko background mein chalane ke liye
if 'process' not in st.session_state:
    with st.spinner("Starting Flask Backend..."):
        proc = subprocess.Popen([sys.executable, "app.py"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.STDOUT)
        st.session_state.process = proc
        time.sleep(5) # Server ko uthne ka time dein

st.success("Server is Live!")
st.write("Note: Streamlit might not show the HTML directly. Check the logs for the local URL.")