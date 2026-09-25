from datetime import UTC, date, datetime
from typing import Any

import pytest

from pipeline.models import Edital

HOJE = date(2026, 9, 25)
AGORA = datetime(2026, 9, 25, 9, 0, tzinfo=UTC)


def fazer_edital(**campos: Any) -> Edital:
    base: dict[str, Any] = {
        "id": "teste-abc123",
        "titulo": "Edital de Teste",
        "fonte": "teste",
        "source_url": "https://exemplo.gov.br/edital",
        "captured_at": AGORA,
        "updated_at": AGORA,
    }
    base.update(campos)
    return Edital(**base)


@pytest.fixture
def edital() -> Edital:
    return fazer_edital()
