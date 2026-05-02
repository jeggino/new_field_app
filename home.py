import os
from datetime import datetime, date

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager

# ---------------------------------------------------------
# Constants (from your secrets)
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SECRET_PASSWORD = st.secrets["COOKIE_PASSWORD"]
USERS_TABLE = "users"
PROJECTS_TABLE = "projects"
OBS_TABLE = "observations"
REPORT_TABLE = "daily_report"

MEDIA_BUCKET = "observations-media"  # change if your bucket is named differently
COOKIE_NAME = "fieldapp_session_v1"

# ---------------------------------------------------------
# Supabase + cookies
# ---------------------------------------------------------
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

cookies = EncryptedCookieManager(
    prefix="fieldapp_",
    password=SECRET_PASSWORD,
)

# This is required for the cookie manager to initialize
if not cookies.ready():
    st.stop()

# ---------------------------------------------------------
# Session persistence helpers
# ---------------------------------------------------------
def save_session_to_cookie(username: str):
    cookies[COOKIE_NAME] = username
    cookies.save()

def clear_session_cookie():
    if COOKIE_NAME in cookies:
        del cookies[COOKIE_NAME]
        cookies.save()

def restore_session_from_cookie():
    username = cookies.get(COOKIE_NAME)
    if not username:
        return None
    resp = supabase.table(USERS_TABLE).select("*").eq("username", username).limit(1).execute()
    if getattr(resp, "error", None) or not resp.data:
        return None
    user = resp.data[0]
    return {
        "username": username,
        "license": user.get("license", "guest"),
    }

# ---------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------
def supabase_sign_in(username: str, password: str):
    resp = supabase.table(USERS_TABLE).select("*").eq("username", username).limit(1).execute()
    if getattr(resp, "error", None):
        return None, "Error querying users table"
    rows = resp.data
    if not rows:
        return None, "User not found"
    user = rows[0]
    # NOTE: plaintext for demo only; use hashing in production
    if user.get("password") != password:
        return None, "Invalid password"
    session = {
        "username": username,
        "license": user.get("license", "guest"),
        "created_at": datetime.utcnow().isoformat()
    }
    return session, None

def is_guest() -> bool:
    return st.session_state.get("user", {}).get("license", "guest") == "guest"

# ---------------------------------------------------------
# Data helpers
# ---------------------------------------------------------
def load_projects_for_user(username: str):
    resp = supabase.table(PROJECTS_TABLE).select("*").execute()
    if getattr(resp, "error", None):
        st.error("Failed to load projects")
        return []
    projects = resp.data
    return [p for p in projects if username in (p.get("users") or [])]

def load_observations(project_name: str):
    resp = supabase.table(OBS_TABLE).select("*").eq("project", project_name).execute()
    if getattr(resp, "error", None):
        st.error("Failed to load observations")
        return []
    return resp.data

def load_daily_reports(project_name: str, day: date | None = None):
    query = supabase.table(REPORT_TABLE).select("*").eq("project", project_name)
    if day is not None:
        query = query.eq("date", day.isoformat())
    resp = query.execute()
    if getattr(resp, "error", None):
        st.error("Failed to load daily reports")
        return []
    return resp.data

def create_observation(obs: dict) -> bool:
    if is_guest():
        st.warning("Guests cannot create observations.")
        return False
    resp = supabase.table(OBS_TABLE).insert(obs).execute()
    if getattr(resp, "error", None):
        st.error(f"Failed to create observation: {resp.error.message}")
        return False
    return True

def update_observation(obs_id: str, updates: dict) -> bool:
    if is_guest():
        st.warning("Guests cannot modify observations.")
        return False
    resp = supabase.table(OBS_TABLE).update(updates).eq("id", obs_id).execute()
    if getattr(resp, "error", None):
        st.error(f"Failed to update observation: {resp.error.message}")
        return False
    return True

def delete_observation(obs_id: str) -> bool:
    if is_guest():
        st.warning("Guests cannot delete observations.")
        return False
    resp = supabase.table(OBS_TABLE).delete().eq("id", obs_id).execute()
    if getattr(resp, "error", None):
        st.error(f"Failed to delete observation: {resp.error.message}")
        return False
    return True

def create_daily_report(report: dict) -> bool:
    if is_guest():
        st.warning("Guests cannot create daily reports.")
        return False
    resp = supabase.table(REPORT_TABLE).insert(report).execute()
    if getattr(resp, "error", None):
        st.error(f"Failed to create daily report: {resp.error.message}")
        return False
    return True

def upload_media(file, username: str, project: str):
    if file is None:
        return None
    ext = os.path.splitext(file.name)[1] or ".bin"
    key = f"{project}/{username}/{datetime.utcnow().isoformat().replace(':','-')}{ext}"
    data = file.read()
    res = supabase.storage.from_(MEDIA_BUCKET).upload(key, data)
    if res.get("error"):
        st.error(f"Failed to upload media: {res['error']['message']}")
        return None
    return key

