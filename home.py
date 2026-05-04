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
        polygon_geojson




















    

