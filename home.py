# import streamlit as st
# import streamlit_folium as st_folium
# import folium
# from supabase import create_client, Client
# import geocoder
# import uuid

# # --- CONFIG ---


# import streamlit as st
# from streamlit_folium import st_folium
# import folium
# from supabase import create_client, Client
# import uuid

# # --- CONFIG ---
# st.set_page_config(page_title="Geo Observations", layout="wide")
# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



# # --- SESSION LOGIN ---
# if "user" not in st.session_state:
#     st.session_state.user = None


# def login(email: str, password: str):
#     # Example: custom auth table "app_users" with columns: id, email, password
#     # In production, store hashed passwords and verify properly.
#     res = (
#         supabase.table("app_users")
#         .select("*")
#         .eq("email", email)
#         .eq("password", password)
#         .execute()
#     )
#     if res.data:
#         st.session_state.user = res.data[0]
#         st.session_state.logged_in = True
#         st.success("Logged in successfully")
#         st.rerun()
#     else:
#         st.error("Invalid credentials")

# def logout():
#     st.session_state.user = None
#     st.session_state.logged_in = False
#     st.rerun()






# # def login(username, password):
# #     # Replace with Supabase Auth if needed
# #     if username and password:
# #         st.session_state.user = {"username": username}
# #         st.success(f"Welcome {username}!")

# # def logout():
# #     st.session_state.user = None

# if not st.session_state.user:
#     st.title("🔐 Login")
#     with st.form("login_form"):
#         username = st.text_input("Username")
#         password = st.text_input("Password", type="password")
#         submit = st.form_submit_button("Login")
#         if submit:
#             login(username, password)
#     st.stop()

# # --- MAIN APP ---
# # st.sidebar.write(f"👤 Logged in as: {st.session_state.user['username']}")
# if st.sidebar.button("Logout"):
#     logout()
#     st.experimental_rerun()

# st.title("📍 Geo Observation Tool")

# # --- MAP ---
# m = folium.Map(location=[52.37, 4.90], zoom_start=12)
# map_data = st_folium(m, height=500, width=800)

# # --- OBSERVATION FORM ---
# if map_data and map_data.get("last_clicked"):
#     lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
#     st.subheader("📝 New Observation")
#     with st.form("obs_form"):
#         title = st.text_input("Title")
#         description = st.text_area("Description")
#         category = st.selectbox("Category", ["Wildlife", "Infrastructure", "Other"])
#         save_btn = st.form_submit_button("Save Observation")
#         if save_btn:
#             obs_id = str(uuid.uuid4())
#             supabase.table("observations").insert({
#                 "id": obs_id,
#                 "username": st.session_state.user,
#                 "lat": lat,
#                 "lon": lon,
#                 "title": title,
#                 "description": description,
#                 "category": category
#             }).execute()
#             st.success("✅ Observation saved!")

# # --- DISPLAY EXISTING OBSERVATIONS ---
# st.subheader("📂 Existing Observations")
# data = supabase.table("observations").select("*").execute()

# #--SECOND VERSION
# import streamlit as st
# import pandas as pd
# import plotly.express as px
# from datetime import datetime
# from supabase import create_client, Client
# import uuid

# # ----------------------------
# # CONFIGURATION
# # ----------------------------
# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# st.set_page_config(page_title="Observation Map", layout="wide")

# # ----------------------------
# # SESSION MANAGEMENT
# # ----------------------------
# if "user" not in st.session_state:
#     st.session_state.user = None

# def login(email, password):
#     try:
#         auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
#         st.session_state.user = auth_response.user
#         st.success("Logged in successfully!")
#     except Exception as e:
#         st.error(f"Login failed: {e}")

# def logout():
#     st.session_state.user = None
#     st.experimental_rerun()

# # ----------------------------
# # LOGIN SCREEN
# # ----------------------------
# if not st.session_state.user:
#     st.title("🔐 Login to Observation Map")
#     with st.form("login_form"):
#         email = st.text_input("Email")
#         password = st.text_input("Password", type="password")
#         submit = st.form_submit_button("Login")
#         if submit:
#             login(email, password)
#     st.stop()

# # ----------------------------
# # MAIN APP
# # ----------------------------
# st.title("📍 Interactive Observation Map")
# st.write(f"Welcome, **{st.session_state.user.email}**")
# st.button("Logout", on_click=logout)

