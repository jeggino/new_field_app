import streamlit as st
from streamlit_folium import st_folium
import folium
from supabase import create_client, Client
from datetime import datetime, date
import uuid

# ----------------- CONFIG -----------------
st.set_page_config(page_title="Observations Map", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

PROJECTS_TABLE = "projects"
OBS_TABLE = "observations"
BUCKET = "observation_photos"

CROSS_IMAGE_PATH = "https://static.vecteezy.com/system/resources/previews/031/742/868/non_2x/transparent-circle-cross-icon-free-png.png"
OPACITY = 1
WIDTH = 30


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
    "map_center": [0.0, 0.0],
    "map_input_center": [0.0, 0.0],
    "map_input_zoom": 2,
    "show_signup": False,
    "filter_species": [],
    "filter_date_range": None,
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
    res = supabase.table(PROJECTS_TABLE).select("*").execute()
    return res.data or []


def load_observations(project_name: str):
    res = supabase.table(OBS_TABLE).select("*").eq("project", project_name).execute()
    st.session_state.observations = res.data or []


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
        supabase.storage.from_(BUCKET).upload(file_id, file_bytes)
        return supabase.storage.from_(BUCKET).get_public_url(file_id)
    except Exception:
        # If upload fails, just skip photo instead of crashing
        return None


# ----------------- UI: LOGIN -----------------
def show_login():
    st.title("Login")

    with st.form("login_form"):
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
                st.error("Invalid email or password")

    st.info("Don't have an account?")
    if st.button("Go to Sign Up"):
        st.session_state.show_signup = True
        st.rerun()


# ----------------- UI: SIGNUP -----------------
def show_signup():
    st.title("Create Account")

    with st.form("signup_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign Up")

        if submitted:
            res = signup(email, password)
            if res and res.user:
                st.success("Account created. Please log in.")
                st.session_state.show_signup = False
                st.rerun()
            else:
                st.error("Sign-up failed")

    if st.button("Back to Login"):
        st.session_state.show_signup = False
        st.rerun()


# ----------------- UI: PROJECT SELECT -----------------
def show_project_selection():
    st.title("Select Project")

    projects = load_projects()
    if not projects:
        st.warning("No projects found.")
        return

    project_names = [p["name"] for p in projects]
    selected = st.selectbox("Project", project_names)

    if st.button("Confirm project"):
        st.session_state.project = selected
        supabase.auth.update_user({"data": {"project": selected}})
        load_observations(selected)
        st.session_state.changing_project = False
        st.rerun()


# ----------------- MAP HELPERS -----------------
def _get_center_from_map_data(map_data, fallback_center):
    if not map_data:
        return fallback_center
    bounds = map_data.get("bounds")
    if not bounds:
        return fallback_center
    sw = bounds.get("_southWest")
    ne = bounds.get("_northEast")
    if not sw or not ne:
        return fallback_center
    return [(sw["lat"] + ne["lat"]) / 2, (sw["lng"] + ne["lng"]) / 2]


# ----------------- DIALOG: NEW OBSERVATION -----------------
@st.dialog("New Observation")
def new_observation_dialog():
    st.write("Use the map center as the observation position.")

    base_center = st.session_state.map_input_center
    zoom = st.session_state.map_input_zoom

    m = folium.Map(location=base_center, zoom_start=zoom)

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

    map_data = st_folium(m, width="100%", height=400)

    try:
        lat = map_data["center"]["lat"]
        lon = map_data["center"]["lng"]
    except Exception:
        lat, lon = base_center

    col1, col2 = st.columns(2)

    with col1:
        species = st.text_input("Species")
        behavior = st.text_input("Behavior")
        username = st.text_input("Observer", value=st.session_state.user.email)

    with col2:
        obs_date = st.date_input("Date", value=datetime.utcnow().date())
        photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])

    if st.button("Save observation"):
        if not species:
            st.warning("Species is required.")
            st.stop()

        photo_url = upload_photo(photo)

        data = {
            "species": species,
            "behavior": behavior,
            "username": username,
            "date": str(obs_date),
            "project": st.session_state.project,
            "lat": float(lat),
            "lon": float(lon),
            "photo_url": photo_url,
        }

        supabase.table(OBS_TABLE).insert(data).execute()
        load_observations(st.session_state.project)
        st.rerun()


