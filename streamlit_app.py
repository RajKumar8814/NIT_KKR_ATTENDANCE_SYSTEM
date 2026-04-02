import streamlit as st
import cv2
import numpy as np
from PIL import Image
import os

# Page Config
st.set_page_config(page_title="NIT KKR Attendance System", layout="centered")

st.title("🎓 NIT KKR Attendance System")
st.write("Welcome to the Smart Attendance Portal")

# Sidebar for Navigation
menu = ["Take Attendance", "Admin Login", "View Records"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Take Attendance":
    st.subheader("Face Recognition Attendance")
    
    # Streamlit ka inbuilt camera component use karenge jo har browser par chalta hai
    img_file = st.camera_input("Smile for the camera!")

    if img_file is not None:
        st.success("Image captured! Processing...")
        # Yahan hum aapke face_recognition logic ko call karenge
        # (Abhi ke liye ye bas UI setup hai)

elif choice == "Admin Login":
    st.subheader("Staff Portal")
    user = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        st.info("Authenticating via MongoDB...")

elif choice == "View Records":
    st.subheader("Attendance Logs")
    st.write("Connecting to Database...")
    # Yahan MongoDB se data fetch hoke table dikhega