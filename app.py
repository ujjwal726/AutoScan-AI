import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import urllib.parse

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan AI", page_icon="🚗", layout="centered")
st.title("🚗 AutoScan AI")
st.markdown("### ⚡ Instant Damage & Insurance Verdict")
st.caption("AI-Powered Surveyor • 2026 Nashik Rates • Live Part Validation")

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
        st.image(img, caption="Analyzing Damage...", use_container_width=True)

        if st.button("GET VERDICT"):
            with st.spinner("Analyzing Part Prices & Insurance..."):
                # PROMPT DESIGNED FOR DYNAMIC LINK EXTRACTION
                prompt = f"""
                Act as a Precise Auto Surveyor. Analyze this photo.
                Output exactly in this JSON-style structure (but in Markdown):
                
                ### 🛠️ Damage Summary
                - **Vehicle:** [Model Name]
                - **Part Identified:** [Specific Part Name]
                - **Severity:** [Low/Med/High]

                ### 📊 Cost Breakdown (Nashik 2026)
                | Component | Cost (INR) |
                | :--- | :--- |
                | Spare Part (MGP) | ₹[Cost] |
                | Paint & Labor | ₹[Cost] |
                | **Total Out-of-Pocket** | **₹[Sum]** |

                ### ⚖️ Insurance Math
                - **Claim Value:** ₹[Total - 1000]
                - **NCB Loss:** ₹{premium * (ncb/100)}

                # FINAL VERDICT: [GO FOR CLAIM / GO FOR CASH]
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    output_text = response.text
                    
                    # --- DISPLAY REPORT ---
                    st.markdown("---")
                    st.markdown(output_text)

                    # --- DYNAMIC DEEP LINK GENERATION ---
                    # We extract the car and part names to create a direct search link
                    st.subheader("🔗 Verify This Price")
                    
                    # AI might provide different text, so we'll look for keywords
                    # This is a simplified logic for our MVP
                    search_query = f"Maruti Suzuki Genuine Parts"
                    if "Vehicle:" in output_text and "Part Identified:" in output_text:
                        # Extracting info for the link
                        lines = output_text.split('\n')
                        car = next((line.split('**Vehicle:**')[1].strip() for line in lines if '**Vehicle:**' in line), "Maruti")
                        part = next((line.split('**Part Identified:**')[1].strip() for line in lines if '**Part Identified:**' in line), "Bumper")
                        search_query = f"{car} {part} genuine price"

                    encoded_query = urllib.parse.quote(search_query)
                    boodmo_url = f"https://boodmo.com/search/{encoded_query}/"
                    
                    st.info(f"The AI detected a **{search_query}**. Validate the current market price below:")
                    st.link_button(f"👉 Check Price for {part}", boodmo_url)
                    
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
else:
    st.warning("Sidebar: Enter Gemini API Key to activate.")
