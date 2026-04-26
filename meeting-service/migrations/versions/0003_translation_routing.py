"""Translation routing: provider_configs, language_routes, meeting mode.

Revision ID: m0003
Create Date: 2026-04-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "m0003"
down_revision = "m0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── provider_configs ──
    op.create_table(
        "provider_configs",
        sa.Column("provider_id", UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("provider_type", sa.String(30), nullable=False),
        sa.Column("api_url", sa.String(500), nullable=True),
        sa.Column("api_key_env", sa.String(100), nullable=True),
        sa.Column("supported_pairs", JSONB, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="10"),
        sa.Column("config_extra", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("provider_id"),
    )

    # ── language_routes ──
    op.create_table(
        "language_routes",
        sa.Column("route_id", UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("source_lang", sa.String(10), nullable=False),
        sa.Column("target_lang", sa.String(10), nullable=False),
        sa.Column("primary_provider_id", UUID(as_uuid=True), sa.ForeignKey("provider_configs.provider_id"), nullable=False),
        sa.Column("backup_provider_id", UUID(as_uuid=True), sa.ForeignKey("provider_configs.provider_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("route_id"),
        sa.UniqueConstraint("source_lang", "target_lang", name="uq_language_route"),
    )

    # ── meeting mode ──
    op.add_column("meetings", sa.Column("mode", sa.String(10), nullable=False, server_default="online"))
    op.create_check_constraint("meeting_mode_check", "meetings", "mode IN ('live', 'online')")

    # ── Seed data: 3 providers ──
    op.execute("""
        INSERT INTO provider_configs (name, provider_type, supported_pairs, enabled, priority) VALUES
        ('argostranslate', 'argostranslate', '[["de","en"],["en","de"],["de","fr"],["fr","de"],["en","fr"],["fr","en"],["de","es"],["es","de"],["en","es"],["es","en"]]', true, 1),
        ('mistral-voxtral', 'mistral', '[["de","en"],["en","de"],["de","fr"],["fr","de"],["en","fr"],["fr","en"],["de","es"],["es","de"],["en","es"],["es","en"],["de","it"],["it","de"],["de","ar"],["ar","de"],["de","zh"],["zh","de"],["de","ja"],["ja","de"]]', true, 5),
        ('seed-bytedance', 'seed', '[["de","en"],["en","de"],["de","fr"],["fr","de"],["en","fr"],["fr","en"],["de","zh"],["zh","de"],["de","ja"],["ja","de"],["de","ko"],["ko","de"],["en","zh"],["zh","en"],["en","ja"],["ja","en"]]', true, 10)
    """)

    # ── Seed data: default routes (argos primary, mistral backup) ──
    op.execute("""
        INSERT INTO language_routes (source_lang, target_lang, primary_provider_id, backup_provider_id)
        SELECT src, tgt, argos.provider_id, mistral.provider_id
        FROM (VALUES ('de','en'),('en','de'),('de','fr'),('fr','de'),('en','fr'),('fr','en'),('de','es'),('es','de'),('en','es'),('es','en')) AS pairs(src, tgt)
        CROSS JOIN (SELECT provider_id FROM provider_configs WHERE name = 'argostranslate') AS argos
        CROSS JOIN (SELECT provider_id FROM provider_configs WHERE name = 'mistral-voxtral') AS mistral
    """)


def downgrade() -> None:
    op.drop_constraint("meeting_mode_check", "meetings", type_="check")
    op.drop_column("meetings", "mode")
    op.drop_table("language_routes")
    op.drop_table("provider_configs")
