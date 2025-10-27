import contextlib
import io
from pathlib import Path

import control as ct
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from dc_motor_auto_tune import (
    dc_motor_tf,
    identify_J_b,
    tune_pid,
)


def generate_synthetic_response(
    R,
    L,
    J_true,
    b_true,
    Kt,
    Ke,
    step_mag,
    t_end,
    dt,
    include_L,
    noise_std,
    seed,
):
    """Create synthetic step-response data for identification."""
    sys = dc_motor_tf(R, L, J_true, b_true, Kt, Ke, include_L=include_L)
    t = np.arange(0.0, t_end + 1e-12, dt)
    _, y = ct.step_response(sys * step_mag, T=t)
    y = np.squeeze(y)

    if noise_std > 0.0:
        rng = np.random.default_rng(seed)
        y = y + rng.normal(0.0, noise_std, size=y.shape)

    return t, y


st.set_page_config(page_title="DC Motor Auto Tune", layout="wide")

st.title("DC Motor PID Auto-Tune")
st.write(
    "Interactive tool for identifying DC motor parameters and auto-tuning a PID controller."
)

with st.sidebar:
    st.header("Electrical Parameters")
    R = st.number_input("Resistance R (Ω)", min_value=0.0, value=1.0, step=0.1, format="%.4f")
    L = st.number_input("Inductance L (H)", min_value=0.0, value=0.5, step=0.05, format="%.4f")
    include_L = st.checkbox("Include inductance (second-order model)", value=True)

    st.header("Motor Constants")
    Kt = st.number_input("Torque constant Kt (N·m/A)", min_value=0.0, value=0.01, format="%.5f")
    Ke = st.number_input("Back-emf constant Ke (V·s/rad)", min_value=0.0, value=0.01, format="%.5f")

    st.header("Mechanical Parameters")
    identify_J = st.checkbox("Identify inertia J from data", value=False)
    if identify_J:
        J_input = -1.0
        st.caption("J will be estimated from step-response data.")
    else:
        J_input = st.number_input(
            "Inertia J (kg·m²)", min_value=1e-6, value=0.01, step=0.005, format="%.5f"
        )

    identify_b = st.checkbox("Identify viscous friction b from data", value=False)
    if identify_b:
        b_input = -1.0
        st.caption("b will be estimated from step-response data.")
    else:
        b_input = st.number_input(
            "Viscous friction b (N·m·s)", min_value=1e-6, value=0.1, step=0.01, format="%.5f"
        )

    st.header("Control Settings")
    step_mag = st.number_input("Step magnitude", min_value=0.0, value=1.0, format="%.3f")
    sim_T = st.number_input("Simulation time (s)", min_value=0.1, value=4.0, format="%.2f")
    use_d_filter = st.checkbox("Use derivative filter for Kd", value=True)
    Tf = st.number_input("Derivative filter Tf (s)", min_value=1e-4, value=0.01, format="%.4f")

needs_identification = identify_J or identify_b
data_mode = None
uploaded_file = None
synthetic_params = {}

if needs_identification:
    st.subheader("Identification Data")
    data_options = [
        "Upload CSV (t, ω)",
        "Use bundled sample (step_data.csv)",
        "Generate synthetic data",
    ]
    data_mode = st.radio("Select step-response data source", data_options)

    if data_mode == "Upload CSV (t, ω)":
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        st.caption("Provide two columns without headers: time (s), angular velocity (rad/s).")
    elif data_mode == "Generate synthetic data":
        st.markdown("Configure synthetic data to identify the unknown parameters.")
        col_synth_left, col_synth_right = st.columns(2)
        with col_synth_left:
            synthetic_params["J_true"] = st.number_input(
                "True J for simulation (kg·m²)", min_value=1e-6, value=0.01, format="%.5f"
            )
            synthetic_params["t_end"] = st.number_input(
                "Simulation length (s)", min_value=0.1, value=3.0, format="%.2f"
            )
            synthetic_params["noise_std"] = st.number_input(
                "Noise σ (rad/s)", min_value=0.0, value=0.0, format="%.4f"
            )
        with col_synth_right:
            synthetic_params["b_true"] = st.number_input(
                "True b for simulation (N·m·s)",
                min_value=1e-6,
                value=0.1,
                format="%.5f",
            )
            synthetic_params["dt"] = st.number_input(
                "Sampling period dt (s)", min_value=1e-4, value=0.01, format="%.4f"
            )
            synthetic_params["seed"] = st.number_input(
                "Noise seed", min_value=0, value=0, step=1
            )

run_clicked = st.button("Run Auto-Tune", type="primary")

