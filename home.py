import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import json
from supabase import create_client
import pandas as pd

# ---------------------------------------------------------
# SUPABASE SETUP
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = "observation_photos"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to:",
    [
        "Create Project",
        "View Projects",
    ],
)

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
    if geojson_obj is None:
        return [52.37, 4.90]  # fallback: Amsterdam-ish

    geom = geojson_obj.get("geometry", geojson_obj)
    if "type" not in geom or "coordinates" not in geom:
        return [52.37, 4.90]

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
# PAGE 1 — CREATE PROJECT
# ---------------------------------------------------------
if page == "Create Project":
    st.title("Create Project")

    st.markdown(
        """
1. Draw a polygon on the map.  
2. Choose a project name and description.  
3. Select which users can work on this project.  
4. Save — this will:
   - Store the polygon as `<project_name>.geojson` in the `observation_photos` bucket  
   - Store the project in the `projects` table (`name`, `description`)  
   - Store members in `project_members` (`project`, `user_id`)
"""
    )

    # Map with drawing
    st.subheader("1. Draw project area")

    m = folium.Map(location=[52.37, 4.90], zoom_start=12)

    draw = Draw(
        draw_options={
            "polyline": False,
            "rectangle": False,
            "circle": False,
            "circlemarker": False,
            "marker": False,
            "polygon": True,
        },
        edit_options={"edit": True, "remove": True},
    )
    draw.add_to(m)

    map_data = st_folium(m, height=500, width=800)

    polygon_geojson = None
    if map_data and "all_drawings" in map_data:
        drawings = map_data["all_drawings"]
        if drawings:
            polygon_geojson = drawings[-1]

    # Project details
    st.subheader("2. Project details")
    project_name_input = st.text_input("Project name")
    project_description = st.text_area("Project description")

    # Users
    st.subheader("3. Select users for this project")
    users = load_users()
    if users:
        email_to_id = {u["email"]: u["id"] for u in users}
        selected_emails = st.multiselect("Users (by email)", list(email_to_id.keys()))
    else:
        st.warning("No users found.")
        selected_emails = []

    # Save button
    if st.button("Save Project"):
        if not polygon_geojson:
            st.error("Please draw a polygon on the map.")
        elif not project_name_input:
            st.error("Please enter a project name.")
        elif not project_description:
            st.error("Please enter a project description.")
        elif not selected_emails:
            st.error("Please select at least one user.")
        else:
            try:
                safe_name = project_name_input.replace(" ", "_")
                filename = f"{safe_name}.geojson"
                geojson_str = json.dumps(polygon_geojson)

                # Upload polygon file to bucket
                supabase.storage.from_(BUCKET).upload(
                    filename,
                    geojson_str.encode("utf-8"),
                    file_options={
                        "content-type": "application/geo+json",
                        "x-upsert": "true",  # allow overwrite if same name
                    },
                )

                # Insert into projects table
                project_res = (
                    supabase.table("projects")
                    .insert({"name": safe_name, "description": project_description})
                    .execute()
                )

                if not project_res.data:
                    st.error("Could not insert project (RLS or schema issue).")
                    st.stop()

                # Insert into project_members
                for email in selected_emails:
                    user_id = email_to_id[email]
                    supabase.table("project_members").insert(
                        {"project": safe_name, "user_id": user_id}
                    ).execute()

                st.success(f"Project '{safe_name}' saved and file '{filename}' uploaded.")

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
    else:
        # Map project name -> row
        name_to_project = {p["name"]: p for p in projects}
        selected_project_name = st.selectbox(
            "Select a project", list(name_to_project.keys())
        )

        project = name_to_project[selected_project_name]
        project_name = project["name"]
        project_description = project.get("description", "")

        st.subheader("Project info")
        st.write(f"**Name:** {project_name}")
        st.write(f"**Description:** {project_description}")

        # Load users and project_members to show emails
        users = load_users()
        id_to_email = {u["id"]: u["email"] for u in users} if users else {}

        try:
            pm_res = (
                supabase.table("project_members")
                .select("user_id")
                .eq("project", project_name)
                .execute()
            )
            members = pm_res.data or []
        except Exception as e:
            st.error(f"Error loading project members: {e}")
            members = []

        st.subheader("Users who can work on this project")
        if members and id_to_email:
            emails = [id_to_email.get(m["user_id"], "Unknown user") for m in members]
            for email in emails:
                st.write(f"- {email}")
        else:
            st.write("No users linked to this project or user lookup failed.")

        # Load GeoJSON from bucket
        filename = f"{project_name}.geojson"
        geojson_obj = None
        try:
            file_bytes = supabase.storage.from_(BUCKET).download(filename)
            geojson_obj = json.loads(file_bytes.decode("utf-8"))
        except Exception as e:
            st.error(f"Could not load GeoJSON file '{filename}': {e}")

        st.subheader("Project area")

        if geojson_obj is None:
            st.info("No geometry available for this project.")
        else:
            centroid = compute_centroid(geojson_obj)
            m = folium.Map(location=centroid, zoom_start=13)

            folium.GeoJson(
                geojson_obj,
                name="Project Polygon",
            ).add_to(m)

            st_folium(m, height=500, width=800)










