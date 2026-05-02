import streamlit as st
from streamlit_folium import st_folium
import folium
from supabase import create_client, Client
from datetime import datetime

# ----------------- CONFIG -----------------
st.set_page_config(page_title="Observations Map", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

PROJECTS_TABLE = "projects"
OBS_TABLE = "observations"
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
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ----------------- RESTORE AUTH SESSION -----------------
def restore_session():
    sess = supabase.auth.get_session()
    if sess and sess.user:
        st.session_state.logged_in = True
        st.session_state.user = sess.user
        st.session_state.session = sess

        # Restore project from user metadata
        metadata = sess.user.user_metadata or {}
        saved_project = metadata.get("project")

        if saved_project and not st.session_state.project:
            st.session_state.project = saved_project
            load_observations(saved_project)

restore_session()


# ----------------- AUTH -----------------
def login(email: str, password: str):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except:
        return None

def signup(email: str, password: str):
    try:
        return supabase.auth.sign_up({"email": email, "password": password})
    except:
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

        # Persist project in Supabase user metadata
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


# ----------------- DIALOGS -----------------
@st.dialog("New Observation")
def new_observation_dialog():
    st.write("Use the map center as the observation position.")

    base_center = st.session_state.map_input_center
    zoom = st.session_state.map_input_zoom

    m = folium.Map(location=base_center, zoom_start=zoom)

    html = f"""
    <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); pointer-events: none;">
        <img src="{CROSS_IMAGE_PATH}" style="width:{WIDTH}px; opacity:{OPACITY};" />
    </div>
    """

    folium.Marker(location=base_center, icon=folium.DivIcon(html=html)).add_to(m)

    map_data = st_folium(m, height=400, width=700)
    center = _get_center_from_map_data(map_data, base_center)

    description = st.text_area("Description")
    if st.button("Save observation"):
        supabase.table(OBS_TABLE).insert({
            "project": st.session_state.project,
            "lat": center[0],
            "lon": center[1],
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
        }).execute()
        load_observations(st.session_state.project)
        st.rerun()


@st.dialog("Edit Observation")
def edit_observation_dialog(obs):
    st.write("Edit the observation.")

    lat = st.number_input("Latitude", value=obs["lat"])
    lon = st.number_input("Longitude", value=obs["lon"])
    description = st.text_area("Description", value=obs.get("description", ""))

    if st.button("Update"):
        supabase.table(OBS_TABLE).update({
            "lat": lat,
            "lon": lon,
            "description": description,
        }).eq("id", obs["id"]).execute()
        load_observations(st.session_state.project)
        st.rerun()

    if st.button("Delete", type="secondary"):
        supabase.table(OBS_TABLE).delete().eq("id", obs["id"]).execute()
        load_observations(st.session_state.project)
        st.rerun()


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

    m = folium.Map(location=st.session_state.map_center, zoom_start=4)

    for obs in st.session_state.observations:
        folium.Marker([obs["lat"], obs["lon"]], popup=obs.get("description", "")).add_to(m)

    map_data = st_folium(m, height=500, width=900)
    st.session_state.map_input_center = _get_center_from_map_data(map_data, st.session_state.map_center)
    if map_data and "zoom" in map_data:
        st.session_state.map_input_zoom = map_data["zoom"]

    st.sidebar.header("Observations")
    if st.sidebar.button("New observation"):
        new_observation_dialog()

    for obs in st.session_state.observations:
        label = f"{obs['id']} - {obs.get('description', '')[:30]}"
        if st.sidebar.button(label):
            edit_observation_dialog(obs)


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


    

