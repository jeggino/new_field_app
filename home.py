if polygon_geojson and area_name:
    if st.button("💾 Save to Supabase"):
        try:
            # Convert polygon to GeoJSON string
            geojson_str = json.dumps(polygon_geojson)

            # Create filename
            file_id = f"{area_name.replace(' ', '_')}_{uuid.uuid4()}.geojson"

            # Upload to Supabase bucket
            supabase.storage.from_(BUCKET).upload(
                file_id,
                geojson_str.encode("utf-8"),
                file_options={"content-type": "application/geo+json"}
            )

            # Save filename to Supabase table "projects"
            supabase.table("projects").insert({
                "area_file": file_id,
                "area_name": area_name
            }).execute()

            st.success(f"Saved successfully as {file_id}")

        except Exception as e:
            st.error(f"Upload failed: {e}")



















    

