import streamlit as st
from streamlit_folium import st_folium
import folium
import json
from supabase import create_client
from folium.plugins import Geocoder, Fullscreen, Draw

# ---------------------------------------------------------
# USERNAME + PASSWORD LOGIN (from st.secrets)
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:

    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        allowed_users = st.secrets["users"]  # [users] section in secrets.toml

        if username not in allowed_users:
            st.error("Unknown username")
            st.stop()

        if password != allowed_users[username]:
            st.error("Incorrect password")
            st.stop()

        st.session_state.authenticated = True
        st.session_state.username = username
        st.success("Login successful")

        st.rerun()

    st.stop()

# ---------------------------------------------------------
# SUPABASE SETUP
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = "observation_photos"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def compute_centroid(geojson_obj):
    geom = geojson_obj.get("geometry", geojson_obj)
    coords = []

    if geom["type"] == "Polygon":
        coords = geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            coords.extend(poly[0])

    if not coords:
        return [52.37, 4.90]

    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    return [sum(lats) / len(lats), sum(lons) / len(lons)]


def get_bounds(geojson_obj):
    """Return [[min_lat, min_lon], [max_lat, max_lon]] from Polygon/MultiPolygon."""
    geom = geojson_obj.get("geometry", geojson_obj)
    coords = []

    if geom["type"] == "Polygon":
        coords = geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            coords.extend(poly[0])

    if not coords:
        return [[52.37, 4.90], [52.37, 4.90]]

    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]

# ---------------------------------------------------------
# DELETE CONFIRMATION DIALOG
# ---------------------------------------------------------
@st.dialog("Confirm deletion", width="small")
def confirm_delete_dialog(project_name):
    st.image(
        "https://media1.tenor.com/m/Y3qtler-qqEAAAAC/suspicious-dog.gif",
        width=80,
    )
    st.write(f"Are you sure you want to delete project **{project_name}**?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, delete", type="primary"):
            try:
                supabase.storage.from_(BUCKET).remove([f"{project_name}.geojson"])
                supabase.table("project_members").delete().eq("project", project_name).execute()
                supabase.table("projects").delete().eq("name", project_name).execute()
                st.success(f"Project '{project_name}' deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting project: {e}")
    with col2:
        if st.button("Cancel"):
            st.rerun()

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
page = st.sidebar.radio("Navigation", ["Create Project", "View Projects", "Delete Project"])

# ---------------------------------------------------------
# PAGE 1 — CREATE PROJECT
# ---------------------------------------------------------
if page == "Create Project":
    st.title("Create Project")
    st.write("Draw a polygon, enter a name, description, and assign users.")

    if "last_drawings" not in st.session_state:
        st.session_state["last_drawings"] = None

    # MAP
    m = folium.Map(location=[52.37, 4.90], zoom_start=12, zoom_control=True)

    # OpenStreetMap
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", control=True).add_to(m)

    # Satellite (Esri)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=True
    ).add_to(m)

    Fullscreen(position="topright").add_to(m)
    Draw(
        draw_options={"polygon": True, "marker": False, "circle": False,
                      "polyline": False, "rectangle": False},
        edit_options={"edit": True, "remove": True},
    ).add_to(m)
    Geocoder(collapsed=False, add_marker=True, position="bottomleft").add_to(m)
    folium.LayerControl(position="topright").add_to(m)

    # Put map in a container, full width
    with st.container():
        map_data = st_folium(m, height=500, use_container_width=True)

    if map_data and "all_drawings" in map_data:
        st.session_state["last_drawings"] = map_data["all_drawings"]

    polygon_geojson = None

    if st.session_state["last_drawings"]:
        drawings = st.session_state["last_drawings"]
        polygons = []

        for d in drawings:
            geom = d.get("geometry", {})
            if geom.get("type") == "Polygon":
                polygons.append(geom["coordinates"])
            elif geom.get("type") == "MultiPolygon":
                polygons.extend(geom["coordinates"])

        if len(polygons) == 1:
            polygon_geojson = {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": polygons[0]}
            }
        elif len(polygons) > 1:
            polygon_geojson = {
                "type": "Feature",
                "geometry": {"type": "MultiPolygon", "coordinates": polygons}
            }

    # FORM
    project_name = st.text_input("Project name")
    description = st.text_area("Description")

    try:
        users = supabase.rpc("get_all_users").execute().data or []
    except:
        users = []

    email_to_id = {u["email"]: u["id"] for u in users}
    selected_emails = st.multiselect("Users who can work on this project", list(email_to_id.keys()))

    # SAVE PROJECT
    if st.button("Save Project"):

        if not polygon_geojson:
            st.error("Draw a polygon first.")
            st.stop()

        if not project_name:
            st.error("Enter a project name.")
            st.stop()

        safe_name = project_name.replace(" ", "_")
        filename = f"{safe_name}.geojson"

        # Check duplicate
        try:
            existing = supabase.table("projects").select("name").eq("name", safe_name).execute()
            if existing.data:
                st.error(f"A project named '{safe_name}' already exists. Choose another name.")
                st.stop()
        except Exception as e:
            st.error(f"Error checking existing projects: {e}")
            st.stop()

        try:
            supabase.storage.from_(BUCKET).upload(
                filename,
                json.dumps(polygon_geojson).encode("utf-8"),
                file_options={"content-type": "application/geo+json", "x-upsert": "true"}
            )

            supabase.table("projects").insert(
                {"name": safe_name, "description": description}
            ).execute()

            for email in selected_emails:
                supabase.table("project_members").insert(
                    {"project": safe_name, "user_id": email_to_id[email]}
                ).execute()

            st.success(f"Project '{safe_name}' has been successfully created.")

            # Clear drawings and rerun
            st.session_state["last_drawings"] = None
            st.rerun()

        except Exception as e:
            st.error(f"Exception while saving project: {e}")

