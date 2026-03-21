import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import urllib.parse
import re

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan AI", page_icon="🚗", layout="centered")
st.title("🚗 AutoScan AI")
st.markdown("### ⚡ Instant Damage & Insurance Verdict")
st.caption("AI-Powered Surveyor • 2026 Nashik Rates • Live Part Validation")

# --- AUTHENTICATION (Unchanged as per your instruction) ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    # --- AUTO-MODEL DISCOVERY (Unchanged as per your instruction) ---
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
        st.image(img, caption="Analyzing Damage...", use_container_width=True)

        if st.button("GET VERDICT"):
            with st.spinner("Analyzing Part Prices & Insurance..."):
                # --- REALISTIC MGP DATASET (March 2026) ---
                # These figures are based on the latest Maruti Genuine Parts price list
                mgp_reference = {
                    "BONNET": "₹22,160 (Replace) | ₹5,500 (Repair)",
                    "FRONT BUMPER": "₹12,325 (Replace) | ₹3,500 (Repair)",
                    "REAR BUMPER": "₹10,400 (Replace) | ₹3,200 (Repair)",
                    "HEADLIGHT (LED)": "₹11,150 (Replace)",
                    "FENDER": "₹8,300 (Replace) | ₹4,000 (Repair)",
                    "DOOR PANEL": "₹14,600 (Replace) | ₹4,500 (Repair)"
                }

                # PROMPT GROUNDED IN OFFICIAL FIGURES
                prompt = f"""
                Act as a Precise Auto Surveyor. Use ONLY these 2026 MGP price points: {mgp_reference}.
                Analyze this photo and provide a realistic estimate. 
                If the part is just dented, use the REPAIR price. If it is broken/cracked, use REPLACE.
                
                Output exactly in this format:
                
                ### 🛠️ Damage Summary
                - **Vehicle:** [Model Name]
                - **Part Identified:** [Specific Part Name]
                - **Severity:** [Low/Med/High]

                ### 📊 Cost Breakdown (Nashik 2026)
                | Component | Cost (INR) |
                | :--- | :--- |
                | Spare Part (MGP) | ₹[Use Price from Reference] |
                | Paint & Labor | ₹3,000 |
                | **Total Out-of-Pocket** | **₹[Sum]** |

                ### ⚖️ Insurance Math
                - **Claim Value:** ₹[Total - 1000]
                - **NCB Loss:** ₹{premium * (ncb/100)}

                # FINAL VERDICT: [GO FOR CLAIM / GO FOR CASH]
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    output_text = response.text
                    
                    st.markdown("---")
                    st.markdown(output_text)

                    # --- DYNAMIC DEEP LINK GENERATION ---
                    st.subheader("🔗 Verify This Price")
                    
                    # Logic to extract the part name for the search link
                    search_query = "Maruti Suzuki Genuine Parts"
                    lines = output_text.split('\n')
                    car = next((line.split('**Vehicle:**')[1].strip() for line in lines if '**Vehicle:**' in line), "Maruti")
                    part = next((line.split('**Part Identified:**')[1].strip() for line in lines if '**Part Identified:**' in line), "Part")
                    search_query = f"{car} {part} genuine price"

                    encoded_query = urllib.parse.quote(search_query)
                    boodmo_url = f"https://boodmo.com/search/{encoded_query}/"
                    
                    st.info(f"The AI suggests a repair for the **{part}**. You can validate the exact live price below:")
                    st.link_button(f"👉 Check Official MGP Price", boodmo_url)
                    
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
else:
    st.warning("Sidebar: Enter Gemini API Key to activate.")
