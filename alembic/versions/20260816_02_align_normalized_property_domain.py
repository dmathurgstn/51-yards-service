"""align Sprint 6 with the existing normalized property schema"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "20260816_02"
down_revision: str | None = "20260807_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {value["name"] for value in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {value["name"] for value in sa.inspect(op.get_bind()).get_indexes(table)}


def _require_normalized_schema() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    required = {
        "properties",
        "property_amenities",
        "property_status_history",
        "amenities_master",
        "property_location",
        "property_sell_details",
        "property_rent_details",
        "property_lease_details",
        "property_types",
    }
    missing = required - tables
    if missing:
        raise RuntimeError(
            "Expected normalized property baseline is missing tables: " + ", ".join(sorted(missing))
        )
    expected = {
        "properties": {"property_id", "user_id", "transaction_type", "property_type"},
        "property_amenities": {"id", "property_id", "amenity_id"},
        "property_status_history": {"history_id", "property_id", "changed_at"},
        "amenities_master": {"amenity_id", "name"},
    }
    for table, columns in expected.items():
        absent = columns - _columns(table)
        if absent:
            raise RuntimeError(f"Unexpected {table} structure; missing columns: {sorted(absent)}")


def _create_masters() -> None:
    op.create_table(
        "states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(8), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_states_code", "states", ["code"], unique=True)
    op.create_index("ix_states_name", "states", ["name"], unique=True)
    op.create_index("ix_states_is_active", "states", ["is_active"])
    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state_id", sa.Integer(), sa.ForeignKey("states.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("state_id", "slug", name="uq_cities_state_slug"),
    )
    for column in ("state_id", "name", "slug", "is_active"):
        op.create_index(f"ix_cities_{column}", "cities", [column])
    op.create_table(
        "localities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(140), nullable=False),
        sa.Column("pin_code", sa.String(10)),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("city_id", "slug", name="uq_localities_city_slug"),
    )
    for column in ("city_id", "name", "slug", "is_active"):
        op.create_index(f"ix_localities_{column}", "localities", [column])
    op.create_table(
        "property_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_property_categories_code", "property_categories", ["code"], unique=True)
    op.create_index("ix_property_categories_is_active", "property_categories", ["is_active"])


def upgrade() -> None:
    _require_normalized_schema()
    _create_masters()
    for column in (
        sa.Column("category_id", sa.Integer()),
        sa.Column("code", sa.String(50)),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    ):
        if column.name not in _columns("property_types"):
            op.add_column("property_types", column)
    op.execute(
        sa.text(
            "UPDATE property_types SET code=UPPER(REPLACE(TRIM(name), ' ', '_')) WHERE code IS NULL"
        )
    )
    op.create_foreign_key(
        "fk_property_types_category",
        "property_types",
        "property_categories",
        ["category_id"],
        ["id"],
    )
    op.create_index("ix_property_types_category_id", "property_types", ["category_id"])
    op.create_index("ix_property_types_code", "property_types", ["code"], unique=True)
    op.create_index("ix_property_types_is_active", "property_types", ["is_active"])
    for column in (
        sa.Column("code", sa.String(50)),
        sa.Column("icon_key", sa.String(80)),
        sa.Column("category", sa.String(80)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    ):
        if column.name not in _columns("amenities_master"):
            op.add_column("amenities_master", column)
    op.execute(
        sa.text(
            "UPDATE amenities_master "
            "SET code=UPPER(REPLACE(TRIM(name), ' ', '_')) WHERE code IS NULL"
        )
    )
    op.create_index("ix_amenities_master_code", "amenities_master", ["code"], unique=True)
    op.create_index("ix_amenities_master_is_active", "amenities_master", ["is_active"])
    for column in (
        sa.Column("public_id", sa.String(36)),
        sa.Column("property_category_id", sa.Integer()),
        sa.Column("construction_status", sa.String(24)),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("submitted_at", sa.DateTime()),
        sa.Column("approved_at", sa.DateTime()),
    ):
        if column.name not in _columns("properties"):
            op.add_column("properties", column)
    op.execute(sa.text("UPDATE properties SET public_id=UUID() WHERE public_id IS NULL"))
    op.create_foreign_key(
        "fk_properties_category",
        "properties",
        "property_categories",
        ["property_category_id"],
        ["id"],
    )
    op.alter_column("properties", "public_id", existing_type=sa.String(36), nullable=False)
    op.alter_column(
        "properties",
        "status",
        existing_type=mysql.ENUM("DRAFT", "ACTIVE", "INACTIVE", "SOLD", "RENTED"),
        type_=mysql.ENUM(
            "DRAFT",
            "PENDING_REVIEW",
            "ACTIVE",
            "REJECTED",
            "PAUSED",
            "EXPIRED",
            "ARCHIVED",
            "INACTIVE",
            "SOLD",
            "RENTED",
        ),
        existing_nullable=True,
        existing_server_default="DRAFT",
    )
    op.alter_column(
        "properties",
        "area_unit",
        existing_type=mysql.ENUM("SQFT", "SQM"),
        type_=mysql.ENUM("SQFT", "SQM", "SQ_FT", "SQ_YARD", "SQ_METER", "ACRE"),
        existing_nullable=True,
    )
    op.create_index("ix_properties_public_id", "properties", ["public_id"], unique=True)
    op.create_index("ix_properties_property_category_id", "properties", ["property_category_id"])
    op.create_index("ix_properties_owner_status", "properties", ["user_id", "status"])
    for column in (
        sa.Column("state_id", sa.Integer()),
        sa.Column("city_id", sa.Integer()),
        sa.Column("locality_id", sa.Integer()),
    ):
        if column.name not in _columns("property_location"):
            op.add_column("property_location", column)
        op.create_index(f"ix_property_location_{column.name}", "property_location", [column.name])
    for name, column, target in (
        ("fk_property_location_state", "state_id", "states"),
        ("fk_property_location_city", "city_id", "cities"),
        ("fk_property_location_locality", "locality_id", "localities"),
    ):
        op.create_foreign_key(name, "property_location", target, [column], ["id"])
    if "uq_property_location_property_id" not in _indexes("property_location"):
        op.create_unique_constraint(
            "uq_property_location_property_id", "property_location", ["property_id"]
        )
    common = (
        sa.Column("maintenance_charge", sa.Numeric(14, 2)),
        sa.Column("brokerage_amount", sa.Numeric(14, 2)),
    )
    for table in ("property_sell_details", "property_rent_details", "property_lease_details"):
        for column in common:
            if column.name not in _columns(table):
                op.add_column(table, sa.Column(column.name, column.type))
    for table in ("property_rent_details", "property_lease_details"):
        for column in (
            sa.Column("is_negotiable", sa.Boolean()),
            sa.Column("available_from", sa.Date()),
            sa.Column("security_deposit", sa.Numeric(16, 2)),
        ):
            if column.name not in _columns(table):
                op.add_column(table, column)
    if "created_at" not in _columns("property_amenities"):
        op.add_column(
            "property_amenities",
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if "changed_by_user_id" not in _columns("property_status_history"):
        op.add_column(
            "property_status_history",
            sa.Column("changed_by_user_id", sa.BigInteger()),
        )
        op.create_foreign_key(
            "fk_property_status_history_changed_by",
            "property_status_history",
            "users",
            ["changed_by_user_id"],
            ["user_id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "ix_property_status_history_changed_by_user_id",
            "property_status_history",
            ["changed_by_user_id"],
        )
    op.create_index(
        "ix_property_status_history_changed_at",
        "property_status_history",
        ["changed_at"],
    )


def downgrade() -> None:
    # Adopted legacy tables are intentionally retained. Only Sprint 6 additions are reversed.
    op.drop_index("ix_property_status_history_changed_at", "property_status_history")
    op.drop_constraint(
        "fk_property_status_history_changed_by", "property_status_history", type_="foreignkey"
    )
    op.drop_index("ix_property_status_history_changed_by_user_id", "property_status_history")
    op.drop_constraint("uq_property_location_property_id", "property_location", type_="unique")
    for name, column in (
        ("fk_property_location_locality", "locality_id"),
        ("fk_property_location_city", "city_id"),
        ("fk_property_location_state", "state_id"),
    ):
        op.drop_constraint(name, "property_location", type_="foreignkey")
        op.drop_index(f"ix_property_location_{column}", "property_location")
    op.drop_constraint("fk_properties_category", "properties", type_="foreignkey")
    op.drop_index("ix_properties_owner_status", "properties")
    op.drop_index("ix_properties_property_category_id", "properties")
    op.drop_index("ix_properties_public_id", "properties")
    op.drop_index("ix_amenities_master_is_active", "amenities_master")
    op.drop_index("ix_amenities_master_code", "amenities_master")
    op.drop_constraint("fk_property_types_category", "property_types", type_="foreignkey")
    op.drop_index("ix_property_types_is_active", "property_types")
    op.drop_index("ix_property_types_code", "property_types")
    op.drop_index("ix_property_types_category_id", "property_types")
    for table, columns in (
        ("property_status_history", ["changed_by_user_id"]),
        ("property_amenities", ["created_at"]),
        (
            "property_lease_details",
            [
                "maintenance_charge",
                "brokerage_amount",
                "is_negotiable",
                "available_from",
                "security_deposit",
            ],
        ),
        ("property_rent_details", ["maintenance_charge", "brokerage_amount", "is_negotiable"]),
        ("property_sell_details", ["maintenance_charge", "brokerage_amount"]),
        ("property_location", ["locality_id", "city_id", "state_id"]),
        (
            "properties",
            [
                "approved_at",
                "submitted_at",
                "rejection_reason",
                "construction_status",
                "property_category_id",
                "public_id",
            ],
        ),
        (
            "amenities_master",
            ["updated_at", "created_at", "sort_order", "is_active", "category", "icon_key", "code"],
        ),
        (
            "property_types",
            [
                "updated_at",
                "created_at",
                "sort_order",
                "is_active",
                "description",
                "code",
                "category_id",
            ],
        ),
    ):
        for column in columns:
            if column in _columns(table):
                op.drop_column(table, column)
    for table in ("property_categories", "localities", "cities", "states"):
        op.drop_table(table)
