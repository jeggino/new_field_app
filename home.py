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
st.subheader("1. Draw your
