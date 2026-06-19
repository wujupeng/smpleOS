from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.domain.enums import FidelityLevel
from src.domain.plugins.interfaces import (
    BatteryOutput,
    BatteryState,
    IPhysicsModelPlugin,
    StabilityCheck,
)


@dataclass
class CellState:
    terminal_voltage: float = 0.0
    current: float = 0.0
    soc: float = 1.0
    soh: float = 1.0
    temperature: float = 25.0
    v_rc1: float = 0.0
    v_rc2: float = 0.0
    is_faulty: bool = False
    is_isolated: bool = False


@dataclass
class ThermalParams:
    cell_mass: float = 0.046
    cell_Cp: float = 1000.0
    cooling_coeff: float = 10.0
    cooling_area: float = 0.006


@dataclass
class AgingParams:
    calendar_aging_A: float = 1e-4
    calendar_aging_Ea: float = 50000.0
    cycle_aging_B: float = 1e-5
    cycle_aging_z: float = 0.5


@dataclass
class OCVSOCurve:
    points: list[tuple[float, float]] = field(default_factory=lambda: [
        (0.0, 3.0), (0.1, 3.3), (0.2, 3.5), (0.3, 3.6), (0.4, 3.7),
        (0.5, 3.8), (0.6, 3.9), (0.7, 4.0), (0.8, 4.05), (0.9, 4.1), (1.0, 4.2),
    ])

    def ocv(self, soc: float) -> float:
        soc = max(0.0, min(1.0, soc))
        for i in range(len(self.points) - 1):
            s0, v0 = self.points[i]
            s1, v1 = self.points[i + 1]
            if s0 <= soc <= s1:
                t = (soc - s0) / (s1 - s0) if s1 != s0 else 0.0
                return v0 + t * (v1 - v0)
        return self.points[-1][1] if soc > self.points[-1][0] else self.points[0][1]

    def docv_dsoc(self, soc: float) -> float:
        soc = max(0.0, min(1.0, soc))
        for i in range(len(self.points) - 1):
            s0, v0 = self.points[i]
            s1, v1 = self.points[i + 1]
            if s0 <= soc <= s1:
                return (v1 - v0) / (s1 - s0) if s1 != s0 else 0.0
        return 0.0


