import uuid
from datetime import datetime, timezone

from aeroforge_common.utils.helpers import generate_code, now_utc, validate_uuid


class TestGenerateCode:
    def test_generate_code_format(self) -> None:
        code = generate_code("AAF")
        assert code.startswith("AAF-")
        parts = code.split("-")
        assert len(parts) == 3

    def test_generate_code_uniqueness(self) -> None:
        code1 = generate_code("AAF")
        code2 = generate_code("AAF")
        assert code1 != code2


class TestNowUtc:
    def test_now_utc_returns_aware_datetime(self) -> None:
        result = now_utc()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_now_utc_is_utc(self) -> None:
        result = now_utc()
        assert result.tzinfo == timezone.utc


class TestValidateUuid:
    def test_valid_uuid(self) -> None:
        assert validate_uuid(str(uuid.uuid4())) is True

    def test_invalid_uuid(self) -> None:
        assert validate_uuid("not-a-uuid") is False

    def test_empty_string(self) -> None:
        assert validate_uuid("") is False