"""
lqr_solver.py

Linear Quadratic Regulator (LQR) solver for the cart double pendulum.
Uses NumPy to linearize the dynamics of the double pendulum on a cart around the
upright equilibrium point and solve the Algebraic Riccati Equation (ARE)
using discrete-time Riccati iteration.
"""

import numpy as np
from typing import Tuple, List, Dict


class LQRSolver:
    """
    Computes optimal LQR gain matrix K for stabilizing a cart double pendulum.
    """

    def __init__(
        self,
        cart_mass: float = 1.5,
        link1_mass: float = 0.3,
        link2_mass: float = 0.2,
        link1_len: float = 1.3,
        link2_len: float = 1.1,
        cart_damping: float = 0.1,
        joint1_damping: float = 0.02,
        joint2_damping: float = 0.02,
        gravity: float = 9.81,
    ):
        self.M = cart_mass
        self.m1 = link1_mass
        self.m2 = link2_mass
        self.l1 = link1_len
        self.l2 = link2_len
        self.b = cart_damping
        self.d1 = joint1_damping
        self.d2 = joint2_damping
        self.g = gravity

    def get_linearized_dynamics(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Builds the linearized continuous-time A (6x6) and B (6x1) matrices
        around the upright vertical equilibrium (theta1 = pi, theta2 = pi, relative or absolute).
        
        State vector x:
            [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]
            (where theta = 0 is vertically upright for stabilization coordinates).
        """
        # Let's define the mass matrix and gravity vector for the linearized system.
        # Length variables (distance to center of mass is l/2)
        lc1 = self.l1 / 2.0
        lc2 = self.l2 / 2.0

        # Inertia moments about joint centers
        I1 = (1.0 / 12.0) * self.m1 * (self.l1**2)
        I2 = (1.0 / 12.0) * self.m2 * (self.l2**2)

        # Simplified linearized mass matrix (inertia matrix) H around upright position
        # Column variables: [theta1, theta2, cart_pos]
        # H11 = I1 + m1*lc1^2 + m2*l1^2
        # H12 = m2*l1*lc2
        # H13 = (m1*lc1 + m2*l1)
        # H21 = m2*l1*lc2
        # H22 = I2 + m2*lc2^2
        # H23 = m2*lc2
        # H31 = m1*lc1 + m2*l1
        # H32 = m2*lc2
        # H33 = M + m1 + m2
        h11 = I1 + self.m1 * (lc1**2) + self.m2 * (self.l1**2)
        h12 = self.m2 * self.l1 * lc2
        h13 = self.m1 * lc1 + self.m2 * self.l1
        
        h21 = h12
        h22 = I2 + self.m2 * (lc2**2)
        h23 = self.m2 * lc2

        h31 = h13
        h32 = h23
        h33 = self.M + self.m1 + self.m2

        H = np.array([
            [h11, h12, h13],
            [h21, h22, h23],
            [h31, h32, h33]
        ])

        # Gravity/Stiffness matrix G (linearized gravity torques/forces)
        # Upright equilibrium means gravity pulls down relative to pivots,
        # creating positive feedback (unstable stiffness).
        g11 = (self.m1 * lc1 + self.m2 * self.l1) * self.g
        g22 = self.m2 * lc2 * self.g

        G = np.array([
            [g11, 0.0, 0.0],
            [0.0, g22, 0.0],
            [0.0, 0.0, 0.0]
        ])

        # Damping matrix D
        d_11 = self.d1
        d_22 = self.d2
        d_33 = self.b

        D_mat = np.array([
            [d_11, 0.0, 0.0],
            [0.0, d_22, 0.0],
            [0.0, 0.0, d_33]
        ])

        # Force distribution vector F_dist (cart is directly actuated)
        F_dist = np.array([[0.0], [0.0], [1.0]])

        # Invert H to get accelerations
        H_inv = np.linalg.inv(H)

        # Equations:
        # q_ddot = H_inv * (G * q - D_mat * q_dot + F_dist * u)
        # Let's map q = [theta1, theta2, cart_pos]^T
        # and x = [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]^T
        
        # State-space mapping:
        # x_dot = A * x + B * u
        # A = [ 0   I ]
        #     [ H^-1*G  -H^-1*D ]
        
        A = np.zeros((6, 6))
        # Top-right 3x3 identity (positions to velocities)
        A[0, 2] = 1.0
        A[1, 3] = 1.0
        A[4, 5] = 1.0

        # Bottom-left 3x3 (gravity torques effect)
        acc_G = H_inv @ G
        # bottom-left mapping:
        # A[2, 0] = theta1_acc from theta1
        # A[2, 1] = theta1_acc from theta2
        # A[2, 4] = theta1_acc from cart_pos (0)
        A[2:4, 0:2] = acc_G[0:2, 0:2]
        A[5, 0:2] = acc_G[2, 0:2]

        # Bottom-right 3x3 (damping effect)
        acc_D = H_inv @ D_mat
        # A[2, 2] = theta1_acc from theta1_dot
        # A[2, 3] = theta1_acc from theta2_dot
        # A[2, 5] = theta1_acc from cart_vel
        A[2:4, 2:4] = -acc_D[0:2, 0:2]
        A[2:4, 5] = -acc_D[0:2, 2]
        A[5, 2:4] = -acc_D[2, 0:2]
        A[5, 5] = -acc_D[2, 2]

        # B matrix:
        # B = [ 0 ]
        #     [ H^-1 * F_dist ]
        B = np.zeros((6, 1))
        acc_F = H_inv @ F_dist
        B[2] = acc_F[0, 0]
        B[3] = acc_F[1, 0]
        B[5] = acc_F[2, 0]

        return A, B

    def solve_lqr(
        self,
        q_gains: List[float],
        r_gain: float,
        dt: float = 0.001,
        max_iter: int = 50000,
        tol: float = 1e-6,
    ) -> np.ndarray:
        """
        Solves the continuous-time LQR Algebraic Riccati Equation (ARE)
        using Riccati differential equation forward integration.
        
        q_gains: List of 6 weights for the state diagonal matrix Q.
        r_gain: Control effort cost weight R.
        """
        A, B = self.get_linearized_dynamics()

        # Build Q and R matrices
        Q = np.diag(q_gains)
        R = np.array([[r_gain]])
        R_inv = np.linalg.inv(R)

        # Integrate continuous Algebraic Riccati Equation:
        # dP/dt = A^T * P + P * A - P * B * R^-1 * B^T * P + Q
        # Start with P = Q
        P = Q.copy()
        
        for i in range(max_iter):
            dP = A.T @ P + P @ A - P @ B @ R_inv @ B.T @ P + Q
            P_next = P + dt * dP

            if np.any(np.isnan(P_next)) or np.any(np.isinf(P_next)):
                # If it diverges, reduce step size
                dt = dt * 0.5
                continue

            if np.max(np.abs(P_next - P)) < tol:
                P = P_next
                break
            P = P_next

        # Compute feedback gain matrix K = R^-1 * B^T * P
        K = R_inv @ B.T @ P

        return K.flatten()


if __name__ == "__main__":
    print("Testing LQR Solver...")
    solver = LQRSolver()
    
    A, B = solver.get_linearized_dynamics()
    print("A matrix:\n", A)
    print("\nB matrix:\n", B)

    # Q diagonal weights for [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]
    q_gains = [10.0, 10.0, 1.0, 1.0, 5.0, 1.0]
    r_gain = 0.1

    K = solver.solve_lqr(q_gains, r_gain)
    print("\nComputed LQR Gain Vector K:")
    print([round(val, 4) for val in K])