def get_media_public_url(media_id: str | None):
    if not media_id:
        return None
    return supabase.storage.from_(MEDIA_BUCKET).get_public_url(media_id)

# ---------------------------------------------------------
# UI: login
# ---------------------------------------------------------
def login_page():
    st.title("Field Data App - Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        session, err = supabase_sign_in(username.strip(), password)
        if err:
            st.error(err)
            return
        st.session_state["user"] = session
        save_session_to_cookie(username.strip())
        st.rerun()

def logout():
    clear_session_cookie()
    st.session_state.clear()
    st.rerun()

# ---------------------------------------------------------
# Initial session restore
# ---------------------------------------------------------
if "user" not in st.session_state:
    restored = restore_session_from_cookie()
    if restored:
        st.session_state["user"] = restored

if "page" not in st.session_state:
    st.session_state["page"] = "main"

if "user" not in st.session_state or not st.session_state["user"]:
    login_page()
    st.stop()

user = st.session_state["user"]

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
st.sidebar.write(f"**User:** {user.get('username')} ({user.get('license', 'guest')})")

if st.sidebar.button("Switch project"):
    if "project" in st.session_state:
        del st.session_state["project"]
    st.rerun()

if st.sidebar.button("Log out"):
    logout()

projects = load_projects_for_user(user.get("username"))
project_names = [p["name"] for p in projects]

if not project_names:
    st.warning("No projects assigned to this user.")
    st.stop()

if "project" not in st.session_state:
    st.session_state["project"] = project_names[0]

st.sidebar.markdown("### Projects")
selected_project = st.sidebar.selectbox(
    "Select project",
    project_names,
    index=project_names.index(st.session_state["project"])
    if st.session_state["project"] in project_names else 0
)
st.session_state["project"] = selected_project

st.sidebar.markdown("---")
if st.sidebar.button("Create observation", disabled=is_guest()):
    st.session_state["action"] = "create_obs"
    st.rerun()
if st.sidebar.button("View / Edit observation"):
    st.session_state["action"] = "view_obs"
    st.rerun()
if st.sidebar.button("Delete observation", disabled=is_guest()):
    st.session_state["action"] = "delete_obs"
    st.rerun()
if st.sidebar.button("Generate daily report", disabled=is_guest()):
    st.session_state["action"] = "daily_report"
    st.rerun()

# ---------------------------------------------------------
# Main layout
# ---------------------------------------------------------
st.header(f"Project: {st.session_state['project']}")

observations = load_observations(st.session_state["project"])
df_obs = pd.DataFrame(observations) if observations else pd.DataFrame(
    columns=[
        "id", "username", "project", "assignment", "date", "species",
        "behavior", "function", "description", "media_id", "latitude", "longitude"
    ]
)

# ---------------------------------------------------------
# Map with legend
# ---------------------------------------------------------
st.subheader("Map")
if not df_obs.empty and df_obs["latitude"].notnull().any() and df_obs["longitude"].notnull().any():
    center_lat = float(df_obs["latitude"].dropna().iloc[0])
    center_lon = float(df_obs["longitude"].dropna().iloc[0])
else:
    center_lat, center_lon = 52.4, 4.8  # default center

m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

for _, row in df_obs.iterrows():
    lat, lon = row.get("latitude"), row.get("longitude")
    if pd.isna(lat) or pd.isna(lon):
        continue
    media_url = get_media_public_url(row.get("media_id"))
    media_html = f'<br><img src="{media_url}" width="150">' if media_url else ""
    popup_html = f"""
    <b>{row.get('species','')}</b><br>
    {row.get('date','')}<br>
    <i>{row.get('description','')}</i><br>
    <small>By: {row.get('username')}</small>
    {media_html}
    """
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=row.get("species", "")
    ).add_to(m)

legend_html = """
 <div style="
 position: fixed;
 bottom: 50px;
 left: 50px;
 width: 220px;
 z-index:9999;
 background-color:white;
 padding:10px;
 border:2px solid grey;
 ">
 <b>Legend</b><br>
 Marker: Observation point<br>
 Click marker for details
 </div>
"""
m.get_root().html.add_child(folium.Element(legend_html))
st_folium(m, width=900, height=500)

action = st.session_state.get("action")

# ---------------------------------------------------------
# Create observation
# ---------------------------------------------------------
if action == "create_obs":
    st.subheader("Create observation")
    with st.form("create_obs_form"):
        assignment = st.text_input("Assignment")
        date_val = st.date_input("Date", value=datetime.utcnow().date())
        species = st.text_input("Species")
        behavior = st.text_input("Behavior")
        function = st.text_input("Function")
        description = st.text_area("Description")
        lat = st.number_input("Latitude", format="%.6f")
        lon = st.number_input("Longitude", format="%.6f")
        media_file = st.file_uploader("Picture (optional)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Save")

    if submitted:
        media_id = upload_media(media_file, user.get("username"), st.session_state["project"])
        obs = {
            "username": user.get("username"),
            "project": st.session_state["project"],
            "assignment": assignment,
            "date": datetime.combine(date_val, datetime.min.time()).isoformat(),
            "species": species,
            "behavior": behavior,
            "function": function,
            "description": description,
            "media_id": media_id,
            "latitude": float(lat),
            "longitude": float(lon),
        }
        if create_observation(obs):
            st.success("Observation created")
            del st.session_state["action"]
            st.rerun()

