"""Configure optimal routing for all 30 language pairs.

Primary + Backup per pair based on provider strengths:
- DeepL: EU-Sprachen (DE/EN/FR/ES/IT/NL/PL/PT/RU)
- OpenAI GPT-4o-mini: CJK + Arabisch (kontextuell)
- Google Translate: breite Abdeckung, Fallback
- argostranslate: immer-verfügbar Offline-Fallback

Revision ID: m0005
Create Date: 2026-04-26
"""
from alembic import op

revision = "m0005"
down_revision = "m0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove old default routes (from migration 0003)
    op.execute("DELETE FROM language_routes")

    # Insert optimized routes with correct provider assignments
    op.execute("""
        INSERT INTO language_routes (source_lang, target_lang, primary_provider_id, backup_provider_id)

        -- ═══ TIER 1: EU-Kernsprachen — DeepL primary, argostranslate backup ═══
        SELECT 'de', 'en', deepl.pid, argos.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'argostranslate') argos
        UNION ALL SELECT 'en', 'de', deepl.pid, argos.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'argostranslate') argos
        UNION ALL SELECT 'de', 'fr', deepl.pid, argos.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'argostranslate') argos
        UNION ALL SELECT 'fr', 'de', deepl.pid, argos.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'argostranslate') argos
        UNION ALL SELECT 'en', 'fr', deepl.pid, argos.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'argostranslate') argos
        UNION ALL SELECT 'fr', 'en', deepl.pid, argos.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'argostranslate') argos

        -- DeepL primary, Google backup
        UNION ALL SELECT 'de', 'es', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'es', 'de', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'de', 'it', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'it', 'de', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'de', 'nl', deepl.pid, argos.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'argostranslate') argos
        UNION ALL SELECT 'de', 'pl', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'de', 'pt', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'de', 'ru', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'ru', 'de', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'en', 'es', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'es', 'en', deepl.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'deepl') deepl,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google

        -- ═══ TIER 2: CJK + Arabisch — OpenAI primary, Google backup ═══
        UNION ALL SELECT 'de', 'ar', openai.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'ar', 'de', openai.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'de', 'zh', openai.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'zh', 'de', openai.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'de', 'ja', openai.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'ja', 'de', openai.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'en', 'zh', openai.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'en', 'ja', openai.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google
        UNION ALL SELECT 'en', 'ar', openai.pid, google.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google

        -- ═══ TIER 2: Korea, Türkisch, Hindi — Google primary, OpenAI backup ═══
        UNION ALL SELECT 'de', 'ko', google.pid, openai.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai
        UNION ALL SELECT 'ko', 'de', google.pid, openai.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai
        UNION ALL SELECT 'de', 'tr', google.pid, openai.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai
        UNION ALL SELECT 'tr', 'de', google.pid, openai.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai
        UNION ALL SELECT 'de', 'hi', google.pid, openai.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai
        UNION ALL SELECT 'en', 'ko', google.pid, openai.pid FROM
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'google-translate') google,
            (SELECT provider_id AS pid FROM provider_configs WHERE name = 'openai-gpt4o-mini') openai
    """)


def downgrade() -> None:
    op.execute("DELETE FROM language_routes")
