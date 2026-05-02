import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import LocateControl, BeautifyIcon
from supabase import create_client, Client
from datetime import datetime
import uuid

# ----------------- CONFIG -----------------
st.set_page_config(
    page_title="",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}  # removes GitHub / fork icons
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

PROJECTS_TABLE = "projects"
OBS_TABLE = "observations"
BUCKET = "observation_photos"

CROSS_IMAGE_PATH = "https://static.vecteezy.com/system/resources/previews/031/742/868/non_2x/transparent-circle-cross-icon-free-png.png"
OPACITY = 1
WIDTH = 30

# ----------------- SPECIES LISTS -----------------
BAT_SPECIES = [
    'Gewone dwergvleermuis','Ruige dwergvleermuis','Laatvlieger','Rosse vleermuis',
    'Baardvleermuis','Meervleermuis','Watervleermuis','Kleine dwergvleermuis',
    'Tweekleurige vleermuis','Gewone grootoorvleermuis','onbekend'
]

BIRD_SPECIES = [
    'Gierzwaluw','Huiszwaluw','Boerenzwaluw','Huismus','Spreeuw',
    'Boomkruiper','Kauw','..ander'
]

# ----------------- FUNCTION LISTS -----------------
BAT_FUNCTIONS = [
    'vleermuis waarneming','zomerverblijfplaats','kraamverblijfplaats',
    'paarverblijfplaats','winterverblijfplaats','vleermuiskast','zender'
]

BIRD_FUNCTIONS = [
    'vogel waarneming','nestlocatie','mogelijke nestlocatie'
]

# ----------------- ICONS FOR FUNCTIONS -----------------
FUNCTION_ICONS = {
    "vleermuis waarneming": "info-sign",
    "zomerverblijfplaats": "sun",
    "kraamverblijfplaats": "heart",
    "paarverblijfplaats": "star",
    "winterverblijfplaats": "snowflake",
    "vleermuiskast": "home",
    "zender": "signal",

    "vogel waarneming": "info-sign",
    "nestlocatie": "home",
    "mogelijke nestlocatie": "question-sign",
}

# ----------------- COLORS FOR SPECIES -----------------
ALL_SPECIES = BAT_SPECIES + BIRD_SPECIES
COLOR_PALETTE = [
    "red","green","blue","purple","orange","darkred","lightred","beige","darkblue",
    "darkgreen","cadetblue","darkpurple","white","pink","lightblue","lightgreen",
    "gray","black"
]
SPECIES_COLORS = {sp: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, sp in enumerate(ALL_SPECIES)}

# ----------------- SHAPE SETTINGS -----------------
BAT_BORDER = True  # border around bat markers

# ----------------- INIT -----------------
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

defaults = {
    "logged_in": False,
    "user": None,
    "session": None,
    "project": None,
    "changing_project": False,
    "observations": [],
    "map_center": [52.0, 5.0],
    "map_input_center": [52.0, 5.0],
    "map_input_zoom": 6,
    "show_signup": False,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ----------------- AUTH -----------------
def login(email: str, password: str):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return None


def signup(email: str, password: str):
    try:
        return supabase.auth.sign_up({"email": email, "password": password})
    except Exception:
        return None


def logout():
    supabase.auth.sign_out()
    st.session_state.clear()
    for k, v in defaults.items():
        st.session_state[k] = v
    st.rerun()


# ----------------- DATA HELPERS -----------------
def load_projects():
    user = st.session_state.user
    if not user:
        return []
    res = (
        supabase
        .table(PROJECTS_TABLE)
        .select("*")
        .eq("user_id", user.id)
        .execute()
    )
    return res.data or []


def load_observations(project_name: str):
    res = (
        supabase
        .table(OBS_TABLE)
        .select("*")
        .eq("project", project_name)
        .order("date", desc=False)
        .execute()
    )
    st.session_state.observations = res.data or []

    if st.session_state.observations:
        last = st.session_state.observations[-1]
        st.session_state.map_center = [last["lat"], last["lon"]]
        st.session_state.map_input_center = [last["lat"], last["lon"]]


# ----------------- STORAGE HELPERS -----------------
def upload_photo(file):
    if not file:
        return None

    try:
        file_bytes = file.read()
        if not file_bytes:
            return None

        ext = file.name.split(".")[-1]
        file_id = f"{uuid.uuid4()}.{ext}"

        supabase.storage.from_(BUCKET).upload(
            file_id,
            {"file": file_bytes},
        )

        return supabase.storage.from_(BUCKET).get_public_url(file_id)

    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None


# ----------------- MAP HELPERS -----------------
def _get_center_from_map_data(map_data, fallback_center):
    if not map_data:
        return fallback_center
    if "center" not in map_data:
        return fallback_center
    return [map_data["center"]["lat"], map_data["center"]["lng"]]


# ----------------- LEGEND -----------------
@st.dialog("Legend")
def show_legend():
    st.subheader("Animal Type (shape)")
    st.write("🟣 **Circle** = Bat")
    st.write("🟩 **Square** = Bird")

    st.subheader("Species Colors")
    for sp, col in SPECIES_COLORS.items():
        st.write(f"● <span style='color:{col}'>{sp}</span>", unsafe_allow_html=True)

    st.subheader("Function Icons")
    for func, icon in FUNCTION_ICONS.items():
        st.write(f"🔹 {func} → {icon}")


# ----------------- EDIT OBSERVATION -----------------
@st.dialog("Edit Observation")
def edit_observation_dialog(obs):
    st.write("Move the map to update coordinates.")

    # Map for coordinate update
    m = folium.Map(location=[obs["lat"], obs["lon"]], zoom_start=18)
    LocateControl(auto_start=False).add_to(m)

    crosshair_html = f"""
    <div style='position: fixed; top: 50%; left: 50%; 
    transform: translate(-50%, -50%); pointer-events: none; z-index: 9999;'>
        <img src="{CROSS_IMAGE_PATH}" style="width:{WIDTH}px; opacity:{OPACITY};">
    </div>
    """
    m.get_root().html.add_child(folium.Element(crosshair_html))

    map_data = st_folium(m, width="100%", height=300)

    try:
        lat = map_data["center"]["lat"]
        lon = map_data["center"]["lng"]
    except:
        lat, lon = obs["lat"], obs["lon"]

    # Photo preview
    if obs.get("photo_url"):
        st.image(obs["photo_url"], width=250)

    # Animal type
    animal_type = st.radio("Animal type", ["bat", "bird"], index=0 if obs["animal_type"]=="bat" else 1)

    species_list = BAT_SPECIES if animal_type=="bat" else BIRD_SPECIES
    function_list = BAT_FUNCTIONS if animal_type=="bat















    

