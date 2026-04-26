"""Add premium translation providers (DeepL, OpenAI, Google).

Revision ID: m0004
Create Date: 2026-04-26
"""
from alembic import op

revision = "m0004"
down_revision = "m0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add premium providers (disabled by default — need API keys)
    op.execute("""
        INSERT INTO provider_configs (name, provider_type, api_url, api_key_env, supported_pairs, enabled, priority) VALUES
        ('deepl', 'deepl', 'https://api-free.deepl.com/v2', 'DEEPL_API_KEY',
         '[["de","en"],["en","de"],["de","fr"],["fr","de"],["en","fr"],["fr","en"],["de","es"],["es","de"],["de","it"],["it","de"],["de","nl"],["nl","de"],["de","pl"],["pl","de"],["en","es"],["es","en"],["en","it"],["it","en"],["de","pt"],["pt","de"],["de","ru"],["ru","de"],["de","ja"],["ja","de"],["de","zh"],["zh","de"],["de","ko"],["ko","de"]]',
         false, 2),
        ('openai-gpt4o-mini', 'openai', 'https://api.openai.com/v1', 'OPENAI_API_KEY',
         '[["de","en"],["en","de"],["de","fr"],["fr","de"],["en","fr"],["fr","en"],["de","es"],["es","de"],["de","it"],["it","de"],["de","ar"],["ar","de"],["de","zh"],["zh","de"],["de","ja"],["ja","de"],["de","ko"],["ko","de"],["de","hi"],["hi","de"],["de","tr"],["tr","de"],["de","ru"],["ru","de"],["en","ar"],["ar","en"],["en","zh"],["zh","en"],["en","ja"],["ja","en"]]',
         false, 3),
        ('google-translate', 'google', 'https://translation.googleapis.com/language/translate/v2', 'GOOGLE_TRANSLATE_API_KEY',
         '[["de","en"],["en","de"],["de","fr"],["fr","de"],["en","fr"],["fr","en"],["de","es"],["es","de"],["de","it"],["it","de"],["de","ar"],["ar","de"],["de","zh"],["zh","de"],["de","ja"],["ja","de"],["de","ko"],["ko","de"],["de","hi"],["hi","de"],["de","tr"],["tr","de"],["de","ru"],["ru","de"],["de","th"],["th","de"],["de","vi"],["vi","de"]]',
         false, 4)
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM provider_configs WHERE name IN ('deepl', 'openai-gpt4o-mini', 'google-translate')")
