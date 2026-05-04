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
# SIDEBAR NAVIGATION
# ---------------------------------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to:",
    [
        "Create Project",
        "Projects",
        "User Project Overview",
    ],
)

# ---------------------------------------------------------
# HELPER: LOAD USERS
# ---------------------------------------------------------
def load_users():
    try:
        res = supabase.rpc("get_all_users").execute()
        return res.data or []
    except Exception:
        return []


# ---------------------------------------------------------
# HELPER: GET BOUNDS FROM GEOJSON
# ---------------------------------------------------------
def get_bounds(geojson_obj):
    geom = geojson_obj.get("geometry", geojson_obj)
    coords = []

    if geom["type"] == "Polygon":
        coords = geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            coords.extend(poly[0])

    if not coords:
        return None

    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


# ---------------------------------------------------------
# PAGE 1 — CREATE PROJECT
# ---------------------------------------------------------
if page == "Create Project":
    st.title("Create Project Area")

    with st.expander("ℹ️ How this application works"):
        st.markdown(
            """
**Step 1 — Draw an area on the map**  
Use the polygon tool to outline your project area.

**Step 2 — Enter project details**  
Give your project a name and a short description.

**Step 3 — Select project members**  
Choose which users are allowed to work on this project.

**Step 4 — Save the project**  
When you click *Save Project*:
- The polygon is saved as a GeoJSON file in the bucket **observation_photos**
- The project name (spaces → `_`) and description are saved in the **projects** table
- The selected users are added to the **project_members** table (column `project` = project name)
"""
        )

    # Draw map
    st.subheader("1. Draw your project area")

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
    project_name = st.text_input("Project name")
    project_description = st.text_area("Project description")

    # Select users
    st.subheader("3. Select users who can work on this project")
    users = load_users()
    if users:
        user_options = {u["email"]: u["id"] for u in users}
        selected_users = st.multiselect("Choose users", list(user_options.keys()))
    else:
        st.warning("No users found.")
        selected_users = []

    # Save
    if polygon_geojson and project_name and project_description and selected_users:
        if st.button("Save Project"):
            try:
                geojson_str = json.dumps(polygon_geojson)
                safe_name = project_name.replace(" ", "_")
                filename = f"{safe_name}.geojson"

                # Upload polygon file (overwrite if exists)
                supabase.storage.from_(BUCKET).upload(
                    filename,
                    geojson_str.encode("utf-8"),
                    file_options={
                        "content-type": "application/geo+json",
                        "upsert": "true",
                    },
                )

                # Insert project with safe_name
                project_res = (
                    supabase.table("projects")
                    .insert({"name": safe_name, "description": project_description})
                    .execute()
                )

                if not project_res.data:
                    st.error("Project insert failed. Check RLS policies.")
                    st.stop()

                # Insert project members (project = project name)
                for email in selected_users:
                    user_id = user_options[email]
                    supabase.table("project_members").insert(
                        {"project": safe_name, "user_id": user_id}
                    ).execute()

                st.success(f"Project saved! File uploaded as {filename}")

            except Exception as e:
                st.error(f"Exception: {e}")
    else:
        st.info("Draw a polygon, fill in all fields, and select users to save the project.")

