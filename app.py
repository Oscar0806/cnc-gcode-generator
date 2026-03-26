import streamlit as st
import plotly.graph_objects as go
import numpy as np
from gcode_engine import GCodeGenerator
 
st.set_page_config(page_title="CNC G-Code Generator",
                   page_icon="\u2699\uFE0F", layout="wide")
st.title("\u2699\uFE0F CNC G-Code Generator & Toolpath Visualizer")
st.markdown("**Generate real G-code from geometry parameters "
            "\u2013 CNC/Robotics concept**")
st.divider()
 
# ── SIDEBAR ──
st.sidebar.header("\U0001f527 Tool Settings")
tool_dia = st.sidebar.select_slider("Tool diameter (mm)",
    [2,3,4,5,6,8,10,12], value=6)
feed = st.sidebar.slider("Feed rate (mm/min)", 50, 500, 200, 25)
plunge = st.sidebar.slider("Plunge rate (mm/min)", 10, 200, 50, 10)
spindle = st.sidebar.slider("Spindle speed (RPM)",
    1000, 20000, 8000, 1000)
 
st.sidebar.header("\U0001f4d0 Operations")
op_type = st.sidebar.selectbox("Operation type",
    ["Rectangular pocket", "Circular pocket",
     "Hole pattern (bolt circle)", "Combined part"])
 
gen = GCodeGenerator(feed, plunge, spindle, tool_dia=tool_dia)
gen.header("PART_001")
 
# ── OPERATION PARAMETERS ──
if op_type == "Rectangular pocket":
    st.sidebar.subheader("Pocket dimensions")
    px = st.sidebar.number_input("X position", 0.0, 200.0, 10.0)
    py = st.sidebar.number_input("Y position", 0.0, 200.0, 10.0)
    pw = st.sidebar.number_input("Width (mm)", 5.0, 200.0, 40.0)
    ph = st.sidebar.number_input("Height (mm)", 5.0, 200.0, 30.0)
    pd = st.sidebar.number_input("Depth (mm)", 0.5, 50.0, 5.0)
    psd = st.sidebar.number_input("Step down (mm)", 0.5, 10.0, 1.5)
    gen.rectangular_pocket(px, py, pw, ph, pd, psd)
 
elif op_type == "Circular pocket":
    st.sidebar.subheader("Circle dimensions")
    ccx = st.sidebar.number_input("Center X", 0.0, 200.0, 50.0)
    ccy = st.sidebar.number_input("Center Y", 0.0, 200.0, 50.0)
    cd = st.sidebar.number_input("Diameter (mm)", 5.0, 200.0, 30.0)
    cdp = st.sidebar.number_input("Depth (mm)", 0.5, 50.0, 3.0)
    gen.circular_pocket(ccx, ccy, cd, cdp)
 
elif op_type == "Hole pattern (bolt circle)":
    st.sidebar.subheader("Bolt circle")
    bcx = st.sidebar.number_input("Center X", 0.0, 200.0, 50.0)
    bcy = st.sidebar.number_input("Center Y", 0.0, 200.0, 50.0)
    bcr = st.sidebar.number_input("Circle radius (mm)",
                                   5.0, 100.0, 25.0)
    bn = st.sidebar.slider("Number of holes", 3, 12, 6)
    bdp = st.sidebar.number_input("Hole depth (mm)", 1.0, 50.0, 8.0)
    centers = [(bcx + bcr * np.cos(2*np.pi*i/bn),
                bcy + bcr * np.sin(2*np.pi*i/bn))
               for i in range(bn)]
    gen.hole_pattern(centers, bdp)
 
else:  # Combined part
    gen.rectangular_pocket(10, 10, 60, 40, 5, 1.5)
    gen.circular_pocket(90, 30, 25, 3)
    centers = [(30+20*np.cos(2*np.pi*i/4),
                70+20*np.sin(2*np.pi*i/4)) for i in range(4)]
    gen.hole_pattern(centers, 8)
 
gen.footer()
gcode = gen.get_gcode()
 
# ── KPIs ──
c1,c2,c3,c4 = st.columns(4)
with c1: st.metric("G-code Lines", len(gen.lines))
with c2: st.metric("Toolpath Points", len(gen.toolpath))
with c3: st.metric("Tool", f"\u00D8{tool_dia}mm")
with c4: st.metric("Feed", f"{feed} mm/min")
 
st.divider()
 
# ── 3D TOOLPATH VISUALIZATION ──
st.subheader("\U0001f4c8 3D Toolpath Visualization")
if gen.toolpath:
    tp = gen.toolpath
    xs = [p[0] for p in tp]
    ys = [p[1] for p in tp]
    zs = [p[2] for p in tp]
    
    fig = go.Figure()
    # Rapid moves (red) vs cutting moves (blue)
    for i in range(1, len(tp)):
        color = "#E74C3C" if zs[i] >= gen.safe_z - 0.1 else "#3498DB"
        fig.add_trace(go.Scatter3d(
            x=[xs[i-1],xs[i]], y=[ys[i-1],ys[i]], z=[zs[i-1],zs[i]],
            mode="lines",
            line=dict(color=color, width=2 if color=="#3498DB" else 1),
            showlegend=False, hoverinfo="skip"))
    
    # Legend entries
    fig.add_trace(go.Scatter3d(x=[None],y=[None],z=[None],
        mode="lines",line=dict(color="#3498DB",width=3),
        name="Cutting move"))
    fig.add_trace(go.Scatter3d(x=[None],y=[None],z=[None],
        mode="lines",line=dict(color="#E74C3C",width=2),
        name="Rapid move"))
    
    fig.update_layout(scene=dict(
        xaxis_title="X (mm)", yaxis_title="Y (mm)",
        zaxis_title="Z (mm)", aspectmode="data"),
        height=500, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
 
# ── 2D TOP VIEW ──
st.subheader("\U0001f5fa\uFE0F 2D Top View (XY Plane)")
fig2d = go.Figure()
if gen.toolpath:
    cutting_x, cutting_y = [], []
    for i in range(1, len(tp)):
        if zs[i] < gen.safe_z - 0.1:
            cutting_x.extend([xs[i-1], xs[i], None])
            cutting_y.extend([ys[i-1], ys[i], None])
    fig2d.add_trace(go.Scatter(x=cutting_x, y=cutting_y,
        mode="lines", line=dict(color="#3498DB", width=1.5),
        name="Toolpath"))
fig2d.update_layout(xaxis_title="X (mm)", yaxis_title="Y (mm)",
    height=400, template="plotly_white",
    yaxis=dict(scaleanchor="x"))
st.plotly_chart(fig2d, use_container_width=True)
 
# ── G-CODE OUTPUT ──
st.subheader("\U0001f4c4 Generated G-Code")
st.code(gcode, language="gcode")
st.download_button("\u2B07\uFE0F Download .nc file",
    gcode, file_name="part.nc", mime="text/plain")
 
st.divider()
st.caption("CNC G-Code Generator | Robotics/CNC Module Concept | "
           "Built by Oscar Vincent Dbritto")
