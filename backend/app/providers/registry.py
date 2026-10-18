"""Small explicit provider registry used by later orchestration phases."""

from backend.app.providers.base import DecisionProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, DecisionProvider] = {}

    def register(self, name: str, provider: DecisionProvider) -> None:
        if not name or name in self._providers:
            raise ValueError(f"provider name must be unique: {name!r}")
        self._providers[name] = provider

    def get(self, name: str) -> DecisionProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise KeyError(f"unknown provider: {name}") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    async def aclose(self) -> None:
        for provider in self._providers.values():
            close = getattr(provider, "aclose", None)
            if close is not None:
                await close()
