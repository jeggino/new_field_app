# import streamlit as st
# from streamlit_folium import st_folium
# import folium
# import json
# from supabase import create_client
# from folium.plugins import Geocoder, Fullscreen, Draw
# import pandas as pd





# # ---------------------------------------------------------
# # USERNAME + PASSWORD LOGIN (from st.secrets)
# # ---------------------------------------------------------
# if "authenticated" not in st.session_state:
#     st.session_state.authenticated = False

# if not st.session_state.authenticated:

#     st.title("Login")

#     username = st.text_input("Username")
#     password = st.text_input("Password", type="password")

#     if st.button("Login"):

#         allowed_users = st.secrets["users"]  # [users] section in secrets.toml

#         if username not in allowed_users:
#             st.error("Unknown username")
#             st.stop()

#         if password != allowed_users[username]:
#             st.error("Incorrect password")
#             st.stop()

#         st.session_state.authenticated = True
#         st.session_state.username = username
#         st.success("Login successful")

#         st.rerun()

#     st.stop()

# # ---------------------------------------------------------
# # SUPABASE SETUP
# # ---------------------------------------------------------
# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# BUCKET = "observation_photos"

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# # ---------------------------------------------------------
# # HELPERS
# # ---------------------------------------------------------
# def load_project_boundary(project_name):
#     """Load <project>.geojson from Supabase and return (geojson_dict, bounds)."""

#     filename = f"{project_name}.geojson"

#     try:
#         file_bytes = supabase.storage.from_(BUCKET).download(filename)
#         if not file_bytes:
#             return None, None

#         geojson_str = file_bytes.decode("utf-8")
#         data = json.loads(geojson_str)

#         # Extract coordinates for bounds
#         coords = []

#         def extract_coords(geom):
#             t = geom["type"]
#             c = geom["coordinates"]

#             if t == "Polygon":
#                 for ring in c:
#                     coords.extend(ring)

#             elif t == "MultiPolygon":
#                 for poly in c:
#                     for ring in poly:
#                         coords.extend(ring)

#         # GeoJSON may be Feature or FeatureCollection
#         if data.get("type") == "Feature":
#             extract_coords(data["geometry"])

#         elif data.get("type") == "FeatureCollection":
#             for feature in data["features"]:
#                 extract_coords(feature["geometry"])

#         if not coords:
#             return data, None

#         lats = [p[1] for p in coords]
#         lngs = [p[0] for p in coords]

#         bounds = [[min(lats), min(lngs)], [max(lats), max(lngs)]]

#         return data, bounds

#     except Exception as e:
#         st.warning(f"Could not load boundary for project '{project_name}': {e}")
#         return None, None
        
# def compute_centroid(geojson_obj):
#     geom = geojson_obj.get("geometry", geojson_obj)
#     coords = []

#     if geom["type"] == "Polygon":
#         coords = geom["coordinates"][0]
#     elif geom["type"] == "MultiPolygon":
#         for poly in geom["coordinates"]:
#             coords.extend(poly[0])

#     if not coords:
#         return [52.37, 4.90]

#     lats = [c[1] for c in coords]
#     lons = [c[0] for c in coords]
#     return [sum(lats) / len(lats), sum(lons) / len(lons)]


# def get_bounds(geojson_obj):
#     """Return [[min_lat, min_lon], [max_lat, max_lon]] from Polygon/MultiPolygon."""
#     geom = geojson_obj.get("geometry", geojson_obj)
#     coords = []

#     if geom["type"] == "Polygon":
#         coords = geom["coordinates"][0]
#     elif geom["type"] == "MultiPolygon":
#         for poly in geom["coordinates"]:
#             coords.extend(poly[0])

#     if not coords:
#         return [[52.37, 4.90], [52.37, 4.90]]

#     lats = [c[1] for c in coords]
#     lons = [c[0] for c in coords]
#     return [[min(lats), min(lons)], [max(lats), max(lons)]]

# # ---------------------------------------------------------
# # DELETE CONFIRMATION DIALOG
# # ---------------------------------------------------------
# @st.dialog("Confirm deletion", width="small")
# def confirm_delete_dialog(project_name):
#     st.image(
#         "https://media1.tenor.com/m/Y3qtler-qqEAAAAC/suspicious-dog.gif",
#         width=500,
#     )
#     st.write(f"Are you sure you want to delete project **{project_name}**?")
#     col1, col2 = st.columns(2)
#     with col1:
#         if st.button("Yes, delete", type="primary"):
#             try:
#                 supabase.storage.from_(BUCKET).remove([f"{project_name}.geojson"])
#                 supabase.table("project_members").delete().eq("project", project_name).execute()
#                 supabase.table("projects").delete().eq("name", project_name).execute()
#                 st.success(f"Project '{project_name}' deleted.")
#                 st.rerun()
#             except Exception as e:
#                 st.error(f"Error deleting project: {e}")
#     with col2:
#         if st.button("Cancel"):
#             st.rerun()

