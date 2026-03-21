import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import urllib.parse
import re

# --- UI SETUP ---
st.set_page_config(page_title="AutoScan AI", page_icon="🚗", layout="centered")
st.title("🚗 AutoScan AI")
st.markdown("### 🔍 Precision Part-by-Part Audit")
st.caption("2026 Nashik Estimates • Individual Part Verification")

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
        st.image(img, caption="Scanning for specific components...", use_container_width=True)

        if st.button("RUN GRANULAR AUDIT"):
            with st.spinner("Identifying individual parts..."):
                # ADVANCED PROMPT FOR LINE-ITEM EXTRACTION
                prompt = f"""
                Act as a Precision Auto Surveyor. Analyze the car in the photo.
                1. Identify the Car Model.
                2. List EVERY damaged component that needs replacement.
                3. For each part, estimate the 2026 MGP (Maruti Genuine Part) price.
                
                OUTPUT FORMAT:
                VEHICLE: [Car Name]
                
                PART_LIST:
                - [Part Name 1] | ₹[Price 1]
                - [Part Name 2] | ₹[Price 2]
                
                LABOR: ₹[Total Painting/Fitting]
                
                VERDICT: [GO FOR CLAIM / GO FOR CASH] (Based on {premium} Premium and {ncb}% NCB)
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    res_text = response.text
                    
                    # --- PARSING THE DATA ---
                    st.markdown("---")
                    
                    # Extract Vehicle Name
                    vehicle_match = re.search(r"VEHICLE:\s*(.*)", res_text)
                    vehicle_name = vehicle_match.group(1) if vehicle_match else "Maruti"
                    
                    st.subheader(f"📊 Repair Estimate: {vehicle_name}")
                    
                    # Extract Parts and Create Granular Table
                    parts_data = []
                    total_parts_cost = 0
                    
                    # Regex to find the part list lines
                    parts_lines = re.findall(r"-\s*(.*?)\s*\|\s*₹([\d,]+)", res_text)
                    
                    for part_name, part_price in parts_lines:
                        price_val = int(part_price.replace(',', ''))
                        total_parts_cost += price_val
                        
                        # Create a Deep Link for this specific part
                        search_q = f"{vehicle_name} {part_name} genuine price"
                        encoded_q = urllib.parse.quote(search_q)
                        verify_url = f"https://boodmo.com/search/{encoded_q}/"
                        
                        parts_data.append({
                            "Component": part_name,
                            "Est. Price": f"₹{part_price}",
                            "Action": verify_url
                        })

                    # Displaying the Granular Table with Links
                    if parts_data:
                        for item in parts_data:
                            c1, c2, c3 = st.columns([2, 1, 1.5])
                            c1.write(f"**{item['Component']}**")
                            c2.write(item['Est. Price'])
                            c3.link_button("🔗 Verify Price", item['Action'])
                            st.divider()
                    
                    # Display the Rest of the Report
                    st.markdown(res_text.split("PART_LIST:")[0]) # Show vehicle info
                    
                    # Final Verdict Section
                    verdict_match = re.search(r"VERDICT:\s*(.*)", res_text)
                    if verdict_match:
                        st.info(f"💡 **AI Recommendation:** {verdict_match.group(1)}")

                except Exception as e:
                    st.error(f"Surveyor Error: {e}")
                    st.write("Ensure your photo clearly shows the damaged panels.")
else:
    st.warning("Please enter your API Key in the sidebar.")
