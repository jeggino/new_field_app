# import streamlit as st
# import streamlit_folium as st_folium
# import folium
# from supabase import create_client, Client
# import geocoder
# import uuid

# # --- CONFIG ---


# import streamlit as st
# from streamlit_folium import st_folium
# import folium
# from supabase import create_client, Client
# import uuid

# # --- CONFIG ---
# st.set_page_config(page_title="Geo Observations", layout="wide")
# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



# # --- SESSION LOGIN ---
# if "user" not in st.session_state:
#     st.session_state.user = None


# def login(email: str, password: str):
#     # Example: custom auth table "app_users" with columns: id, email, password
#     # In production, store hashed passwords and verify properly.
#     res = (
#         supabase.table("app_users")
#         .select("*")
#         .eq("email", email)
#         .eq("password", password)
#         .execute()
#     )
#     if res.data:
#         st.session_state.user = res.data[0]
#         st.session_state.logged_in = True
#         st.success("Logged in successfully")
#         st.rerun()
#     else:
#         st.error("Invalid credentials")

# def logout():
#     st.session_state.user = None
#     st.session_state.logged_in = False
#     st.rerun()






# # def login(username, password):
# #     # Replace with Supabase Auth if needed
# #     if username and password:
# #         st.session_state.user = {"username": username}
# #         st.success(f"Welcome {username}!")

# # def logout():
# #     st.session_state.user = None

# if not st.session_state.user:
#     st.title("🔐 Login")
#     with st.form("login_form"):
#         username = st.text_input("Username")
#         password = st.text_input("Password", type="password")
#         submit = st.form_submit_button("Login")
#         if submit:
#             login(username, password)
#     st.stop()

# # --- MAIN APP ---
# # st.sidebar.write(f"👤 Logged in as: {st.session_state.user['username']}")
# if st.sidebar.button("Logout"):
#     logout()
#     st.experimental_rerun()

# st.title("📍 Geo Observation Tool")

# # --- MAP ---
# m = folium.Map(location=[52.37, 4.90], zoom_start=12)
# map_data = st_folium(m, height=500, width=800)

# # --- OBSERVATION FORM ---
# if map_data and map_data.get("last_clicked"):
#     lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
#     st.subheader("📝 New Observation")
#     with st.form("obs_form"):
#         title = st.text_input("Title")
#         description = st.text_area("Description")
#         category = st.selectbox("Category", ["Wildlife", "Infrastructure", "Other"])
#         save_btn = st.form_submit_button("Save Observation")
#         if save_btn:
#             obs_id = str(uuid.uuid4())
#             supabase.table("observations").insert({
#                 "id": obs_id,
#                 "username": st.session_state.user,
#                 "lat": lat,
#                 "lon": lon,
#                 "title": title,
#                 "description": description,
#                 "category": category
#             }).execute()
#             st.success("✅ Observation saved!")

# # --- DISPLAY EXISTING OBSERVATIONS ---
# st.subheader("📂 Existing Observations")
# data = supabase.table("observations").select("*").execute()

# #--SECOND VERSION
# import streamlit as st
# import pandas as pd
# import plotly.express as px
# from datetime import datetime
# from supabase import create_client, Client
# import uuid

# # ----------------------------
# # CONFIGURATION
# # ----------------------------
# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# st.set_page_config(page_title="Observation Map", layout="wide")

# # ----------------------------
# # SESSION MANAGEMENT
# # ----------------------------
# if "user" not in st.session_state:
#     st.session_state.user = None

# def login(email, password):
#     try:
#         auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
#         st.session_state.user = auth_response.user
#         st.success("Logged in successfully!")
#     except Exception as e:
#         st.error(f"Login failed: {e}")

# def logout():
#     st.session_state.user = None
#     st.experimental_rerun()

# # ----------------------------
# # LOGIN SCREEN
# # ----------------------------
# if not st.session_state.user:
#     st.title("🔐 Login to Observation Map")
#     with st.form("login_form"):
#         email = st.text_input("Email")
#         password = st.text_input("Password", type="password")
#         submit = st.form_submit_button("Login")
#         if submit:
#             login(email, password)
#     st.stop()

# # ----------------------------
# # MAIN APP
# # ----------------------------
# st.title("📍 Interactive Observation Map")
# st.write(f"Welcome, **{st.session_state.user.email}**")
# st.button("Logout", on_click=logout)

# # Load existing observations
# def load_observations():
#     data = supabase.table("observations").select("*").execute()
#     return pd.DataFrame(data.data)

# df = load_observations()

# # Display map
# if not df.empty:
#     fig = px.scatter_mapbox(
#         df,
#         lat="latitude",
#         lon="longitude",
#         hover_name="description",
#         hover_data=["date"],
#         zoom=2,
#         height=600
#     )
#     fig.update_layout(mapbox_style="open-street-map")
#     st.plotly_chart(fig, use_container_width=True)
# else:
#     st.info("No observations yet. Add one below!")

# # ----------------------------
# # ADD OBSERVATION POP-UP
# # ----------------------------
# with st.expander("➕ Add New Observation"):
#     col1, col2 = st.columns(2)
#     with col1:
#         latitude = st.number_input("Latitude", format="%.6f")
#         longitude = st.number_input("Longitude", format="%.6f")
#     with col2:
#         date = st.date_input("Observation Date", datetime.today())
#         description = st.text_area("Description")

