import os

import pytest


@pytest.fixture
def database_url() -> str:
    # Missing variable must fail, not skip, so CI can never go green silently.
    return os.environ["DATABASE_URL"]