# ---------------------------------------------------------
# PAGE 2 — PROJECTS (VIEW + EDIT)
# ---------------------------------------------------------
elif page == "Projects":
    st.title("Projects")

    # List all projects
    try:
        projects_res = supabase.table("projects").select("*").execute()
        projects = projects_res.data or []
    except Exception as e:
        st.error(f"Error loading projects: {e}")
        projects = []

    if not projects:
        st.info("No projects available.")
    else:
        st.subheader("All projects")
        st.dataframe(projects)

        st.subheader("View and edit a project")

        project_names = {p["name"]: p for p in projects}
        selected_project_name = st.selectbox(
            "Select a project", list(project_names.keys())
        )

        project = project_names[selected_project_name]
        project_name = project["name"]  # fixed (FK)
        current_description = project.get("description", "")

        st.write(f"Project name (fixed): `{project_name}`")
        filename = f"{project_name}.geojson"
        st.write(f"Related file: `{filename}`")

        # Load existing polygon
        existing_geojson = None
        try:
            file_bytes = supabase.storage.from_(BUCKET).download(filename)
            existing_geojson = json.loads(file_bytes.decode("utf-8"))
        except Exception:
            st.warning("Could not load existing polygon file. You can create a new one.")

        st.subheader("1. Polygon (old in red, new replaces it)")

        # Create map
        m = folium.Map(location=[52.37, 4.90], zoom_start=12)

        # Show existing polygon in red and zoom to it
        if existing_geojson is not None:
            folium.GeoJson(
                existing_geojson,
                name="Existing Polygon",
                style_function=lambda x: {"color": "red"},
            ).add_to(m)

            bounds = get_bounds(existing_geojson)
            if bounds:
                m.fit_bounds(bounds)

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

        new_polygon_geojson = None
        if map_data and "all_drawings" in map_data:
            drawings = map_data["all_drawings"]
            if drawings:
                new_polygon_geojson = drawings[-1]

        st.markdown(
            """
- The **red polygon** is the current geometry.  
- If you **draw a new polygon**, it will **replace** the existing one.  
- If you **do nothing on the map**, the existing polygon file will be kept.
"""
        )

        st.subheader("2. Edit project details")
        new_description = st.text_area(
            "Project description", value=current_description
        )

        st.subheader("3. Optional: upload a new GeoJSON file instead of drawing")
        new_file = st.file_uploader(
            "Upload a new polygon file (optional, overrides map drawing if provided)",
            type=["geojson", "json"],
        )

        if st.button("Save Changes"):
            try:
                file_content = None

                if new_file is not None:
                    file_content = new_file.read()
                elif new_polygon_geojson is not None:
                    file_content = json.dumps(new_polygon_geojson).encode("utf-8")

                # If we have new content, upload and replace existing file
                if file_content is not None:
                    supabase.storage.from_(BUCKET).upload(
                        filename,
                        file_content,
                        file_options={
                            "content-type": "application/geo+json",
                            "upsert": "true",
                        },
                    )

                # Update description only (name stays fixed)
                supabase.table("projects").update(
                    {"description": new_description}
                ).eq("id", project["id"]).execute()

                st.success(
                    f"Project updated. Description saved and polygon file "
                    f"{'replaced' if file_content is not None else 'left unchanged'}."
                )

            except Exception as e:
                st.error(f"Error updating project: {e}")

# ---------------------------------------------------------
# PAGE 3 — USER PROJECT OVERVIEW
# ---------------------------------------------------------
elif page == "User Project Overview":
    st.title("User Project Overview")

    try:
        users = load_users()
        user_lookup = {u["id"]: u["email"] for u in users}

        members = supabase.table("project_members").select("*").execute().data or []

        # Build mapping email -> list of projects
        overview = {}
        for m in members:
            uid = m["user_id"]
            pname = m["project"]
            email = user_lookup.get(uid, "Unknown")

            if email not in overview:
                overview[email] = []
            overview[email].append(pname)

        if not overview:
            st.info("No project memberships found.")
        else:
            # Build dropdown options with counts
            options = []
            for email, plist in overview.items():
                label = f"{email} ({len(plist)} projects)"
                options.append((label, email))

            labels = [o[0] for o in options]
            label_to_email = {o[0]: o[1] for o in options}

            selected_label = st.selectbox("Select a user", labels)
            selected_email = label_to_email[selected_label]

            user_projects = overview.get(selected_email, [])

            st.subheader(f"Projects for {selected_email}")
            st.write(f"Number of projects: **{len(user_projects)}**")

            if user_projects:
                st.write("Projects:")
                for p in user_projects:
                    st.write(f"- {p}")

    except Exception as e:
        st.error(f"Error loading overview: {e}")







