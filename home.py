import streamlit as st
from streamlit_folium import st_folium
import folium
import json
from supabase import create_client
from folium.plugins import Geocoder, Fullscreen

# ---------------------------------------------------------
# PASSWORD PROTECTION
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Login")
    pwd = st.text_input("Enter password", type="password")
    if st.button("Login"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
        else:
            st.error("Incorrect password")
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
    """Compute centroid (lat, lon) from Polygon or MultiPolygon GeoJSON."""
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

    from folium.plugins import Draw
    m = folium.Map(location=[52.37, 4.90], zoom_start=12,zoom_control=False)

    # Base map (default street)
    folium.TileLayer(
        "OpenStreetMap",
        name="Street",
        control=True
    ).add_to(m)
    
    # Satellite (Esri)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satellite",
        overlay=False,
        control=True
    ).add_to(m)
    
    # Hybrid (Esri Satellite + Labels)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        attr="Esri Boundaries & Places",
        name="Hybrid Labels",
        overlay=True,
        control=True
    ).add_to(m)

    # Fullscreen button
    Fullscreen(
        position="topright",
        title="Full Screen",
        title_cancel="Exit Full Screen",
        force_separate_button=True
    ).add_to(m)



    folium.LayerControl(position="topright").add_to(m)

    
    Draw(
        draw_options={"polygon": True, "marker": False, "circle": False,
                      "polyline": False, "rectangle": False},
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    # ⭐ Add address search bar

    Geocoder(
        collapsed=False,
        add_marker=True,
        position='bottomleft'
    ).add_to(m)


    map_data = st_folium(m, height=500, width=800)

    polygon_geojson = None
    
    if map_data and "all_drawings" in map_data and map_data["all_drawings"]:
        drawings = map_data["all_drawings"]
    
        # Extract all polygon coordinate lists
        polygons = []
        for d in drawings:
            geom = d.get("geometry", {})
            if geom.get("type") == "Polygon":
                polygons.append(geom["coordinates"])
            elif geom.get("type") == "MultiPolygon":
                polygons.extend(geom["coordinates"])
    
        # Build a MultiPolygon GeoJSON if multiple polygons exist
        if len(polygons) == 1:
            polygon_geojson = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": polygons[0]
                }
            }
        else:
            polygon_geojson = {
                "type": "Feature",
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": polygons
                }
            }


    project_name = st.text_input("Project name")
    description = st.text_area("Description")

    # Load users
    try:
        users = supabase.rpc("get_all_users").execute().data or []
    except:
        users = []

    email_to_id = {u["email"]: u["id"] for u in users}
    selected_emails = st.multiselect("Users who can work on this project", list(email_to_id.keys()))

    if st.button("Save Project"):
        if not polygon_geojson:
            st.error("Draw a polygon first.")
            st.stop()

        if not project_name:
            st.error("Enter a project name.")
            st.stop()

        safe_name = project_name.replace(" ", "_")
        filename = f"{safe_name}.geojson"

        try:
            # Upload polygon file
            supabase.storage.from_(BUCKET).upload(
                filename,
                json.dumps(polygon_geojson).encode("utf-8"),
                file_options={
                    "content-type": "application/geo+json",
                    "x-upsert": "true"
                }
            )

            # Insert into projects table
            supabase.table("projects").insert(
                {"name": safe_name, "description": description}
            ).execute()

            # Insert project members
            for email in selected_emails:
                supabase.table("project_members").insert(
                    {"project": safe_name, "user_id": email_to_id[email]}
                ).execute()

            st.success(f"Project '{safe_name}' saved.")

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

    # Load users
    try:
        users = supabase.rpc("get_all_users").execute().data or []
    except:
        users = []

    id_to_email = {u["id"]: u["email"] for u in users}

    # Load members
    pm_res = supabase.table("project_members").select("*").eq("project", selected).execute()
    members = pm_res.data or []

    st.subheader("Users who can work on this project")
    if members:
        for m in members:
            st.write(f"- {id_to_email.get(m['user_id'], 'Unknown')}")
    else:
        st.write("No users assigned.")

    # Load GeoJSON
    filename = f"{selected}.geojson"
    try:
        file_bytes = supabase.storage.from_(BUCKET).download(filename)
        geojson_obj = json.loads(file_bytes.decode("utf-8"))
    except Exception as e:
        st.error(f"Could not load GeoJSON: {e}")
        st.stop()
    
    st.subheader("Project Area")
    
    # ⭐ Compute centroid from geometry
    centroid = compute_centroid(geojson_obj.get("geometry", geojson_obj))
    
    # ⭐ Create map centered on centroid, zoom 17
    m = folium.Map(location=centroid, zoom_start=17, zoom_control=False)
    
    # ⭐ Add polygon(s) — supports Polygon + MultiPolygon
    folium.GeoJson(
        geojson_obj,
        name="Project Area",
        zoom_on_click=False
    ).add_to(m)
    
    # ⭐ Add address search bar
    from folium.plugins import Geocoder
    Geocoder(
        collapsed=False,
        add_marker=True,
        position='topleft'
    ).add_to(m)
    
    st_folium(m, height=500, width=800)


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
        try:
            supabase.storage.from_(BUCKET).remove([f"{selected}.geojson"])
            supabase.table("project_members").delete().eq("project", selected).execute()
            supabase.table("projects").delete().eq("name", selected).execute()

            st.success(f"Project '{selected}' deleted.")

        except Exception as e:
            st.error(f"Error deleting project: {e}")

















