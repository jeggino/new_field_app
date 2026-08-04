import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import LocateControl, BeautifyIcon, MarkerCluster, Draw, StripePattern, CirclePattern, Fullscreen
from supabase import create_client, Client
from datetime import datetime, time
import uuid
import json
import pandas as pd
import re
import time

import colorsys




# ----------------- CONFIG -----------------
st.set_page_config(
    page_title="",
    layout="wide",
    initial_sidebar_state="expanded"
)



SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

PROJECTS_TABLE = "project_members"
OBS_TABLE = "observations"
OBS_POLYGONS = "polygons_app"
BUCKET = "observation_photos"

CROSS_IMAGE_PATH = "https://static.vecteezy.com/system/resources/previews/031/742/868/non_2x/transparent-circle-cross-icon-free-png.png"
OPACITY = 1
WIDTH = 30

# ----------------- LOGO --------------------------
IMAGE = "https://www.nachtvandevleermuis.nl/wp-content/uploads/Elsken_Ecologie_LOGO-min-1024x748.png"

# ................. ICON CUSTUMIZE ----------------
marker_size = 28
inner_icon_px = 12

#------------------  MAP SIZE ---------------------
map_height = 510

# ----------------- REPORT KINDS ------------------
REPORT_KINDS = [
    'Kraamverblijf Avond (1/2)','Kraamverblijf Avond (2/2)','Kraamverblijf Ochtend (1/3)', 'Kraamverblijf Ochtend (2/3)', 'Kraamverblijf Ochtend (3/3)',
    'Winterverblijf','Paarverblijf (1/2)',
    'Paarverblijf (2/2)', 'Huismus (1/3)','Huismus (2/3)', 'Huismus (3/3)','Gierzwaluw (1/3)','Gierzwaluw (2/3)','Gierzwaluw (3/3)','Steenuil (1/3)','Steenuil (2/3)', 'Steenuil (3/3)'
]

REPORT_RAIN = ["Droog", "Nevel/mist", "Motregen"]
# ----------------- SPECIES LISTS -----------------
BAT_SPECIES = [
    'Gewone dwergvleermuis','Ruige dwergvleermuis','Laatvlieger','Rosse vleermuis',
    'Baardvleermuis','Meervleermuis','Watervleermuis','Kleine dwergvleermuis',
    'Tweekleurige vleermuis','Gewone grootoorvleermuis','onbekend'
]

BIRD_SPECIES = [
    'Gierzwaluw','Huiszwaluw','Boerenzwaluw','Huismus','Spreeuw',
    'Boomkruiper','Kauw','Steenuil','..ander'
]

PLANT_SPECIES = [
    'Sneeuwbes',
     'Gewone dwergvleermuis',
     'Japanse berberis',
     'Broodboom',
     'Tuinjudaspenning',
     'Deutzia',
     'Zegekruid',
     'Japanse duizendknoop',
     'Gewone hortensia',
     'Bamboe',
    '..ander'
    ]

DUTCH_AMPHIBIANS = [
    "Kleine watersalamander",
    "Alpenwatersalamander",
    "Kamsalamander",
    "Vinpootsalamander",
    "Bruine kikker",
    "Heikikker",
    "Poelkikker",
    "Meerkikker",
    "Middelste groene kikker",
    "Boomkikker",
    "Gewone pad",
    "Rugstreeppad",
    "Vroedmeesterpad",
]

ODONATA_SPECIES = [
    "Azuurwaterjuffer",
    "Lantaarntje",
    "Gewone pantserjuffer",
    "Weidebeekjuffer",
    "Bosbeekjuffer",
    "Vuurjuffer",
    "Variabele waterjuffer",
    "Grote roodoogjuffer",
    "Paardenbijter",
    "Blauwe glazenmaker",
    "Bruine glazenmaker",
    "Grote keizerlibel",
    "Glassnijder",
    "Platbuik",
    "Viervlek",
    "Gewone oeverlibel",
    "Bruinrode heidelibel",
    "Bloedrode heidelibel",
    "Steenrode heidelibel",
    "Vuurlibel",
]

# ----------------- FUNCTION LISTS -----------------
BAT_FUNCTIONS = [
    'vleermuis waarneming','zomerverblijfplaats','kraamverblijfplaats',
    'paarverblijfplaats','winterverblijfplaats','vleermuiskast','zender'
]

BIRD_FUNCTIONS = [
    'vogel waarneming','nestlocatie','mogelijke nestlocatie'
]

BAT_FUNCTIONS_POLYGON = [
    'foerageergebied','paarterritorium'
]

BIRD_FUNCTIONS_POLYGON = [
    'dekking','foerageergebied','slaapplaats/broedgebied', 'water als dronk en/of badderplaats', 'zandplekken'
]

PLANT_FUNCTIONS = [ 
    "Aanwezig", 
    "Bloeiend", 
    "Vrucht", 
    "Dood",
]

PLANT_FUNCTIONS_POLYGON = [ 
    "Groeiplaats", 
    "Vegetatie", 
    "Dominante soort",
]



AMPHIBIE_FUNCTIONS = [ 
    "Volwassen", 
    "Roepend", 
    "Paring", 
    "Eieren", 
    "Larven", 
    "Jong dier", 
    "Foeragerend", 
    "Trek", 
    "Dood",
]

AMPHIBIE_FUNCTIONS_POLYGON = [ 
    "Voortplantingswater", 
    "Larvenhabitat", 
    "Foerageergebied", 
    "Migratieroute", 
    "Overwinteringsgebied",
]

ODONATA_FUNCTIONS = [ 
    "Volwassen", 
    "Paring", 
    "Eiafzet", 
    "Tandem", 
    "Uitsluipen", 
    "Larve", 
    "Exuvia", 
    "Rustend", 
    "Foeragerend", 
    "Dood",
]

ODONATA_FUNCTIONS_POLYGON = [ 
    "Voortplantingswater", 
    "Eiafzetgebied", 
    "Larvenhabitat", 
    "Foerageergebied", 
    "Rustgebied",
]

