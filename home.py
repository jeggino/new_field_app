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
        "Projects",
        "User Statistics",
    ],
)

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def load_users():
    try:
        res = supabase.rpc("get_all_users").execute()
        return res.data or []
    except Exception:
        return []


def get_bounds(geojson_obj):
    if geojson_obj is None:
        return None

    geom = geojson_obj.get("geometry", geojson_obj)
    if "type" not in geom or "coordinates" not in geom:
        return None

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

    with st.expander("How this works"):
        st.markdown(
            """
1. Draw a polygon on the map.  
2. Enter a project name and description.  
3. Select users who can work on this project.  
4. Save — this will:
   - Store the polygon as `<project_name>.geojson` in the `observation_photos` bucket  
   - Store the project in the `projects` table  
   - Store members in `project_members` (`project` = project name)
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
                        "upsert": True,
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
                            "upsert": True,
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
# PAGE 3 — USER STATISTICS
# ---------------------------------------------------------
elif page == "User Statistics":
    st.title("User Statistics")

    users = load_users()
    if not users:
        st.info("No users found.")
    else:
        # Build base structures
        emails = [u["email"] for u in users]
        id_by_email = {u["email"]: u["id"] for u in users}

        # Load observations
        try:
            obs_res = supabase.table("observations").select("username").execute()
            observations = obs_res.data or []
        except Exception:
            observations = []

        # Load reports
        try:
            rep_res = supabase.table("report").select("operator").execute()
            reports = rep_res.data or []
        except Exception:
            reports = []

        # Load project_members
        try:
            pm_res = supabase.table("project_members").select("user_id, project").execute()
            project_members = pm_res.data or []
        except Exception:
            project_members = []

        # Count observations per email
        obs_count = {email: 0 for email in emails}
        for row in observations:
            email = row.get("username")
            if email in obs_count:
                obs_count[email] += 1

        # Count reports per email
        rep_count = {email: 0 for email in emails}
        for row in reports:
            email = row.get("operator")
            if email in rep_count:
                rep_count[email] += 1

        # Count projects per email + list of projects
        proj_count = {email: 0 for email in emails}
        proj_list = {email: [] for email in emails}
        for row in project_members:
            uid = row.get("user_id")
            project_name = row.get("project")
            # find email for this uid
            email = None
            for e, i in id_by_email.items():
                if i == uid:
                    email = e
                    break
            if email is not None:
                proj_count[email] += 1
                if project_name not in proj_list[email]:
                    proj_list[email].append(project_name)

        # Build dropdown options with project count
        options = []
        for email in emails:
            label = f"{email} ({proj_count[email]} projects)"
            options.append((label, email))

        labels = [o[0] for o in options]
        label_to_email = {o[0]: o[1] for o in options}

        selected_label = st.selectbox("Select a user", labels)
        selected_email = label_to_email[selected_label]

        # Stats for selected user
        n_obs = obs_count.get(selected_email, 0)
        n_rep = rep_count.get(selected_email, 0)
        n_proj = proj_count.get(selected_email, 0)
        user_projects = proj_list.get(selected_email, [])

        st.subheader(f"Overview for {selected_email}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Observations", n_obs)
        col2.metric("Reports", n_rep)
        col3.metric("Projects", n_proj)

        # Bar chart
        st.subheader("Activity chart")
        df_chart = pd.DataFrame(
            {
                "metric": ["Observations", "Reports", "Projects"],
                "value": [n_obs, n_rep, n_proj],
            }
        ).set_index("metric")
        st.bar_chart(df_chart)

        # Projects list
        st.subheader("Projects")
        if user_projects:
            for p in user_projects:
                st.write(f"- {p}")
        else:
            st.write("No projects for this user.")

        # Optional raw counts table
        st.subheader("Raw counts table")
        df_counts = pd.DataFrame(
            [
                {
                    "email": email,
                    "observations": obs_count[email],
                    "reports": rep_count[email],
                    "projects": proj_count[email],
                }
                for email in emails
            ]
        )
        st.dataframe(df_counts)








