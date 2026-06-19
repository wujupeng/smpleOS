import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'mes-center'))

from decimal import Decimal
import unittest
from datetime import date

from src.domain.entities.v1.traveler_record import TravelerRecord, TravelerStatus
from src.domain.entities.v1.ndt_inspection import NDTInspection, NDTMethod, NDTResult, NDTStatus
from src.domain.entities.v1.tool_calibration import ToolCalibration, CalibrationStatus
from src.domain.services.v1.mes_v1_services import TravelerService, NDTService, ToolCalibrationService


class TestTravelerRecord(unittest.TestCase):
    def test_create_traveler(self):
        t = TravelerRecord(work_order_id="wo-001", serial_number="SN-001", process_step="curing")
        self.assertEqual(t.status, TravelerStatus.IN_PROGRESS)

    def test_record_temperature_within_tolerance(self):
        t = TravelerRecord()
        reading = t.record_temperature(Decimal("180"), Decimal("175"), Decimal("5"))
        self.assertTrue(reading.is_within_tolerance)

    def test_record_temperature_deviation(self):
        t = TravelerRecord()
        reading = t.record_temperature(Decimal("200"), Decimal("175"), Decimal("5"))
        self.assertFalse(reading.is_within_tolerance)
        self.assertEqual(t.status, TravelerStatus.NON_CONFORMING)

    def test_confirm_traveler(self):
        t = TravelerRecord()
        t.confirm("inspector-001")
        self.assertEqual(t.status, TravelerStatus.CONFIRMED)
        self.assertEqual(t.quality_inspector, "inspector-001")

    def test_finalize_traveler(self):
        t = TravelerRecord(serial_number="SN-001", process_step="curing")
        t.confirm("inspector-001")
        t.finalize()
        self.assertEqual(t.status, TravelerStatus.FINALIZED)
        self.assertEqual(len(t.domain_events), 1)

    def test_finalize_missing_fields(self):
        t = TravelerRecord()
        with self.assertRaises(ValueError):
            t.finalize()

    def test_finalize_non_conforming(self):
        t = TravelerRecord(serial_number="SN-001", process_step="curing")
        t.record_temperature(Decimal("200"), Decimal("175"), Decimal("5"))
        t.confirm("inspector-001")
        with self.assertRaises(ValueError):
            t.finalize()


class TestNDTInspection(unittest.TestCase):
    def test_create_inspection(self):
        insp = NDTInspection(serial_number="SN-001", inspection_method=NDTMethod.ULTRASONIC)
        self.assertEqual(insp.status, NDTStatus.PLANNED)

    def test_record_acceptable_result(self):
        insp = NDTInspection()
        insp.record_result(NDTResult.ACCEPTABLE, inspector_id="insp-001")
        self.assertEqual(insp.result, NDTResult.ACCEPTABLE)
        self.assertEqual(insp.status, NDTStatus.COMPLETED)

    def test_marginal_requires_level_ii(self):
        insp = NDTInspection(inspector_level=1)
        with self.assertRaises(ValueError):
            insp.record_result(NDTResult.MARGINAL, inspector_id="insp-001")

    def test_unacceptable_triggers_event(self):
        insp = NDTInspection()
        insp.record_result(NDTResult.UNACCEPTABLE, inspector_id="insp-001")
        self.assertTrue(len(insp.domain_events) > 0)

    def test_expired_calibration_blocks(self):
        insp = NDTInspection(tool_calibration_valid=False)
        with self.assertRaises(ValueError):
            insp.record_result(NDTResult.ACCEPTABLE)


class TestToolCalibration(unittest.TestCase):
    def test_create_calibration(self):
        cal = ToolCalibration(tool_id="TOOL-001", tool_name="Torque Wrench",
                              next_due_date=date(2030, 1, 1))
        self.assertEqual(cal.status, CalibrationStatus.CURRENT)

    def test_check_expiry_expired(self):
        cal = ToolCalibration(next_due_date=date(2020, 1, 1))
        cal.check_expiry()
        self.assertEqual(cal.status, CalibrationStatus.EXPIRED)

    def test_check_expiry_expiring_soon(self):
        from datetime import timedelta
        cal = ToolCalibration(next_due_date=date.today() + timedelta(days=3))
        cal.check_expiry(warning_days=7)
        self.assertEqual(cal.status, CalibrationStatus.EXPIRING_SOON)

    def test_invalidate(self):
        cal = ToolCalibration()
        cal.invalidate("Post-review invalid")
        self.assertEqual(cal.status, CalibrationStatus.INVALID)

    def test_is_usable(self):
        cal = ToolCalibration(next_due_date=date(2030, 1, 1))
        cal.check_expiry()
        self.assertTrue(cal.is_usable())


class TestTravelerService(unittest.TestCase):
    def setUp(self):
        self.service = TravelerService()

    def test_create_traveler(self):
        t = self.service.create_traveler("wo-001", "SN-001", "curing")
        self.assertEqual(t.work_order_id, "wo-001")

    def test_record_temperature_and_finalize(self):
        t = self.service.create_traveler("wo-001", "SN-001", "curing")
        self.service.record_temperature_profile(t, Decimal("180"), Decimal("175"))
        self.service.confirm_traveler(t, "inspector-001")
        self.service.finalize_traveler(t)
        self.assertEqual(t.status, TravelerStatus.FINALIZED)


class TestNDTService(unittest.TestCase):
    def setUp(self):
        self.service = NDTService()

    def test_create_and_record(self):
        insp = self.service.create_inspection("SN-001", "ultrasonic")
        self.service.record_result(insp, "acceptable")
        judgment = self.service.judge_result(insp)
        self.assertEqual(judgment["judgment"], "pass")

    def test_unacceptable_judgment(self):
        insp = self.service.create_inspection("SN-001", "ultrasonic")
        self.service.record_result(insp, "unacceptable")
        judgment = self.service.judge_result(insp)
        self.assertEqual(judgment["action"], "quarantine_and_investigate")


class TestToolCalibrationService(unittest.TestCase):
    def setUp(self):
        self.service = ToolCalibrationService()

    def test_record_calibration(self):
        cal = self.service.record_calibration("TOOL-001", "Torque Wrench", "2025-01-01", "2030-01-01")
        self.assertEqual(cal.status, CalibrationStatus.CURRENT)

    def test_check_expiry(self):
        self.service.record_calibration("TOOL-001", "Wrench", "2020-01-01", "2020-02-01")
        expiring = self.service.check_calibration_expiry()
        self.assertTrue(len(expiring) > 0)


if __name__ == "__main__":
    unittest.main()