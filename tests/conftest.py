import pytest

@pytest.fixture
def sample_fixture():
    return "sample data"

@pytest.fixture(scope='session')
def session_fixture():
    return "session fixture data"

# Additional pytest configurations can be added here.
