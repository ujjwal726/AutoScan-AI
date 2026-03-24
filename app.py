import streamlit as st
import google.generativeai as genai
import pandas as pd # This is for Excel/Google Sheets
from PIL import Image

st.set_page_config(page_title="AI Manager: Phase 3", layout="wide")
st.title("🚀 Phase 3: The Universal Intake Valve")

# Sidebar for API Key
st.sidebar.header("Settings")
user_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if user_key:
    try:
        genai.configure(api_key=user_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        st.sidebar.success("✅ Engine Online")

        # --- THE UNIVERSAL INTAKE SECTION ---
        st.write("### 📥 Select your Data Source")
        
        # We use a 'Select Box' to keep the screen clean
        option = st.selectbox(
            'How would you like to upload your records?',
            ('Manual Text Entry', 'Image/PDF of Paper Records', 'Excel/CSV Spreadsheet')
        )

        data_to_process = None

        if option == 'Manual Text Entry':
            data_to_process = st.text_area("Paste Ledger Text:", height=150)

        elif option == 'Image/PDF of Paper Records':
            # This creates a file uploader for images
            uploaded_file = st.file_uploader("Upload a photo or PDF of your ledger", type=['png', 'jpg', 'jpeg', 'pdf'])
            if uploaded_file:
                st.image(uploaded_file, caption="Uploaded Record", width=300)
                data_to_process = "FILE_UPLOADED" # We will handle the AI Vision in Phase 4

        elif option == 'Excel/CSV Spreadsheet':
            # This handles digital data
            digital_file = st.file_uploader("Upload your Excel or CSV file", type=['csv', 'xlsx'])
            if digital_file:
                # 'Pandas' reads the sheet and shows it as a table
                df = pd.read_csv(digital_file) if digital_file.name.endswith('csv') else pd.read_excel(digital_file)
                st.write("Preview of Digital Records:")
                st.dataframe(df.head())
                data_to_process = df.to_string() # Turn the table into text for the AI

        # --- THE ACTION BUTTON ---
        # --- THE ACTION BUTTON (The Brain) ---
        if st.button("🛠️ Orchestrate AI Analysis"):
            if data_to_process:
                with st.spinner('AI Freelancer is reading and structuring the data...'):
                    
                    # SYSTEM PROMPT: The "Rules of the Game" for the AI
                    system_prompt = """
                    You are a Data Extraction Specialist for a retail shop. 
                    Convert the input into a clean Markdown Table.
                    Columns: Date, Item Name, Category, Quantity, Unit Price, Total, Payment Type (Cash/Credit).
                    Rules: 
                    1. If 'Udhari' is mentioned, Payment Type is 'Credit'.
                    2. Normalize names (e.g., 'Tel' -> 'Oil', 'Sakhar' -> 'Sugar').
                    3. If an image is provided, perform OCR to find all line items.
                    """

                    try:
                        # LOGIC: Different handling for different 'option' variables
                        if option == 'Manual Text Entry':
                            response = model.generate_content([system_prompt, data_to_process])
                        
                        elif option == 'Image/PDF of Paper Records' and uploaded_file:
                            # We must convert the upload into a format Gemini understands
                            img = Image.open(uploaded_file)
                            response = model.generate_content([system_prompt, img])
                        
                        elif option == 'Excel/CSV Spreadsheet':
                            response = model.generate_content([system_prompt, data_to_process])

                        # DISPLAY THE RESULT
                        st.divider()
                        st.subheader("✅ Extracted Clean Data")
                        st.markdown(response.text)
                        
                        # Store for the next phase (The Analyst)
                        st.session_state['clean_data'] = response.text

                    except Exception as ai_err:
                        st.error(f"AI Processing Error: {ai_err}")
            else:
                st.warning("Please provide data before analyzing.")

    except Exception as e:
        st.sidebar.error(f"❌ Error: {e}")
else:
    st.info("Waiting for API Key...")