# ---------------- SHORT NAMES --------------------------------
SPECIES_SHORT = {

    # BATS
    "Gewone dwergvleermuis": "GDV",
    "Ruige dwergvleermuis": "RDV",
    "Laatvlieger": "LV",
    "Rosse vleermuis": "RV",
    "Baardvleermuis": "BV",
    "Meervleermuis": "MV",
    "Watervleermuis": "WV",
    "Kleine dwergvleermuis": "KDV",
    "Tweekleurige vleermuis": "TV",
    "Gewone grootoorvleermuis": "GGV",
    "onbekend": "ONB",

    # BIRDS
    "Gierzwaluw": "GZW",
    "Huiszwaluw": "HZW",
    "Boerenzwaluw": "BZW",
    "Huismus": "HM",
    "Spreeuw": "SPR",
    "Boomkruiper": "BKR",
    "Kauw": "KAW",
    "Steenuil": "STU",
    "..ander": "AND",

    # PLANTS
    "Sneeuwbes": "SNB",
    "Japanse berberis": "JBB",
    "Broodboom": "BRB",
    "Tuinjudaspenning": "TJP",
    "Deutzia": "DEU",
    "Zegekruid": "ZKG",
    "Japanse duizendknoop": "JDK",
    "Gewone hortensia": "GHO",
    "Bamboe": "BAM",

    # AMPHIBIANS
    "Kleine watersalamander": "KWS",
    "Alpenwatersalamander": "AWS",
    "Kamsalamander": "KAM",
    "Vinpootsalamander": "VPS",
    "Bruine kikker": "BRK",
    "Heikikker": "HEK",
    "Poelkikker": "POK",
    "Meerkikker": "MEK",
    "Middelste groene kikker": "MGK",
    "Boomkikker": "BOK",
    "Gewone pad": "GEP",
    "Rugstreeppad": "RSP",
    "Vroedmeesterpad": "VMP",

    # ODONATA
    "Azuurwaterjuffer": "AWJ",
    "Lantaarntje": "LAN",
    "Gewone pantserjuffer": "GPJ",
    "Weidebeekjuffer": "WBJ",
    "Bosbeekjuffer": "BBJ",
    "Vuurjuffer": "VUJ",
    "Variabele waterjuffer": "VWJ",
    "Grote roodoogjuffer": "GRJ",
    "Paardenbijter": "PB",
    "Blauwe glazenmaker": "BGM",
    "Bruine glazenmaker": "BRG",
    "Grote keizerlibel": "GKL",
    "Glassnijder": "GLS",
    "Platbuik": "PLB",
    "Viervlek": "VVL",
    "Gewone oeverlibel": "GOL",
    "Bruinrode heidelibel": "BHL",
    "Bloedrode heidelibel": "BDL",
    "Steenrode heidelibel": "SHL",
    "Vuurlibel": "VUL",
}

FUNCTION_SHORT = {

    # Bats
    "vleermuis waarneming": "WA",
    "zomerverblijfplaats": "ZV",
    "kraamverblijfplaats": "KV",
    "paarverblijfplaats": "PV",
    "winterverblijfplaats": "WV",
    "vleermuiskast": "VK",
    "zender": "ZD",

    # Birds
    "vogel waarneming": "WA",
    "nestlocatie": "NL",
    "mogelijke nestlocatie": "MNL",

    # Polygon
    "foerageergebied": "FG",
    "paarterritorium": "PT",
    "dekking": "DK",
    "slaapplaats/broedgebied": "SB",
    "water als dronk en/of badderplaats": "WB",
    "zandplekken": "ZP",

    # Plants
    "Aanwezig": "AA",
    "Bloeiend": "BL",
    "Vrucht": "VR",
    "Dood": "DD",
    "Groeiplaats": "GP",
    "Vegetatie": "VEG",
    "Dominante soort": "DS",

    # Amphibians
    "Volwassen": "VOL",
    "Roepend": "ROE",
    "Paring": "PAR",
    "Eieren": "EI",
    "Larven": "LAR",
    "Jong dier": "JD",
    "Foeragerend": "FOE",
    "Trek": "TRK",
    "Dood": "DD",
    "Voortplantingswater": "VW",
    "Larvenhabitat": "LH",
    "Migratieroute": "MR",
    "Overwinteringsgebied": "OW",

    # Odonata
    "Eiafzet": "EA",
    "Tandem": "TAN",
    "Uitsluipen": "UIT",
    "Larve": "LAR",
    "Exuvia": "EX",
    "Rustend": "RUS",
    "Eiafzetgebied": "EG",
    "Rustgebied": "RG",
}


# ---------------- PICTOGRAMMEN VOOR FUNCTIES -----------------
FUNCTION_ICONS = {
    # Bats
    "vleermuis waarneming": "walkie-talkie",
    "zomerverblijfplaats": "sun",
    "kraamverblijfplaats": "venus",
    "paarverblijfplaats": "heart",
    "winterverblijfplaats": "snowflake",
    "vleermuiskast": "box-archive",
    "zender": "tower-broadcast",

    # Birds
    "vogel waarneming": "binoculars",
    "nestlocatie": "egg",
    "mogelijke nestlocatie": "question",

    # Plants
    "Aanwezig": "leaf",
    "Bloeiend": "seedling",
    "Vrucht": "apple-whole",
    "Dood": "skull-crossbones",

    # Amphibians
    "Adult": "frog",
    "Roepend": "volume-high",
    "Paring": "heart",
    "Eieren": "egg",
    "Larven": "water",
    "Jong dier": "child",
    "Foeragerend": "utensils",
    "Trek": "route",

    # Odonata
    "Eiafzet": "egg",
    "Tandem": "link",
    "Uitsluiping": "arrow-up-right-dots",
    "Larve": "water",
    "Exuvia": "shirt",
    "Rustend": "pause",
}

# ----------------- COLORS FOR SPECIES -----------------
def generate_colors(species_list):
    n = len(species_list)

    colors = []
    for i in range(n):
        h = i / n
        r, g, b = colorsys.hsv_to_rgb(h, 0.8, 0.9)
        colors.append(
            f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        )

    return dict(zip(species_list, colors))

BAT_COLORS = generate_colors(BAT_SPECIES)
BIRD_COLORS = generate_colors(BIRD_SPECIES)
PLANT_COLORS = generate_colors(PLANT_SPECIES)
AMPHIBIAN_COLORS = generate_colors(DUTCH_AMPHIBIANS)
ODONATA_COLORS = generate_colors(ODONATA_SPECIES)

SPECIES_COLORS = {
    **BAT_COLORS,
    **BIRD_COLORS,
    **PLANT_COLORS,
    **AMPHIBIAN_COLORS,
    **ODONATA_COLORS,
}

# ----------------- GET DIRECTION ------------------
def show_google_maps_button():
    boundary, bounds = load_project_boundary(st.session_state.project)

    centroid_lat = (bounds[0][0] + bounds[1][0]) / 2
    centroid_lng = (bounds[0][1] + bounds[1][1]) / 2

    if centroid_lat and centroid_lng:
        maps_url = f"https://www.google.com/maps?q={centroid_lat},{centroid_lng}"

        st.sidebar.link_button(
            "🗺️ Open in Google Maps",
            maps_url,
            use_container_width=True,
        )
# ----------------- SHAPE SETTINGS -----------------
BAT_BORDER = True

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
    "polygons": [],
    "map_center": [52.0, 5.0],
    "map_input_center": [52.0, 5.0],
    "map_input_zoom": 6,
    "show_signup": False,
    "selected_obs_id": None,
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
def get_project_description():
    try:
        response = (
            supabase.table("projects")
            .select("description")
            .eq("name", st.session_state["project"])
            .single()
            .execute()
        )

        if response.data:
            return response.data.get("description")

        return None

    except Exception as e:
        st.error(f"Error loading project description: {e}")
        return None

