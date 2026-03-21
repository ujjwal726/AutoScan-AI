import streamlit as st
import google.generativeai as genai
from PIL import Image
import urllib.parse
import re

# --- 1. CLEAN DATA: OFFICIAL 2026 MGP PRICE REFERENCE ---
# Grounding the AI in official Maruti figures to prevent high-price hallucinations
MGP_DATABASE_2026 = {
    "BONNET": {"replace": 22163, "repair": 5500, "label": "Bonnet/Hood Assembly"},
    "FRONT BUMPER": {"replace": 12325, "repair": 3500, "label": "Front Bumper Shell"},
    "REAR BUMPER": {"replace": 10396, "repair": 3200, "label": "Rear Bumper Shell"},
    "HEADLIGHT (LED)": {"replace": 11152, "repair": 1500, "label": "LED Headlight (Nexa)"},
    "FENDER": {"replace": 8335, "repair": 4000, "label": "Front Fender Panel"},
    "DOOR": {"replace": 14665, "repair": 4500, "label": "Door Shell (Front/Rear)"},
    "SIDE MIRROR": {"replace": 5500, "repair": 1500, "label": "ORVM Auto-Fold"},
    "WINDSHIELD": {"replace": 18564, "repair": 0, "label": "Front Windshield Glass"}
}

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan AI", page_icon="🚗", layout="centered")
st.title("🚗 AutoScan Insurance AI")
st.markdown("### ⚡ Precision Surveyor & Claim Verdict")
st.caption("Grounded in 2026 MGP Official Rates • VJTI-PM Framework")

# --- AUTHENTICATION ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    # Using 1.5-Flash-8B for higher quota and reliability
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-8b")
    except Exception as e:
        st.error(f"Model Error: {e}")
        st.stop()

    # --- INPUT SECTION ---
    uploaded_file = st.file_uploader("Upload damage photo", type=["jpg", "jpeg", "png"])
    
    col1, col2 = st.columns(2)
    with col1:
        premium = st.number_input("Annual Premium (₹)", value=22000, step=500)
    with col2:
        ncb = st.slider("Current NCB %", 0, 50, 25, step=5)

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Scanning against MGP Database...", use_container_width=True)

        if st.button("GET VERIFIED VERDICT", type="primary"):
            with st.spinner("Calculating Insurance Math..."):
                # PROMPT WITH EMBEDDED REALISTIC DATA
                prompt = f"""
                Act as an Official Maruti Suzuki Surveyor. 
                Use ONLY these 2026 MGP prices for estimation: {MGP_DATABASE_2026}
                
                Analyze the car photo:
                1. Identify the car model.
                2. Identify the specific damaged component.
                3. If the damage is a 'dent/scratch', use REPAIR price. If 'cracked/broken', use REPLACE price.
                
                OUTPUT FORMAT:
                VEHICLE: [Model Name]
                PART: [Specific Part Name]
                ACTION: [REPAIR/REPLACE]
                COST: ₹[Exact Price from Data]
                LABOR: ₹[Estimate 2500-4000 for Paint]
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    output_text = response.text
                    
                    # --- DATA EXTRACTION ---
                    # Using Regex to pull numbers for the math
                    cost_match = re.search(r"COST: ₹([\d,]+)", output_text)
                    labor_match = re.search(r"LABOR: ₹([\d,]+)", output_text)
                    part_match = re.search(r"PART:\s*(.*)", output_text)
                    vehicle_match = re.search(r"VEHICLE:\s*(.*)", output_text)
                    
                    part_price = int(cost_match.group(1).replace(',', '')) if cost_match else 0
                    labor_price = int(labor_match.group(1).replace(',', '')) if labor_match else 3000
                    total_out_of_pocket = part_price + labor_price
                    
                    # --- INSURANCE LOGIC ---
                    ncb_loss_value = premium * (ncb/100)
                    # File Charge + NCB Loss vs Total Cost
                    claim_benefit = total_out_of_pocket - 1000 # 1000 is mandatory deductible
                    
                    # --- DISPLAY REPORT ---
                    st.markdown("---")
                    st.markdown(f"### 📊 Survey Report: {vehicle_match.group(1) if vehicle_match else 'Maruti'}")
                    
                    res_col1, res_col2 = st.columns(2)
                    res_col1.write(f"**Part identified:** {part_match.group(1) if part_match else 'Component'}")
                    res_col2.write(f"**Total Repair Cost:** ₹{total_out_of_pocket:,}")
                    
                    st.divider()
                    
                    # --- FINAL VERDICT LOGIC ---
                    if total_out_of_pocket > (ncb_loss_value + 1500):
                        st.success("🏁 **FINAL VERDICT: GO FOR CLAIM**")
                        st.caption(f"Reason: Your repair cost (₹{total_out_of_pocket:,}) significantly exceeds your NCB loss (₹{int(ncb_loss_value):,}).")
                    else:
                        st.warning("🏁 **FINAL VERDICT: GO FOR CASH**")
                        st.caption(f"Reason: Your NCB loss (₹{int(ncb_loss_value):,}) is close to or higher than the repair cost. Better to save your NCB.")

                    # --- DEEP LINK ---
                    st.subheader("🔗 Live Validation")
                    search_query = f"Maruti {vehicle_match.group(1) if vehicle_match else ''} {part_match.group(1) if part_match else 'Part'} price"
                    encoded_query = urllib.parse.quote(search_query)
                    st.link_button(f"👉 Cross-Check MGP Price on Boodmo", f"https://boodmo.com/search/{encoded_query}/")
                    
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
else:
    st.warning("Please enter your API Key in the sidebar.")
