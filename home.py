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

        allowed_users = st.secrets["users"]

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

    folium.TileLayer("OpenStreetMap", name="Street").add_to(m)
    folium.TileLayer(
        tiles="https://stamen-tiles.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg",
        attr="Map tiles by Stamen Design — Data © OpenStreetMap",
        name="Terrain"
    ).add_to(m)
    
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        attr="Labels © Esri — Boundaries & Places",
        name="Hybrid Labels",
        overlay=True,
        control=True
    ).add_to(m)


    Fullscreen().add_to(m)

    Draw(
        draw_options={"polygon": True, "marker": False, "circle": False,
                      "polyline": False, "rectangle": False},
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    Geocoder(add_marker=True).add_to(m)
    folium.LayerControl().add_to(m)

    map_data = st_folium(m, height=500, width=800)

    if map_data and "all_drawings" in map_data:
        st.session_state["last_drawings"] = map_data["all_drawings"]

    polygon_geojson = None

    if st.session_state.last_drawings:
        drawings = st.session_state.last_drawings
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

    users = supabase.rpc("get_all_users").execute().data or []
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

        existing = supabase.table("projects").select("name").eq("name", safe_name).execute()
        if existing.data:
            st.error("A project with this name already exists.")
            st.stop()

        supabase.storage.from_(BUCKET).upload(
            f"{safe_name}.geojson",
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

        st.success(f"Project '{safe_name}' created.")

        st.session_state.clear()
        st.session_state.authenticated = True  # keep login
        st.rerun()


# ---------------------------------------------------------
# PAGE 2 — VIEW PROJECTS
# ---------------------------------------------------------
elif page == "View Projects":
    st.title("View Projects")

    projects = supabase.table("projects").select("*").execute().data or []

    if not projects:
        st.info("No projects found.")
        st.stop()

    selected = st.selectbox("Select a project", [p["name"] for p in projects])
    project = next(p for p in projects if p["name"] == selected)

    st.subheader("Project Info")
    st.write(f"**Name:** {project['name']}")
    st.write(f"**Description:** {project['description']}")

    users = supabase.rpc("get_all_users").execute().data or []
    id_to_email = {u["id"]: u["email"] for u in users}

    members = supabase.table("project_members").select("*").eq("project", selected).execute().data or []

    st.subheader("Users")
    for m in members:
        st.write(f"- {id_to_email.get(m['user_id'], 'Unknown')}")

    file_bytes = supabase.storage.from_(BUCKET).download(f"{selected}.geojson")
    geojson_obj = json.loads(file_bytes.decode("utf-8"))

    centroid = compute_centroid(geojson_obj)

    m = folium.Map(location=centroid, zoom_start=17)
    folium.GeoJson(geojson_obj).add_to(m)
    Geocoder().add_to(m)

    st_folium(m, height=500, width=800)

# ---------------------------------------------------------
# PAGE 3 — DELETE PROJECT
# ---------------------------------------------------------
elif page == "Delete Project":
    st.title("Delete Project")

    projects = supabase.table("projects").select("*").execute().data or []

    if not projects:
        st.info("No projects found.")
        st.stop()

    selected = st.selectbox("Select project to delete", [p["name"] for p in projects])

    if st.button("DELETE PROJECT", type="primary"):

        supabase.storage.from_(BUCKET).remove([f"{selected}.geojson"])
        supabase.table("project_members").delete().eq("project", selected).execute()
        supabase.table("projects").delete().eq("name", selected).execute()

        st.success(f"Project '{selected}' deleted.")

        st.rerun()


















