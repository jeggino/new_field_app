import uuid
import streamlit as st
from supabase import create_client, Client

# Initialize Supabase
SUPABASE_URL = "YOUR_URL"
SUPABASE_KEY = "YOUR_KEY"
BUCKET = "YOUR_BUCKET"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_photo(file):
    if not file:
        st.error("No file provided")
        return None

    try:
        # Read file bytes
        file_bytes = file.read()
        if not file_bytes:
            st.error("File is empty")
            return None

        # Create unique filename
        ext = file.name.split(".")[-1]
        file_id = f"{uuid.uuid4()}.{ext}"

        # Upload to Supabase Storage (Python client expects raw bytes)
        res = supabase.storage.from_(BUCKET).upload(
            file_id,
            file_bytes,
            {
                "content-type": file.type
            }
        )

        # Check for upload errors
        if isinstance(res, dict) and res.get("error"):
            st.error(f"Upload error: {res['error']['message']}")
            return None

        # Get public URL
        url = supabase.storage.from_(BUCKET).get_public_url(file_id)

        return url

    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None
















    

