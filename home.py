

# # app.py
# import json
# import os
# from datetime import datetime
# import uuid

# import streamlit as st
# from streamlit_folium import st_folium
# import folium
# from folium.plugins import Fullscreen, LocateControl

# from supabase import create_client, Client
# from streamlit_cookies_manager import EncryptedCookieManager

# # ---------- CONFIG ----------

# st.markdown(
#     """
#     <style>
#     [data-testid="collapsedControl"] svg {
#         height: 0rem;
#         width: 0rem;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True,
# )


# reduce_header_height_style = """
# <style>
#     div.block-container {padding-top: 2rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem; margin-top: 0rem; margin-bottom: 0rem;}
# </style>
# """ 

# st.markdown(reduce_header_height_style, unsafe_allow_html=True)

# st.set_page_config(page_title="Map Observations", layout="wide")

# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# USERS_TABLE = "users"
# OBS_TABLE = "observations"

# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# cookie_manager = EncryptedCookieManager(prefix="myapp_", password=st.secrets["COOKIE_PASSWORD"])


# if not cookie_manager.ready():
#     st.stop()

# # ---------- AUTH HELPERS ----------

# def load_user_from_cookie():
#     raw = cookie_manager.get("user")
#     if not raw:
#         return None
#     try:
#         return json.loads(raw)
#     except Exception:
#         return None


# def save_user_to_cookie(user_dict: dict):
#     cookie_manager["user"] = json.dumps(user_dict)
#     cookie_manager.save()


# def clear_user_cookie():
#     cookie_manager.pop("user", None)
#     cookie_manager.save()


# def validate_credentials(username: str, password: str):
#     # Example: simple username/password stored in a Supabase table
#     # You should hash passwords in a real app
#     res = (
#         supabase.table(USERS_TABLE)
#         .select("*")
#         .eq("username", username)
#         .eq("password", password)
#         .maybe_single()
#         .execute()
#     )
#     return res.data


# # ---------- LOGIN VIEW ----------

# def login_view():

#     username = st.text_input("Username")
#     password = st.text_input("Password", type="password")

#     col1, col2 = st.columns([1, 3])
#     with col1:
#         login_clicked = st.button("Log in", type="primary")

#     if login_clicked:
#         if not username or not password:
#             st.error("Please enter both username and password.")
#             return

#         user = validate_credentials(username, password)
#         if user:
#             st.session_state["user"] = user
#             save_user_to_cookie(user)
#             st.success("Logged in successfully.")
#             st.rerun()
#         else:
#             st.error("Invalid credentials.")


# # ---------- DIALOG FOR NEW OBSERVATION ----------

# @st.dialog(" ",width="large")
# def new_observation_dialog(user):
#     st.write("Drag the marker to the correct location and click on it to capture the coordinates.")

#     default_location = [52.37, 4.90]  # Amsterdam-ish default
#     m = folium.Map(location=default_location, zoom_start=18, control_scale=False,zoom_control=False)
#     Fullscreen(position="topleft").add_to(m)


#     # Draggable marker
#     draggable_marker = folium.Marker(
#         location=default_location,
#         draggable=True,
#         popup="locations recorded!",
#         icon=folium.Icon(color="blue", icon="info-sign")
#     )
#     draggable_marker.add_to(m)

#     map_data = st_folium(
#         m,
#         width="100%",
#         height=300,
#         returned_objects=["last_object_clicked", "last_active_drawing", "all_drawings"],
#     )

    
#     obs_id = str(uuid.uuid4())
#     title = st.text_input("Title")
#     description = st.text_area("Description")
#     category = st.selectbox("Category", ["General", "Issue", "Point of interest", "Other"])


#     save_clicked = st.button("Save observation", type="primary")

#     if save_clicked:
#         # Try to infer marker position from map_data
#         lat, lon = None, None

#         # 1. From last click
#         if map_data and map_data.get("last_object_clicked"):
#             loc = map_data["last_object_clicked"]
#             lat, lon = loc.get("lat"), loc.get("lng")

