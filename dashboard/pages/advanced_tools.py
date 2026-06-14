"""
dashboard/pages/advanced_tools.py

Advanced control systems utility page.
Integrates the newly added safety manager, LQR Riccati solver, digital twin 
parameter estimator, and experiment report compiler into the ControlForge dashboard.
"""

from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import time

# Imports of new modules
from backend.safety_manager import SafetyManager, SafetyStatus
from controllers.lqr_solver import LQRSolver
from simulation.parameter_estimator import ParameterEstimator
from reports.report_generator import ReportGenerator

# Safety manager instance stored in session state to persist ESTOP state
if "safety_manager" not in st.session_state:
    st.session_state.safety_manager = SafetyManager()


def render_lqr_solver_tab() -> None:
    st.subheader("Optimal LQR Feedback Gain Calculator")
    st.caption("Linearizes the system around the upright equilibrium and solves the continuous-time Algebraic Riccati Equation.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.write("**Physical Parameters**")
        cart_mass = st.number_input("Cart Mass (M)", min_value=0.1, max_value=10.0, value=1.5, step=0.1)
        link1_mass = st.number_input("Link 1 Mass (m1)", min_value=0.01, max_value=5.0, value=0.3, step=0.05)
        link2_mass = st.number_input("Link 2 Mass (m2)", min_value=0.01, max_value=5.0, value=0.2, step=0.05)
        link1_length = st.number_input("Link 1 Length (l1)", min_value=0.1, max_value=5.0, value=1.3, step=0.1)
        link2_length = st.number_input("Link 2 Length (l2)", min_value=0.1, max_value=5.0, value=1.1, step=0.1)
        
        st.write("**Damping Coefficients**")
        cart_damping = st.number_input("Cart Damping (b)", min_value=0.0, max_value=2.0, value=0.1, step=0.05)
        joint1_damping = st.number_input("Joint 1 Damping (d1)", min_value=0.0, max_value=1.0, value=0.02, step=0.01)
        joint2_damping = st.number_input("Joint 2 Damping (d2)", min_value=0.0, max_value=1.0, value=0.02, step=0.01)

    with col2:
        st.write("**LQR Optimization Weights**")
        st.caption("Define the penalty diagonal values for state vector Q: [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]")
        
        q_theta1 = st.slider("Q - Theta 1 (Angle 1)", 0.0, 100.0, 10.0, 1.0)
        q_theta2 = st.slider("Q - Theta 2 (Angle 2)", 0.0, 100.0, 10.0, 1.0)
        q_theta1_dot = st.slider("Q - Theta 1 Dot (Vel 1)", 0.0, 50.0, 1.0, 0.5)
        q_theta2_dot = st.slider("Q - Theta 2 Dot (Vel 2)", 0.0, 50.0, 1.0, 0.5)
        q_cart_pos = st.slider("Q - Cart Position", 0.0, 100.0, 5.0, 0.5)
        q_cart_vel = st.slider("Q - Cart Velocity", 0.0, 50.0, 1.0, 0.5)
        
        r_gain = st.number_input("R - Control Input Cost Penalty", min_value=0.001, max_value=10.0, value=0.1, step=0.05)

    solve_clicked = st.button("Solve Algebraic Riccati Equation", type="primary")

    if solve_clicked:
        solver = LQRSolver(
            cart_mass=cart_mass,
            link1_mass=link1_mass,
            link2_mass=link2_mass,
            link1_len=link1_length,
            link2_len=link2_length,
            cart_damping=cart_damping,
            joint1_damping=joint1_damping,
            joint2_damping=joint2_damping
        )
        
        q_gains = [q_theta1, q_theta2, q_theta1_dot, q_theta2_dot, q_cart_pos, q_cart_vel]
        
        with st.spinner("Solving ARE..."):
            K = solver.solve_lqr(q_gains, r_gain)
            A, B = solver.get_linearized_dynamics()
            
        st.success("LQR Gains Successfully Calculated!")
        
        # Display gains
        st.write("**Optimal Feedback Gain Vector K**:")
        gain_df = pd.DataFrame({
            "State Variable": ["Theta 1 (Angle 1)", "Theta 2 (Angle 2)", "Theta 1 Velocity", "Theta 2 Velocity", "Cart Position", "Cart Velocity"],
            "Gain Value (K)": K
        })
        st.table(gain_df)
        
        st.write("**Linearized State Space A Matrix (6x6)**:")
        st.dataframe(pd.DataFrame(A))
        
        st.write("**Linearized Input B Matrix (6x1)**:")
        st.dataframe(pd.DataFrame(B))

        # Store calculated gains in session state for control panel use
        st.session_state.calculated_lqr_gains = list(K)
        st.info("These gains are now saved. You can manually copy these values into the LQR panel for simulation testing.")


def render_parameter_estimator_tab() -> None:
    st.subheader("Digital Twin Physics Calibration")
    st.caption("Aligns physical properties of the simulator with hardware logs using Coordinate Descent error minimization.")

    uploaded_file = st.file_uploader("Upload recorded CSV log", type=["csv"], key="param_est_upload")
    
    # Generate simple demo log if no file uploaded
    use_demo = st.checkbox("Or use demo experiment log file", value=True)
    
    if uploaded_file is None and not use_demo:
        st.info("Upload a CSV log or select the demo checkmark above to run calibration.")
        return

    if use_demo:
        # Load a default log or generate mock calibration data
        # Let's generate a mock trajectory with length 1.45 and joint damping 0.993
        rows = []
        for i in range(120):
            rows.append({
                "timestamp": i * 20.0,
                "theta1": 0.3 * np.sin(i / 12.0),
                "theta2": -0.4 * np.cos(i / 15.0),
                "theta1_dot": 0.02 * np.cos(i / 12.0),
                "theta2_dot": 0.03 * np.sin(i / 15.0),
                "cart_pos": 0.05 * np.sin(i / 25.0),
                "cart_vel": 0.002 * np.cos(i / 25.0),
                "controller_output": 0.15,
            })
        df = pd.DataFrame(rows)
        st.write("Using simulated demo experiment log (120 frames).")
    else:
        df = pd.read_csv(uploaded_file)
        
    st.write("**Log preview**:")
    st.dataframe(df.head(5), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        max_iter = st.slider("Max Calibration Iterations", 10, 100, 30, 5)
    with col2:
        learning_rate = st.selectbox("Learning Rate Step Size", [0.005, 0.01, 0.02, 0.05], index=1)

    calibrate_clicked = st.button("Run Parameter Estimator", type="primary")

    if calibrate_clicked:
        estimator = ParameterEstimator()
        
        with st.spinner("Calibrating Digital Twin parameters..."):
            best_params, mse_history = estimator.estimate_parameters(df, max_iterations=max_iter, learning_rate=learning_rate)
            
        st.success("Calibration Finished!")
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write("**Estimated Physical Properties**:")
            res_df = pd.DataFrame({
                "Parameter Name": ["Link 1 Length", "Link 2 Length", "Theta 1 Damping Factor", "Theta 2 Damping Factor"],
                "Calibrated Value": [best_params["link1_length"], best_params["link2_length"], best_params["theta1_damping"], best_params["theta2_damping"]],
                "Default Value": [1.3, 1.1, 0.995, 0.995]
            })
            st.table(res_df)
            
        with col_res2:
            st.write("**Mean Squared Error (MSE) Convergence**:")
            st.line_chart(pd.DataFrame({"MSE": mse_history}))
            st.write(f"Initial MSE: {mse_history[0]:.6f} | Final MSE: {mse_history[-1]:.6f}")


def render_safety_watchdog_tab() -> None:
    st.subheader("Hardware Safety Watchdog & ESTOP Control")
    
    safety_mgr = st.session_state.safety_manager
    status = safety_mgr.status
    
    # Display large safety banners
    if status == SafetyStatus.SAFE:
        st.success("### SYSTEM STATUS: SAFE (Motor Output Permitted)")
    elif status == SafetyStatus.ESTOP_LIMIT_EXCEEDED:
        st.error(f"### SYSTEM STATUS: ESTOP ACTIVE!\n**Reason**: Safety Boundary Exceeded\n\n`{safety_mgr.trigger_cause}`")
    elif status == SafetyStatus.ESTOP_MANUAL:
        st.error(f"### SYSTEM STATUS: ESTOP ACTIVE!\n**Reason**: Manual E-stop Triggered by Operator")

    # Safety metrics
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Operational Limits Settings**")
        pos_lim = st.slider("Cart Position Bounds (m)", 0.5, 2.5, 1.5, 0.1)
        vel_lim = st.slider("Cart Velocity Limit (m/s)", 1.0, 5.0, 3.0, 0.5)
        
        safety_mgr.cart_pos_min = -pos_lim
        safety_mgr.cart_pos_max = pos_lim
        safety_mgr.cart_vel_max = vel_lim

    with col2:
        st.write("**Joint Velocity Limits**")
        j1_vel_lim = st.slider("Theta 1 Velocity Limit (rad/s)", 5.0, 20.0, 12.0, 1.0)
        j2_vel_lim = st.slider("Theta 2 Velocity Limit (rad/s)", 5.0, 25.0, 15.0, 1.0)
        
        safety_mgr.theta1_vel_max = j1_vel_lim
        safety_mgr.theta2_vel_max = j2_vel_lim

    st.write("---")
    
    # Action buttons
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        estop_clicked = st.button("🔴 TRIGGER EMERGENCY STOP (ESTOP)", use_container_width=True, type="secondary")
        if estop_clicked:
            safety_mgr.trigger_manual_estop()
            st.rerun()
            
    with col_btn2:
        reset_clicked = st.button("🟢 RESET SAFETY ESTOP", use_container_width=True, type="primary")
        if reset_clicked:
            safety_mgr.reset_estop()
            st.rerun()


def render_report_compiler_tab() -> None:
    st.subheader("Experiment Report Compiler")
    st.caption("Processes recorded CSV log files and compiles a comprehensive Markdown report saved to the reports/ folder.")

    uploaded_file = st.file_uploader("Select log file to analyze", type=["csv"], key="report_upload")
    use_demo = st.checkbox("Use demo log for report compilation", value=True)

    if uploaded_file is None and not use_demo:
        st.info("Upload a CSV log or select the demo checkmark above to run compilation.")
        return

    if use_demo:
        # Recreate similar dataframe
        rows = []
        for i in range(150):
            rows.append({
                "timestamp": i * 20.0,
                "theta1": 0.25 * np.sin(i / 15.0) + 0.02 * np.random.randn(),
                "theta2": -0.35 * np.cos(i / 18.0) + 0.02 * np.random.randn(),
                "theta1_dot": 0.05 * np.sin(i / 8.0),
                "theta2_dot": 0.05 * np.cos(i / 10.0),
                "cart_pos": 0.01 * np.sin(i / 20.0),
                "cart_vel": 0.02 * np.cos(i / 20.0),
                "controller_output": 0.1,
            })
        df = pd.DataFrame(rows)
        filename = "demo_experiment_log.csv"
    else:
        df = pd.read_csv(uploaded_file)
        filename = uploaded_file.name

    compile_clicked = st.button("Compile Analytical Report", type="primary")

    if compile_clicked:
        generator = ReportGenerator()
        
        with st.spinner("Generating analytical report..."):
            report_path = generator.generate_report(df, filename)
            
        st.success(f"Report Successfully Compiled!")
        st.info(f"Saved to: `{report_path}`")
        
        st.write("### Report Preview:")
        # Read the file to display in st.markdown
        with open(report_path, "r", encoding="utf-8") as f:
            md_content = f.read()
            
        st.markdown(md_content)


def render_advanced_tools_page() -> None:
    st.title("ControlForge Advanced Tools")
    st.caption("Specialized utility suite for LQR solvers, physical calibrations, watchdogs, and report generators.")

    # Show warning if ESTOP active
    safety_mgr = st.session_state.safety_manager
    if safety_mgr.status != SafetyStatus.SAFE:
        st.error(f"🚨 WARNING: EMERGENCY STOP (ESTOP) ACTIVE! Reason: {safety_mgr.trigger_cause or 'Manual trigger'}")

    tabs = st.tabs(["LQR Solver", "Parameter Estimator", "Safety Watchdog", "Report Compiler"])

    with tabs[0]:
        render_lqr_solver_tab()
        
    with tabs[1]:
        render_parameter_estimator_tab()
        
    with tabs[2]:
        render_safety_watchdog_tab()
        
    with tabs[3]:
        render_report_compiler_tab()


if __name__ == "__main__":
    st.set_page_config(page_title="ControlForge Advanced Tools", layout="wide")
    render_advanced_tools_page()