# # ---------------------------------------------------------
# # SIDEBAR
# # ---------------------------------------------------------
# page = st.sidebar.radio("Navigation", ["Create Project", "View Projects"])

# # ---------------------------------------------------------
# # PAGE 1 — CREATE PROJECT
# # ---------------------------------------------------------
# if page == "Create Project":
#     st.title("Create Project")
#     st.write("Draw a polygon, enter a name, description, and assign users.")

#     # Initialize drawing state
#     if "last_drawings" not in st.session_state:
#         st.session_state["last_drawings"] = None

#     if "confirm_multipolygon" not in st.session_state:
#         st.session_state.confirm_multipolygon = False

#     # MAP
#     m = folium.Map(location=[52.37, 4.90], zoom_start=12, zoom_control=True)

#     # Satellite (Esri)
#     folium.TileLayer(
#         tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
#         attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
#         name="Satellite",
#         overlay=False,
#         control=True
#     ).add_to(m)

#     # Geocoder FIRST
#     Geocoder(
#         collapsed=False,
#         add_marker=True,
#         position='topleft'
#     ).add_to(m)

#     # Draw SECOND
#     Draw(
#         draw_options={"polygon": True, "marker": False, "circle": False,
#                       "polyline": False, "rectangle": False},
#         edit_options={"edit": True, "remove": True},
#     ).add_to(m)

#     Fullscreen(position="topleft").add_to(m)
#     folium.LayerControl(position="topright").add_to(m)

#     # Render map
#     with st.container():
#         map_data = st_folium(m, height=500, use_container_width=True)

#     # Store drawings
#     if map_data and "all_drawings" in map_data:
#         st.session_state["last_drawings"] = map_data["all_drawings"]

#     polygon_geojson = None

#     # Process drawings
#     if st.session_state["last_drawings"]:
#         drawings = st.session_state["last_drawings"]
#         polygons = []

#         for d in drawings:
#             geom = d.get("geometry", {})
#             if geom.get("type") == "Polygon":
#                 polygons.append(geom["coordinates"])
#             elif geom.get("type") == "MultiPolygon":
#                 polygons.extend(geom["coordinates"])

#         # MULTIPOLYGON CHECK
#         if len(polygons) > 1:

#             if not st.session_state.confirm_multipolygon:
#                 st.warning("⚠️ You drew more than one polygon. This will be saved as a MultiPolygon.")

#                 colA, colB = st.columns(2)

#                 with colA:
#                     if st.button("Yes, save as MultiPolygon"):
#                         st.session_state.confirm_multipolygon = True
#                         st.rerun()

#                 with colB:
#                     if st.button("No, let me fix it"):
#                         st.info("Please delete the extra polygons and draw only one.")
#                         st.stop()

#                 st.stop()

#             # User confirmed → build multipolygon
#             polygon_geojson = {
#                 "type": "Feature",
#                 "geometry": {"type": "MultiPolygon", "coordinates": polygons}
#             }

#         else:
#             # Single polygon
#             polygon_geojson = {
#                 "type": "Feature",
#                 "geometry": {"type": "Polygon", "coordinates": polygons[0]}
#             }

#     # FORM
#     project_name = st.text_input("Project name")
#     description = st.text_area("Description")

#     try:
#         users = supabase.rpc("get_all_users").execute().data or []
#     except:
#         users = []

#     email_to_id = {u["email"]: u["id"] for u in users}
#     selected_emails = st.multiselect("Users who can work on this project", list(email_to_id.keys()))

#     # SAVE PROJECT
#     if st.button("Save Project"):

#         if not polygon_geojson:
#             st.error("Draw a polygon first.")
#             st.stop()

#         if not project_name:
#             st.error("Enter a project name.")
#             st.stop()

#         safe_name = project_name.replace(" ", "_")
#         filename = f"{safe_name}.geojson"

#         # Check duplicate
#         existing = supabase.table("projects").select("name").eq("name", safe_name).execute()
#         if existing.data:
#             st.error(f"A project named '{safe_name}' already exists. Choose another name.")
#             st.stop()

#         # Save
#         supabase.storage.from_(BUCKET).upload(
#             filename,
#             json.dumps(polygon_geojson).encode("utf-8"),
#             file_options={"content-type": "application/geo+json", "x-upsert": "true"}
#         )

#         supabase.table("projects").insert(
#             {"name": safe_name, "description": description}
#         ).execute()

#         for email in selected_emails:
#             supabase.table("project_members").insert(
#                 {"project": safe_name, "user_id": email_to_id[email]}
#             ).execute()

#         st.success(f"Project '{safe_name}' has been successfully created.")

