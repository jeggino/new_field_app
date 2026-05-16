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
# PAGE 2 — VIEW PROJECTS
# ---------------------------
elif page == "View Projects":
    import json
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

    # --- Load boundary using your helper (must return GeoJSON Feature or None) ---
    # boundary: GeoJSON Feature or None
    # bounds: [[min_lat, min_lon], [max_lat, max_lon]] or None
    boundary, bounds = load_project_boundary(selected)

    st.subheader("Project Area")

    # -------------------------
    # Helpers: sanitize geometry and convert types
    # -------------------------
    def _to_native(obj):
        """
        Convert numpy types and other non-JSON-native types to Python native types.
        """
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
        """
        Accepts a Leaflet/Draw returned shape and returns a valid GeoJSON Feature
        or None if invalid. Handles FeatureCollection, Feature, geometry dicts,
        and nested geometry under 'geometry'.
        """
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

        # Geometry-like dict (has type and coordinates)
        if "type" in shape and "coordinates" in shape:
            geom = {"type": shape["type"], "coordinates": shape["coordinates"]}
            return {"type": "Feature", "properties": {}, "geometry": _to_native(geom)}

        # Nested geometry under 'geometry'
        geom = shape.get("geometry")
        if geom and isinstance(geom, dict) and "type" in geom and "coordinates" in geom:
            return {"type": "Feature", "properties": shape.get("properties", {}), "geometry": _to_native(geom)}

        # No valid geometry found
        return None

    # -------------------------
    # Create map and layers
    # -------------------------
    m = folium.Map(location=[52.37, 4.90], zoom_start=12, zoom_control=True)

    # Basemaps
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    # Google Satellite (unofficial tile) - replace if you prefer another provider
    folium.TileLayer(
        tiles="http://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Satellite",
        name="Google Satellite",
        overlay=False,
        control=True,
    ).add_to(m)

    # Add existing polygon if exists (boundary expected to be a Feature)
    if boundary:
        try:
            folium.GeoJson(
                _to_native(boundary),
                name="Boundary",
                style_function=lambda x: {
                    "fillColor": "#ffcc00",
                    "color": "red",
                    "weight": 2.5,
                    "fillOpacity": 0.1,
                },
            ).add_to(m)
        except Exception:
            # If boundary is malformed, ignore rendering but keep it for saving fallback
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

    # Try to get the most reliable shape:
    # 1) last_active_drawing (preferred)
    # 2) last element of all_drawings
    # 3) fallback to None
    new_polygon_feature = None
    if map_data:
        st.subheader("Debug: last_active_drawing")
        st.write(map_data.get("last_active_drawing"))
        st.subheader("Debug: all_drawings (full list)")
        st.write(map_data.get("all_drawings", []))

        shape = map_data.get("last_active_drawing") or None
        if not shape:
            drawings = map_data.get("all_drawings", [])
            if drawings:
                shape = drawings[-1]

        st.subheader("Debug: selected raw shape")
        st.write(shape)

        # Build sanitized GeoJSON Feature and show it
        new_polygon_feature = build_feature_from_shape(shape) if shape else None
        st.subheader("Debug: sanitized GeoJSON Feature (what will be saved)")
        st.write(new_polygon_feature)
        if new_polygon_feature:
            st.json(new_polygon_feature)

    st.markdown(
        "You can draw, edit, or delete the project area. When you're happy, click **Save Area**. "
        "The debug panels above show exactly what will be sent to Supabase."
    )

    # -------------------------
    # Save Area button (safe replace logic)
    # -------------------------
    if st.button("Save Area"):
        # Choose geometry to save: new drawn feature if present, otherwise existing boundary
        geometry_to_save = new_polygon_feature if new_polygon_feature is not None else boundary

        if geometry_to_save is None:
            st.error("No polygon found. Please draw a project area first.")
        else:
            # Final validation and serialization check
            try:
                # Ensure geometry_to_save is a dict and a GeoJSON Feature
                if not isinstance(geometry_to_save, dict):
                    raise ValueError("Geometry is not a dict")

                if geometry_to_save.get("type") != "Feature" or "geometry" not in geometry_to_save:
                    raise ValueError("Geometry must be a GeoJSON Feature with a geometry member")

                geom = geometry_to_save["geometry"]
                if not isinstance(geom, dict) or "type" not in geom or "coordinates" not in geom:
                    raise ValueError("Feature.geometry must contain type and coordinates")

                # Convert to native Python types (lists, floats)
                geometry_to_save = _to_native(geometry_to_save)

                # Quick JSON dump to catch serialization issues early
                json_text = json.dumps(geometry_to_save)

                # Debug: show the JSON that will be sent (first 2000 chars)
                st.subheader("Debug: JSON payload to be sent to Supabase (truncated)")
                st.code(json_text[:2000] + ("..." if len(json_text) > 2000 else ""), language="json")

            except Exception as ex:
                st.error(f"Invalid geometry: {ex}")
            else:
                # Attempt to replace existing boundary row (UPDATE) or INSERT if none exists
                try:
                    existing = supabase.table("project_boundaries").select("*").eq("project", selected).execute()
                    existing_rows = existing.data or []

                    if existing_rows:
                        # Update the existing row (replace geometry only)
                        res = supabase.table("project_boundaries").update(
                            {"geometry": geometry_to_save}
                        ).eq("project", selected).execute()
                    else:
                        # Insert new row
                        res = supabase.table("project_boundaries").insert(
                            {"project": selected, "geometry": geometry_to_save}
                        ).execute()

                    # Show Supabase response for debugging
                    st.subheader("Supabase response (jsonb path)")
                    st.write(res)

                    # If Supabase returns an error structure, show it
                    if isinstance(res, dict) and res.get("error"):
                        st.error(f"Supabase error: {res.get('error')}")
                    else:
                        st.success("Project area updated successfully. Existing reports and observations remain linked to this project.")
                except Exception as e_jsonb:
                    # If jsonb path fails, show error and attempt PostGIS RPC path (if available)
                    st.error(f"jsonb update/insert failed: {e_jsonb}")
                    st.write("Attempting PostGIS RPC path (if you have a server-side RPC to accept GeoJSON).")

                    # Example RPC approach (requires a server-side function)
                    # You must create a Postgres function like:
                    # CREATE OR REPLACE FUNCTION update_project_boundary_geom(p_project text, p_geojson jsonb) RETURNS void AS $$
                    # BEGIN
                    #   UPDATE project_boundaries
                    #   SET geom = ST_SetSRID(ST_GeomFromGeoJSON(p_geojson::text), 4326)
                    #   WHERE project = p_project;
                    #   IF NOT FOUND THEN
                    #     INSERT INTO project_boundaries(project, geom) VALUES (p_project, ST_SetSRID(ST_GeomFromGeoJSON(p_geojson::text), 4326));
                    #   END IF;
                    # END;
                    # $$ LANGUAGE plpgsql;
                    try:
                        geojson_text = json.dumps(geometry_to_save)
                        rpc_res = supabase.rpc("update_project_boundary_geom", {"p_project": selected, "p_geojson": geojson_text}).execute()
                        st.subheader("Supabase RPC response (PostGIS path)")
                        st.write(rpc_res)
                        st.success("Boundary saved via PostGIS RPC. Reports/observations unchanged.")
                    except Exception as e_rpc:
                        st.error("PostGIS RPC path failed as well.")
                        st.write("jsonb error:", e_jsonb)
                        st.write("rpc error:", e_rpc)
                        st.error("Both jsonb and PostGIS save attempts failed. Inspect the debug JSON above and paste it here for further help.")

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
        obs_df = pd.DataFrame(obs_res.data or []
        )
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
