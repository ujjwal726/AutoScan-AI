import streamlit as st
import google.generativeai as genai
from PIL import Image
import urllib.parse
import re

# --- 1. THE "GROUND TRUTH" DATASET (2026 MGP Nashik Rates) ---
# Prices for Grand Vitara / Brezza Class
PARTS_DATABASE = {
    "BONNET": {"replace": 22163, "repair": 5500, "label": "Bonnet/Hood Assembly"},
    "FRONT BUMPER": {"replace": 12325, "repair": 3500, "label": "Front Bumper Shell"},
    "REAR BUMPER": {"replace": 10396, "repair": 3200, "label": "Rear Bumper Shell"},
    "HEADLIGHT (LED)": {"replace": 11152, "repair": 1500, "label": "LED Headlight Assy"},
    "FENDER": {"replace": 8335, "repair": 4000, "label": "Front Fender Panel"},
    "DOOR": {"replace": 14665, "repair": 4500, "label": "Door Shell (Front/Rear)"},
    "WINDSHIELD": {"replace": 18564, "repair": 0, "label": "Front Windshield Glass"}
}

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan Insurance AI", page_icon="🚗", layout="wide")
st.title("🚗 AutoScan Insurance AI")
st.markdown("### 🔍 Precision Audit & Claim Consultant")
st.caption("Grounded in 2026 MGP Data • Nashik Verified")

# --- AUTHENTICATION ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # --- 2. INPUT SECTION ---
    with st.sidebar:
        st.header("📋 Policy Details")
        premium = st.number_input("Annual Premium (₹)", value=22000)
        ncb_pct = st.slider("Current NCB %", 0, 50, 25)
        ncb_value = (premium * ncb_pct) / 100
        st.info(f"💡 Potential NCB Loss: ₹{int(ncb_value)}")

    uploaded_file = st.file_uploader("Upload damage photo", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Scanning for component damage...", use_container_width=True)

        if st.button("RUN CRITICAL AUDIT", type="primary"):
            with st.spinner("Analyzing against 2026 MGP Price List..."):
                prompt = f"""
                Act as a Senior Insurance Surveyor for Maruti Nexa/Arena. 
                Use ONLY this price list: {PARTS_DATABASE}
                
                1. Identify the car model (e.g. Grand Vitara).
                2. List specific damaged parts.
                3. Decide: 'REPLACE' (if cracked/smashed) or 'REPAIR' (if dented/scratched).
                4. Match the EXACT price from the provided data.
                
                FORMAT:
                VEHICLE: [Model Name]
                DAMAGED_PARTS:
                - [Part Name] | ₹[Price] | [Action]
                ANALYSIS: [One line on severity]
                VERDICT: [CLAIM / CASH]
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    res_text = response.text
                    
                    # --- 3. CRISP ANALYSIS & TABLE ---
                    st.markdown("---")
                    vehicle_name = re.search(r"VEHICLE:\s*(.*)", res_text).group(1)
                    st.subheader(f"📊 Audit Report: {vehicle_name}")
                    
                    parts_lines = re.findall(r"-\s*(.*?)\s*\|\s*₹([\d,]+)", res_text)
                    total_estimate = 0
                    
                    # Header for Table
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write("**Component**")
                    c2.write("**Verified Rate**")
                    c3.write("**Action**")
                    st.divider()

                    for name, price in parts_lines:
                        p_val = int(price.replace(',', ''))
                        total_estimate += p_val
                        
                        col1, col2, col3 = st.columns([2, 1, 1])
                        col1.write(f"**{name}**")
                        col2.write(f"₹{price}")
                        # Direct Verification Link
                        q = urllib.parse.quote(f"Maruti {vehicle_name} {name} price")
                        col3.link_button("🔗 Verify Rates", f"https://boodmo.com/search/{q}/")
                        st.divider()

                    # --- 4. THE DECISION ENGINE ---
                    st.subheader("💡 Claim Suggestion")
                    if total_estimate > (ncb_value + 2000): # Adding a 2k buffer for file charges
                        st.success(f"**GO FOR CLAIM**: Total Repair (₹{total_estimate:,}) > NCB Loss (₹{int(ncb_value):,})")
                    else:
                        st.warning(f"**PAY CASH**: Total Repair (₹{total_estimate:,}) is close to your NCB Loss. Save your claim for bigger damage.")

                except Exception as e:
                    st.error(f"Surveyor Error: {e}")
else:
    st.warning("Please enter your API Key in the sidebar.")
