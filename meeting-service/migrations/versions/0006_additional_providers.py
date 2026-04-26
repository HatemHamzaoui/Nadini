"""Add Papago, Azure, Claude, NLLB-200 providers.

Revision ID: m0006
Create Date: 2026-04-26
"""
from alembic import op

revision = "m0006"
down_revision = "m0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO provider_configs (name, provider_type, api_url, api_key_env, supported_pairs, enabled, priority) VALUES
        ('naver-papago', 'papago', 'https://naveropenapi.apigw.ntruss.com/nmt/v1/translation', 'PAPAGO_CLIENT_ID',
         '[["ko","en"],["en","ko"],["ko","de"],["de","ko"],["ko","fr"],["fr","ko"],["ko","es"],["es","ko"],["ko","ja"],["ja","ko"],["ko","zh"],["zh","ko"],["ko","it"],["it","ko"],["ko","ru"],["ru","ko"],["ko","pt"],["pt","ko"],["ko","vi"],["vi","ko"],["ko","th"],["th","ko"],["ko","id"],["id","ko"]]',
         false, 2),
        ('azure-translator', 'azure', 'https://api.cognitive.microsofttranslator.com/translate', 'AZURE_TRANSLATOR_KEY',
         '[["de","en"],["en","de"],["de","fr"],["fr","de"],["de","es"],["es","de"],["de","it"],["it","de"],["de","ar"],["ar","de"],["de","zh"],["zh","de"],["de","ja"],["ja","de"],["de","ko"],["ko","de"],["de","hi"],["hi","de"],["de","tr"],["tr","de"],["de","ru"],["ru","de"],["de","th"],["th","de"],["de","vi"],["vi","de"],["de","id"],["id","de"],["de","uk"],["uk","de"],["de","cs"],["cs","de"],["de","he"],["he","de"],["de","fa"],["fa","de"],["en","ar"],["ar","en"],["en","zh"],["zh","en"],["en","ja"],["ja","en"],["en","ko"],["ko","en"],["en","hi"],["hi","en"]]',
         false, 6),
        ('claude-anthropic', 'claude', 'https://api.anthropic.com/v1/messages', 'ANTHROPIC_API_KEY',
         '[["de","en"],["en","de"],["de","fr"],["fr","de"],["de","es"],["es","de"],["de","ja"],["ja","de"],["de","ko"],["ko","de"],["de","zh"],["zh","de"],["de","ar"],["ar","de"],["de","hi"],["hi","de"],["de","tr"],["tr","de"],["de","th"],["th","de"],["de","vi"],["vi","de"],["en","ja"],["ja","en"],["en","ko"],["ko","en"],["en","zh"],["zh","en"],["en","ar"],["ar","en"]]',
         false, 3),
        ('nllb-200', 'nllb', NULL, NULL,
         '[["de","en"],["en","de"],["de","fr"],["fr","de"],["de","es"],["es","de"],["de","it"],["it","de"],["de","ar"],["ar","de"],["de","zh"],["zh","de"],["de","ja"],["ja","de"],["de","ko"],["ko","de"],["de","hi"],["hi","de"],["de","tr"],["tr","de"],["de","ru"],["ru","de"],["de","th"],["th","de"],["de","vi"],["vi","de"],["de","id"],["id","de"],["de","bn"],["bn","de"],["de","sw"],["sw","de"],["de","am"],["am","de"],["de","he"],["he","de"],["de","fa"],["fa","de"]]',
         false, 8)
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM provider_configs WHERE name IN ('naver-papago', 'azure-translator', 'claude-anthropic', 'nllb-200')")