def load_projects():
    user = st.session_state.user
    if not user:
        return []
    res = (
        supabase
        .table(PROJECTS_TABLE)
        .select("project")
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

def load_polygons(project_name: str):
    res = (
        supabase
        .table(OBS_POLYGONS)
        .select("*")
        .eq("project", project_name)
        .order("date", desc=False)
        .execute()
    )
    st.session_state.polygons = res.data or []


def load_project_boundary(project_name):
    """Load <project>.geojson from Supabase and return (geojson_dict, bounds)."""

    filename = f"{project_name}.geojson"

    try:
        file_bytes = supabase.storage.from_(BUCKET).download(filename)
        if not file_bytes:
            return None, None

        geojson_str = file_bytes.decode("utf-8")
        data = json.loads(geojson_str)

        # Extract coordinates for bounds
        coords = []

        def extract_coords(geom):
            t = geom["type"]
            c = geom["coordinates"]

            if t == "Polygon":
                for ring in c:
                    coords.extend(ring)

            elif t == "MultiPolygon":
                for poly in c:
                    for ring in poly:
                        coords.extend(ring)

        # GeoJSON may be Feature or FeatureCollection
        if data.get("type") == "Feature":
            extract_coords(data["geometry"])

        elif data.get("type") == "FeatureCollection":
            for feature in data["features"]:
                extract_coords(feature["geometry"])

        if not coords:
            return data, None

        lats = [p[1] for p in coords]
        lngs = [p[0] for p in coords]

        bounds = [[min(lats), min(lngs)], [max(lats), max(lngs)]]

        return data, bounds

    except Exception as e:
        st.warning(f"Could not load boundary for project '{project_name}': {e}")
        return None, None


def download_observations_csv():
    """Return a CSV bytes object for all observations of the current project."""
    obs = st.session_state.observations

    if not obs:
        return None

    df = pd.DataFrame(obs)

    return df.to_csv(index=False).encode("utf-8")


# ----------------- STORAGE HELPERS -----------------
def upload_photo(file):
    if not file:
        return None

    try:
        # Read file bytes safely
        file_bytes = file.getvalue()
        if not file_bytes:
            return None

        # Build unique filename
        ext = file.name.split(".")[-1].lower()
        file_id = f"{uuid.uuid4()}.{ext}"

        # Upload to Supabase
        supabase.storage.from_(BUCKET).upload(
            file_id,
            file_bytes,
            file_options={"content-type": f"image/{ext}"}
        )

        # Return public URL
        return supabase.storage.from_(BUCKET).get_public_url(file_id)

    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None


# ----------------- HELPER FUNCTION -------------
def delete_photo_from_storage(photo_url):
    """
    Extracts the file name from the Supabase public URL
    and deletes it from the storage bucket.
    """
    if not photo_url:
        return

    try:
        # Example URL:
        # https://xxxx.supabase.co/storage/v1/object/public/observations/myphoto.jpg
        filename = photo_url.split("/")[-1]

        supabase.storage.from_(BUCKET).remove(filename)

    except Exception as e:
        st.warning(f"Could not delete photo: {e}")

def extract_id_from_popup(popup_html):
    if not popup_html:
        return None
    match = re.search(r"<span style=\"display:none\">(.*?)</span>", popup_html)
    return match.group(1) if match else None

def parse_time_safe(value):
    """Convert a Supabase time string into a Python time object safely."""
    if not value:
        return time(0, 0)

    value = value.strip()

    # # If already a time object
    # if isinstance(value, time):
    #     return value

    # Try HH:MM
    try:
        return datetime.strptime(value, "%H:%M").time()
    except:
        pass

    # Try HH:MM:SS
    try:
        return datetime.strptime(value, "%H:%M:%S").time()
    except:
        pass

    # Try HH:MM:SS.microseconds
    try:
        return datetime.strptime(value, "%H:%M:%S.%f").time()
    except:
        pass

    # Fallback
    return time(0, 0)

# ----------------- MAP HELPERS -----------------
def _get_center_from_map_data(map_data, fallback_center):
    if not map_data:
        return fallback_center
    if "center" not in map_data:
        return fallback_center
    return [map_data["center"]["lat"], map_data["center"]["lng"]]



# ----------------- EDIT OBSERVATION -----------------
@st.dialog("Daily Report")
def daily_report_dialog():
    st.write("Fill in the daily report.")

    kind = st.selectbox("Kind", REPORT_KINDS)

    with st.expander("Choose date"):
        date = st.date_input("Date", value=datetime.utcnow().date())

    start_time = st.time_input("Start Time",value=None)
    end_time = st.time_input("End Time",value=None)
    operator = st.text_input("Operator", value=st.session_state.user.email)
    extra_operator = st.text_input("Extra Operator")
    temperature = st.number_input("Temperature (°C)", step=1)
    wind = st.number_input("Wind", step=1)
    rain = st.selectbox("Rain", REPORT_RAIN)
    comment = st.text_area("Comment")

    if st.button("Submit Report", width="stretch"):

        # ---------------------------------------------------------
        # CHECK FOR DUPLICATE REPORT (same project + same kind)
        # ---------------------------------------------------------
        existing = (
            supabase.table("report")
            .select("id")
            .eq("project", st.session_state.project)
            .eq("kind", kind)
            .execute()
        )

        if existing.data:
            st.error(f"A report of kind **{kind}** already exists for this project.")
            st.stop()

        # ---------------------------------------------------------
        # INSERT NEW REPORT
        # ---------------------------------------------------------
        supabase.table("report").insert({
            "kind": kind,
            "date": str(date),
            "operator": operator,
            "extra_operator": extra_operator,
            "start_time": str(start_time),
            "end_time": str(end_time),
            "temperature": temperature,
            "wind": wind,
            "rain": rain,
            "comment": comment,
            "project": st.session_state.project
        }).execute()

        st.success("Report submitted.")
        time.sleep(1)
        st.rerun()

@st.dialog("Daily Reports")
def show_reports_dialog():
    st.subheader("Daily Reports")

    # Load reports
    res = (
        supabase.table("report")
        .select("*")
        .eq("project", st.session_state.project)
        .order("date", desc=True)
        .execute()
    )
    reports = res.data or []

    if not reports:
        st.info("No reports yet.")
        return

    # Map for dropdown
    report_map = {
        f"{r['kind']} - {r['date']}": r
        for r in reports
    }

    tab_view, tab_edit = st.tabs(["📄 View Report", "✏️ Edit / Delete Report"])

    # ---------------------------------------------------------
    # TAB 1 — VIEW ONLY
    # ---------------------------------------------------------
    with tab_view:
        st.write("Select a report to view")

        selected_label = st.selectbox("Report", list(report_map.keys()), key="view_select")
        r = report_map[selected_label]

        st.markdown("### Report Details")
        st.write(f"**Kind:** {r['kind']}")
        st.write(f"**Date:** {r['date']}")
        st.write(f"**Operator:** {r['operator']}")
        st.write(f"**Extra Operator:** {r.get('extra_operator','')}")
        st.write(f"**Start Time:** {r.get('start_time','')}")
        st.write(f"**End Time:** {r.get('end_time','')}")
        st.write(f"**Temperature:** {r.get('temperature','')}")
        st.write(f"**Wind:** {r.get('wind','')}")
        st.write(f"**Rain:** {r.get('rain','')}")
        st.write(f"**Comment:** {r.get('comment','')}")

    # ---------------------------------------------------------
    # TAB 2 — EDIT / DELETE
    # ---------------------------------------------------------
    with tab_edit:
        st.write("Select a report to edit or delete")

        selected_label = st.selectbox("Report", list(report_map.keys()), key="edit_select")
        report = report_map[selected_label]

        "---"

        # Editable fields
        kind = st.selectbox("Kind", REPORT_KINDS,
                            index=REPORT_KINDS.index(report["kind"]))

        with st.expander("Edit date"):
            date = st.date_input("Date", value=datetime.fromisoformat(report["date"]).date())

        start_time = st.time_input("Start Time", value=parse_time_safe(report.get("start_time")))
        end_time = st.time_input("End Time", value=parse_time_safe(report.get("end_time")))
        operator = st.text_input("Operator", value=report["operator"])
        extra_operator = st.text_input("Extra Operator", value=report.get("extra_operator", ""))

        temperature = st.number_input("Temperature (°C)", step=1, value=int(report.get("temperature")))
        wind = st.number_input("Wind", step=1, value=int(report.get("wind")))
        rain = st.selectbox("Rain", REPORT_RAIN,
                            index=REPORT_RAIN.index(report["rain"]))
        comment = st.text_area("Comment", value=report.get("comment", ""))

        # Save changes
        if st.button("Save Changes", use_container_width=True):
            supabase.table("report").update({
                "kind": kind,
                "date": str(date),
                "operator": operator,
                "extra_operator": extra_operator,
                "start_time": str(start_time),
                "end_time": str(end_time),
                "temperature": temperature,
                "wind": wind,
                "rain": rain,
                "comment": comment
            }).eq("id", report["id"]).execute()

            st.success("Report updated.")
            time.sleep(1)
            st.rerun()

        # ---------------------------------------------------------
        # DELETE WITH CONFIRMATION (NO NESTED DIALOG)
        # ---------------------------------------------------------
        
        # Step 1: user clicks delete → activate confirmation mode
        if st.button("Delete Report", type="secondary", use_container_width=True):
            supabase.table("report").delete().eq("id", report["id"]).execute()
            st.rerun()





@st.dialog("Edit Observation")
def edit_observation_dialog(obs):
    st.write("Move the map to adjust the coordinates")
    
    edit_center = [obs["lat"], obs["lon"]]
    m = folium.Map(location=edit_center, zoom_start=18, zoom_control=False)
    LocateControl(auto_start=False).add_to(m)

    # Satellite (Esri)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=False
    ).add_to(m)


    # BeautifyIcon marker
    marker_icon = BeautifyIcon(
        icon="map-marker",
        icon_shape="marker",
        icon_anchor=[marker_size/2, marker_size],
        background_color="blue",
        border_color="black",
        border_width=0.7,
        text_color="white",
        icon_size=[marker_size, marker_size],                 # marker size
        inner_icon_style=f"font-size:{inner_icon_px}px; display:flex; align-items:center; justify-content:center; width:100%; height:100%; text-align:center; padding:0; margin:0" # icon size
    )

    folium.Marker(
        location=[obs["lat"], obs["lon"]],
        icon=marker_icon,
        popup="Original location"
    ).add_to(m)

    
    crosshair_html = f"""
    <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 9999;
    ">
        <img src="{CROSS_IMAGE_PATH}"
             style="width:{WIDTH}px; opacity:{OPACITY};">
    </div>
    """
    m.get_root().html.add_child(folium.Element(crosshair_html))
    
    map_data = st_folium(m, width="100%", height=350)
    
    try:
        new_lat = map_data["center"]["lat"]
        new_lon = map_data["center"]["lng"]
    except:
        new_lat, new_lon = obs["lat"], obs["lon"]

    if obs.get("photo_url"):
        st.image(obs["photo_url"], width=150, caption="Current photo")

    try:
        d = datetime.fromisoformat(obs["date"]).date()
    except:
        d = datetime.utcnow().date()
        
    with st.expander("Edit date"):
        obs_date = st.date_input("Date", value=d)
        
    options = {
        "🦇": "bat",
        "🪶": "bird",
        "🍃": "plant",
        "🐸": "amphibian",
        "≽༏≼": "odonata",
    }
    
    animal_type_obs = obs.get("animal_type", "bird")
    
    selected_emoji = st.radio(
        "group",
        list(options.keys()),
        index=list(options.values()).index(animal_type_obs),
        horizontal=True,
        label_visibility="collapsed",
    )
    
    animal_type = options[selected_emoji]
    
    # Determine lists
    if animal_type == "bat":
        species_list = BAT_SPECIES
        func_list = BAT_FUNCTIONS
    
    elif animal_type == "bird":
        species_list = BIRD_SPECIES
        func_list = BIRD_FUNCTIONS
    
    elif animal_type == "amphibian":
        species_list = DUTCH_AMPHIBIANS
        func_list = AMPHIBIE_FUNCTIONS
    
    elif animal_type == "odonata":
        species_list = ODONATA_SPECIES
        func_list = ODONATA_FUNCTIONS
    
    elif animal_type == "plant":
        species_list = PLANT_SPECIES
        func_list = PLANT_FUNCTIONS
    
    # Use values from obs only if they are valid in the current group
    species_value = obs.get("species")
    if species_value in species_list:
        species_index = species_list.index(species_value)
    else:
        species_index = 0
    
    species = st.selectbox(
        "Species",
        species_list,
        index=species_index,
    )
    
    function_value = obs.get("function")
    if function_value in func_list:
        function_index = func_list.index(function_value)
    else:
        function_index = 0
    
    function = st.selectbox(
        "Function",
        func_list,
        index=function_index,
    )
        
   
    aantal = st.number_input("amount", step=1, value=int(obs.get("aantal")))

    behavior = st.text_area("Comments", value=obs.get("behavior", ""))
    username = st.text_input("Observer", value=obs.get("username", ""))
    
    new_photo = st.file_uploader("Replace Photo", type=["jpg", "jpeg", "png"])

    # UPDATE
    if st.button("Update", width="stretch"):
        photo_url = obs.get("photo_url")

        # Delete old photo if new one is uploaded
        if new_photo:
            delete_photo_from_storage(photo_url)
            photo_url = upload_photo(new_photo)

        supabase.table(OBS_TABLE).update({
            "animal_type": animal_type,
            "species": species,
            "function": function,
            "behavior": behavior,
            "aantal": aantal,
            "username": username,
            "date": str(obs_date),
            "lat": float(new_lat),
            "lon": float(new_lon),
            "photo_url": photo_url,
        }).eq("id", obs["id"]).execute()

        st.success("Point edited!")
        time.sleep(1)

        load_observations(st.session_state.project)
        st.rerun()

    # DELETE
    if st.button("Delete", type="secondary", width="stretch"):
        delete_photo_from_storage(obs.get("photo_url"))
        supabase.table(OBS_TABLE).delete().eq("id", obs["id"]).execute()
        load_observations(st.session_state.project)
        st.rerun()


