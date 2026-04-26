"""Provider Registry — lädt Provider aus DB, hält In-Memory-Cache."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import ProviderConfig
from app.translation.base import TranslationProvider
from app.translation.providers.argos_provider import ArgosProvider
from app.translation.providers.deepl_provider import DeepLProvider
from app.translation.providers.google_provider import GoogleTranslateProvider
from app.translation.providers.mistral_mock import MistralMockProvider
from app.translation.providers.openai_provider import OpenAIProvider
from app.translation.providers.seed_mock import SeedMockProvider

log = get_logger(__name__)

PROVIDER_CLASSES = {
    "argostranslate": ArgosProvider,
    "mistral": MistralMockProvider,
    "seed": SeedMockProvider,
    "deepl": DeepLProvider,
    "openai": OpenAIProvider,
    "google": GoogleTranslateProvider,
}


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, TranslationProvider] = {}
        self._configs: dict[str, ProviderConfig] = {}

    def register(self, provider: TranslationProvider, config: ProviderConfig | None = None) -> None:
        self._providers[provider.name] = provider
        if config:
            self._configs[provider.name] = config
        log.info("provider_registered", name=provider.name, type=provider.provider_type)

    def get(self, name: str) -> TranslationProvider | None:
        return self._providers.get(name)

    def get_config(self, name: str) -> ProviderConfig | None:
        return self._configs.get(name)

    def list_all(self) -> list[TranslationProvider]:
        return list(self._providers.values())

    def list_enabled(self) -> list[TranslationProvider]:
        return [p for p in self._providers.values()
                if self._configs.get(p.name) is None or self._configs[p.name].enabled]

    async def load_from_db(self, session: AsyncSession) -> None:
        configs = (await session.execute(select(ProviderConfig))).scalars().all()

        for cfg in configs:
            if not cfg.enabled:
                continue
            cls = PROVIDER_CLASSES.get(cfg.provider_type)
            if not cls:
                log.warning("unknown_provider_type", type=cfg.provider_type, name=cfg.name)
                continue

            provider = cls()
            provider.name = cfg.name
            self.register(provider, cfg)

        # Ensure argostranslate is always available
        if "argostranslate" not in self._providers:
            argos = ArgosProvider()
            self.register(argos)

        log.info("registry_loaded", provider_count=len(self._providers))

    def init_argos(self) -> None:
        """Initialize argostranslate packages (blocking, call at startup)."""
        argos = self._providers.get("argostranslate")
        if isinstance(argos, ArgosProvider):
            argos.ensure_packages()