# ---------------------------------------------------------
# PAGE 2 — VIEW PROJECTS
# ---------------------------------------------------------
elif page == "View Projects":
    st.title("View Projects")

    proj_res = supabase.table("projects").select("*").execute()
    projects = proj_res.data or []

    if not projects:
        st.info("No projects found.")
        st.stop()

    project_names = [p["name"] for p in projects]
    selected = st.selectbox("Select a project", project_names)

    project = next(p for p in projects if p["name"] == selected)

    st.subheader("Project Info")
    st.write(f"**Name:** {project['name']}")
    st.write(f"**Description:** {project['description']}")

    try:
        users = supabase.rpc("get_all_users").execute().data or []
    except:
        users = []

    id_to_email = {u["id"]: u["email"] for u in users}

    pm_res = supabase.table("project_members").select("*").eq("project", selected).execute()
    members = pm_res.data or []

    st.subheader("Users who can work on this project")
    if members:
        for m in members:
            st.write(f"- {id_to_email.get(m['user_id'], 'Unknown')}")
    else:
        st.write("No users assigned.")

    filename = f"{selected}.geojson"
    try:
        file_bytes = supabase.storage.from_(BUCKET).download(filename)
        geojson_obj = json.loads(file_bytes.decode("utf-8"))
    except Exception as e:
        st.error(f"Could not load GeoJSON: {e}")
        st.stop()

    st.subheader("Project Area")

    bounds = get_bounds(geojson_obj)

    m = folium.Map(location=[(bounds[0][0] + bounds[1][0]) / 2,
                             (bounds[0][1] + bounds[1][1]) / 2],
                   zoom_start=17, zoom_control=True)

    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", control=True).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=True
    ).add_to(m)

    folium.GeoJson(
        geojson_obj,
        name="Project Area",
        zoom_on_click=False
    ).add_to(m)

    m.fit_bounds(bounds)

    Geocoder(collapsed=False, add_marker=True, position="topleft").add_to(m)
    folium.LayerControl(position="topright").add_to(m)

    with st.container():
        st_folium(m, height=500, use_container_width=True)

# ---------------------------------------------------------
# PAGE 3 — DELETE PROJECT
# ---------------------------------------------------------
elif page == "Delete Project":
    st.title("Delete Project")

    proj_res = supabase.table("projects").select("*").execute()
    projects = proj_res.data or []

    if not projects:
        st.info("No projects found.")
        st.stop()

    project_names = [p["name"] for p in projects]
    selected = st.selectbox("Select project to delete", project_names)

    if st.button("DELETE PROJECT", type="primary"):
        confirm_delete_dialog(selected)



















