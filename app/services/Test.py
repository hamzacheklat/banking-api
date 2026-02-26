Voici **tous les tests (singleton + as_response)** regroupés dans **un seul fichier pytest**, prêt à l’emploi.

> ⚠️ Remplace `your_module` par le vrai chemin de ton module
> (ex: `app.metrics`, `cinego.metrics`, etc.)

---

# 📁 `test_metrics_collector.py`

```python
import pytest
from unittest.mock import MagicMock, patch

from your_module import MetricsCollector


# ============================================================
# FIXTURE : reset du singleton avant chaque test
# ============================================================

@pytest.fixture(autouse=True)
def reset_singleton():
    MetricsCollector._instance = None
    yield
    MetricsCollector._instance = None


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def collector(mock_logger):
    return MetricsCollector(mock_logger)


# ============================================================
# TESTS DU SINGLETON
# ============================================================

def test_singleton_returns_same_instance():
    logger1 = MagicMock()
    logger2 = MagicMock()

    collector1 = MetricsCollector(logger1)
    collector2 = MetricsCollector(logger2)

    assert collector1 is collector2


def test_singleton_init_called_once(mock_logger):
    with patch("your_module.CollectorRegistry") as mock_registry:
        collector1 = MetricsCollector(mock_logger)
        collector2 = MetricsCollector(mock_logger)

        assert collector1 is collector2
        assert mock_registry.call_count == 1


def test_singleton_keeps_first_logger():
    logger1 = MagicMock()
    logger2 = MagicMock()

    collector1 = MetricsCollector(logger1)
    collector2 = MetricsCollector(logger2)

    assert collector1 is collector2
    assert collector1.logger is logger1
    assert collector2.logger is logger1


# ============================================================
# TESTS DE as_response()
# ============================================================

def test_as_response_success(collector, mock_logger):
    fake_metrics = b"fake_metrics_payload"

    with patch("your_module.generate_latest", return_value=fake_metrics) as mock_generate:
        result = collector.as_response()

        # Vérifie l'appel à Prometheus
        mock_generate.assert_called_once_with(collector._registry)

        # Vérifie le retour
        assert result == fake_metrics

        # Vérifie les logs
        mock_logger.start.assert_called_once_with(
            "Generating Prometheus metrics payload"
        )
        mock_logger.success.assert_called_once_with(
            "Metrics generated - %d bytes",
            len(fake_metrics),
        )
        mock_logger.error.assert_not_called()


def test_as_response_failure(collector, mock_logger):
    with patch("your_module.generate_latest", side_effect=Exception("Boom")):
        with pytest.raises(Exception, match="Boom"):
            collector.as_response()

        mock_logger.error.assert_called_once()
        mock_logger.success.assert_not_called()
```

---

# ✅ Ce fichier teste

### 🔹 Singleton

* Une seule instance
* `CollectorRegistry` appelé une seule fois
* Le logger n’est pas remplacé

### 🔹 Méthode `as_response`

* Retour correct des métriques
* Appel correct à `generate_latest`
* Logs corrects
* Gestion des exceptions

---

# 🎯 Résultat attendu

```bash
pytest -v
```

Tu devrais voir :

```
5 passed
```

---

Si tu veux, je peux te générer :

* ✅ Version avec `pytest-mock`
* 🔥 Test thread-safe du singleton
* 📊 Version avec 100% coverage garanti
* 🧪 Test d’intégration Prometheus multiprocess
* 🏗️ Refacto plus propre du singleton

Dis-moi ce que tu veux améliorer 😉
