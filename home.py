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
        "View Projects",
        "View Project Members",
        "User Project Overview",
        "Edit Project",
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
- The selected users are added to the **project_members** table
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

                # Upload polygon file
                supabase.storage.from_(BUCKET).upload(
                    filename,
                    geojson_str.encode("utf-8"),
                    file_options={"content-type": "application/geo+json"},
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

                project_id = project_res.data[0]["id"]

                # Insert project members
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
# PAGE 2 — VIEW PROJECTS
# ---------------------------------------------------------
elif page == "View Projects":
    st.title("Projects Table")
    try:
        res = supabase.table("projects").select("*").execute()
        st.dataframe(res.data)
    except Exception as e:
        st.error(f"Error loading projects: {e}")

# ---------------------------------------------------------
# PAGE 3 — VIEW PROJECT MEMBERS
# ---------------------------------------------------------
elif page == "View Project Members":
    st.title("Project Members Table")
    try:
        members = supabase.table("project_members").select("*").execute().data
        users = load_users()
        user_lookup = {u["id"]: u["email"] for u in users}

        for m in members:
            m["email"] = user_lookup.get(m["user_id"], "Unknown")

        st.dataframe(members)
    except Exception as e:
        st.error(f"Error loading project members: {e}")

# ---------------------------------------------------------
# PAGE 4 — USER PROJECT OVERVIEW
# ---------------------------------------------------------
elif page == "User Project Overview":
    st.title("User Project Overview")

    try:
        users = load_users()
        user_lookup = {u["id"]: u["email"] for u in users}

        members = supabase.table("project_members").select("*").execute().data
        projects = supabase.table("projects").select("*").execute().data
        project_lookup = {p["name"]: p["name"] for p in projects}

        overview = {}
        for m in members:
            uid = m["user_id"]
            pname = m["project"]
            email = user_lookup.get(uid, "Unknown")

            if email not in overview:
                overview[email] = []
            overview[email].append(pname)

        rows = []
        for email, plist in overview.items():
            rows.append(
                {
                    "email": email,
                    "number_of_projects": len(plist),
                    "projects": ", ".join(plist),
                }
            )

        st.dataframe(rows)

    except Exception as e:
        st.error(f"Error loading overview: {e}")

# ---------------------------------------------------------
# PAGE 5 — EDIT PROJECT
# ---------------------------------------------------------
elif page == "Edit Project":
    st.title("Edit Project and Related File")

    try:
        projects_res = supabase.table("projects").select("*").execute()
        projects = projects_res.data or []
    except Exception as e:
        st.error(f"Error loading projects: {e}")
        projects = []

    if not projects:
        st.info("No projects available to edit.")
    else:
        project_names = {p["name"]: p for p in projects}
        selected_project_name = st.selectbox(
            "Select a project to edit", list(project_names.keys())
        )

        project = project_names[selected_project_name]
        current_name = project["name"]
        current_description = project.get("description", "")

        st.write(f"Current file name: `{current_name}.geojson`")

        new_name = st.text_input("New project name", value=current_name)
        new_description = st.text_area(
            "New project description", value=current_description
        )
        new_file = st.file_uploader(
            "Upload a new polygon file to replace the existing one (optional)",
            type=["geojson", "json"],
        )

        if st.button("Save Changes"):
            try:
                safe_new_name = new_name.replace(" ", "_")

                # If a new file is uploaded, replace file in bucket
                if new_file is not None:
                    file_content = new_file.read()
                    new_filename = f"{safe_new_name}.geojson"
                    supabase.storage.from_(BUCKET).upload(
                        new_filename,
                        file_content,
                        file_options={"content-type": "application/geo+json"},
                    )

                # Update project_members to keep FK valid
                supabase.table("project_members").update(
                    {"project": safe_new_name}
                ).eq("project", current_name).execute()

                # Update project record
                supabase.table("projects").update(
                    {"name": safe_new_name, "description": new_description}
                ).eq("id", project["id"]).execute()

                st.success(
                    f"Project updated. Name is now '{safe_new_name}' and file (if uploaded) is '{safe_new_name}.geojson'."
                )

            except Exception as e:
                st.error(f"Error updating project: {e}")





