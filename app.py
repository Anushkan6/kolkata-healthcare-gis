import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
import branca.colormap as cm

st.set_page_config(page_title="Kolkata Healthcare Access Dashboard", layout="wide")

# ---------- Load data ----------
@st.cache_data
def load_data():
    grid = gpd.read_file("grid_export.geojson")
    facilities = gpd.read_file("facilities_export.geojson")
    return grid, facilities

grid, facilities = load_data()

# Proposed new facility locations (Candidates B and C from the analysis)
proposed_facilities = pd.DataFrame([
    {"name": "Proposed Facility 1 (South-western fringe)", "lat": 22.487823, "lon": 88.299643},
    {"name": "Proposed Facility 2 (Eastern fringe)", "lat": 22.517823, "lon": 88.424643},
])

st.title("🏥 Kolkata (KMC) Healthcare Access Dashboard")
st.markdown(
    "Interactive exploration of healthcare accessibility across Kolkata Municipal Corporation, "
    "based on network travel time (not straight-line distance), population demand, and facility load."
)

# ---------- Sidebar controls ----------
st.sidebar.header("View Options")
layer_choice = st.sidebar.radio(
    "Select layer to display",
    ["Travel time to nearest facility", "Underserved area score", "Facility load (demand vs capacity)"]
)
show_facilities = st.sidebar.checkbox("Show existing facilities", value=True)
show_proposed = st.sidebar.checkbox("Show proposed new facilities", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### Key Numbers")
st.sidebar.metric("Total population (KMC)", f"{grid['population'].sum():,.0f}")
st.sidebar.metric("Existing facilities", f"{len(facilities)}")
st.sidebar.metric("Underserved grid cells", f"{(grid['underserved_score'] > grid['underserved_score'].quantile(0.8)).sum()} / {len(grid)}")
st.sidebar.metric("Max travel time (baseline)", f"{grid['travel_time_min'].replace([float('inf')], None).max():.1f} min")

# ---------- Map ----------
col1, col2 = st.columns([3, 1])

with col1:
    center = [grid.geometry.centroid.y.mean(), grid.geometry.centroid.x.mean()]
    m = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")

    if layer_choice == "Travel time to nearest facility":
        col = "travel_time_min"
        colormap = cm.LinearColormap(["#2ecc71", "#f1c40f", "#e74c3c"], vmin=grid[col].replace([float('inf')], None).min(), vmax=grid[col].replace([float('inf')], None).quantile(0.98))
        legend_name = "Travel time (min)"
    elif layer_choice == "Underserved area score":
        col = "underserved_score"
        colormap = cm.LinearColormap(["#fff5eb", "#fd8d3c", "#a50f15"], vmin=grid[col].min(), vmax=grid[col].max())
        legend_name = "Underserved score"
    else:
        col = "facility_load_norm"
        colormap = cm.LinearColormap(["#deebf7", "#3182bd", "#08306b"], vmin=0, vmax=1)
        legend_name = "Facility load (normalized)"

    def style_fn(feature, col=col, colormap=colormap):
        val = feature["properties"].get(col)
        if val is None or (isinstance(val, float) and val != val):
            return {"fillColor": "#cccccc", "color": "none", "fillOpacity": 0.5}
        return {"fillColor": colormap(val), "color": "none", "fillOpacity": 0.75}

    folium.GeoJson(
        grid,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(fields=["travel_time_min", "population", "underserved_score"],
                                       aliases=["Travel time (min)", "Population", "Underserved score"]),
    ).add_to(m)
    colormap.caption = legend_name
    colormap.add_to(m)

    if show_facilities:
        for _, row in facilities.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=3,
                color="#2c3e50",
                fill=True,
                fill_opacity=0.8,
                popup=f"{row['name']}<br>Load ratio: {row['load_ratio']:.1f}",
            ).add_to(m)

    if show_proposed:
        for _, row in proposed_facilities.iterrows():
            folium.Marker(
                location=[row["lat"], row["lon"]],
                icon=folium.Icon(color="green", icon="plus-sign"),
                popup=row["name"],
            ).add_to(m)

    st_folium(m, width=None, height=650)

with col2:
    st.markdown("### Before / After")
    st.markdown("**Objective A — Population within 15 min**")
    st.write("Baseline: 6,029,267")
    st.write("+ Facility 1: 6,043,157 (+13,890)")
    st.write("+ Facility 2: 6,048,203 (+5,046)")
    st.markdown("**Objective B — Worst-case travel time**")
    st.write("Baseline: 20.3 min")
    st.write("+ Facility 1: 16.7 min (−3.6 min)")
    st.write("+ Facility 2: 15.0 min (−1.6 min)")
    st.markdown("---")
    st.markdown(
        "**Decision:** 2 new facilities recommended (not 3). A third candidate site, "
        "despite scoring highest on the composite underserved index, showed zero "
        "marginal improvement on either objective — it was already within 4 minutes "
        "of a facility, and its 'underserved' flag was driven by facility overload, "
        "not distance. See report for full reasoning."
    )

st.markdown("---")
st.markdown(
    "Built for the Skylark Drones GIS Engineer Assessment. Data: OpenStreetMap (roads, facilities), "
    "WorldPop 2020 (population). Methodology: network-based travel time via multi-source Dijkstra, "
    "500m population grid, multi-factor underserved scoring."
)
