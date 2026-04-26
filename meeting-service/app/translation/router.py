"""Translation Router — wählt Provider pro Sprachpaar + Modus, mit Failover."""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import LanguageRoute
from app.translation.base import ProviderStatus, TranslationError, TranslationProvider
from app.translation.health_monitor import HealthMonitor
from app.translation.registry import ProviderRegistry

log = get_logger(__name__)

LANG_FLAGS = {
    "de": "🇩🇪", "en": "🇬🇧", "fr": "🇫🇷", "es": "🇪🇸", "it": "🇮🇹",
    "pt": "🇵🇹", "ar": "🇸🇦", "zh": "🇨🇳", "ja": "🇯🇵", "ko": "🇰🇷",
    "ru": "🇷🇺", "tr": "🇹🇷",
}


class TranslationRouter:
    def __init__(
        self,
        registry: ProviderRegistry,
        health_monitor: HealthMonitor,
    ) -> None:
        self._registry = registry
        self._health = health_monitor
        # In-memory route cache: (src, tgt) -> (primary_name, backup_name)
        self._routes: dict[tuple[str, str], tuple[str, str]] = {}

    async def load_routes(self, session: AsyncSession) -> None:
        """Load language routes from DB into memory cache."""
        from app.db.models import ProviderConfig

        routes = (await session.execute(
            select(LanguageRoute, ProviderConfig.name.label("primary_name"))
            .join(ProviderConfig, LanguageRoute.primary_provider_id == ProviderConfig.provider_id)
        )).all()

        # Need backup names too
        all_routes = (await session.execute(select(LanguageRoute))).scalars().all()
        configs = {c.provider_id: c.name for c in (await session.execute(select(ProviderConfig))).scalars().all()}

        self._routes = {}
        for route in all_routes:
            primary = configs.get(route.primary_provider_id, "argostranslate")
            backup = configs.get(route.backup_provider_id, "argostranslate")
            self._routes[(route.source_lang, route.target_lang)] = (primary, backup)

        log.info("routes_loaded", count=len(self._routes))

    def _get_provider_for_pair(
        self, source_lang: str, target_lang: str
    ) -> tuple[str, str]:
        """Get (primary_name, backup_name) for a language pair."""
        return self._routes.get(
            (source_lang, target_lang),
            ("argostranslate", "argostranslate"),  # fallback
        )

    async def _select_provider(
        self, source_lang: str, target_lang: str, mode: str
    ) -> tuple[TranslationProvider, bool]:
        """Select best provider based on health + mode. Returns (provider, is_failover)."""
        primary_name, backup_name = self._get_provider_for_pair(source_lang, target_lang)

        primary = self._registry.get(primary_name)
        backup = self._registry.get(backup_name)
        argos = self._registry.get("argostranslate")

        if mode == "live":
            # LIVE MODE: prioritize lowest latency, strict health requirements
            # If primary is GREEN and fast → use it
            # If primary is YELLOW or slow → immediate failover
            # If both slow → argostranslate (always fast, ~100ms)
            candidates = []
            for name, provider in [(primary_name, primary), (backup_name, backup)]:
                if provider:
                    h = await self._health.get_health(name)
                    if h.status != ProviderStatus.RED:
                        candidates.append((provider, h.avg_latency_ms, name == backup_name))

            if candidates:
                # Sort by latency — pick fastest
                candidates.sort(key=lambda c: c[1])
                best, lat, is_fo = candidates[0]
                if lat < 500:  # Under 500ms → acceptable for live
                    return best, is_fo

            # All too slow → argostranslate (fastest offline)
            if argos:
                return argos, True

        else:
            # ONLINE MODE: prioritize quality (priority-based), tolerate higher latency
            if primary:
                health = await self._health.get_health(primary_name)
                if health.status == ProviderStatus.GREEN:
                    return primary, False
                if health.status == ProviderStatus.YELLOW:
                    return primary, False  # Accept yellow in online mode

            # Primary is RED → try backup
            if backup and backup_name != primary_name:
                backup_health = await self._health.get_health(backup_name)
                if backup_health.status != ProviderStatus.RED:
                    return backup, True

            # Both RED → argostranslate
            if argos:
                return argos, True

        raise TranslationError("No translation provider available")

    async def translate_to_targets(
        self,
        text: str,
        source_lang: str,
        target_langs: list[str],
        mode: str = "online",
        meeting_id: str | None = None,
        speaker: str | None = None,
    ) -> list[dict]:
        """Translate text to multiple targets using routing engine.

        Returns: [{lang, flag, text, provider, failover}]
        """
        timeout = 0.5 if mode == "live" else 2.0

        # Update meeting context for LLM providers
        context_prompt = None
        if meeting_id:
            from app.translation.context import get_meeting_context
            ctx = get_meeting_context(meeting_id, source_lang)
            ctx.add_segment(speaker or "?", text, source_lang)
            context_prompt = ctx.build_translation_prompt(text, source_lang, "TARGET")

        async def translate_one(target: str) -> dict | None:
            if target == source_lang:
                return None
            try:
                provider, is_failover = await self._select_provider(source_lang, target, mode)

                # LLM providers get contextual prompt
                is_llm = provider.provider_type in ("openai", "claude", "deepseek")
                if is_llm and context_prompt and meeting_id:
                    from app.translation.context import get_meeting_context
                    ctx = get_meeting_context(meeting_id, source_lang)
                    enriched_text = ctx.build_translation_prompt(text, source_lang, target)
                    translated = await asyncio.wait_for(
                        provider.translate(enriched_text, source_lang, target),
                        timeout=timeout,
                    )
                else:
                    translated = await asyncio.wait_for(
                        provider.translate(text, source_lang, target),
                        timeout=timeout,
                    )
                # Record metrics
                latency = provider.get_latency_ms()
                try:
                    from app.api.deps import state
                    if state.quality_monitor:
                        state.quality_monitor.record_latency(provider.name, latency)
                    from app.core.metrics import TRANSLATION_REQUESTS, TRANSLATION_LATENCY, TRANSLATION_FAILOVERS
                    TRANSLATION_REQUESTS.labels(provider=provider.name, source_lang=source_lang, target_lang=target, status="success").inc()
                    TRANSLATION_LATENCY.labels(provider=provider.name).observe(latency / 1000)
                    if is_failover:
                        TRANSLATION_FAILOVERS.labels(source_provider="primary", fallback_provider=provider.name).inc()
                except Exception:
                    pass

                if is_failover:
                    log.info("translation_failover", src=source_lang, tgt=target,
                             provider=provider.name)
                return {
                    "lang": target.upper(),
                    "flag": LANG_FLAGS.get(target, ""),
                    "text": translated,
                    "provider": provider.name,
                    "failover": is_failover,
                }
            except asyncio.TimeoutError:
                try:
                    from app.core.metrics import TRANSLATION_REQUESTS
                    TRANSLATION_REQUESTS.labels(provider="timeout", source_lang=source_lang, target_lang=target, status="timeout").inc()
                except Exception:
                    pass
                log.warning("translation_timeout", src=source_lang, tgt=target, timeout=timeout)
                # Last resort: try argos synchronously
                try:
                    argos = self._registry.get("argostranslate")
                    if argos:
                        translated = await argos.translate(text, source_lang, target)
                        return {"lang": target.upper(), "flag": LANG_FLAGS.get(target, ""),
                                "text": translated, "provider": "argostranslate", "failover": True}
                except Exception:
                    pass
                return None
            except TranslationError as exc:
                log.warning("translation_error", src=source_lang, tgt=target, error=str(exc))
                return None

        results = await asyncio.gather(*(translate_one(t) for t in target_langs))
        return [r for r in results if r is not None]
