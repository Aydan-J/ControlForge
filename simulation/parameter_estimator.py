"""
parameter_estimator.py

Parameter estimation and calibration module for the Digital Twin.
Uses Coordinate Descent optimization to find the physical parameters 
(joint damping coefficients, link lengths) that minimize the error 
between digital twin simulations and logged hardware experimental data.
"""

from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

try:
    from simulation.double_pendulum import DoublePendulumSimulator
except ImportError:
    # Allow local testing import
    from double_pendulum import DoublePendulumSimulator


class ParameterEstimator:
    """
    Fits simulator physics parameters to logged experimental trajectories.
    """

    def __init__(self, simulator: DoublePendulumSimulator = None):
        self.simulator = simulator or DoublePendulumSimulator()

    def run_simulation_trajectory(
        self,
        initial_state: List[float],
        control_inputs: List[float],
        dt: float,
        time_steps: int,
        link1_length: float,
        link2_length: float,
        theta1_damping: float,
        theta2_damping: float,
    ) -> np.ndarray:
        """
        Runs a simulation trajectory with specific parameter settings.
        Returns:
            np.ndarray of shape (time_steps, 6) containing states.
        """
        # Set parameters (damping is simplified in DoublePendulumSimulator step as damping coefficients)
        # We can temporarily patch the simulator's stepping equations or wrap it.
        # In double_pendulum.py, the damping rates are fixed:
        # self.state.theta1_dot *= 0.995
        # self.state.theta2_dot *= 0.995
        # Let's write a custom stepper that applies specific damping coefficients!
        
        self.simulator.reset()
        # Set initial states
        self.simulator.state.theta1 = initial_state[0]
        self.simulator.state.theta2 = initial_state[1]
        self.simulator.state.theta1_dot = initial_state[2]
        self.simulator.state.theta2_dot = initial_state[3]
        self.simulator.state.cart_pos = initial_state[4]
        self.simulator.state.cart_vel = initial_state[5]

        sim_states = []
        for u in control_inputs:
            # Replicate the double_pendulum.py stepping logic but with parameterized coefficients:
            # We can use theta1_damping and theta2_damping as damping factors per step (e.g. 0.995)
            
            control_output = max(-1.0, min(1.0, u))
            cart_acceleration = control_output * 0.8
            self.simulator.state.cart_vel += cart_acceleration * dt
            self.simulator.state.cart_vel *= 0.98
            self.simulator.state.cart_pos += self.simulator.state.cart_vel * dt

            # Keep fake cart inside a small visible range
            if self.simulator.state.cart_pos > 1.0:
                self.simulator.state.cart_pos = 1.0
                self.simulator.state.cart_vel *= -0.3
            if self.simulator.state.cart_pos < -1.0:
                self.simulator.state.cart_pos = -1.0
                self.simulator.state.cart_vel *= -0.3

            # Parameterized pendulum motion
            import math
            # Link lengths affect the angular acceleration scaling:
            # Acc ~ g/len * sin(theta)
            # We scale gravity acceleration coefficients by (1.3 / link1_length) and (1.1 / link2_length)
            scale1 = 1.3 / link1_length
            scale2 = 1.1 / link2_length

            theta1_acc = (
                -0.7 * scale1 * math.sin(self.simulator.state.theta1)
                + 0.15 * math.sin(self.simulator.state.theta2 - self.simulator.state.theta1)
                + 0.25 * control_output
            )

            theta2_acc = (
                -0.9 * scale2 * math.sin(self.simulator.state.theta2)
                + 0.20 * math.sin(self.simulator.state.theta1 - self.simulator.state.theta2)
                - 0.15 * control_output
            )

            self.simulator.state.theta1_dot += theta1_acc * dt
            self.simulator.state.theta2_dot += theta2_acc * dt

            # Apply damping
            self.simulator.state.theta1_dot *= theta1_damping
            self.simulator.state.theta2_dot *= theta2_damping

            self.simulator.state.theta1 += self.simulator.state.theta1_dot * dt
            self.simulator.state.theta2 += self.simulator.state.theta2_dot * dt
            
            # Wrap
            self.simulator.state.theta1 = self.simulator._wrap_angle(self.simulator.state.theta1)
            self.simulator.state.theta2 = self.simulator._wrap_angle(self.simulator.state.theta2)

            sim_states.append(self.simulator.get_state_list())

        return np.array(sim_states)

    def calculate_mse(self, real_states: np.ndarray, sim_states: np.ndarray) -> float:
        """
        Computes the Mean Squared Error for the angle states (theta1, theta2).
        """
        # Focus on theta1 (col 0) and theta2 (col 1) errors
        diff = real_states[:, 0:2] - sim_states[:, 0:2]
        # Handle wrapping differences (e.g. pi vs -pi)
        diff = (diff + np.pi) % (2 * np.pi) - np.pi
        return float(np.mean(diff**2))

    def estimate_parameters(
        self,
        log_df: pd.DataFrame,
        max_iterations: int = 50,
        learning_rate: float = 0.01,
    ) -> Tuple[Dict[str, float], List[float]]:
        """
        Estimates the parameters from log data.
        
        Returns:
            Tuple: (Best parameter dict, History of MSE values)
        """
        # Extract states and controls from log
        # Assume columns: theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel, controller_output (optional)
        real_states = log_df[["theta1", "theta2", "theta1_dot", "theta2_dot", "cart_pos", "cart_vel"]].values
        
        # Calculate time step dt
        timestamps = log_df["timestamp"].values
        dt = float(np.mean(np.diff(timestamps))) / 1000.0  # ms to seconds
        if dt <= 0 or np.isnan(dt):
            dt = 0.02

        control_inputs = log_df["controller_output"].values if "controller_output" in log_df.columns else [0.0] * len(log_df)

        initial_state = list(real_states[0])
        time_steps = len(log_df) - 1

        # Truncate real_states to match sim trajectory
        real_states_compare = real_states[1:]
        control_inputs = control_inputs[:-1]

        # Initial parameter guesses
        params = {
            "link1_length": 1.3,
            "link2_length": 1.1,
            "theta1_damping": 0.995,
            "theta2_damping": 0.995,
        }

        # Parameter search bounds
        bounds = {
            "link1_length": (0.5, 2.0),
            "link2_length": (0.5, 2.0),
            "theta1_damping": (0.95, 0.9999),
            "theta2_damping": (0.95, 0.9999),
        }

        mse_history = []

        # Run coordinate descent
        for step in range(max_iterations):
            current_sim = self.run_simulation_trajectory(
                initial_state=initial_state,
                control_inputs=control_inputs,
                dt=dt,
                time_steps=time_steps,
                **params,
            )
            current_mse = self.calculate_mse(real_states_compare, current_sim)
            mse_history.append(current_mse)

            improved = False
            # Check shifts for each parameter
            for key in params.keys():
                best_val = params[key]
                best_mse = current_mse
                
                # Try small perturbations
                perturbation = learning_rate if "length" in key else learning_rate * 0.1
                
                for shift in [-perturbation, perturbation]:
                    test_val = best_val + shift
                    # Enforce bounds
                    test_val = max(bounds[key][0], min(bounds[key][1], test_val))
                    
                    test_params = params.copy()
                    test_params[key] = test_val
                    
                    test_sim = self.run_simulation_trajectory(
                        initial_state=initial_state,
                        control_inputs=control_inputs,
                        dt=dt,
                        time_steps=time_steps,
                        **test_params,
                    )
                    test_mse = self.calculate_mse(real_states_compare, test_sim)
                    
                    if test_mse < best_mse:
                        best_mse = test_mse
                        params[key] = test_val
                        improved = True
            
            if not improved:
                # Reduce step size if stuck
                learning_rate *= 0.5
                if learning_rate < 1e-4:
                    break

        return params, mse_history


