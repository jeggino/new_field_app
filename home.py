

# app.py
import json
import os
from datetime import datetime
import uuid

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Fullscreen, LocateControl

from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager

# ---------- CONFIG ----------

st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] svg {
        height: 0rem;
        width: 0rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


reduce_header_height_style = """
<style>
    div.block-container {padding-top: 2rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem; margin-top: 0rem; margin-bottom: 0rem;}
</style>
""" 

st.markdown(reduce_header_height_style, unsafe_allow_html=True)

st.set_page_config(page_title="Map Observations", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
USERS_TABLE = "users"
OBS_TABLE = "observations"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

cookie_manager = EncryptedCookieManager(prefix="myapp_", password=st.secrets["COOKIE_PASSWORD"])


if not cookie_manager.ready():
    st.stop()

# ---------- AUTH HELPERS ----------

def load_user_from_cookie():
    raw = cookie_manager.get("user")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def save_user_to_cookie(user_dict: dict):
    cookie_manager["user"] = json.dumps(user_dict)
    cookie_manager.save()


def clear_user_cookie():
    cookie_manager.pop("user", None)
    cookie_manager.save()


def validate_credentials(username: str, password: str):
    # Example: simple username/password stored in a Supabase table
    # You should hash passwords in a real app
    res = (
        supabase.table(USERS_TABLE)
        .select("*")
        .eq("username", username)
        .eq("password", password)
        .maybe_single()
        .execute()
    )
    return res.data


# ---------- LOGIN VIEW ----------

def login_view():

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns([1, 3])
    with col1:
        login_clicked = st.button("Log in", type="primary")

    if login_clicked:
        if not username or not password:
            st.error("Please enter both username and password.")
            return

        user = validate_credentials(username, password)
        if user:
            st.session_state["user"] = user
            save_user_to_cookie(user)
            st.success("Logged in successfully.")
            st.rerun()
        else:
            st.error("Invalid credentials.")


# ---------- DIALOG FOR NEW OBSERVATION ----------

@st.dialog(" ",width="large")
def new_observation_dialog(user):
    st.write("Drag the marker to the correct location and click on it to capture the coordinates.")

    default_location = [52.37, 4.90]  # Amsterdam-ish default
    m = folium.Map(location=default_location, zoom_start=18, control_scale=False,zoom_control=False)
    Fullscreen(position="topleft").add_to(m)


    # Draggable marker
    draggable_marker = folium.Marker(
        location=default_location,
        draggable=True,
        popup="locations recorded!",
        icon=folium.Icon(color="blue", icon="info-sign")
    )
    draggable_marker.add_to(m)

    map_data = st_folium(
        m,
        width="100%",
        height=300,
        returned_objects=["last_object_clicked", "last_active_drawing", "all_drawings"],
    )

    
    obs_id = str(uuid.uuid4())
    title = st.text_input("Title")
    description = st.text_area("Description")
    category = st.selectbox("Category", ["General", "Issue", "Point of interest", "Other"])


    save_clicked = st.button("Save observation", type="primary")

    if save_clicked:
        # Try to infer marker position from map_data
        lat, lon = None, None

        # 1. From last click
        if map_data and map_data.get("last_object_clicked"):
            loc = map_data["last_object_clicked"]
            lat, lon = loc.get("lat"), loc.get("lng")

        # 2. Fallback: from last drawing (if any)
        if (lat is None or lon is None) and map_data and map_data.get("last_active_drawing"):
            loc = map_data["last_active_drawing"]
            if isinstance(loc, dict) and "geometry" in loc:
                coords = loc["geometry"]["coordinates"]
                if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]

        if lat is None or lon is None:
            st.error("Could not determine marker position. Try clicking on the marker after dragging it.")
            return

        if not title:
            st.error("Please provide a title.")
            return

        payload = {
            "username": user["id"],
            "title": title,
            "description": description,
            "category": category,
            "id": obs_id,
            "lat": lat,
            "lon": lon,

        }

        try:
            supabase.table(OBS_TABLE).insert(payload).execute()
            st.success("Observation saved.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save observation: {e}")


# ---------- MAIN APP VIEW ----------

def main_app(user):
    with st.sidebar:

        if st.button("Log out"):
            clear_user_cookie()
            st.session_state.pop("user", None)
            st.rerun()
            
        st.divider(width="stretch")
        
        if st.button("Add new observation", icon=":material/add_location_alt:",type="primary"):
            new_observation_dialog(user)

    # Load existing observations
    try:
        res = (
            supabase.table(OBS_TABLE)
            .select("*")
            .execute()
        )
        observations = res.data or []
    except Exception as e:
        st.error(f"Failed to load observations: {e}")
        observations = []

    # Determine map center
    if observations:
        avg_lat = sum(o["lat"] for o in observations) / len(observations)
        avg_lon = sum(o["lon"] for o in observations) / len(observations)
        center = [avg_lat, avg_lon]
    else:
        center = [52.37, 4.90]

    m = folium.Map(location=center, zoom_start=13, control_scale=False,zoom_control=False)

    LocateControl(auto_start=True,position="topleft").add_to(m)
    Fullscreen(position="topleft").add_to(m)

    for obs in observations:
        popup_html = f"""
        <b>{obs.get('title', 'No title')}</b><br>
        {obs.get('description', '')}<br>
        <i>Category:</i> {obs.get('category', 'N/A')}<br>
        <i>Created:</i> {obs.get('created_at', '')}
        """
        folium.Marker(
            location=[obs["lat"], obs["lon"]],
            popup=popup_html,
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(m)

    st_folium(
        m,
        
        width="100%",
        height=600,
    )

    st.markdown("")

    # add_col1, _ = st.columns([1, 3])
    # with add_col1:
    #     if st.button("Add new observation", type="primary"):
    #         new_observation_dialog(user)


# ---------- ENTRY POINT ----------

def main():
    # Restore user from cookie if possible
    if "user" not in st.session_state:
        user = load_user_from_cookie()
        if user:
            st.session_state["user"] = user

    user = st.session_state.get("user")

    if not user:
        login_view()
    else:
        main_app(user)


if __name__ == "__main__":
    main()
