from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import numpy as np

from src.domain.enums import FidelityLevel
from src.domain.plugins.interfaces import (
    DOF6Output,
    DOF6State,
    IPhysicsModelPlugin,
    StabilityCheck,
)

if TYPE_CHECKING:
    from src.domain.plugins.aerodynamic_database import AerodynamicDatabase


@dataclass
class FlexibleBodyParams:
    mode_shapes: list[np.ndarray] = field(default_factory=list)
    natural_frequencies: list[float] = field(default_factory=lambda: [10.0, 25.0, 50.0])
    damping_ratios: list[float] = field(default_factory=lambda: [0.02, 0.02, 0.02])
    modal_masses: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    modal_count: int = 3


@dataclass
class BodyDefinition:
    body_id: str
    body_type: str = "Rigid"
    mass: float = 1.0
    inertia_tensor: np.ndarray = field(default_factory=lambda: np.eye(3))
    initial_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    initial_orientation: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0, 0.0, 0.0]))
    flexible_body_params: FlexibleBodyParams | None = None


@dataclass
class JointDefinition:
    joint_id: str
    joint_type: str = "Fixed"
    parent_body_id: str = ""
    child_body_id: str = ""
    joint_axis: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 1.0]))
    joint_limits: tuple[float, float] | None = None


@dataclass
class ConstraintForce:
    joint_id: str
    force: np.ndarray = field(default_factory=lambda: np.zeros(3))
    torque: np.ndarray = field(default_factory=lambda: np.zeros(3))


@dataclass
class MultiBodyState:
    positions: dict[str, np.ndarray] = field(default_factory=dict)
    velocities: dict[str, np.ndarray] = field(default_factory=dict)
    accelerations: dict[str, np.ndarray] = field(default_factory=dict)
    orientations: dict[str, np.ndarray] = field(default_factory=dict)
    angular_velocities: dict[str, np.ndarray] = field(default_factory=dict)
    modal_coordinates: dict[str, np.ndarray] = field(default_factory=dict)
    modal_velocities: dict[str, np.ndarray] = field(default_factory=dict)
    constraint_forces: list[ConstraintForce] = field(default_factory=list)


@dataclass
class FlutterResult:
    flutter_speed: float
    flutter_frequency: float
    is_stable: bool
    velocity_damping: list[tuple[float, float]] = field(default_factory=list)
    method: str = "pk"


@dataclass
class DivergenceResult:
    divergence_speed: float
    is_divergent: bool
    critical_mode: int = 0


@dataclass
class SNCurve:
    material_id: str
    stress_cycles: list[tuple[float, float]] = field(default_factory=lambda: [
        (100e6, 1e3), (80e6, 1e4), (60e6, 1e5), (40e6, 1e6), (25e6, 1e7), (15e6, 1e8),
    ])
    endurance_limit: float = 10e6


@dataclass
class LoadSpectrum:
    stress_amplitudes: list[float] = field(default_factory=list)
    cycle_counts: list[float] = field(default_factory=list)


@dataclass
class FatigueResult:
    cumulative_damage: float
    remaining_life_ratio: float
    is_failed: bool
    confidence: str = "high"