# ----------------- NEW OBSERVATION -----------------
@st.dialog("New Observation")
def new_observation_dialog(center):
    st.write("Use the map center as the observation position.")

    base_center = center
    zoom = 18

    m = folium.Map(location=base_center, zoom_start=zoom,zoom_control=False)
    LocateControl(auto_start=False).add_to(m)


    # Satellite (Esri)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=False
    ).add_to(m)


    crosshair_html = f"""
    <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 9999;
    ">
        <img src="{CROSS_IMAGE_PATH}"
             style="width:{WIDTH}px; opacity:{OPACITY};">
    </div>
    """
    m.get_root().html.add_child(folium.Element(crosshair_html))

    map_data = st_folium(m, width="100%", height=350)

    try:
        lat = map_data["center"]["lat"]
        lon = map_data["center"]["lng"]
    except Exception:
        lat, lon = base_center

    with st.expander("Choose date"):
         obs_date = st.date_input("Date", value=datetime.utcnow().date())
   
    options = {
        "🦇": "bat",
        "🪶": "bird",
        "🍃": "plant",
        "🐸": "amphibian",
        "≽༏≼": "odonata",
    }
    
    selected_emoji = st.radio(
        "group",
        list(options.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
    
    animal_type = options[selected_emoji]

    if animal_type == "bat":
        species = st.selectbox("Species", BAT_SPECIES)
        function = st.selectbox("Function", BAT_FUNCTIONS)
        
    elif animal_type == "bird":
        species = st.selectbox("Species", BIRD_SPECIES)
        if species == "..ander":
            species = st.text_input("Write a species")       
        function = st.selectbox("Function", BIRD_FUNCTIONS)
        
    elif animal_type == "amphibian":
        species = st.selectbox("Species", DUTCH_AMPHIBIANS)
        function = st.selectbox("Function", AMPHIBIE_FUNCTIONS)

    elif animal_type == "odonata":
        species = st.selectbox("Species", ODONATA_SPECIES)
        function = st.selectbox("Function", ODONATA_FUNCTIONS)
    
    else:
        species = st.selectbox("Species", PLANT_SPECIES)
        if species == "..ander":
            species = st.text_input("Write a species")
        function = st.selectbox("Function", PLANT_FUNCTIONS)        

    aantal = st.number_input("amount", step=1, value=1)
    behavior = st.text_area("Comments")
    username = st.session_state.user.email
    
    photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])

    if st.button("Save observation",width="stretch"):
        photo_url = upload_photo(photo)

        data = {
            "animal_type": animal_type,
            "species": species,
            "function": function,
            "aantal": aantal,
            "behavior": behavior,
            "username": username,
            "date": str(obs_date),
            "project": st.session_state.project,
            "lat": float(lat),
            "lon": float(lon),
            "photo_url": photo_url,
        }

        supabase.table(OBS_TABLE).insert(data).execute()

        st.session_state.map_center = [float(lat), float(lon)]
        st.session_state.map_input_center = [float(lat), float(lon)]

        st.success("Point saved!")
        time.sleep(1)

        load_observations(st.session_state.project)
        st.rerun()


