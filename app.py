import streamlit as st
import google.generativeai as genai

st.title("🔍 Phase 1.5: Model Discovery")

user_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if user_key:
    try:
        genai.configure(api_key=user_key)
        
        # This line asks Google: "What models can this key use?"
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        st.write("### ✅ Key is working!")
        st.write("Your key has access to these models:")
        st.write(available_models)
        
        if "models/gemini-1.5-flash" in available_models:
            st.success("Perfect! gemini-1.5-flash is available. We can proceed.")
        else:
            st.warning("gemini-1.5-flash is NOT in your list. Pick one from the list above instead.")

    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
else:
    st.info("Please enter your key to see your available models.")
