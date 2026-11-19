"""esquema inicial del marketplace

Revisión: 0001
Anterior:
Fecha: 2026-11-19 04:12:35.371503
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica el cambio de esquema."""
    op.create_table(
        "transportistas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=60), nullable=False),
        sa.Column("ciudad", sa.String(length=30), nullable=False),
        sa.Column("zonas", sa.JSON(), nullable=False),
        sa.Column("vehiculo", sa.String(length=30), nullable=False),
        sa.Column("capacidad_kg", sa.Integer(), nullable=False),
        sa.Column("categorias", sa.JSON(), nullable=False),
        sa.Column("tarifa_base", sa.Integer(), nullable=False),
        sa.Column("telefono", sa.String(length=20), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("suma_estrellas", sa.Integer(), nullable=False),
        sa.Column("num_opiniones", sa.Integer(), nullable=False),
        sa.Column("verificado", sa.Boolean(), nullable=False),
        sa.Column("destacado", sa.Boolean(), nullable=False),
        sa.Column("tono", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transportistas")),
    )
    op.create_table(
        "envios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente", sa.String(length=60), nullable=False),
        sa.Column("transportista_id", sa.Integer(), nullable=False),
        sa.Column("origen", sa.String(length=30), nullable=False),
        sa.Column("destino", sa.String(length=30), nullable=False),
        sa.Column("categoria", sa.String(length=30), nullable=False),
        sa.Column("peso_kg", sa.Integer(), nullable=False),
        sa.Column("fecha_entrega", sa.Date(), nullable=False),
        sa.Column("distancia_km", sa.Integer(), nullable=False),
        sa.Column("precio", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("notas", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("calificacion", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["transportista_id"],
            ["transportistas.id"],
            name=op.f("fk_envios_transportista_id_transportistas"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_envios")),
    )
    with op.batch_alter_table("envios", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_envios_cliente"), ["cliente"], unique=False)
        batch_op.create_index(batch_op.f("ix_envios_estado"), ["estado"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_envios_transportista_id"), ["transportista_id"], unique=False
        )

    op.create_table(
        "eventos_envio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("envio_id", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("ocurrido_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["envio_id"], ["envios.id"], name=op.f("fk_eventos_envio_envio_id_envios")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eventos_envio")),
    )
    with op.batch_alter_table("eventos_envio", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_eventos_envio_envio_id"), ["envio_id"], unique=False)

    op.create_table(
        "opiniones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transportista_id", sa.Integer(), nullable=False),
        sa.Column("autor", sa.String(length=60), nullable=False),
        sa.Column("estrellas", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("envio_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["envio_id"], ["envios.id"], name=op.f("fk_opiniones_envio_id_envios")
        ),
        sa.ForeignKeyConstraint(
            ["transportista_id"],
            ["transportistas.id"],
            name=op.f("fk_opiniones_transportista_id_transportistas"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_opiniones")),
        sa.UniqueConstraint("envio_id", name=op.f("uq_opiniones_envio_id")),
    )
    with op.batch_alter_table("opiniones", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_opiniones_transportista_id"), ["transportista_id"], unique=False
        )


def downgrade() -> None:
    """Revierte el cambio de esquema."""
    with op.batch_alter_table("opiniones", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_opiniones_transportista_id"))

    op.drop_table("opiniones")
    with op.batch_alter_table("eventos_envio", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_eventos_envio_envio_id"))

    op.drop_table("eventos_envio")
    with op.batch_alter_table("envios", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_envios_transportista_id"))
        batch_op.drop_index(batch_op.f("ix_envios_estado"))
        batch_op.drop_index(batch_op.f("ix_envios_cliente"))

    op.drop_table("envios")
    op.drop_table("transportistas")