#         # 2. Fallback: from last drawing (if any)
#         if (lat is None or lon is None) and map_data and map_data.get("last_active_drawing"):
#             loc = map_data["last_active_drawing"]
#             if isinstance(loc, dict) and "geometry" in loc:
#                 coords = loc["geometry"]["coordinates"]
#                 if isinstance(coords, (list, tuple)) and len(coords) >= 2:
#                     lon, lat = coords[0], coords[1]

#         if lat is None or lon is None:
#             st.error("Could not determine marker position. Try clicking on the marker after dragging it.")
#             return

#         if not title:
#             st.error("Please provide a title.")
#             return

#         payload = {
#             "username": user["id"],
#             "title": title,
#             "description": description,
#             "category": category,
#             "id": obs_id,
#             "lat": lat,
#             "lon": lon,

#         }

#         try:
#             supabase.table(OBS_TABLE).insert(payload).execute()
#             st.success("Observation saved.")
#             st.rerun()
#         except Exception as e:
#             st.error(f"Failed to save observation: {e}")


# # ---------- MAIN APP VIEW ----------

# def main_app(user):
#     with st.sidebar:

#         if st.button("Log out"):
#             clear_user_cookie()
#             st.session_state.pop("user", None)
#             st.rerun()
            
#         st.divider(width="stretch")
        
#         if st.button("Add new observation", icon=":material/add_location_alt:",type="primary",width="stretch" ):
#             new_observation_dialog(user)

#     # Load existing observations
#     try:
#         res = (
#             supabase.table(OBS_TABLE)
#             .select("*")
#             .execute()
#         )
#         observations = res.data or []
#     except Exception as e:
#         st.error(f"Failed to load observations: {e}")
#         observations = []

#     # Determine map center
#     if observations:
#         avg_lat = sum(o["lat"] for o in observations) / len(observations)
#         avg_lon = sum(o["lon"] for o in observations) / len(observations)
#         center = [avg_lat, avg_lon]
#     else:
#         center = [52.37, 4.90]

#     m = folium.Map(location=center, zoom_start=13, control_scale=False,zoom_control=False)

#     LocateControl(auto_start=True,position="topleft").add_to(m)
#     Fullscreen(position="topleft").add_to(m)

#     for obs in observations:
#         popup_html = f"""
#         <b>{obs.get('title', 'No title')}</b><br>
#         {obs.get('description', '')}<br>
#         <i>Category:</i> {obs.get('category', 'N/A')}<br>
#         <i>Created:</i> {obs.get('created_at', '')}
#         """
#         folium.Marker(
#             location=[obs["lat"], obs["lon"]],
#             popup=popup_html,
#             icon=folium.Icon(color="blue", icon="info-sign"),
#         ).add_to(m)

#     st_folium(
#         m,
        
#         width="100%",
#         height=550,
#     )

#     st.markdown("")

#     # add_col1, _ = st.columns([1, 3])
#     # with add_col1:
#     #     if st.button("Add new observation", type="primary"):
#     #         new_observation_dialog(user)


# # ---------- ENTRY POINT ----------

# def main():
#     # Restore user from cookie if possible
#     if "user" not in st.session_state:
#         user = load_user_from_cookie()
#         if user:
#             st.session_state["user"] = user

#     user = st.session_state.get("user")

#     if not user:
#         login_view()
#     else:
#         main_app(user)


# if __name__ == "__main__":
#     main()


# #_____________________SECOND__________________
# # app.py
# import os
# import json
# from datetime import datetime
# from typing import Optional
# import uuid
# import pandas as pd

# import streamlit as st
# from streamlit_folium import st_folium
# import folium
# from folium.plugins import LocateControl

# from supabase import create_client, Client
# from streamlit_cookies_manager import EncryptedCookieManager

# # ----------------- CONFIG -----------------
# st.set_page_config(page_title="Geo Observations", layout="wide")






# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# USERS_TABLE = "users"
# OBS_TABLE = "observations"

# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# cookie_manager = EncryptedCookieManager(prefix="myapp_", password=st.secrets["COOKIE_PASSWORD"])


# if not cookie_manager.ready():
#     st.stop()