#     if st.button("Save Observation"):
#         if latitude and longitude and description:
#             supabase.table("observations").insert({
#                 "id": str(uuid.uuid4()),
#                 "user_id": st.session_state.user.id,
#                 "latitude": latitude,
#                 "longitude": longitude,
#                 "date": str(date),
#                 "description": description
#             }).execute()
#             st.success("Observation saved!")
#             st.experimental_rerun()
#         else:
#             st.error("Please fill in all required fields.")

# for obs in data.data:
#     st.write(f"**{obs['title']}** ({obs['lat']}, {obs['lon']}) - {obs['category']}")


# #----THIRD VERSION
# import streamlit as st
# import pandas as pd
# import plotly.express as px
# from datetime import datetime
# from supabase import create_client, Client
# import uuid

# # ----------------------------
# # CONFIGURATION
# # ----------------------------
# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# st.set_page_config(page_title="Observation Map", layout="wide")

# # ----------------------------
# # SESSION MANAGEMENT
# # ----------------------------
# if "user" not in st.session_state:
#     st.session_state.user = None

# def login(email, password):
#     try:
#         auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
#         st.session_state.user = auth_response.user
#         st.success("Logged in successfully!")
#     except Exception as e:
#         st.error(f"Login failed: {e}")

# def logout():
#     st.session_state.user = None
#     st.experimental_rerun()

# # ----------------------------
# # LOGIN SCREEN
# # ----------------------------
# if not st.session_state.user:
#     st.title("🔐 Login to Observation Map")
#     with st.form("login_form"):
#         email = st.text_input("Email")
#         password = st.text_input("Password", type="password")
#         submit = st.form_submit_button("Login")
#         if submit:
#             login(email, password)
#     st.stop()

# # ----------------------------
# # MAIN APP
# # ----------------------------
# st.title("📍 Interactive Observation Map")
# st.write(f"Welcome, **{st.session_state.user.email}**")
# st.button("Logout", on_click=logout)

# # Load existing observations
# def load_observations():
#     data = supabase.table("observations").select("*").execute()
#     return pd.DataFrame(data.data)

# df = load_observations()

# # Display map
# if not df.empty:
#     fig = px.scatter_mapbox(
#         df,
#         lat="latitude",
#         lon="longitude",
#         hover_name="description",
#         hover_data=["date"],
#         zoom=2,
#         height=600
#     )
#     fig.update_layout(mapbox_style="open-street-map")
#     st.plotly_chart(fig, use_container_width=True)
# else:
#     st.info("No observations yet. Add one below!")

# # ----------------------------
# # ADD OBSERVATION POP-UP
# # ----------------------------
# with st.expander("➕ Add New Observation"):
#     col1, col2 = st.columns(2)
#     with col1:
#         latitude = st.number_input("Latitude", format="%.6f")
#         longitude = st.number_input("Longitude", format="%.6f")
#     with col2:
#         date = st.date_input("Observation Date", datetime.today())
#         description = st.text_area("Description")

#     if st.button("Save Observation"):
#         if latitude and longitude and description:
#             supabase.table("observations").insert({
#                 "id": str(uuid.uuid4()),
#                 "user_id": st.session_state.user.id,
#                 "latitude": latitude,
#                 "longitude": longitude,
#                 "date": str(date),
#                 "description": description
#             }).execute()
#             st.success("Observation saved!")
#             st.experimental_rerun()
#         else:
#             st.error("Please fill in all required fields.")


import streamlit as st
from streamlit_folium import st_folium
import folium
from datetime import date
from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager

# ---------------------------
# CONFIGURATION
# ---------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Cookie manager for persistent login
cookies = EncryptedCookieManager(prefix="myapp_", password=st.secrets["COOKIE_PASSWORD"])
if not cookies.ready():
    st.stop()

# ---------------------------
# AUTHENTICATION
# ---------------------------
def login(username, password):
    res = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
    return len(res.data) > 0

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    saved_user = cookies.get("username")
    if saved_user:
        st.session_state.logged_in = True
        st.session_state.username = saved_user
    else:
        st.title("🔐 Login")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if login(user, pwd):
                st.session_state.logged_in = True
                st.session_state.username = user
                cookies["username"] = user
                cookies.save()
                # st.experimental_rerun()
            else:
                st.error("Invalid credentials")
        st.stop()

# ---------------------------
# MAP & OBSERVATIONS
# ---------------------------
st.title("🗺️ Observation Map")
st.write(f"Welcome, **{st.session_state.username}**!")

# Load existing observations
obs_data = supabase.table("observations").select("*").execute().data

# Create Folium map
m = folium.Map(location=[52.37, 4.90], zoom_start=12)

# Add existing markers
for obs in obs_data:
    folium.Marker(
        location=[obs["lat"], obs["lon"]],
        popup=f"{obs['description']} ({obs['date']})"
    ).add_to(m)

# Display map and capture click
map_data = st_folium(m, height=500, width=800)

# ---------------------------
# ADD NEW OBSERVATION
# ---------------------------
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    with st.dialog("Add New Observation"):
        st.write(f"📍 Location: {lat:.5f}, {lon:.5f}")
        desc = st.text_area("Description")
        obs_date = st.date_input("Date", value=date.today())
        if st.button("Save Observation"):
            supabase.table("observations").insert({
                "lat": lat,
                "lon": lon,
                "description": desc,
                "date": str(obs_date),
                "user": st.session_state.username
            }).execute()
            st.success("Observation saved!")
            st.experimental_rerun()