#         # Reset multipolygon confirmation
#         st.session_state.confirm_multipolygon = False
#         st.session_state["last_drawings"] = None

#         st.rerun()


# # # ---------------------------------------------------------
# # # PAGE 2 — VIEW PROJECTS
# # # ---------------------------------------------------------
# # elif page == "View Projects":
# #     st.title("View Projects")

# #     # --- Load all projects ---
# #     proj_res = supabase.table("projects").select("*").execute()
# #     projects = proj_res.data or []

# #     if not projects:
# #         st.info("No projects found.")
# #         st.stop()

# #     project_names = [p["name"] for p in projects]
# #     selected = st.selectbox("Select a project", 
# #                             project_names,
# #                             index=None,
# #                             placeholder="Select a project...",)

# #     if not selected:
# #         st.stop()

# #     # Current project data
# #     project = next(p for p in projects if p["name"] == selected)

# #     st.subheader("Project Info")
# #     st.write(f"**Name:** {project['name']}")
# #     st.write(f"**Description:** {project['description']}")

# #     # --- Load all users from Supabase ---
# #     try:
# #         users = supabase.rpc("get_all_users").execute().data or []
# #     except:
# #         users = []

# #     # Two mappings
# #     id_to_email = {u["id"]: u["email"] for u in users}
# #     email_to_id = {u["email"]: u["id"] for u in users}

# #     # --- Load project members ---
# #     pm_res = supabase.table("project_members").select("*").eq("project", selected).execute()
# #     members = pm_res.data or []

# #     st.subheader("Users who can work on this project")
# #     if members:
# #         for m in members:
# #             st.write(f"- {id_to_email.get(m['user_id'], 'Unknown')}")
# #     else:
# #         st.write("No users assigned.")

# #     # --- Load boundary using your working function ---
# #     boundary, bounds = load_project_boundary(selected)

# #     st.subheader("Project Area")

# #     # --- Create map ---
# #     m = folium.Map(location=[52.37, 4.90], zoom_start=12, zoom_control=True)

# #     # Basemaps
# #     folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)



# #     # Add polygon if exists
# #     if boundary:
# #             folium.GeoJson(
# #                 boundary,
# #                 name="Boundary",
# #                 style_function=lambda x: {
# #                     "fillColor": "#ffcc00",
# #                     "color": "red",
# #                     "weight": 2.5,
# #                     "fillOpacity": 0.1,
# #                 }
# #             ).add_to(m)

# #     # Fit to bounds if valid
# #     if bounds:
# #         try:
# #             m.fit_bounds(bounds)
# #         except:
# #             pass

# #     # Plugins


# #     # --- Render map (NO HTML WRAPPER) ---
# #     with st.container():
# #         st_folium(m, height=500, use_container_width=True)

# #     # --- Edit Users Section ---
# #     "---"
# #     st.subheader("Edit Users")

# #     all_user_emails = list(email_to_id.keys())

# #     current_user_ids = [m["user_id"] for m in members]
# #     current_user_emails = [
# #         id_to_email.get(uid) for uid in current_user_ids if uid in id_to_email
# #     ]

# #     new_selection = st.multiselect(
# #         "Select users for this project",
# #         all_user_emails,
# #         default=current_user_emails
# #     )

# #     if st.button("Save User Changes"):
# #         try:
# #             # Remove all existing users
# #             supabase.table("project_members").delete().eq("project", selected).execute()

# #             # Add new users
# #             for email in new_selection:
# #                 supabase.table("project_members").insert(
# #                     {"project": selected, "user_id": email_to_id[email]}
# #                 ).execute()

# #             st.success("Users updated.")
# #             st.rerun()

# #         except Exception as e:
# #             st.error(f"Error updating users: {e}")



# # # ---------------------------------------------------------
# # #   DELETE PROJECT
# # # ---------------------------------------------------------
# #     "---"


# #     if st.button("DELETE PROJECT", type="primary"):
# #         confirm_delete_dialog(selected)








    

# #     st_folium(m, height=500, width="100%")

# # ---------------------------------------------------------
# # PAGE 2 — VIEW PROJECTS
# # ---------------------------------------------------------
# elif page == "View Projects":
#     st.title("View Projects")

#     # --- Load all projects ---
#     proj_res = supabase.table("projects").select("*").execute()
#     projects = proj_res.data or []

#     if not projects:
#         st.info("No projects found.")
#         st.stop()

#     project_names = [p["name"] for p in projects]
#     selected = st.selectbox(
#         "Select a project",
#         project_names,
#         index=None,
#         placeholder="Select a project...",
#     )

#     if not selected:
#         st.stop()

#     # Current project data
#     project = next(p for p in projects if p["name"] == selected)

#     st.subheader("Project Info")
#     st.write(f"**Name:** {project['name']}")
#     st.write(f"**Description:** {project['description']}")