# ---------------------------------------------------------
# View / edit observation
# ---------------------------------------------------------
elif action == "view_obs":
    st.subheader("View / Edit observation")
    if df_obs.empty:
        st.info("No observations for this project")
    else:
        options = df_obs.apply(
            lambda r: f"{r['id']} | {r.get('species','')} | {r.get('date','')}",
            axis=1
        ).tolist()
        selected_label = st.selectbox("Observation", options)
        selected_id = selected_label.split(" | ")[0]
        obs_row = df_obs[df_obs["id"] == selected_id].iloc[0].to_dict()

        media_url = get_media_public_url(obs_row.get("media_id"))
        if media_url:
            st.markdown("Current picture:")
            st.image(media_url, width=200)

        with st.form("edit_obs_form"):
            species = st.text_input("Species", value=obs_row.get("species", ""))
            behavior = st.text_input("Behavior", value=obs_row.get("behavior", ""))
            function = st.text_input("Function", value=obs_row.get("function", ""))
            description = st.text_area("Description", value=obs_row.get("description", ""))
            lat = st.number_input(
                "Latitude",
                value=float(obs_row.get("latitude") or 0.0),
                format="%.6f"
            )
            lon = st.number_input(
                "Longitude",
                value=float(obs_row.get("longitude") or 0.0),
                format="%.6f"
            )
            new_media_file = st.file_uploader("Replace picture (optional)", type=["jpg", "jpeg", "png"])
            save = st.form_submit_button("Save changes", disabled=is_guest())

        if save:
            media_id = obs_row.get("media_id")
            if new_media_file is not None:
                media_id = upload_media(new_media_file, user.get("username"), st.session_state["project"])
            updates = {
                "species": species,
                "behavior": behavior,
                "function": function,
                "description": description,
                "latitude": float(lat),
                "longitude": float(lon),
                "media_id": media_id,
            }
            if update_observation(selected_id, updates):
                st.success("Observation updated")
                del st.session_state["action"]
                st.rerun()

# ---------------------------------------------------------
# Delete observation
# ---------------------------------------------------------
elif action == "delete_obs":
    st.subheader("Delete observation")
    if df_obs.empty:
        st.info("No observations to delete")
    else:
        options = df_obs.apply(
            lambda r: f"{r['id']} | {r.get('species','')} | {r.get('date','')}",
            axis=1
        ).tolist()
        selected_label = st.selectbox("Observation to delete", options)
        selected_id = selected_label.split(" | ")[0]
        if st.button("Confirm delete", disabled=is_guest()):
            if delete_observation(selected_id):
                st.success("Observation deleted")
                del st.session_state["action"]
                st.rerun()

# ---------------------------------------------------------
# Daily report
# ---------------------------------------------------------
elif action == "daily_report":
    st.subheader("Daily report")
    with st.form("daily_report_form"):
        assignment = st.text_input("Assignment")
        date_val = st.date_input("Date", value=datetime.utcnow().date())
        temperature = st.number_input("Temperature (°C)", format="%.1f")
        rainfall = st.number_input("Rainfall (mm)", format="%.1f")
        wind = st.number_input("Wind speed (m/s)", format="%.1f")
        description = st.text_area("Description")
        submitted = st.form_submit_button("Save daily report", disabled=is_guest())

    if submitted:
        report = {
            "username": user.get("username"),
            "project": st.session_state["project"],
            "assignment": assignment,
            "date": date_val.isoformat(),
            "temperature": float(temperature),
            "rainfall": float(rainfall),
            "wind": float(wind),
            "description": description,
        }
        if create_daily_report(report):
            st.success("Daily report saved")
            del st.session_state["action"]
            st.rerun()

    st.markdown("### Daily reports for selected date")
    reports = load_daily_reports(st.session_state["project"], day=date_val)
    df_reports = pd.DataFrame(reports) if reports else pd.DataFrame(
        columns=["id", "username", "project", "assignment", "date",
                 "temperature", "rainfall", "wind", "description"]
    )
    if not df_reports.empty:
        st.dataframe(df_reports)
    else:
        st.info("No daily reports for this date")

# ---------------------------------------------------------
# Observations table
# ---------------------------------------------------------
st.markdown("---")
st.subheader("Observations table")
if not df_obs.empty:
    st.dataframe(
        df_obs[
            [
                "id", "username", "assignment", "date", "species",
                "behavior", "function", "description", "media_id",
                "latitude", "longitude"
            ]
        ]
    )
else:
    st.info("No observations to display")






