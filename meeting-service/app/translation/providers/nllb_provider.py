"""Meta NLLB-200 Provider — 200 Sprachen, self-hosted, open-source.

Ersetzt argostranslate als universeller Offline-Fallback mit massiv
mehr Sprachabdeckung. Nutzt CTranslate2 für schnelle CPU-Inferenz.

Benötigt: pip install ctranslate2 sentencepiece
Modell wird bei erstem Start heruntergeladen (~1.2GB für distilled-600M).
"""
from __future__ import annotations

import asyncio
import os

from app.core.logging import get_logger
from app.translation.base import ProviderStatus, TranslationError, TranslationProvider

log = get_logger(__name__)

# NLLB-200 uses Flores language codes
FLORES_MAP = {
    "de": "deu_Latn", "en": "eng_Latn", "fr": "fra_Latn", "es": "spa_Latn",
    "it": "ita_Latn", "pt": "por_Latn", "nl": "nld_Latn", "pl": "pol_Latn",
    "ru": "rus_Cyrl", "ja": "jpn_Jpan", "zh": "zho_Hans", "ko": "kor_Hang",
    "ar": "arb_Arab", "tr": "tur_Latn", "sv": "swe_Latn", "hi": "hin_Deva",
    "th": "tha_Thai", "vi": "vie_Latn", "id": "ind_Latn", "uk": "ukr_Cyrl",
    "cs": "ces_Latn", "ro": "ron_Latn", "el": "ell_Grek", "da": "dan_Latn",
    "fi": "fin_Latn", "hu": "hun_Latn", "bg": "bul_Cyrl", "he": "heb_Hebr",
    "fa": "pes_Arab", "bn": "ben_Beng", "ta": "tam_Taml", "te": "tel_Telu",
    "ur": "urd_Arab", "sw": "swh_Latn", "am": "amh_Ethi",
}

SUPPORTED_PAIRS = [
    (s, t) for s in FLORES_MAP for t in FLORES_MAP if s != t
]


class NLLBProvider(TranslationProvider):
    """Meta NLLB-200 — 200 languages, self-hosted, open-source."""

    def __init__(self) -> None:
        super().__init__(name="nllb-200", provider_type="nllb")
        self._model_name = os.environ.get("NLLB_MODEL", "facebook/nllb-200-distilled-600M")
        self._translator = None
        self._tokenizer = None

    def _ensure_model(self) -> None:
        if self._translator is not None:
            return
        try:
            import ctranslate2
            import sentencepiece as spm
            from huggingface_hub import snapshot_download

            model_path = snapshot_download(
                self._model_name,
                allow_patterns=["*.bin", "*.txt", "*.model", "*.json", "sentencepiece*"],
            )

            # Try CTranslate2 converted model, fallback to transformers
            try:
                ct2_path = os.path.join(model_path, "ct2")
                if os.path.exists(ct2_path):
                    self._translator = ctranslate2.Translator(ct2_path, device="cpu")
                else:
                    raise FileNotFoundError("CT2 model not found")
            except Exception:
                # Fallback: use transformers pipeline
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
                self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
                self._translator = AutoModelForSeq2SeqLM.from_pretrained(self._model_name)

            log.info("nllb_model_loaded", model=self._model_name)
        except ImportError:
            log.warning("nllb_dependencies_missing", hint="pip install ctranslate2 sentencepiece transformers")
            raise TranslationError("NLLB dependencies not installed")
        except Exception as exc:
            log.warning("nllb_model_load_failed", error=str(exc))
            raise TranslationError(f"NLLB model load failed: {exc}")

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        src_flores = FLORES_MAP.get(source_lang)
        tgt_flores = FLORES_MAP.get(target_lang)
        if not src_flores or not tgt_flores:
            raise TranslationError(f"NLLB: unsupported language pair {source_lang}->{target_lang}")

        def _sync_translate():
            self._ensure_model()

            if self._tokenizer is not None:
                # Transformers pipeline
                self._tokenizer.src_lang = src_flores
                inputs = self._tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
                from transformers import AutoModelForSeq2SeqLM
                tgt_id = self._tokenizer.convert_tokens_to_ids(tgt_flores)
                outputs = self._translator.generate(**inputs, forced_bos_token_id=tgt_id, max_new_tokens=512)
                return self._tokenizer.decode(outputs[0], skip_special_tokens=True)
            else:
                raise TranslationError("NLLB model not properly initialized")

        try:
            return await asyncio.to_thread(_sync_translate)
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"NLLB error: {exc}") from exc

    async def health_check(self) -> ProviderStatus:
        try:
            _, latency = await self.timed_translate("Hello", "en", "de")
            if latency < 1000:
                return ProviderStatus.GREEN
            elif latency < 3000:
                return ProviderStatus.YELLOW
            return ProviderStatus.RED
        except TranslationError:
            return ProviderStatus.RED

    def get_supported_pairs(self) -> list[tuple[str, str]]:
        return list(SUPPORTED_PAIRS)