if __name__ == "__main__":
    print("Testing ParameterEstimator...")
    
    # Generate some fake log data with slightly different lengths
    sim = DoublePendulumSimulator()
    estimator = ParameterEstimator(sim)
    
    # Generate "experimental" log with actual parameters:
    # link1_length=1.4, link2_length=1.0, theta1_damping=0.992, theta2_damping=0.996
    dt = 0.02
    control_inputs = [0.1] * 100
    sim_states = estimator.run_simulation_trajectory(
        initial_state=[0.2, -0.3, 0.0, 0.0, 0.0, 0.0],
        control_inputs=control_inputs,
        dt=dt,
        time_steps=100,
        link1_length=1.4,
        link2_length=1.0,
        theta1_damping=0.992,
        theta2_damping=0.996,
    )
    
    states_log = []
    for i in range(100):
        state = sim_states[i]
        states_log.append({
            "timestamp": i * 20.0,
            "theta1": state[0],
            "theta2": state[1],
            "theta1_dot": state[2],
            "theta2_dot": state[3],
            "cart_pos": state[4],
            "cart_vel": state[5],
            "controller_output": 0.1,
        })
        
    log_df = pd.DataFrame(states_log)
    
    # Estimate parameters
    best_params, mse_history = estimator.estimate_parameters(log_df, max_iterations=30)
    
    print("\nEstimated Physics Parameters:")
    for k, v in best_params.items():
        print(f"  {k}: {v:.4f}")
    print(f"Final trajectory MSE: {mse_history[-1]:.6f}")
