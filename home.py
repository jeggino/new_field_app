import streamlit as st
from streamlit_folium import st_folium
import folium
import json
from supabase import create_client
from folium.plugins import Geocoder, Fullscreen, Draw
import pandas as pd
import altair as alt
import geopandas as gpd
from folium.plugins.pattern import StripePattern
from folium.plugins.pattern import CirclePattern
import re
from openpyxl.workbook import Workbook



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


def dagverslagen_overview():
    st.set_page_config(layout="wide")
    st.title("Projectoverzicht")

    # --- Fetch data ---
    projects = supabase.table("projects").select("*").execute().data
    reports = supabase.table("report").select("*").execute().data
    observations = supabase.table("observations").select("*").execute().data

    df_projects = pd.DataFrame(projects)
    df_reports = pd.DataFrame(reports)
    df_obs = pd.DataFrame(observations)

    # --- Clean report type ---
    df_reports["report_type"] = (
        df_reports["kind"]
        .str.replace(r"\s*\(.*?\)", "", regex=True)
        .str.strip()
    )

    # --- Count reports per project + type ---
    report_counts = (
        df_reports.groupby(["project", "report_type"])
        .size()
        .reset_index(name="count")
    )

    # --- Merge so ALL projects appear ---
    merged = df_projects.merge(
        report_counts,
        left_on="name",
        right_on="project",
        how="left"
    )

    merged["count"] = merged["count"].fillna(0).astype(int)
    merged["total_reports"] = merged.groupby("name")["count"].transform("sum")
    merged = merged.sort_values("total_reports", ascending=False)

    # --- Tabs ---
    tab1, tab2 = st.tabs([
        "📘 Aantal dagverslagen per project (per soort verslag)",
        "🪺 Nest & Verblijfplaats Overzicht per Project"
    ])

    # ---------------------------------------------------------
    # TAB 1 — DAGVERSLAGEN
    # ---------------------------------------------------------
    with tab1:
        st.subheader("Aantal dagverslagen per project (per soort verslag)")
    
        # Replace underscores in project names
        merged["name_clean"] = merged["name"].str.replace("_", " ")
    
        # Create single-line details text: entries separated by " | "
        report_details = (
            df_reports
            .sort_values("date")
            .groupby(["project", "report_type"])
            .apply(lambda x: " | ".join([
                f"{row['kind']} : {pd.to_datetime(row['date']).strftime('%d %B %Y')}"
                for _, row in x.iterrows()
            ]))
            .reset_index(name="details_text")
        )
    
        # Merge into main dataset
        merged_with_details = merged.merge(
            report_details,
            left_on=["name", "report_type"],
            right_on=["project", "report_type"],
            how="left"
        )
    
        # Use cleaned project name
        merged_with_details["project_display"] = merged_with_details["name_clean"]
    
        chart1 = (
            alt.Chart(merged_with_details)
            .mark_bar()
            .encode(
                y=alt.Y("project_display:N", title="Project", sort='-x'),
                x=alt.X("count:Q", title="Aantal dagverslagen", stack="zero"),
                color=alt.Color("report_type:N", title="Soort verslag"),
                tooltip=[
                    alt.Tooltip("project_display:N", title="Project"),
                    alt.Tooltip("details_text:N", title="Details dagverslagen")
                ]
            )
            .properties(
                height=max(300, len(merged["name"].unique()) * 28),
                width="container"
            )
        )
    
        st.altair_chart(chart1, use_container_width=True)
    
        # --- DOWNLOAD REPORTS ---
        st.markdown("---")
        st.subheader("Download dagverslagen")
    
        report_df = pd.DataFrame(reports)
    
        st.download_button(
            label="Download alle dagverslagen (CSV)",
            data=report_df.to_csv(index=False).encode("utf-8"),
            file_name="alle_dagverslagen.csv",
            mime="text/csv",
        )




    # ---------------------------------------------------------
    # TAB 2 — NEST & VERBLIJFPLAATS
    # ---------------------------------------------------------
    with tab2:
    
        st.subheader("Nest & Verblijfplaats Overzicht per Project")
    
        # Only projects with observations
        projects_with_obs = sorted(df_obs["project"].dropna().unique())
    
        if len(projects_with_obs) == 0:
            st.info("Geen nest- of verblijfplaatsdata beschikbaar.")
            return
    
        # Clean project names
        df_obs["project_clean"] = df_obs["project"].str.replace("_", " ")
    
        # --- FUNCTION FILTER ---
        st.markdown("### Filter op functie")
    
        available_functions = sorted(df_obs["function"].dropna().unique())
        selected_function = st.selectbox(
            "Kies een functie…",
            ["-- Kies een functie --"] + available_functions
        )
    
        # Only show table if a real function is selected
        if selected_function != "-- Kies een functie --":
    
            df_filtered = df_obs[df_obs["function"] == selected_function]
    
            # --- PIVOT TABLE: PROJECT_CLEAN × SPECIES ---
            pivot_table = (
                df_filtered
                .groupby(["project_clean", "species"])
                .size()
                .reset_index(name="count")
                .pivot(index="project_clean", columns="species", values="count")
            )
    
            # Replace NaN with "–"
            pivot_table = pivot_table.fillna("–")
    
            # Convert numeric values to int (no floats)
            for col in pivot_table.columns:
                pivot_table[col] = pivot_table[col].map(
                    lambda x: int(x) if isinstance(x, (int, float)) else x
                )
    
            # Remove index name "project_clean"
            pivot_table.index.name = None
    
            st.markdown("### Overzicht per project en soort")
            st.dataframe(pivot_table, use_container_width=True)
    
        # Separator before chart
        st.markdown("---")
    
        # --- ORIGINAL CHART (STAYS BELOW) ---
    
        # Count per project + function
        obs_counts = (
            df_obs.groupby(["project_clean", "function"])
            .size()
            .reset_index(name="count")
        )
    
        # Species breakdown
        species_summary = (
            df_obs.groupby(["project_clean", "function", "species"])
            .size()
            .reset_index(name="count")
        )
    
        # Combine species into tooltip text
        species_text = (
            species_summary
            .groupby(["project_clean", "function"])
            .apply(lambda x: "\n".join([
                f"• {row['species']} : {row['count']}"
                for _, row in x.iterrows()
            ]))
            .reset_index(name="species_info")
        )
    
        obs_counts = obs_counts.merge(species_text, on=["project_clean", "function"], how="left")
    
        chart2 = (
            alt.Chart(obs_counts)
            .mark_bar()
            .encode(
                y=alt.Y("project_clean:N", title="Project", sort='-x'),
                x=alt.X("count:Q", title="Aantal", stack="zero"),
                color=alt.Color("function:N", title="Functie"),
                tooltip=[
                    alt.Tooltip("project_clean:N", title="Project"),
                    alt.Tooltip("function:N", title="Functie"),
                    alt.Tooltip("count:Q", title="Aantal", format="d"),
                    alt.Tooltip("species_info:N", title="Soorten", format="")
                ]
            )
            .properties(
                height=max(300, len(obs_counts["project_clean"].unique()) * 28),
                width="container"
            )
        )
    
        st.altair_chart(chart2, use_container_width=True)
    
        # --- DOWNLOAD OBSERVATIONS ---
        st.markdown("---")
        st.subheader("Download observaties")
    
        obs_df = pd.DataFrame(observations)
    
        st.download_button(
            label="Download alle observaties (CSV)",
            data=obs_df.to_csv(index=False).encode("utf-8"),
            file_name="alle_observaties.csv",
            mime="text/csv",
        )











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
st.set_page_config(layout="wide")
page = st.sidebar.radio("Navigation", ["Create Project", "View Projects","Gegenereerde output"])
#"HTML-generator","Projectoverzicht",
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
    m = folium.Map(location=[52.37, 4.90], zoom_start=12, zoom_control=True,tiles=None)

    tiles = 'https://api.mapbox.com/styles/v1/jeggino/cmn7ms1u3001f01pl691k0eyu/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoiamVnZ2lubyIsImEiOiJjbHdscmRkZHAxMTl1MmlyeTJpb3Z2eHdzIn0.N9TRN7xxTikk235dVs1YeQ'
    folium.TileLayer(tiles=tiles,
                     attr='XXX Mapbox Attribution',
                         max_zoom=24,
        max_native_zoom=22,
        overlay=False,
        control=False,name="OpenStreetMap").add_to(m)
    
    
    # Satellite
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        max_native_zoom=21,
        max_zoom=21,
        overlay=False,
        control=False
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
                      "polyline": False, "rectangle": True},
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    Fullscreen(position="topleft").add_to(m)

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






