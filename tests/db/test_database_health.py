from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError

from app.db.health import database_is_ready


def test_database_health_executes_select_one() -> None:
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    with patch("app.db.health.get_engine", return_value=engine):
        assert database_is_ready() is True
    connection.execute.assert_called_once()
    assert str(connection.execute.call_args.args[0]) == "SELECT 1"


def test_database_health_safely_maps_sqlalchemy_failure() -> None:
    engine = MagicMock()
    engine.connect.side_effect = OperationalError("SELECT 1", {}, Exception("credentials"))
    with patch("app.db.health.get_engine", return_value=engine):
        assert database_is_ready() is False