#     # --- Load all users from Supabase ---
#     try:
#         users = supabase.rpc("get_all_users").execute().data or []
#     except:
#         users = []

#     # Two mappings
#     id_to_email = {u["id"]: u["email"] for u in users}
#     email_to_id = {u["email"]: u["id"] for u in users}

#     # --- Load project members ---
#     pm_res = supabase.table("project_members").select("*").eq("project", selected).execute()
#     members = pm_res.data or []

#     st.subheader("Users who can work on this project")
#     if members:
#         for m in members:
#             st.write(f"- {id_to_email.get(m['user_id'], 'Unknown')}")
#     else:
#         st.write("No users assigned.")

#     # --- Load boundary using your working function ---
#     boundary, bounds = load_project_boundary(selected)

#     st.subheader("Project Area")

#     # --- Create map ---
#     m = folium.Map(location=[52.37, 4.90], zoom_start=12, zoom_control=True)

#     # Basemaps
#     folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)

#     # Add polygon if exists
#     if boundary:
#         folium.GeoJson(
#             boundary,
#             name="Boundary",
#             style_function=lambda x: {
#                 "fillColor": "#ffcc00",
#                 "color": "red",
#                 "weight": 2.5,
#                 "fillOpacity": 0.1,
#             }
#         ).add_to(m)

#     # Fit to bounds if valid
#     if bounds:
#         try:
#             m.fit_bounds(bounds)
#         except:
#             pass

#     # --- Render map ---
#     with st.container():
#         st_folium(m, height=500, use_container_width=True)

#     # --- Edit Users Section ---
#     st.markdown("---")
#     st.subheader("Edit Users")

#     all_user_emails = list(email_to_id.keys())

#     current_user_ids = [m["user_id"] for m in members]
#     current_user_emails = [
#         id_to_email.get(uid) for uid in current_user_ids if uid in id_to_email
#     ]

#     new_selection = st.multiselect(
#         "Select users for this project",
#         all_user_emails,
#         default=current_user_emails
#     )

#     if st.button("Save User Changes"):
#         try:
#             # Remove all existing users
#             supabase.table("project_members").delete().eq("project", selected).execute()

#             # Add new users
#             for email in new_selection:
#                 supabase.table("project_members").insert(
#                     {"project": selected, "user_id": email_to_id[email]}
#                 ).execute()

#             st.success("Users updated.")
#             st.rerun()

#         except Exception as e:
#             st.error(f"Error updating users: {e}")

#     # ---------------------------------------------------------
#     #   DELETE PROJECT
#     # ---------------------------------------------------------
#     st.markdown("---")

#     if st.button("DELETE PROJECT", type="primary"):
#         confirm_delete_dialog(selected)

#     # ---------------------------------------------------------
#     #   DOWNLOAD REPORTS + OBSERVATIONS
#     # ---------------------------------------------------------
#     st.markdown("---")
#     st.subheader("Download Data")

#     # --- Download Reports ---
#     try:
#         report_res = (
#             supabase.table("report")
#             .select("*")
#             .eq("project", selected)
#             .order("date", desc=True)
#             .execute()
#         )
#         report_df = pd.DataFrame(report_res.data or [])
#     except Exception as e:
#         report_df = pd.DataFrame()
#         st.error(f"Error loading reports: {e}")

#     st.download_button(
#         label="Download Reports (CSV)",
#         data=report_df.to_csv(index=False).encode("utf-8"),
#         file_name=f"{selected}_reports.csv",
#         mime="text/csv",
#         icon=":material/sim_card_download:"
#     )

#     # --- Download Observations ---
#     try:
#         obs_res = (
#             supabase.table("observations")
#             .select("*")
#             .eq("project", selected)
#             .order("date", desc=True)
#             .execute()
#         )
#         obs_df = pd.DataFrame(obs_res.data or [])
#     except Exception as e:
#         obs_df = pd.DataFrame()
#         st.error(f"Error loading observations: {e}")

#     st.download_button(
#         label="Download Observations (CSV)",
#         data=obs_df.to_csv(index=False).encode("utf-8"),
#         file_name=f"{selected}_observations.csv",
#         mime="text/csv",
#         icon=":material/download:"
#     )

import streamlit as st
from streamlit_folium import st_folium, folium_static
import folium
from folium.plugins import MarkerCluster, FastMarkerCluster
import json
from supabase import create_client
from folium.plugins import Geocoder, Fullscreen, Draw
import pandas as pd
from typing import Optional, Tuple, Dict, List, Any