# # Load existing observations
# def load_observations():
#     data = supabase.table("observations").select("*").execute()
#     return pd.DataFrame(data.data)

# df = load_observations()

# # Display map
# if not df.empty:
#     fig = px.scatter_mapbox(
#         df,
#         lat="latitude",
#         lon="longitude",
#         hover_name="description",
#         hover_data=["date"],
#         zoom=2,
#         height=600
#     )
#     fig.update_layout(mapbox_style="open-street-map")
#     st.plotly_chart(fig, use_container_width=True)
# else:
#     st.info("No observations yet. Add one below!")

# # ----------------------------
# # ADD OBSERVATION POP-UP
# # ----------------------------
# with st.expander("➕ Add New Observation"):
#     col1, col2 = st.columns(2)
#     with col1:
#         latitude = st.number_input("Latitude", format="%.6f")
#         longitude = st.number_input("Longitude", format="%.6f")
#     with col2:
#         date = st.date_input("Observation Date", datetime.today())
#         description = st.text_area("Description")

#     if st.button("Save Observation"):
#         if latitude and longitude and description:
#             supabase.table("observations").insert({
#                 "id": str(uuid.uuid4()),
#                 "user_id": st.session_state.user.id,
#                 "latitude": latitude,
#                 "longitude": longitude,
#                 "date": str(date),
#                 "description": description
#             }).execute()
#             st.success("Observation saved!")
#             st.experimental_rerun()
#         else:
#             st.error("Please fill in all required fields.")

# for obs in data.data:
#     st.write(f"**{obs['title']}** ({obs['lat']}, {obs['lon']}) - {obs['category']}")


# #----THIRD VERSION
# import streamlit as st
# import pandas as pd
# import plotly.express as px
# from datetime import datetime
# from supabase import create_client, Client
# import uuid

# # ----------------------------
# # CONFIGURATION
# # ----------------------------
# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# st.set_page_config(page_title="Observation Map", layout="wide")

# # ----------------------------
# # SESSION MANAGEMENT
# # ----------------------------
# if "user" not in st.session_state:
#     st.session_state.user = None

# def login(email, password):
#     try:
#         auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
#         st.session_state.user = auth_response.user
#         st.success("Logged in successfully!")
#     except Exception as e:
#         st.error(f"Login failed: {e}")

# def logout():
#     st.session_state.user = None
#     st.experimental_rerun()

# # ----------------------------
# # LOGIN SCREEN
# # ----------------------------
# if not st.session_state.user:
#     st.title("🔐 Login to Observation Map")
#     with st.form("login_form"):
#         email = st.text_input("Email")
#         password = st.text_input("Password", type="password")
#         submit = st.form_submit_button("Login")
#         if submit:
#             login(email, password)
#     st.stop()

# # ----------------------------
# # MAIN APP
# # ----------------------------
# st.title("📍 Interactive Observation Map")
# st.write(f"Welcome, **{st.session_state.user.email}**")
# st.button("Logout", on_click=logout)

# # Load existing observations
# def load_observations():
#     data = supabase.table("observations").select("*").execute()
#     return pd.DataFrame(data.data)

# df = load_observations()

# # Display map
# if not df.empty:
#     fig = px.scatter_mapbox(
#         df,
#         lat="latitude",
#         lon="longitude",
#         hover_name="description",
#         hover_data=["date"],
#         zoom=2,
#         height=600
#     )
#     fig.update_layout(mapbox_style="open-street-map")
#     st.plotly_chart(fig, use_container_width=True)
# else:
#     st.info("No observations yet. Add one below!")

# # ----------------------------
# # ADD OBSERVATION POP-UP
# # ----------------------------
# with st.expander("➕ Add New Observation"):
#     col1, col2 = st.columns(2)
#     with col1:
#         latitude = st.number_input("Latitude", format="%.6f")
#         longitude = st.number_input("Longitude", format="%.6f")
#     with col2:
#         date = st.date_input("Observation Date", datetime.today())
#         description = st.text_area("Description")

