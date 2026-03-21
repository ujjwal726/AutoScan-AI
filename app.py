import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan AI", page_icon="🚗", layout="centered")
st.title("🚗 AutoScan AI")
st.markdown("### ⚡ Fast Damage & Insurance Verdict")
st.caption("AI-Powered Surveyor • 2026 Nashik Rates • Genuine Parts")

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
        st.error(f"Environment Error: {e}")
        st.stop()

    # --- INPUT SECTION ---
    uploaded_file = st.file_uploader("Upload damage photo", type=["jpg", "jpeg", "png"])
    
    col1, col2 = st.columns(2)
    with col1:
        premium = st.number_input("Annual Premium (₹)", value=22000, step=500)
    with col2:
        ncb = st.slider("NCB %", 0, 50, 25, step=5)

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Damage Analysis in Progress...", use_container_width=True)

        if st.button("GET VERDICT"):
            with st.spinner("Calculating Financial Impact..."):
                # CRISP & AUTHORITATIVE PROMPT
                prompt = f"""
                Act as a Precise Auto Surveyor. Analyze this photo.
                Output ONLY this structure:
                
                ### 🛠️ Damage Summary
                - **Vehicle:** [Model Name]
                - **Severity:** [Low/Med/High]
                - **Primary Damage:** [1-sentence description]

                ### 📊 Cost Breakdown (2026 Nashik Rates)
                | Component | Estimated Cost (INR) |
                | :--- | :--- |
                | Genuine Spare Part | [Cost] |
                | Painting & Finishing | [Cost] |
                | Fitting/Labor | [Cost] |
                | **Total Out-of-Pocket** | **₹[Sum]** |

                ### ⚖️ Insurance Math
                - **Claim Value:** ₹[Total - 1000 deductible]
                - **NCB Loss:** ₹{premium * (ncb/100)} (Next year's premium hike)

                # FINAL VERDICT: [GO FOR CLAIM / GO FOR CASH]
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    
                    st.markdown("---")
                    st.markdown(response.text)
                    
                    # --- AUTHORITY VALIDATION SECTION ---
                    st.markdown("### 🔗 Validate These Rates")
                    st.info("Check official 2026 prices for your specific variant:")
                    v_col1, v_col2 = st.columns(2)
                    with v_col1:
                        st.link_button("Official Maruti Parts", "https://www.marutisuzuki.com/genuine-parts")
                    with v_col2:
                        st.link_button("Boodmo Live Catalog", "https://boodmo.com/vehicles/maruti-286/")
                    
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
else:
    st.warning("Sidebar: Enter Gemini API Key to activate.")
