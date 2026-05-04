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
# PAGE — CREATE PROJECT
# ---------------------------------------------------------
st.title("Create Project (Minimal Version)")

st.write("Draw a polygon, enter a name, and save the project.")

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

        st.success(f"Project '{safe_name}' saved.")

    except Exception as e:
        st.error(f"Exception while saving project: {e}")