# ----------------- NEW POLYGON -----------------
@st.dialog("New Polygon")
def new_polygon_dialog(center):    
    st.write("Draw a polygon on the map and save it.")
  
    base_center = center 
    zoom = 18

    m = folium.Map(
        location=base_center,
        zoom_start=zoom,
        zoom_control=False
    )

    LocateControl(auto_start=False).add_to(m)

    Fullscreen(
        position="topleft",
        title="Full Screen",
        title_cancel="Exit Full Screen",
        force_separate_button=True,
    ).add_to(m)

    # Satellite (Esri)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=False
    ).add_to(m)


    Draw(
        export=False,
        draw_options={
            "polyline": False,
            "rectangle": False,
            "circle": False,
            "circlemarker": False,
            "marker": False,
            "polygon": True,
        },
        edit_options={
            "edit": False,
            "remove": True,
        },
    ).add_to(m)

    map_data = st_folium(
        m,
        width="100%",
        height=350,
        returned_objects=["all_drawings"],
        key="new_polygon_map",
    )


    polygon_coords = None

    try:
        drawings = map_data.get("all_drawings", [])

        if drawings:
            polygon_coords = drawings[0]["geometry"]["coordinates"][0]

    except Exception:
        polygon_coords = None

    with st.expander("Choose date"):
        polygon_date = st.date_input(
            "Date",
            value=datetime.utcnow().date()
        )

    options = {
        "🦇": "bat",
        "🪶": "bird",
        "🍃": "plant",
        "🐸": "amphibian",
        "≽༏≼": "odonata",
    }
    
    selected_emoji = st.radio(
        "group",
        list(options.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
    
    animal_type = options[selected_emoji]

    if animal_type == "bat":
        species = st.selectbox("Species", BAT_SPECIES)
        function = st.selectbox("Function", BAT_FUNCTIONS_POLYGON)
        
    elif animal_type == "bird":
        species = st.selectbox("Species", BIRD_SPECIES)
        function = st.selectbox("Function", BIRD_FUNCTIONS_POLYGON)

    elif animal_type == "amphibian":
        species = st.selectbox("Species", DUTCH_AMPHIBIANS)
        function = st.selectbox("Function", AMPHIBIE_FUNCTIONS_POLYGON)

    elif animal_type == "odonata":
        species = st.selectbox("Species", ODONATA_SPECIES)
        function = st.selectbox("Function", ODONATA_FUNCTIONS_POLYGON)

    else:
        species = st.selectbox("Species", PLANT_SPECIES)
        if species == "..ander":
            species = st.text_input("Write a species")
        function = st.selectbox("Function", PLANT_FUNCTIONS_POLYGON)        
    

    aantal = st.number_input("amount", step=1, value=1)
    comments = st.text_area("Comments")
    username = st.session_state.user.email
    
    photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])

    

    if st.button("Save polygon", width="stretch"):

        if not polygon_coords:
            st.warning("Please draw a polygon first.")
            return

        photo_url = upload_photo(photo)
        
        data = {
            "project": st.session_state.project,
            "username": st.session_state.user.email,
            "date": str(polygon_date),
            "aantal": aantal,
            "group": animal_type,
            "species": species,
            "function": function,
            "comments": comments,
        
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_coords]
            },
        
            "photo_url": photo_url,
        }


        supabase.table("polygons_app").insert(data).execute()

        st.success("Polygon saved.")
        time.sleep(1)

        st.rerun()
        
