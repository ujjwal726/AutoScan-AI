import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
from PIL import Image

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="WealthTrace AI", page_icon="📈", layout="wide")
st.title("📈 WealthTrace AI")
st.markdown("### The Zero-Trust Opportunity Cost Engine")

# --- AUTHENTICATION & DYNAMIC MODEL SELECTION ---
model = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if 'models/gemini-1.5-flash' in available_models:
            target_model = 'gemini-1.5-flash'
        elif 'models/gemini-1.5-flash-latest' in available_models:
            target_model = 'gemini-1.5-flash-latest'
        elif 'models/gemini-pro-vision' in available_models:
            target_model = 'gemini-pro-vision'
        elif available_models:
            target_model = available_models[0].replace('models/', '')
        else:
            target_model = 'gemini-1.5-flash'
            
        model = genai.GenerativeModel(target_model)
        st.sidebar.success(f"🟢 Secured Connection: {target_model.replace('models/', '')}")
    except Exception as e:
        st.sidebar.error(f"Connection Error: {e}")
else:
    st.sidebar.warning("API Key required to run the AI Wealth Engine.")

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["📸 1. Secure Ledger Upload", "🧠 2. The Wealth Engine", "🛑 3. Pre-Spend Interceptor"])

# ==========================================
# TAB 1: DATA INGESTION (Analog Air-Gap ONLY)
# ==========================================
with tab1:
    st.header("Step 1: Digitize Your Paper Ledger")
    
    st.error("🔒 **ZERO-TRUST PROTOCOL:** Do NOT upload official bank statements or screenshots of your banking apps.")
    
    st.write("To guarantee absolute privacy, write your expenses on paper and upload a photo. Our Vision AI will digitize it instantly.")
    
    with st.container(border=True):
        st.markdown("""
        **📝 Format Example:**
        * 12-March | Zomato (Burger) | 450
        * 14-March | Amazon Jacket | 8500
        * 15-March | Salary | 50000
        """)
        
    st.divider()
    
    photo_file = st.file_uploader("Upload Photo of Handwritten Ledger (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if photo_file and model:
        image = Image.open(photo_file)
        st.image(image, caption="Your Secure Ledger", width=500)
        
        if st.button("Extract Data", type="primary"):
            with st.spinner("Digitizing handwriting..."):
                try:
                    vision_prompt = """
                    Extract the transactions from this handwritten image. 
                    Output strictly as a valid CSV with three columns: Date, Description, Amount.
                    Do not use commas inside the text fields. Ensure amounts are purely numbers.
                    Do not include markdown. Just raw text.
                    """
                    response = model.generate_content([vision_prompt, image])
                    clean_csv_text = response.text.replace("```csv\n", "").replace("```", "").strip()
                    
                    df_vision = pd.read_csv(io.StringIO(clean_csv_text))
                    df_vision["Tag"] = "Uncategorized"
                    
                    st.success("✅ Ledger Digitized Successfully!")
                    st.dataframe(df_vision)
