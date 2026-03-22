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
        target_model = 'gemini-1.5-flash'
        if 'models/gemini-1.5-flash' not in available_models:
            if available_models:
                target_model = available_models[0].replace('models/', '')
        
        model = genai.GenerativeModel(target_model)
        st.sidebar.success(f"🟢 Secured Connection: {target_model}")
    except Exception as e:
        st.sidebar.error(f"Connection Error: {e}")
else:
    st.sidebar.warning("API Key required to run the AI Wealth Engine.")

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["📸 1. Secure Ledger Upload", "🧠 2. The Wealth Engine", "🛑 3. Pre-Spend Interceptor"])

# ==========================================
# TAB 1: DATA INGESTION
# ==========================================
with tab1:
    st.header("Step 1: Digitize Your Paper Ledger")
    st.error("🔒 **ZERO-TRUST PROTOCOL:** Do NOT upload official statements. Hand-written paper notes only.")
    
    with st.container(border=True):
        st.markdown("**📝 Example:** 12-March | Zomato (Burger) | 450")
        
    photo_file = st.file_uploader("Upload Photo (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if photo_file and model:
        image = Image.open(photo_file)
        st.image(image, caption="Your Secure Ledger", width=500)
        
        if st.button("Extract Data", type="primary"):
            with st.spinner("Digitizing handwriting..."):
                try:
                    vision_prompt = "Extract transactions. Output ONLY raw CSV: Date, Description, Amount. No markdown."
                    response = model.generate_content([vision_prompt, image])
                    clean_csv_text = response.text.replace("```csv\n", "").replace("```", "").strip()
                    df_vision = pd.read_csv(io.StringIO(clean_csv_text))
                    
                    # Ensure columns exist and add placeholders
                    df_vision["Tag"] = "Uncategorized"
                    df_vision["Context"] = ""
                    
                    st.success("✅ Ledger Digitized!")
                    st.dataframe(df_vision)
                    
                    csv_buffer = io.StringIO()
                    df_vision.to_csv(csv_buffer, index=False)
                    st.download_button("⬇️ Download Clean CSV", data=csv_buffer.getvalue(), file_name="secure_expenses.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# TAB 2: THE WEALTH ENGINE (V1.7.1 STABLE)
# ==========================================
with tab2:
    st.header("Step 2: Tag & Analyze")
    clean_file = st.file_uploader("Upload Digitized Data (CSV)", type=["csv"], key="clean_upload")
    
    if clean_file:
        # Load file and initialize state if needed
        if "auto_tagged_df" not in st.session_state or st.session_state.get("last_file") != clean_file.name:
            df = pd.read_csv(clean_file)
            
            # 1. Clean data basics
            for col in ["Tag", "Context"]:
                if col not in df.columns:
                    df[col] = "" if col == "Context" else "Uncategorized"
            
            # 2. Robust Auto-Tagging
            if model and "Description" in df.columns:
                with st.spinner("✨ AI Auto-Tagging..."):
                    try:
                        desc_list = df['Description'].astype(str).tolist()
                        tag_prompt = f"Categorize into exactly one: Need, Desire, Salary, Income. List: {desc_list}. Return ONLY comma-separated tags."
                        res = model.generate_content(tag_prompt).text.split(',')
                        
                        # Use list comprehension with index safety
                        clean_tags = [t.strip().title() for t in res]
                        valid_tags = ["Need", "Desire", "Salary", "Income"]
                        
                        # Apply tags only where they exist and match valid options
                        final_tags = []
                        for i in range(len(df)):
                            if i < len(clean_tags) and clean_tags[i] in valid_tags:
                                final_tags.append(clean_tags[i])
                            else:
                                final_tags.append("Uncategorized")
                        df['Tag'] = final_tags
                    except:
                        df['Tag'] = "Uncategorized"
            
            st.session_state.auto_tagged_df = df
            st.session_state.last_file = clean_file.name

        st.subheader("1. Financial Triage & Clarification")
        
        # Display the editor
        try:
            edited_df = st.data_editor(
                st.session_state.auto_tagged_df,
                key="editor_v1.7.1",
                column_config={
                    "Tag": st.column_config.SelectboxColumn("Tag", options=["Need", "Desire", "Salary", "Income", "Uncategorized"], required=True),
                    "Context": st.column_config.TextColumn("Context (Optional)")
                },
                use_container_width=True
            )
            
            # Standard Math & Analysis
            if "Amount" in edited_df.columns:
                edited_df['Amount'] = pd.to_numeric(edited_df['Amount'], errors='coerce').fillna(0)
                desires = edited_df[edited_df["Tag"] == "Desire"]
                total_desire = desires["Amount"].sum()
                
                st.divider()
                col1, col2 = st.columns(2)
                col1.metric("Monthly 'Desire' Spend", f"₹{total_desire:,.2f}")
                
                monthly_rate = 0.01 # 12% annually
                sip_fv = total_desire * (((1 + monthly_rate)**12 - 1) / monthly_rate) * (1 + monthly_rate)
                col2.metric("1-Year SIP Potential", f"₹{sip_fv:,.2f}")
                
                if st.button("Generate Strategy Report", type="primary") and model:
                    with st.spinner("Analyzing..."):
                        csv_data = edited_df[['Description', 'Amount', 'Tag', 'Context']].to_csv(index=False)
                        report_prompt = f"Data: {csv_data}\nTotal Desire: {total_desire}\nProvide: 1. Financial Wins 2. Market Rate Warnings (check 'Context') 3. Micro-Opportunity Cost Table 4. 1-Year Goal 5. Behavioral Pattern."
                        st.markdown(model.generate_content(report_prompt).text)
        except Exception as e:
            st.error("Table display error. Try re-uploading the file.")
            st.session_state.clear()

# ==========================================
# TAB 3: THE INTERCEPTOR
# ==========================================
with tab3:
    st.header("Step 3: Pre-Spend Interceptor")
    item_name = st.text_input("Product Name")
    item_price = st.number_input("Price (₹)", min_value=0)
    if st.button("Evaluate", type="primary") and model and item_price > 0:
        st.error(f"10-Year Opportunity Cost: ₹{item_price * (1.12**10):,.2f}")
        st.markdown(model.generate_content(f"Item: {item_name}, Price: {item_price}. Give 2 Indian investments and 1 psychological question.").text)
