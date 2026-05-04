import streamlit as st
from supabase import create_client, Client

# ---------------------------------------------------------
# SUPABASE SETUP
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = "observation_photos"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.title("Simple Supabase File Upload")

name = st.text_input("Enter file name (without extension)")
file = st.file_uploader("Choose a file to upload")

if name and file:
    if st.button("Upload"):
        try:
            filename = f"{name}.geojson"  # or any extension you want

            # Upload to bucket
            res = supabase.storage.from_(BUCKET).upload(
                filename,
                file.read(),
                file_options={"content-type": "application/octet-stream"}
            )

            st.write("Upload response:", res)

            if "error" in res:
                st.error(f"Upload failed: {res['error']}")
            else:
                st.success(f"Uploaded as {filename}")

        except Exception as e:
            st.error(f"Error: {e}")









    

