import streamlit as st
import pandas as pd
import folium
from datetime import datetime, date
from streamlit_folium import st_folium
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# ---------------------------------------------------------
# CONSTANTS (from your secrets)
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SECRET_PASSWORD = st.secrets["COOKIE_PASSWORD"]

USERS_TABLE = "users"
PROJECTS_TABLE = "projects"
OBS_TABLE = "observations"
REPORT_TABLE = "daily_report"

MEDIA_BUCKET = "observations-media"
COOKIE_NAME = "fieldapp_session"

# ---------------------------------------------------------
# INIT SUPABASE + COOKIES
# ---------------------------------------------------------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

cookies = EncryptedCookieManager(prefix="fieldapp_", password=SECRET_PASSWORD)
if not cookies.ready():
    st.stop()

# ---------------------------------------------------------
# SESSION HELPERS
# ---------------------------------------------------------
def save_session(username: str):
    cookies[COOKIE_NAME] = username
    cookies.save()

def clear_session():
    if COOKIE_NAME in cookies:
        del cookies[COOKIE_NAME]
        cookies.save()
    st.session_state.clear()

def restore_session():
    username = cookies.get(COOKIE_NAME)
    if not username:
        return None
    try:
        user = supabase.table(USERS_TABLE).select("*").eq("username", username).single().execute().data
        return {"username": username, "license": user["license"]}
    except Exception:
        return None

# ---------------------------------------------------------
# AUTH
# ---------------------------------------------------------
def login_page():
    st.title("Field Data App – Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log in")

    if submit:
        try:
            user = supabase.table(USERS_TABLE).select("*").eq("username", username).single().execute().data
        except Exception:
            st.error("Invalid username or password")
            return

        if user["password"] != password:
            st.error("Invalid username or password")
            return

        st.session_state["user"] = {"username": username, "license": user["license"]}
        save_session(username)
        st.rerun()

# ---------------------------------------------------------
# RESTORE SESSION
# ---------------------------------------------------------
if "user" not in st.session_state:
    restored = restore_session()
    if restored:
        st.session_state["user"] = restored

if "user" not in st.session_state:
    login_page()
    st.stop()

user = st.session_state["user"]

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
st.sidebar.title("Menu")
st.sidebar.write(f"Logged in as **{user['username']}** ({user['license']})")

# Project selection
projects = supabase.table(PROJECTS_TABLE).select("*").execute().data
user_projects = [p["name"] for p in projects if user["username"] in p["users"]]

if "project" not in st.session_state:
    st.session_state["project"] = user_projects[0]

project = st.sidebar.selectbox("Select project", user_projects)
st.session_state["project"] = project

# Action buttons
is_guest = user["license"] == "guest"

if st.sidebar.button("Create Observation", disabled=is_guest):
    st.session_state["action"] = "create_obs"
    st.rerun()

if st.sidebar.button("View / Edit Observation"):
    st.session_state["action"] = "view_obs"
    st.rerun()

if st.sidebar.button("Delete Observation", disabled=is_guest):
    st.session_state["action"] = "delete_obs"
    st.rerun()

# ⭐ NEW: Daily Report Button
if st.sidebar.button("Create Daily Report", disabled=is_guest):
    st.session_state["action"] = "daily_report"
    st.rerun()

# Logout
if st.sidebar.button("Log out"):
    clear_session()
    st.rerun()

# ---------------------------------------------------------
# MAIN PAGE
# ---------------------------------------------------------
st.title(f"Project: {project}")

# Load observations
obs = supabase.table(OBS_TABLE).select("*").eq("project", project).execute().data
df_obs = pd.DataFrame(obs)

# Map
st.subheader("Map")
if not df_obs.empty:
    lat = df_obs["latitude"].dropna().iloc[0]
    lon = df_obs["longitude"].dropna().iloc[0]
else:
    lat, lon = 52.4, 4.8

m = folium.Map(location=[lat, lon], zoom_start=10)

for _, row in df_obs.iterrows():
    if pd.notna(row["latitude"]) and pd.notna(row["longitude"]):
        folium.Marker(
            [row["latitude"], row["longitude"]],
            tooltip=row["species"],
            popup=row["description"]
        ).add_to(m)

st_folium(m, width=900, height=500)

# ---------------------------------------------------------
# ACTION HANDLING
# ---------------------------------------------------------
action = st.session_state.get("action")

if action == "daily_report":
    st.subheader("Create Daily Report")

    with st.form("daily_report_form"):
        assignment = st.text_input("Assignment")
        date_val = st.date_input("Date", value=datetime.utcnow().date())
        temperature = st.number_input("Temperature (°C)")
        rainfall = st.number_input("Rainfall (mm)")
        wind = st.number_input("Wind speed (m/s)")
        description = st.text_area("Description")
        submit = st.form_submit_button("Save")

    if submit:
        supabase.table(REPORT_TABLE).insert({
            "username": user["username"],
            "project": project,
            "assignment": assignment,
            "date": date_val.isoformat(),
            "temperature": temperature,
            "rainfall": rainfall,
            "wind": wind,
            "description": description
        }).execute()

        st.success("Daily report saved!")
        del st.session_state["action"]
        st.rerun()