# =========================================================
# PAGE CONFIG - MUST BE FIRST STREAMLIT COMMAND
# =========================================================
st.set_page_config(
    page_title="Project Manager",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# CONSTANTS
# =========================================================
DEFAULT_LOCATION = [52.37, 4.90]  # Amsterdam
BUCKET = "observation_photos"

# =========================================================
# AUTHENTICATION
# =========================================================
def init_auth_state():
    """Initialize authentication state."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None

def login_page():
    """Render login form."""
    st.title("Login")
    
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            allowed_users = st.secrets.get("users", {})
            
            if username not in allowed_users:
                st.error("Unknown username")
                return
            
            if password != allowed_users[username]:
                st.error("Incorrect password")
                return
            
            st.session_state.authenticated = True
            st.session_state.username = username
            st.rerun()

# =========================================================
# SUPABASE CLIENT (Singleton pattern)
# =========================================================
@st.cache_resource
def get_supabase_client():
    """Create and cache Supabase client."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# =========================================================
# CACHED DATA FETCHING
# =========================================================
@st.cache_data(ttl=300)
def fetch_all_projects() -> List[Dict]:
    """Fetch all projects with caching."""
    supabase = get_supabase_client()
    try:
        res = supabase.table("projects").select("*").execute()
        return res.data or []
    except Exception as e:
        st.error(f"Error loading projects: {e}")
        return []

@st.cache_data(ttl=300)
def fetch_project_members(project_name: str) -> List[Dict]:
    """Fetch members for a specific project."""
    supabase = get_supabase_client()
    try:
        res = supabase.table("project_members").select("*").eq("project", project_name).execute()
        return res.data or []
    except Exception as e:
        st.error(f"Error loading members: {e}")
        return []

@st.cache_data(ttl=300)
def fetch_all_users() -> List[Dict]:
    """Fetch all users with caching."""
    supabase = get_supabase_client()
    try:
        res = supabase.rpc("get_all_users").execute()
        return res.data or []
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return []

@st.cache_data(ttl=60)
def load_project_boundary(project_name: str) -> Tuple[Optional[Dict], Optional[List]]:
    """Load GeoJSON boundary from Supabase storage."""
    supabase = get_supabase_client()
    filename = f"{project_name}.geojson"
    
    try:
        file_bytes = supabase.storage.from_(BUCKET).download(filename)
        if not file_bytes:
            return None, None
        
        data = json.loads(file_bytes.decode("utf-8"))
        bounds = extract_bounds(data)
        return data, bounds
        
    except Exception as e:
        st.warning(f"Could not load boundary for '{project_name}': {e}")
        return None, None

@st.cache_data(ttl=60)
def fetch_project_observations(project_name: str) -> pd.DataFrame:
    """Fetch observations with lat/lon for map display."""
    supabase = get_supabase_client()
    try:
        res = supabase.table("observations").select("*").eq("project", project_name).execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        st.error(f"Error loading observations: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_project_reports(project_name: str) -> pd.DataFrame:
    """Fetch reports for project."""
    supabase = get_supabase_client()
    try:
        res = supabase.table("report").select("*").eq("project", project_name).order("date", desc=True).execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        st.error(f"Error loading reports: {e}")
        return pd.DataFrame()

# =========================================================
# GEOMETRY UTILITIES
# =========================================================
def extract_coordinates(geometry: Dict) -> List[List[float]]:
    """Extract all coordinates from a GeoJSON geometry."""
    geom_type = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    
    if geom_type == "Polygon":
        return [coord for ring in coords for coord in ring]
    elif geom_type == "MultiPolygon":
        return [coord for poly in coords for ring in poly for coord in ring]
    elif geom_type == "Point":
        return [coords]
    return []

def extract_bounds(geojson_obj: Dict) -> Optional[List[List[float]]]:
    """Extract bounding box from GeoJSON Feature or FeatureCollection."""
    if geojson_obj.get("type") == "Feature":
        coords = extract_coordinates(geojson_obj.get("geometry", {}))
    elif geojson_obj.get("type") == "FeatureCollection":
        coords = []
        for feature in geojson_obj.get("features", []):
            coords.extend(extract_coordinates(feature.get("geometry", {})))
    else:
        return None
    
    if not coords:
        return None
    
    lats = [p[1] for p in coords]
    lngs = [p[0] for p in coords]
    return [[min(lats), min(lngs)], [max(lats), max(lngs)]]

def compute_centroid(geojson_obj: Dict) -> List[float]:
    """Compute centroid from GeoJSON geometry."""
    coords = extract_coordinates(geojson_obj.get("geometry", geojson_obj))
    
    if not coords:
        return DEFAULT_LOCATION
    
    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    return [sum(lats) / len(lats), sum(lons) / len(lons)]

# =========================================================
# MAP CREATION WITH POINTS
# =========================================================
def create_base_map(location: Optional[List[float]] = None, 
                    zoom_start: int = 12) -> folium.Map:
    """Create a base Folium map with standard layers."""
    loc = location or DEFAULT_LOCATION
    
    m = folium.Map(
        location=loc, 
        zoom_start=zoom_start, 
        zoom_control=True,
        tiles=None  # Don't add default tile yet
    )
    
    # Add OpenStreetMap as default
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap",
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add satellite layer
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=True
    ).add_to(m)
    
    return m

def add_boundary_to_map(m: folium.Map, boundary: Dict) -> folium.Map:
    """Add a GeoJSON boundary to the map."""
    folium.GeoJson(
        boundary,
        name="Project Boundary",
        style_function=lambda x: {
            "fillColor": "#ffcc00",
            "color": "red",
            "weight": 2.5,
            "fillOpacity": 0.15,
        },
        highlight_function=lambda x: {
            "fillOpacity": 0.3
        }
    ).add_to(m)
    return m

def add_observations_to_map(m: folium.Map, observations_df: pd.DataFrame) -> folium.Map:
    """Add observation points to the map with clustering."""
    if observations_df.empty or 'latitude' not in observations_df.columns or 'longitude' not in observations_df.columns:
        return m
    
    # Create feature group for observations
    obs_group = folium.FeatureGroup(name="Observations")
    
    # Add points
    for _, row in observations_df.iterrows():
        lat = row.get('latitude')
        lon = row.get('longitude')
        
        if pd.isna(lat) or pd.isna(lon):
            continue
            
        # Create popup content
        popup_content = "<div style='min-width: 200px;'>"
        popup_content += f"<b>Date:</b> {row.get('date', 'N/A')}<br>"
        popup_content += f"<b>Type:</b> {row.get('type', 'N/A')}<br>"
        popup_content += f"<b>Description:</b> {row.get('description', 'N/A')}<br>"
        
        # Add photo if available
        if 'photo_url' in row and row['photo_url']:
            popup_content += f"<img src='{row['photo_url']}' style='max-width: 200px; margin-top: 5px;'><br>"
        
        popup_content += "</div>"
        
        # Color based on type or status
        color = "blue"
        if 'status' in row:
            status_colors = {
                'pending': 'orange',
                'completed': 'green',
                'urgent': 'red',
                'review': 'purple'
            }
            color = status_colors.get(row['status'], 'blue')
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"Observation: {row.get('type', 'Unknown')}",
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(obs_group)
    
    obs_group.add_to(m)
    return m

def add_reports_to_map(m: folium.Map, reports_df: pd.DataFrame) -> folium.Map:
    """Add report points to the map."""
    if reports_df.empty or 'latitude' not in reports_df.columns or 'longitude' not in reports_df.columns:
        return m
    
    reports_group = folium.FeatureGroup(name="Reports")
    
    for _, row in reports_df.iterrows():
        lat = row.get('latitude')
        lon = row.get('longitude')
        
        if pd.isna(lat) or pd.isna(lon):
            continue
        
        popup_content = "<div style='min-width: 200px;'>"
        popup_content += f"<b>Report Date:</b> {row.get('date', 'N/A')}<br>"
        popup_content += f"<b>Title:</b> {row.get('title', 'N/A')}<br>"
        popup_content += f"<b>Status:</b> {row.get('status', 'N/A')}<br>"
        popup_content += "</div>"
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"Report: {row.get('title', 'Unknown')}",
            icon=folium.Icon(color='green', icon='file-alt', prefix='fa')
        ).add_to(reports_group)
    
    reports_group.add_to(m)
    return m

