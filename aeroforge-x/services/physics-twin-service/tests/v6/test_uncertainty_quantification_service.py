"""AeroForge-X V6.0/V6.1 Unit Tests - UncertaintyQuantificationService
REQ-E-ENH-001~007, REQ-VP-020
"""

import pytest

from src.domain.services.generative_design.uncertainty_quantification_service import (
    UncertaintyQuantificationService,
    UQMethodType,
    UQMethodSpec,
    UQPredictionResult,
    HighUncertaintyAlert,
    HotSwapResult,
    MDOUncertaintyResult,
)


@pytest.fixture
def service():
    return UncertaintyQuantificationService()


@pytest.fixture
def bayesian_spec():
    return UQMethodSpec(
        method_id="UQ-BP-001",
        method_type=UQMethodType.BAYESIAN_PINN,
        surrogate_model_id="SM-001",
        hyperparameters={"mcmc_steps": 100, "burn_in_ratio": 0.3},
    )


@pytest.fixture
def mc_dropout_spec():
    return UQMethodSpec(
        method_id="UQ-MC-001",
        method_type=UQMethodType.MC_DROPOUT,
        hyperparameters={"num_forward_passes": 20, "dropout_rate": 0.1},
    )


@pytest.fixture
def ensemble_spec():
    return UQMethodSpec(
        method_id="UQ-EN-001",
        method_type=UQMethodType.ENSEMBLE,
        hyperparameters={"num_models": 5, "seeds": [1, 2, 3, 4, 5]},
    )


class TestRegisterUQMethod:

    def test_register_bayesian(self, service, bayesian_spec):
        result = service.registerUQMethod(bayesian_spec)
        assert result == "UQ-BP-001"

    def test_register_mc_dropout(self, service, mc_dropout_spec):
        result = service.registerUQMethod(mc_dropout_spec)
        assert result == "UQ-MC-001"

    def test_register_ensemble(self, service, ensemble_spec):
        result = service.registerUQMethod(ensemble_spec)
        assert result == "UQ-EN-001"

    def test_register_duplicate_raises(self, service, bayesian_spec):
        service.registerUQMethod(bayesian_spec)
        with pytest.raises(ValueError, match="already registered"):
            service.registerUQMethod(bayesian_spec)

    def test_first_registered_becomes_active(self, service, bayesian_spec):
        service.registerUQMethod(bayesian_spec)
        assert service._active_method_id == "UQ-BP-001"


class TestPredictWithUQ:

    def test_predict_bayesian(self, service, bayesian_spec):
        service.registerUQMethod(bayesian_spec)
        result = service.predictWithUQ({"CL": 0.5}, method="UQ-BP-001")
        assert isinstance(result, UQPredictionResult)
        assert result.uq_method == "BayesianPINN"
        assert "CL" in result.aero_coefficients
        assert "CL" in result.prediction_intervals

    def test_predict_mc_dropout(self, service, mc_dropout_spec):
        service.registerUQMethod(mc_dropout_spec)
        result = service.predictWithUQ({"CL": 0.5}, method="UQ-MC-001")
        assert result.uq_method == "MCDropout"

    def test_predict_ensemble(self, service, ensemble_spec):
        service.registerUQMethod(ensemble_spec)
        result = service.predictWithUQ({"CL": 0.5}, method="UQ-EN-001")
        assert result.uq_method == "Ensemble"

    def test_predict_nonexistent_method_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.predictWithUQ({"CL": 0.5}, method="FAKE-METHOD")

    def test_predict_uses_active_method(self, service, bayesian_spec):
        service.registerUQMethod(bayesian_spec)
        result = service.predictWithUQ({"CL": 0.5})
        assert result.uq_method == "BayesianPINN"


class TestHotSwap:

    def test_hot_swap_method(self, service, bayesian_spec, mc_dropout_spec):
        service.registerUQMethod(bayesian_spec)
        service.registerUQMethod(mc_dropout_spec)
        result = service.hotSwapUQMethod("UQ-MC-001")
        assert isinstance(result, HotSwapResult)
        assert result.old_method_id == "UQ-BP-001"
        assert result.new_method_id == "UQ-MC-001"
        assert result.swapped is True

    def test_hot_swap_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.hotSwapUQMethod("FAKE-METHOD")


class TestHighUncertaintyFlagging:

    def test_flag_high_uncertainty(self, service, bayesian_spec):
        service.registerUQMethod(bayesian_spec)
        prediction = UQPredictionResult(
            aero_coefficients={"CL": 0.5},
            coefficient_of_variation=0.15,
            is_high_uncertainty=True,
        )
        alert = service.flagHighUncertainty(prediction)
        assert isinstance(alert, HighUncertaintyAlert)
        assert alert.recommendation != ""

    def test_no_flag_for_low_uncertainty(self, service):
        prediction = UQPredictionResult(
            aero_coefficients={"CL": 0.5},
            coefficient_of_variation=0.05,
            is_high_uncertainty=False,
        )
        alert = service.flagHighUncertainty(prediction)
        assert alert is None


class TestMDOUncertaintyPropagation:

    def test_propagate_uncertainty_through_mdo(self, service):
        result = service.propagateUncertaintyThroughMDO("MDO-RUN-001")
        assert isinstance(result, MDOUncertaintyResult)
        assert result.run_id == "MDO-RUN-001"
        assert len(result.objective_intervals) > 0