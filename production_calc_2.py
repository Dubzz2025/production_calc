import streamlit as st
import pandas as pd

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Wrap Cost Calculator", 
    layout="wide", 
    page_icon="https://github.com/Dubzz2025/production_calc/blob/main/app_icon.png", # This puts a clapperboard in the browser tab
    initial_sidebar_state="collapsed" # Starts with sidebar closed for a cleaner mobile look
)

# --- 2. SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("📂 File Management")
    
    # NEW: File Uploader to load data from Mac to iPhone
    uploaded_file = st.file_uploader("Load Saved Crew List (CSV)", type=["csv"])
    
    st.divider()
    
    st.header("1. Day Settings")
    day_basis = st.radio("Weekly Rate Basis:", [10, 8], horizontal=True)
    
    st.divider()
    
    st.header("2. Current Status")
    hours_worked = st.number_input("Hours Already Worked", min_value=8.0, value=10.0, step=0.5)
    
    st.divider()
    
    st.header("3. Penalties")
    apply_night_25 = st.checkbox("Night Loading (25%)")
    apply_night_50 = st.checkbox("Night Loading (50%)")
    apply_load_100 = st.checkbox("Loading (100%)")
    
    st.divider()
    
    st.subheader("4. Global Settings")
    is_accommodated = st.checkbox("Crew Accommodated?", value=False)
    fringe_rate = st.number_input("Fringe Rate %", value=15.0, step=0.5) / 100

# --- 3. DATA SETUP ---

# Initialize Session State
if "crew_df" not in st.session_state:
    default_data = {
        "On-Set Crew": [True, True, True, True],
        "Description": ["DOP", "Gaffer", "Sound Recordist", "Runner"],
        "Weekly Rate": [0.0, 0.0, 0.0, 0.0],
        "Hourly Rate": [100.0, 80.0, 90.0, 40.0],
        "Time & Half (9th-10th)": [0.0, 0.0, 0.0, 0.0], 
        "Double Time (11th-12th)": [0.0, 0.0, 0.0, 0.0],
        "Triple Time": [0.0, 0.0, 0.0, 0.0],
        "Night Loading 25%": [0.0, 0.0, 0.0, 0.0],
        "Night Loading 50%": [0.0, 0.0, 0.0, 0.0],
        "Loading 100%": [0.0, 0.0, 0.0, 0.0]
    }
    st.session_state.crew_df = pd.DataFrame(default_data)

# LOGIC: If a file is uploaded, we overwrite the current session state with the file data
if uploaded_file is not None:
    try:
        loaded_df = pd.read_csv(uploaded_file)
        # Ensure the checkbox column is read correctly as boolean
        if "On-Set Crew" in loaded_df.columns:
            loaded_df["On-Set Crew"] = loaded_df["On-Set Crew"].astype(bool)
        
        st.session_state.crew_df = loaded_df
        # We add a success message but don't stop the script
        st.toast("✅ Crew List Loaded Successfully!", icon="📂")
    except Exception as e:
        st.error(f"Error loading file: {e}")

st.info(f"👇 Paste friendly mode: **Description** and **Weekly Rate** are now side-by-side.")

# COLUMN CONFIG
column_config = {
    "On-Set Crew": st.column_config.CheckboxColumn("Active?", default=True),
    "Weekly Rate": st.column_config.NumberColumn(format="$%.2f"),
    "Hourly Rate": st.column_config.NumberColumn(format="$%.2f"),
    "Time & Half (9th-10th)": st.column_config.NumberColumn(format="$%.2f"),
    "Double Time (11th-12th)": st.column_config.NumberColumn(format="$%.2f"),
    "Triple Time": st.column_config.NumberColumn(format="$%.2f"),
}

edited_df = st.data_editor(
    st.session_state.crew_df, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config=column_config,
    key="editor" 
)

# --- THE MAGIC BUTTON ---
if st.button("🔄 Calculate Rates (Weekly → Hourly → OT)"):
    df_calc = edited_df.copy()
    
    for index, row in df_calc.iterrows():
        weekly = row["Weekly Rate"]
        hourly = row["Hourly Rate"]
        
        base_rate = hourly
        if weekly > 0:
            base_rate = (weekly / 5) / day_basis
            df_calc.at[index, "Hourly Rate"] = base_rate
        
        if base_rate > 0:
            df_calc.at[index, "Time & Half (9th-10th)"] = base_rate * 1.5
            df_calc.at[index, "Double Time (11th-12th)"] = base_rate * 2.0
            df_calc.at[index, "Triple Time"] = base_rate * 3.0
            df_calc.at[index, "Night Loading 25%"] = base_rate * 0.25
            df_calc.at[index, "Night Loading 50%"] = base_rate * 0.50
            df_calc.at[index, "Loading 100%"] = base_rate * 1.0

    st.session_state.crew_df = df_calc
    st.rerun()

edited_df = st.session_state.crew_df

# --- 4. CALCULATION ENGINE ---
def get_hourly_cost(crew_df, current_hour_number):
    hour_cost = 0
    active_crew = crew_df[crew_df["On-Set Crew"] == True]
    
    for index, row in active_crew.iterrows():
        rate_for_this_hour = 0
        if current_hour_number <= 8:
            rate_for_this_hour = row["Hourly Rate"]
        elif current_hour_number <= 10:
            rate_for_this_hour = row["Time & Half (9th-10th)"]
        elif current_hour_number <= 12:
            rate_for_this_hour = row["Double Time (11th-12th)"]
        else:
            if is_accommodated and current_hour_number == 13:
                 rate_for_this_hour = row["Double Time (11th-12th)"]
            else:
                rate_for_this_hour = row["Triple Time"]

        loading_cost = 0
        if apply_night_25: loading_cost += row["Night Loading 25%"]
        if apply_night_50: loading_cost += row["Night Loading 50%"]
        if apply_load_100: loading_cost += row["Loading 100%"]
            
        hour_cost += (rate_for_this_hour + loading_cost)
    return hour_cost

# --- 5. DISPLAY RESULTS ---
st.divider()
st.subheader(f"💰 Projected Cost (Start Point: {hours_worked} Hours)")

cols = st.columns(4)
cumulative_raw = 0
cumulative_fringe = 0

for i in range(1, 5):
    this_hour_number = hours_worked + i
    cost_raw = get_hourly_cost(edited_df, this_hour_number)
    cost_fringe = cost_raw * (1 + fringe_rate)
    cumulative_raw += cost_raw
    cumulative_fringe += cost_fringe
    
    with cols[i-1]:
        st.markdown(f"#### +{i} Hour ({this_hour_number}th hr)")
        st.metric(label="Total Cost", value=f"${cumulative_fringe:,.0f}")
        st.caption(f"Fees: ${cumulative_raw:,.0f} | Fringes: ${cumulative_fringe - cumulative_raw:,.0f}")
        
        if this_hour_number > 12:
            st.error("TRIPLE TIME")
        elif this_hour_number > 10:
            st.warning("DOUBLE TIME")
        elif this_hour_number > 8:
            st.info("TIME & HALF")

# --- 6. EXPORT ---
st.divider()
csv = edited_df.to_csv(index=False).encode('utf-8')
st.download_button("💾 Save Crew List to CSV", data=csv, file_name="crew_list.csv", mime="text/csv", help="Save this file to iCloud to open on iPhone")
