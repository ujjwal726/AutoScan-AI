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
        # Dynamically find the best available model
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
        Keep it simple. Write the Date, Description, and Amount. No names, no UPI IDs.
        
        *Example:*
        * **12-March | Zomato | 450**
        * **14-March | Amazon Jacket | 1200**
        * **15-March | Petrol | 2000**
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
                    
                    st.success("✅ Ledger Digitized Successfully!")
                    st.dataframe(df_vision)
                    
                    csv_buffer = io.StringIO()
                    df_vision.to_csv(csv_buffer, index=False)
                    st.download_button("⬇️ Download Clean CSV for Step 2", data=csv_buffer.getvalue(), file_name="secure_expenses.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Error reading image: Please ensure your handwriting is clear and try again. ({e})")

# ==========================================
# TAB 2: THE WEALTH ENGINE
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    st.write("Upload the clean CSV you just downloaded from Step 1.")
    clean_file = st.file_uploader("Upload Digitized Data (CSV)", type=["csv"], key="clean_upload")
    
    if clean_file:
        df = pd.read_csv(clean_file)
        
        st.subheader("1. Triage Your Spending")
        st.caption("Double-click the 'Tag' column to honestly label your transactions as a Need or a Desire.")
        
        edited_df = st.data_editor(
            df,
            column_config={
                "Tag": st.column_config.SelectboxColumn("Tag", options=["Need", "Desire", "Uncategorized"], required=True)
            },
            use_container_width=True
        )
        
        if "Amount" in edited_df.columns:
            edited_df['Amount'] = pd.to_numeric(edited_df['Amount'], errors='coerce').fillna(0)
            desires_df = edited_df[edited_df["Tag"] == "Desire"]
            total_desire_spend = desires_df["Amount"].sum()
            
            st.divider()
            st.subheader("2. Opportunity Cost Math")
            rate = 0.12 
            years = 10
            future_value = total_desire_spend * ((1 + rate) ** years)
            
            col1, col2 = st.columns(2)
            col1.metric("Total 'Desire' Spend", f"₹{total_desire_spend:,.2f}")
            col2.metric("10-Year Opportunity Cost (12% CAGR)", f"₹{future_value:,.2f}", delta=f"+₹{future_value - total_desire_spend:,.2f}")
            
            st.divider()
            st.subheader("3. AI Wealth Strategist")
            
            if not desires_df.empty and model:
                desc_col = 'Description' if 'Description' in desires_df.columns else desires_df.columns[1]
                options = desires_df.apply(lambda row: f"₹{row['Amount']} on {row.get(desc_col, 'Item')}", axis=1).tolist()
                selected_trans = st.selectbox("Select a 'Desire' transaction to analyze:", options)
                
                if st.button("Generate Investment Alternatives"):
                    amount_match = float(selected_trans.split("₹")[1].split(" ")[0].replace(',', ''))
                    with st.spinner("Consulting AI..."):
                        prompt = f"""
                        A user spent ₹{amount_match} on a non-essential item. 
                        Provide 3 concrete, actionable investment or wealth-building alternatives for exactly ₹{amount_match} in India.
                        Format as a numbered list. Keep reasons brief. End with a 1-sentence macro recommendation.
                        """
                        try:
                            st.markdown(model.generate_content(prompt).text)
                        except Exception as e:
                            st.error(f"API Error: {e}")
        else:
            st.error("No 'Amount' column found in the uploaded data. Please ensure the extraction was successful.")

# ==========================================
# TAB 3: THE INTERCEPTOR
# ==========================================
with tab3:
    st.header("Step 3: The Pre-Spend Interceptor")
    st.write("About to make an impulse purchase online? Run it through the engine first.")
    with st.container(border=True):
        item_name = st.text_input("What are you about to buy?")
        item_price = st.number_input("Price (₹)", min_value=0, step=100)
        
        if st.button("Evaluate Purchase", type="primary") and model and item_price > 0:
            fv = item_price * ((1 + 0.12) ** 10)
            st.error(f"⚠️ **Wait!** That ₹{item_price:,.2f} today will cost you **₹{fv:,.2f}** in 10 years.")
            
            with st.spinner("Finding better uses for this capital..."):
                prompt2 = f"A user is about to spend ₹{item_price} on '{item_name}'. Provide 2 concrete investment alternatives in India, and 1 psychological question to reconsider the purchase."
                try:
                    st.markdown("---")
                    st.markdown(model.generate_content(prompt2).text)
                except Exception as e:
                    st.error(f"API Error: {e}")
