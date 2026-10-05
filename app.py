import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ============================================================
# VOLTGUARD - EV BATTERY DIGITAL TWIN / BMS SIMULATOR
# ============================================================

st.set_page_config(
    page_title="VoltGuard | EV Battery Digital Twin",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- SESSION STATE --------------------

defaults = {
    "soc": 69.0,
    "temperature": 25.0,
    "current": 18.0,
    "nominal_voltage": 48.0,
    "resistance_mohm": 27.8,
    "capacity_ah": 100.0,
    "max_current": 60.0,
    "max_temperature": 60.0,
    "max_voltage": 54.6,
    "mode": "IDLE",
    "fault": "NONE",
    "running": False,
    "history": [],
    "events": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -------------------- CSS --------------------

st.markdown("""
<style>
html { scroll-behavior:smooth; }

.stApp {
    background:#080D18;
    color:#F4F7FF;
}

.block-container {
    max-width:1500px;
    padding-top:1.2rem;
    padding-bottom:3rem;
}

[data-testid="stHeader"] { background:#080D18; }

[data-testid="stSidebar"] {
    background:#0F1828;
    border-right:1px solid #26354D;
}

[data-testid="stSidebar"] * {
    color:#EAF1FC !important;
}

[data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] label {
    color:#E7EEFC !important;
}

h1,h2,h3,h4,p,label {
    color:#F4F7FF !important;
}

.brand {
    font-size:28px;
    font-weight:850;
    color:#FFFFFF !important;
}

.brand-sub {
    color:#9EACC0 !important;
    font-size:11px;
    letter-spacing:1.2px;
}

.nav-title {
    color:#8E9DB3 !important;
    font-size:11px;
    font-weight:800;
    letter-spacing:1.2px;
    margin:20px 0 8px;
}

.hero {
    background:linear-gradient(135deg,#111D30,#0C1422);
    border:1px solid #26354D;
    border-radius:22px;
    padding:28px 32px;
    margin-bottom:20px;
}

.hero-title {
    color:#FFFFFF !important;
    font-size:38px;
    font-weight:850;
}

.hero-sub {
    color:#AAB7C9 !important;
    margin-top:6px;
}

.live-pill {
    display:inline-block;
    margin-top:14px;
    padding:6px 12px;
    border-radius:20px;
    background:#103A30;
    color:#4BE1AE !important;
    font-size:12px;
    font-weight:800;
}

.metric-card {
    background:linear-gradient(145deg,#121E31,#0D1625);
    border:1px solid #273851;
    border-radius:17px;
    padding:18px;
    min-height:128px;
}

.metric-label {
    color:#91A3BC !important;
    font-size:12px;
    font-weight:750;
}

.metric-value {
    color:#FFFFFF !important;
    font-size:30px;
    font-weight:850;
    margin-top:8px;
}

.metric-note {
    color:#43DDA9 !important;
    font-size:12px;
    margin-top:5px;
}

.section-title {
    color:#FFFFFF !important;
    font-size:27px;
    font-weight:850;
    margin:28px 0 5px;
}

.section-sub {
    color:#96A4B8 !important;
    margin-bottom:16px;
}

.input-panel {
    background:#0E1726;
    border:1px solid #273851;
    border-radius:18px;
    padding:20px;
}

.input-title {
    color:#FFFFFF !important;
    font-size:20px;
    font-weight:800;
}

.stButton > button,
.stDownloadButton > button {
    width:100%;
    min-height:43px;
    border-radius:10px;
    border:1px solid #344660 !important;
    background:#152238 !important;
    color:#FFFFFF !important;
    font-weight:750;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color:#35C8FF !important;
    background:#182B45 !important;
    color:#FFFFFF !important;
}

button[kind="primary"] {
    background:#168BC1 !important;
    border-color:#168BC1 !important;
    color:#FFFFFF !important;
}

[data-baseweb="input"] {
    background:#111D2D !important;
    border-color:#30425D !important;
}

[data-baseweb="input"] input {
    color:#FFFFFF !important;
}

[data-baseweb="select"] > div {
    background:#111D2D !important;
    color:#FFFFFF !important;
    border-color:#30425D !important;
}

[data-baseweb="select"] * {
    color:#FFFFFF !important;
}

[data-testid="stDataFrame"] {
    border:1px solid #273851;
    border-radius:12px;
}

#MainMenu { visibility:hidden; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# -------------------- BATTERY MODEL --------------------

def calculate_model():
    soc = float(st.session_state.soc)
    temp = float(st.session_state.temperature)
    current = float(st.session_state.current)
    nominal = float(st.session_state.nominal_voltage)
    resistance = float(st.session_state.resistance_mohm) / 1000.0

    # Simplified educational OCV + internal-resistance model.
    ocv = nominal * (0.86 + 0.14 * soc / 100.0)
    voltage = ocv - current * resistance

    if st.session_state.fault == "VOLTAGE DROP":
        voltage -= 5.0

    voltage = max(0.0, voltage)
    voltage_drop = current * resistance
    power = voltage * current

    efficiency = max(
        0.0,
        min(100.0, 98.0 - current * 0.08 - abs(temp - 25.0) * 0.12)
    )

    pack_energy = nominal * float(st.session_state.capacity_ah) / 1000.0
    available_energy = pack_energy * soc / 100.0
    range_km = available_energy / 0.12 if available_energy > 0 else 0.0

    alerts = []

    if voltage > float(st.session_state.max_voltage):
        alerts.append("OVER-VOLTAGE")
    if current > float(st.session_state.max_current):
        alerts.append("OVER-CURRENT")
    if temp > float(st.session_state.max_temperature):
        alerts.append("OVER-TEMPERATURE")
    if soc < 15:
        alerts.append("LOW SOC")
    if st.session_state.fault != "NONE":
        alerts.append(st.session_state.fault)

    return {
        "soc": soc,
        "temperature": temp,
        "current": current,
        "nominal": nominal,
        "resistance": resistance,
        "ocv": ocv,
        "voltage": voltage,
        "voltage_drop": voltage_drop,
        "power": power,
        "efficiency": efficiency,
        "pack_energy": pack_energy,
        "available_energy": available_energy,
        "range_km": range_km,
        "alerts": list(dict.fromkeys(alerts)),
    }


def add_event(message):
    stamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.events.insert(0, f"{stamp} — {message}")
    st.session_state.events = st.session_state.events[:30]


def record(model):
    st.session_state.history.append({
        "Time": datetime.now().strftime("%H:%M:%S"),
        "SOC (%)": round(model["soc"], 2),
        "Voltage (V)": round(model["voltage"], 3),
        "Current (A)": round(model["current"], 2),
        "Temperature (°C)": round(model["temperature"], 2),
        "Power (W)": round(model["power"], 2),
        "Efficiency (%)": round(model["efficiency"], 2),
        "Mode": st.session_state.mode,
    })
    st.session_state.history = st.session_state.history[-100:]


def reset_system():
    st.session_state.soc = 69.0
    st.session_state.temperature = 25.0
    st.session_state.current = 18.0
    st.session_state.nominal_voltage = 48.0
    st.session_state.resistance_mohm = 27.8
    st.session_state.capacity_ah = 100.0
    st.session_state.mode = "IDLE"
    st.session_state.fault = "NONE"
    st.session_state.running = False
    st.session_state.history = []
    add_event("System reset")


def apply_fault(name):
    st.session_state.fault = name
    st.session_state.mode = "FAULT TEST"

    if name == "OVER-CURRENT":
        st.session_state.current = max(
            75.0, st.session_state.max_current + 15.0
        )
    elif name == "OVER-TEMPERATURE":
        st.session_state.temperature = max(
            70.0, st.session_state.max_temperature + 10.0
        )
    elif name == "LOW SOC":
        st.session_state.soc = 8.0

    add_event(f"Injected {name} fault")


# -------------------- SIDEBAR --------------------

with st.sidebar:
    st.markdown('<div class="brand">⚡ VoltGuard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-sub">EV BATTERY INTELLIGENCE LAB</div>',
        unsafe_allow_html=True
    )
    st.divider()

    if st.button(
        "▶  Start simulation",
        type="primary",
        width="stretch",
    ):
        st.session_state.running = True
        st.session_state.mode = "RUNNING"
        add_event("Live simulation started")
        st.rerun()

    if st.button("Ⅱ  Pause simulation", width="stretch"):
        st.session_state.running = False
        st.session_state.mode = "PAUSED"
        add_event("Simulation paused")
        st.rerun()

    if st.button("↺  Reset simulation", width="stretch"):
        reset_system()
        st.rerun()

    st.divider()

    side_model = calculate_model()

    if side_model["alerts"]:
        st.markdown(
            '<div class="status-danger">⚠ BMS ALERT</div>',
            unsafe_allow_html=True
        )
        st.caption(" • ".join(side_model["alerts"]))
    else:
        st.markdown(
            '<div class="status-normal">● SYSTEM NORMAL</div>',
            unsafe_allow_html=True
        )

    st.write("")
    st.caption(f"Mode: {st.session_state.mode}")
    st.caption(f"SOC: {st.session_state.soc:.0f}%")

    st.divider()
    st.markdown(
        '<div class="nav-title">FAULT TEST</div>',
        unsafe_allow_html=True
    )

    fault_choice = st.selectbox(
        "Fault condition",
        ["None", "OVER-CURRENT", "OVER-TEMPERATURE", "LOW SOC", "VOLTAGE DROP"],
        label_visibility="collapsed",
    )

    if st.button("⚠ Apply fault", width="stretch"):
        if fault_choice == "None":
            st.session_state.fault = "NONE"
            st.session_state.mode = "IDLE"
            add_event("Fault cleared")
        else:
            apply_fault(fault_choice)
        st.rerun()

    if st.button("✓ Clear fault", width="stretch"):
        st.session_state.fault = "NONE"
        st.session_state.mode = "IDLE"
        add_event("Fault cleared")
        st.rerun()


# -------------------- HEADER --------------------

st.markdown("""
<div class="hero">
    <div class="hero-title">⚡ VoltGuard</div>
    <div class="hero-sub">EV BATTERY MANAGEMENT • LIVE DIGITAL TWIN</div>
    <div class="live-pill">● SOFTWARE SIMULATION</div>
</div>
""", unsafe_allow_html=True)


# -------------------- LIVE SIMULATION AREA --------------------
# Everything in this fragment refreshes every second when running.
# This makes the circuit, values and graphs actually move together.

@st.fragment(run_every="1s" if st.session_state.running else None)
def live_simulation():

    # Update the model first.
    model = calculate_model()

    if st.session_state.running:
        # Illustrative discharge.
        soc_loss = max(0.01, model["current"] / 3600.0 * 2.0)
        st.session_state.soc = max(0.0, st.session_state.soc - soc_loss)

        # Illustrative thermal response.
        target_temp = 25.0 + (model["current"] / 100.0) ** 2 * 45.0
        st.session_state.temperature += (
            target_temp - st.session_state.temperature
        ) * 0.08

        model = calculate_model()
        record(model)

        if st.session_state.soc <= 0:
            st.session_state.running = False
            st.session_state.mode = "EMPTY"
            add_event("Battery reached 0% SOC")

    # -------- Metrics --------
    m1, m2, m3, m4 = st.columns(4)

    def card(label, value, note):
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with m1:
        card("STATE OF CHARGE", f'{model["soc"]:.1f}%', "Battery energy level")
    with m2:
        card("PACK VOLTAGE", f'{model["voltage"]:.2f} V',
             "Estimated terminal voltage")
    with m3:
        card("LOAD CURRENT", f'{model["current"]:.1f} A',
             f'Power: {model["power"]:.0f} W')
    with m4:
        card("CELL TEMPERATURE", f'{model["temperature"]:.1f} °C',
             f'Efficiency: {model["efficiency"]:.1f}%')

    # -------- Circuit --------

    st.markdown(
        '<div class="section-title">Interactive battery simulation</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-sub">Live equivalent-circuit response</div>',
        unsafe_allow_html=True
    )

    circuit_color = "#FF647C" if model["alerts"] else "#35C8FF"

    svg = f"""
    <div style="background:#090F1A;border:1px solid #293A55;
                border-radius:20px;padding:8px;">
    <svg viewBox="0 0 1000 350" width="100%" height="350"
         xmlns="http://www.w3.org/2000/svg">

    <style>
    .wire {{stroke:{circuit_color};stroke-width:5;fill:none;
            stroke-linecap:round;stroke-linejoin:round;}}
    .box {{fill:#142238;stroke:#607894;stroke-width:2;}}
    .label {{fill:#AFC0D7;font-size:17px;font-family:Arial;}}
    .value {{fill:#FFFFFF;font-size:22px;font-weight:bold;font-family:Arial;}}
    .green {{fill:#43DDA9;font-size:25px;font-weight:bold;font-family:Arial;}}
    .dot {{fill:{circuit_color};}}
    @keyframes pulse {{0%,100%{{opacity:.25;}}50%{{opacity:1;}}}}
    .moving {{animation:pulse 1s infinite;}}
    </style>

    <text x="55" y="45" class="label">BATTERY</text>
    <text x="300" y="45" class="label">INTERNAL RESISTANCE</text>
    <text x="560" y="45" class="label">POLARIZATION MODEL</text>

    <path class="wire" d="M90 135 H225"/>
    <path class="wire" d="M90 135 V235 H870 V135 H800"/>

    <line x1="65" y1="150" x2="115" y2="150"
          stroke="{circuit_color}" stroke-width="6"/>
    <line x1="55" y1="177" x2="125" y2="177"
          stroke="{circuit_color}" stroke-width="10"/>
    <line x1="65" y1="204" x2="115" y2="204"
          stroke="{circuit_color}" stroke-width="6"/>

    <rect x="225" y="108" width="125" height="55" rx="10" class="box"/>
    <text x="287" y="143" text-anchor="middle" class="value">
    R₀ = {model["resistance"]*1000:.1f} mΩ
    </text>

    <rect x="470" y="108" width="160" height="55" rx="10" class="box"/>
    <text x="550" y="143" text-anchor="middle" class="value">
    Rₚ ‖ Cₚ
    </text>

    <path class="wire" d="M350 135 H470"/>
    <path class="wire" d="M630 135 H800"/>

    <text x="135" y="165" class="green">{model["voltage"]:.2f} V</text>

    <text x="800" y="105" class="label">TERMINAL VOLTAGE</text>
    <text x="800" y="137" class="green">{model["voltage"]:.2f} V</text>

    <text x="800" y="185" class="label">LOAD CURRENT</text>
    <text x="800" y="217" class="value">{model["current"]:.1f} A</text>

    <circle cx="175" cy="235" r="8" class="dot moving"/>
    <circle cx="390" cy="235" r="8" class="dot moving"/>
    <circle cx="610" cy="235" r="8" class="dot moving"/>

    <text x="80" y="300" class="label">SOC: {model["soc"]:.1f}%</text>
    <text x="355" y="300" class="label">
    Temperature: {model["temperature"]:.1f} °C
    </text>
    <text x="700" y="300" class="label">
    ΔV: {model["voltage_drop"]:.3f} V
    </text>
    </svg>
    </div>
    """

    st.components.v1.html(svg, height=370)

    # -------- USER INPUTS DIRECTLY BELOW SIMULATION --------

    st.markdown(
        '<div class="section-title">Simulation parameters</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-sub">Move the sliders or type exact values. '
        'Click Apply Values to update the digital twin.</div>',
        unsafe_allow_html=True
    )

    with st.container(border=True):
        st.markdown(
            '<div class="input-title">🎛 User-controlled battery inputs</div>',
            unsafe_allow_html=True
        )

        a, b, c = st.columns(3)

        with a:
            new_soc = st.slider(
                "State of Charge (%)",
                0.0, 100.0,
                float(st.session_state.soc),
                1.0,
                key="sim_soc"
            )

        with b:
            new_temp = st.slider(
                "Cell Temperature (°C)",
                -10.0, 100.0,
                float(st.session_state.temperature),
                1.0,
                key="sim_temp"
            )

        with c:
            new_current = st.slider(
                "Load Current (A)",
                0.0, 100.0,
                float(st.session_state.current),
                1.0,
                key="sim_current"
            )

        d, e, f = st.columns(3)

        with d:
            new_voltage = st.number_input(
                "Nominal Pack Voltage (V)",
                12.0, 1000.0,
                float(st.session_state.nominal_voltage),
                1.0,
                key="sim_voltage"
            )

        with e:
            new_resistance = st.number_input(
                "Internal Resistance (mΩ)",
                1.0, 500.0,
                float(st.session_state.resistance_mohm),
                0.5,
                key="sim_resistance"
            )

        with f:
            new_capacity = st.number_input(
                "Battery Capacity (Ah)",
                1.0, 1000.0,
                float(st.session_state.capacity_ah),
                1.0,
                key="sim_capacity"
            )

        if st.button(
            "⚡ APPLY VALUES TO SIMULATION",
            type="primary",
            width="stretch",
        ):
            st.session_state.soc = new_soc
            st.session_state.temperature = new_temp
            st.session_state.current = new_current
            st.session_state.nominal_voltage = new_voltage
            st.session_state.resistance_mohm = new_resistance
            st.session_state.capacity_ah = new_capacity
            st.session_state.fault = "NONE"
            st.session_state.mode = "CUSTOM"
            add_event("User simulation values applied")
            st.rerun()

    # -------- Safety monitor --------

    model = calculate_model()

    st.markdown(
        '<div class="section-title">Battery safety monitor</div>',
        unsafe_allow_html=True
    )

    if model["alerts"]:
        for alert in model["alerts"]:
            st.error(f"⚠ {alert}")
    else:
        st.success(
            "● Battery parameters are within the illustrative warning limits."
        )

    # -------- Energy --------

    e1, e2, e3, e4 = st.columns(4)

    with e1:
        card("PACK ENERGY", f'{model["pack_energy"]:.2f} kWh',
             "Nominal stored energy")

    with e2:
        card("AVAILABLE ENERGY", f'{model["available_energy"]:.2f} kWh',
             "Based on current SOC")

    with e3:
        card("POWER", f'{model["power"]/1000:.2f} kW',
             "Voltage × current")

    with e4:
        card("ESTIMATED RANGE", f'{model["range_km"]:.1f} km',
             "Using 120 Wh/km model")

    # -------- 12-cell monitor --------

    st.markdown(
        '<div class="section-title">12-cell battery pack</div>',
        unsafe_allow_html=True
    )

    base_cell = model["voltage"] / 12.0
    offsets = [
        -0.018, 0.012, -0.009, 0.021,
        -0.006, 0.008, -0.014, 0.016,
        -0.004, 0.011, -0.012, -0.005
    ]

    cells = [base_cell + x for x in offsets]

    if st.session_state.fault == "VOLTAGE DROP":
        cells[8] -= 0.08

    cell_cols = st.columns(6)

    for i, value in enumerate(cells):
        with cell_cols[i % 6]:
            st.markdown(
                f"""
                <div class="metric-card"
                     style="min-height:90px;padding:12px;text-align:center;">
                    <div class="metric-label">CELL {i+1:02d}</div>
                    <div class="metric-value" style="font-size:19px;">
                        {value:.3f} V
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # -------- Charts --------

    st.markdown(
        '<div class="section-title">Battery analytics</div>',
        unsafe_allow_html=True
    )

    if not st.session_state.history:
        record(model)

    df = pd.DataFrame(st.session_state.history)

    left, right = st.columns(2)

    with left:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["Time"],
            y=df["SOC (%)"],
            mode="lines+markers",
            name="SOC",
            line=dict(color="#35C8FF", width=3),
        ))
        fig.add_trace(go.Scatter(
            x=df["Time"],
            y=df["Voltage (V)"],
            mode="lines",
            name="Voltage",
            line=dict(color="#43DDA9", width=2),
            yaxis="y2",
        ))
        fig.update_layout(
            title="SOC & terminal voltage",
            paper_bgcolor="#0E1726",
            plot_bgcolor="#0E1726",
            font=dict(color="#E8EEF9"),
            height=350,
            margin=dict(l=20, r=20, t=55, b=30),
            xaxis=dict(showgrid=False),
            yaxis=dict(
                title="SOC (%)",
                range=[0, 100],
                gridcolor="#243149"
            ),
            yaxis2=dict(
                title="Voltage (V)",
                overlaying="y",
                side="right",
                showgrid=False
            ),
        )
        st.plotly_chart(fig, width="stretch")

    with right:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df["Time"],
            y=df["Current (A)"],
            mode="lines+markers",
            name="Current",
            line=dict(color="#FFB454", width=3),
        ))
        fig2.add_trace(go.Scatter(
            x=df["Time"],
            y=df["Temperature (°C)"],
            mode="lines",
            name="Temperature",
            line=dict(color="#FF647C", width=3),
            yaxis="y2",
        ))
        fig2.update_layout(
            title="Load & thermal response",
            paper_bgcolor="#0E1726",
            plot_bgcolor="#0E1726",
            font=dict(color="#E8EEF9"),
            height=350,
            margin=dict(l=20, r=20, t=55, b=30),
            xaxis=dict(showgrid=False),
            yaxis=dict(
                title="Current (A)",
                gridcolor="#243149"
            ),
            yaxis2=dict(
                title="Temperature (°C)",
                overlaying="y",
                side="right",
                showgrid=False
            ),
        )
        st.plotly_chart(fig2, width="stretch")


live_simulation()


# -------------------- DATA LOG --------------------

st.markdown(
    '<div class="section-title">Measurement history</div>',
    unsafe_allow_html=True
)

if st.session_state.history:
    df_all = pd.DataFrame(st.session_state.history)

    st.dataframe(
        df_all.tail(20),
        width="stretch",
        hide_index=True
    )

    st.download_button(
        "⬇ Download measurement CSV",
        data=df_all.to_csv(index=False).encode("utf-8"),
        file_name="voltguard_measurements.csv",
        mime="text/csv",
        width="stretch"
    )
else:
    st.info("No readings recorded yet.")


# -------------------- EVENT LOG --------------------

st.markdown(
    '<div class="section-title">Event log</div>',
    unsafe_allow_html=True
)

if st.session_state.events:
    for item in st.session_state.events:
        st.markdown(
            f"""
            <div style="
                background:#0E1726;
                border:1px solid #273851;
                border-left:4px solid #35C8FF;
                border-radius:9px;
                padding:10px 13px;
                margin:6px 0;
                color:#DDE7F8;">
                ● {item}
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.caption("No events yet.")


st.markdown(
    """
    <div style="text-align:center;color:#718096;font-size:12px;
                padding:35px 0 10px;">
        ⚡ VoltGuard • Educational EV Battery Digital Twin
        <br>
        Simplified software model — not a certified BMS or real battery
        protection controller.
    </div>
    """,
    unsafe_allow_html=True
)
