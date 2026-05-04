import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import json
import uuid
from supabase import create_client, Client

# ---------------------------------------------------------
# SUPABASE SETUP
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = "observation_photos"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="Polygon Creator", layout="wide")
st.title("📍 Draw & Save Polygon Areas")

st.write("Draw a polygon, name it, preview it, edit it, and save it to Supabase.")

# ---------------------------------------------------------
# DRAW MAP
# ---------------------------------------------------------
st.subheader("1. Draw your area")

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

# ---------------------------------------------------------
# EXTRACT GEOJSON FROM DRAW TOOL
# ---------------------------------------------------------
polygon_geojson = None

if map_data and "all_drawings" in map_data:
    drawings = map_data["all_drawings"]
    if drawings:
        polygon_geojson = drawings[-1]  # last drawn polygon

# ---------------------------------------------------------
# NAME INPUT
# ---------------------------------------------------------
st.subheader("2. Name your area")

area_name = st.text_input("Area name", placeholder="Example: North Field A")

# ---------------------------------------------------------
# PREVIEW SECTION
# ---------------------------------------------------------
if polygon_geojson and area_name:
    st.subheader("3. Preview your area")

    st.write("### 🗺️ Polygon Preview")
    st.json(polygon_geojson)

    st.write(f"### 🏷️ Name: **{area_name}**")

    st.info("If needed, go back to the map and edit the polygon or change the name.")

# ---------------------------------------------------------
# SAVE BUTTON
# ---------------------------------------------------------
if polygon_geojson and area_name:
    if st.button("💾 Save to Supabase"):
        try:
            # Convert polygon to GeoJSON string
            geojson_str = json.dumps(polygon_geojson)

            # Create filename
            safe_name = area_name.replace(" ", "_")
            file_id = f"{safe_name}_{uuid.uuid4()}.geojson"

            # Upload to Supabase bucket
            upload_res = supabase.storage.from_(BUCKET).upload(
                file_id,
                geojson_str.encode("utf-8"),
                file_options={"content-type": "application/geo+json"}
            )

            if upload_res.get("error"):
                st.error(f"Upload failed: {upload_res['error']}")
                st.stop()

            # Insert into projects table
            insert_res = supabase.table("projects").insert({
                "area_file": file_id,
                "area_name": area_name
            }).execute()

            if insert_res.get("error"):
                st.error(f"Database insert failed: {insert_res['error']}")
                st.stop()

            st.success(f"Saved successfully as {file_id}")

        except Exception as e:
            st.error(f"Upload failed: {e}")

else:
    st.warning("Draw a polygon and enter a name to continue.")




















    