# # ---------- AUTH HELPERS ----------

# def load_user_from_cookie():
#     raw = cookie_manager.get("user")
#     if not raw:
#         return None
#     try:
#         return json.loads(raw)
#     except Exception:
#         return None


# def save_user_to_cookie(user_dict: dict):
#     cookie_manager["user"] = json.dumps(user_dict)
#     cookie_manager.save()


# def clear_user_cookie():
#     cookie_manager.pop("user", None)
#     cookie_manager.save()


# def validate_credentials(username: str, password: str):
#     # Example: simple username/password stored in a Supabase table
#     # You should hash passwords in a real app
#     res = (
#         supabase.table(USERS_TABLE)
#         .select("*")
#         .eq("username", username)
#         .eq("password", password)
#         .maybe_single()
#         .execute()
#     )
#     return res.data






# # ----------------- SUPABASE CRUD -----------------
# def fetch_observations():
#     try:
#         res = supabase.table(OBS_TABLE).select("*").execute()
#         return res.data or []
#     except Exception as e:
#         st.error(f"Failed to load observations: {e}")
#         return []


# def insert_observation(payload: dict) -> bool:
#     try:
#         supabase.table(OBS_TABLE).insert(payload).execute()
#         return True
#     except Exception as e:
#         st.error(f"Failed to insert observation: {e}")
#         return False


# def update_observation(obs_id: str, payload: dict) -> bool:
#     try:
#         supabase.table(OBS_TABLE).update(payload).eq("id", obs_id).execute()
#         return True
#     except Exception as e:
#         st.error(f"Failed to update observation: {e}")
#         return False


# def delete_observation(obs_id: str) -> bool:
#     try:
#         supabase.table(OBS_TABLE).delete().eq("id", obs_id).execute()
#         return True
#     except Exception as e:
#         st.error(f"Failed to delete observation: {e}")
#         return False


# # ----------------- LOGIN VIEW -----------------
# def login_view():
#     st.title("Login")

#     username = st.text_input("Username")
#     password = st.text_input("Password", type="password")

#     if st.button("Log in", type="primary"):
#         if not username or not password:
#             st.error("Please enter both username and password.")
#             return

#         user = validate_credentials(username, password)
#         if user:
#             st.session_state["user"] = user
#             save_user_to_cookie(user)
#             st.success("Logged in.")
#             st.rerun()
#         else:
#             st.error("Invalid credentials.")


# # ----------------- DIALOG: ADD / EDIT OBS -----------------
# def open_observation_dialog(user: dict, obs: Optional[dict] = None):
#     title = "Edit observation" if obs else "Add new observation"

#     @st.dialog(title)
#     def _dialog():
#         st.write("Drag the marker to the correct location and click on the map to capture coordinates.")

#         # Default center: last map center or existing obs location or fallback
#         # default_center = st.session_state.get("map_center")

#         # default_center = ["lat", "lon"]
#         st.write(st.session_state.get("map_center"))
#         default_center = st.session_state.get("map_center")
#         m = folium.Map(location=default_center, zoom_start=16, control_scale=False)

#         folium.Marker(
#             location=default_center,
#             draggable=True,
#             popup="Drag me to the observation location",
#             icon=folium.Icon(color="blue", icon="info-sign"),
#         ).add_to(m)

#         map_data = st_folium(
#             m,
#             width="100%",
#             height=360,
#             returned_objects=["last_object_clicked", "last_active_drawing"],
#         )

#         obs_id = str(uuid.uuid4())
#         title_val = st.text_input("Title", value=obs.get("title", "") if obs else "")
#         description_val = st.text_area("Description", value=obs.get("description", "") if obs else "")
#         category_val = st.selectbox(
#             "Category",
#             ["General", "Issue", "Point of Interest", "Other"],
#             index=(
#                 ["General", "Issue", "Point of Interest", "Other"].index(obs.get("category"))
#                 if obs and obs.get("category") in ["General", "Issue", "Point of Interest", "Other"]
#                 else 0
#             ),
#         )
#         notes_val = st.text_area("Notes (optional)", value=obs.get("notes", "") if obs else "")