class CellModel:

    def __init__(
        self,
        cell_id: str,
        chemistry: str = "NMC",
        capacity: float = 3.5,
        nominal_voltage: float = 3.7,
        r0: float = 0.02,
        r1: float = 0.01,
        tau1: float = 10.0,
        r2: float = 0.005,
        tau2: float = 100.0,
        ocv_table: OCVSOCurve | None = None,
        thermal_params: ThermalParams | None = None,
        aging_params: AgingParams | None = None,
    ):
        self.cell_id = cell_id
        self.chemistry = chemistry
        self.capacity = capacity
        self.nominal_voltage = nominal_voltage
        self.r0 = r0
        self.r1 = r1
        self.tau1 = tau1
        self.r2 = r2
        self.tau2 = tau2
        self.ocv_table = ocv_table or OCVSOCurve()
        self.thermal_params = thermal_params or ThermalParams()
        self.aging_params = aging_params or AgingParams()
        self.state = CellState()
        self._time = 0.0

    def step(self, dt: float, current: float, T_amb: float = 25.0) -> CellState:
        if self.state.is_isolated:
            self.state.current = 0.0
            return self.state

        I = current
        OCV = self.ocv_table.ocv(self.state.soc)

        v_rc1_new = self.state.v_rc1 * math.exp(-dt / self.tau1) + self.r1 * I * (1 - math.exp(-dt / self.tau1))
        v_rc2_new = self.state.v_rc2 * math.exp(-dt / self.tau2) + self.r2 * I * (1 - math.exp(-dt / self.tau2))

        V_terminal = self.compute_terminal_voltage(I, OCV, v_rc1_new, v_rc2_new)

        self.state.soc = self.estimate_soc(I, dt)

        if abs(I) < 0.01 and self._time > 60:
            ocv_measured = V_terminal + I * self.r0
            soc_from_ocv = self._soc_from_ocv(ocv_measured)
            if soc_from_ocv is not None:
                self.state.soc = 0.7 * self.state.soc + 0.3 * soc_from_ocv

        self.state.soh = self.estimate_soh(I, dt)

        self.state.temperature = self.compute_temperature(I, T_amb, dt, v_rc1_new, v_rc2_new)

        self.state.terminal_voltage = V_terminal
        self.state.current = I
        self.state.v_rc1 = v_rc1_new
        self.state.v_rc2 = v_rc2_new
        self._time += dt

        return self.state

    def compute_terminal_voltage(self, I: float, OCV: float | None = None, v_rc1: float | None = None, v_rc2: float | None = None) -> float:
        if OCV is None:
            OCV = self.ocv_table.ocv(self.state.soc)
        if v_rc1 is None:
            v_rc1 = self.state.v_rc1
        if v_rc2 is None:
            v_rc2 = self.state.v_rc2
        return OCV - I * self.r0 - v_rc1 - v_rc2

    def estimate_soc(self, I: float, dt: float) -> float:
        Q_nom = self.capacity
        new_soc = self.state.soc - (I * dt) / (Q_nom * 3600)
        return max(0.0, min(1.0, new_soc))

    def estimate_soh(self, I: float, dt: float) -> float:
        R_gas = 8.314
        T_K = self.state.temperature + 273.15

        A_cal = self.aging_params.calendar_aging_A
        Ea = self.aging_params.calendar_aging_Ea
        delta_Q_cal = A_cal * math.exp(-Ea / (R_gas * T_K)) * math.sqrt(max(self._time / 3600, 0))

        B_cyc = self.aging_params.cycle_aging_B
        z_cyc = self.aging_params.cycle_aging_z
        DOD = abs(I * dt / (self.capacity * 3600))
        N_equiv = self._time / 3600
        delta_Q_cyc = B_cyc * (DOD ** z_cyc) * math.sqrt(max(N_equiv, 0))

        return max(0.0, min(1.0, 1.0 - delta_Q_cal - delta_Q_cyc))

    def compute_temperature(self, I: float, T_amb: float, dt: float, v_rc1: float = 0.0, v_rc2: float = 0.0) -> float:
        m = self.thermal_params.cell_mass
        Cp = self.thermal_params.cell_Cp
        h = self.thermal_params.cooling_coeff
        A_cool = self.thermal_params.cooling_area

        Q_gen = I ** 2 * self.r0 + I * v_rc1 + I * v_rc2
        Q_cool = h * A_cool * (self.state.temperature - T_amb)
        dT = (Q_gen - Q_cool) / (m * Cp) * dt
        return self.state.temperature + dT

    def _soc_from_ocv(self, ocv: float) -> float | None:
        for i in range(len(self.ocv_table.points) - 1):
            s0, v0 = self.ocv_table.points[i]
            s1, v1 = self.ocv_table.points[i + 1]
            if v0 <= ocv <= v1 or v1 <= ocv <= v0:
                if abs(v1 - v0) < 1e-10:
                    return s0
                t = (ocv - v0) / (v1 - v0)
                return max(0.0, min(1.0, s0 + t * (s1 - s0)))
        return None


@dataclass
class ModuleState:
    module_voltage: float = 0.0
    module_current: float = 0.0
    temperature_distribution: dict[str, float] = field(default_factory=dict)
    imbalance_report: dict[str, Any] | None = None


@dataclass
class ImbalanceReport:
    max_voltage_spread: float = 0.0
    max_temperature_spread: float = 0.0
    max_soc_spread: float = 0.0
    is_imbalanced: bool = False
    details: str = ""


