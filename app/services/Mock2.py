import pytest
from unittest.mock import MagicMock, patch

from utils.metrics import MetricsCollector


# ============================================================
# RESET DU SINGLETON
# ============================================================

@pytest.fixture(autouse=True)
def reset_singleton():
    MetricsCollector._instance = None
    yield
    MetricsCollector._instance = None


# ============================================================
# LOGGER MOCK
# ============================================================

@pytest.fixture
def mock_logger():
    return MagicMock()


# ============================================================
# COLLECTOR FIXTURE (SAFE)
# On mock Prometheus pour éviter PROMETHEUS_MULTIPROC_DIR
# ============================================================

@pytest.fixture
def collector(mock_logger):
    with patch("utils.metrics.CollectorRegistry"), \
         patch("utils.metrics.multiprocess.MultiProcessCollector"):
        return MetricsCollector(mock_logger)


# ============================================================
# TESTS SINGLETON
# ============================================================

def test_singleton_returns_same_instance(mock_logger):
    with patch("utils.metrics.CollectorRegistry"), \
         patch("utils.metrics.multiprocess.MultiProcessCollector"):

        collector1 = MetricsCollector(mock_logger)
        collector2 = MetricsCollector(mock_logger)

        assert collector1 is collector2


def test_singleton_init_called_once(mock_logger):
    with patch("utils.metrics.CollectorRegistry") as mock_registry, \
         patch("utils.metrics.multiprocess.MultiProcessCollector"):

        collector1 = MetricsCollector(mock_logger)
        collector2 = MetricsCollector(mock_logger)

        assert collector1 is collector2
        assert mock_registry.call_count == 1


def test_singleton_keeps_first_logger(mock_logger):
    logger1 = MagicMock()
    logger2 = MagicMock()

    with patch("utils.metrics.CollectorRegistry"), \
         patch("utils.metrics.multiprocess.MultiProcessCollector"):

        collector1 = MetricsCollector(logger1)
        collector2 = MetricsCollector(logger2)

        assert collector1 is collector2
        assert collector1.logger is logger1
        assert collector2.logger is logger1


# ============================================================
# TESTS as_response()
# ============================================================

def test_as_response_success(collector, mock_logger):
    fake_metrics = b"fake_metrics_payload"

    with patch("utils.metrics.generate_latest", return_value=fake_metrics) as mock_generate:
        result = collector.as_response()

        mock_generate.assert_called_once_with(collector._registry)
        assert result == fake_metrics

        mock_logger.start.assert_called_once_with(
            "Generating Prometheus metrics payload"
        )
        mock_logger.success.assert_called_once_with(
            "Metrics generated - %d bytes",
            len(fake_metrics),
        )
        mock_logger.error.assert_not_called()


def test_as_response_failure(collector, mock_logger):
    with patch("utils.metrics.generate_latest", side_effect=Exception("Boom")):
        with pytest.raises(Exception, match="Boom"):
            collector.as_response()

        mock_logger.error.assert_called_once()
        mock_logger.success.assert_not_called()