# ---------------------------------------------------------
# PAGE 2 — VIEW PROJECTS (GeoJSON stored in observation_photos bucket)
# ---------------------------------------------------------
elif page == "View Projects":
    import json
    import io
    import os
    import tempfile
    import folium
    from folium.plugins import Draw
    from streamlit_folium import st_folium
    import pandas as pd
    import streamlit as st

    BUCKET_NAME = "observation_photos"   # your bucket

    st.title("View Projects")

    # ---------------------------------------------------------
    # LOAD PROJECTS
    # ---------------------------------------------------------
    proj_res = supabase.table("projects").select("*").execute()
    projects = proj_res.data or []

    if not projects:
        st.info("No projects found.")
        st.stop()

    project_names = [p["name"] for p in projects]
    selected = st.selectbox("Select a project", project_names)

    if not selected:
        st.stop()

    project = next(p for p in projects if p["name"] == selected)

    st.subheader("Project Info")
    st.write(f"**Name:** {project['name']}")
    st.write(f"**Description:** {project.get('description', '')}")

    # ---------------------------------------------------------
    # LOAD USERS
    # ---------------------------------------------------------
    try:
        users = supabase.rpc("get_all_users").execute().data or []
    except Exception:
        users = []

    id_to_email = {u["id"]: u["email"] for u in users}
    email_to_id = {u["email"]: u["id"] for u in users}

    pm_res = supabase.table("project_members").select("*").eq("project", selected).execute()
    members = pm_res.data or []

    st.subheader("Users who can work on this project")
    if members:
        for m in members:
            st.write(f"- {id_to_email.get(m['user_id'], 'Unknown')}")
    else:
        st.write("No users assigned.")

    # ---------------------------------------------------------
    # LOAD EXISTING GEOJSON FILE FROM STORAGE
    # ---------------------------------------------------------
    file_path = f"{selected}.geojson"   # naming convention

    existing_boundary_feature = None
    bounds = None

    try:
        download_res = supabase.storage.from_(BUCKET_NAME).download(file_path)
        if download_res:
            geojson_text = (
                download_res.decode("utf-8")
                if isinstance(download_res, (bytes, bytearray))
                else download_res
            )
            existing_boundary_feature = json.loads(geojson_text)

            # compute bounds
            geom = existing_boundary_feature.get("geometry", {})
            coords = geom.get("coordinates", [])
            flat = []
            if geom.get("type") == "Polygon":
                for ring in coords:
                    flat.extend(ring)
            elif geom.get("type") == "MultiPolygon":
                for poly in coords:
                    for ring in poly:
                        flat.extend(ring)
            if flat:
                lats = [pt[1] for pt in flat]
                lons = [pt[0] for pt in flat]
                bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
    except Exception:
        existing_boundary_feature = None
        bounds = None

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # CREATE MAP
    # ---------------------------------------------------------
    m = folium.Map(location=[52.37, 4.90], zoom_start=12,tiles = None)

    tiles = 'https://api.mapbox.com/styles/v1/jeggino/cmn7ms1u3001f01pl691k0eyu/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoiamVnZ2lubyIsImEiOiJjbHdscmRkZHAxMTl1MmlyeTJpb3Z2eHdzIn0.N9TRN7xxTikk235dVs1YeQ'
    folium.TileLayer(tiles=tiles,
                     attr='XXX Mapbox Attribution',
                         max_zoom=24,
        max_native_zoom=22,
        overlay=False,
        control=False,name="OpenStreetMap").add_to(m)
    
    
    # Satellite
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        max_native_zoom=21,
        max_zoom=21,
        overlay=False,
        control=False
    ).add_to(m)

    if existing_boundary_feature:
        folium.GeoJson(
            existing_boundary_feature,
            name="Boundary",
            style_function=lambda x: {
                "fillColor": "#ffcc00",
                "color": "red",
                "weight": 2.5,
                "fillOpacity": 0.1,
            },
        ).add_to(m)

    if bounds:
        m.fit_bounds(bounds)

    Draw(
        draw_options={
            "polyline": False,
            "rectangle": True,
            "polygon": True,
            "circle": False,
            "marker": False,
            "circlemarker": True,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    Fullscreen(position="topleft").add_to(m)

    folium.LayerControl().add_to(m)

    # ---------------------------------------------------------
    # CAPTURE DRAWINGS
    # ---------------------------------------------------------
    map_data = st_folium(m, height=500, use_container_width=True)

    if "last_drawings" not in st.session_state:
        st.session_state["last_drawings"] = []

    if map_data and "all_drawings" in map_data:
        st.session_state["last_drawings"] = map_data["all_drawings"]

    polygon_geojson = None
    drawings = st.session_state["last_drawings"]

    if drawings:
        polygons = []

        for d in drawings:
            geom = d.get("geometry", {})
            if geom.get("type") == "Polygon":
                polygons.append(geom["coordinates"])
            elif geom.get("type") == "MultiPolygon":
                polygons.extend(geom["coordinates"])

        # MULTIPOLYGON CHECK
        if len(polygons) > 1:
            polygon_geojson = {
                "type": "Feature",
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
            }
        else:
            polygon_geojson = {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": polygons[0]},
            }

    # ---------------------------------------------------------
    # SAVE AREA — OVERWRITE GEOJSON FILE IN STORAGE
    # ---------------------------------------------------------
    if st.button("Save Area"):
        geometry_to_save = polygon_geojson or existing_boundary_feature

        if geometry_to_save is None:
            st.error("No polygon found. Draw a project area first.")
        else:
            try:
                # Serialize
                geometry_to_save = _to_native(geometry_to_save)
                geojson_text = json.dumps(geometry_to_save, indent=2)

                # Write to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as tmp:
                    tmp.write(geojson_text.encode("utf-8"))
                    tmp_path = tmp.name

                # Delete old file
                try:
                    supabase.storage.from_(BUCKET_NAME).remove([file_path])
                except Exception:
                    pass

                # Upload new file
                upload_res = supabase.storage.from_(BUCKET_NAME).upload(
                    file_path,
                    tmp_path
                )

                os.remove(tmp_path)

                st.success("GeoJSON saved. Old file replaced. Reports & observations remain linked.")

            except Exception as ex:
                st.error(f"Error saving GeoJSON: {ex}")

    # ---------------------------------------------------------
    # EDIT USERS
    # ---------------------------------------------------------
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
        supabase.table("project_members").delete().eq("project", selected).execute()
        for email in new_selection:
            supabase.table("project_members").insert(
                {"project": selected, "user_id": email_to_id[email]}
            ).execute()
        st.success("Users updated.")
        st.rerun()

    # ---------------------------------------------------------
    # DOWNLOAD REPORTS + OBSERVATIONS
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("Download Data")

    # Reports
    report_res = supabase.table("report").select("*").eq("project", selected).order("date", desc=True).execute()
    report_df = pd.DataFrame(report_res.data or [])

    # st.download_button(
    #     label="Download Reports (CSV)",
    #     data=report_df.to_csv(index=False).encode("utf-8"),
    #     file_name=f"{selected}_reports.csv",
    #     mime="text/csv",
    # )

    # Observations
    obs_res = supabase.table("observations").select("*").eq("project", selected).order("date", desc=True).execute()
    obs_df = pd.DataFrame(obs_res.data or [])

    # st.download_button(
    #     label="Download Observations (CSV)",
    #     data=obs_df.to_csv(index=False).encode("utf-8"),
    #     file_name=f"{selected}_observations.csv",
    #     mime="text/csv",
    # )

    
    # Path inside the bucket
    # Download file from storage
    boundary_path = f"{selected}.geojson"
    try:
        boundary_file = supabase.storage.from_(BUCKET).download(boundary_path)
    
        st.download_button(
            label="Download Boundary (GeoJSON)",
            data=boundary_file,
            file_name=f"{selected}_boundary.geojson",
            mime="application/geo+json",
        )
    
    except Exception as e:
        st.warning(f"No boundary file found for {selected}.")
    # ---------------------------------------------------------
    # DELETE PROJECT (with optional deletion of reports & observations)
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("Delete Project")
    
    if "confirm_delete_project" not in st.session_state:
        st.session_state.confirm_delete_project = False
    
    if st.button("DELETE PROJECT", type="primary"):
        st.session_state.confirm_delete_project = True
    
    if st.session_state.confirm_delete_project:
    
        st.error(f"⚠️ You are about to delete the project **{selected}**.")
    
        delete_reports = st.checkbox("Also delete all reports for this project")
        delete_observations = st.checkbox("Also delete all observations for this project")
    
        colA, colB = st.columns(2)
    
        with colA:
            if st.button("Yes, delete now"):
                try:
                    # 1. Drop FK constraints
                    supabase.rpc("drop_project_fks").execute()
    
                    # 2. Delete GeoJSON file
                    file_path = f"{selected}.geojson"
                    try:
                        supabase.storage.from_(BUCKET_NAME).remove([file_path])
                    except Exception:
                        pass
    
                    # 3. Optional: delete reports
                    if delete_reports:
                        supabase.table("report").delete().eq("project", selected).execute()
    
                    # 4. Optional: delete observations
                    if delete_observations:
                        supabase.table("observations").delete().eq("project", selected).execute()
    
                    # 5. Delete project members
                    supabase.table("project_members").delete().eq("project", selected).execute()
    
                    # 6. Delete project itself
                    supabase.table("projects").delete().eq("name", selected).execute()
    
                    # 7. Re-add FK constraints
                    supabase.rpc("add_project_fks").execute()
    
                    st.success("Project deleted successfully.")
                    st.session_state.confirm_delete_project = False
                    st.rerun()
    
                except Exception as e:
                    st.error(f"Error deleting project: {e}")
    
        with colB:
            if st.button("Cancel"):
                st.session_state.confirm_delete_project = False
                st.info("Deletion cancelled.")


# ---------------------------------------------------------
# PAGE 3 — GENERATE OUTPUT
# ---------------------------------------------------------
elif page == "Gegenereerde output":

    st.set_page_config(layout="wide")

    if st.sidebar.button("Clear Cache"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Cache cleared.")

    

    with st.expander("Projectoverzicht", expanded=False, type="compact"):
        dagverslagen_overview()

    st.text(" ")
    st.text(" ")
    
    BUCKET = "observation_photos"
    projects = supabase.table("projects").select("*").execute().data
    reports = supabase.table("report").select("*").execute().data
    observations = supabase.table("observations").select("*").execute().data

   

    df_projects = pd.DataFrame(projects)
    df_reports = pd.DataFrame(reports)
    df_obs = pd.DataFrame(observations)



    from io import BytesIO
    
    def create_excel_file(dataframes):
        """
        dataframes = {
            "Sheet name": dataframe,
            ...
        }
        """
    
        output = BytesIO()
    
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sheet_name, df in dataframes.items():
                df.to_excel(
                    writer,
                    sheet_name=sheet_name[:31],  # Excel limit
                    index=False
                )
    
        output.seek(0)
        return output




    
    import os
    import tempfile
    import geopandas as gpd
    from shapely.ops import unary_union
    
    BUCKET = "observation_photos"
    
    
    @st.cache_data(show_spinner="Loading project polygons...")
    def load_project_polygons():
    
        def list_folder_paginated(bucket, path=""):
            items = []
    
            offset = 0
            limit = 100
    
            while True:
    
                batch = supabase.storage.from_(bucket).list(
                    path,
                    {
                        "limit": limit,
                        "offset": offset
                    }
                )
    
                if not batch:
                    break
    
                items.extend(batch)
    
                if len(batch) < limit:
                    break
    
                offset += limit
    
            return items
    
        def list_all_geojson(bucket, path=""):
    
            files = []
    
            items = list_folder_paginated(bucket, path)
    
            for item in items:
    
                name = item["name"]
    
                # Folder
                if item.get("id") is None:
    
                    subpath = f"{path}/{name}" if path else name
    
                    files.extend(
                        list_all_geojson(bucket, subpath)
                    )
    
                # File
                else:
    
                    filepath = f"{path}/{name}" if path else name
    
                    if filepath.lower().endswith(".geojson"):
                        files.append(filepath)
    
            return files
    
        geojson_files = sorted(
            list_all_geojson(BUCKET)
        )
    
        records = []
        crs = None
    
        for filepath in geojson_files:
    
            tmp_path = None
    
            try:
    
                file_content = (
                    supabase.storage
                    .from_(BUCKET)
                    .download(filepath)
                )
    
                with tempfile.NamedTemporaryFile(
                    suffix=".geojson",
                    delete=False
                ) as tmp:
    
                    tmp.write(file_content)
                    tmp_path = tmp.name
    
                gdf = gpd.read_file(tmp_path)
    
                if gdf.empty:
                    continue
    
                if crs is None:
                    crs = gdf.crs
    
                records.append(
                    {
                        "project_polygon": os.path.splitext(filepath)[0],
                        "geometry": unary_union(gdf.geometry),
                    }
                )
    
            except Exception as e:
    
                st.warning(
                    f"Error loading {filepath}: {e}"
                )
    
            finally:
    
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
    
        polygons_gdf = gpd.GeoDataFrame(
            records,
            geometry="geometry",
            crs=crs
        )
    
        return polygons_gdf

    polygons_gdf = load_project_polygons()
    
    # ==========================================================
    # FORMAT VELDBEZOEK
    # ==========================================================
    
    def format_veldbezoek(value):
        value = str(value)
    
        # Extract first number from patterns like (1/3)
        match = re.search(r"\((\d+)\s*/\s*\d+\)", value)
    
        if match:
            nr = match.group(1)
    
            name = re.sub(
                r"\s*\(\d+\s*/\s*\d+\)",
                "",
                value
            ).strip()
    
            formatted = f"{name} ({nr})"
    
        else:
            formatted = value
    
        # Keep these groups unchanged
        if (
            formatted.startswith("Huismus")
            or formatted.startswith("Gierzwaluw")
            or formatted.startswith("Steenuil")
        ):
            return formatted
    
        # Everything else is a bat survey
        return f"Vleermuis - {formatted}"
    
    
    # ==========================================================
    # PROJECT FILTER
    # ==========================================================
    
    projects = sorted(
        df_reports["project"]
        .dropna()
        .unique()
    )
    
    selected_project = st.selectbox(
        "Project",
        projects
    )
    
    df_filtered = df_reports[
        df_reports["project"] == selected_project
    ].copy()

    # ==========================================================
    # TIME BLOCK COLUMN
    # ==========================================================
    
    df_filtered["Tijdsblok"] = (
        pd.to_datetime(df_filtered["start_time"].astype(str))
        .dt.strftime("%H:%M")
        + " / "
        + pd.to_datetime(df_filtered["end_time"].astype(str))
        .dt.strftime("%H:%M")
    )                    
    
    
    # ==========================================================
    # WEATHER COLUMN
    # ==========================================================
    
    df_filtered["Weersomstandigheden"] = (
        df_filtered["temperature"].astype(str)
        + "°C, "
        + df_filtered["wind"].astype(str)
        + " Bft, "
        + df_filtered["rain"].fillna("").astype(str)
    )
    
    # ==========================================================
    # OUTPUT TABLE
    # ==========================================================
    
    df_veldbezoeken = pd.DataFrame(
        {
            "Veldbezoek": df_filtered["kind"].apply(format_veldbezoek),
            "Datum": pd.to_datetime(
                df_filtered["date"]
            ).dt.strftime("%d-%m-%Y"),
            "Aantal pers.": "???",
            "Tijdsblok": df_filtered["Tijdsblok"],
            "Weersomstandigheden": df_filtered["Weersomstandigheden"],
        }
    )

    
    # Optional: sort by date
    
    df_veldbezoeken = df_veldbezoeken.sort_values(
        "Datum"
    )
    
    # ==========================================================
    # SHOW TABLE
    # ==========================================================
    
    # title = 
    st.title(f":blue[**{selected_project.replace('_', ' ')}**]", help=None, width="stretch", text_alignment="center")

    st.text(" ")
    st.text(" ")
    st.text(" ")# Adds a blank line
    
    st.markdown(
        """
        <p style='font-size:16px; color:#555; margin-top:0.2rem;'>
            Uitgevoerde veldbezoeken gedurende het aanvullend onderzoek.
        </p>
        """,
        unsafe_allow_html=True
    )

    
    st.dataframe(
        df_veldbezoeken,
        use_container_width=True,
        hide_index=True,
        height=(len(df_veldbezoeken) + 1) * 35
    )


    #----------------
    # Filter reports for selected project
    df_filtered = df_reports[
        df_reports["project"] == selected_project
    ].copy()
    
    # Filter observations for selected project
    df_obs_project = df_obs[
        df_obs["project"] == selected_project
    ].copy()
    
    # Only bats and exclude generic observations
    df_bats = df_obs_project[
        (df_obs_project["animal_type"] == "bat") &
        (df_obs_project["function"] != "vleermuis waarneming")
    ].copy()
    
    # Make sure dates have the same format
    df_filtered["date"] = pd.to_datetime(df_filtered["date"]).dt.date
    df_bats["date"] = pd.to_datetime(df_bats["date"]).dt.date
    
    # Remove bird survey kinds
    df_kind_lookup = df_filtered[
        ~df_filtered["kind"].str.startswith(
            ("Huismus", "Gierzwaluw", "Steenuil"),
            na=False
        )
    ].copy()
    
    # Keep only the first remaining kind per date
    df_kind_lookup = (
        df_kind_lookup
        .groupby("date", as_index=False)
        .first()[["date", "kind"]]
    )
    
    # Merge into bat observations
    df_bats = df_bats.merge(
        df_kind_lookup,
        on="date",
        how="left"
    )
    
    # Create Veldbezoek from date + matched kind
    df_bats["Veldbezoek"] = (df_bats["kind"].fillna("Onbekend")
    )
    
    # Apply existing formatter
    df_bats["Veldbezoek"] = df_bats["Veldbezoek"].apply(format_veldbezoek)
    
    # Final table
    df_verblijfplaatsen = pd.DataFrame({
        "Veldbezoek": df_bats["Veldbezoek"],
        "Soort": df_bats["species"],
        "Aantal individuen": df_bats["aantal"],
        "Verblijplaatsen": df_bats["function"],
        "Adres": df_bats["address"]
    })
    
    # Optional: sort chronologically before displaying
    df_verblijfplaatsen = df_verblijfplaatsen.sort_values(
        by="Veldbezoek"
    )
    st.text(" ") # Adds a blank line
    st.subheader("Vleermuizen", anchor=None, help=None, divider='green', width="stretch", text_alignment="left")


#--------------------
    import geopandas as gpd
    
    # Filter polygons for selected project
    polygons_project = polygons_gdf[
        polygons_gdf["project_polygon"] == selected_project
    ].copy()
    
    # Only bats and exclude generic observations
    df_bats = df_obs_project[
        (df_obs_project["animal_type"] == "bat") &
        (df_obs_project["function"] != "vleermuis waarneming")
    ].copy()
    
    # Convert observations to GeoDataFrame
    gdf_bats = gpd.GeoDataFrame(
        df_bats,
        geometry=gpd.points_from_xy(
            df_bats["lon"],
            df_bats["lat"]
        ),
        crs=polygons_project.crs
    )

    # Spatial join
    gdf_bats = gpd.sjoin(
        gdf_bats,
        polygons_project[["geometry"]],
        how="left",
        predicate="within"
    )
    
    # Create Plangebied column
    gdf_bats["Plangebied"] = (
        gdf_bats["index_right"]
        .notna()
        .map({True: "Binnen", False: "Buiten"})
    )
    
    
    # Convert back to DataFrame if desired
    df_bats = pd.DataFrame(gdf_bats.drop(columns=["geometry", "index_right"]))

    # Make sure dates have the same format
    df_filtered["date"] = pd.to_datetime(df_filtered["date"]).dt.date
    df_bats["date"] = pd.to_datetime(df_bats["date"]).dt.date
    
    # Remove bird survey kinds
    df_kind_lookup = df_filtered[
        ~df_filtered["kind"].str.startswith(
            ( "Gierzwaluw", "Steenuil"),
            na=False
        )
    ].copy()
    
    # Keep only the first remaining kind per date
    df_kind_lookup = (
        df_kind_lookup
        .groupby("date", as_index=False)
        .first()[["date", "kind"]]
    )
    
    # Merge into bat observations
    df_bats = df_bats.merge(
        df_kind_lookup,
        on="date",
        how="left"
    )
    
    # Create Veldbezoek from date + matched kind
    df_bats["Veldbezoek"] = (df_bats["kind"].fillna("Onbekend")
    )
    
    # Apply existing formatter
    df_bats["Veldbezoek"] = df_bats["Veldbezoek"].apply(format_veldbezoek)


    
    # Final table
    df_verblijfplaatsen = pd.DataFrame({
        "Veldbezoek": df_bats["Veldbezoek"],
        "Soort": df_bats["species"],
        "Plangebied": df_bats["Plangebied"],
        "Aantal individuen": df_bats["aantal"],
        "Verblijplaatsen": df_bats["function"],
        "Adres": df_bats["address"]
    })


    
    # Optional: sort chronologically before displaying
    df_verblijfplaatsen = df_verblijfplaatsen.sort_values(
        by="Veldbezoek"
    )

    def kleur_plangebied(val):
        if val == "Binnen":
            return "color: red; font-weight: bold"
        elif val == "Buiten":
            return "color: green; font-weight: bold"
        return ""
    
    styled_df = df_verblijfplaatsen.style.map(
        kleur_plangebied,
        subset=["Plangebied"]
    )
    
    st.markdown(
        """
        <p style='font-size:16px; color:#555; margin-top:0.2rem;'>
            Waarnemingen en aantallen van vleermuizen gedurende de veldbezoeken
        </p>
        """,
        unsafe_allow_html=True
    )
    

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        height=(len(df_verblijfplaatsen) + 1) * 35
    )

    # ---------------------------------------------------------
    # HUISMUS OBSERVATIONS
    # ---------------------------------------------------------
    import geopandas as gpd
    
    
    # Only Huismus nest locations
    df_huismus = df_obs_project[
        (df_obs_project["species"] == "Huismus") &
        (df_obs_project["function"] == "nestlocatie")
    ].copy()
    
    # Convert observations to GeoDataFrame
    gdf_huismus = gpd.GeoDataFrame(
        df_huismus,
        geometry=gpd.points_from_xy(
            df_huismus["lon"],
            df_huismus["lat"]
        ),
        crs=polygons_project.crs
    )

    # Spatial join
    gdf_huismus = gpd.sjoin(
        gdf_huismus,
        polygons_project[["geometry"]],
        how="left",
        predicate="within"
    )
    
    # Create Plangebied column
    gdf_huismus["Plangebied"] = (
        gdf_huismus["index_right"]
        .notna()
        .map({True: "Binnen", False: "Buiten"})
    )
    
    
    # Convert back to DataFrame if desired
    df_huismus = pd.DataFrame(gdf_huismus.drop(columns=["geometry", "index_right"]))

    # Make sure dates have the same format
    df_filtered["date"] = pd.to_datetime(df_filtered["date"]).dt.date
    df_huismus["date"] = pd.to_datetime(df_huismus["date"]).dt.date
    
    # Remove bird survey kinds
    df_kind_lookup = df_filtered[
        ~df_filtered["kind"].str.startswith(
            ("Steenuil"),
            na=False
        )
    ].copy()
    
    # Keep only the first remaining kind per date
    df_kind_lookup = (
        df_kind_lookup
        .groupby("date", as_index=False)
        .first()[["date", "kind"]]
    )
    
    # Merge into bat observations
    df_huismus = df_huismus.merge(
        df_kind_lookup,
        on="date",
        how="left"
    )
    
    # Create Veldbezoek from date + matched kind
    df_huismus["Veldbezoek"] = (df_huismus["kind"].fillna("Onbekend")
    )
    
    # Apply existing formatter
    df_huismus["Veldbezoek"] = df_huismus["Veldbezoek"].apply(format_veldbezoek)


    
    # Final table
    df_hm_nestlocatie = pd.DataFrame({
        "Veldbezoek": df_huismus["Veldbezoek"],
        "Plangebied": df_huismus["Plangebied"],
        "Aantal nestlocatie": df_huismus["aantal"],
        "Adres": df_bats["address"]
    })


    
    # Optional: sort chronologically before displaying
    df_hm_nestlocatie = df_hm_nestlocatie.sort_values(
        by="Veldbezoek"
    )

    def kleur_plangebied(val):
        if val == "Binnen":
            return "color: red; font-weight: bold"
        elif val == "Buiten":
            return "color: green; font-weight: bold"
        return ""
    
    styled_df_hm = df_hm_nestlocatie.style.map(
        kleur_plangebied,
        subset=["Plangebied"]
    )
    
    st.markdown(
        """
        <p style='font-size:16px; color:#555; margin-top:0.2rem;'>
            Waarnemingen en aantal nestlocatie van huismussen gedurende de veldbezoeken
        </p>
        """,
        unsafe_allow_html=True
    )
    

    st.dataframe(
        styled_df_hm,
        use_container_width=True,
        hide_index=True,
        height=(len(df_verblijfplaatsen) + 1) * 35
    )

    "---"
    #--------------------------------------------------------
    #-------------------------------
    # Filter reports for selected project
    df_filtered = df_reports[
        df_reports["project"] == selected_project
    ].copy()
    
    # Filter observations for selected project
    df_obs_project = df_obs[
        df_obs["project"] == selected_project
    ].copy()
    
    # Only Huismus nest locations
    df_huismus = df_obs_project[
        (df_obs_project["species"] == "Huismus") &
        (df_obs_project["function"] == "nestlocatie")
    ].copy()
  
    
    # Make sure dates have same format
    df_filtered["date"] = pd.to_datetime(
        df_filtered["date"]
    ).dt.date
    
    df_huismus["date"] = pd.to_datetime(
        df_huismus["date"]
    ).dt.date
    
    # Get only Huismus surveys
    df_kind_lookup = df_filtered[
        df_filtered["kind"].str.startswith(
            "Huismus",
            na=False
        )
    ].copy()

    
    # Keep only one survey per date
    df_kind_lookup = (
        df_kind_lookup
        .groupby("date", as_index=False)
        .first()[["date", "kind"]]
    )
    
    # Merge survey type into observations
    df_huismus = df_huismus.merge(
        df_kind_lookup,
        on="date",
        how="left"
    )
    
    # Create Veldbezoek
    df_huismus["Veldbezoek"] = (
        df_huismus["kind"]
        .fillna("Huismus")
        .apply(format_veldbezoek)
    )
    
    # Final table
    df_huismus_tabel = pd.DataFrame({
        "Veldbezoek": df_huismus["Veldbezoek"],
        "Soort": df_huismus["species"],
        "Aantal nestlocatie": df_huismus["aantal"],
        "Adres": df_huismus["address"]
    })
    
    df_huismus_tabel = df_huismus_tabel.sort_values(
        by="Veldbezoek"
    )
    
    # ---------------------------------------------------------
    # DISPLAY
    # ---------------------------------------------------------
    gif_url = "https://i.makeagif.com/media/1-17-2023/JfKHrM.gif"
    # st.image(gif_url)
    st.text(" ") # Adds a blank line
    st.subheader("Huismussen", anchor=None, help=None, divider='green', width="stretch", text_alignment="left")
    
    st.dataframe(
        df_huismus_tabel,
        use_container_width=True,
        hide_index=True,
        height=(len(df_huismus_tabel) + 1) * 35
    )

    
# --------------HTML-----------------------------------
    st.text(" ") # Adds a blank line
    st.subheader("Kaart", anchor=None, help=None, divider='green', width="stretch", text_alignment="left")

    import folium
    from folium.plugins import MarkerCluster, BeautifyIcon
    from branca.element import Template, MacroElement
    import pandas as pd
    import numpy as np
    
    # --------------------------------------------------
    # CONFIGURATION
    # --------------------------------------------------
    
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

    # =====================================================
    # HELPER FUNCTION
    # =====================================================
    
    def load_table(table_name):
    
        response = (
            supabase
            .table(table_name)
            .select("*")
            .execute()
        )
    
        return pd.DataFrame(response.data)
    
    # =====================================================
    # DOWNLOAD TABLES
    # =====================================================
    
    reports_df = load_table("report")
    
    observations_df = load_table("observations")
    
    project_df = load_table("projects")

#------------------------
    import os
    import tempfile
    import streamlit as st
    import geopandas as gpd
    
    from shapely.ops import unary_union
    
    
    BUCKET = "observation_photos"
    
    
    def list_folder_paginated(bucket, path=""):
        items = []
        offset = 0
        limit = 100
    
        while True:
            batch = supabase.storage.from_(bucket).list(
                path,
                {"limit": limit, "offset": offset},
            )
    
            if not batch:
                break
    
            items.extend(batch)
    
            if len(batch) < limit:
                break
    
            offset += limit
    
        return items
    
    
    def list_all_geojson(bucket, path=""):
        files = []
    
        for item in list_folder_paginated(bucket, path):
            name = item["name"]
    
            if item.get("id") is None:
                subpath = f"{path}/{name}" if path else name
                files.extend(list_all_geojson(bucket, subpath))
            else:
                filepath = f"{path}/{name}" if path else name
    
                if filepath.lower().endswith(".geojson"):
                    files.append(filepath)
    
        return files
    
    
#------------------------

    OBS_POLYGONS = 'polygons_app'

    # project_name = st.selectbox(
    #     "Choose a project",
    #     list(project_df['name'].unique()),
    #     index=0
    # )
    project_name = selected_project
    df = observations_df[
        observations_df["project"] == project_name
    ].copy()
    
    survey_area = polygons_gdf[
        polygons_gdf["project_polygon"] == project_name
    ].copy()
    
    species_list = sorted(
        df["species"].fillna("Unknown").unique()
    )
    
    palette = (
        list(plt.cm.tab20.colors)
        + list(plt.cm.Set3.colors)
        + list(plt.cm.Dark2.colors)
    )
    
    species_colors = {
        species: mcolors.to_hex(
            palette[i % len(palette)]
        )
        for i, species in enumerate(species_list)
    }
    
    # ==========================================================
    # LOAD POLYGONS
    # ==========================================================
    polygon_rows = (
    supabase
    .table(OBS_POLYGONS)
    .select("*")
    .eq("project", project_name)
    .execute()
    ).data
    
    # --------------------------------------------------
    # FUNCTION ICONS
    # --------------------------------------------------
    ANIMAL_TYPE_LABELS = {
        "bat": "🦇 Vleermuizen",
        "bird": "🪶 Vogels",
        "plant": "🍃 Planten",
        "amphibian": "🐸 Amfibieën",
        "odonata": "≽༏≼ Libellen",
        "unknown": "❓ Onbekend",
    }
    
    FUNCTION_ICONS = {
        # Bats
        "vleermuis waarneming": "walkie-talkie",
        "zomerverblijfplaats": "mars",
        "kraamverblijfplaats": "venus",
        "paarverblijfplaats": "heart",
        "winterverblijfplaats": "snowflake",
        "vleermuiskast": "box-archive",
        "zender": "tower-broadcast",
    
        # Birds
        "vogel waarneming": "binoculars",
        "nestlocatie": "egg",
        "mogelijke nestlocatie": "question",
    
        # Plants
        "Aanwezig": "leaf",
        "Bloeiend": "seedling",
        "Vrucht": "apple-whole",
        "Dood": "skull-crossbones",
    
        # Amphibians
        "Adult": "frog",
        "Roepend": "volume-high",
        "Paring": "heart",
        "Eieren": "egg",
        "Larven": "water",
        "Jong dier": "child",
        "Foeragerend": "utensils",
        "Trek": "route",
    
        # Odonata
        "Eiafzet": "egg",
        "Tandem": "link",
        "Uitsluiping": "arrow-up-right-dots",
        "Larve": "water",
        "Exuvia": "shirt",
        "Rustend": "pause",
    }
    # --------------------------------------------------
    # CREATE MAP
    # --------------------------------------------------
    
    center_lat = observations_df["lat"].mean()
    center_lon = observations_df["lon"].mean()
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        zoom_control=False,
        tiles=None
    )
    
    tiles = 'https://api.mapbox.com/styles/v1/jeggino/cmn7ms1u3001f01pl691k0eyu/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1IjoiamVnZ2lubyIsImEiOiJjbHdscmRkZHAxMTl1MmlyeTJpb3Z2eHdzIn0.N9TRN7xxTikk235dVs1YeQ'
    folium.TileLayer(tiles=tiles,
                     attr='XXX Mapbox Attribution',
                         max_zoom=24,
        max_native_zoom=22,
        overlay=False,
        control=False,name="Satellietkaart").add_to(m)
    
    
    # Satellite
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellit",
        max_native_zoom=21,
        max_zoom=21,
        overlay=False,
        control=False
    ).add_to(m)
    
    
    
    folium.GeoJson(
        survey_area,
        name="Onderzoeksgebied",
        style_function=lambda feature: {
            "fillColor": "#d62728",
            "color": "#b30000",
            "weight": 4,
            "fillOpacity": 0.12,
            "opacity": 0.9,
        },
        highlight_function=lambda feature: {
            "weight": 5,
            "color": "#ff0000",
            "fillOpacity": 0.18,
        },
    ).add_to(m)
    
    
    cluster = MarkerCluster(
        name="Waarnemingen",
        disableClusteringAtZoom=18
    ).add_to(m)
    
    if len(polygon_rows) == 0:
        pass  # skip
    else:
        polygons = folium.FeatureGroup(name="Functionele gebieden").add_to(m)
    
    # --------------------------------------------------
    # OBSERVATIONS
    # --------------------------------------------------
    
    
    for _, obs in df.iterrows():
    
        animal_type = str(obs.get("animal_type", "")).lower()
    
        species = obs["species"]
        color = species_colors[species]
        icon = "fa-solid fa-leaf"
    
    
    
    
        marker_size = 34
        inner_icon_px = 15
    
        # ----------------------------
        # Image block
        # ----------------------------
        photo_url = obs.get("photo_url", '')
    
        if pd.notna(photo_url) and str(photo_url).strip():
            image_block = f"""
                <a href="{photo_url}" target="_blank">
                    <img src="{photo_url}" 
                         style="width: 100%; max-height: 120px; object-fit: cover; border-radius: 6px;">
                </a>
                """
    
        else:
            # Choose emoji based on species type
            if "bat" in obs.get('animal_type', ''):
                emoji = "🦇"
            elif "bird" in obs.get('animal_type', ''):
                emoji = "🪶"  # default feather for birds or unknown
            elif "amphibian" in obs.get('animal_type', ''):
                emoji = "🐸"  # default feather for birds or unknown
            elif "odonata" in obs.get('animal_type', ''):
                emoji = "≽༏≼"  # default feather for birds or unknown
            else:
                emoji = "🍃"
        
            image_block = f"""
                <div style="
                    font-size: 20px;
                    text-align: center;
                    margin: 10px 0;
                ">{emoji}</div>
            """
        # ----------------------------
        # Popup
        # ----------------------------
    
        popup_html = f"""
        <div style="
            background-color:white;
            padding:10px 14px;
            border-radius:10px;
            box-shadow:0 2px 6px rgba(0,0,0,0.25);
            font-family:Arial,sans-serif;
            width:220px;
            border:3px solid {color};
        ">
    
            <div style="
                font-weight:700;
                font-size:15px;
                color:{color};
                margin-bottom:6px;
                text-align:center;
            ">
                {obs.get('species', '')}
            </div>
    
            <div style="text-align:center; margin-bottom:8px;">
                {image_block}
            </div>
    
            <div style="
                font-size:13px;
                color:#444;
                margin-bottom:4px;
                text-align:center;
            ">
                {obs.get('date', '')}
            </div>
    
            <div style="
                font-size:12px;
                color:#555;
                margin-bottom:4px;
                font-style:italic;
                text-align:center;
            ">
                ({obs.get('aantal', '')}) {str(obs.get('function', '')).capitalize()}
            </div>
    
            <div style="
                font-size:12px;
                color:#333;
                font-weight:bold;
                text-align:justify;
            ">
                {obs.get('behavior', '')}
            </div>
    
        </div>
        """
    
        tooltip_text = (
            f"{obs.get('species', '')}"
        )
    
        # ----------------------------
        # BeautifyIcon
        # ----------------------------
    
        function_name = str(obs.get("function", "")).strip()
        
        icon_name = FUNCTION_ICONS.get(
            function_name,
            "circle-info"
        )
        
        icon = f"fa-solid fa-{icon_name}"
        
        marker_icon = BeautifyIcon(
            icon=icon,
            icon_shape="marker",
            background_color="white",
            border_color=color,
            border_width=3,
            text_color="black",
            icon_anchor=[marker_size/2, marker_size],
            icon_size=[marker_size, marker_size],
            inner_icon_style=f"""
                font-size:{inner_icon_px}px;
                display:flex;
                align-items:center;
                justify-content:center;
                width:100%;
                height:100%;
                text-align:center;
                padding:0;
                margin:0;
            """
        )
    
        folium.Marker(
            location=[obs["lat"], obs["lon"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=tooltip_text,
            icon=marker_icon,
        ).add_to(cluster)
    
    
    
    # ============================================================
    # ADD POLYGONS TO MAP
    # ============================================================
    if len(polygon_rows) == 0:
        pass  # skip
    else:
    
        for row in polygon_rows:
        
            geometry = row["geometry"]
            species = row.get("species", "Unknown")
            date = row.get("date", )
            aantal = row.get("aantal",)
            fill_color = species_colors.get(species, "yellow")
            comments = row.get("comments",)
            group = row.get('group')
        
            function_type = row.get("function", "")
            id_type = row.get("id", "")
        
        
            if row.get("photo_url"):
                # Use real image
                image_block = f"""
                    <a href="{row.get('photo_url')}" target="_blank">
                        <img src="{row.get('photo_url')}" 
                             style="width: 100%; max-height: 120px; object-fit: cover; border-radius: 6px;">
                    </a>
                """
            else:
                # Choose emoji based on species type
                if "bat" in row.get('group', ''):
                    emoji = "🦇"
                elif "bird" in row.get('group', ''):
                    emoji = "🪶"  # default feather for birds or unknown
                elif "amphibian" in row.get('group', ''):
                    emoji = "🐸"  # default feather for birds or unknown
                elif "odonata" in row.get('group', ''):
                    emoji = "≽༏≼"  # default feather for birds or unknown
                else:
                    emoji = "🍃"
            
                image_block = f"""
                    <div style="
                        font-size: 20px;
                        text-align: center;
                        margin: 10px 0;
                    ">{emoji}</div>
                """
            
            # Styled popup with colored border matching the marker color
            popup_html_polygon = f"""
            <div style="
                background-color: white;
                padding: 10px 14px;
                border-radius: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25);
                font-family: 'Arial', sans-serif;
                width: 200px;
                border: 3px solid {fill_color};
            ">
            
                <!-- Species Title -->
                <div style="
                    font-weight: 700;
                    font-size: 15px;
                    color: {fill_color};
                    margin-bottom: 6px;
                    text-align: center;
                ">
                    {species}
                </div>
            
                <!-- Image or Emoji -->
                <div style="text-align:center; margin-bottom:8px;">
                    {image_block}
                </div>
            
                <!-- Date (NO label) -->
                <div style="
                    font-size: 13px;
                    color: #444;
                    margin-bottom: 4px;
                    text-align: center;
                ">
                    {date}
                </div>
            
                <!-- Function (italic, centered, capitalized) -->
                <div style="
                    font-size: 12px;
                    color: #555;
                    margin-bottom: 4px;
                    font-style: italic;
                    text-align: center;
                ">
                    ({aantal}) {function_type.capitalize()}
                </div>
            
                <!-- Comment (bold, justified) -->
                <div style="
                    font-size: 12px;
                    color: #333;
                    font-weight: bold;
                    text-align: justify;
                ">
                    {comments}
                </div>
            
            </div>
            """
            
            popup = folium.Popup(
                folium.Html(popup_html_polygon, script=True),
                max_width=300,
            )
        
        
        
        
        
            pattern = None
            fill_opacity = 1
        
            if function_type == "foerageergebied":
        
                pattern = StripePattern(
                    angle=45,
                    weight=4,
                    space_weight=4,
                    color=fill_color,
                    opacity=0.8,
                )
                pattern.add_to(polygons)
        
            elif function_type == "paarterritorium":
        
                pattern = CirclePattern(
                    width=8,
                    height=8,
                    radius=1,
                    fill_color=fill_color,
                    color=fill_color,
                    fill_opacity=0.8,
                    
                )
                pattern.add_to(polygons)
        
            else:
                fill_opacity = 0.1
        
            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "species": species,
                    "function": function_type,
                    "group": group,
                    "date": date,
                    "comments": comments,
                    "aantal": aantal,
                    "id": id_type,
                },
            }
            
            geojson = folium.GeoJson(
                feature,
                popup=popup,
                tooltip=None,
                style_function=lambda f,
                fill_color=fill_color,
                fill_opacity=fill_opacity: {
                    "fillColor": fill_color,
                    "fillOpacity": fill_opacity,
                    "color": fill_color,
                    "weight": 1.5,
                },
                highlight_function=lambda feature: {
                    "weight": 4.5,
                    "fillOpacity": 1,
                },
            ).add_to(polygons)
        
        
            if pattern:
                geojson.options["fillPattern"] = pattern
    
    # --------------------------------------------------
    # PROFESSIONAL LEGEND
    # --------------------------------------------------
    
    from branca.element import MacroElement, Template
    import folium
    
    
    points_df = (
        df.fillna({
            "animal_type": "Unknown",
            "function": "Unknown",
            "species": "Unknown"
        })
        .groupby(["animal_type", "function", "species"])
        .size()
        .reset_index(name="count")
    )
    
    points_df["source"] = "point"
    
    if len(polygon_rows) == 0:
        combined_df = points_df.copy()
    else:
    
        polygon_df = pd.DataFrame(polygon_rows)
        
        polygon_df = (
            polygon_df.fillna({
                "group": "Unknown",
                "function": "Unknown",
                "species": "Unknown"
            })
            .groupby(["group", "function", "species"])
            .size()
            .reset_index(name="count")
        )
        
        polygon_df["source"] = "polygon"
        
        polygon_df.rename(
            columns={"group": "animal_type"},
            inplace=True
        )
    
        combined_df = pd.concat(
            [points_df, polygon_df],
            ignore_index=True
        )
    
    
    
    # Load Font Awesome
    m.get_root().header.add_child(
        folium.Element(
            '<link rel="stylesheet" '
            'href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">'
        )
    )
    
    project_title = project_name.replace("_", " ")
    
    
    legend_html = f"""
    {{% macro html(this, kwargs) %}}
    
    <button id="legendButton"
            onclick="toggleLegend()"
            style="
                position:fixed;
                bottom:24px;
                left:24px;
                z-index:99999;
    
                display:flex;
                align-items:center;
                gap:10px;
    
                padding:12px 18px;
    
                background:linear-gradient(
                    135deg,
                    #2563eb,
                    #1d4ed8
                );
    
                color:white;
    
                border:none;
                border-radius:14px;
    
                font-family:'Segoe UI',Arial,sans-serif;
                font-size:14px;
                font-weight:600;
    
                cursor:pointer;
    
                box-shadow:
                    0 8px 20px rgba(37,99,235,.30),
                    0 2px 6px rgba(0,0,0,.15);
    
                transition:all .25s ease;
            "
    
            onmouseover="
                this.style.transform='translateY(-3px) scale(1.02)';
                this.style.boxShadow='0 12px 28px rgba(37,99,235,.40)';
            "
    
            onmouseout="
                this.style.transform='translateY(0) scale(1)';
                this.style.boxShadow='0 8px 20px rgba(37,99,235,.30),0 2px 6px rgba(0,0,0,.15)';
            ">
    
        <i class="fa-solid fa-list"
           style="font-size:16px;"></i>
    
        <span>Legende</span>
    
    </button>
    
    <div id="legendDialog"
         style="
            display:none;
            position:fixed;
            bottom:85px;
            left:24px;
            z-index:99998;
    
            width:350px;
            max-height:500px;
            overflow-y:auto;
    
            background:rgba(255,255,255,0.82);
            backdrop-filter:blur(12px);
            -webkit-backdrop-filter:blur(12px);
    
            border-radius:18px;
    
            border:1px solid rgba(37,99,235,.15);
    
            padding:18px;
    
            box-shadow:
                0 12px 28px rgba(37,99,235,.20),
                0 4px 12px rgba(0,0,0,.12);
    
            font-family:'Segoe UI',Arial,sans-serif;
            font-size:13px;
    
            transition:all .25s ease;
         ">
    
        <div style="
            font-size:17px;
            font-weight:700;
            margin-bottom:12px;
            padding-bottom:8px;
        
            color:#001b15;
        
            border-bottom:
                2px solid rgba(37,99,235,.15);
        ">
    
        
            {project_title}
        </div>
    
        <div style="
            display:flex;
            align-items:center;
            margin-bottom:10px;
        ">
            <span style="
                width:18px;
                height:12px;
                background:rgba(255,0,0,0.15);
                border:2px solid #b30000;
                display:inline-block;
                margin-right:8px;
            "></span>
    
            <span>Onderzoeksgebied</span>
        </div>
        <div style="height:10px;"></div>
    
    
    
    """
    
    
    
    
    
        
    # Animal Type → Function → Species
    for animal_type in sorted(combined_df["animal_type"].unique()):
    
        label = ANIMAL_TYPE_LABELS.get(
            str(animal_type).lower(),
            animal_type
        )
    
        legend_html += f"""
        <div style="
            font-size:15px;
            font-weight:bold;
            margin-top:12px;
            margin-bottom:6px;
            color:#111827;
            border-bottom:1px solid #d1d5db;
            padding-bottom:3px;
        ">
            {label}
        </div>
        """
    
        animal_subset = combined_df[
            combined_df["animal_type"] == animal_type
        ]
    
        for function_name in sorted(animal_subset["function"].unique()):
        
            function_subset = (
                animal_subset[
                    animal_subset["function"] == function_name
                ]
                .sort_values("species")
            )
        
            source = function_subset["source"].iloc[0]
    
            if source == "polygon":
            
                if function_name.lower() == "foerageergebied":
                    # striped square
                    symbol = """
                    <span style="
                        display:inline-block;
                        width:14px;
                        height:14px;
                        border:1px solid #444;
                        background:
                        repeating-linear-gradient(
                            45deg,
                            #666,
                            #666 2px,
                            white 2px,
                            white 5px
                        );
                        margin-right:6px;
                    "></span>
                    """
            
                elif function_name.lower() == "paarterritorium":
                    # dotted square
                    symbol = """
                    <span style="
                        display:inline-block;
                        width:14px;
                        height:14px;
                        border:1px solid #444;
                        background-color:white;
                        background-image:radial-gradient(
                            #666 1.5px,
                            transparent 1.5px
                        );
                        background-size:5px 5px;
                        margin-right:6px;
                    "></span>
                    """
            
                else:
                    # fallback
                    symbol = """
                    <span style="
                        display:inline-block;
                        width:14px;
                        height:14px;
                        border:1px solid #444;
                        background:#999;
                        margin-right:6px;
                    "></span>
                    """
    
        
    
            elif source == "point": #HERE
        
                icon = FUNCTION_ICONS.get(
                    function_name,
                    "circle-info"
                )
        
                symbol = f"""
                <i class="fa-solid fa-{icon}"
                   style="margin-right:6px;"></i>
                """
    
    
            legend_html += f"""
            <div style="
                margin-top:6px;
                margin-bottom:4px;
                margin-left:10px;
                font-weight:bold;
                color:#374151;
                display:flex;
                align-items:center;
            ">
                {symbol}
                <span>{function_name}</span>
            </div>
            """
    
    
    
            for _, row in function_subset.iterrows():
    
                species = row["species"]
                count = row["count"]
    
                color = species_colors.get(
                    species,
                    "#999999"
                )
    
                legend_html += f"""
                <div style="
                    display:flex;
                    align-items:center;
                    margin-bottom:5px;
                    margin-left:25px;
                ">
                    <span style="
                        width:14px;
                        height:14px;
                        background:{color};
                        border-radius:50%;
                        display:inline-block;
                        margin-right:8px;
                        border:1px solid #555;
                        flex-shrink:0;
                    "></span>
    
                    <span>
                        {species} ({count})
                    </span>
                </div>
                """
    
    legend_html += """
    </div>
    
    <script>
    function toggleLegend() {
    
        var legend =
            document.getElementById("legendDialog");
    
        if (legend.style.display === "block") {
            legend.style.display = "none";
        } else {
            legend.style.display = "block";
        }
    }
    </script>
    
    {% endmacro %}
    """
    
    
    
    legend = MacroElement()
    legend._template = Template(legend_html)
    
    m.get_root().add_child(legend)
    
    # --------------------------------------------------
    # EXTRAS
    # --------------------------------------------------
    
    # folium.LayerControl().add_to(m)
    
    # Fit bounds to observations
    bounds = df[["lat", "lon"]].dropna().values.tolist()
    if len(bounds) > 0:
        m.fit_bounds(bounds)
    
    
    
    
    
    
    # --------------------------------------------------
    # LAYER CONTROL
    # --------------------------------------------------
    from branca.element import Element
    
    folium.LayerControl(
        position="topright",
        collapsed=True
    ).add_to(m)
    
    css = """
    <style>
    
    /* Closed button */
    .leaflet-control-layers-toggle{
        width:42px !important;
        height:42px !important;
    
        background-size:22px 22px !important;
    
        border-radius:12px !important;
    
        box-shadow:
            0 4px 12px rgba(0,0,0,0.15);
    
        transition:all 0.2s ease;
    }
    
    /* Open panel */
    .leaflet-control-layers{
        background:rgba(255,255,255,0.85)!important;
        backdrop-filter:blur(8px);
    
        border:none!important;
    
        border-radius:16px!important;
    
        padding:12px!important;
    
        box-shadow:
            0 8px 30px rgba(0,0,0,0.18)!important;
    
        font-family:'Segoe UI', Arial, sans-serif;
    
        overflow:hidden;
    }
    
    /* Scroll area */
    .leaflet-control-layers-list{
        max-height:350px;
        overflow-y:auto;
    }
    
    /* Labels */
    .leaflet-control-layers label{
        font-size:13px;
        cursor:pointer;
    }
    
    /* Hover effect */
    .leaflet-control-layers label:hover{
        color:#2563eb;
    }
    
    </style>
    """
    
    m.get_root().html.add_child(
        Element(css)
    )
    
    # --------------------------------------------------
    # MEASURE CONTROL
    # --------------------------------------------------
    from folium.plugins import MeasureControl
    
    MeasureControl(
        position="topright",
        primary_length_unit="meters",
        secondary_length_unit="kilometers",
        primary_area_unit="sqmeters",
        secondary_area_unit="hectares",
        active_color="#2563eb",
        completed_color="#1d4ed8"
    ).add_to(m)
    
    
    from branca.element import Element
    
    css = """
    <style>
    
    /* -------------------------------------------------
       MEASURE BUTTON
    ------------------------------------------------- */
    
    .leaflet-control-measure-toggle {
    
        width:42px !important;
        height:42px !important;
    
        border-radius:12px !important;
    
        box-shadow:
            0 4px 12px rgba(0,0,0,0.15);
    
        transition:all 0.2s ease;
    }
    
    .leaflet-control-measure-toggle:hover {
    
        transform:translateY(-2px);
    
        box-shadow:
            0 8px 20px rgba(37,99,235,.25);
    }
    
    /* -------------------------------------------------
       MEASURE PANEL
    ------------------------------------------------- */
    
    .leaflet-control-measure {
    
        background:rgba(255,255,255,0.85)!important;
    
        backdrop-filter:blur(8px);
        -webkit-backdrop-filter:blur(8px);
    
        border:none!important;
    
        border-radius:16px!important;
    
        padding:12px!important;
    
        box-shadow:
            0 8px 30px rgba(0,0,0,0.18)!important;
    
        font-family:'Segoe UI', Arial, sans-serif;
    
        overflow:hidden;
    
        transition:all .25s ease;
    }
    
    /* -------------------------------------------------
       PANEL CONTENT
    ------------------------------------------------- */
    
    .leaflet-control-measure h3,
    .leaflet-control-measure h4 {
    
        color:#1d4ed8;
        font-weight:600;
    }
    
    .leaflet-control-measure a {
    
        color:#2563eb;
    }
    
    .leaflet-control-measure-resultpopup {
    
        border-radius:12px;
        overflow:hidden;
    }
    
    /* -------------------------------------------------
       BUTTONS INSIDE PANEL
    ------------------------------------------------- */
    
    .leaflet-control-measure .button {
    
        border-radius:8px !important;
    
        transition:all .2s ease;
    }
    
    .leaflet-control-measure .button:hover {
    
        background:#2563eb !important;
    
        color:white !important;
    }
    
    </style>
    """
    
    
    m.get_root().html.add_child(
        Element(css)
    )
    
    # --------------------------------------------------
    # LOGO
    # --------------------------------------------------
    import base64
    from pathlib import Path
    
    logo_path = Path("signal-2026-08-31-14-39-37-051.jpg")
    
    with open(logo_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    
    
    
    from branca.element import Element
    
    logo_html = f"""
    <style>
    #map-logo {{
        position: fixed;
        top: 15px;
        left: 15px;
        z-index: 999999;
    }}
    
    #map-logo img {{
        width: 100px;
        cursor: pointer;
    }}
    
    @keyframes logoIntro {{
        from {{
            opacity: 0;
            transform: translateY(-100px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    #map-logo {{
        animation: logoIntro 1.2s cubic-bezier(0.22, 1, 0.36, 1);
    }}
    
    </style>
    
    <div id="map-logo">
        <img id="logo-img"
             src="data:image/jpeg;base64,{encoded}">
    </div>
    
    <script>
    document.getElementByIdk', function() {{
        alert('Logo clicked');
    }});
    </script>
    """
    
    m.get_root().html.add_child(Element(logo_html))
    
    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------
    
    import re
    
    safe_project_name = re.sub(
        r'[^A-Za-z0-9_-]+',
        "_",
        str(project_name)
    ).strip("_")
    

    # Display map
    st_folium(m, use_container_width=True)
    
    # Save map as HTML string
    html_map = m.get_root().render()

    col1, col2 = st.columns(2, gap="xxlarge")

    with col1:
        # Download button
        st.download_button(
            label="📥 Download HTML Map",
            data=html_map,
            file_name=f"{safe_project_name}_HTML.html",
            mime="text/html"
        )

#------------------
    with col2:
        # Example
        excel_file = create_excel_file({
            "Veldbezoeken": df_veldbezoeken,
            "Vleermuizen": df_verblijfplaatsen,
            "Huismus": df_huismus_tabel,
            "Rapporten": df_filtered
        })
        
        st.download_button(
            label="📥 Download Excel",
            data=excel_file,
            file_name=f"{selected_project}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


    


    