class ModuleModel:

    def __init__(
        self,
        module_id: str,
        series_config: int = 1,
        parallel_config: int = 1,
        cells: list[CellModel] | None = None,
    ):
        self.module_id = module_id
        self.series_config = series_config
        self.parallel_config = parallel_config
        self.cells = cells or []
        self.state = ModuleState()

    def step(self, dt: float, current: float, T_amb: float = 25.0) -> ModuleState:
        if not self.cells:
            return self.state

        I_per_branch = current / self.parallel_config if self.parallel_config > 0 else current

        for cell in self.cells:
            cell.step(dt, I_per_branch, T_amb)

        self.state.module_voltage = self.compute_module_voltage()
        self.state.module_current = self.compute_module_current(current)
        self.state.temperature_distribution = {
            c.cell_id: c.state.temperature for c in self.cells
        }
        self.state.imbalance_report = self.check_cell_imbalance()

        return self.state

    def compute_module_voltage(self) -> float:
        if not self.cells:
            return 0.0
        branch_voltages: list[float] = []
        for p in range(self.parallel_config):
            start = p * self.series_config
            end = start + self.series_config
            branch_cells = self.cells[start:end]
            v = sum(c.state.terminal_voltage for c in branch_cells if not c.state.is_isolated)
            branch_voltages.append(v)
        return min(branch_voltages) if branch_voltages else 0.0

    def compute_module_current(self, pack_current: float) -> float:
        return pack_current

    def check_cell_imbalance(self) -> ImbalanceReport | None:
        if len(self.cells) < 2:
            return None

        voltages = [c.state.terminal_voltage for c in self.cells if not c.state.is_isolated]
        temps = [c.state.temperature for c in self.cells if not c.state.is_isolated]
        socs = [c.state.soc for c in self.cells if not c.state.is_isolated]

        if not voltages:
            return None

        v_spread = max(voltages) - min(voltages)
        t_spread = max(temps) - min(temps) if temps else 0.0
        s_spread = max(socs) - min(socs) if socs else 0.0

        is_imbalanced = v_spread > 0.1 or t_spread > 5.0 or s_spread > 0.05

        return ImbalanceReport(
            max_voltage_spread=v_spread,
            max_temperature_spread=t_spread,
            max_soc_spread=s_spread,
            is_imbalanced=is_imbalanced,
            details=f"V_spread={v_spread:.3f}V, T_spread={t_spread:.1f}°C, SOC_spread={s_spread:.3f}",
        )


@dataclass
class PackState:
    pack_voltage: float = 0.0
    pack_current: float = 0.0
    pack_soc: float = 1.0
    pack_soh: float = 1.0
    pack_temperature: float = 25.0
    bms_status: str = "Normal"
    isolated_modules: list[str] = field(default_factory=list)


class ThermalDiffusionGrid:

    def __init__(
        self,
        rows: int,
        cols: int,
        cell_spacing: float = 5.0,
        thermal_conductivity: float = 0.5,
        convective_cooling_coeff: float = 10.0,
        initial_temperature: float = 25.0,
    ):
        self.rows = rows
        self.cols = cols
        self.cell_spacing = cell_spacing * 1e-3
        self.thermal_conductivity = thermal_conductivity
        self.convective_cooling_coeff = convective_cooling_coeff
        self.temperature_matrix = np.full((rows, cols), initial_temperature, dtype=np.float64)

    def step(self, dt: float, heat_sources: dict[str, float], T_amb: float) -> dict[str, float]:
        k = self.thermal_conductivity
        d = self.cell_spacing
        h = self.convective_cooling_coeff
        A_cell = 0.006
        A_surface = 0.004

        new_temp = self.temperature_matrix.copy()

        for i in range(self.rows):
            for j in range(self.cols):
                key = f"cell_{i}_{j}"
                Q_gen = heat_sources.get(key, 0.0)

                Q_cond = 0.0
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < self.rows and 0 <= nj < self.cols:
                        Q_cond += k * A_cell / d * (self.temperature_matrix[ni, nj] - self.temperature_matrix[i, j])

                Q_conv = h * A_surface * (self.temperature_matrix[i, j] - T_amb)

                m_cell = 0.046
                Cp = 1000.0
                dT = (Q_gen + Q_cond - Q_conv) / (m_cell * Cp) * dt
                new_temp[i, j] = self.temperature_matrix[i, j] + dT

        self.temperature_matrix = new_temp

        result: dict[str, float] = {}
        for i in range(self.rows):
            for j in range(self.cols):
                result[f"cell_{i}_{j}"] = float(self.temperature_matrix[i, j])
        return result

    def compute_heat_transfer(self, i: int, j: int) -> float:
        k = self.thermal_conductivity
        A_cell = 0.006
        d = self.cell_spacing
        total = 0.0
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < self.rows and 0 <= nj < self.cols:
                total += k * A_cell / d * (self.temperature_matrix[ni, nj] - self.temperature_matrix[i, j])
        return total