def render_map(m: folium.Map, key: str, height: int = 600):
    """
    Render Folium map with fallback methods.
    Primary: st_folium (interactive)
    Fallback: folium_static or components.html if st_folium fails
    """
    try:
        # Try st_folium first with unique key
        map_data = st_folium(
            m, 
            height=height, 
            width=None,  # Use None instead of use_container_width to avoid issues
            returned_objects=[],  # Don't return data to avoid rerenders
            key=key
        )
        return map_data
    except Exception as e:
        st.warning(f"Interactive map failed, using static display: {e}")
        try:
            # Fallback to folium_static
            folium_static(m, width=1200, height=height)
        except:
            # Final fallback to components.html
            import streamlit.components.v1 as components
            fig = folium.Figure().add_child(m)
            components.html(fig.render(), height=height, scrolling=False)

# =========================================================
# PROJECT OPERATIONS
# =========================================================
def save_project_with_boundary(project_name: str, description: str, 
                               boundary: Dict, user_ids: List[str]) -> bool:
    """Save project with boundary and members."""
    supabase = get_supabase_client()
    safe_name = project_name.replace(" ", "_")
    filename = f"{safe_name}.geojson"
    
    try:
        # 1. Upload GeoJSON
        supabase.storage.from_(BUCKET).upload(
            filename,
            json.dumps(boundary).encode("utf-8"),
            file_options={"content-type": "application/geo+json", "x-upsert": "true"}
        )
        
        # 2. Insert project
        supabase.table("projects").insert({
            "name": safe_name, 
            "description": description
        }).execute()
        
        # 3. Insert members
        if user_ids:
            members_data = [{"project": safe_name, "user_id": uid} for uid in user_ids]
            supabase.table("project_members").insert(members_data).execute()
        
        return True
        
    except Exception as e:
        st.error(f"Error saving project: {e}")
        return False