#         # Determine coordinates
#         lat, lon = None, None
#         if map_data and map_data.get("last_object_clicked"):
#             loc = map_data["last_object_clicked"]
#             lat, lon = loc.get("lat"), loc.get("lng")

#         if (lat is None or lon is None) and map_data and map_data.get("last_active_drawing"):
#             drawing = map_data["last_active_drawing"]
#             if isinstance(drawing, dict) and "geometry" in drawing:
#                 coords = drawing["geometry"].get("coordinates")
#                 if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
#                     lon, lat = coords[0], coords[1]

#         if obs and (lat is None or lon is None):
#             lat, lon = obs.get("lat"), obs.get("lon")

#         if st.button("Save", type="primary",width="stretch"):
#             if not title_val:
#                 st.error("Title is required.")
#                 return
#             if lat is None or lon is None:
#                 st.error("Could not determine coordinates. Drag the marker and click on the map.")
#                 return

#             payload = {
#                 "id": obs_id,
#                 "title": title_val,
#                 "description": description_val,
#                 "category": category_val,
#                 "lat": lat,
#                 "lon": lon,
#                 "username": user["id"]

#             }

#             ok = update_observation(obs["id"], payload) if obs else insert_observation(payload)
#             if ok:
#                 st.success("Observation saved.")
#                 st.rerun()
#             else:
#                 st.error("Failed to save observation.")

#     _dialog()


# # ----------------- MAIN APP -----------------
# def main_app(user: dict):

#     with st.sidebar:
#         if st.button("Log out",width="stretch"):
#             clear_user_cookie()
#             st.session_state.pop("user", None)
#             st.rerun()

#         st.divider()

#         if st.button("Add new observation", type="primary",width="stretch"):
#             open_observation_dialog(user, obs=None)

#     observations = fetch_observations()

#     # Map center: last center, or average of observations, or fallback
#     if "map_center" in st.session_state:
#         center = st.session_state["map_center"]
#     elif observations:
#         avg_lat = sum(o["lat"] for o in observations) / len(observations)
#         avg_lon = sum(o["lon"] for o in observations) / len(observations)
#         center = [avg_lat, avg_lon]
#     else:
#         center = [52.37, 4.90]

#     m = folium.Map(location=center, zoom_start=13, control_scale=True)
#     LocateControl(auto_start=False).add_to(m)

#     # Add markers with click-to-edit/delete behavior
#     for obs in observations:
#         popup_html = f"""
#         <b>{obs.get('title','')}</b><br>
#         {obs.get('description','')}<br>
#         <i>Category:</i> {obs.get('category','')}<br>
#         <i>Created:</i> {obs.get('created_at','')}
#         """
#         folium.Marker(
#             location=[obs["lat"], obs["lon"]],
#             popup=obs["id"],
#             icon=folium.Icon(color="blue", icon="info-sign"),
#         ).add_to(m)

#     map_state = st_folium(
#         m,
#         width="100%",
#         height=600,
#         returned_objects=["center","last_object_clicked_popup","last_object_clicked_id"],
#     )

#     # loc = map_state["center"]
#     # st.session_state["map_center"] = [loc.get("lat"), loc.get("lng")]
#     st.write(map_state)
#     loc = map_state["center"]
#     st.session_state["map_center"] = [loc.get("lat"), loc.get("lng")]
#     # st.write(observations)
#     # df = pd.DataFrame(observations).set_index("id")
    

    
#     if map_state.get("last_object_clicked_popup"):
#         # st.write(df.loc[map_state.get("last_object_clicked_popup")])
#         # df = pd.DataFrame(observations)
#         # # # st.write(observations)
#         # # df
#         # c1, c2 = st.columns(2)
#         # with c1:
#         #     if st.button("Edit", key=f"edit_{obs['id']}"):
#         #         open_observation_dialog(user, obs=obs)
#         # with c2:
#         if st.button("Delete"):
#             if delete_observation(map_state.get("last_object_clicked_popup")):
#                 st.success("Observation deleted.")
#                 st.rerun()
#     # # Store last clicked location as map_center (for default marker position)
#     # if map_state or map_state.get("last_object_clicked"):
#     #     loc = map_state["center"]
#     #     st.session_state["map_center"] = [loc.get("lat"), loc.get("lng")]

