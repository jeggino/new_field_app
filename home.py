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

# ---------------------------------------------------------
# PAGE — CREATE PROJECT
# ---------------------------------------------------------
st.title("Create Project (with Users)")

st.write("Draw a polygon, enter a name, description, and assign users.")

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

# Load users
users = load_users()
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

        st.success(f"Project '{safe_name}' saved with {len(selected_emails)} users.")

    except Exception as e:
        st.error(f"Exception while saving project: {e}")














