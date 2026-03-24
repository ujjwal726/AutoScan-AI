import streamlit as st
import google.generativeai as genai

# Setup the page
st.set_page_config(page_title="AI Manager: Phase 1", layout="centered")
st.title("🚀 Phase 1: Ignition (Model 2.5 Flash)")

# Sidebar for the API Key
st.sidebar.header("Settings")
user_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if user_key:
    try:
        # Link the key to the library
        genai.configure(api_key=user_key)
        
        # We specify the exact model you want: gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Test the connection
        response = model.generate_content("Hello! Are you Gemini 2.5 Flash?")
        
        st.sidebar.success("✅ Key Validated!")
        st.balloons()
        
        st.write("### System Status: Online")
        st.success(f"Response from AI: {response.text}")
        st.info("The 2.5 Flash engine is warmed up. Ready for the next task.")

    except Exception as e:
        # This will tell us EXACTLY why it failed
        st.sidebar.error(f"❌ Error: {e}")
        st.write("### 🔍 Diagnostic Info")
        st.write("If you see an error about 'Model not found', it might be because your key doesn't have access to 2.5 Flash yet. Check the error message in the sidebar.")
else:
    st.info("Waiting for API Key in the sidebar...")
