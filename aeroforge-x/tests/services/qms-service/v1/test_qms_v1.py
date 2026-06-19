import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'qms-service'))

import unittest

from src.domain.entities.v1.qms_v1_entities import (
    FMEAAnalysis, FMEAFailureMode, FRACASRecord, FRACASCorrectiveAction,
    ReliabilityPrediction, LifePrediction,
    FMEAService, FRACASService, ReliabilityService,
)


class TestFMEAAnalysis(unittest.TestCase):
    def test_create_analysis(self):
        a = FMEAAnalysis(fmea_type="dfmea", component_name="Wing Spar")
        self.assertEqual(a.fmea_type, "dfmea")
        self.assertEqual(a.status, "in_progress")

    def test_add_failure_mode(self):
        a = FMEAAnalysis()
        mode = a.add_failure_mode("Delamination", severity=8, occurrence=4, detection=5)
        self.assertEqual(mode.rpn, 160)
        self.assertEqual(a.highest_rpn, 160)

    def test_safety_critical_event(self):
        a = FMEAAnalysis()
        a.add_failure_mode("Structural failure", severity=10, occurrence=3, detection=2, is_safety_critical=True)
        self.assertTrue(len(a.domain_events) > 0)
        self.assertEqual(a.domain_events[0]["event_type"], "fmea.safety_critical_detected")

    def test_recommend_corrective_actions(self):
        a = FMEAAnalysis()
        a.add_failure_mode("High RPN mode", severity=9, occurrence=8, detection=7)
        recs = a.recommend_corrective_actions(rpn_threshold=200)
        self.assertTrue(len(recs) > 0)

    def test_complete_analysis(self):
        a = FMEAAnalysis()
        a.add_failure_mode("Mode 1", severity=5, occurrence=5, detection=5)
        a.complete()
        self.assertEqual(a.status, "completed")


class TestFMEAFailureMode(unittest.TestCase):
    def test_rpn_calculation(self):
        m = FMEAFailureMode(severity=8, occurrence=5, detection=4)
        m.calculate_rpn()
        self.assertEqual(m.rpn, 160)

    def test_rpn_bounds(self):
        m = FMEAFailureMode(severity=1, occurrence=1, detection=1)
        m.calculate_rpn()
        self.assertEqual(m.rpn, 1)

    def test_is_high_risk(self):
        m = FMEAFailureMode(severity=8, occurrence=8, detection=8)
        m.calculate_rpn()
        self.assertTrue(m.is_high_risk(200))


class TestFRACASRecord(unittest.TestCase):
    def test_create_record(self):
        r = FRACASRecord(failure_description="Motor overheating")
        self.assertEqual(r.status, "reported")

    def test_root_cause_analysis(self):
        r = FRACASRecord()
        r.record_root_cause("Insufficient cooling")
        self.assertEqual(r.status, "root_cause_identified")

    def test_corrective_action(self):
        r = FRACASRecord()
        r.record_root_cause("Bad design")
        action = r.add_corrective_action("Redesign cooling system", "eng-001")
        self.assertEqual(action.status, "planned")
        self.assertEqual(r.status, "corrective_action_planned")

    def test_verify_and_close(self):
        r = FRACASRecord()
        r.record_root_cause("Bad design")
        action = r.add_corrective_action("Fix it")
        r.verify_corrective_action(action.action_id, "qa-001", "effective")
        self.assertEqual(r.status, "verified")
        r.close()
        self.assertEqual(r.status, "closed")

    def test_safety_critical(self):
        r = FRACASRecord(is_safety_critical=True)
        r.close()
        self.assertTrue(len(r.domain_events) > 0)


class TestReliabilityPrediction(unittest.TestCase):
    def test_predict_mtbf(self):
        service = ReliabilityService()
        pred = service.predict_mtbf("comp-001", 10000, 2)
        self.assertEqual(pred.mtbf_hours, 5000.0)
        self.assertTrue(pred.failure_rate_per_million_hours > 0)

    def test_predict_mtbf_zero_failures(self):
        service = ReliabilityService()
        pred = service.predict_mtbf("comp-001", 10000, 0)
        self.assertTrue(pred.mtbf_hours > 0)

    def test_update_mtbf(self):
        pred = ReliabilityPrediction(mtbf_hours=5000)
        pred.update_mtbf(6000)
        self.assertEqual(pred.mtbf_hours, 6000)
        self.assertEqual(pred.status, "updated")


class TestLifePrediction(unittest.TestCase):
    def test_predict_remaining_life(self):
        service = ReliabilityService()
        pred = service.predict_remaining_life("comp-001", "SN-001", 10000, 5000)
        self.assertEqual(pred.remaining_useful_life_hours, 5000)
        self.assertEqual(pred.consumption_pct, 50.0)

    def test_warning_status(self):
        service = ReliabilityService()
        pred = service.predict_remaining_life("comp-001", None, 10000, 9950, warning_threshold_hours=100)
        self.assertEqual(pred.status, "warning")

    def test_critical_status(self):
        service = ReliabilityService()
        pred = service.predict_remaining_life("comp-001", None, 10000, 9990, warning_threshold_hours=100)
        self.assertEqual(pred.status, "critical")


class TestFMEAService(unittest.TestCase):
    def setUp(self):
        self.service = FMEAService()

    def test_create_and_add_mode(self):
        a = self.service.create_analysis("dfmea", component_name="Test")
        mode = self.service.add_failure_mode(a, "Crack", 8, 4, 5)
        self.assertEqual(mode.rpn, 160)


class TestFRACASService(unittest.TestCase):
    def setUp(self):
        self.service = FRACASService()

    def test_full_flow(self):
        r = self.service.create_failure_report("Motor failure", "Motor", "SN-001")
        self.service.record_root_cause(r, "Overheating")
        action = self.service.add_corrective_action(r, "Add cooling", "eng-001")
        self.service.verify_corrective_action(r, action.action_id, "qa-001", "effective")
        self.assertEqual(r.status, "verified")


if __name__ == "__main__":
    unittest.main()