@dataclass
class ThermalRunawayEvent:
    trigger_cell_id: str
    propagation_path: list[str]
    estimated_full_propagation_time: float
    safety_recommendation: str
    simulation_should_stop: bool = True


class ThermalRunawayModel:

    def __init__(
        self,
        onset_temperature: float = 150.0,
        heat_generation_rate: float = 1000.0,
        propagation_delay: float = 30.0,
    ):
        self.onset_temperature = onset_temperature
        self.heat_generation_rate = heat_generation_rate
        self.propagation_delay = propagation_delay
        self.trigger_cell_id: str | None = None
        self.propagation_path: list[str] = []
        self._runaway_cells: set[str] = set()

    def check_runaway(self, temperature: float, cell_id: str) -> bool:
        if temperature > self.onset_temperature and cell_id not in self._runaway_cells:
            self._runaway_cells.add(cell_id)
            if self.trigger_cell_id is None:
                self.trigger_cell_id = cell_id
            if cell_id not in self.propagation_path:
                self.propagation_path.append(cell_id)
            return True
        return False

    def compute_propagation(self, grid: ThermalDiffusionGrid) -> ThermalRunawayEvent | None:
        if self.trigger_cell_id is None:
            return None

        newly_triggered: list[str] = []
        for i in range(grid.rows):
            for j in range(grid.cols):
                cell_key = f"cell_{i}_{j}"
                temp = grid.temperature_matrix[i, j]
                if self.check_runaway(temp, cell_key):
                    newly_triggered.append(cell_key)

        if not self.propagation_path:
            return None

        remaining = grid.rows * grid.cols - len(self._runaway_cells)
        est_time = remaining * self.propagation_delay

        return ThermalRunawayEvent(
            trigger_cell_id=self.trigger_cell_id,
            propagation_path=list(self.propagation_path),
            estimated_full_propagation_time=est_time,
            safety_recommendation="Immediately terminate simulation and activate emergency cooling",
            simulation_should_stop=len(self._runaway_cells) > 1,
        )

    def emit_safety_event(self, result: ThermalRunawayEvent) -> dict[str, Any]:
        return {
            "event_type": "aeroforge.battery.thermal_runaway",
            "trigger_cell": result.trigger_cell_id,
            "propagation_path": result.propagation_path,
            "estimated_full_propagation_time_s": result.estimated_full_propagation_time,
            "safety_recommendation": result.safety_recommendation,
            "simulation_should_stop": result.simulation_should_stop,
        }


@dataclass
class BMSAction:
    action_type: str = "none"
    target_cell_id: str = ""
    limited_current: float | None = None
    message: str = ""


@dataclass
class BalancingResult:
    balanced_cells: list[str] = field(default_factory=list)
    energy_transferred: float = 0.0
    mode: str = "passive"


@dataclass
class IsolationResult:
    isolated_module_id: str
    remaining_pack_voltage: float
    reduced_max_current: float
    message: str


