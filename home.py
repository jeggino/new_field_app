import streamlit as st
from streamlit_folium import st_folium
import folium
import json
from supabase import create_client
from folium.plugins import Geocoder, Fullscreen, Draw
import pandas as pd





# ---------------------------------------------------------
# USERNAME + PASSWORD LOGIN (from st.secrets)
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:

    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        allowed_users = st.secrets["users"]  # [users] section in secrets.toml

        if username not in allowed_users:
            st.error("Unknown username")
            st.stop()

        if password != allowed_users[username]:
            st.error("Incorrect password")
            st.stop()

        st.session_state.authenticated = True
        st.session_state.username = username
        st.success("Login successful")

        st.rerun()

    st.stop()

# ---------------------------------------------------------
# SUPABASE SETUP
# ---------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
BUCKET = "observation_photos"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def load_project_boundary(project_name):
    """Load <project>.geojson from Supabase and return (geojson_dict, bounds)."""

    filename = f"{project_name}.geojson"

    try:
        file_bytes = supabase.storage.from_(BUCKET).download(filename)
        if not file_bytes:
            return None, None

        geojson_str = file_bytes.decode("utf-8")
        data = json.loads(geojson_str)

        # Extract coordinates for bounds
        coords = []

        def extract_coords(geom):
            t = geom["type"]
            c = geom["coordinates"]

            if t == "Polygon":
                for ring in c:
                    coords.extend(ring)

            elif t == "MultiPolygon":
                for poly in c:
                    for ring in poly:
                        coords.extend(ring)

        # GeoJSON may be Feature or FeatureCollection
        if data.get("type") == "Feature":
            extract_coords(data["geometry"])

        elif data.get("type") == "FeatureCollection":
            for feature in data["features"]:
                extract_coords(feature["geometry"])

        if not coords:
            return data, None

        lats = [p[1] for p in coords]
        lngs = [p[0] for p in coords]

        bounds = [[min(lats), min(lngs)], [max(lats), max(lngs)]]

        return data, bounds

    except Exception as e:
        st.warning(f"Could not load boundary for project '{project_name}': {e}")
        return None, None
        
def compute_centroid(geojson_obj):
    geom = geojson_obj.get("geometry", geojson_obj)
    coords = []

    if geom["type"] == "Polygon":
        coords = geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            coords.extend(poly[0])

    if not coords:
        return [52.37, 4.90]

    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    return [sum(lats) / len(lats), sum(lons) / len(lons)]


def get_bounds(geojson_obj):
    """Return [[min_lat, min_lon], [max_lat, max_lon]] from Polygon/MultiPolygon."""
    geom = geojson_obj.get("geometry", geojson_obj)
    coords = []

    if geom["type"] == "Polygon":
        coords = geom["coordinates"][0]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            coords.extend(poly[0])

    if not coords:
        return [[52.37, 4.90], [52.37, 4.90]]

    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]

# ---------------------------------------------------------
# DELETE CONFIRMATION DIALOG
# ---------------------------------------------------------
@st.dialog("Confirm deletion", width="small")
def confirm_delete_dialog(project_name):
    st.image(
        "https://media1.tenor.com/m/Y3qtler-qqEAAAAC/suspicious-dog.gif",
        width=500,
    )
    st.write(f"Are you sure you want to delete project **{project_name}**?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, delete", type="primary"):
            try:
                supabase.storage.from_(BUCKET).remove([f"{project_name}.geojson"])
                supabase.table("project_members").delete().eq("project", project_name).execute()
                supabase.table("projects").delete().eq("name", project_name).execute()
                st.success(f"Project '{project_name}' deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting project: {e}")
    with col2:
        if st.button("Cancel"):
            st.rerun()

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
page = st.sidebar.radio("Navigation", ["Create Project", "View Projects"])

