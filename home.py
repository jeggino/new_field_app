import streamlit as st
import streamlit_folium as st_folium
import folium
from supabase import create_client, Client
import geocoder
import uuid

# --- CONFIG ---


import streamlit as st
from streamlit_folium import st_folium
import folium
from supabase import create_client, Client
import uuid

# --- CONFIG ---
st.set_page_config(page_title="Geo Observations", layout="wide")
SUPABASE_URL = "https://anydhrpvfenefacuoarv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFueWRocnB2ZmVuZWZhY3VvYXJ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzY3NTUyMDQsImV4cCI6MjA1MjMzMTIwNH0.mvCK6ya82Nu8E3GLpqw-Cl-0te55nK2tpEioDMiSTkM"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- SESSION LOGIN ---
if "user" not in st.session_state:
    st.session_state.user = None

def login(username, password):
    # Replace with Supabase Auth if needed
    if username and password:
        st.session_state.user = {"username": username}
        st.success(f"Welcome {username}!")

def logout():
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        if submit:
            login(username, password)
    st.stop()

# --- MAIN APP ---
st.sidebar.write(f"👤 Logged in as: {st.session_state.user['username']}")
if st.sidebar.button("Logout"):
    logout()
    st.experimental_rerun()

st.title("📍 Geo Observation Tool")

# --- MAP ---
m = folium.Map(location=[52.37, 4.90], zoom_start=12)
map_data = st_folium(m, height=500, width=800)

# --- OBSERVATION FORM ---
if map_data and map_data.get("last_clicked"):
    lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    st.subheader("📝 New Observation")
    with st.form("obs_form"):
        title = st.text_input("Title")
        description = st.text_area("Description")
        category = st.selectbox("Category", ["Wildlife", "Infrastructure", "Other"])
        save_btn = st.form_submit_button("Save Observation")
        if save_btn:
            obs_id = str(uuid.uuid4())
            supabase.table("observations").insert({
                "id": obs_id,
                "username": st.session_state.user["username"],
                "lat": lat,
                "lon": lon,
                "title": title,
                "description": description,
                "category": category
            }).execute()
            st.success("✅ Observation saved!")

# --- DISPLAY EXISTING OBSERVATIONS ---
st.subheader("📂 Existing Observations")
data = supabase.table("observations").select("*").execute()
for obs in data.data:
    st.write(f"**{obs['title']}** ({obs['lat']}, {obs['lon']}) - {obs['category']}")
