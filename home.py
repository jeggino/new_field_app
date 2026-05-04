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
# UI
# ---------------------------------------------------------
st.title("Create Project Area")

with st.expander("ℹ️ How this application works"):
    st.markdown("""
**Step 1 — Draw an area on the map**  
Use the polygon tool to outline your project area.

**Step 2 — Enter project details**  
Give your project a name and a short description.

**Step 3 — Save the project**  
When you click *Save Project*:
- The polygon is saved as a GeoJSON file in the bucket **observation_photos**
- The project name and description are saved in the **projects** table

That's it — your project is stored safely and can be retrieved later.
""")

# ---------------------------------------------------------
# DRAW MAP
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# PROJECT DETAILS
# ---------------------------------------------------------
st.subheader("2. Project details")

project_name = st.text_input("Project name")
project_description = st.text_area("Project description")

# ---------------------------------------------------------
# SAVE BUTTON
# ---------------------------------------------------------
if polygon_geojson and project_name and project_description:
    if st.button("Save Project"):
        try:
            # Convert polygon to GeoJSON string
            geojson_str = json.dumps(polygon_geojson)

            # Create filename
            filename = f"{project_name.replace(' ', '_')}.geojson"

            # 1. Upload file to bucket
            upload_res = supabase.storage.from_(BUCKET).upload(
                filename,
                geojson_str.encode("utf-8"),
                file_options={"content-type": "application/geo+json"}
            )

            # 2. Insert into projects table
            insert_res = supabase.table("projects").insert({
                "name": project_name,
                "description": project_description
            }).execute()

            st.success(f"Project saved! File uploaded as {filename}")

        except Exception as e:
            st.error(f"Exception: {e}")

else:
    st.info("Draw a polygon and fill in all fields to save the project.")

