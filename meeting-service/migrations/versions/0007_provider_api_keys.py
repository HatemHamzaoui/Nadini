"""Add api_key column to provider_configs for DB-stored keys.

Keys are stored in the database so admins can configure them via UI.
The api_key_env column remains for backward-compat (env var override).

Revision ID: m0007
Create Date: 2026-04-26
"""
import sqlalchemy as sa
from alembic import op

revision = "m0007"
down_revision = "m0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("provider_configs", sa.Column("api_key", sa.Text, nullable=True))

    # Add DeepSeek provider
    op.execute("""
        INSERT INTO provider_configs (name, provider_type, api_url, api_key_env, supported_pairs, enabled, priority)
        VALUES ('deepseek', 'deepseek', 'https://api.deepseek.com/v1', 'DEEPSEEK_API_KEY',
         '[["de","en"],["en","de"],["de","fr"],["fr","de"],["en","fr"],["fr","en"],["de","es"],["es","de"],["de","zh"],["zh","de"],["de","ja"],["ja","de"],["de","ko"],["ko","de"],["de","ar"],["ar","de"],["de","hi"],["hi","de"],["de","tr"],["tr","de"],["en","zh"],["zh","en"],["en","ja"],["ja","en"],["en","ko"],["ko","en"],["en","ar"],["ar","en"]]',
         false, 4)
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_column("provider_configs", "api_key")
