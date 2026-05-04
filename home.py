import streamlit as st
from supabase import create_client

# -----------------------------
# Supabase setup
# -----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = "observation_photos"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# UI
# -----------------------------
st.title("Save Project + Upload File")

project_name = st.text_input("Project name")
project_description = st.text_area("Project description")
file = st.file_uploader("Choose a file to upload")

if project_name and project_description and file:
    if st.button("Save Project"):
        filename = f"{project_name.replace(' ', '_')}.geojson"

        try:
            # 1. Upload file to bucket
            upload_res = supabase.storage.from_(BUCKET).upload(
                filename,
                file.read(),
                file_options={"content-type": "application/octet-stream"}
            )

            # Optional: inspect raw response for debugging
            # st.write(upload_res)

            # 2. Insert into projects table
            insert_res = supabase.table("projects").insert({
                "name": project_name,
                "description": project_description
            }).execute()

            # Optional: inspect DB response
            # st.write(insert_res)

            st.success(f"Project saved! File uploaded as {filename}")

        except Exception as e:
            st.error(f"Exception: {e}")

