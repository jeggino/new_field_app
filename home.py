import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import json
from supabase import create_client

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
def load_users():
    """Return list of users from get_all_users RPC."""
    try:
        res = supabase.rpc("get_all_users").execute()
        return res.data or []
    except Exception:
        return []

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
page = st.sidebar.radio("Navigation", ["Create Project", "View Projects"])

# ---------------------------------------------------------
# PAGE 1 — CREATE PROJECT
# ---------------------------------------------------------
if page == "Create Project":
    st.title("Create Project")

    st.write("Draw a polygon, choose a name, description, and assign users.")

    # Map
    m = folium.Map(location=[52.37, 4.90], zoom_start=12)
    Draw(
        draw_options={"polygon": True, "marker": False, "circle": False,
                      "polyline": False, "rectangle": False},
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    map_data = st_folium(m, height=500, width=800)

    polygon_geojson = None
    if map_data and "all_drawings" in map_data and map_data["all_drawings"]:
        polygon_geojson = map_data["all_drawings"][-1]

    # Inputs
    project_name = st.text_input("Project name")
    description = st.text_area("Description")

    users = load_users()
    email_to_id = {u["email"]: u["id"] for u in users}
    selected_emails = st.multiselect("Users", list(email_to_id.keys()))

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
            # Upload polygon
            supabase.storage.from_(BUCKET).upload(
                filename,
                json.dumps(polygon_geojson).encode("utf-8"),
                file_options={
                    "content-type": "application/geo+json",
                    "x-upsert": "true"
                }
            )

            # Insert project
            supabase.table("projects").insert(
                {"name": safe_name, "description": description}
            ).execute()

            # Insert members
            for email in selected_emails:
                supabase.table("project_members").insert(
                    {"project": safe_name, "user_id": email_to_id[email]}
                ).execute()

            st.success(f"Project '{safe_name}' created.")

        except Exception as e:
            st.error(f"Exception while saving project: {e}")

# ---------------------------------------------------------
# PAGE 2 — VIEW PROJECTS
# ---------------------------------------------------------
elif page == "View Projects":
    st.title("View Projects")

    # Load projects
    try:
        proj_res = supabase.table("projects").select("*").execute()
        projects = proj_res.data or []
    except Exception as e:
        st.error(f"Error loading projects: {e}")
        projects = []

    if not projects:
        st.info("No projects found.")
        st.stop()

    project_names = [p["name"] for p in projects]
    selected = st.selectbox("Select project", project_names)

    project = next(p for p in projects if p["name"] == selected)

    st.subheader("Project Info")
    st.write(f"**Name:** {project['name']}")
    st.write(f"**Description:** {project['description']}")

    # Load users
    users = load_users()
    id_to_email = {u["id"]: u["email"] for u in users}

    # Load members
    try:
        pm_res = supabase.table("project_members").select("*").eq("project", selected).execute()
        members = pm_res.data or []
    except:
        members = []

    st.subheader("Users with access")
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

    centroid = compute_centroid(geojson_obj)

    st.subheader("Project Area")
    m = folium.Map(location=centroid, zoom_start=14)
    folium.GeoJson(geojson_obj).add_to(m)
    st_folium(m, height=500, width=800)