#     #     st.markdown("---")
    
#     #     st.markdown("### Observations list")
#     #     st.write(map_state)
#     #     if not observations:
#     #         st.info("No observations yet.")
#     #     else:
#     #         for obs in observations:
#     #             with st.expander(f"{obs.get('title','(no title)')} — {obs.get('category','')}"):
#     #                 st.write(obs.get("description", ""))
#     #                 st.caption(f"Created: {obs.get('created_at','')}")
#     #                 c1, c2 = st.columns(2)
#     #                 with c1:
#     #                     if st.button("Edit", key=f"edit_{obs['id']}"):
#     #                         open_observation_dialog(user, obs=obs)
#     #                 with c2:
#     #                     if st.button("Delete", key=f"del_{obs['id']}"):
#     #                         if delete_observation(obs["id"]):
#     #                             st.success("Observation deleted.")
#     #                             st.rerun()


# # ----------------- ENTRY POINT -----------------
# def main():
#     if "user" not in st.session_state:
#         user = load_user_from_cookie()
#         if user:
#             st.session_state["user"] = user

#     user = st.session_state.get("user")

#     if not user:
#         login_view()
#     else:
#         main_app(user)


# if __name__ == "__main__":
#     main()

#_____________________3__________________
import streamlit as st
from streamlit_folium import st_folium
import folium
from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager

# -----------------------------
# CONFIG & INITIALIZATION
# -----------------------------
st.set_page_config(page_title="Observation Map", layout="wide")

# Cookie manager (for login persistence)
cookies = EncryptedCookieManager(
    prefix="obs_app_",
    password=st.secrets["COOKIE_PASSWORD"],  # or use env var
)
if not cookies.ready():
    st.stop()


SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# USERS_TABLE = "users"
# OBS_TABLE = "observations"

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# -----------------------------
# SESSION STATE HELPERS
# -----------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "project" not in st.session_state:
    st.session_state.project = None
if "observations" not in st.session_state:
    st.session_state.observations = []
if "selected_obs" not in st.session_state:
    st.session_state.selected_obs = None
if "new_marker_location" not in st.session_state:
    st.session_state.new_marker_location = None

