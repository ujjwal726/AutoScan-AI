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
        Keep it simple. Write the Date, Description, and Amount. No names, no UPI IDs.
        
        *Example:*
        * **12-March | Zomato (Burger) | 450**
        * **14-March | Amazon Jacket | 1200**
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
                    
                    st.success("✅ Ledger Digitized Successfully!")
                    st.dataframe(df_vision)
                    
                    csv_buffer = io.StringIO()
                    df_vision.to_csv(csv_buffer, index=False)
                    st.download_button("⬇️ Download Clean CSV for Step 2", data=csv_buffer.getvalue(), file_name="secure_expenses.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Error reading image: Please ensure your handwriting is clear and try again. ({e})")

# ==========================================
# TAB 2: THE WEALTH ENGINE (V1.5 OVERHAUL)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    st.write("Upload the clean CSV you just downloaded from Step 1.")
    clean_file = st.file_uploader("Upload Digitized Data (CSV)", type=["csv"], key="clean_upload")
    
    if clean_file:
        df = pd.read_csv(clean_file)
        
        st.subheader("1. Financial Triage")
        st.info("💡 **Instructions:** Double-click the 'Tag' column to label your transactions. Use **Need** (essentials), **Desire** (wants/cravings), **Salary**, or **Income**.")
        
        edited_df = st.data_editor(
            df,
            column_config={
                "Tag": st.column_config.SelectboxColumn(
                    "Tag", 
                    options=["Need", "Desire", "Salary", "Income", "Uncategorized"], 
                    required=True
                )
            },
            use_container_width=True
        )
        
        if "Amount" in edited_df.columns:
            edited_df['Amount'] = pd.to_numeric(edited_df['Amount'], errors='coerce').fillna(0)
            
            # Filter Desires
            desires_df = edited_df[edited_df["Tag"] == "Desire"]
            total_desire_spend = desires_df["Amount"].sum()
            
            st.divider()
            st.subheader("2. The 'Desire' Leakage & 1-Year SIP Potential")
            
            # --- MATH: 1-Year SIP Calculation (Moderate Risk ~12% Annual) ---
            # Assuming the uploaded ledger represents a typical month
            monthly_rate = 0.12 / 12
            months = 12
            # Standard SIP FV Formula
            sip_fv = total_desire_spend * (((1 + monthly_rate)**months - 1) / monthly_rate) * (1 + monthly_rate)
            
            col1, col2 = st.columns(2)
            col1.metric("Total Monthly 'Desire' Spend", f"₹{total_desire_spend:,.2f}")
            col2.metric("If Saved Monthly for 1 Year (12% SIP)", f"₹{sip_fv:,.2f}", delta=f"Wealth Created: +₹{sip_fv - (total_desire_spend * 12):,.2f}")
            
            st.divider()
            st.subheader("3. Deep Behavioral Analysis")
            
            if st.button("Generate Opportunity Cost Table & Pattern Analysis", type="primary") and model:
                if total_desire_spend == 0:
                    st.success("Incredible discipline! You have zero 'Desire' spending logged. Keep investing the surplus.")
                else:
                    with st.spinner("Analyzing transaction DNA and calculating micro-opportunity costs..."):
                        # Convert the dataframe to a string to send to the AI
                        csv_data = edited_df[['Description', 'Amount', 'Tag']].to_csv(index=False)
                        
                        prompt = f"""
                        You are an expert financial and behavioral analyst in India.
                        Here is the user's categorized spending data for this period:
                        {csv_data}
                        
                        Total Monthly Desire Spend: ₹{total_desire_spend}
                        Future Value of these Desires invested in a monthly SIP for 1 year: ₹{sip_fv:,.2f}
                        
                        Please format your response EXACTLY into these 3 sections:
                        
                        ### 🔍 1. Micro-Opportunity Costs
                        Create a crisp Markdown table ONLY for transactions tagged as "Desire". 
                        For EACH desire, provide 3 highly specific, similarly-priced, and pragmatic alternative uses for that exact amount of money (e.g., if it's ₹200, suggest things like 'Half-month broadband', 'Tank of petrol', 'Protein-rich groceries', 'Term insurance premium').
                        Columns must be: Description | Amount (₹) | Viable Alternative 1 | Viable Alternative 2 | Viable Alternative 3
                        
                        ### 🎯 2. The 1-Year Tangible Upgrade
                        Based on their 1-Year SIP Future Value of ₹{sip_fv:,.2f}, suggest EXACTLY ONE tangible, high-value, life-enriching purchase or experience they could buy a year from now if they saved this money instead. Make it specific to the Indian context (e.g., a specific trip, a gadget, an upskilling course).
                        
                        ### 🧠 3. Behavioral Pattern & Verdict
                        Analyze the descriptions of their 'Desire' spending. 
                        - Identify their core spending trigger in ONE sentence. 
                        - If you notice a trend toward unhealthy habits (e.g., lots of sugary/salty foods, fast food), explicitly flag the health risk in ONE sentence.
                        - Give ONE sentence of actionable advice to shift to a better lifestyle/financial habit.
                        """
                        try:
                            response = model.generate_content(prompt)
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"API Error: {e}")
        else:
            st.error("No 'Amount' column found in the uploaded data.")

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
