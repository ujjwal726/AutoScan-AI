import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import pandas as pd

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan AI", page_icon="🚗", layout="centered")
st.title("🚗 AutoScan AI")
st.markdown("### 60-Second Car Damage & Insurance Consultant")
st.info("Identify damage and get an instant Claim vs. Cash verdict.")

# --- AUTHENTICATION ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    # --- AUTO-MODEL DISCOVERY ---
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_model = next((m for m in available_models if 'flash' in m), "gemini-1.5-flash")
        model = genai.GenerativeModel(flash_model)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

    # --- INPUT SECTION ---
    uploaded_file = st.file_uploader("Upload a photo of the damage", type=["jpg", "jpeg", "png"])
    
    col1, col2 = st.columns(2)
    with col1:
        premium = st.number_input("Annual Premium (₹)", value=22000, step=500)
    with col2:
        ncb = st.slider("Current NCB %", 0, 50, 25, step=5)

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Damage Preview", use_container_width=True)

        if st.button("Analyze & Advise"):
            with st.spinner("AI Surveyor is calculating..."):
                # REFINED PROMPT FOR STRUCTURED OUTPUT
                prompt = f"""
                Act as a Senior Motor Insurance Surveyor for the Indian market. 
                Analyze this car damage photo and provide a structured report.

                1. IDENTIFICATION: Brand/Model and Damage Severity.
                2. REPAIR ESTIMATE: List parts needed and 2026 Nashik labor rates.
                3. FINANCIAL LOGIC:
                   - Total Repair Cost (R)
                   - Claim Value = R - ₹1,000 (Deductible)
                   - NCB Loss = ₹{premium * (ncb/100)} (Based on {ncb}% of ₹{premium})
                4. FINAL VERDICT: Must be "GO FOR CLAIM" or "GO FOR CASH".
                
                Keep the tone professional and the math crystal clear.
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    
                    st.success("Analysis Complete!")
                    st.subheader("📋 Surveyor's Report")
                    st.markdown(response.text)
                    
                    st.divider()
                    st.caption("Disclaimer: Estimates are AI-generated based on 2026 Nashik market averages. Final costs may vary at authorized workshops.")
                    
                except Exception as e:
                    st.error(f"Analysis Failed: {e}")
else:
    st.warning("Please enter your API Key in the sidebar or add it to Streamlit Secrets.")
