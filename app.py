import streamlit as st
import google.generativeai as genai
import json
import re

# --- CONFIGURATION & API SETUP ---
st.set_page_config(page_title="Personal AI Nutritionist", layout="wide")

# Securely fetch API key from Streamlit Secrets or local environment
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not GOOGLE_API_KEY:
    st.error("Please configure your GOOGLE_API_KEY in Streamlit Secrets or your local environment.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- SESSION STATE INITIALIZATION ---
if "logged_meals" not in st.session_state:
    st.session_state.logged_meals = []
if "targets" not in st.session_state:
    st.session_state.targets = {"calories": 2000, "protein": 150, "carbs": 200, "fats": 65}

# --- HELPER FUNCTIONS ---
def analyze_food_with_gemini(food_input):
    """Uses Gemini to parse flexible quantities, cooking methods, and oils into structured JSON."""
    prompt = f"""
    You are an expert nutrition database. Analyze the following food item or meal description.
    Account strictly for quantities (fractions or decimals), cooking methods, and added oils/ingredients.
    
    Food Description: "{food_input}"
    
    Respond ONLY with a raw JSON object matching this exact structure, no markdown formatting, no text outside the JSON:
    {{
        "food_name": "Cleaned up name of food",
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fats": 0,
        "micros": "Brief note on key micros present (e.g., High in Iron, Vit C)"
    }}
    """
    try:
        response = model.generate_content(prompt)
        # Clean up any accidental markdown wrapper if the model includes it
        clean_text = re.sub(r"```json|```", "", response.text).strip()
        return json.loads(clean_text)
    except Exception as e:
        st.error(f"Error parsing food item: {e}")
        return None

# --- UI LAYOUT ---
st.title("🍏 Personal AI Nutrition Tracker")
st.write("Powered by Gemini 1.5 Flash — Flexible, precise, and completely free.")

# Sidebar: Target & Profile Adjustments
with st.sidebar:
    st.header("🎯 Daily Targets")
    st.session_state.targets["calories"] = st.number_input("Calories (kcal)", value=st.session_state.targets["calories"])
    st.session_state.targets["protein"] = st.number_input("Protein (g)", value=st.session_state.targets["protein"])
    st.session_state.targets["carbs"] = st.number_input("Carbs (g)", value=st.session_state.targets["carbs"])
    st.session_state.targets["fats"] = st.number_input("Fats (g)", value=st.session_state.targets["fats"])
    
    if st.button("Clear Today's Log"):
        st.session_state.logged_meals = []
        st.rerun()

# Main Layout Columns
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📝 Log Food / Ask Gemini")
    st.caption("Example: '1.25 cups of white rice' or '3/4 chicken breast pan-fried in 1 tbsp olive oil'")
    
    food_input = st.text_input("What did you eat?", placeholder="Type here...")
    
    if st.button("Analyze & Preview"):
        if food_input:
            with st.spinner("Gemini is calculating..."):
                result = analyze_food_with_gemini(food_input)
                if result:
                    st.session_state.current_preview = result
        else:
            st.warning("Please enter a food description first.")

    # Editable Preview Section
    if "current_preview" in st.session_state and st.session_state.current_preview:
        st.markdown("---")
        st.subheader("🔍 Review & Override Metrics")
        st.write("Gemini found the following. Adjust manually if you prefer:")
        
        # User can manually override metrics directly before saving
        p_name = st.text_input("Name", value=st.session_state.current_preview["food_name"])
        p_cal = st.number_input("Calories", value=int(st.session_state.current_preview["calories"]))
        
        # Proportional adjustment logic if user changes calories directly
        orig_cal = st.session_state.current_preview["calories"]
        ratio = (p_cal / orig_cal) if orig_cal > 0 else 1.0
        
        p_prot = st.number_input("Protein (g)", value=round(st.session_state.current_preview["protein"] * ratio, 1))
        p_carbs = st.number_input("Carbs (g)", value=round(st.session_state.current_preview["carbs"] * ratio, 1))
        p_fats = st.number_input("Fats (g)", value=round(st.session_state.current_preview["fats"] * ratio, 1))
        p_micros = st.text_area("Micros/Notes", value=st.session_state.current_preview["micros"])
        
        if st.button("✅ Confirm & Add to Log"):
            st.session_state.logged_meals.append({
                "food_name": p_name,
                "calories": p_cal,
                "protein": p_prot,
                "carbs": p_carbs,
                "fats": p_fats,
                "micros": p_micros
            })
            st.session_state.current_preview = None
            st.success(f"Added {p_name} to log!")
            st.rerun()

# Progress and Tracking Dashboard
with col2:
    st.header("📊 Daily Progress")
    
    # Calculate Totals
    total_cal = sum(m["calories"] for m in st.session_state.logged_meals)
    total_prot = sum(m["protein"] for m in st.session_state.logged_meals)
    total_carbs = sum(m["carbs"] for m in st.session_state.logged_meals)
    total_fats = sum(m["fats"] for m in st.session_state.logged_meals)
    
    # Helper for progress bars
    def progress_helper(current, target):
        return min(float(current / target), 1.0) if target > 0 else 0.0

    st.metric("Total Calories", f"{total_cal} / {st.session_state.targets['calories']} kcal")
    st.progress(progress_helper(total_cal, st.session_state.targets['calories']))
    
    st.metric("Protein", f"{total_prot}g / {st.session_state.targets['protein']}g")
    st.progress(progress_helper(total_prot, st.session_state.targets['protein']))
    
    st.metric("Carbs", f"{total_carbs}g / {st.session_state.targets['carbs']}g")
    st.progress(progress_helper(total_carbs, st.session_state.targets['carbs']))
    
    st.metric("Fats", f"{total_fats}g / {st.session_state.targets['fats']}g")
    st.progress(progress_helper(total_fats, st.session_state.targets['fats']))
    
    # Today's History Log
    st.markdown("---")
    st.subheader("📋 Today's Meals")
    if st.session_state.logged_meals:
        for item in st.session_state.logged_meals:
            with st.expander(f"{item['food_name']} — {item['calories']} kcal"):
                st.write(f"**Macros:** P: {item['protein']}g | C: {item['carbs']}g | F: {item['fats']}g")
                st.write(f"**Micros/Notes:** {item['micros']}")
    else:
        st.info("No meals logged today yet.")
