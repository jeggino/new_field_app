import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import LocateControl, BeautifyIcon
from supabase import create_client, Client
from datetime import datetime
import uuid
import json





# ----------------- CONFIG -----------------
st.set_page_config(
    page_title="",
    layout="wide",
    initial_sidebar_state="expanded"
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
@st.dialog("Daily Report")
def daily_report_dialog():
    st.write("Fill in the daily report.")

    kind = st.selectbox("Kind", ["survey", "maintenance", "inspection", "other"])
    date = st.date_input("Date", value=datetime.utcnow().date())
    operator = st.text_input("Operator", value=st.session_state.user.email)
    extra_operator = st.text_input("Extra Operator")
    temperature = st.number_input("Temperature (°C)", step=0.1)
    wind = st.text_input("Wind")
    rain = st.text_input("Rain")
    comment = st.text_area("Comment")

    if st.button("Submit Report"):
        supabase.table("report").insert({
            "kind": kind,
            "date": str(date),
            "operator": operator,
            "extra_operator": extra_operator,
            "temperature": temperature,
            "wind": wind,
            "rain": rain,
            "comment": comment,
            "project": st.session_state.project
        }).execute()

        st.success("Report submitted.")
        st.rerun()


@st.dialog("Edit Observation")
def edit_observation_dialog(obs):
    st.write("Edit the observation.")

    if obs.get("photo_url"):
        st.image(obs["photo_url"], width=250, caption="Current photo")

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

    behavior = st.text_input("Behavior", value=obs.get("behavior", ""))
    username = st.text_input("Observer", value=obs.get("username", ""))

    try:
        d = datetime.fromisoformat(obs["date"]).date()
    except:
        d = datetime.utcnow().date()

    obs_date = st.date_input("Date", value=d)
    new_photo = st.file_uploader("Replace Photo", type=["jpg", "jpeg", "png"])

    lat = st.number_input("Latitude", value=float(obs["lat"]))
    lon = st.number_input("Longitude", value=float(obs["lon"]))

    if st.button("Update"):
        photo_url = obs.get("photo_url")
        if new_photo:
            photo_url = upload_photo(new_photo)

        supabase.table(OBS_TABLE).update({
            "animal_type": animal_type,
            "species": species,
            "function": function,
            "behavior": behavior,
            "username": username,
            "date": str(obs_date),
            "lat": lat,
            "lon": lon,
            "photo_url": photo_url,
        }).eq("id", obs["id"]).execute()

        load_observations(st.session_state.project)
        st.rerun()

    if st.button("Delete", type="secondary"):
        supabase.table(OBS_TABLE).delete().eq("id", obs["id"]).execute()
        load_observations(st.session_state.project)
        st.rerun()


# ----------------- NEW OBSERVATION -----------------
@st.dialog("New Observation")
def new_observation_dialog():
    st.write("Use the map center as the observation position.")

    base_center = st.session_state.map_input_center
    zoom = 18

    m = folium.Map(location=base_center, zoom_start=zoom)
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

    animal_type = st.radio("Is it a bat or a bird?", ["bat", "bird"])

    if animal_type == "bat":
        species = st.selectbox("Species", BAT_SPECIES)
        function = st.selectbox("Function", BAT_FUNCTIONS)
    else:
        species = st.selectbox("Species", BIRD_SPECIES)
        function = st.selectbox("Function", BIRD_FUNCTIONS)

    behavior = st.text_input("Behavior")
    username = st.text_input("Observer", value=st.session_state.user.email)
    obs_date = st.date_input("Date", value=datetime.utcnow().date())
    photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])

    if st.button("Save observation"):
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

    if st.sidebar.button("Back to Login"):
        st.session_state.show_signup = False
        st.rerun()


# ----------------- UI: PROJECT SELECT -----------------
def show_project_selection():
    st.sidebar.title("Select Project")

    projects = load_projects()
    if not projects:
        st.sidebar.warning("No projects found for this user.")
        return

    project_names = [p["name"] for p in projects]
    selected = st.sidebar.selectbox("Project", project_names)

    if st.sidebar.button("Confirm project"):
        st.session_state.project = selected
        supabase.auth.update_user({"data": {"project": selected}})
        load_observations(selected)
        st.session_state.changing_project = False
        st.rerun()

# ----------------- SHOW REPORT --------------
def show_reports_page():
    st.subheader("Daily Reports")

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

    st.dataframe(reports)

    # CSV download
    import pandas as pd
    df = pd.DataFrame(reports)

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"{st.session_state.project}_reports.csv",
        mime="text/csv"
    )

# ----------------- MAIN APP -----------------
def show_main_app():
    # NO title on main page, only New Observation button (mobile-friendly)
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.write("")  # empty, no title
    with col2:
        if st.button("➕ New Observation"):
            new_observation_dialog()

    # # Sidebar menu (no observations title, no new observation button)
    # st.sidebar.write(f"Logged in as: {st.session_state.user.email}")


    if st.sidebar.button("Change Project"):
        st.session_state.changing_project = True
        st.rerun()

    if st.sidebar.button("Logout"):
        logout()

    st.sidebar.divider()

    if st.sidebar.button("Legend"):
        show_legend()
    

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
    
    if st.sidebar.button("Fill a Report"):
        daily_report_dialog()
    
    if st.sidebar.button("View Reports"):
        show_reports_page()


    # MAP
    m = folium.Map(location=st.session_state.map_center, zoom_start=12)
    LocateControl(auto_start=False).add_to(m)


    # Load boundary
    boundary, bounds = load_project_boundary(st.session_state.project)
    
    if boundary:
        folium.GeoJson(
            boundary,
            name="Boundary",
            style_function=lambda x: {
                "fillColor": "#ffcc00",
                "color": "#ff8800",
                "weight": 2,
                "fillOpacity": 0.15,
            }
        ).add_to(m)
    
        if bounds:
            m.fit_bounds(bounds)


    for obs in filtered:
        animal_type = obs.get("animal_type", "bat")
        species = obs.get("species", "")
        color = SPECIES_COLORS.get(species, "blue")
        icon = FUNCTION_ICONS.get(obs.get("function", ""), "info-sign")
        # shape = "circle" if animal_type == "bat" else "rectangle"
        shape = "marker"

        marker_icon = BeautifyIcon(
            icon=icon,
            icon_shape=shape,
            background_color=color,
            border_color="black" if (animal_type == "bat" and BAT_BORDER) else color,
            text_color="white"
        )

        folium.Marker(
            [obs["lat"], obs["lon"]],
            popup=str(obs["id"]),
            icon=marker_icon,
        ).add_to(m)

    with st.container():
        st.markdown('<div class="fixed-map">', unsafe_allow_html=True)
        map_data = st_folium(m, height=450, width="100%")
        st.markdown('</div>', unsafe_allow_html=True)


    # map_data = st_folium(m, height=550, width="100%")

    st.session_state.map_input_center = _get_center_from_map_data(map_data, st.session_state.map_center)

    # Use last_object_clicked_popup from st_folium
    if map_data and map_data.get("last_object_clicked_popup"):
        st.session_state.selected_obs_id = str(map_data["last_object_clicked_popup"])

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

        if st.sidebar.button(label, key=f"obs_{obs_id}"):
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
    elif not st.session_state.project:
        show_project_selection()
    else:
        show_main_app()


if __name__ == "__main__":
    main()




















    



    



















    