#-----------------------------------------------------------
@st.dialog("Edit Polygon")
def edit_polygon_dialog(obs):

    st.write(
        "The red polygon is the current one. "
        "Draw a new polygon only if you want to replace it."
    )

    geometry = obs["geometry"]

    coords = geometry["coordinates"][0]

    lats = [p[1] for p in coords]
    lons = [p[0] for p in coords]

    center = [
        sum(lats) / len(lats),
        sum(lons) / len(lons)
    ]

    m = folium.Map(
        location=center,
        zoom_start=18,
        zoom_control=False
    )

    LocateControl(auto_start=False).add_to(m)
    Fullscreen(
        position="topleft",
        title="Full Screen",
        title_cancel="Exit Full Screen",
        force_separate_button=True,
    ).add_to(m)

    # Satellite (Esri)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=False
    ).add_to(m)


    # CURRENT POLYGON (RED)

    folium.GeoJson(
        {
            "type": "Feature",
            "geometry": geometry,
        },
        tooltip="Current polygon",
        style_function=lambda x: {
            "fillColor": "red",
            "color": "red",
            "weight": 3,
            "fillOpacity": 0.2,
        },
    ).add_to(m)

    Draw(
        export=False,
        draw_options={
            "polyline": False,
            "rectangle": False,
            "circle": False,
            "circlemarker": False,
            "marker": False,
            "polygon": True,
        },
        edit_options={
            "edit": False,
            "remove": True,
        },
    ).add_to(m)

    map_data = st_folium(
        m,
        width="100%",
        height=350,
        returned_objects=["all_drawings"],
        key=f"edit_polygon_{obs['properties']['id']}",
    )

    new_polygon_coords = None

    try:
        drawings = map_data.get("all_drawings", [])

        if drawings:
            new_polygon_coords = (
                drawings[0]["geometry"]["coordinates"][0]
            )

    except Exception:
        pass

    # DATE

    try:
        polygon_date = datetime.fromisoformat(
            obs['properties']["date"]
        ).date()
    except:
        polygon_date = datetime.utcnow().date()

    with st.expander("Choose date"):
        polygon_date = st.date_input(
            "Date",
            value=polygon_date
        )

    # GROUP


    options = {
        "🦇": "bat",
        "🪶": "bird",
        "🍃": "plant",
        "🐸": "amphibian",
        "≽༏≼": "odonata",
    }
    
    animal_type_obs = obs['properties']["group"]
    selected_emoji = st.radio(
        "group",
        list(options.keys()),
        index=list(options.values()).index(animal_type_obs),
        horizontal=True,
        label_visibility="collapsed",
    )
    
    animal_type = options[selected_emoji]
    
    # Determine lists
    if animal_type == "bat":
        species_list = BAT_SPECIES
        func_list = BAT_FUNCTIONS_POLYGON
    
    elif animal_type == "bird":
        species_list = BIRD_SPECIES
        func_list = BIRD_FUNCTIONS_POLYGON
    
    elif animal_type == "amphibian":
        species_list = DUTCH_AMPHIBIANS
        func_list = AMPHIBIE_FUNCTIONS_POLYGON
    
    elif animal_type == "odonata":
        species_list = ODONATA_SPECIES
        func_list = ODONATA_FUNCTIONS_POLYGON
    
    elif animal_type == "plant":
        species_list = PLANT_SPECIES
        func_list = PLANT_FUNCTIONS_POLYGON
    
    # Use values from obs only if they are valid in the current group
    species_value = obs.get("species")
    if species_value in species_list:
        species_index = species_list.index(species_value)
    else:
        species_index = 0
    
    species = st.selectbox(
        "Species",
        species_list,
        index=species_index,
    )
    
    function_value = obs.get("function")
    if function_value in func_list:
        function_index = func_list.index(function_value)
    else:
        function_index = 0
    
    function = st.selectbox(
        "Function",
        func_list,
        index=function_index,
    )




    aantal = st.number_input(
        "Amount",
        step=1,
        value=int(obs['properties']['aantal'])
    )

    comments = st.text_area(
        "Comments",
        value=obs.get("comments", "")
    )

    if obs.get("photo_url"):
        st.image(
            obs["photo_url"],
            width=150,
            caption="Current photo"
        )

    new_photo = st.file_uploader(
        "Replace Photo",
        type=["jpg", "jpeg", "png"]
    )

    # UPDATE

    if st.button("Update Polygon", width="stretch"):

        photo_url = obs.get("photo_url")

        if new_photo:
            delete_photo_from_storage(photo_url)
            photo_url = upload_photo(new_photo)

        geometry_to_save = geometry

        if new_polygon_coords:
            geometry_to_save = {
                "type": "Polygon",
                "coordinates": [new_polygon_coords]
            }


        supabase.table(OBS_POLYGONS).update({

            "group": animal_type,
            "species": species,
            "function": function,
            "aantal": aantal,
            "comments": comments,
            "date": str(polygon_date),
            "photo_url": photo_url,
            "geometry": geometry_to_save,

        }).eq(
            "id",
            obs['properties']["id"]
        ).execute()

        load_polygons(st.session_state.project)

        st.success("Polygon updated")
        time.sleep(1)

        st.rerun()

    # DELETE

    if st.button(
        "Delete Polygon",
        type="secondary",
        width="stretch"
    ):

        delete_photo_from_storage(
            obs.get("photo_url")
        )

        supabase.table(
            OBS_POLYGONS
        ).delete().eq(
            "id",
            obs['properties']["id"]
        ).execute()

        load_polygons(
            st.session_state.project
        )

        st.rerun()


