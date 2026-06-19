from aeroforge_common.types.common import JsonDict, Timestamp, UserId


class TestTypes:
    def test_user_id_is_str(self) -> None:
        uid: UserId = "user-123"
        assert isinstance(uid, str)

    def test_timestamp_is_str(self) -> None:
        ts: Timestamp = "2026-01-01T00:00:00Z"
        assert isinstance(ts, str)

    def test_json_dict(self) -> None:
        data: JsonDict = {"key": "value", "count": 42}
        assert data["key"] == "value"
        assert data["count"] == 42