# -----------------------------
# AUTH & PROJECT SELECTION
# -----------------------------
def load_user_from_cookies():
    user_id = cookies.get("user_id")
    if user_id:
        res = (
            supabase.table("users")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if res.data:
            st.session_state.user = res.data

def save_user_to_cookies(user):
    cookies["user_id"] = str(user["id"])
    cookies.save()

def clear_user():
    st.session_state.user = None
    st.session_state.project = None
    cookies.pop("user_id", None)
    cookies.save()

def login(username, password):
    # Example: users table with columns: id, username, password_hash (simplified here)
    res = (
        supabase.table("users")
        .select("*")
        .eq("username", username)
        .eq("password", password)  # in real app: verify hash!
        .single()
        .execute()
    )
    return res.data

def get_projects_for_user(user_id):
    # Example: projects table with columns: id, name, user_id (or shared)
    res = (
        supabase.table("projects")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return res.data or []

def load_observations(project_id):
    # Example: observations table with columns:
    # id, project_id, lat, lon, title, description, extra_json
    res = (
        supabase.table("observations")
        .select("*")
        .eq("project_id", project_id)
        .execute()
    )
    return res.data or []

def create_observation(project_id, lat, lon, title, description, extra):
    res = (
        supabase.table("observations")
        .insert(
            {
                "project_id": project_id,
                "lat": lat,
                "lon": lon,
                "title": title,
                "description": description,
                "extra_json": extra,
            }
        )
        .execute()
    )
    return res.data[0] if res.data else None

def update_observation(obs_id, lat, lon, title, description, extra):
    res = (
        supabase.table("observations")
        .update(
            {
                "lat": lat,
                "lon": lon,
                "title": title,
                "description": description,
                "extra_json": extra,
            }
        )
        .eq("id", obs_id)
        .execute()
    )
    return res.data[0] if res.data else None

# -----------------------------
# DIALOGS
# -----------------------------
@st.dialog("Login")
def login_dialog():
    st.write("Please log in to continue.")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", type="primary"):
            user = login(username, password)
            if user:
                st.session_state.user = user
                save_user_to_cookies(user)
                st.rerun()
            else:
                st.error("Invalid credentials.")
    with col2:
        if st.button("Cancel"):
            st.stop()

@st.dialog("Select project")
def project_dialog():
    st.write("Choose a project to work on.")
    projects = get_projects_for_user(st.session_state.user["id"])
    if not projects:
        st.info("No projects found for this user.")
        if st.button("Close"):
            st.stop()
    else:
        project_names = [p["name"] for p in projects]
        selected_name = st.selectbox("Project", project_names)
        if st.button("Confirm", type="primary"):
            selected_project = next(p for p in projects if p["name"] == selected_name)
            st.session_state.project = selected_project
            st.session_state.observations = load_observations(selected_project["id"])
            st.rerun()

@st.dialog("New observation")
def new_observation_dialog():
    lat, lon = st.session_state.new_marker_location
    st.write(f"New observation at: {lat:.5f}, {lon:.5f}")
    title = st.text_input("Title")
    description = st.text_area("Description")
    extra_field_1 = st.text_input("Extra field 1")
    extra_field_2 = st.text_input("Extra field 2")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save", type="primary"):
            extra = {
                "extra_field_1": extra_field_1,
                "extra_field_2": extra_field_2,
            }
            obs = create_observation(
                st.session_state.project["id"],
                lat,
                lon,
                title,
                description,
            )
            if obs:
                st.session_state.observations.append(obs)
            st.session_state.new_marker_location = None
            st.rerun()
    with col2:
        if st.button("Cancel"):
            st.session_state.new_marker_location = None
            st.rerun()

@st.dialog("Observation details")
def observation_dialog():
    obs = st.session_state.selected_obs
    if obs is None:
        st.stop()

    st.write(f"ID: {obs['id']}")
    st.write(f"Location: {obs['lat']:.5f}, {obs['lon']:.5f}")
    title = st.text_input("Title", value=obs.get("title", ""))
    description = st.text_area("Description", value=obs.get("description", ""))

    extra = obs.get("extra_json") or {}
    extra_field_1 = st.text_input("Extra field 1", value=extra.get("extra_field_1", ""))
    extra_field_2 = st.text_input("Extra field 2", value=extra.get("extra_field_2", ""))

    st.write("Drag the marker on the map to update position (will be saved on Edit).")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Edit", type="primary"):
            # Use possibly updated position from session_state
            lat = obs["lat"]
            lon = obs["lon"]
            if "edit_position" in st.session_state and st.session_state["edit_position"]:
                lat, lon = st.session_state["edit_position"]

            updated = update_observation(
                obs["id"],
                lat,
                lon,
                title,
                description,
                {
                    "extra_field_1": extra_field_1,
                    "extra_field_2": extra_field_2,
                },
            )
            # Update local list
            if updated:
                for i, o in enumerate(st.session_state.observations):
                    if o["id"] == updated["id"]:
                        st.session_state.observations[i] = updated
                        break
            st.session_state.selected_obs = None
            st.session_state["edit_position"] = None
            st.rerun()
    with col2:
        if st.button("Cancel"):
            st.session_state.selected_obs = None
            st.session_state["edit_position"] = None
            st.rerun()

# -----------------------------
# MAIN FLOW: AUTH & PROJECT
# -----------------------------
load_user_from_cookies()

if st.session_state.user is None:
    login_dialog()

if st.session_state.project is None and st.session_state.user is not None:
    project_dialog()

# -----------------------------
# LAYOUT
# -----------------------------
st.title("Observation Map")

top_col1, top_col2, top_col3 = st.columns([3, 1, 1])
with top_col1:
    st.markdown(f"**User:** {st.session_state.user['username']}")
    # st.markdown(f"**Project:** {st.session_state.project['name']}")
with top_col2:
    if st.button("Change project"):
        project_dialog()
with top_col3:
    if st.button("Logout"):
        clear_user()
        st.rerun()

st.markdown("---")

# -----------------------------
# MAP SETUP
# -----------------------------
# Center map on average of observations or default
if st.session_state.observations:
    avg_lat = sum(o["lat"] for o in st.session_state.observations) / len(
        st.session_state.observations
    )
    avg_lon = sum(o["lon"] for o in st.session_state.observations) / len(
        st.session_state.observations
    )
else:
    avg_lat, avg_lon = 52.37, 4.90  # Example: Amsterdam

m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12, control_scale=True)

# Add existing observations as markers
for obs in st.session_state.observations:
    popup_html = f"""
    <b>{obs.get('title','No title')}</b><br>
    {obs.get('description','')}<br>
    <i>Click marker in app to view/edit.</i>
    """
    folium.Marker(
        location=[obs["lat"], obs["lon"]],
        popup=popup_html,
        tooltip=obs.get("title", "Observation"),
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(m)

# Draggable marker for new observation
if st.session_state.new_marker_location:
    lat, lon = st.session_state.new_marker_location
else:
    lat, lon = avg_lat, avg_lon

draggable_marker = folium.Marker(
    location=[lat, lon],
    draggable=True,
    icon=folium.Icon(color="red", icon="plus"),
)
draggable_marker.add_to(m)

# Render map (responsive height/width)
map_data = st_folium(
    m,
    width="100%",
    height=500,
    returned_objects=["last_object_clicked", "last_active_drawing", "last_marker_dragging"],
)

# -----------------------------
# MAP INTERACTIONS
# -----------------------------
# 1. Handle draggable marker for new observation
if map_data and map_data.get("last_marker_dragging"):
    drag = map_data["last_marker_dragging"]
    st.session_state.new_marker_location = (drag["lat"], drag["lng"])

# 2. Handle click on existing markers (approximate by nearest observation)
if map_data and map_data.get("last_object_clicked"):
    click = map_data["last_object_clicked"]
    click_lat, click_lon = click["lat"], click["lng"]

    # Find nearest observation within small threshold
    def distance_sq(o):
        return (o["lat"] - click_lat) ** 2 + (o["lon"] - click_lon) ** 2

    if st.session_state.observations:
        nearest = min(st.session_state.observations, key=distance_sq)
        # You can tune this threshold
        if distance_sq(nearest) < 0.0001:
            st.session_state.selected_obs = nearest
            observation_dialog()

# 3. Circular button to add new observation
st.markdown(
    """
    <style>
    .circle-btn {
        width: 60px;
        height: 60px;
        border-radius: 30px;
        background-color: #FF4B4B;
        color: white;
        border: none;
        font-size: 30px;
        text-align: center;
        line-height: 60px;
        cursor: pointer;
    }
    .circle-btn-container {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9999;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

circle_col = st.container()
with circle_col:
    st.markdown(
        """
        <div class="circle-btn-container">
            <button class="circle-btn" onclick="window.dispatchEvent(new Event('addObservation'))">+</button>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Small JS hack: we can't directly catch JS events in Streamlit,
# so we simulate with a button in the UI.
st.write("")
add_obs = st.button("Add observation (mobile-friendly alternative)", type="primary")

if add_obs:
    # Use current draggable marker position as starting point
    if st.session_state.new_marker_location is None:
        st.session_state.new_marker_location = (avg_lat, avg_lon)
    new_observation_dialog()

# If user has dragged marker but not clicked button yet, show hint
if st.session_state.new_marker_location and not add_obs:
    st.info("Drag the red marker, then click 'Add observation' to save it.")

# For editing position of existing observation:
# We reuse the same draggable marker; when an observation is selected,
# user can drag marker and then click Edit in dialog.
if st.session_state.selected_obs and map_data and map_data.get("last_marker_dragging"):
    drag = map_data["last_marker_dragging"]
    st.session_state["edit_position"] = (drag["lat"], drag["lng"])


