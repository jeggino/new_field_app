

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

# #_____________________3__________________




import streamlit as st
from streamlit_folium import st_folium
import folium
from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager
from datetime import datetime

# ----------------- CONFIG -----------------
st.set_page_config(page_title="Observations Map", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SECRET_PASSWORD = st.secrets["COOKIE_PASSWORD"]
USERS_TABLE = "users"
PROJECTS_TABLE = "projects"
OBS_TABLE = "observations"


# ----------------- INIT -----------------
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

cookies = EncryptedCookieManager(
    prefix="obs_app_5",
    password=SECRET_PASSWORD,
)
if not cookies.ready():
    st.stop()

defaults = {
    "logged_in": False,
    "username": None,
    "project": None,
    "observations": [],
    "selected_obs_id": None,
    "map_center": [0.0, 0.0],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ----------------- SUPABASE HELPERS -----------------
def login(username: str, password: str) -> bool:
    res = (
        supabase.table(USERS_TABLE)
        .select("*")
        .eq("username", username)
        .eq("password", password)
        .execute()
    )
    return len(res.data) == 1


def load_projects():
    res = supabase.table(PROJECTS_TABLE).select("*").execute()
    return res.data or []


def load_observations(project_name: str):
    res = (
        supabase.table(OBS_TABLE)
        .select("*")
        .eq("project", project_name)
        .execute()
    )
    st.session_state.observations = res.data or []


def insert_observation(data: dict):
    supabase.table(OBS_TABLE).insert(data).execute()
    load_observations(st.session_state.project)


def update_observation(obs_id: int, data: dict):
    supabase.table(OBS_TABLE).update(data).eq("id", obs_id).execute()
    load_observations(st.session_state.project)


def delete_observation(obs_id: int):
    supabase.table(OBS_TABLE).delete().eq("id", obs_id).execute()
    load_observations(st.session_state.project)


# ----------------- COOKIES -----------------
def set_login_cookies(username: str):
    cookies["logged_in"] = "1"
    cookies["username"] = username
    cookies.save()


def clear_login_cookies():
    for k in list(cookies.keys()):
        del cookies[k]
    cookies.save()


def restore_login_from_cookies():
    if cookies.get("logged_in") == "1" and not st.session_state.logged_in:
        st.session_state.logged_in = True
        st.session_state.username = cookies.get("username")


restore_login_from_cookies()


# ----------------- UI: LOGIN & PROJECT SELECT -----------------
def show_login():
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                set_login_cookies(username)
                st.rerun()
            else:
                st.error("Invalid credentials")


def show_project_selection():
    st.title("Select Project")
    projects = load_projects()
    if not projects:
        st.warning("No projects found in Supabase.")
        return

    project_names = [p["name"] for p in projects]
    selected = st.selectbox("Project", project_names)
    if st.button("Confirm project"):
        st.session_state.project = selected
        load_observations(selected)
        st.rerun()


# ----------------- DIALOGS -----------------
@st.dialog("New Observation")
def new_observation_dialog():
    st.write("Fill in the details and use the map center as position if you want.")

    col1, col2 = st.columns(2)
    with col1:
        species = st.text_input("Species")
        username = st.text_input("Username", value=st.session_state.username or "")
        behavior = st.text_input("Behavior")
    with col2:
        date = st.date_input("Date", value=datetime.utcnow().date())
        lat = st.number_input("Latitude", format="%.6f")
        lon = st.number_input("Longitude", format="%.6f")

    center_lat, center_lon = st.session_state.map_center

    st.markdown("**Map (center will be used if you click the button below)**")
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    folium.CircleMarker(
        location=[center_lat, center_lon],
        radius=6,
        color="red",
        fill=True,
        fill_color="red",
    ).add_to(m)

    st_folium(m, width="100%", height=400)

    if st.button("Use center of map as coordinates"):
        lat, lon = center_lat, center_lon
        st.info(f"Using center coordinates: lat={lat:.6f}, lon={lon:.6f}")

    if st.button("Save observation"):
        if lat is None or lon is None:
            st.warning("Please provide latitude and longitude (via button or manual input).")
            st.stop()
        if not species:
            st.warning("Species is required.")
            st.stop()

        data = {
            "species": species,
            "project": st.session_state.project,
            "username": username,
            "behavior": behavior,
            "date": str(date),
            "lat": float(lat),
            "lon": float(lon),
        }
        insert_observation(data)
        st.success("Observation saved.")
        st.rerun()


@st.dialog("Edit Observation")
def edit_observation_dialog(obs):
    st.write("Update the details and position.")

    col1, col2 = st.columns(2)
    with col1:
        species = st.text_input("Species", value=obs.get("species", ""))
        username = st.text_input("Username", value=obs.get("username", ""))
        behavior = st.text_input("Behavior", value=obs.get("behavior", ""))
    with col2:
        date = st.date_input(
            "Date",
            value=datetime.fromisoformat(obs.get("date")).date()
            if obs.get("date")
            else datetime.utcnow().date(),
        )
        lat = st.number_input("Latitude", value=float(obs.get("lat", 0)), format="%.6f")
        lon = st.number_input("Longitude", value=float(obs.get("lon", 0)), format="%.6f")

    st.markdown("**Map (you can reuse the main map center if desired)**")
    center_lat, center_lon = st.session_state.map_center
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    folium.CircleMarker(
        location=[center_lat, center_lon],
        radius=6,
        color="blue",
        fill=True,
        fill_color="blue",
    ).add_to(m)

    st_folium(m, width="100%", height=400)

    if st.button("Use center of map as coordinates (edit)"):
        lat, lon = center_lat, center_lon
        st.info(f"Using center coordinates: lat={lat:.6f}, lon={lon:.6f}")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Save changes"):
            if lat is None or lon is None:
                st.warning("Please provide latitude and longitude.")
                st.stop()
            data = {
                "species": species,
                "username": username,
                "behavior": behavior,
                "date": str(date),
                "lat": float(lat),
                "lon": float(lon),
            }
            update_observation(obs["id"], data)
            st.success("Observation updated.")
            st.rerun()
    with col_b:
        if st.button("Cancel"):
            st.rerun()


# ----------------- MAIN APP -----------------
def find_clicked_observation(click_lat, click_lon, observations, tol=1e-5):
    for o in observations:
        if abs(o["lat"] - click_lat) < tol and abs(o["lon"] - click_lon) < tol:
            return o
    return None


def show_main_app():
    st.title("Observations Map")

    # Sidebar
    with st.sidebar:
        st.subheader("Controls")

        st.markdown(
            """
            <style>
            .circle-btn button {
                border-radius: 50% !important;
                height: 60px !important;
                width: 60px !important;
                padding: 0 !important;
                font-size: 24px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="circle-btn">', unsafe_allow_html=True)
        if st.button("＋", key="add_obs_circle"):
            new_observation_dialog()
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Logout", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.project = None
            clear_login_cookies()
            st.rerun()

        st.markdown("---")
        st.write(f"User: **{st.session_state.username}**")
        st.write(f"Project: **{st.session_state.project}**")

    # Map center
    if st.session_state.observations:
        avg_lat = sum(o["lat"] for o in st.session_state.observations) / len(
            st.session_state.observations
        )
        avg_lon = sum(o["lon"] for o in st.session_state.observations) / len(
            st.session_state.observations
        )
        center = [avg_lat, avg_lon]
    else:
        center = [0.0, 0.0]

    st.session_state.map_center = center

    # Main map (mobile/laptop friendly)
    m = folium.Map(location=center, zoom_start=2)
    for obs in st.session_state.observations:
        popup_text = f"{obs.get('species', '')} ({obs.get('username', '')})"
        folium.Marker(
            location=[obs["lat"], obs["lon"]],
            popup=popup_text,
        ).add_to(m)

    map_data = st_folium(m, width="100%", height=500)

    selected_obs = None
    if map_data and map_data.get("last_object_clicked"):
        click_lat = map_data["last_object_clicked"]["lat"]
        click_lon = map_data["last_object_clicked"]["lng"]
        selected_obs = find_clicked_observation(
            click_lat, click_lon, st.session_state.observations
        )
        if selected_obs:
            st.session_state.selected_obs_id = selected_obs["id"]
        else:
            st.session_state.selected_obs_id = None
    else:
        selected_obs = None

    st.subheader("Observations")
    if not st.session_state.observations:
        st.info("No observations yet. Use the circular button in the sidebar to create one.")
        return

    if st.session_state.selected_obs_id is not None:
        selected_obs = next(
            (o for o in st.session_state.observations if o["id"] == st.session_state.selected_obs_id),
            None,
        )

    if selected_obs:
        st.table(
            {
                "Field": [
                    "ID",
                    "Species",
                    "Project",
                    "Username",
                    "Behavior",
                    "Date",
                    "Latitude",
                    "Longitude",
                ],
                "Value": [
                    selected_obs.get("id"),
                    selected_obs.get("species"),
                    selected_obs.get("project"),
                    selected_obs.get("username"),
                    selected_obs.get("behavior"),
                    selected_obs.get("date"),
                    selected_obs.get("lat"),
                    selected_obs.get("lon"),
                ],
            }
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Edit observation"):
                edit_observation_dialog(selected_obs)
        with col2:
            if st.button("Delete observation"):
                delete_observation(selected_obs["id"])
                st.success("Observation deleted.")
                st.session_state.selected_obs_id = None
                st.rerun()
    else:
        st.info("Click on a marker on the map to see its details.")


# ----------------- ROUTING -----------------
if not st.session_state.logged_in:
    show_login()
elif not st.session_state.project:
    show_project_selection()
else:
    show_main_app()