class NewtonEulerSolver:

    def __init__(self, integration_method: str = "RK4", constraint_solver: str = "LagrangeMultiplier"):
        self.integration_method = integration_method
        self.constraint_solver = constraint_solver

    def solve(
        self,
        bodies: list[BodyDefinition],
        joints: list[JointDefinition],
        state: MultiBodyState,
        external_forces: dict[str, tuple[np.ndarray, np.ndarray]],
        dt: float,
    ) -> MultiBodyState:
        new_state = MultiBodyState()

        for body in bodies:
            pos = state.positions.get(body.body_id, body.initial_position.copy())
            vel = state.velocities.get(body.body_id, np.zeros(3))
            orient = state.orientations.get(body.body_id, body.initial_orientation.copy())
            omega = state.angular_velocities.get(body.body_id, np.zeros(3))

            F_ext, T_ext = external_forces.get(body.body_id, (np.zeros(3), np.zeros(3)))

            acc = F_ext / body.mass
            I = body.inertia_tensor
            alpha = np.linalg.solve(I, T_ext - np.cross(omega, I @ omega))

            if self.integration_method == "RK4":
                new_vel = vel + acc * dt
                new_omega = omega + alpha * dt
                new_pos = pos + new_vel * dt
                q_dot = 0.5 * self._omega_to_quat_mat(omega) @ orient
                new_orient = orient + q_dot * dt
                norm = np.linalg.norm(new_orient)
                if norm > 0:
                    new_orient = new_orient / norm
            else:
                new_vel = vel + acc * dt
                new_omega = omega + alpha * dt
                new_pos = pos + new_vel * dt
                new_orient = orient

            new_state.positions[body.body_id] = new_pos
            new_state.velocities[body.body_id] = new_vel
            new_state.accelerations[body.body_id] = acc
            new_state.orientations[body.body_id] = new_orient
            new_state.angular_velocities[body.body_id] = new_omega

        if joints:
            constraint_forces = self._compute_constraint_forces(bodies, joints, new_state, external_forces)
            new_state.constraint_forces = constraint_forces

        return new_state

    def compute_mass_matrix(self, bodies: list[BodyDefinition]) -> np.ndarray:
        n = len(bodies) * 6
        M = np.zeros((n, n))
        for i, body in enumerate(bodies):
            M[i * 6, i * 6] = body.mass
            M[i * 6 + 1, i * 6 + 1] = body.mass
            M[i * 6 + 2, i * 6 + 2] = body.mass
            I = body.inertia_tensor
            for r in range(3):
                for c in range(3):
                    M[i * 6 + 3 + r, i * 6 + 3 + c] = I[r, c]
        return M

    def compute_constraint_jacobian(self, joints: list[JointDefinition], bodies: list[BodyDefinition]) -> np.ndarray:
        n_dof = len(bodies) * 6
        n_constraints = len(joints)
        J = np.zeros((n_constraints, n_dof))

        for j_idx, joint in enumerate(joints):
            parent_idx = next((i for i, b in enumerate(bodies) if b.body_id == joint.parent_body_id), None)
            child_idx = next((i for i, b in enumerate(bodies) if b.body_id == joint.child_body_id), None)

            if parent_idx is not None:
                J[j_idx, parent_idx * 6 + 0] = 1.0
                J[j_idx, parent_idx * 6 + 1] = 1.0
                J[j_idx, parent_idx * 6 + 2] = 1.0
            if child_idx is not None:
                J[j_idx, child_idx * 6 + 0] = -1.0
                J[j_idx, child_idx * 6 + 1] = -1.0
                J[j_idx, child_idx * 6 + 2] = -1.0

        return J

    def solve_lagrange_multipliers(self, M: np.ndarray, J: np.ndarray, Q: np.ndarray) -> np.ndarray:
        n = M.shape[0]
        m = J.shape[0]
        A = np.zeros((n + m, n + m))
        A[:n, :n] = M
        A[:n, n:] = J.T
        A[n:, :n] = J
        b = np.zeros(n + m)
        b[:n] = Q
        try:
            x = np.linalg.solve(A, b)
            return x[n:]
        except np.linalg.LinAlgError:
            return np.zeros(m)

    def _compute_constraint_forces(
        self,
        bodies: list[BodyDefinition],
        joints: list[JointDefinition],
        state: MultiBodyState,
        external_forces: dict[str, tuple[np.ndarray, np.ndarray]],
    ) -> list[ConstraintForce]:
        forces: list[ConstraintForce] = []
        for joint in joints:
            parent_pos = state.positions.get(joint.parent_body_id, np.zeros(3))
            child_pos = state.positions.get(joint.child_body_id, np.zeros(3))

            diff = child_pos - parent_pos
            F_constraint = -diff * 100.0

            forces.append(ConstraintForce(
                joint_id=joint.joint_id,
                force=F_constraint,
                torque=np.zeros(3),
            ))
        return forces

    @staticmethod
    def _omega_to_quat_mat(omega: np.ndarray) -> np.ndarray:
        return np.array([
            [0, -omega[0], -omega[1], -omega[2]],
            [omega[0], 0, omega[2], -omega[1]],
            [omega[1], -omega[2], 0, omega[0]],
            [omega[2], omega[1], -omega[0], 0],
        ])


