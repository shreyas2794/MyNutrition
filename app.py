import streamlit as st
import google.generativeai as genai
import json
import re

# --- CONFIGURATION & API SETUP ---
st.set_page_config(page_title="Personal AI Nutritionist", layout="wide")

GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not GOOGLE_API_KEY:
    st.error("Please configure your GOOGLE_API_KEY in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- SESSION STATE INITIALIZATION ---
if "logged_meals" not in st.session_state:
    st.session_state.logged_meals = []
if "water_glasses" not in st.session_state:
    st.session_state.water_glasses = 0

# Set user requested profile defaults
if "targets" not in st.session_state:
    st.session_state.targets = {
        "calories": 1250,  # Max limit requested
        "protein": 75,     # Safe baseline for 63kg on weight loss deficit
        "carbs": 140,
        "fats": 45,
        "water": 8         # Standard daily glasses target
    }

# --- HELPER FUNCTIONS ---
def analyze_food_with_gemini(food_input):
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
        "micros": "Brief note on key micros present"
    }}
    """
    try:
        response = model.generate_content(prompt)
        clean_text = re.sub(r"```json|```", "", response.text).strip()
        return json.loads(clean_text)
    except Exception as e:
        st.error(f"Error parsing food item: {e}")
        return None

# --- UI LAYOUT ---
st.title("🍏 Personal AI Nutrition Tracker")
st.caption("Custom Target Profile: Max 1250 kcal | Sustainable Weight Management")

# Sidebar: Targets & Profile
with st.sidebar:
    st.header("🎯 Profile & Targets")
    st.info("Profile: 63 kg | 149 cm")
    st.session_state.targets["calories"] = st.number_input("Max Calories (kcal)", value=st.session_state.targets["calories"])
    st.session_state.targets["protein"] = st.number_input("Target Protein (g)", value=st.session_state.targets["protein"])
    st.session_state.targets["carbs"] = st.number_input("Target Carbs (g)", value=st.session_state.targets["carbs"])
    st.session_state.targets["fats"] = st.number_input("Target Fats (g)", value=st.session_state.targets["fats"])
    st.session_state.targets["water"] = st.number_input("Water Target (Glasses)", value=st.session_state.targets["water"])
    
    st.markdown("---")
    if st.button("Clear Dashboard Data"):
        st.session_state.logged_meals = []
        st.session_state.water_glasses = 0
        st.annotation = "Cleared!"
        st.rerun()

# Layout Columns
col1, col2 = st.columns([1, 1])

# Column 1: Food Logging & Water Tracking
with col1:
    st.header("📝 Log Your Intake")
    
    # 💧 Water Tracking Component
    st.subheader("💧 Water Intake Tracker")
    w_col1, w_col2, w_col3 = st.columns([1, 1, 2])
    with w_col1:
        if st.button("➕ Add Glass"):
            st.session_state.water_glasses += 1
            st.rerun()
    with w_col2:
        if st.button("➖ Remove") and st.session_state.water_glasses > 0:
            st.session_state.water_glasses -= 1
            st.rerun()
    with w_col3:
        st.markdown(f"**Progress:** {st.session_state.water_glasses} / {st.session_state.targets['water']} glasses")
    
    st.markdown("---")
    
    # 🍽️ Meal Logging Component
    st.subheader("Meal Logger")
    meal_slot = st.selectbox("Select Meal Slot", ["Breakfast", "Lunch", "Evening Snack", "Dinner"])
    food_input = st.text_input("What did you have?", placeholder="e.g., 3/4 cup cooked rolled oats or 150g raw paneer cooked in 1 tsp ghee...")
    
    if st.button("Analyze & Preview"):
        if food_input:
            with st.spinner("Gemini is calculating metrics..."):
                result = analyze_food_with_gemini(food_input)
                if result:
                    st.session_state.current_preview = result
        else:
            st.warning("Please enter a food description.")

    # Override Adjustments
    if "current_preview" in st.session_state and st.session_state.current_preview:
        st.markdown("---")
        st.subheader("🔍 Review & Override Metrics")
        
        p_name = st.text_input("Name", value=st.session_state.current_preview["food_name"])
        p_cal = st.number_input("Calories", value=int(st.session_state.current_preview["calories"]))
        
        # Proportional shifting logic if user manually edits calories
        orig_cal = st.session_state.current_preview["calories"]
        ratio = (p_cal / orig_cal) if orig_cal > 0 else 1.0
        
        p_prot = st.number_input("Protein (g)", value=round(st.session_state.current_preview["protein"] * ratio, 1))
        p_carbs = st.number_input("Carbs (g)", value=round(st.session_state.current_preview["carbs"] * ratio, 1))
        p_fats = st.number_input("Fats (g)", value=round(st.session_state.current_preview["fats"] * ratio, 1))
        p_micros = st.text_area("Micros/Notes", value=st.session_state.current_preview["micros"])
        
        if st.button("✅ Save to Diary"):
            st.session_state.logged_meals.append({
                "slot": meal_slot,
                "food_name": p_name,
                "calories": p_cal,
                "protein": p_prot,
                "carbs": p_carbs,
                "fats": p_fats,
                "micros": p_micros
            })
            st.session_state.current_preview = None
            st.success(f"Added to {meal_slot}!")
            st.rerun()

# Column 2: Dashboard Overview & Slot Lists
with col2:
    st.header("📊 Today's Progress Summary")
    
    # Mathematical Totals
    total_cal = sum(m["calories"] for m in st.session_state.logged_meals)
    total_prot = sum(m["protein"] for m in st.session_state.logged_meals)
    total_carbs = sum(m["carbs"] for m in st.session_state.logged_meals)
    total_fats = sum(m["fats"] for m in st.session_state.logged_meals)
    
    def progress_helper(current, target):
        return min(float(current / target), 1.0) if target > 0 else 0.0

    # Macro progress indicators
    st.metric("Total Calories", f"{total_cal} / {st.session_state.targets['calories']} kcal")
    st.progress(progress_helper(total_cal, st.session_state.targets['calories']))
    
    st.metric("Protein Intake", f"{total_prot}g / {st.session_state.targets['protein']}g")
    st.progress(progress_helper(total_prot, st.session_state.targets['protein']))
    
    st.metric("Carbs Intake", f"{total_carbs}g / {st.session_state.targets['carbs']}g")
    st.progress(progress_helper(total_carbs, st.session_state.targets['carbs']))
    
    st.metric("Fats Intake", f"{total_fats}g / {st.session_state.targets['fats']}g")
    st.progress(progress_helper(total_fats, st.session_state.targets['fats']))
    
    # Categorized Meals Breakdown
    st.markdown("---")
    st.subheader("📋 Meal Log Details")
    
    for slot in ["Breakfast", "Lunch", "Evening Snack", "Dinner"]:
        st.markdown(f"#### {slot}")
        slot_meals = [m for m in st.session_state.logged_meals if m["slot"] == slot]
        
        if slot_meals:
            for item in slot_meals:
                with st.expander(f"{item['food_name']} — {item['calories']} kcal"):
                    st.write(f"**Macros:** P: {item['protein']}g | C: {item['carbs']}g | F: {item['fats']}g")
                    st.write(f"**Micros:** {item['micros']}")
        else:
            st.caption("No items logged for this slot yet.")
