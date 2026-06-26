"""add billing tables fase3

Revision ID: 6960f0440f84
Revises: cc74351769d3
Create Date: 2026-04-25 20:41:21.591066

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6960f0440f84'
down_revision = 'cc74351769d3'
branch_labels = None
depends_on = None


def upgrade():
    # Campo agregado en Fase 1 que puede faltar en algunas bases
    with op.batch_alter_table('inmueble', schema=None) as batch_op:
        batch_op.add_column(sa.Column('estado_detalle', sa.String(length=50), nullable=True))

    op.create_table(
        'contrato_arriendo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('inmueble_id', sa.Integer(), nullable=False),
        sa.Column('incremento', sa.Float(), nullable=True),
        sa.Column('fecha_inicio_contrato', sa.Date(), nullable=False),
        sa.Column('vigencia_contrato', sa.Integer(), nullable=True),
        sa.Column('mes', sa.String(length=20), nullable=True),
        sa.Column('fecha_pago', sa.Date(), nullable=True),
        sa.Column('nombre', sa.String(length=120), nullable=False),
        sa.Column('nit', sa.String(length=50), nullable=True),
        sa.Column('celular', sa.String(length=50), nullable=True),
        sa.Column('direccion', sa.String(length=255), nullable=True),
        sa.Column('direccion2', sa.String(length=255), nullable=True),
        sa.Column('correo', sa.String(length=120), nullable=True),
        sa.Column('canon', sa.Float(), nullable=True),
        sa.Column('estado_pago_inquilino', sa.String(length=20), nullable=True),
        sa.Column('fecha_limite', sa.Date(), nullable=True),
        sa.Column('dias_mora', sa.Integer(), nullable=True),
        sa.Column('pago', sa.Float(), nullable=True),
        sa.Column('propietario', sa.String(length=120), nullable=True),
        sa.Column('comision', sa.Float(), nullable=True),
        sa.Column('pago_adicional', sa.Float(), nullable=True),
        sa.Column('reintegro', sa.Float(), nullable=True),
        sa.Column('pago_propietario', sa.Float(), nullable=True),
        sa.Column('estado_pago_propietario', sa.String(length=20), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=True),
        sa.Column('actualizado_en', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['inmueble_id'], ['inmueble.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'pago_arriendo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contrato_id', sa.Integer(), nullable=False),
        sa.Column('fecha_pago', sa.Date(), nullable=False),
        sa.Column('valor_pagado', sa.Float(), nullable=True),
        sa.Column('mes_correspondiente', sa.String(length=20), nullable=False),
        sa.Column('anio_correspondiente', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=True),
        sa.Column('observacion', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contrato_id'], ['contrato_arriendo.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'ingreso',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('propiedad_id', sa.Integer(), nullable=True),
        sa.Column('cliente', sa.String(length=120), nullable=True),
        sa.Column('valor', sa.Float(), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=True),
        sa.Column('observacion', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['propiedad_id'], ['inmueble.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'otro_ingreso',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('cliente', sa.String(length=120), nullable=True),
        sa.Column('propiedad', sa.String(length=200), nullable=True),
        sa.Column('valor', sa.Float(), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=True),
        sa.Column('observacion', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'gasto',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('categoria', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('valor', sa.Float(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'factura_electronica',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('numero_factura', sa.String(length=50), nullable=False),
        sa.Column('contrato_id', sa.Integer(), nullable=True),
        sa.Column('cliente_nombre', sa.String(length=120), nullable=False),
        sa.Column('cliente_nit', sa.String(length=50), nullable=True),
        sa.Column('cliente_correo', sa.String(length=120), nullable=True),
        sa.Column('valor_total', sa.Float(), nullable=True),
        sa.Column('valor_arriendo', sa.Float(), nullable=True),
        sa.Column('valor_comision', sa.Float(), nullable=True),
        sa.Column('otros_valores', sa.Float(), nullable=True),
        sa.Column('fecha_emision', sa.DateTime(), nullable=True),
        sa.Column('fecha_vencimiento', sa.Date(), nullable=True),
        sa.Column('estado_dian', sa.String(length=20), nullable=True),
        sa.Column('cufe', sa.String(length=100), nullable=True),
        sa.Column('xml_firmado', sa.Text(), nullable=True),
        sa.Column('pdf_url', sa.String(length=500), nullable=True),
        sa.Column('observacion', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contrato_id'], ['contrato_arriendo.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero_factura')
    )


def downgrade():
    op.drop_table('factura_electronica')
    op.drop_table('gasto')
    op.drop_table('otro_ingreso')
    op.drop_table('ingreso')
    op.drop_table('pago_arriendo')
    op.drop_table('contrato_arriendo')

    with op.batch_alter_table('inmueble', schema=None) as batch_op:
        batch_op.drop_column('estado_detalle')