class FlexibleBodyModal:

    def __init__(self, modal_count: int = 3):
        self.modal_count = modal_count

    def compute_deformation(self, mode_shapes: list[np.ndarray], modal_coords: np.ndarray) -> np.ndarray:
        if not mode_shapes:
            return np.zeros(3)
        deformation = np.zeros_like(mode_shapes[0])
        for i in range(min(len(mode_shapes), len(modal_coords))):
            deformation += modal_coords[i] * mode_shapes[i]
        return deformation

    def step_modal_equations(
        self,
        dt: float,
        modal_coords: np.ndarray,
        modal_velocities: np.ndarray,
        params: FlexibleBodyParams,
        forces: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        n = min(self.modal_count, len(params.natural_frequencies))
        new_coords = modal_coords.copy() if len(modal_coords) >= n else np.zeros(n)
        new_vels = modal_velocities.copy() if len(modal_velocities) >= n else np.zeros(n)

        for i in range(n):
            omega_i = 2 * math.pi * params.natural_frequencies[i]
            zeta_i = params.damping_ratios[i] if i < len(params.damping_ratios) else 0.02
            m_i = params.modal_masses[i] if i < len(params.modal_masses) else 1.0

            k_i = m_i * omega_i ** 2
            c_i = 2 * zeta_i * m_i * omega_i
            F_i = forces[i] if i < len(forces) else 0.0

            eta_ddot = (F_i - c_i * new_vels[i] - k_i * new_coords[i]) / m_i
            new_vels[i] = new_vels[i] + eta_ddot * dt
            new_coords[i] = new_coords[i] + new_vels[i] * dt

        return new_coords, new_vels

    def update_local_aoa(self, deformation: np.ndarray, base_aoa: float, wing_chord: float = 1.0) -> float:
        if wing_chord <= 0 or len(deformation) < 2:
            return base_aoa
        d_aoa = math.atan2(deformation[1], wing_chord * 0.25)
        return base_aoa + d_aoa


class AeroelasticCoupler:

    def __init__(self, max_iterations: int = 20, convergence_tolerance: float = 1e-4):
        self.max_iterations = max_iterations
        self.convergence_tolerance = convergence_tolerance

    def couple_step(
        self,
        aero_db: AerodynamicDatabase | None,
        flex_solver: FlexibleBodyModal,
        flex_params: FlexibleBodyParams,
        modal_coords: np.ndarray,
        modal_velocities: np.ndarray,
        base_alpha: float,
        base_beta: float,
        mach: float,
        reynolds: float,
        dt: float,
        wing_chord: float = 1.0,
    ) -> tuple[np.ndarray, np.ndarray, bool]:
        prev_deformation = np.zeros(3)
        converged = False

        current_modal_coords = modal_coords.copy()
        current_modal_vels = modal_velocities.copy()

        for iteration in range(self.max_iterations):
            deformation = flex_solver.compute_deformation(flex_params.mode_shapes, current_modal_coords)
            local_aoa = flex_solver.update_local_aoa(deformation, base_alpha, wing_chord)

            if aero_db is not None:
                coeffs = aero_db.query_coefficients(local_aoa, base_beta, mach, reynolds)
                modal_forces = np.array([
                    coeffs.CL * 0.5 * 1.225 * 50 ** 2 * 16.0 * 0.1,
                    coeffs.CM * 0.5 * 1.225 * 50 ** 2 * 16.0 * 0.05,
                    coeffs.Cl * 0.5 * 1.225 * 50 ** 2 * 16.0 * 0.05,
                ])
            else:
                modal_forces = np.zeros(flex_solver.modal_count)

            current_modal_coords, current_modal_vels = flex_solver.step_modal_equations(
                dt, current_modal_coords, current_modal_vels, flex_params, modal_forces
            )

            new_deformation = flex_solver.compute_deformation(flex_params.mode_shapes, current_modal_coords)
            if self.check_convergence(prev_deformation, new_deformation):
                converged = True
                break
            prev_deformation = new_deformation

        if not converged:
            warnings.warn(
                "Aeroelastic coupling did not converge within max iterations — results may be inaccurate",
                stacklevel=2,
            )

        return current_modal_coords, current_modal_vels, converged

    def check_convergence(self, prev: np.ndarray, curr: np.ndarray) -> bool:
        if prev.shape != curr.shape:
            return False
        diff = np.linalg.norm(curr - prev)
        norm = max(np.linalg.norm(curr), 1e-10)
        return (diff / norm) < self.convergence_tolerance


class FlutterAnalyzer:

    def __init__(self, method: str = "pk", velocity_range: tuple[float, float] = (10.0, 200.0), velocity_step: float = 5.0):
        self.method = method
        self.velocity_range = velocity_range
        self.velocity_step = velocity_step

    def compute_flutter_speed(self, flex_params: FlexibleBodyParams, aero_db: AerodynamicDatabase | None = None) -> FlutterResult:
        if self.method == "pk":
            return self.pk_method(flex_params, aero_db)

        return FlutterResult(flutter_speed=float("inf"), flutter_frequency=0.0, is_stable=True, method="fallback")

    def pk_method(self, flex_params: FlexibleBodyParams, aero_db: AerodynamicDatabase | None = None) -> FlutterResult:
        n_modes = min(len(flex_params.natural_frequencies), flex_params.modal_count)
        if n_modes == 0:
            return FlutterResult(flutter_speed=float("inf"), flutter_frequency=0.0, is_stable=True, method="pk")

        v_range = np.arange(self.velocity_range[0], self.velocity_range[1], self.velocity_step)
        velocity_damping: list[tuple[float, float]] = []
        flutter_speed = float("inf")
        flutter_freq = 0.0
        is_stable = True

        rho = 1.225
        S = 16.0
        c = 1.6

        for V in v_range:
            q = 0.5 * rho * V ** 2

            max_damping = 0.0
            dominant_freq = 0.0

            for i in range(n_modes):
                omega_i = 2 * math.pi * flex_params.natural_frequencies[i]
                zeta_i = flex_params.damping_ratios[i] if i < len(flex_params.damping_ratios) else 0.02
                m_i = flex_params.modal_masses[i] if i < len(flex_params.modal_masses) else 1.0

                k_i = m_i * omega_i ** 2
                c_i = 2 * zeta_i * m_i * omega_i

                q_aero = q * S * c * 0.01

                effective_k = k_i - q_aero
                effective_c = c_i

                if effective_k > 0 and m_i > 0:
                    omega_eff = math.sqrt(effective_k / m_i)
                    sigma = -effective_c / (2 * m_i)
                else:
                    sigma = 0.01
                    omega_eff = omega_i

                if sigma > max_damping:
                    max_damping = sigma
                    dominant_freq = omega_eff / (2 * math.pi)

            velocity_damping.append((float(V), max_damping))

            if max_damping > 0 and is_stable:
                flutter_speed = float(V)
                flutter_freq = dominant_freq
                is_stable = False

        return FlutterResult(
            flutter_speed=flutter_speed,
            flutter_frequency=flutter_freq,
            is_stable=is_stable,
            velocity_damping=velocity_damping,
            method="pk",
        )

    def compute_divergence_speed(self, flex_params: FlexibleBodyParams) -> DivergenceResult:
        if not flex_params.natural_frequencies:
            return DivergenceResult(divergence_speed=float("inf"), is_divergent=False)

        rho = 1.225
        S = 16.0
        c = 1.6

        for i in range(len(flex_params.natural_frequencies)):
            omega_i = 2 * math.pi * flex_params.natural_frequencies[i]
            m_i = flex_params.modal_masses[i] if i < len(flex_params.modal_masses) else 1.0
            k_i = m_i * omega_i ** 2

            q_div = k_i / (S * c * 0.01)
            if q_div > 0:
                V_div = math.sqrt(2 * q_div / rho)
                return DivergenceResult(divergence_speed=V_div, is_divergent=True, critical_mode=i)

        return DivergenceResult(divergence_speed=float("inf"), is_divergent=False)


class FatigueLifePredictor:

    def __init__(self, sn_curves: dict[str, SNCurve] | None = None, miner_damage_limit: float = 1.0):
        self.sn_curves = sn_curves or {"default": SNCurve(material_id="default")}
        self.miner_damage_limit = miner_damage_limit

    def compute_cumulative_damage(self, load_spectrum: LoadSpectrum, material_id: str = "default") -> float:
        curve = self.sn_curves.get(material_id, self.sn_curves.get("default", SNCurve(material_id="default")))

        total_damage = 0.0
        for stress, cycles in zip(load_spectrum.stress_amplitudes, load_spectrum.cycle_counts):
            if stress < curve.endurance_limit:
                continue
            N = self._cycles_from_sn(stress, curve)
            if N > 0:
                total_damage += cycles / N

        return total_damage

    def predict_remaining_life(self, cumulative_damage: float, elapsed_life_ratio: float = 0.1) -> FatigueResult:
        if cumulative_damage >= self.miner_damage_limit:
            return FatigueResult(
                cumulative_damage=cumulative_damage,
                remaining_life_ratio=0.0,
                is_failed=True,
                confidence="high",
            )

        if cumulative_damage <= 0:
            return FatigueResult(
                cumulative_damage=0.0,
                remaining_life_ratio=1.0,
                is_failed=False,
                confidence="high",
            )

        remaining = (1.0 - cumulative_damage) / cumulative_damage * elapsed_life_ratio
        return FatigueResult(
            cumulative_damage=cumulative_damage,
            remaining_life_ratio=remaining,
            is_failed=False,
            confidence="high" if len(self.sn_curves) > 1 else "low",
        )

    @staticmethod
    def _cycles_from_sn(stress: float, curve: SNCurve) -> float:
        if not curve.stress_cycles:
            return 1e6

        sorted_points = sorted(curve.stress_cycles, key=lambda x: x[0], reverse=True)

        if stress >= sorted_points[0][0]:
            return sorted_points[0][1]
        if stress <= sorted_points[-1][0]:
            return float("inf")

        for i in range(len(sorted_points) - 1):
            S_high, N_high = sorted_points[i]
            S_low, N_low = sorted_points[i + 1]
            if S_low <= stress <= S_high:
                if S_high == S_low:
                    return N_high
                t = (stress - S_low) / (S_high - S_low)
                log_N = math.log10(N_low) + t * (math.log10(N_high) - math.log10(N_low))
                return 10 ** log_N

        return 1e6


class MultiBodyDynamicsModel(IPhysicsModelPlugin):

    def __init__(self, fidelity: str = "Low"):
        self.fidelity = fidelity
        self.mbd_id: str = ""
        self.bodies: list[BodyDefinition] = []
        self.joints: list[JointDefinition] = []
        self.solver = NewtonEulerSolver()
        self.flexible_body_solver: FlexibleBodyModal | None = None
        self.aeroelastic_coupler: AeroelasticCoupler | None = None
        self.flutter_analyzer: FlutterAnalyzer | None = None
        self.fatigue_predictor: FatigueLifePredictor | None = None
        self._aero_database_ref: AerodynamicDatabase | None = None
        self._state = DOF6State()
        self._mbd_state = MultiBodyState()
        self._time = 0.0
        self._params: dict[str, Any] = {}

    def initialize(self, params: dict[str, Any]) -> None:
        self._params = params
        self.mbd_id = params.get("mbd_id", "MBD-001")
        self.fidelity = params.get("fidelity", self.fidelity)

        self._state = DOF6State(
            position=[0.0, 0.0, params.get("initial_altitude", 1000.0)],
            velocity=[params.get("initial_speed", 50.0), 0.0, 0.0],
            attitude=[0.0, 0.0, 0.0],
            angular_rates=[0.0, 0.0, 0.0],
        )
        self._time = 0.0

        aero_db = params.get("aero_database_ref")
        if aero_db is not None:
            self._aero_database_ref = aero_db

        if self.fidelity == "Low":
            pass
        elif self.fidelity in ("Mid", "Detail"):
            self._build_bodies(params)

        if self.fidelity == "Mid":
            self.flexible_body_solver = FlexibleBodyModal(modal_count=2)
            self.fatigue_predictor = FatigueLifePredictor()

        if self.fidelity == "Detail":
            modal_count = params.get("modal_count", 6)
            self.flexible_body_solver = FlexibleBodyModal(modal_count=modal_count)
            self.aeroelastic_coupler = AeroelasticCoupler(
                max_iterations=params.get("aeroelastic_max_iterations", 20),
                convergence_tolerance=params.get("aeroelastic_tolerance", 1e-4),
            )
            self.flutter_analyzer = FlutterAnalyzer(
                velocity_range=tuple(params.get("flutter_velocity_range", [10.0, 200.0])),
                velocity_step=params.get("flutter_velocity_step", 5.0),
            )
            self.fatigue_predictor = FatigueLifePredictor(
                miner_damage_limit=params.get("miner_damage_limit", 1.0),
            )

    def _build_bodies(self, params: dict[str, Any]) -> None:
        n_bodies = params.get("n_bodies", 2)
        self.bodies = []
        for i in range(n_bodies):
            mass = params.get(f"body_{i}_mass", 750.0 if i == 0 else 100.0)
            Ixx = params.get(f"body_{i}_Ixx", 500.0 if i == 0 else 50.0)
            Iyy = params.get(f"body_{i}_Iyy", 1500.0 if i == 0 else 100.0)
            Izz = params.get(f"body_{i}_Izz", 1750.0 if i == 0 else 80.0)

            flex_params = None
            if i == 1 and self.fidelity in ("Mid", "Detail"):
                n_modes = 2 if self.fidelity == "Mid" else params.get("modal_count", 6)
                flex_params = FlexibleBodyParams(
                    natural_frequencies=params.get("natural_frequencies", [10.0, 25.0, 50.0, 80.0, 120.0, 180.0])[:n_modes],
                    damping_ratios=params.get("damping_ratios", [0.02] * 6)[:n_modes],
                    modal_masses=params.get("modal_masses", [1.0] * 6)[:n_modes],
                    modal_count=n_modes,
                )

            body = BodyDefinition(
                body_id=f"body_{i}",
                body_type="Flexible" if flex_params else "Rigid",
                mass=mass,
                inertia_tensor=np.diag([Ixx, Iyy, Izz]),
                initial_position=np.array([i * 2.0, 0.0, 0.0]),
                flexible_body_params=flex_params,
            )
            self.bodies.append(body)

        if n_bodies > 1:
            self.joints = [
                JointDefinition(
                    joint_id="joint_0_1",
                    joint_type="Revolute",
                    parent_body_id="body_0",
                    child_body_id="body_1",
                    joint_axis=np.array([0.0, 1.0, 0.0]),
                )
            ]

        for body in self.bodies:
            self._mbd_state.positions[body.body_id] = body.initial_position.copy()
            self._mbd_state.velocities[body.body_id] = np.zeros(3)
            self._mbd_state.orientations[body.body_id] = body.initial_orientation.copy()
            self._mbd_state.angular_velocities[body.body_id] = np.zeros(3)
            if body.flexible_body_params:
                n = body.flexible_body_params.modal_count
                self._mbd_state.modal_coordinates[body.body_id] = np.zeros(n)
                self._mbd_state.modal_velocities[body.body_id] = np.zeros(n)

    def step(self, dt: float, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        inputs = inputs or {}
        if self.fidelity == "Low":
            return self._step_low(dt, inputs)
        elif self.fidelity == "Mid":
            return self._step_mid(dt, inputs)
        elif self.fidelity == "Detail":
            return self._step_detail(dt, inputs)
        return self._step_low(dt, inputs)

    def _step_low(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        m = self._params.get("mass", 1500.0)
        S = self._params.get("wing_area", 16.0)
        V = max(math.sqrt(sum(v ** 2 for v in self._state.velocity)), 1.0)
        rho = self._isa_density(self._state.position[2])
        q_s = 0.5 * rho * V ** 2 * S

        alpha = self._compute_alpha()
        CL_alpha = self._params.get("CL_alpha", 5.0)
        CD_0 = self._params.get("CD_0", 0.02)
        k = self._params.get("k_induced", 0.05)

        CL = CL_alpha * alpha
        CD = CD_0 + k * CL ** 2

        elevator = inputs.get("elevator_cmd", 0.0)
        CL += elevator * 0.01

        L = q_s * CL
        D = q_s * CD
        T = inputs.get("thrust", self._params.get("max_thrust", 5000.0))

        phi, theta, psi = self._state.attitude
        u, v, w = self._state.velocity
        p, q, r = self._state.angular_rates

        du = (T * math.cos(alpha) - D) / m - q * w + r * v
        dv = 0.0 - r * u + p * w
        dw = (-T * math.sin(alpha) + L - m * 9.81 * math.cos(theta)) / m - p * v + q * u

        u_new = u + du * dt
        v_new = v + dv * dt
        w_new = w + dw * dt

        x_new = self._state.position[0] + u_new * dt
        y_new = self._state.position[1] + v_new * dt
        z_new = self._state.position[2] - w_new * dt

        self._state = DOF6State(
            position=[x_new, y_new, z_new],
            velocity=[u_new, v_new, w_new],
            attitude=self._state.attitude,
            angular_rates=self._state.angular_rates,
            acceleration=[du, dv, dw],
        )
        self._time += dt

        return DOF6Output(
            state=self._state,
            forces=[T * math.cos(alpha) - D, 0, -T * math.sin(alpha) + L],
            moments=[0.0, 0.0, 0.0],
            fidelity="Low",
        ).model_dump()

    def _step_mid(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        external_forces = self._compute_external_forces(inputs)

        self._mbd_state = self.solver.solve(
            self.bodies, self.joints, self._mbd_state, external_forces, dt
        )

        if self.flexible_body_solver:
            for body in self.bodies:
                if body.flexible_body_params and body.body_id in self._mbd_state.modal_coordinates:
                    modal_coords = self._mbd_state.modal_coordinates[body.body_id]
                    modal_vels = self._mbd_state.modal_velocities[body.body_id]
                    forces = np.zeros(self.flexible_body_solver.modal_count)
                    new_coords, new_vels = self.flexible_body_solver.step_modal_equations(
                        dt, modal_coords, modal_vels, body.flexible_body_params, forces
                    )
                    self._mbd_state.modal_coordinates[body.body_id] = new_coords
                    self._mbd_state.modal_velocities[body.body_id] = new_vels

        self._time += dt
        return self._build_output("Mid")

    def _step_detail(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        external_forces = self._compute_external_forces(inputs)

        self._mbd_state = self.solver.solve(
            self.bodies, self.joints, self._mbd_state, external_forces, dt
        )

        if self.flexible_body_solver and self.aeroelastic_coupler:
            alpha = self._compute_alpha()
            beta = 0.0
            V = max(math.sqrt(sum(v ** 2 for v in self._state.velocity)), 1.0)
            mach = V / self._speed_of_sound(self._state.position[2])
            rho = self._isa_density(self._state.position[2])
            c = self._params.get("chord_length", 1.6)
            reynolds = rho * V * c / self._dynamic_viscosity(self._state.position[2])

            for body in self.bodies:
                if body.flexible_body_params and body.body_id in self._mbd_state.modal_coordinates:
                    modal_coords = self._mbd_state.modal_coordinates[body.body_id]
                    modal_vels = self._mbd_state.modal_velocities[body.body_id]

                    new_coords, new_vels, converged = self.aeroelastic_coupler.couple_step(
                        self._aero_database_ref,
                        self.flexible_body_solver,
                        body.flexible_body_params,
                        modal_coords,
                        modal_vels,
                        alpha, beta, mach, reynolds, dt,
                        wing_chord=c,
                    )

                    self._mbd_state.modal_coordinates[body.body_id] = new_coords
                    self._mbd_state.modal_velocities[body.body_id] = new_vels

        self._time += dt
        return self._build_output("Detail")

    def compute_constraint_forces(self) -> list[ConstraintForce]:
        return self._mbd_state.constraint_forces

    def compute_flutter_speed(self) -> FlutterResult:
        if self.flutter_analyzer is None:
            return FlutterResult(flutter_speed=float("inf"), flutter_frequency=0.0, is_stable=True)

        flex_body = next((b for b in self.bodies if b.flexible_body_params), None)
        if flex_body is None or flex_body.flexible_body_params is None:
            return FlutterResult(flutter_speed=float("inf"), flutter_frequency=0.0, is_stable=True)

        return self.flutter_analyzer.compute_flutter_speed(flex_body.flexible_body_params, self._aero_database_ref)

    def compute_divergence_speed(self) -> DivergenceResult:
        if self.flutter_analyzer is None:
            return DivergenceResult(divergence_speed=float("inf"), is_divergent=False)

        flex_body = next((b for b in self.bodies if b.flexible_body_params), None)
        if flex_body is None or flex_body.flexible_body_params is None:
            return DivergenceResult(divergence_speed=float("inf"), is_divergent=False)

        return self.flutter_analyzer.compute_divergence_speed(flex_body.flexible_body_params)

    def predict_fatigue_life(self, load_spectrum: LoadSpectrum, material_id: str = "default") -> FatigueResult:
        if self.fatigue_predictor is None:
            return FatigueResult(cumulative_damage=0.0, remaining_life_ratio=1.0, is_failed=False, confidence="none")

        damage = self.fatigue_predictor.compute_cumulative_damage(load_spectrum, material_id)
        return self.fatigue_predictor.predict_remaining_life(damage)

    def _compute_external_forces(self, inputs: dict[str, Any]) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        forces: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for body in self.bodies:
            F = np.array([0.0, 0.0, -body.mass * 9.81])
            T = np.zeros(3)

            thrust = inputs.get("thrust", self._params.get("max_thrust", 5000.0))
            if body.body_id == "body_0":
                F[0] += thrust

            forces[body.body_id] = (F, T)
        return forces

    def _build_output(self, fidelity: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "mbd_id": self.mbd_id,
            "fidelity": fidelity,
            "time": self._time,
            "bodies": {},
        }
        for body in self.bodies:
            pos = self._mbd_state.positions.get(body.body_id, np.zeros(3))
            vel = self._mbd_state.velocities.get(body.body_id, np.zeros(3))
            body_result: dict[str, Any] = {
                "position": pos.tolist(),
                "velocity": vel.tolist(),
                "body_type": body.body_type,
            }
            if body.body_id in self._mbd_state.modal_coordinates:
                body_result["modal_coordinates"] = self._mbd_state.modal_coordinates[body.body_id].tolist()
            result["bodies"][body.body_id] = body_result

        if self._mbd_state.constraint_forces:
            result["constraint_forces"] = [
                {"joint_id": cf.joint_id, "force": cf.force.tolist()}
                for cf in self._mbd_state.constraint_forces
            ]
        return result

    def get_state(self) -> dict[str, Any]:
        return {
            "mbd_id": self.mbd_id,
            "fidelity": self.fidelity,
            "time": self._time,
            "body_count": len(self.bodies),
            "joint_count": len(self.joints),
            "bodies": {
                b.body_id: {"type": b.body_type, "mass": b.mass}
                for b in self.bodies
            },
        }

    def reset(self) -> None:
        self._state = DOF6State()
        self._mbd_state = MultiBodyState()
        for body in self.bodies:
            self._mbd_state.positions[body.body_id] = body.initial_position.copy()
            self._mbd_state.velocities[body.body_id] = np.zeros(3)
            self._mbd_state.orientations[body.body_id] = body.initial_orientation.copy()
            self._mbd_state.angular_velocities[body.body_id] = np.zeros(3)
            if body.flexible_body_params:
                n = body.flexible_body_params.modal_count
                self._mbd_state.modal_coordinates[body.body_id] = np.zeros(n)
                self._mbd_state.modal_velocities[body.body_id] = np.zeros(n)
        self._time = 0.0

    def get_supported_fidelities(self) -> list[str]:
        return [FidelityLevel.Low.value, FidelityLevel.Mid.value, FidelityLevel.High.value]

    def get_schema_references(self) -> list[str]:
        return ["AircraftStructure"]

    def validate_numerical_stability(self) -> StabilityCheck:
        for body_id, coords in self._mbd_state.modal_coordinates.items():
            if np.any(np.isnan(coords)) or np.any(np.isinf(coords)):
                return StabilityCheck(
                    is_stable=False,
                    message=f"Modal coordinate divergence detected in {body_id}",
                )
            if np.any(np.abs(coords) > 1e6):
                return StabilityCheck(
                    is_stable=False,
                    message=f"Modal coordinate magnitude excessive in {body_id}",
                )
        return StabilityCheck(is_stable=True, message="Stable")

    def _compute_alpha(self) -> float:
        u, v, w = self._state.velocity
        return math.atan2(w, max(u, 0.1))

    @staticmethod
    def _isa_density(altitude: float) -> float:
        T0 = 288.15
        P0 = 101325.0
        L = 0.0065
        g = 9.80665
        R = 287.058
        if altitude < 11000:
            T = T0 - L * max(altitude, 0)
            P = P0 * (T / T0) ** (g / (L * R))
        else:
            T11 = T0 - L * 11000
            P11 = P0 * (T11 / T0) ** (g / (L * R))
            T = T11
            P = P11 * math.exp(-g * (altitude - 11000) / (R * T11))
        return P / (R * T)

    @staticmethod
    def _speed_of_sound(altitude: float) -> float:
        T0 = 288.15
        L = 0.0065
        T = T0 - L * max(altitude, 0) if altitude < 11000 else T0 - L * 11000
        return math.sqrt(1.4 * 287.058 * T)

    @staticmethod
    def _dynamic_viscosity(altitude: float) -> float:
        T0 = 288.15
        L = 0.0065
        T = T0 - L * max(altitude, 0) if altitude < 11000 else T0 - L * 11000
        mu0 = 1.716e-5
        T_ref = 273.15 + 110.0
        S = 110.4
        return mu0 * (T / T_ref) ** 1.5 * (T_ref + S) / (T + S)