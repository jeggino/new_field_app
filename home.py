import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import LocateControl, BeautifyIcon, MarkerCluster
from supabase import create_client, Client
from datetime import datetime, time
import uuid
import json
import pandas as pd
import re


# st.image(
#     "https://image.shutterstock.com/image-illustration/work-progress-red-sign-isolated-260nw-87217798.jpg", width = "stretch"
# )

# st.stop()


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
BUCKET = "observation_photos"

CROSS_IMAGE_PATH = "https://static.vecteezy.com/system/resources/previews/031/742/868/non_2x/transparent-circle-cross-icon-free-png.png"
OPACITY = 1
WIDTH = 30

# ----------------- LOGO --------------------------
IMAGE = "https://www.nachtvandevleermuis.nl/wp-content/uploads/Elsken_Ecologie_LOGO-min-1024x748.png"

# ................. ICON CUSTUMIZE ----------------
marker_size = 22
inner_icon_px = 12

# ----------------- REPORT KINDS ------------------
REPORT_KINDS = [
    'Kraamverblijf Avond (1/2)','Kraamverblijf Avond (2/2)','Kraamverblijf Ochtend (1/3)', 'Kraamverblijf Ochtend (2/3)', 'Kraamverblijf Ochtend (3/3)',
    'Winterverblijf','Paarverblijf (1/2)',
    'Paarverblijf (2/2)', 'Huismus (1/3)','Huismus (2/3)', 'Huismus (3/3)','Gierzwaluw (1/3)','Gierzwaluw (2/3)','Gierzwaluw (3/3)','Steenuil (1/3)','Steenuil (2/3)', 'Steenuil (3/3)',
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
    "vleermuis waarneming": "walkie-talkie",
    "zomerverblijfplaats": "sun",
    "kraamverblijfplaats": "venus",
    "paarverblijfplaats": "heart",
    "winterverblijfplaats": "snowflake",
    "vleermuiskast": "box-archive",
    "zender": "tower-broadcast",

    "vogel waarneming": "binoculars",
    "nestlocatie": "egg",
    "mogelijke nestlocatie": "question",
}

# ----------------- COLORS FOR SPECIES -----------------
ALL_SPECIES = BAT_SPECIES + BIRD_SPECIES
COLOR_PALETTE = [
    "red","green","blue","purple","orange","darkred","lightred","beige","darkblue",
    "darkgreen","cadetblue","cadetblue","white","pink","lightblue","lightgreen",
    "gray","black","red"
]
SPECIES_COLORS = {sp: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, sp in enumerate(ALL_SPECIES)}

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

    # If already a time object
    if isinstance(value, time):
        return value

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

    start_time = st.time_input("Start Time")
    end_time = st.time_input("End Time")
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
            st.rerun()

        # Delete
        if st.button("Delete Report", type="secondary", use_container_width=True):
            supabase.table("report").delete().eq("id", report["id"]).execute()
            st.success("Report deleted.")
            st.rerun()



