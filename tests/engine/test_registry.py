import pytest

from backend.engine.systems.demo import DemoSystem
from backend.engine.systems.registry import (
    UnknownSystemError,
    create_system,
    get_system_class,
    list_systems,
    register_system,
)


def test_demo_system_is_registered():
    assert get_system_class("demo") is DemoSystem
    assert create_system("DEMO").system_id == "demo"
    assert list_systems()[0]["id"] == "demo"


def test_unknown_system_has_actionable_error():
    with pytest.raises(UnknownSystemError) as exc_info:
        create_system("not-a-game")
    assert "available systems" in str(exc_info.value)


def test_register_requires_explicit_replace():
    class DuplicateSystem(DemoSystem):
        pass

    with pytest.raises(ValueError):
        register_system(DuplicateSystem)