# ----------------- DIALOG: EDIT OBSERVATION -----------------
@st.dialog("Edit Observation")
def edit_observation_dialog(obs):
    st.write("Edit the observation.")

    col1, col2 = st.columns(2)

    with col1:
        species = st.text_input("Species", value=obs.get("species", ""))
        behavior = st.text_input("Behavior", value=obs.get("behavior", ""))
        username = st.text_input("Observer", value=obs.get("username", ""))

    with col2:
        try:
            d = datetime.fromisoformat(obs["date"]).date()
        except Exception:
            d = datetime.utcnow().date()
        obs_date = st.date_input("Date", value=d)
        new_photo = st.file_uploader("Replace Photo", type=["jpg", "jpeg", "png"])

    lat = st.number_input("Latitude", value=obs["lat"])
    lon = st.number_input("Longitude", value=obs["lon"])

    if st.button("Update"):
        photo_url = obs.get("photo_url")
        if new_photo:
            photo_url = upload_photo(new_photo)

        supabase.table(OBS_TABLE).update({
            "species": species,
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


# ----------------- RESTORE SESSION (AFTER FUNCTIONS) -----------------
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


# ----------------- MAIN APP -----------------
def show_main_app():
    st.title(f"Observations for project: {st.session_state.project}")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.write(f"Logged in as: {st.session_state.user.email}")
    with col2:
        if st.button("Change Project"):
            st.session_state.changing_project = True
            st.rerun()
    with col3:
        if st.button("Logout"):
            logout()

    # -------- FILTERS --------
    st.sidebar.header("Filters")

    species_values = sorted({o.get("species", "") for o in st.session_state.observations if o.get("species")})
    st.session_state.filter_species = st.sidebar.multiselect("Filter by species", species_values)

    dates = []
    for o in st.session_state.observations:
        if o.get("date"):
            try:
                dates.append(datetime.fromisoformat(o["date"]).date())
            except Exception:
                pass

    if dates:
        min_d, max_d = min(dates), max(dates)
        if st.session_state.filter_date_range is None:
            st.session_state.filter_date_range = (min_d, max_d)
        st.session_state.filter_date_range = st.sidebar.slider(
            "Filter by date range",
            min_value=min_d,
            max_value=max_d,
            value=st.session_state.filter_date_range,
        )
    else:
        st.session_state.filter_date_range = None

    filtered = st.session_state.observations

    if st.session_state.filter_species:
        filtered = [o for o in filtered if o.get("species") in st.session_state.filter_species]

    if st.session_state.filter_date_range:
        start_d, end_d = st.session_state.filter_date_range
        tmp = []
        for o in filtered:
            if o.get("date"):
                try:
                    d = datetime.fromisoformat(o["date"]).date()
                    if start_d <= d <= end_d:
                        tmp.append(o)
                except Exception:
                    pass
        filtered = tmp

    # -------- MAP --------
    m = folium.Map(location=st.session_state.map_center, zoom_start=4)

    # Observations as blue markers
    for obs in filtered:
        popup = f"""
        <b>Species:</b> {obs.get('species', '')}<br>
        <b>Observer:</b> {obs.get('username', '')}<br>
        <b>Date:</b> {obs.get('date', '')}<br>
        """
        if obs.get("photo_url"):
            popup += f'<img src="{obs["photo_url"]}" width="150"><br>'

        folium.Marker(
            [obs["lat"], obs["lon"]],
            popup=popup,
            icon=folium.Icon(color="blue"),
        ).add_to(m)

    map_data = st_folium(m, height=500, width=900)

    st.session_state.map_input_center = _get_center_from_map_data(map_data, st.session_state.map_center)
    if map_data and "zoom" in map_data:
        st.session_state.map_input_zoom = map_data["zoom"]

    # "GPS" blue marker at last clicked location if available
    if map_data and map_data.get("last_clicked"):
        lc = map_data["last_clicked"]
        folium.Marker(
            [lc["lat"], lc["lng"]],
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(m)

    # Re-render map with GPS marker (optional second render)
    # (If you prefer single render, remove this block and the above GPS marker)
    # st_folium(m, height=500, width=900)

    # -------- SIDEBAR LIST --------
    st.sidebar.header("Observations")
    if st.sidebar.button("New observation"):
        new_observation_dialog()

    for obs in filtered:
        label = f"{obs['id']} - {obs.get('species', '')[:30]}"
        if st.sidebar.button(label):
            edit_observation_dialog(obs)


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






    

