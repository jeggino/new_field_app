import streamlit as st
import streamlit_folium as st_folium
import folium
from supabase import create_client, Client
import geocoder
import uuid

# --- CONFIG ---
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="GPS Observation App", layout="wide")

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        # Replace with real authentication logic
        if username and password:
            st.session_state.logged_in = True
            st.session_state.username = username
        else:
            st.error("Invalid credentials")
    st.stop()

# --- GET USER LOCATION ---
g = geocoder.ip('me')
lat, lon = g.latlng if g.latlng else (52.37, 4.90)  # fallback coords

st.sidebar.success(f"Logged in as {st.session_state.username}")
st.sidebar.write(f"📍 Current location: {lat:.5f}, {lon:.5f}")

# --- MAP ---
m = folium.Map(location=[lat, lon], zoom_start=14)
folium.Marker([lat, lon], tooltip="You are here").add_to(m)

# --- INTERACTIVE MAP ---
map_data = st_folium.st_folium(m, width=700, height=500)

# --- ADD OBSERVATION ---
if map_data and map_data.get("last_clicked"):
    click_lat = map_data["last_clicked"]["lat"]
    click_lon = map_data["last_clicked"]["lng"]

    with st.form(f"obs_form_{uuid.uuid4()}"):
        st.write(f"🆕 New Observation at ({click_lat:.5f}, {click_lon:.5f})")
        title = st.text_input("Title")
        description = st.text_area("Description")
        category = st.selectbox("Category", ["Wildlife", "Infrastructure", "Other"])
        submit = st.form_submit_button("Save Observation")

        if submit:
            data = {
                "user": st.session_state.username,
                "lat": click_lat,
                "lon": click_lon,
                "title": title,
                "description": description,
                "category": category
            }
            supabase.table("observations").insert(data).execute()
            st.success("✅ Observation saved!")