# ---------------------------------------------------------
# PAGE 1 — CREATE PROJECT
# ---------------------------------------------------------
if page == "Create Project":
    st.title("Create Project")
    st.write("Draw a polygon, enter a name, description, and assign users.")

    # Initialize drawing state
    if "last_drawings" not in st.session_state:
        st.session_state["last_drawings"] = None

    if "confirm_multipolygon" not in st.session_state:
        st.session_state.confirm_multipolygon = False

    # MAP
    m = folium.Map(location=[52.37, 4.90], zoom_start=12, zoom_control=True)

    # Satellite (Esri)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=True
    ).add_to(m)

    # Geocoder FIRST
    Geocoder(
        collapsed=False,
        add_marker=True,
        position='topleft'
    ).add_to(m)

    # Draw SECOND
    Draw(
        draw_options={"polygon": True, "marker": False, "circle": False,
                      "polyline": False, "rectangle": False},
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    Fullscreen(position="topleft").add_to(m)
    folium.LayerControl(position="topright").add_to(m)

    # Render map
    with st.container():
        map_data = st_folium(m, height=500, use_container_width=True)

    # Store drawings
    if map_data and "all_drawings" in map_data:
        st.session_state["last_drawings"] = map_data["all_drawings"]

    polygon_geojson = None

    # Process drawings
    if st.session_state["last_drawings"]:
        drawings = st.session_state["last_drawings"]
        polygons = []

        for d in drawings:
            geom = d.get("geometry", {})
            if geom.get("type") == "Polygon":
                polygons.append(geom["coordinates"])
            elif geom.get("type") == "MultiPolygon":
                polygons.extend(geom["coordinates"])

        # MULTIPOLYGON CHECK
        if len(polygons) > 1:

            if not st.session_state.confirm_multipolygon:
                st.warning("⚠️ You drew more than one polygon. This will be saved as a MultiPolygon.")

                colA, colB = st.columns(2)

                with colA:
                    if st.button("Yes, save as MultiPolygon"):
                        st.session_state.confirm_multipolygon = True
                        st.rerun()

                with colB:
                    if st.button("No, let me fix it"):
                        st.info("Please delete the extra polygons and draw only one.")
                        st.stop()

                st.stop()

            # User confirmed → build multipolygon
            polygon_geojson = {
                "type": "Feature",
                "geometry": {"type": "MultiPolygon", "coordinates": polygons}
            }

        else:
            # Single polygon
            polygon_geojson = {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": polygons[0]}
            }

    # FORM
    project_name = st.text_input("Project name")
    description = st.text_area("Description")

    try:
        users = supabase.rpc("get_all_users").execute().data or []
    except:
        users = []

    email_to_id = {u["email"]: u["id"] for u in users}
    selected_emails = st.multiselect("Users who can work on this project", list(email_to_id.keys()))

    # SAVE PROJECT
    if st.button("Save Project"):

        if not polygon_geojson:
            st.error("Draw a polygon first.")
            st.stop()

        if not project_name:
            st.error("Enter a project name.")
            st.stop()

        safe_name = project_name.replace(" ", "_")
        filename = f"{safe_name}.geojson"

        # Check duplicate
        existing = supabase.table("projects").select("name").eq("name", safe_name).execute()
        if existing.data:
            st.error(f"A project named '{safe_name}' already exists. Choose another name.")
            st.stop()

        # Save
        supabase.storage.from_(BUCKET).upload(
            filename,
            json.dumps(polygon_geojson).encode("utf-8"),
            file_options={"content-type": "application/geo+json", "x-upsert": "true"}
        )

        supabase.table("projects").insert(
            {"name": safe_name, "description": description}
        ).execute()

        for email in selected_emails:
            supabase.table("project_members").insert(
                {"project": safe_name, "user_id": email_to_id[email]}
            ).execute()

        st.success(f"Project '{safe_name}' has been successfully created.")

        # Reset multipolygon confirmation
        st.session_state.confirm_multipolygon = False
        st.session_state["last_drawings"] = None

        st.rerun()




# # ---------------------------------------------------------
# # PAGE 2 — VIEW PROJECTS
# # ---------------------------------------------------------
# elif page == "View Projects":
#     st.title("View Projects")

#     # --- Load all projects ---
#     proj_res = supabase.table("projects").select("*").execute()
#     projects = proj_res.data or []

#     if not projects:
#         st.info("No projects found.")
#         st.stop()

#     project_names = [p["name"] for p in projects]
#     selected = st.selectbox(
#         "Select a project",
#         project_names,
#         index=None,
#         placeholder="Select a project...",
#     )

#     if not selected:
#         st.stop()

#     # Current project data
#     project = next(p for p in projects if p["name"] == selected)

#     st.subheader("Project Info")
#     st.write(f"**Name:** {project['name']}")
#     st.write(f"**Description:** {project['description']}")

#     # --- Load all users from Supabase ---
#     try:
#         users = supabase.rpc("get_all_users").execute().data or []
#     except:
#         users = []

#     # Two mappings
#     id_to_email = {u["id"]: u["email"] for u in users}
#     email_to_id = {u["email"]: u["id"] for u in users}

#     # --- Load project members ---
#     pm_res = supabase.table("project_members").select("*").eq("project", selected).execute()
#     members = pm_res.data or []

#     st.subheader("Users who can work on this project")
#     if members:
#         for m in members:
#             st.write(f"- {id_to_email.get(m['user_id'], 'Unknown')}")
#     else:
#         st.write("No users assigned.")

#     # --- Load boundary using your working function ---
#     boundary, bounds = load_project_boundary(selected)

#     st.subheader("Project Area")

#     # --- Create map ---
#     m = folium.Map(location=[52.37, 4.90], zoom_start=12, zoom_control=True)

#     # Basemaps
#     folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)

#     # Add polygon if exists
#     if boundary:
#         folium.GeoJson(
#             boundary,
#             name="Boundary",
#             style_function=lambda x: {
#                 "fillColor": "#ffcc00",
#                 "color": "red",
#                 "weight": 2.5,
#                 "fillOpacity": 0.1,
#             }
#         ).add_to(m)

#     # Fit to bounds if valid
#     if bounds:
#         try:
#             m.fit_bounds(bounds)
#         except:
#             pass

#     # --- Render map ---
#     with st.container():
#         st_folium(m, height=500, use_container_width=True)

#     # --- Edit Users Section ---
#     st.markdown("---")
#     st.subheader("Edit Users")

#     all_user_emails = list(email_to_id.keys())

#     current_user_ids = [m["user_id"] for m in members]
#     current_user_emails = [
#         id_to_email.get(uid) for uid in current_user_ids if uid in id_to_email
#     ]

#     new_selection = st.multiselect(
#         "Select users for this project",
#         all_user_emails,
#         default=current_user_emails
#     )

#     if st.button("Save User Changes"):
#         try:
#             # Remove all existing users
#             supabase.table("project_members").delete().eq("project", selected).execute()

#             # Add new users
#             for email in new_selection:
#                 supabase.table("project_members").insert(
#                     {"project": selected, "user_id": email_to_id[email]}
#                 ).execute()

#             st.success("Users updated.")
#             st.rerun()

#         except Exception as e:
#             st.error(f"Error updating users: {e}")

#     # ---------------------------------------------------------
#     #   DELETE PROJECT
#     # ---------------------------------------------------------
#     st.markdown("---")

#     if st.button("DELETE PROJECT", type="primary"):
#         confirm_delete_dialog(selected)

#     # ---------------------------------------------------------
#     #   DOWNLOAD REPORTS + OBSERVATIONS
#     # ---------------------------------------------------------
#     st.markdown("---")
#     st.subheader("Download Data")

#     # --- Download Reports ---
#     try:
#         report_res = (
#             supabase.table("report")
#             .select("*")
#             .eq("project", selected)
#             .order("date", desc=True)
#             .execute()
#         )
#         report_df = pd.DataFrame(report_res.data or [])
#     except Exception as e:
#         report_df = pd.DataFrame()
#         st.error(f"Error loading reports: {e}")

#     st.download_button(
#         label="Download Reports (CSV)",
#         data=report_df.to_csv(index=False).encode("utf-8"),
#         file_name=f"{selected}_reports.csv",
#         mime="text/csv",
#         icon=":material/sim_card_download:"
#     )

#     # --- Download Observations ---
#     try:
#         obs_res = (
#             supabase.table("observations")
#             .select("*")
#             .eq("project", selected)
#             .order("date", desc=True)
#             .execute()
#         )
#         obs_df = pd.DataFrame(obs_res.data or [])
#     except Exception as e:
#         obs_df = pd.DataFrame()
#         st.error(f"Error loading observations: {e}")

#     st.download_button(
#         label="Download Observations (CSV)",
#         data=obs_df.to_csv(index=False).encode("utf-8"),
#         file_name=f"{selected}_observations.csv",
#         mime="text/csv",
#         icon=":material/download:"
#     )

# ---------------------------
# PAGE 2 — VIEW PROJECTS (store geojson as file, replace old)
# ---------------------------
elif page == "View Projects":
    import json
    import io
    import folium
    from folium.plugins import Draw
    from streamlit_folium import st_folium
    import pandas as pd
    import streamlit as st

    st.title("View Projects")

    # --- Load all projects ---
    proj_res = supabase.table("projects").select("*").execute()
    projects = proj_res.data or []

    if not projects:
        st.info("No projects found.")
        st.stop()

    project_names = [p["name"] for p in projects]
    selected = st.selectbox(
        "Select a project",
        project_names,
        index=None,
        placeholder="Select a project...",
    )

    if not selected:
        st.stop()

    # Current project data
    project = next(p for p in projects if p["name"] == selected)

    st.subheader("Project Info")
    st.write(f"**Name:** {project.get('name')}")
    st.write(f"**Description:** {project.get('description', '')}")

    # --- Load all users from Supabase ---
    try:
        users = supabase.rpc("get_all_users").execute().data or []
    except Exception:
        users = []

    id_to_email = {u["id"]: u["email"] for u in users}
    email_to_id = {u["email"]: u["id"] for u in users}

    # --- Load project members ---
    pm_res = (
        supabase.table("project_members")
        .select("*")
        .eq("project", selected)
        .execute()
    )
    members = pm_res.data or []

    st.subheader("Users who can work on this project")
    if members:
        for m in members:
            st.write(f"- {id_to_email.get(m['user_id'], 'Unknown')}")
    else:
        st.write("No users assigned.")

    # --- Load boundary file path from project_boundaries (if any) ---
    # We expect project_boundaries to store the file path to the geojson in storage
    try:
        pb_res = supabase.table("project_boundaries").select("*").eq("project", selected).execute()
        pb_rows = pb_res.data or []
        existing_file_path = pb_rows[0].get("file_path") if pb_rows else None
    except Exception:
        existing_file_path = None

    # If there is an existing file, try to fetch and display it as GeoJSON on the map
    existing_boundary_feature = None
    bounds = None
    if existing_file_path:
        try:
            # Download file bytes from storage
            download_res = supabase.storage.from_("project-geojsons").download(existing_file_path)
            if download_res:
                # download_res is bytes-like; decode and parse
                geojson_text = download_res.decode("utf-8") if isinstance(download_res, (bytes, bytearray)) else download_res
                existing_boundary_feature = json.loads(geojson_text)
                # compute bounds if polygon present (simple bounding box)
                try:
                    coords = existing_boundary_feature.get("geometry", {}).get("coordinates", [])
                    # handle Polygon or MultiPolygon
                    flat_coords = []
                    if existing_boundary_feature.get("geometry", {}).get("type") == "Polygon":
                        for ring in coords:
                            flat_coords.extend(ring)
                    elif existing_boundary_feature.get("geometry", {}).get("type") == "MultiPolygon":
                        for poly in coords:
                            for ring in poly:
                                flat_coords.extend(ring)
                    if flat_coords:
                        lats = [pt[1] for pt in flat_coords]
                        lons = [pt[0] for pt in flat_coords]
                        bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
                except Exception:
                    bounds = None
        except Exception:
            existing_boundary_feature = None
            bounds = None

    st.subheader("Project Area")

    # -------------------------
    # Helpers: sanitize geometry and convert types
    # -------------------------
    def _to_native(obj):
        if isinstance(obj, dict):
            return {str(k): _to_native(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_native(v) for v in obj]
        if hasattr(obj, "item"):
            try:
                return obj.item()
            except Exception:
                pass
        return obj

    def build_feature_from_shape(shape):
        if not shape or not isinstance(shape, dict):
            return None
        # FeatureCollection -> take first feature
        if shape.get("type") == "FeatureCollection":
            features = shape.get("features", [])
            if not features:
                return None
            feat = features[0]
            geom = feat.get("geometry")
            if not geom:
                return None
            return {"type": "Feature", "properties": feat.get("properties", {}), "geometry": _to_native(geom)}
        # Feature with geometry
        if shape.get("type") == "Feature" and "geometry" in shape:
            geom = shape.get("geometry")
            if not geom:
                return None
            return {"type": "Feature", "properties": shape.get("properties", {}), "geometry": _to_native(geom)}
        # Geometry-like dict
        if "type" in shape and "coordinates" in shape:
            geom = {"type": shape["type"], "coordinates": shape["coordinates"]}
            return {"type": "Feature", "properties": {}, "geometry": _to_native(geom)}
        # Nested geometry under 'geometry'
        geom = shape.get("geometry")
        if geom and isinstance(geom, dict) and "type" in geom and "coordinates" in geom:
            return {"type": "Feature", "properties": shape.get("properties", {}), "geometry": _to_native(geom)}
        return None

    # -------------------------
    # Create map and layers
    # -------------------------
    m = folium.Map(location=[52.37, 4.90], zoom_start=12, zoom_control=True)

    # Basemaps
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    folium.TileLayer(
        tiles="http://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Satellite",
        name="Google Satellite",
        overlay=False,
        control=True,
    ).add_to(m)

    # Add existing polygon if exists
    if existing_boundary_feature:
        try:
            folium.GeoJson(
                _to_native(existing_boundary_feature),
                name="Boundary",
                style_function=lambda x: {
                    "fillColor": "#ffcc00",
                    "color": "red",
                    "weight": 2.5,
                    "fillOpacity": 0.1,
                },
            ).add_to(m)
        except Exception:
            pass

    # Fit to bounds if valid
    if bounds:
        try:
            m.fit_bounds(bounds)
        except Exception:
            pass

    # Draw / edit tools
    draw = Draw(
        draw_options={
            "polyline": False,
            "rectangle": True,
            "polygon": True,
            "circle": False,
            "marker": False,
            "circlemarker": False,
        },
        edit_options={"edit": True, "remove": True},
    )
    draw.add_to(m)

    folium.LayerControl().add_to(m)

    # -------------------------
    # Render map and capture edits (debugging output included)
    # -------------------------
    map_data = st_folium(
        m,
        height=650,
        use_container_width=True,
        returned_objects=["all_drawings", "last_active_drawing"],
    )

    # Debug: show raw map_data so you can inspect what Leaflet returned
    st.subheader("Debug: raw map_data from st_folium")
    st.write(map_data)
    st.markdown("---")

    # Build sanitized GeoJSON Feature from the drawing
    new_polygon_feature = None
    if map_data:
        shape = map_data.get("last_active_drawing") or None
        if not shape:
            drawings = map_data.get("all_drawings", [])
            if drawings:
                shape = drawings[-1]
        st.subheader("Debug: selected raw shape")
        st.write(shape)
        new_polygon_feature = build_feature_from_shape(shape) if shape else None
        st.subheader("Debug: sanitized GeoJSON Feature (what will be uploaded)")
        st.write(new_polygon_feature)
        if new_polygon_feature:
            st.json(new_polygon_feature)

    st.markdown(
        "Draw or edit the project area. When you're happy, click **Save Area** to upload the GeoJSON file and replace the old one."
    )

    # -------------------------
    # Save Area button: upload file to Supabase Storage and update project_boundaries.file_path
    # -------------------------
    if st.button("Save Area"):
        # Choose geometry to save: new drawn feature if present, otherwise existing boundary loaded from file
        geometry_to_save = new_polygon_feature if new_polygon_feature is not None else existing_boundary_feature

        if geometry_to_save is None:
            st.error("No polygon found. Please draw a project area first.")
        else:
            try:
                # Validate and serialize
                if not isinstance(geometry_to_save, dict):
                    raise ValueError("Geometry is not a dict")
                if geometry_to_save.get("type") != "Feature" or "geometry" not in geometry_to_save:
                    raise ValueError("Geometry must be a GeoJSON Feature with a geometry member")
                geom = geometry_to_save["geometry"]
                if not isinstance(geom, dict) or "type" not in geom or "coordinates" not in geom:
                    raise ValueError("Feature.geometry must contain type and coordinates")

                geometry_to_save = _to_native(geometry_to_save)
                geojson_text = json.dumps(geometry_to_save)

                # Prepare file path and bytes
                # We'll store files under a folder named by project, filename project.geojson
                bucket_name = "project-geojsons"   # change if your bucket name differs
                file_path = f"{selected}/{selected}.geojson"  # e.g., "MyProject/MyProject.geojson"
                file_bytes = io.BytesIO(geojson_text.encode("utf-8"))

                # If an old file exists, delete it first (optional)
                if existing_file_path and existing_file_path != file_path:
                    try:
                        supabase.storage.from_(bucket_name).remove([existing_file_path])
                        st.write(f"Deleted old file: {existing_file_path}")
                    except Exception as e_del:
                        # Not fatal; continue to upload new file
                        st.write(f"Warning: could not delete old file: {e_del}")

                # Upload new file (upsert behavior)
                # supabase-py upload signature: storage.from_(bucket).upload(path, file, content_type=..., upsert=True)
                try:
                    upload_res = supabase.storage.from_(bucket_name).upload(
                        file_path,
                        file_bytes,
                        content_type="application/geo+json",
                        upsert=True
                    )
                    st.write("Upload response:", upload_res)
                except Exception as e_upload:
                    # Some supabase clients return bytes on download but raise on upload; show error
                    st.error(f"Upload failed: {e_upload}")
                    raise

                # Optionally make the file public and get public URL (if your bucket is private, skip or generate signed URL)
                try:
                    # Make public (if your bucket policy allows)
                    supabase.storage.from_(bucket_name).update_public(file_path)
                except Exception:
                    # update_public may not be available or allowed; ignore
                    pass

                try:
                    public_url = supabase.storage.from_(bucket_name).get_public_url(file_path).get("publicURL")
                except Exception:
                    public_url = None

                # Update project_boundaries table to point to the new file path
                # If a row exists, update file_path; otherwise insert
                try:
                    existing = supabase.table("project_boundaries").select("*").eq("project", selected).execute()
                    existing_rows = existing.data or []
                    if existing_rows:
                        res = supabase.table("project_boundaries").update(
                            {"file_path": file_path, "file_url": public_url}
                        ).eq("project", selected).execute()
                    else:
                        res = supabase.table("project_boundaries").insert(
                            {"project": selected, "file_path": file_path, "file_url": public_url}
                        ).execute()
                    st.write("DB update response:", res)
                    st.success("GeoJSON file uploaded and project boundary record updated. Reports and observations remain linked to the project.")
                except Exception as e_db:
                    st.error(f"Failed to update project_boundaries table: {e_db}")
                    st.write("Uploaded file remains in storage at:", file_path)
            except Exception as ex:
                st.error(f"Error preparing or uploading GeoJSON: {ex}")

    # -------------------------
    # Edit Users Section
    # -------------------------
    st.markdown("---")
    st.subheader("Edit Users")

    all_user_emails = list(email_to_id.keys())

    current_user_ids = [m["user_id"] for m in members]
    current_user_emails = [
        id_to_email.get(uid) for uid in current_user_ids if uid in id_to_email
    ]

    new_selection = st.multiselect(
        "Select users for this project",
        all_user_emails,
        default=current_user_emails,
    )

    if st.button("Save User Changes"):
        try:
            supabase.table("project_members").delete().eq("project", selected).execute()
            for email in new_selection:
                supabase.table("project_members").insert(
                    {"project": selected, "user_id": email_to_id[email]}
                ).execute()
            st.success("Users updated.")
            st.rerun()
        except Exception as e:
            st.error(f"Error updating users: {e}")

    # -------------------------
    # DELETE PROJECT
    # -------------------------
    st.markdown("---")
    if st.button("DELETE PROJECT", type="primary"):
        confirm_delete_dialog(selected)

    # -------------------------
    # DOWNLOAD REPORTS + OBSERVATIONS
    # -------------------------
    st.markdown("---")
    st.subheader("Download Data")

    # --- Download Reports ---
    try:
        report_res = (
            supabase.table("report")
            .select("*")
            .eq("project", selected)
            .order("date", desc=True)
            .execute()
        )
        report_df = pd.DataFrame(report_res.data or [])
    except Exception as e:
        report_df = pd.DataFrame()
        st.error(f"Error loading reports: {e}")

    st.download_button(
        label="Download Reports (CSV)",
        data=report_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected}_reports.csv",
        mime="text/csv",
        icon=":material/sim_card_download:",
    )

    # --- Download Observations ---
    try:
        obs_res = (
            supabase.table("observations")
            .select("*")
            .eq("project", selected)
            .order("date", desc=True)
            .execute()
        )
        obs_df = pd.DataFrame(obs_res.data or [])
    except Exception as e:
        obs_df = pd.DataFrame()
        st.error(f"Error loading observations: {e}")

    st.download_button(
        label="Download Observations (CSV)",
        data=obs_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected}_observations.csv",
        mime="text/csv",
        icon=":material/download:",
    )
