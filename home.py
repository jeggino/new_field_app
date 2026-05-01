import streamlit as st
from streamlit_folium import st_folium
import folium
from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager
from datetime import datetime

# ----------------- CONFIG -----------------
st.set_page_config(page_title="Observations Map", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SECRET_PASSWORD = st.secrets["COOKIE_PASSWORD"]
USERS_TABLE = "users"
PROJECTS_TABLE = "projects"
OBS_TABLE = "observations"
CROSS_IMAGE_PATH = "https://e1.pngegg.com/pngimages/314/988/png-clipart-symbolize-x.png"  # put your JPEG cross in the same folder

# ----------------- INIT -----------------
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

cookies = EncryptedCookieManager(
    prefix="obs_app_",
    password="CHANGE_THIS_SECRET_PASSWORD",
)
if not cookies.ready():
    st.stop()

defaults = {
    "logged_in": False,
    "username": None,
    "project": None,
    "observations": [],
    "selected_obs_id": None,
    "map_center": [0.0, 0.0],
    "map_input_center": None,
    "map_input_zoom": None,
    
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ----------------- SUPABASE HELPERS -----------------
def login(username: str, password: str) -> bool:
    res = (
        supabase.table(USERS_TABLE)
        .select("*")
        .eq("username", username)
        .eq("password", password)
        .execute()
    )
    return len(res.data) == 1


def load_projects():
    res = supabase.table(PROJECTS_TABLE).select("*").execute()
    return res.data or []


def load_observations(project_name: str):
    res = (
        supabase.table(OBS_TABLE)
        .select("*")
        .eq("project", project_name)
        .execute()
    )
    st.session_state.observations = res.data or []


def insert_observation(data: dict):
    supabase.table(OBS_TABLE).insert(data).execute()
    load_observations(st.session_state.project)


def update_observation(obs_id: int, data: dict):
    supabase.table(OBS_TABLE).update(data).eq("id", obs_id).execute()
    load_observations(st.session_state.project)


def delete_observation(obs_id: int):
    supabase.table(OBS_TABLE).delete().eq("id", obs_id).execute()
    load_observations(st.session_state.project)


# ----------------- COOKIES -----------------
def set_login_cookies(username: str):
    cookies["logged_in"] = "1"
    cookies["username"] = username
    cookies.save()


def clear_login_cookies():
    for k in list(cookies.keys()):
        del cookies[k]
    cookies.save()


def restore_login_from_cookies():
    if cookies.get("logged_in") == "1" and not st.session_state.logged_in:
        st.session_state.logged_in = True
        st.session_state.username = cookies.get("username")


restore_login_from_cookies()


# ----------------- UI: LOGIN & PROJECT SELECT -----------------
def show_login():
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                set_login_cookies(username)
                st.rerun()
            else:
                st.error("Invalid credentials")


def show_project_selection():
    st.title("Select Project")
    projects = load_projects()
    if not projects:
        st.warning("No projects found in Supabase.")
        return

    project_names = [p["name"] for p in projects]
    selected = st.selectbox("Project", project_names)
    if st.button("Confirm project"):
        st.session_state.project = selected
        load_observations(selected)
        st.rerun()


# ----------------- DIALOGS -----------------
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
    center_lat = (sw["lat"] + ne["lat"]) / 2
    center_lon = (sw["lng"] + ne["lng"]) / 2
    return [center_lat, center_lon]


@st.dialog("New Observation")
def new_observation_dialog():
    st.write("Fill in the details and use the map center as position if you want.")

    base_center = st.session_state.map_input_center
    zoom = st.session_state.map_input_zoom

    st.markdown("**Map (cross image indicates center; pan/zoom as needed)**")
    m = folium.Map(location=base_center, zoom_start=zoom)

    # Add a fixed image overlay using HTML and CSS
    html = """
    <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        pointer-events: none; /* Let clicks pass through */
        z-index: 9999;
    ">
        <img src="https://www.bookmarkseparators.com/img/fav/dot-black.png"
             style="width:20px; height:auto; opacity:0.8; color:red">
    </div>
    """

    m.get_root().html.add_child(folium.Element(html))

    # Just a normal map; the cross is shown as an image overlay in Streamlit
    map_data = st_folium(m, width="100%", height=400)

    # lat, lon = current_center
    lat = map_data['center']['lat']
    lon = map_data['center']['lng']
    # st.info(f"Coordinates: lat={lat}, lon={lon}")

    col1, col2 = st.columns(2)
    with col1:
        species = st.text_input("Species")
        username = st.text_input("Username", value=st.session_state.username or "")
        behavior = st.text_input("Behavior")
    with col2:
        date = st.date_input("Date", value=datetime.utcnow().date())


    if st.button("Save observation"):
        if lat is None or lon is None:
            st.warning("Please provide latitude and longitude (via button or manual input).")
            st.stop()
        if not species:
            st.warning("Species is required.")
            st.stop()

        data = {
            "species": species,
            "project": st.session_state.project,
            "username": username,
            "behavior": behavior,
            "date": str(date),
            "lat": float(lat),
            "lon": float(lon),
        }
        insert_observation(data)
        st.rerun()


@st.dialog("Edit Observation")
def edit_observation_dialog(obs):
    st.write(obs)
    st.write("Update the details and position.")

    base_center = [obs.get("lat", 0),obs.get("lon", 0)]
    st.write(base_center)

    m = folium.Map(location=base_center, zoom_start=20)

    # Add a fixed image overlay using HTML and CSS
    html = """
    <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        pointer-events: none; /* Let clicks pass through */
        z-index: 9999;
    ">
        <img src="https://www.bookmarkseparators.com/img/fav/dot-black.png"
             style="width:20px; height:auto; opacity:0.8; color:red">
    </div>
    """

    m.get_root().html.add_child(folium.Element(html))

    map_data = st_folium(m, width="100%", height=400)

    
    
    if st.button("Use current map center as coordinates (edit)"):
        lat = map_data['center']['lat']
        lon = map_data['center']['lng']

    st.write(lat)
    st.write(lon)

    col1, col2 = st.columns(2)
    with col1:
        species = st.text_input("Species", value=obs.get("species", ""))
        username = st.text_input("Username", value=obs.get("username", ""))
        behavior = st.text_input("Behavior", value=obs.get("behavior", ""))
    with col2:
        date = st.date_input(
            "Date",
            value=datetime.fromisoformat(obs.get("date")).date()
            if obs.get("date")
            else datetime.utcnow().date(),
        )


    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Save changes"):
            if lat is None or lon is None:
                st.warning("Please provide latitude and longitude.")
                st.stop()
        data = {
            "species": species,
            "username": username,
            "behavior": behavior,
            "date": str(date),
            "lat": float(lat),
            "lon": float(lon),
        }
        update_observation(obs["id"], data)
        st.rerun()


# ----------------- MAIN APP -----------------
def find_clicked_observation(click_lat, click_lon, observations, tol=1e-5):
    for o in observations:
        if abs(o["lat"] - click_lat) < tol and abs(o["lon"] - click_lon) < tol:
            return o
    return None


def show_main_app():
    st.title("Observations Map")

    # Sidebar
    with st.sidebar:
        st.subheader("Controls")

        st.markdown(
            """
            <style>
            .circle-btn button {
                border-radius: 50% !important;
                height: 60px !important;
                width: 60px !important;
                padding: 0 !important;
                font-size: 24px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="circle-btn">', unsafe_allow_html=True)
        if st.button("＋", key="add_obs_circle"):
            new_observation_dialog()
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Logout", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.project = None
            clear_login_cookies()
            st.rerun()

        st.markdown("---")
        st.write(f"User: **{st.session_state.username}**")
        st.write(f"Project: **{st.session_state.project}**")

    # Map center
    if st.session_state.observations:
        avg_lat = sum(o["lat"] for o in st.session_state.observations) / len(
            st.session_state.observations
        )
        avg_lon = sum(o["lon"] for o in st.session_state.observations) / len(
            st.session_state.observations
        )
        center = [avg_lat, avg_lon]
    else:
        center = [52.01594052906511, 5.300651216815735]

    st.session_state.map_center = center

    # Main map (mobile/laptop friendly)
    m = folium.Map(location=center, zoom_start=2)
    for obs in st.session_state.observations:
        popup_text = f"{obs.get('species', '')} ({obs.get('username', '')})"
        folium.Marker(
            location=[obs["lat"], obs["lon"]],
            popup=popup_text,
            icon=folium.Icon(color="green", icon="cloud", prefix="fa")
        ).add_to(m)

    map_data = st_folium(m, width="100%", height=500)

    st.session_state.map_input_zoom = map_data["zoom"]
    st.session_state.map_input_center = [map_data["center"]['lat'],map_data["center"]['lng']]

    selected_obs = None
    if map_data and map_data.get("last_object_clicked"):
        click_lat = map_data["last_object_clicked"]["lat"]
        click_lon = map_data["last_object_clicked"]["lng"]
        selected_obs = find_clicked_observation(
            click_lat, click_lon, st.session_state.observations
        )
        if selected_obs:
            st.session_state.selected_obs_id = selected_obs["id"]
        else:
            st.session_state.selected_obs_id = None
    else:
        selected_obs = None

    st.subheader("Observations")
    if not st.session_state.observations:
        st.info("No observations yet. Use the circular button in the sidebar to create one.")
        return

    if st.session_state.selected_obs_id is not None:
        selected_obs = next(
            (o for o in st.session_state.observations if o["id"] == st.session_state.selected_obs_id),
            None,
        )

    if selected_obs:
        st.table(
            {
                "Field": [
                    "ID",
                    "Species",
                    "Project",
                    "Username",
                    "Behavior",
                    "Date",
                    "Latitude",
                    "Longitude",
                ],
                "Value": [
                    selected_obs.get("id"),
                    selected_obs.get("species"),
                    selected_obs.get("project"),
                    selected_obs.get("username"),
                    selected_obs.get("behavior"),
                    selected_obs.get("date"),
                    selected_obs.get("lat"),
                    selected_obs.get("lon"),
                ],
            }
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Edit observation"):
                edit_observation_dialog(selected_obs)
        with col2:
            if st.button("Delete observation"):
                delete_observation(selected_obs["id"])
                st.success("Observation deleted.")
                st.session_state.selected_obs_id = None
                st.rerun()
    else:
        st.info("Click on a marker on the map to see its details.")


# ----------------- ROUTING -----------------
if not st.session_state.logged_in:
    show_login()
elif not st.session_state.project:
    show_project_selection()
else:
    show_main_app()

