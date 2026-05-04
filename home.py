import streamlit as st
from supabase import create_client

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = "observation_photos"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Upload Test to Supabase Bucket")

name = st.text_input("Enter file name (without extension)")
file = st.file_uploader("Choose a file")

if name and file:
    if st.button("Upload"):
        filename = f"{name}.geojson"  # or any extension you want

        res = supabase.storage.from_(BUCKET).upload(
            filename,
            file.read(),
            file_options={"content-type": "application/octet-stream"}
        )

        st.write(res)

        if "error" in res:
            st.error("Upload failed")
        else:
            st.success(f"Uploaded as {filename}")











    

