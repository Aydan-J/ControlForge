"""
report_generator.py

Experiment log analyzer and Markdown report generator for ControlForge.
Calculates statistical metrics (Mean Absolute Error, Root Mean Square Error,
Max Error) between experimental log states and digital twin simulations,
computes control effort, and writes a structured report to the reports/ directory.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

try:
    from simulation.double_pendulum import DoublePendulumSimulator
except ImportError:
    # Allow local testing import
    from simulation.double_pendulum import DoublePendulumSimulator


class ReportGenerator:
    """
    Analyzes experiment CSV logs and generates detailed Markdown reports.
    """

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def analyze_log(self, log_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes the log data and compares it to a digital twin simulation.
        """
        # Validate required columns
        required = ["timestamp", "theta1", "theta2", "theta1_dot", "theta2_dot", "cart_pos", "cart_vel"]
        for col in required:
            if col not in log_df.columns:
                raise ValueError(f"Log DataFrame missing required column: {col}")

        # Compute log basics
        num_samples = len(log_df)
        duration_ms = float(log_df["timestamp"].max() - log_df["timestamp"].min())
        
        # Calculate sampling rate (Hz)
        dt_mean = float(np.mean(np.diff(log_df["timestamp"].values))) / 1000.0  # seconds
        freq_hz = 1.0 / dt_mean if dt_mean > 0 else 0.0

        # Calculate control effort
        has_control = "controller_output" in log_df.columns
        if has_control:
            control_values = log_df["controller_output"].values
            total_control_effort = float(np.sum(np.abs(control_values)))
            mean_control_effort = float(np.mean(np.abs(control_values)))
            max_control_effort = float(np.max(np.abs(control_values)))
        else:
            total_control_effort = 0.0
            mean_control_effort = 0.0
            max_control_effort = 0.0

        # Run side-by-side digital twin simulation starting from same initial conditions
        sim = DoublePendulumSimulator()
        
        # Set initial state
        sim.state.theta1 = float(log_df["theta1"].iloc[0])
        sim.state.theta2 = float(log_df["theta2"].iloc[0])
        sim.state.theta1_dot = float(log_df["theta1_dot"].iloc[0])
        sim.state.theta2_dot = float(log_df["theta2_dot"].iloc[0])
        sim.state.cart_pos = float(log_df["cart_pos"].iloc[0])
        sim.state.cart_vel = float(log_df["cart_vel"].iloc[0])

        sim_states = [sim.get_state_list()]
        
        # Sim step
        dt = dt_mean if dt_mean > 0 else 0.02
        for i in range(num_samples - 1):
            u = float(log_df["controller_output"].iloc[i]) if has_control else 0.0
            sim.step(dt=dt, control_output=u)
            sim_states.append(sim.get_state_list())

        sim_states = np.array(sim_states)
        real_states = log_df[["theta1", "theta2", "theta1_dot", "theta2_dot", "cart_pos", "cart_vel"]].values

        # Compute error metrics per state
        # states: [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]
        state_labels = ["theta1", "theta2", "theta1_dot", "theta2_dot", "cart_pos", "cart_vel"]
        error_stats = {}

        for idx, name in enumerate(state_labels):
            real_val = real_states[:, idx]
            sim_val = sim_states[:, idx]
            
            # Wrap angles for theta1 and theta2 to calculate correct differences
            if name in ["theta1", "theta2"]:
                diff = (real_val - sim_val + np.pi) % (2 * np.pi) - np.pi
            else:
                diff = real_val - sim_val

            abs_diff = np.abs(diff)
            
            error_stats[name] = {
                "mae": float(np.mean(abs_diff)),
                "rmse": float(np.sqrt(np.mean(diff**2))),
                "max_error": float(np.max(abs_diff)),
            }

        return {
            "num_samples": num_samples,
            "duration_ms": duration_ms,
            "freq_hz": freq_hz,
            "has_control": has_control,
            "total_control_effort": total_control_effort,
            "mean_control_effort": mean_control_effort,
            "max_control_effort": max_control_effort,
            "error_stats": error_stats,
            "real_states": real_states,
            "sim_states": sim_states,
        }

    def generate_report(self, log_df: pd.DataFrame, log_filename: str) -> Path:
        """
        Runs analysis and compiles the Markdown report file.
        """
        analysis = self.analyze_log(log_df)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"report_summary_{timestamp_str}.md"
        report_path = self.reports_dir / report_filename

        # Compile markdown string
        md = []
        md.append(f"# ControlForge Experiment Analysis Report")
        md.append(f"**Date Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"**Source Log File**: `{log_filename}`")
        md.append("\n## 1. Summary Statistics")
        
        md.append(f"- **Total Samples**: {analysis['num_samples']}")
        md.append(f"- **Experiment Duration**: {analysis['duration_ms']:.0f} ms ({analysis['duration_ms']/1000.0:.2f} s)")
        md.append(f"- **Average Sampling Rate**: {analysis['freq_hz']:.2f} Hz")
        
        if analysis["has_control"]:
            md.append(f"- **Total Control Effort (Absolute Sum)**: {analysis['total_control_effort']:.4f}")
            md.append(f"- **Mean Control Effort**: {analysis['mean_control_effort']:.4f}")
            md.append(f"- **Max Control Output**: {analysis['max_control_effort']:.4f}")
        else:
            md.append("- **Control Output**: N/A (Read-only / Passive run)")

        md.append("\n## 2. Digital Twin Error Comparison")
        md.append("This table shows the error metrics comparing the recorded hardware state values vs. the side-by-side digital twin simulation.")
        md.append("\n| State Variable | Mean Absolute Error (MAE) | Root Mean Square Error (RMSE) | Max Absolute Error |")
        md.append("| --- | --- | --- | --- |")

        state_display_names = {
            "theta1": "Theta 1 (rad)",
            "theta2": "Theta 2 (rad)",
            "theta1_dot": "Theta 1 Velocity (rad/s)",
            "theta2_dot": "Theta 2 Velocity (rad/s)",
            "cart_pos": "Cart Position (m)",
            "cart_vel": "Cart Velocity (m/s)"
        }

        for name, metrics in analysis["error_stats"].items():
            disp_name = state_display_names[name]
            md.append(f"| {disp_name} | {metrics['mae']:.6f} | {metrics['rmse']:.6f} | {metrics['max_error']:.6f} |")

        md.append("\n## 3. System Health Evaluation")
        
        # Simple heuristics for system diagnostic evaluation
        mae_theta1 = analysis["error_stats"]["theta1"]["mae"]
        mae_theta2 = analysis["error_stats"]["theta2"]["mae"]
        
        if mae_theta1 < 0.05 and mae_theta2 < 0.05:
            md.append("> [!SUCCESS]\n> **Status: EXCELLENT FIT**\n> The Digital Twin matches the recorded hardware logs extremely closely. Physics models and parameter calibrations are accurate.")
        elif mae_theta1 < 0.15 and mae_theta2 < 0.15:
            md.append("> [!NOTE]\n> **Status: GOOD FIT**\n> The simulation model is generally aligned with the physical hardware, but minor discrepancies exist. Consider running parameter estimation.")
        else:
            md.append("> [!WARNING]\n> **Status: HIGH DISCREPANCY DETECTED**\n> The simulated states deviate significantly from the log data. Running physical parameter estimation/calibration is recommended to tune the digital twin.")

        # Write to file
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))

        print(f"[ReportGenerator] Report successfully written to {report_path}")
        return report_path


if __name__ == "__main__":
    print("Testing ReportGenerator...")
    
    # Generate some fake log data
    rows = []
    for i in range(100):
        rows.append({
            "timestamp": i * 20.0,
            "theta1": 0.2 * np.sin(i / 10.0),
            "theta2": -0.3 * np.cos(i / 10.0),
            "theta1_dot": 0.02 * np.cos(i / 10.0),
            "theta2_dot": 0.03 * np.sin(i / 10.0),
            "cart_pos": 0.1 * np.sin(i / 20.0),
            "cart_vel": 0.005 * np.cos(i / 20.0),
            "controller_output": 0.1,
        })
    df = pd.DataFrame(rows)
    
    generator = ReportGenerator()
    path = generator.generate_report(df, "test_experiment_log.csv")
    
    # Check if report exists
    if path.exists():
        print(f"Report generated successfully!")
        with open(path, "r") as f:
            print("\nPreview of report:")
            print("".join(f.readlines()[:15]))