if run_clicked:
    J = float(J_input)
    b = float(b_input)
    plt.close("all")

    try:
        t_data = None
        w_data = None
        identification_fig = None
        identification_summary = ""

        log_buffer = io.StringIO()
        with contextlib.redirect_stdout(log_buffer):
            if needs_identification:
                if data_mode == "Upload CSV (t, ω)":
                    if uploaded_file is None:
                        raise ValueError("Please upload a CSV file containing time and speed data.")
                    uploaded_file.seek(0)
                    data = np.loadtxt(uploaded_file, delimiter=",")
                elif data_mode == "Use bundled sample (step_data.csv)":
                    sample_path = Path(__file__).with_name("step_data.csv")
                    if not sample_path.exists():
                        raise FileNotFoundError("Bundled sample step_data.csv not found.")
                    data = np.loadtxt(sample_path, delimiter=",")
                else:
                    t_data, w_data = generate_synthetic_response(
                        R=R,
                        L=L,
                        J_true=synthetic_params["J_true"],
                        b_true=synthetic_params["b_true"],
                        Kt=Kt,
                        Ke=Ke,
                        step_mag=step_mag,
                        t_end=synthetic_params["t_end"],
                        dt=synthetic_params["dt"],
                        include_L=include_L,
                        noise_std=synthetic_params["noise_std"],
                        seed=int(synthetic_params["seed"]),
                    )
                    data = np.column_stack([t_data, w_data])
                    identification_summary = (
                        f"Synthetic dataset generated with J_true={synthetic_params['J_true']:.5f}, "
                        f"b_true={synthetic_params['b_true']:.5f}"
                    )

                if needs_identification and data_mode != "Generate synthetic data":
                    if data.ndim != 2 or data.shape[1] < 2:
                        raise ValueError("CSV must contain at least two columns: time, omega.")
                    t_data, w_data = data[:, 0], data[:, 1]

                J_hat, b_hat = identify_J_b(
                    t_data,
                    w_data,
                    R,
                    L,
                    Kt,
                    Ke,
                    step_mag,
                    include_L=include_L,
                )
                identification_fig = plt.gcf()

                if J < 0.0:
                    J = float(J_hat)
                if b < 0.0:
                    b = float(b_hat)

            G = dc_motor_tf(R, L, J, b, Kt, Ke, include_L=include_L)
            Kp_opt, Ki_opt, Kd_opt, met_best = tune_pid(
                G,
                step_mag=step_mag,
                t_end=sim_T,
                npts=1600,
                use_d_filter=use_d_filter,
                Tf=Tf,
            )
            pid_fig = plt.gcf()

        log_output = log_buffer.getvalue()

        st.success("Auto-tuning completed.")
        st.markdown(
            f"**Estimated plant parameters:** J = {J:.6f} kg·m², b = {b:.6f} N·m·s"
        )
        st.markdown(
            f"**Optimized PID gains:** Kp = {Kp_opt:.3f}, Ki = {Ki_opt:.3f}, Kd = {Kd_opt:.3f}"
        )

        if log_output:
            with st.expander("Computation log"):
                st.text(log_output.strip())

        if needs_identification and identification_fig is not None:
            st.subheader("Identification Fit")
            if identification_summary:
                st.caption(identification_summary)
            st.pyplot(identification_fig)
            plt.close(identification_fig)

        metrics_rows = [
            {"Metric": "Overshoot (%)", "Value": f"{met_best['PO']:.3f}"},
            {"Metric": "Settling time ts (s)", "Value": f"{met_best['ts']:.3f}"},
            {"Metric": "Rise time tr (s)", "Value": f"{met_best['tr']:.3f}"},
            {"Metric": "Steady-state error", "Value": f"{met_best['ess']:.6f}"},
            {"Metric": "IAE", "Value": f"{met_best['IAE']:.6f}"},
            {"Metric": "Steady-state output y_ss", "Value": f"{met_best['yss']:.6f}"},
        ]
        st.subheader("Closed-loop Performance Metrics")
        st.table(metrics_rows)

        st.subheader("Step Response Comparison")
        st.pyplot(pid_fig)
        plt.close(pid_fig)

        if needs_identification and t_data is not None and w_data is not None:
            st.subheader("Step Response Data Preview")
            fig_data, ax_data = plt.subplots()
            ax_data.plot(t_data, w_data)
            ax_data.set_xlabel("Time (s)")
            ax_data.set_ylabel("Speed (rad/s)")
            ax_data.grid(True)
            st.pyplot(fig_data)
            plt.close(fig_data)

    except Exception as exc:
        st.error(f"Auto-tuning failed: {exc}")