#     if st.button("Save Observation"):
#         if latitude and longitude and description:
#             supabase.table("observations").insert({
#                 "id": str(uuid.uuid4()),
#                 "user_id": st.session_state.user.id,
#                 "latitude": latitude,
#                 "longitude": longitude,
#                 "date": str(date),
#                 "description": description
#             }).execute()
#             st.success("Observation saved!")
#             st.experimental_rerun()
#         else:
#             st.error("Please fill in all required fields.")





















# import streamlit as st
# from streamlit_folium import st_folium
# import folium
# from datetime import date
# from supabase import create_client, Client
# from streamlit_cookies_manager import EncryptedCookieManager
# import uuid

# # ---------------------------
# # CONFIGURATION
# # ---------------------------
# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# # Cookie manager for persistent login
# cookies = EncryptedCookieManager(prefix="myapp_", password=st.secrets["COOKIE_PASSWORD"])
# if not cookies.ready():
#     st.stop()

# # ---------------------------
# # AUTHENTICATION
# # ---------------------------
# def login(username, password):
#     res = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
#     return len(res.data) > 0

# @st.dialog("Add New Observation")
# def insert():
#     st.write(f"📍 Location: {lat:.5f}, {lon:.5f}")
#     obs_id = str(uuid.uuid4())
#     desc = st.text_area("Description")
#     if st.button("Save Observation"):
#         supabase.table("observations").insert({
#             "id": obs_id,
#             "lat": lat,
#             "lon": lon,
#             "description": desc,
#             "username": st.session_state.username
#         }).execute()
#         st.success("Observation saved!")
#         st.rerun()


# if "logged_in" not in st.session_state:
#     st.session_state.logged_in = False

# if not st.session_state.logged_in:
#     saved_user = cookies.get("username")
#     if saved_user:
#         st.session_state.logged_in = True
#         st.session_state.username = saved_user
#     else:
#         st.title("🔐 Login")
        
#         user = st.text_input("Username")
#         pwd = st.text_input("Password", type="password")
#         if st.button("Login"):
#             if login(user, pwd):
#                 st.session_state.logged_in = True
#                 st.session_state.username = user
#                 cookies["username"] = user
#                 cookies.save()
#                 # st.experimental_rerun()
#             else:
#                 st.error("Invalid credentials")
#         st.stop()

# # ---------------------------
# # MAP & OBSERVATIONS
# # ---------------------------

# # Load existing observations
# obs_data = supabase.table("observations").select("*").execute().data

# # Create Folium map
# m = folium.Map(location=[52.37, 4.90], zoom_start=12)

# # Add existing markers
# for obs in obs_data:
#     folium.Marker(
#         location=[obs["lat"], obs["lon"]],
#         popup=f"{obs['description']}"
#     ).add_to(m)

# # Display map and capture click
# map_data = st_folium(m, height=500, width=300)

# # ---------------------------
# # ADD NEW OBSERVATION
# # ---------------------------
# if map_data and map_data.get("last_clicked"):
#     lat = map_data["last_clicked"]["lat"]
#     lon = map_data["last_clicked"]["lng"]
#     insert()

#----------------------------------

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

@st.dialog("Add new observation",width="large")
def new_observation_dialog(user):
    st.write("Drag the marker to the correct location and fill in the details.")

    default_location = [52.37, 4.90]  # Amsterdam-ish default
    m = folium.Map(location=default_location, zoom_start=15, control_scale=True)

    # Draggable marker
    draggable_marker = folium.Marker(
        location=default_location,
        draggable=True,
        popup="Drag me to the observation location",
        icon=folium.Icon(color="blue", icon="info-sign")
    )
    draggable_marker.add_to(m)

    map_data = st_folium(
        m,
        width="100%",
        height=400,
        returned_objects=["last_object_clicked", "last_active_drawing", "all_drawings"],
    )

    st.write("If the marker position is not captured, try clicking on the map after dragging.")
    
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
            st.error("Could not determine marker position. Try clicking on the map after dragging the marker.")
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

        if st.button("Add new observation", type="primary"):
            new_observation_dialog(user)

        if st.button("Log out"):
            clear_user_cookie()
            st.session_state.pop("user", None)
            st.rerun()

    st.markdown("---")

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

    m = folium.Map(location=center, zoom_start=13, control_scale=True)

    LocateControl(auto_start=true,position="topleft").add_to(m)
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
        height=500,
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
