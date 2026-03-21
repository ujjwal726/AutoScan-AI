import streamlit as st
import google.generativeai as genai
from PIL import Image
import urllib.parse
import re

# --- 1. THE "GROUND TRUTH" DATASET (2026 Maruti Genuine Parts) ---
# Prices for Grand Vitara / Brezza Class
PARTS_DATABASE = {
    "BONNET": {"replace": 22163, "repair": 5500, "label": "Bonnet/Hood Assembly"},
    "FRONT BUMPER": {"replace": 12325, "repair": 3500, "label": "Front Bumper Shell"},
    "REAR BUMPER": {"replace": 10396, "repair": 3200, "label": "Rear Bumper Shell"},
    "HEADLIGHT (LED)": {"replace": 11152, "repair": 1500, "label": "LED Headlight Assy"},
    "FENDER": {"replace": 8335, "repair": 4000, "label": "Front Fender Panel"},
    "DOOR": {"replace": 14665, "repair": 4500, "label": "Door Shell"},
    "WINDSHIELD": {"replace": 18564, "repair": 0, "label": "Front Windshield Glass"}
}

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan AI", page_icon="🚗", layout="wide")
st.title("🚗 AutoScan Insurance AI")
st.markdown("### 📋 Precision Damage Audit & Claim Strategy")

# --- AUTHENTICATION & MODEL FIX ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    # UPDATED: Using Gemini 2.0 Flash to avoid the 404 error
    model = genai.GenerativeModel("gemini-2.0-flash")

    # --- 2. POLICY INPUTS ---
    with st.sidebar:
        st.header("🛡️ Policy Context")
        premium = st.number_input("Annual Premium (₹)", value=22000)
        ncb_pct = st.slider("Current NCB %", 0, 50, 25)
        file_charge = 1000 # Standard MSEDCL/Insurance file charge
        potential_loss = ((premium * ncb_pct) / 100) + file_charge
        st.error(f"Financial Loss on Claim: ₹{int(potential_loss):,}")

    uploaded_file = st.file_uploader("Upload Damage Photo", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, use_container_width=True)

        if st.button("🚀 ANALYZE REPAIR VS CLAIM"):
            with st.spinner("Surveying parts and calculating ROI..."):
                prompt = f"""
                Act as a Professional Insurance Surveyor. Use this dataset: {PARTS_DATABASE}
                Analyze the image for a Maruti car.
                1. Identify the car model.
                2. List parts that are CLEARLY damaged.
                3. Choose 'REPLACE' for cracks/holes or 'REPAIR' for dents.
                4. Match the EXACT price from the provided dataset.

                OUTPUT FORMAT:
                VEHICLE: [Model Name]
                DAMAGED_PARTS:
                - [Part Name] | ₹[Price] | [Action]
                SEVERITY: [One sentence on structural impact]
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    res_text = response.text
                    
                    st.markdown("---")
                    # Extraction Logic
                    vehicle_match = re.search(r"VEHICLE:\s*(.*)", res_text)
                    vehicle = vehicle_match.group(1) if vehicle_match else "Maruti"
                    
                    st.subheader(f"📑 Audit: {vehicle}")
                    
                    # Layout for the parts table
                    parts_lines = re.findall(r"-\s*(.*?)\s*\|\s*₹([\d,]+)", res_text)
                    total_repair = 0
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    col1.write("**Component**")
                    col2.write("**2026 MGP Rate**")
                    col3.write("**Action**")
                    st.divider()

                    for name, price in parts_lines:
                        price_val = int(price.replace(',', ''))
                        total_repair += price_val
                        
                        c1, c2, c3 = st.columns([2, 1, 1])
                        c1.write(f"**{name}**")
                        c2.write(f"₹{price}")
                        # Part-specific verification link
                        q = urllib.parse.quote(f"Maruti {vehicle} {name} price 2026")
                        c3.link_button("🔗 Check Live Rates", f"https://boodmo.com/search/{q}/")
                        st.divider()

                    # --- 3. THE "PM" DECISION ENGINE ---
                    st.subheader("💡 Strategic Suggestion")
                    
                    # Logic: Is Total Repair > (NCB Loss + File Charge)?
                    if total_repair > potential_loss:
                        st.success(f"🎯 **SUGGESTION: GO FOR CLAIM**")
                        st.write(f"Repairing out-of-pocket (₹{total_repair:,}) is more expensive than losing your NCB benefit (₹{int(potential_loss):,}).")
                    else:
                        st.warning(f"🎯 **SUGGESTION: PAY CASH**")
                        st.write(f"Your NCB loss (₹{int(potential_loss):,}) is higher than the repair cost (₹{total_repair:,}). Paying cash protects your future premium discount.")

                except Exception as e:
                    st.error(f"Algorithm Error: {e}. Ensure Generative Language API is enabled.")
else:
    st.warning("Please enter your API Key to proceed.")