@st.dialog("Edit Observation")
def edit_observation_dialog(obs):
    st.write("Move the map to adjust the coordinates")
    
    edit_center = [obs["lat"], obs["lon"]]
    m = folium.Map(location=edit_center, zoom_start=18, zoom_control=False)
    LocateControl(auto_start=False).add_to(m)

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
        
    animal_type = obs.get("animal_type", "bat")
    animal_type = st.radio("Animal type", ["bat", "bird"], index=0 if animal_type == "bat" else 1)

    if animal_type == "bat":
        species_list = BAT_SPECIES
        func_list = BAT_FUNCTIONS
    else:
        species_list = BIRD_SPECIES
        func_list = BIRD_FUNCTIONS

    species_value = obs.get("species", species_list[0])
    if species_value not in species_list:
        species_value = species_list[0]

    function_value = obs.get("function", func_list[0])
    if function_value not in func_list:
        function_value = func_list[0]

    species = st.selectbox("Species", species_list, index=species_list.index(species_value))
    function = st.selectbox("Function", func_list, index=func_list.index(function_value))

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
            "username": username,
            "date": str(obs_date),
            "lat": float(new_lat),
            "lon": float(new_lon),
            "photo_url": photo_url,
        }).eq("id", obs["id"]).execute()

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
def new_observation_dialog():
    st.write("Use the map center as the observation position.")

    base_center = st.session_state.map_input_center
    zoom = 20

    m = folium.Map(location=base_center, zoom_start=zoom,zoom_control=False)
    LocateControl(auto_start=False).add_to(m)

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
   
    animal_type = st.radio("Is it a bat or a bird?", ["bat", "bird"])

    if animal_type == "bat":
        species = st.selectbox("Species", BAT_SPECIES)
        function = st.selectbox("Function", BAT_FUNCTIONS)
        
    else:
        species = st.selectbox("Species", BIRD_SPECIES)
        function = st.selectbox("Function", BIRD_FUNCTIONS)

    behavior = st.text_area("Comments")
    username = st.session_state.user.email
    
    photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])

    if st.button("Save observation",width="stretch"):
        photo_url = upload_photo(photo)

        data = {
            "animal_type": animal_type,
            "species": species,
            "function": function,
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

        load_observations(st.session_state.project)
        st.rerun()


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
    # NO title on main page, only New Observation button (mobile-friendly)
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.write("")  # empty, no title
    with col2:
        if st.button("New Observation",width="stretch",icon=":material/add_location_alt:"):
            new_observation_dialog()

    # # Sidebar menu (no observations title, no new observation button)
    # st.sidebar.write(f"Logged in as: {st.session_state.user.email}")


    if st.sidebar.button("Change Project",width="stretch",icon=":material/sync_alt:"):
        st.session_state.changing_project = True
        st.rerun()

    if st.sidebar.button("Logout",width="stretch",icon=":material/login:"):
        logout()

    st.sidebar.divider()

    # if st.sidebar.button("Legend",width="stretch"):
    #     show_legend()
    

    st.sidebar.header("Filters")

    species_values = sorted({o.get("species", "") for o in st.session_state.observations if o.get("species")})
    selected_species = st.sidebar.multiselect("Species", species_values)

    # DATE FILTER
    dates = []
    for o in st.session_state.observations:
        if o.get("date"):
            try:
                dates.append(datetime.fromisoformat(o["date"]).date())
            except:
                pass

    if dates:
        min_d, max_d = min(dates), max(dates)
        if min_d == max_d:
            date_range = (min_d, max_d)
        else:
            date_range = st.sidebar.slider(
                "Date range",
                min_value=min_d,
                max_value=max_d,
                value=(min_d, max_d),
            )
    else:
        date_range = None

    filtered = st.session_state.observations

    if selected_species:
        filtered = [o for o in filtered if o.get("species") in selected_species]

    if date_range:
        start_d, end_d = date_range
        tmp = []
        for o in filtered:
            if o.get("date"):
                try:
                    d = datetime.fromisoformat(o["date"]).date()
                    if start_d <= d <= end_d:
                        tmp.append(o)
                except:
                    pass
        filtered = tmp

    st.sidebar.divider()
    
    st.sidebar.header("Daily Report")
    
    if st.sidebar.button("Fill a Report",width="stretch",icon=":material/edit_note:"):
        daily_report_dialog()
    
    if st.sidebar.button("View Reports",width="stretch",icon=":material/menu_book:"):
        show_reports_dialog()


    # MAP
    m = folium.Map(location=st.session_state.map_center, zoom_start=12, zoom_control=False)
    LocateControl(auto_start=False).add_to(m)

    # # Satellite (Esri)
    # folium.TileLayer(
    #     tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    #     attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
    #     name="Satellite",
    #     overlay=False,
    #     control=True
    # ).add_to(m)

    # folium.LayerControl(position="topright").add_to(m)


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
                "fillOpacity": 0.1,
            }
        ).add_to(m)
    
        if bounds:
            m.fit_bounds(bounds)


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
            else:
                emoji = "🪶"  # default feather for birds or unknown
        
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
                {obs.get('function', '').capitalize()}
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

        if color in ["darkred","darkblue","darkgreen","black","blue","purple"]:
            text_color="lightgrey"
        else:
            text_color="black"

        
        # BeautifyIcon marker
        marker_icon = BeautifyIcon(
            icon=icon,
            icon_shape="marker",
            background_color=color,
            border_color="black",
            icon_anchor=[marker_size/2, marker_size],
            border_width=0.7,
            text_color=text_color,
            icon_size=[marker_size, marker_size],                 # marker size
            inner_icon_style=f"font-size:{inner_icon_px}px; display:flex; align-items:center; justify-content:center; width:100%; height:100%; text-align:center; padding:0; margin:0" # icon size
        )

    
        # Add marker to cluster (NOT to map)
        folium.Marker(
            location=[obs["lat"], obs["lon"]],
            popup=popup_html,
            tooltip=tooltip_text,
            icon=marker_icon
        ).add_to(cluster)




    with st.container():
        st.markdown('<div class="fixed-map">', unsafe_allow_html=True)
        map_data = st_folium(m, height=450, width="100%")
        st.markdown('</div>', unsafe_allow_html=True)


    # map_data = st_folium(m, height=550, width="100%")

    st.session_state.map_input_center = _get_center_from_map_data(map_data, st.session_state.map_center)

    # Use last_object_clicked_popup from st_folium
    if map_data and map_data.get("last_object_clicked_popup"):
        obs_id = map_data.get("last_object_clicked_tooltip")
        if obs_id:
            st.session_state.selected_obs_id = obs_id



    st.sidebar.divider()
    
    st.sidebar.header("Observations")

    
    # OBSERVATION LIST IN SIDEBAR (no title, no new button)
    for obs in filtered:
        obs_id = str(obs["id"])
        base_label = f"{obs.get('species','')} – {obs.get('function','')}"
        if st.session_state.selected_obs_id == obs_id:
            label = f"🔴 {base_label}"
        else:
            label = base_label

        if st.sidebar.button(label, key=f"obs_{obs_id}",width="stretch"):
            edit_observation_dialog(obs)


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




















    



    



















    