class BMSSimulator:

    def __init__(
        self,
        ovp_threshold: float = 4.25,
        uvp_threshold: float = 2.8,
        ocp_threshold: float = 50.0,
        otp_threshold: float = 60.0,
        balancing_mode: str = "passive",
        balancing_threshold: float = 0.05,
        fault_isolation_enabled: bool = True,
    ):
        self.ovp_threshold = ovp_threshold
        self.uvp_threshold = uvp_threshold
        self.ocp_threshold = ocp_threshold
        self.otp_threshold = otp_threshold
        self.balancing_mode = balancing_mode
        self.balancing_threshold = balancing_threshold
        self.fault_isolation_enabled = fault_isolation_enabled

    def check_protections(self, cell_states: list[CellState]) -> BMSAction:
        for cs in cell_states:
            if cs.is_isolated:
                continue

            if cs.terminal_voltage > self.ovp_threshold:
                return BMSAction(
                    action_type="ovp",
                    target_cell_id="",
                    limited_current=0.0,
                    message=f"OVP triggered: V={cs.terminal_voltage:.2f}V > {self.ovp_threshold}V, charging disabled",
                )

            if cs.terminal_voltage < self.uvp_threshold:
                return BMSAction(
                    action_type="uvp",
                    target_cell_id="",
                    limited_current=0.0,
                    message=f"UVP triggered: V={cs.terminal_voltage:.2f}V < {self.uvp_threshold}V, discharging disabled",
                )

            if abs(cs.current) > self.ocp_threshold:
                limited = math.copysign(self.ocp_threshold, cs.current)
                return BMSAction(
                    action_type="ocp",
                    target_cell_id="",
                    limited_current=limited,
                    message=f"OCP triggered: I={cs.current:.1f}A exceeds {self.ocp_threshold}A",
                )

            if cs.temperature > self.otp_threshold:
                limited = cs.current * 0.5
                return BMSAction(
                    action_type="otp",
                    target_cell_id="",
                    limited_current=limited,
                    message=f"OTP triggered: T={cs.temperature:.1f}°C > {self.otp_threshold}°C, current reduced",
                )

        return BMSAction(action_type="none", message="All protections OK")

    def execute_balancing(self, cell_states: list[CellState]) -> BalancingResult:
        if not cell_states:
            return BalancingResult()

        active_socs = [cs.soc for cs in cell_states if not cs.is_isolated]
        if not active_socs:
            return BalancingResult()

        soc_spread = max(active_socs) - min(active_socs)
        if soc_spread < self.balancing_threshold:
            return BalancingResult()

        balanced: list[str] = []
        energy = 0.0

        avg_soc = sum(active_socs) / len(active_socs)

        if self.balancing_mode == "passive":
            for cs in cell_states:
                if cs.is_isolated:
                    continue
                if cs.soc > avg_soc + 0.01:
                    cs.soc -= 0.001
                    energy += cs.terminal_voltage * 0.001 * cs.capacity * 3600
                    balanced.append("")
        else:
            for cs in cell_states:
                if cs.is_isolated:
                    continue
                if cs.soc > avg_soc + 0.01:
                    cs.soc -= 0.0005
                elif cs.soc < avg_soc - 0.01:
                    cs.soc += 0.0005

        return BalancingResult(
            balanced_cells=balanced,
            energy_transferred=energy,
            mode=self.balancing_mode,
        )

    def isolate_fault(self, fault_cell_id: str, modules: list[ModuleModel], pack_voltage: float) -> IsolationResult | None:
        if not self.fault_isolation_enabled:
            return None

        for mod in modules:
            for cell in mod.cells:
                if cell.cell_id == fault_cell_id:
                    cell.state.is_faulty = True
                    cell.state.is_isolated = True
                    module_voltage = mod.compute_module_voltage()
                    remaining = pack_voltage - module_voltage
                    return IsolationResult(
                        isolated_module_id=mod.module_id,
                        remaining_pack_voltage=remaining,
                        reduced_max_current=self.ocp_threshold * 0.8,
                        message=f"Module {mod.module_id} isolated due to fault in cell {fault_cell_id}",
                    )
        return None