def delete_project(project_name: str) -> bool:
    """Delete project and all associated data."""
    supabase = get_supabase_client()
    try:
        supabase.storage.from_(BUCKET).remove([f"{project_name}.geojson"])
        supabase.table("project_members").delete().eq("project", project_name).execute()
        supabase.table("projects").delete().eq("name", project_name).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting project: {e}")
        return False

def update_project_members(project_name: str, user_ids: List[str]) -> bool:
    """Update project members (replace all)."""
    supabase = get_supabase_client()
    try:
        supabase.table("project_members").delete().eq("project", project_name).execute()
        if user_ids:
            members_data = [{"project": project_name, "user_id": uid} for uid in user_ids]
            supabase.table("project_members").insert(members_data).execute()
        return True
    except Exception as e:
        st.error(f"Error updating members: {e}")
        return False

# =========================================================
# UI COMPONENTS
# =========================================================
def render_delete_dialog(project_name: str):
    """Render delete confirmation dialog."""
    st.image(
        "https://media1.tenor.com/m/Y3qtler-qqEAAAAC/suspicious-dog.gif",
        width=300,
    )
    st.write(f"Are you sure you want to delete project **{project_name}**?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, delete", type="primary", key=f"confirm_del_{project_name}"):
            if delete_project(project_name):
                st.success(f"Project '{project_name}' deleted.")
                st.rerun()
    with col2:
        if st.button("Cancel", key=f"cancel_del_{project_name}"):
            st.rerun()

