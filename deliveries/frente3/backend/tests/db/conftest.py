## Fixtures dos testes de integração (PostgreSQL). ##

import pytest
from sqlalchemy.orm import Session

from backend.tests.db.factories import BaseData, build_base


@pytest.fixture
def base(db: Session) -> BaseData:
    """Unidade, síndica, dois moradores, carregadores de 1 e 2 conectores, tarifa e ISS."""
    return build_base(db)