class PackBatteryModel(IPhysicsModelPlugin):

    def __init__(self, fidelity: str = "Low"):
        self.fidelity = fidelity
        self._state = BatteryState()
        self._pack_state = PackState()
        self._time = 0.0
        self._params: dict[str, Any] = {}
        self._energy_consumed = 0.0
        self.pack_id: str = ""
        self.series_count: int = 1
        self.parallel_count: int = 1
        self.modules: list[ModuleModel] = []
        self.bms_simulator: BMSSimulator = BMSSimulator()
        self.thermal_grid: ThermalDiffusionGrid | None = None
        self.thermal_runaway: ThermalRunawayModel | None = None

    def initialize(self, params: dict[str, Any]) -> None:
        self._params = params
        self.pack_id = params.get("pack_id", "PAK-001")
        self.series_count = params.get("series_count", 1)
        self.parallel_count = params.get("parallel_count", 1)
        self.fidelity = params.get("fidelity", self.fidelity)

        self._state = BatteryState(
            soc=params.get("initial_soc", 1.0),
            soh=params.get("initial_soh", 1.0),
            terminal_voltage=params.get("battery_voltage", 48.0),
            current=0.0,
            temperature=params.get("initial_temperature", 25.0),
            v_rc1=0.0,
            v_rc2=0.0,
        )
        self._pack_state = PackState(
            pack_voltage=params.get("battery_voltage", 48.0),
            pack_soc=params.get("initial_soc", 1.0),
            pack_soh=params.get("initial_soh", 1.0),
        )
        self._time = 0.0
        self._energy_consumed = 0.0

        self.bms_simulator = BMSSimulator(
            ovp_threshold=params.get("ovp_threshold", 4.25),
            uvp_threshold=params.get("uvp_threshold", 2.8),
            ocp_threshold=params.get("ocp_threshold", 50.0),
            otp_threshold=params.get("otp_threshold", 60.0),
            balancing_mode=params.get("balancing_mode", "passive"),
            balancing_threshold=params.get("balancing_threshold", 0.05),
            fault_isolation_enabled=params.get("fault_isolation_enabled", True),
        )

        if self.fidelity == "Low":
            pass
        elif self.fidelity in ("Mid", "Detail"):
            self._build_modules(params)

        if self.fidelity == "Detail":
            n_cells = sum(len(m.cells) for m in self.modules)
            cols = int(math.ceil(math.sqrt(n_cells)))
            rows = int(math.ceil(n_cells / cols))
            self.thermal_grid = ThermalDiffusionGrid(
                rows=rows, cols=cols,
                cell_spacing=params.get("cell_spacing", 5.0),
                thermal_conductivity=params.get("thermal_conductivity", 0.5),
                convective_cooling_coeff=params.get("convective_cooling_coeff", 10.0),
                initial_temperature=params.get("initial_temperature", 25.0),
            )
            self.thermal_runaway = ThermalRunawayModel(
                onset_temperature=params.get("runaway_onset_temperature", 150.0),
                heat_generation_rate=params.get("runaway_heat_generation_rate", 1000.0),
                propagation_delay=params.get("runaway_propagation_delay", 30.0),
            )

    def _build_modules(self, params: dict[str, Any]) -> None:
        n_modules = self.series_count
        cells_per_module = self.parallel_count
        cell_capacity = params.get("cell_capacity", 3.5)
        cell_voltage = params.get("cell_nominal_voltage", 3.7)

        self.modules = []
        for m_idx in range(n_modules):
            cells: list[CellModel] = []
            for c_idx in range(cells_per_module):
                r0_var = params.get("R0", 0.02) * (1 + 0.02 * (c_idx % 3))
                r1_var = params.get("R1", 0.01) * (1 + 0.01 * (c_idx % 2))
                cell = CellModel(
                    cell_id=f"cell_{m_idx}_{c_idx}",
                    chemistry=params.get("cell_chemistry", "NMC"),
                    capacity=cell_capacity * (1 - 0.01 * (c_idx % 4)) if self.fidelity == "Detail" else cell_capacity,
                    nominal_voltage=cell_voltage,
                    r0=r0_var,
                    r1=r1_var,
                    tau1=params.get("tau1", 10.0),
                    r2=params.get("R2", 0.005),
                    tau2=params.get("tau2", 100.0),
                )
                cell.state.soc = params.get("initial_soc", 1.0) - 0.005 * (c_idx % 3) if self.fidelity == "Detail" else params.get("initial_soc", 1.0)
                cells.append(cell)

            module = ModuleModel(
                module_id=f"module_{m_idx}",
                series_config=1,
                parallel_config=cells_per_module,
                cells=cells,
            )
            self.modules.append(module)

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
        Q_nom = self._params.get("battery_capacity", 50.0)
        V_nom = self._params.get("battery_voltage", 48.0)
        R0 = self._params.get("R0", 0.02)
        I = inputs.get("current", 0.0)

        OCV = V_nom * (0.9 + 0.1 * self._state.soc)
        V_terminal = OCV - I * R0

        self._state.soc -= (I * dt) / (Q_nom * 3600)
        self._state.soc = max(0.0, min(1.0, self._state.soc))
        self._state.terminal_voltage = V_terminal
        self._state.current = I
        self._energy_consumed += abs(V_terminal * I * dt / 3600)
        self._time += dt

        self._pack_state.pack_voltage = V_terminal
        self._pack_state.pack_current = I
        self._pack_state.pack_soc = self._state.soc
        self._pack_state.pack_soh = self._state.soh

        result = BatteryOutput(state=self._state, power=V_terminal * I, energy_consumed=self._energy_consumed, fidelity="Low").model_dump()
        result["pack_state"] = {
            "pack_voltage": self._pack_state.pack_voltage,
            "pack_soc": self._pack_state.pack_soc,
            "pack_soh": self._pack_state.pack_soh,
            "bms_status": self._pack_state.bms_status,
        }
        return result

    def _step_mid(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        I = inputs.get("current", 0.0)
        T_amb = inputs.get("ambient_temperature", 25.0)

        for mod in self.modules:
            mod.step(dt, I, T_amb)

        self._pack_state.pack_voltage = self.compute_pack_voltage()
        self._pack_state.pack_current = I
        self._pack_state.pack_soc = self.compute_pack_soc()
        self._pack_state.pack_soh = self.compute_pack_soh()

        all_cells = [c for m in self.modules for c in m.cells]
        bms_action = self.bms_simulator.check_protections([c.state for c in all_cells])
        if bms_action.action_type != "none":
            self._pack_state.bms_status = "Protecting"

        self.bms_simulator.execute_balancing([c.state for c in all_cells])

        self._state.soc = self._pack_state.pack_soc
        self._state.soh = self._pack_state.pack_soh
        self._state.terminal_voltage = self._pack_state.pack_voltage
        self._state.current = I
        self._energy_consumed += abs(self._pack_state.pack_voltage * I * dt / 3600)
        self._time += dt

        result = BatteryOutput(state=self._state, power=self._pack_state.pack_voltage * I, energy_consumed=self._energy_consumed, fidelity="Mid").model_dump()
        result["pack_state"] = {
            "pack_voltage": self._pack_state.pack_voltage,
            "pack_soc": self._pack_state.pack_soc,
            "pack_soh": self._pack_state.pack_soh,
            "bms_status": self._pack_state.bms_status,
            "module_count": len(self.modules),
        }
        return result

    def _step_detail(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        I = inputs.get("current", 0.0)
        T_amb = inputs.get("ambient_temperature", 25.0)

        for mod in self.modules:
            mod.step(dt, I, T_amb)

        all_cells = [c for m in self.modules for c in m.cells]

        if self.thermal_grid is not None:
            heat_sources: dict[str, float] = {}
            cell_idx = 0
            for mod in self.modules:
                for cell in mod.cells:
                    if not cell.state.is_isolated:
                        Q_gen = I ** 2 * cell.r0 + I * cell.state.v_rc1 + I * cell.state.v_rc2
                        row = cell_idx // self.thermal_grid.cols
                        col = cell_idx % self.thermal_grid.cols
                        heat_sources[f"cell_{row}_{col}"] = Q_gen
                    cell_idx += 1

            temp_map = self.thermal_grid.step(dt, heat_sources, T_amb)

            cell_idx = 0
            for mod in self.modules:
                for cell in mod.cells:
                    row = cell_idx // self.thermal_grid.cols
                    col = cell_idx % self.thermal_grid.cols
                    key = f"cell_{row}_{col}"
                    if key in temp_map:
                        cell.state.temperature = temp_map[key]
                    cell_idx += 1

        if self.thermal_runaway is not None and self.thermal_grid is not None:
            for cell in all_cells:
                if not cell.state.is_isolated:
                    self.thermal_runaway.check_runaway(cell.state.temperature, cell.cell_id)

            if self.thermal_runaway.trigger_cell_id is not None:
                runaway_event = self.thermal_runaway.compute_propagation(self.thermal_grid)
                if runaway_event and runaway_event.simulation_should_stop:
                    self._pack_state.bms_status = "Fault"

        bms_action = self.bms_simulator.check_protections([c.state for c in all_cells])
        if bms_action.action_type != "none":
            self._pack_state.bms_status = "Protecting"
            if bms_action.limited_current is not None:
                I = bms_action.limited_current

        self.bms_simulator.execute_balancing([c.state for c in all_cells])

        self._pack_state.pack_voltage = self.compute_pack_voltage()
        self._pack_state.pack_current = I
        self._pack_state.pack_soc = self.compute_pack_soc()
        self._pack_state.pack_soh = self.compute_pack_soh()

        self._state.soc = self._pack_state.pack_soc
        self._state.soh = self._pack_state.pack_soh
        self._state.terminal_voltage = self._pack_state.pack_voltage
        self._state.current = I
        self._energy_consumed += abs(self._pack_state.pack_voltage * I * dt / 3600)
        self._time += dt

        low_battery_event = self.check_low_battery(0.2)

        result = BatteryOutput(state=self._state, power=self._pack_state.pack_voltage * I, energy_consumed=self._energy_consumed, fidelity="Detail").model_dump()
        result["pack_state"] = {
            "pack_voltage": self._pack_state.pack_voltage,
            "pack_soc": self._pack_state.pack_soc,
            "pack_soh": self._pack_state.pack_soh,
            "bms_status": self._pack_state.bms_status,
            "isolated_modules": self._pack_state.isolated_modules,
            "module_count": len(self.modules),
            "cell_count": len(all_cells),
        }
        if low_battery_event:
            result["low_battery_event"] = low_battery_event
        if self.thermal_runaway and self.thermal_runaway.trigger_cell_id:
            runaway_event = self.thermal_runaway.compute_propagation(self.thermal_grid)
            if runaway_event:
                result["thermal_runaway_event"] = self.thermal_runaway.emit_safety_event(runaway_event)
        return result

    def compute_pack_voltage(self) -> float:
        if not self.modules:
            return self._state.terminal_voltage
        return sum(m.compute_module_voltage() for m in self.modules)

    def compute_pack_current(self) -> float:
        return self._pack_state.pack_current

    def compute_pack_soc(self) -> float:
        if not self.modules:
            return self._state.soc
        all_socs = [c.state.soc for m in self.modules for c in m.cells if not c.state.is_isolated]
        return sum(all_socs) / len(all_socs) if all_socs else 0.0

    def compute_pack_soh(self) -> float:
        if not self.modules:
            return self._state.soh
        all_sohs = [c.state.soh for m in self.modules for c in m.cells if not c.state.is_isolated]
        return sum(all_sohs) / len(all_sohs) if all_sohs else 0.0

    def check_low_battery(self, threshold: float = 0.2) -> dict[str, Any] | None:
        if self._pack_state.pack_soc < threshold:
            return {
                "event_type": "aeroforge.battery.low_battery",
                "pack_soc": self._pack_state.pack_soc,
                "threshold": threshold,
                "pack_id": self.pack_id,
            }
        return None

    def check_thermal_runaway(self) -> ThermalRunawayEvent | None:
        if self.thermal_runaway is None or self.thermal_grid is None:
            return None
        return self.thermal_runaway.compute_propagation(self.thermal_grid)

    def get_state(self) -> dict[str, Any]:
        return {
            "battery_state": self._state.model_dump(),
            "pack_state": {
                "pack_voltage": self._pack_state.pack_voltage,
                "pack_soc": self._pack_state.pack_soc,
                "pack_soh": self._pack_state.pack_soh,
                "bms_status": self._pack_state.bms_status,
                "isolated_modules": self._pack_state.isolated_modules,
            },
            "fidelity": self.fidelity,
            "time": self._time,
        }

    def reset(self) -> None:
        self._state = BatteryState()
        self._pack_state = PackState()
        self._time = 0.0
        self._energy_consumed = 0.0
        for mod in self.modules:
            for cell in mod.cells:
                cell.state = CellState()
                cell._time = 0.0

    def get_supported_fidelities(self) -> list[str]:
        return [FidelityLevel.Low.value, FidelityLevel.Mid.value, FidelityLevel.High.value]

    def get_schema_references(self) -> list[str]:
        return ["AircraftPropulsion"]

    def validate_numerical_stability(self) -> StabilityCheck:
        if self._state.soc < 0 or self._state.soc > 1:
            return StabilityCheck(is_stable=False, message="SOC out of bounds")
        if self._state.temperature > 100:
            return StabilityCheck(is_stable=False, message=f"Temperature critical: {self._state.temperature:.1f}°C")
        return StabilityCheck(is_stable=True, message="Stable")