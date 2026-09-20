import json
import logging
import sys

from orchestrator.logging_config import JsonFormatter


def _format(record: logging.LogRecord) -> dict:
    return json.loads(JsonFormatter().format(record))


def test_formats_basic_fields_as_json():
    record = logging.LogRecord(
        name="orchestrator.main",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="validated %d opportunities",
        args=(3,),
        exc_info=None,
    )

    payload = _format(record)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "orchestrator.main"
    assert payload["message"] == "validated 3 opportunities"
    assert "timestamp" in payload
    assert "exception" not in payload


def test_includes_exception_info_when_present():
    try:
        raise RuntimeError("antcrew quick failed")
    except RuntimeError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="build failed",
            args=(),
            exc_info=True,
        )
        record.exc_info = sys.exc_info()

    payload = _format(record)

    assert "RuntimeError: antcrew quick failed" in payload["exception"]


def test_includes_extra_fields():
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="unparseable effort",
        args=(),
        exc_info=None,
    )
    record.niche_title = "A niche"

    payload = _format(record)

    assert payload["niche_title"] == "A niche"
