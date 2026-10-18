import pytest

from backend.app.providers.base import DecisionProvider
from backend.app.providers.registry import ProviderRegistry


class Provider:
    async def evaluate(self, state):
        return state


def test_registry_is_explicit_and_rejects_duplicate_names() -> None:
    registry = ProviderRegistry()
    provider: DecisionProvider = Provider()
    registry.register("test", provider)
    assert registry.get("test") is provider
    assert registry.names == ("test",)
    with pytest.raises(ValueError):
        registry.register("test", provider)
