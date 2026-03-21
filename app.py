import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan AI", page_icon="🚗")
st.title("🚗 AutoScan AI")
st.markdown("### 60-Second Car Damage & Insurance Consultant")

# --- AUTHENTICATION (The "Secret" Way) ---
# This looks for the key in Streamlit Cloud Secrets first
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    # This allows you to still use a sidebar if the secret isn't set yet
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    # --- AUTO-MODEL DISCOVERY (This fixes your error!) ---
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
        premium = st.number_input("Annual Premium (INR)", value=22000)
    with col2:
        ncb = st.slider("Current NCB %", 0, 50, 25)

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Damage Preview", use_container_width=True)

        if st.button("Analyze & Advise"):
            with st.spinner("AI Surveyor is calculating..."):
                prompt = f"""
                Analyze this car damage for the Indian market.
                1. Identify Car Model and Damage Severity.
                2. Estimate Repair Cost (Parts + Nashik Labor) in INR.
                3. Compare (Cost - 1000) vs NCB Loss of ₹{premium * (ncb/100)}.
                4. Give a Bold Recommendation: 'GO FOR CLAIM' or 'GO FOR CASH'.
                """
                try:
                    response = model.generate_content([prompt, img])
                    st.subheader("📋 Final Verdict")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Analysis Failed: {e}")
else:
    st.info("Waiting for API Key. Add it to 'Secrets' in Streamlit settings or enter it in the sidebar.")
