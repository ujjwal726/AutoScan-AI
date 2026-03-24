import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="AI Resource Manager", layout="centered")

st.title("🚀 Phase 1: The Ignition")
st.sidebar.header("Settings")

# User enters their key here
user_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if user_key:
    try:
        genai.configure(api_key=user_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        # We test the key with a simple "Hello"
        response = model.generate_content("Hello")
        
        st.sidebar.success("✅ Key Validated!")
        st.balloons()
        st.write("### Status: System Online")
        st.info("The engine is running. We are ready for Phase 2.")
        
    except Exception as e:
        st.sidebar.error(f"❌ Error: {e}")
else:
    st.warning("Please enter your API Key in the sidebar to proceed.")
