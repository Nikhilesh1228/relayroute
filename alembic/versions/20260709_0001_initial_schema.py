"""Initial RelayRoute schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "20260709_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    op.create_table(
        "deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("courier_id", sa.String(length=36), nullable=True),
        sa.Column("pickup_address", sa.String(length=500), nullable=False),
        sa.Column("pickup_latitude", sa.Float(), nullable=False),
        sa.Column("pickup_longitude", sa.Float(), nullable=False),
        sa.Column("dropoff_address", sa.String(length=500), nullable=False),
        sa.Column("dropoff_latitude", sa.Float(), nullable=False),
        sa.Column("dropoff_longitude", sa.Float(), nullable=False),
        sa.Column("package", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("relay_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["courier_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(op.f("ix_deliveries_courier_id"), "deliveries", ["courier_id"])
    op.create_index(op.f("ix_deliveries_customer_id"), "deliveries", ["customer_id"])
    op.create_index(op.f("ix_deliveries_status"), "deliveries", ["status"])

    op.create_table(
        "delivery_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("delivery_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_delivery_events_delivery_id"), "delivery_events", ["delivery_id"])
    op.create_index(op.f("ix_delivery_events_event_type"), "delivery_events", ["event_type"])

    op.create_table(
        "handoff_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("delivery_id", sa.String(length=36), nullable=False),
        sa.Column("from_courier_id", sa.String(length=36), nullable=False),
        sa.Column("to_courier_id", sa.String(length=36), nullable=True),
        sa.Column("meetup_latitude", sa.Float(), nullable=False),
        sa.Column("meetup_longitude", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_courier_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_courier_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_handoff_offers_delivery_id"), "handoff_offers", ["delivery_id"])
    op.create_index(
        op.f("ix_handoff_offers_from_courier_id"), "handoff_offers", ["from_courier_id"]
    )
    op.create_index(op.f("ix_handoff_offers_status"), "handoff_offers", ["status"])

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("topic", sa.String(length=120), nullable=False),
        sa.Column("event_key", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outbox_events_created_at"), "outbox_events", ["created_at"])
    op.create_index(op.f("ix_outbox_events_topic"), "outbox_events", ["topic"])


def downgrade() -> None:
    op.drop_index(op.f("ix_outbox_events_topic"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_created_at"), table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index(op.f("ix_handoff_offers_status"), table_name="handoff_offers")
    op.drop_index(op.f("ix_handoff_offers_from_courier_id"), table_name="handoff_offers")
    op.drop_index(op.f("ix_handoff_offers_delivery_id"), table_name="handoff_offers")
    op.drop_table("handoff_offers")
    op.drop_index(op.f("ix_delivery_events_event_type"), table_name="delivery_events")
    op.drop_index(op.f("ix_delivery_events_delivery_id"), table_name="delivery_events")
    op.drop_table("delivery_events")
    op.drop_index(op.f("ix_deliveries_status"), table_name="deliveries")
    op.drop_index(op.f("ix_deliveries_customer_id"), table_name="deliveries")
    op.drop_index(op.f("ix_deliveries_courier_id"), table_name="deliveries")
    op.drop_table("deliveries")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