# ----------------- PROJECT DESCRIPTION -------
# Dialog component
@st.dialog("Project Description")
def show_project_description(description: str | None):
    if description and description.strip():
        st.markdown(
            f"""
            <div style="
                padding: 1.5rem;
                border-radius: 12px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                line-height: 1.7;
                font-size: 1rem;
                color: black;
            ">
                {description}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="text-align: center; padding: 2rem;">
                <h4 style="color: #6c757d;">Geen beschrijving beschikbaar, neem contact op met uw teamleider.</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.image(
            "https://tse1.mm.bing.net/th/id/OIP.CLmh58rJ57FG_7zz9c7zvgHaHY?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            use_container_width=True,
        )


# ----------------- UI: LOGIN -----------------
def show_login():
    st.sidebar.title("Login")

    with st.sidebar.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            res = login(email, password)
            if res and res.user:
                st.session_state.logged_in = True
                st.session_state.user = res.user
                st.session_state.session = res.session
                st.rerun()
            else:
                st.sidebar.error("Invalid email or password")

    if st.sidebar.button("Create Account"):
        st.session_state.show_signup = True
        st.rerun()


# ----------------- UI: SIGNUP -----------------
def show_signup():
    st.sidebar.title("Create Account")

    with st.sidebar.form("signup_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign Up")

        if submitted:
            res = signup(email, password)
            if res and res.user:
                st.sidebar.success("Account created. Please log in.")
                st.session_state.show_signup = False
                st.rerun()
            else:
                st.sidebar.error("Sign-up failed")

    if st.sidebar.button("Back to Login",width="stretch"):
        st.session_state.show_signup = False
        st.rerun()


# ----------------- UI: PROJECT SELECT -----------------
def show_project_selection():
    st.sidebar.title("Select Project")

    # Fetch projects the user is a member of
    res = (
        supabase.table("project_members")
        .select("project")
        .eq("user_id", st.session_state.user.id)
        .execute()
    )

    rows = res.data or []

    if not rows:
        st.sidebar.warning("You are not a member of any project.")
        return

    # Extract project names
    project_names = [row["project"] for row in rows]

    selected = st.sidebar.selectbox("Project", project_names)

    if st.sidebar.button("Confirm project",width="stretch"):
        st.session_state.project = selected

        # Save project in user metadata
        supabase.auth.update_user({"data": {"project": selected}})

        load_observations(selected)
        st.session_state.changing_project = False
        st.rerun()




# ----------------- MAIN APP -----------------
def show_main_app():
    with st.bottom:
        # label = st.markdown("""<div style="background:#f3f4f6;border-left:4px solid #16a34a;padding:10px;border-radius:6px;font-weight:600;">New Observation</div>""", unsafe_allow_html=True)
        label = " "
        with st.expander(label,width="stretch",icon=":material/dehaze:"):
            col1, col2 = st.columns([0.5, 0.5])
            # col1 =  st.columns([1])



    # # Sidebar menu (no observations title, no new observation button)
    # st.sidebar.write(f"Logged in as: {st.session_state.user.email}")


    if st.sidebar.button("Change Project",width="stretch",icon=":material/sync_alt:"):
        st.session_state.changing_project = True
        st.rerun()

    if st.sidebar.button("Logout",width="stretch",icon=":material/login:"):
        logout()

    st.sidebar.divider()  

    show_google_maps_button()


    if st.sidebar.button("ℹ️ Info", help="View project description",width="stretch"):
        description = get_project_description()
        show_project_description(description)



    st.sidebar.divider()

    st.sidebar.header("Filters")

    obs = st.session_state.observations
    
    # ---------------------------------------------------------
    # 1) READ PREVIOUS SELECTIONS
    # ---------------------------------------------------------
    prev_species = st.session_state.get("filter_species", [])
    prev_functions = st.session_state.get("filter_functions", [])
    
    # ---------------------------------------------------------
    # 2) APPLY PREVIOUS FILTERS TO GET CURRENT SUBSET
    # ---------------------------------------------------------
    filtered_for_options = obs
    
    # Apply species filter
    if prev_species:
        filtered_for_options = [
            o for o in filtered_for_options
            if o.get("species") in prev_species
        ]
    
    # Apply function filter
    if prev_functions:
        filtered_for_options = [
            o for o in filtered_for_options
            if o.get("function") in prev_functions
        ]
    
    # ---------------------------------------------------------
    # 3) BUILD AVAILABLE OPTIONS FROM CURRENT SUBSET
    # ---------------------------------------------------------
    species_options = sorted({
        o.get("species") for o in filtered_for_options if o.get("species")
    })
    function_options = sorted({
        o.get("function") for o in filtered_for_options if o.get("function")
    })
    
    # Clean invalid previous selections
    prev_species = [s for s in prev_species if s in species_options]
    prev_functions = [f for f in prev_functions if f in function_options]
    
    # ---------------------------------------------------------
    # 4) RENDER WIDGETS (ONLY ONCE EACH)
    # ---------------------------------------------------------
    selected_species = st.sidebar.multiselect(
        "Species",
        species_options,
        default=prev_species,
        key="filter_species"
    )
    
    selected_functions = st.sidebar.multiselect(
        "Function",
        function_options,
        default=prev_functions,
        key="filter_functions"
    )
    
    # ---------------------------------------------------------
    # 5) APPLY FILTERS AGAIN TO GET FINAL RESULT
    # ---------------------------------------------------------
    filtered = obs
    
    if selected_species:
        filtered = [o for o in filtered if o.get("species") in selected_species]
    
    if selected_functions:
        filtered = [o for o in filtered if o.get("function") in selected_functions]
    
    # `filtered` now contains the final cascade result

        


    # MAP
    m = folium.Map(location=st.session_state.map_center, zoom_start=12, zoom_control=False,
    # tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    # attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
    )
    LocateControl(auto_start=False).add_to(m)

    Fullscreen(
        position="topleft",
        title="Full Screen",
        title_cancel="Exit Full Screen",
        force_separate_button=True,
    ).add_to(m)

    # Satellite (Esri)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=False
    ).add_to(m)


    # Load boundary
    boundary, bounds = load_project_boundary(st.session_state.project)
    
    if boundary:
        folium.GeoJson(
            boundary,
            name="Boundary",
            style_function=lambda x: {
                "fillColor": "#ffcc00",
                "color": "red",
                "weight": 2.5,
                "fillOpacity": 0.05,
            }
        ).add_to(m)
    
        if bounds:
            m.fit_bounds(bounds)


    # ============================================================
    # LOAD POLYGONS
    # ============================================================
    
    polygon_rows = (
        supabase
        .table(OBS_POLYGONS)
        .select("*")
        .eq("project", st.session_state.project)
        .execute()
    ).data or []
    
    
    # ============================================================
    # ADD POLYGONS TO MAP
    # ============================================================
    
    for row in polygon_rows:
    
        geometry = row["geometry"]
        species = row.get("species", "Unknown")
        date = row.get("date", )
        aantal = row.get("aantal",)
        fill_color = SPECIES_COLORS.get(species, "yellow")
        comments = row.get("comments",)
        group = row.get('group')
    
        function_type = row.get("function", "")
        id_type = row.get("id", "")


        if row.get("photo_url"):
            # Use real image
            image_block = f"""
                <a href="{row.get('photo_url')}" target="_blank">
                    <img src="{row.get('photo_url')}" 
                         style="width: 100%; max-height: 120px; object-fit: cover; border-radius: 6px;">
                </a>
            """
        else:
            # Choose emoji based on species type
            if "bat" in row.get('group', ''):
                emoji = "🦇"
            elif "bird" in row.get('group', ''):
                emoji = "🪶"  # default feather for birds or unknown
            elif "amphibian" in row.get('group', ''):
                emoji = "🐸"  # default feather for birds or unknown
            elif "odonata" in row.get('group', ''):
                emoji = "≽༏≼"  # default feather for birds or unknown
            else:
                emoji = "🍃"
        
            image_block = f"""
                <div style="
                    font-size: 20px;
                    text-align: center;
                    margin: 10px 0;
                ">{emoji}</div>
            """
        
        # Styled popup with colored border matching the marker color
        popup_html_polygon = f"""
        <div style="
            background-color: white;
            padding: 10px 14px;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
            font-family: 'Arial', sans-serif;
            width: 200px;
            border: 3px solid {fill_color};
        ">
        
            <!-- Species Title -->
            <div style="
                font-weight: 700;
                font-size: 15px;
                color: {fill_color};
                margin-bottom: 6px;
                text-align: center;
            ">
                {species}
            </div>
        
            <!-- Image or Emoji -->
            <div style="text-align:center; margin-bottom:8px;">
                {image_block}
            </div>
        
            <!-- Date (NO label) -->
            <div style="
                font-size: 13px;
                color: #444;
                margin-bottom: 4px;
                text-align: center;
            ">
                {date}
            </div>
        
            <!-- Function (italic, centered, capitalized) -->
            <div style="
                font-size: 12px;
                color: #555;
                margin-bottom: 4px;
                font-style: italic;
                text-align: center;
            ">
                ({aantal}) {function_type.capitalize()}
            </div>
        
            <!-- Comment (bold, justified) -->
            <div style="
                font-size: 12px;
                color: #333;
                font-weight: bold;
                text-align: justify;
            ">
                {comments}
            </div>
        
        </div>
        """
        
        popup = folium.Popup(
            folium.Html(popup_html_polygon, script=True),
            max_width=300,
        )




    
        pattern = None
        fill_opacity = 1
    
        if function_type == "foerageergebied":
    
            pattern = StripePattern(
                angle=45,
                weight=4,
                space_weight=4,
                color=fill_color,
                opacity=0.8,
            )
            pattern.add_to(m)
    
        elif function_type == "paarterritorium":
    
            pattern = CirclePattern(
                width=12,
                height=12,
                radius=2,
                fill_color=fill_color,
                color=fill_color,
                fill_opacity=0.8,
                
            )
            pattern.add_to(m)
    
        else:
            fill_opacity = 0.1
    
        feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "species": species,
                "function": function_type,
                "group": group,
                "date": date,
                "comments": comments,
                "aantal": aantal,
                "id": id_type,
            },
        }

        # species_short = SPECIES_SHORT[species]
        # function_short = FUNCTION_SHORT[function_type]
        
        # layer_name = f"{species_short}-{function_short} (ID:{id_type})"
        # fg = folium.FeatureGroup(name=layer_name)
        
        geojson = folium.GeoJson(
            feature,
            popup=popup,
            tooltip=None,
            style_function=lambda f,
            fill_color=fill_color,
            fill_opacity=fill_opacity: {
                "fillColor": fill_color,
                "fillOpacity": fill_opacity,
                "color": fill_color,
                "weight": 1.5,
            },
        ).add_to(m)

        # fg.add_to(m)
    
        if pattern:
            geojson.options["fillPattern"] = pattern


    for obs in filtered:
        animal_type = obs.get("animal_type", "bat")
        species = obs.get("species", "")
        color = SPECIES_COLORS.get(species, "blue")
        icon = FUNCTION_ICONS.get(obs.get("function", ""), "info-sign")


        # Create cluster group
        cluster = MarkerCluster().add_to(m)
        
        # Determine fallback emoji if no photo
        species_name = obs.get("species", "").lower()
        
        if obs.get("photo_url"):
            # Use real image
            image_block = f"""
                <a href="{obs.get('photo_url')}" target="_blank">
                    <img src="{obs.get('photo_url')}" 
                         style="width: 100%; max-height: 120px; object-fit: cover; border-radius: 6px;">
                </a>
            """
        else:
            # Choose emoji based on species type
            if "bat" in obs.get('animal_type', ''):
                emoji = "🦇"
            elif "bird" in obs.get('animal_type', ''):
                emoji = "🪶"  # default feather for birds or unknown
            elif "amphibian" in obs.get('animal_type', ''):
                emoji = "🐸"  # default feather for birds or unknown
            elif "odonata" in obs.get('animal_type', ''):
                emoji = "≽༏≼"  # default feather for birds or unknown
            else:
                emoji = "🍃"
        
            image_block = f"""
                <div style="
                    font-size: 20px;
                    text-align: center;
                    margin: 10px 0;
                ">{emoji}</div>
            """
        
        # Styled popup with colored border matching the marker color
        popup_html = f"""
        <div style="
            background-color: white;
            padding: 10px 14px;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
            font-family: 'Arial', sans-serif;
            width: 200px;
            border: 3px solid {color};
        ">
        
            <!-- Species Title -->
            <div style="
                font-weight: 700;
                font-size: 15px;
                color: {color};
                margin-bottom: 6px;
                text-align: center;
            ">
                {obs.get('species', '')}
            </div>
        
            <!-- Image or Emoji -->
            <div style="text-align:center; margin-bottom:8px;">
                {image_block}
            </div>
        
            <!-- Date (NO label) -->
            <div style="
                font-size: 13px;
                color: #444;
                margin-bottom: 4px;
                text-align: center;
            ">
                {obs.get('date', '')}
            </div>
        
            <!-- Function (italic, centered, capitalized) -->
            <div style="
                font-size: 12px;
                color: #555;
                margin-bottom: 4px;
                font-style: italic;
                text-align: center;
            ">
                ({obs.get('aantal', '')}) {obs.get('function', '').capitalize()}
            </div>
        
            <!-- Comment (bold, justified) -->
            <div style="
                font-size: 12px;
                color: #333;
                font-weight: bold;
                text-align: justify;
            ">
                {obs.get('behavior', '')}
            </div>
        
        </div>
        """



    
        # Tooltip contains ONLY the ID (for selection)
        tooltip_text = obs["id"]

        # if color in ["darkred","darkblue","darkgreen","black","purple"]:
        #     text_color="white"
        # else:
        #     text_color="black"

        
        # BeautifyIcon marker
        marker_icon = BeautifyIcon(
            icon=icon,
            icon_shape="marker",
            background_color="white",
            border_color=color,
            icon_anchor=[marker_size/2, marker_size],
            border_width=3,
            text_color="black",
            icon_size=[marker_size, marker_size],                 # marker size
            inner_icon_style=f"font-size:{inner_icon_px}px; display:flex; align-items:center; justify-content:center; width:100%; height:100%; text-align:center; padding:0; margin:0" # icon size
        )
        
    
        # Add marker to cluster (NOT to map)
        folium.Marker(
            location=[obs["lat"], obs["lon"]],
            popup=popup_html,
            tooltip=tooltip_text,
            # tooltip=None,
            icon=marker_icon,
        ).add_to(cluster)





    with st.container():
        st.markdown('<div class="fixed-map">', unsafe_allow_html=True)
        map_data = st_folium(m, height=map_height, width="100%")
        st.markdown('</div>', unsafe_allow_html=True)


    st.session_state.map_input_center = _get_center_from_map_data(map_data, st.session_state.map_center)
    
    with col1:
        with st.expander(":green[**New observation**]"):
        # st.markdown(":green[**New observation**]",text_alignment='center')
            if st.button("New Point",key="New Observation",width="stretch",icon=":material/add_location_alt:"):
                new_observation_dialog(st.session_state.map_input_center)
            if st.button("New Polygon", key="New Polygon",width="stretch",icon=":material/screenshot_region:"):
                new_polygon_dialog(st.session_state.map_input_center)

        with st.expander(":red[**Edit/Delete observation**]"):
        # st.markdown(":red[**Edit/Delete observation**]",text_alignment='center')
    
            # Use last_object_clicked_popup from st_folium
            if map_data and map_data.get("last_active_drawing"):
                try:
                    if map_data["last_active_drawing"]["geometry"]["type"] == "Polygon":
                        obs_id = f"{map_data["last_active_drawing"]["properties"]["id"]}"
                        label = f"({obs_id}) {map_data["last_active_drawing"]["properties"]["species"]} - {map_data["last_active_drawing"]["properties"]["function"]}"
                        if st.button(label, key=f"obs_{obs_id}", use_container_width=True,icon=":material/screenshot_region:"):
                            edit_polygon_dialog(map_data["last_active_drawing"])
                            st.stop()
            
                    elif map_data["last_active_drawing"]["geometry"]["type"] == "Point":
            
                        if map_data and map_data.get("last_object_clicked_popup"):
                            obs_id = map_data.get("last_object_clicked_tooltip")
                            if obs_id:
                                st.session_state.selected_obs_id = obs_id      
            
                
                        # # OBSERVATION LIST IN SIDEBAR (no title, no new button)
                        selected_id = st.session_state.selected_obs_id
                        
                        # Find the matching observation
                        selected_obs = None
                        for obs in filtered:
                            if str(obs["id"]) == selected_id:
                                selected_obs = obs
                                break
                            
                        if selected_obs:
                            obs_id = str(selected_obs["id"])
                            base_label = f"({obs_id}) {selected_obs.get('species','')} – {selected_obs.get('function','')}"
                            label = f"{base_label}"
                        
                            # EDIT BUTTON
                            if st.button(label, key=f"obs_{obs_id}", use_container_width=True,icon=":material/add_location_alt:"):
                                edit_observation_dialog(selected_obs)
        
        
        
                except:
                    st.warning("Select a Point or a Polygon")
                    pass
            else:
                st.warning("Select a Point or a Polygon")
                
        with st.expander(":blue[**Daily Report**]"):
        # st.markdown(":blue[**Daily Report**]",text_alignment='center')
        
            if st.button("Fill a Report",width="stretch",icon=":material/edit_note:"):
                daily_report_dialog()
            
            if st.button("View Reports",width="stretch",icon=":material/menu_book:"):
                show_reports_dialog()







# ----------------- RESTORE SESSION -----------------
def restore_session_after_functions():
    sess = supabase.auth.get_session()
    if sess and sess.user:
        st.session_state.logged_in = True
        st.session_state.user = sess.user
        st.session_state.session = sess

        metadata = sess.user.user_metadata or {}
        saved_project = metadata.get("project")

        if saved_project:
            st.session_state.project = saved_project
            load_observations(saved_project)


restore_session_after_functions()


# ----------------- MAIN -----------------
def main():
    if not st.session_state.logged_in:
        if st.session_state.show_signup:
            show_signup()
        else:
            show_login()
    elif st.session_state.changing_project:
        show_project_selection()
        st.sidebar.divider()
        if st.sidebar.button("Logout",width="stretch",icon=":material/login:"):
            logout()
    elif not st.session_state.project:
        show_project_selection()
        st.sidebar.divider()
        if st.sidebar.button("Logout",width="stretch",icon=":material/login:"):
            logout()
    else:
        st.logo(IMAGE,  link=None, size="large", icon_image=IMAGE)
        show_main_app()


if __name__ == "__main__":
    main()

