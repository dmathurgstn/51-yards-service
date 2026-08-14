"""create authentication tables, preserving the compatible legacy users table."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260807_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    tables = set(sa.inspect(connection).get_table_names())
    if "roles" not in tables:
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(32), nullable=False),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("code"),
        )
        op.create_index("ix_roles_code", "roles", ["code"], unique=True)
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("user_id", sa.BigInteger(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("username", sa.String(120), nullable=False),
            sa.Column("email", sa.String(254), nullable=False),
            sa.Column("mobile_number", sa.String(20)),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("is_verified", sa.Boolean(), nullable=False),
            sa.Column("last_login_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("mobile_number"),
            sa.UniqueConstraint("public_id"),
        )
        op.create_index("ix_users_public_id", "users", ["public_id"], unique=True)
    else:
        columns = {column["name"] for column in sa.inspect(connection).get_columns("users")}
        for name, type_ in (
            ("public_id", sa.String(36)),
            ("is_active", sa.Boolean()),
            ("is_verified", sa.Boolean()),
            ("last_login_at", sa.DateTime(timezone=True)),
            ("updated_at", sa.DateTime(timezone=True)),
        ):
            if name not in columns:
                op.add_column("users", sa.Column(name, type_, nullable=True))
        op.execute(sa.text("UPDATE users SET public_id=UUID() WHERE public_id IS NULL"))
        op.execute(sa.text("UPDATE users SET is_active=1 WHERE is_active IS NULL"))
        op.execute(sa.text("UPDATE users SET is_verified=0 WHERE is_verified IS NULL"))
        op.execute(
            sa.text(
                "UPDATE users SET updated_at=COALESCE(created_at, UTC_TIMESTAMP()) "
                "WHERE updated_at IS NULL"
            )
        )
        for name, type_ in (
            ("public_id", sa.String(36)),
            ("is_active", sa.Boolean()),
            ("is_verified", sa.Boolean()),
            ("updated_at", sa.DateTime(timezone=True)),
        ):
            op.alter_column("users", name, existing_type=type_, nullable=False)
        indexes = {index["name"] for index in sa.inspect(connection).get_indexes("users")}
        if "ix_users_public_id" not in indexes:
            op.create_index("ix_users_public_id", "users", ["public_id"], unique=True)
        if "uq_users_mobile_number" not in indexes:
            op.create_index("uq_users_mobile_number", "users", ["mobile_number"], unique=True)
    tables = set(sa.inspect(connection).get_table_names())
    if "user_roles" not in tables:
        op.create_table(
            "user_roles",
            sa.Column(
                "user_id",
                sa.BigInteger(),
                sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "role_id",
                sa.Integer(),
                sa.ForeignKey("roles.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.BigInteger(),
                sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("jti", sa.String(36), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True)),
            sa.Column("last_used_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("jti"),
        )
        op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
        op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=True)
        op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("roles")
    for column in ("updated_at", "last_login_at", "is_verified", "is_active", "public_id"):
        op.drop_column("users", column)
