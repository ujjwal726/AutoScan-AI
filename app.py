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
    
    st.error("🔒 **ZERO-TRUST PROTOCOL:** Do NOT upload official bank statements or screenshots of your banking apps. We do not want your personal data.")
    
    st.write("To guarantee your absolute privacy, please write your expenses on a physical piece of paper and upload a photo of it. Our Vision AI will digitize it instantly.")
    
    with st.container(border=True):
        st.markdown("""
        **📝 How to format your paper ledger:**
        Keep it simple. Write the Date, Description, and Amount. No names, no personal IDs.
        
        *Example:*
        * **12-March | Zomato (Burger) | 450**
        * **14-March | Amazon | 15000**
        * **15-March | Salary | 50000**
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
                    Do not include any markdown formatting like ```csv. Just the raw text.
                    """
                    response = model.generate_content([vision_prompt, image])
                    clean_csv_text = response.text.replace("```csv\n", "").replace("```", "").strip()
                    
                    df_vision = pd.read_csv(io.StringIO(clean_csv_text))
                    df_vision["Tag"] = "Uncategorized"
                    df_vision["Context"] = "" # Pre-load the context column for Step 2
                    
                    st.success("✅ Ledger Digitized Successfully!")
                    st.dataframe(df_vision)
                    
                    csv_buffer = io.StringIO()
                    df_vision.to_csv(csv_buffer, index=False)
                    st.download_button("⬇️ Download Clean CSV for Step 2", data=csv_buffer.getvalue(), file_name="secure_expenses.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Error reading image: Please ensure your handwriting is clear and try again. ({e})")

# ==========================================
# TAB 2: THE WEALTH ENGINE (V1.7 WITH USER DEFENSE)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    st.write("Upload the clean CSV you just downloaded from Step 1.")
    clean_file = st.file_uploader("Upload Digitized Data (CSV)", type=["csv"], key="clean_upload")
    
    if clean_file:
        if "last_processed_file" not in st.session_state or st.session_state.last_processed_file != clean_file.name:
            df = pd.read_csv(clean_file)
            
            if 'Tag' not in df.columns:
                df['Tag'] = "Uncategorized"
            if 'Context' not in df.columns:
                df['Context'] = "" # Add blank context column if it's missing
                
            if model and "Description" in df.columns:
                with st.spinner("✨ AI is pre-reading your transactions and auto-tagging them..."):
                    try:
                        desc_list = df['Description'].tolist()
                        tag_prompt = f"""
                        Categorize these transactions into exactly one of these 4 tags: Need, Desire, Salary, Income.
                        Transactions: {desc_list}
                        Return ONLY a comma-separated list of tags in the exact order. No extra text or markdown.
                        """
                        tag_response = model.generate_content(tag_prompt)
                        tags = [t.strip().strip("'").strip('"') for t in tag_response.text.split(',')]
                        
                        if len(tags) == len(df):
                            df['Tag'] = tags
                    except Exception:
                        pass 
            
            st.session_state.auto_tagged_df = df
            st.session_state.last_processed_file = clean_file.name

        st.subheader("1. Financial Triage & Clarification")
        st.info("💡 **Your Turn:** Review the auto-tags. If you have an unusually large expense (like ₹15,000 on Amazon), type a quick note in the **'Context'** column so the AI knows what it was before it judges the market rate.")
        
        # The updated editor now includes the Context column
        edited_df = st.data_editor(
            st.session_state.auto_
