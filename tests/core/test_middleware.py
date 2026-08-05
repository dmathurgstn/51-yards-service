from uuid import UUID

from app.core.middleware import normalize_request_id


def test_request_id_normalization() -> None:
    generated = normalize_request_id(None)
    assert str(UUID(generated)) == generated
    assert normalize_request_id("x" * 129) != "x" * 129