# =========================================================
# PAGE: CREATE PROJECT
# =========================================================
def create_project_page():
    """Render the Create Project page."""
    st.title("Create Project")
    st.write("Draw a polygon, enter details, and assign users.")
    
    # Initialize state
    if "last_drawings" not in st.session_state:
        st.session_state.last_drawings = None
    if "confirm_multipolygon" not in st.session_state:
        st.session_state.confirm_multipolygon = False
    
    # Create map with drawing tools
    m = create_base_map()
    
    # Add plugins in specific order (Draw before Geocoder to avoid mouse issues)
    Draw(
        draw_options={
            "polygon": True, 
            "marker": False, 
            "circle": False,
            "polyline": False, 
            "rectangle": False
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(m)
    
    Geocoder(collapsed=False, add_marker=True, position='topleft').add_to(m)
    Fullscreen(position="topleft").add_to(m)
    folium.LayerControl(position="topright").add_to(m)
    
    # Render map with unique key
    map_data = render_map(m, key="create_map", height=500)
    
    # Store drawings
    if map_data and "all_drawings" in map_data:
        st.session_state.last_drawings = map_data["all_drawings"]
    
    # Process drawings
    polygon_geojson = process_drawings(st.session_state.last_drawings)
    
    # Form inputs
    project_name = st.text_input("Project name", key="new_project_name")
    description = st.text_area("Description", key="new_project_desc")
    
    # User selection
    users = fetch_all_users()
    email_to_id = {u["email"]: u["id"] for u in users}
    selected_emails = st.multiselect(
        "Users who can work on this project", 
        list(email_to_id.keys()),
        key="new_project_users"
    )
    
    # Save button
    if st.button("Save Project", type="primary", use_container_width=True):
        if not polygon_geojson:
            st.error("Draw a polygon first.")
            return
        
        if not project_name:
            st.error("Enter a project name.")
            return
        
        safe_name = project_name.replace(" ", "_")
        
        # Check for duplicates
        existing = fetch_all_projects()
        if any(p["name"] == safe_name for p in existing):
            st.error(f"Project '{safe_name}' already exists.")
            return
        
        # Save
        selected_ids = [email_to_id[e] for e in selected_emails]
        if save_project_with_boundary(safe_name, description, polygon_geojson, selected_ids):
            st.success(f"Project '{safe_name}' created successfully!")
            st.session_state.confirm_multipolygon = False
            st.session_state.last_drawings = None
            st.rerun()

def process_drawings(drawings: Optional[List[Dict]]) -> Optional[Dict]:
    """Process map drawings into GeoJSON Feature."""
    if not drawings:
        return None
    
    polygons = []
    for d in drawings:
        geom = d.get("geometry", {})
        geom_type = geom.get("type")
        
        if geom_type == "Polygon":
            polygons.append(geom["coordinates"])
        elif geom_type == "MultiPolygon":
            polygons.extend(geom["coordinates"])
    
    if not polygons:
        return None
    
    # Handle multiple polygons
    if len(polygons) > 1:
        if not st.session_state.confirm_multipolygon:
            st.warning("⚠️ You drew multiple polygons. This will be saved as a MultiPolygon.")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Yes, save as MultiPolygon", key="confirm_multi"):
                    st.session_state.confirm_multipolygon = True
                    st.rerun()
            with col2:
                if st.button("No, let me fix it", key="cancel_multi"):
                    st.info("Please delete extra polygons and draw only one.")
            
            st.stop()
        
        return {
            "type": "Feature",
            "geometry": {"type": "MultiPolygon", "coordinates": polygons}
        }
    
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": polygons[0]}
    }

# =========================================================
# PAGE: VIEW PROJECTS
# =========================================================
def view_projects_page():
    """Render the View Projects page."""
    st.title("View Projects")
    
    projects = fetch_all_projects()
    if not projects:
        st.info("No projects found.")
        return
    
    # Project selection
    project_names = [p["name"] for p in projects]
    selected = st.selectbox(
        "Select a project",
        project_names,
        index=None,
        placeholder="Select a project...",
        key="view_project_select"
    )
    
    if not selected:
        return
    
    project = next(p for p in projects if p["name"] == selected)
    
    # Display project info
    st.subheader("Project Info")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Name:** {project['name']}")
    with col2:
        st.write(f"**Description:** {project.get('description', 'N/A')}")
    
    # Load related data
    users = fetch_all_users()
    id_to_email = {u["id"]: u["email"] for u in users}
    email_to_id = {u["email"]: u["id"] for u in users}
    members = fetch_project_members(selected)
    
    # Display members
    st.subheader("Project Members")
    if members:
        member_emails = [id_to_email.get(m["user_id"], "Unknown") for m in members]
        st.write(", ".join(f"**{email}**" for email in member_emails))
    else:
        st.write("No users assigned.")
    
    # Load data for map
    boundary, bounds = load_project_boundary(selected)
    observations_df = fetch_project_observations(selected)
    reports_df = fetch_project_reports(selected)
    
    # Create map with all layers
    st.subheader("Project Map")
    
    # Determine map center
    if boundary:
        center = compute_centroid(boundary)
    elif not observations_df.empty:
        center = [
            observations_df['latitude'].mean(),
            observations_df['longitude'].mean()
        ]
    else:
        center = DEFAULT_LOCATION
    
    m = create_base_map(location=center)
    
    # Add boundary
    if boundary:
        m = add_boundary_to_map(m, boundary)
    
    # Add observations and reports
    m = add_observations_to_map(m, observations_df)
    m = add_reports_to_map(m, reports_df)
    
    # Add layer control and plugins
    Fullscreen(position="topleft").add_to(m)
    folium.LayerControl(position="topright").add_to(m)
    
    # Fit to bounds if available
    if bounds:
        m.fit_bounds(bounds)
    
    # Render map
    render_map(m, key="view_map", height=600)
    
    # Stats
    if not observations_df.empty:
        st.metric("Total Observations", len(observations_df))
    if not reports_df.empty:
        st.metric("Total Reports", len(reports_df))
    
    # Edit members
    st.divider()
    st.subheader("Edit Members")
    
    current_emails = [id_to_email.get(m["user_id"]) for m in members 
                      if m["user_id"] in id_to_email]
    new_selection = st.multiselect(
        "Select users for this project",
        list(email_to_id.keys()),
        default=current_emails,
        key="edit_members"
    )
    
    if st.button("Save Changes", type="primary", key="save_members"):
        new_ids = [email_to_id[e] for e in new_selection]
        if update_project_members(selected, new_ids):
            st.success("Members updated.")
            st.rerun()
    
    # Delete project
    st.divider()
    if st.button("DELETE PROJECT", type="primary", key="delete_project_btn"):
        render_delete_dialog(selected)
    
    # Downloads
    st.divider()
    st.subheader("Download Data")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label=f"📥 Reports ({len(reports_df)} rows)",
            data=reports_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{selected}_reports.csv",
            mime="text/csv",
            disabled=reports_df.empty
        )
    
    with col2:
        st.download_button(
            label=f"📥 Observations ({len(obs_df)} rows)",
            data=observations_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{selected}_observations.csv",
            mime="text/csv",
            disabled=observations_df.empty
        )

# =========================================================
# MAIN APP
# =========================================================
def main():
    """Main application entry point."""
    init_auth_state()
    
    if not st.session_state.authenticated:
        login_page()
        st.stop()
    
    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation", 
        ["Create Project", "View Projects"],
        key="nav"
    )
    
    # Route to page
    if page == "Create Project":
        create_project_page()
    else:
        view_projects_page()

if __name__ == "__main__":
    main()


