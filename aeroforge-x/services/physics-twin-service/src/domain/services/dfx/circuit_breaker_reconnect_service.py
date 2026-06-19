"""AeroForge-X v6.0 CircuitBreakerReconnectService

Provides circuit breaker pattern and automatic reconnection for
OPC-UA/MQTT connections with exponential backoff (1s~60s)
and last-valid-value degradation.

INT-2.8: Circuit breaker for connection interruption (REQ-DFX-V6-009)
INT-2.11: Auto-reconnect with exponential backoff (REQ-DFX-V6-012)
REQ-NFR-V6-013
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CircuitState(str, Enum):
    CLOSED = "Closed"
    OPEN = "Open"
    HALF_OPEN = "HalfOpen"


class ConnectionProtocol(str, Enum):
    OPC_UA = "OPC-UA"
    MQTT = "MQTT"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_s: float = 30.0
    half_open_max_calls: int = 3
    success_threshold: int = 3

    def to_dict(self) -> dict:
        return {
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_s": self.recovery_timeout_s,
            "half_open_max_calls": self.half_open_max_calls,
            "success_threshold": self.success_threshold,
        }


@dataclass
class ReconnectConfig:
    initial_backoff_s: float = 1.0
    max_backoff_s: float = 60.0
    backoff_multiplier: float = 2.0
    max_retries: int = 0

    def to_dict(self) -> dict:
        return {
            "initial_backoff_s": self.initial_backoff_s,
            "max_backoff_s": self.max_backoff_s,
            "backoff_multiplier": self.backoff_multiplier,
            "max_retries": self.max_retries,
        }


@dataclass
class CircuitBreakerState:
    equipment_id: str
    protocol: ConnectionProtocol
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    half_open_calls: int = 0
    last_failure_at: float = 0.0
    last_success_at: float = 0.0
    opened_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "equipment_id": self.equipment_id,
            "protocol": self.protocol.value,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "half_open_calls": self.half_open_calls,
            "last_failure_at": self.last_failure_at,
            "last_success_at": self.last_success_at,
            "opened_at": self.opened_at,
        }


@dataclass
class LastValidValue:
    equipment_id: str
    parameter_name: str
    value: float
    unit: str = ""
    recorded_at: float = 0.0
    is_stale: bool = False

    def to_dict(self) -> dict:
        return {
            "equipment_id": self.equipment_id,
            "parameter_name": self.parameter_name,
            "value": self.value,
            "unit": self.unit,
            "recorded_at": self.recorded_at,
            "is_stale": self.is_stale,
        }


@dataclass
class ReconnectAttempt:
    attempt_id: str
    equipment_id: str
    protocol: ConnectionProtocol
    attempt_number: int
    backoff_s: float
    success: bool = False
    error: str = ""
    attempted_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "attempt_id": self.attempt_id,
            "equipment_id": self.equipment_id,
            "protocol": self.protocol.value,
            "attempt_number": self.attempt_number,
            "backoff_s": self.backoff_s,
            "success": self.success,
            "error": self.error,
            "attempted_at": self.attempted_at,
        }


class CircuitBreakerReconnectService:

    def __init__(
        self,
        circuit_config: CircuitBreakerConfig | None = None,
        reconnect_config: ReconnectConfig | None = None,
    ) -> None:
        self._circuit_config = circuit_config or CircuitBreakerConfig()
        self._reconnect_config = reconnect_config or ReconnectConfig()
        self._circuits: dict[str, CircuitBreakerState] = {}
        self._last_valid: dict[str, dict[str, LastValidValue]] = {}
        self._reconnect_history: list[ReconnectAttempt] = []
        self._reconnect_attempts: dict[str, int] = {}

    def registerCircuit(
        self, equipment_id: str, protocol: ConnectionProtocol
    ) -> CircuitBreakerState:
        circuit = CircuitBreakerState(
            equipment_id=equipment_id,
            protocol=protocol,
        )
        self._circuits[equipment_id] = circuit
        self._last_valid[equipment_id] = {}
        self._reconnect_attempts[equipment_id] = 0
        return circuit

    def recordSuccess(self, equipment_id: str) -> CircuitBreakerState:
        circuit = self._circuits.get(equipment_id)
        if circuit is None:
            raise ValueError(f"Circuit not found: {equipment_id}")

        circuit.success_count += 1
        circuit.last_success_at = time.time()

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.half_open_calls += 1
            if circuit.half_open_calls >= self._circuit_config.success_threshold:
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                circuit.half_open_calls = 0
                self._reconnect_attempts[equipment_id] = 0

        return circuit

    def recordFailure(self, equipment_id: str) -> CircuitBreakerState:
        circuit = self._circuits.get(equipment_id)
        if circuit is None:
            raise ValueError(f"Circuit not found: {equipment_id}")

        circuit.failure_count += 1
        circuit.last_failure_at = time.time()

        if circuit.state == CircuitState.CLOSED:
            if circuit.failure_count >= self._circuit_config.failure_threshold:
                circuit.state = CircuitState.OPEN
                circuit.opened_at = time.time()

        elif circuit.state == CircuitState.HALF_OPEN:
            circuit.state = CircuitState.OPEN
            circuit.opened_at = time.time()
            circuit.half_open_calls = 0

        self._mark_last_valid_stale(equipment_id)

        return circuit

    def checkCircuitState(self, equipment_id: str) -> CircuitBreakerState:
        circuit = self._circuits.get(equipment_id)
        if circuit is None:
            raise ValueError(f"Circuit not found: {equipment_id}")

        if circuit.state == CircuitState.OPEN:
            elapsed = time.time() - circuit.opened_at
            if elapsed >= self._circuit_config.recovery_timeout_s:
                circuit.state = CircuitState.HALF_OPEN
                circuit.half_open_calls = 0

        return circuit

    def calculateBackoff(self, equipment_id: str) -> float:
        attempts = self._reconnect_attempts.get(equipment_id, 0)
        backoff = min(
            self._reconnect_config.initial_backoff_s
            * (self._reconnect_config.backoff_multiplier ** attempts),
            self._reconnect_config.max_backoff_s,
        )
        return backoff

    def attemptReconnect(
        self, equipment_id: str, success: bool, error: str = ""
    ) -> ReconnectAttempt:
        circuit = self._circuits.get(equipment_id)
        if circuit is None:
            raise ValueError(f"Circuit not found: {equipment_id}")

        attempts = self._reconnect_attempts.get(equipment_id, 0) + 1
        self._reconnect_attempts[equipment_id] = attempts
        backoff = self.calculateBackoff(equipment_id)

        attempt = ReconnectAttempt(
            attempt_id=f"RC-{uuid.uuid4().hex[:8]}",
            equipment_id=equipment_id,
            protocol=circuit.protocol,
            attempt_number=attempts,
            backoff_s=backoff,
            success=success,
            error=error,
            attempted_at=time.time(),
        )
        self._reconnect_history.append(attempt)

        if success:
            circuit.state = CircuitState.HALF_OPEN
            circuit.half_open_calls = 0
        else:
            circuit.state = CircuitState.OPEN
            circuit.opened_at = time.time()

        return attempt

    def storeLastValidValue(
        self, equipment_id: str, parameter_name: str, value: float, unit: str = ""
    ) -> LastValidValue:
        if equipment_id not in self._last_valid:
            self._last_valid[equipment_id] = {}

        lvv = LastValidValue(
            equipment_id=equipment_id,
            parameter_name=parameter_name,
            value=value,
            unit=unit,
            recorded_at=time.time(),
            is_stale=False,
        )
        self._last_valid[equipment_id][parameter_name] = lvv
        return lvv

    def getLastValidValues(
        self, equipment_id: str
    ) -> dict[str, LastValidValue]:
        return dict(self._last_valid.get(equipment_id, {}))

    def _mark_last_valid_stale(self, equipment_id: str) -> None:
        for lvv in self._last_valid.get(equipment_id, {}).values():
            lvv.is_stale = True

    def getCircuit(self, equipment_id: str) -> Optional[CircuitBreakerState]:
        return self._circuits.get(equipment_id)

    def getReconnectHistory(
        self, equipment_id: str = ""
    ) -> list[ReconnectAttempt]:
        if not equipment_id:
            return list(self._reconnect_history)
        return [
            a for a in self._reconnect_history if a.equipment_id == equipment_id
        ]