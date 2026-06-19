"""AeroForge-X V6.1 Integration Tests - UQ + MDO Integration
IT-G03: predictWithUQ → flagHighUncertainty → propagateUncertainty → produceParetoFront
REQ-VP-051
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))

import pytest

from src.domain.services.generative_design.uncertainty_quantification_service import (
    UncertaintyQuantificationService, UQMethodType, UQMethodSpec,
)
from src.domain.services.generative_design.seven_discipline_mdo_service import (
    SevenDisciplineMDOService, MDOConfig7D,
)


@pytest.fixture
def uq_svc():
    return UncertaintyQuantificationService()


@pytest.fixture
def mdo_svc():
    return SevenDisciplineMDOService()


class TestUQMDOIntegration:

    def test_uq_mdo_integration(self, uq_svc, mdo_svc):
        bayesian_spec = UQMethodSpec(
            method_id="UQ-BP-001", method_type=UQMethodType.BAYESIAN_PINN,
            hyperparameters={"mcmc_steps": 100, "burn_in_ratio": 0.3},
        )
        ensemble_spec = UQMethodSpec(
            method_id="UQ-EN-001", method_type=UQMethodType.ENSEMBLE,
            hyperparameters={"num_models": 5, "seeds": [1, 2, 3, 4, 5]},
        )
        uq_svc.registerUQMethod(bayesian_spec)
        uq_svc.registerUQMethod(ensemble_spec)

        prediction = uq_svc.predictWithUQ({"CL": 0.5}, method="UQ-EN-001")
        assert prediction.uq_method == "Ensemble"
        assert "CL" in prediction.prediction_intervals

        alert = uq_svc.flagHighUncertainty(prediction)
        if prediction.is_high_uncertainty:
            assert alert is not None

        config = MDOConfig7D(
            requirement_id="REQ-MDO-001",
            design_variables={"wing_span": 30, "engine_count": 2, "fuselage_length": 30},
            active_discipline_count=7,
        )
        solution = mdo_svc.run7DisciplineMDO(config)
        assert len(solution.objective_values) >= 3

        mdo_uq = uq_svc.propagateUncertaintyThroughMDO("MDO-RUN-001")
        assert len(mdo_uq.objective_intervals) > 0

    def test_uq_hot_swap_during_mdo(self, uq_svc, mdo_svc):
        bp_spec = UQMethodSpec(method_id="UQ-BP", method_type=UQMethodType.BAYESIAN_PINN,
                                hyperparameters={"mcmc_steps": 50})
        mc_spec = UQMethodSpec(method_id="UQ-MC", method_type=UQMethodType.MC_DROPOUT,
                                hyperparameters={"num_forward_passes": 20})
        uq_svc.registerUQMethod(bp_spec)
        uq_svc.registerUQMethod(mc_spec)

        pred1 = uq_svc.predictWithUQ({"CL": 0.5}, method="UQ-BP")
        assert pred1.uq_method == "BayesianPINN"

        swap = uq_svc.hotSwapUQMethod("UQ-MC")
        assert swap.swapped is True

        pred2 = uq_svc.predictWithUQ({"CL": 0.5})
        assert pred2.uq_method == "MCDropout"