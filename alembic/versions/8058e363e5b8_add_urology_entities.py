"""add_urology_entities

Revision ID: 8058e363e5b8
Revises: 07f9f1b33bd3
Create Date: 2026-01-24 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8058e363e5b8"
down_revision: Union[str, Sequence[str], None] = "07f9f1b33bd3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create basic_info table
    op.create_table(
        "basic_info",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_name", sa.String(length=100), nullable=False),
        sa.Column("gender", sa.String(length=20), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("occupation", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("diet_preference", sa.Text(), nullable=True),
        sa.Column("likes_diet_preference", sa.Text(), nullable=True),
        sa.Column("dislikes_diet_preference", sa.Text(), nullable=True),
        sa.Column("lifestyle", sa.Text(), nullable=True),
        sa.Column("daily_water_intake", sa.String(length=100), nullable=True),
        sa.Column("medical_history", sa.Text(), nullable=True),
        sa.Column("stone_discovery_method", sa.String(length=200), nullable=True),
        sa.Column("previous_urinary_infection_pathogen", sa.Text(), nullable=True),
        sa.Column("previous_infection_medication", sa.Text(), nullable=True),
        sa.Column("family_history_of_stone", sa.Boolean(), nullable=True),
        sa.Column("repeated_urinary_infection", sa.Boolean(), nullable=True),
        sa.Column("first_urinary_infection_time", sa.Date(), nullable=True),
        sa.Column("surgery_date", sa.Date(), nullable=True),
        sa.Column("surgery_type", sa.String(length=200), nullable=True),
        sa.Column("stone_composition", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id"),
    )
    op.create_index(op.f("ix_basic_info_patient_id"), "basic_info", ["patient_id"], unique=True)

    # Create surgery_indicators table
    op.create_table(
        "surgery_indicators",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_name", sa.String(length=100), nullable=True),
        sa.Column("clinical_diagnosis", sa.Text(), nullable=True),
        sa.Column("stone_location", sa.JSON(), nullable=True),
        sa.Column("stone_size", sa.String(length=100), nullable=True),
        sa.Column("hydronephrosis_degree", sa.String(length=50), nullable=True),
        # Pre-operative lab values
        sa.Column("alt_value_before", sa.Float(), nullable=True),
        sa.Column("ast_value_before", sa.Float(), nullable=True),
        sa.Column("ggt_value_before", sa.Float(), nullable=True),
        sa.Column("scr_value_before", sa.Float(), nullable=True),
        sa.Column("wbc_value_before", sa.Float(), nullable=True),
        sa.Column("hb_value_before", sa.Float(), nullable=True),
        sa.Column("urine_ph_value_before", sa.Float(), nullable=True),
        sa.Column("urine_nit_value_before", sa.String(length=100), nullable=True),
        sa.Column("urine_wbc_value_before", sa.String(length=100), nullable=True),
        sa.Column("urine_culture_result_before", sa.Text(), nullable=True),
        sa.Column("urine_ngs_result_before", sa.Text(), nullable=True),
        # Post-operative lab values
        sa.Column("alt_value_after", sa.Float(), nullable=True),
        sa.Column("ast_value_after", sa.Float(), nullable=True),
        sa.Column("ggt_value_after", sa.Float(), nullable=True),
        sa.Column("scr_value_after", sa.Float(), nullable=True),
        sa.Column("wbc_value_after", sa.Float(), nullable=True),
        sa.Column("hb_value_after", sa.Float(), nullable=True),
        sa.Column("urine_ph_value_after", sa.Float(), nullable=True),
        sa.Column("urine_nit_value_after", sa.String(length=100), nullable=True),
        sa.Column("urine_wbc_value_after", sa.String(length=100), nullable=True),
        sa.Column("urine_culture_result_after", sa.Text(), nullable=True),
        sa.Column("urine_ngs_result_after", sa.Text(), nullable=True),
        # Post-op stone analysis
        sa.Column("stone_culture_result_after", sa.Text(), nullable=True),
        sa.Column("stone_ngs_result_after", sa.Text(), nullable=True),
        sa.Column("stone_composition_after", sa.JSON(), nullable=True),
        sa.Column("stone_clearance_after", sa.String(length=100), nullable=True),
        sa.Column("imaging_method_after", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id"),
    )
    op.create_index(
        op.f("ix_surgery_indicators_patient_id"), "surgery_indicators", ["patient_id"], unique=True
    )

    # Create clinical_followups table
    op.create_table(
        "clinical_followups",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_name", sa.String(length=100), nullable=True),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("followup_date", sa.Date(), nullable=True),
        sa.Column("followup_recurrence", sa.String(length=200), nullable=True),
        sa.Column("followup_stone_size", sa.String(length=100), nullable=True),
        sa.Column("followup_imaging", sa.Text(), nullable=True),
        # Lab values at follow-up
        sa.Column("followup_alt", sa.Float(), nullable=True),
        sa.Column("followup_ast", sa.Float(), nullable=True),
        sa.Column("followup_ggt", sa.Float(), nullable=True),
        sa.Column("followup_scr", sa.Float(), nullable=True),
        sa.Column("followup_wbc", sa.Float(), nullable=True),
        sa.Column("followup_hb", sa.Float(), nullable=True),
        sa.Column("followup_urine_ph", sa.Float(), nullable=True),
        sa.Column("followup_urine_nit", sa.String(length=100), nullable=True),
        sa.Column("followup_urine_wbc", sa.String(length=100), nullable=True),
        sa.Column("followup_urine_culture", sa.Text(), nullable=True),
        # Medication tracking
        sa.Column("followup_medication", sa.String(length=200), nullable=True),
        sa.Column("followup_medication_dose", sa.Float(), nullable=True),
        sa.Column("followup_medication_days", sa.Float(), nullable=True),
        sa.Column("followup_compliance", sa.String(length=100), nullable=True),
        sa.Column("followup_adverse", sa.Text(), nullable=True),
        sa.Column("followup_plan", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_clinical_followups_patient_id"), "clinical_followups", ["patient_id"], unique=False
    )
    op.create_index(op.f("ix_clinical_followups_stage"), "clinical_followups", ["stage"], unique=False)

    # Create nursing_followups table
    op.create_table(
        "nursing_followups",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_name", sa.String(length=100), nullable=True),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("followup_date", sa.Date(), nullable=True),
        sa.Column("nursing_mode", sa.String(length=50), nullable=True),
        # Medication info
        sa.Column("nursing_discharge_drug", sa.Text(), nullable=True),
        sa.Column("nursing_antibiotic", sa.String(length=200), nullable=True),
        sa.Column("nursing_antibiotic_dose", sa.String(length=100), nullable=True),
        sa.Column("nursing_other_drug", sa.String(length=200), nullable=True),
        sa.Column("nursing_other_drug_dose", sa.String(length=100), nullable=True),
        sa.Column("nursing_timed_med", sa.Boolean(), nullable=True),
        # Urine monitoring
        sa.Column("nursing_urine_ph", sa.Float(), nullable=True),
        sa.Column("nursing_urine_output", sa.Boolean(), nullable=True),
        sa.Column("nursing_urine_color", sa.Integer(), nullable=True),
        # Adverse effects and conditions
        sa.Column("nursing_adverse_effects", sa.Text(), nullable=True),
        sa.Column("nursing_acidosis", sa.Boolean(), nullable=True),
        sa.Column("nursing_hco3", sa.Float(), nullable=True),
        # Location and stone tracking
        sa.Column("nursing_followup_location", sa.String(length=200), nullable=True),
        sa.Column("nursing_residual_stone", sa.String(length=200), nullable=True),
        # Lifestyle
        sa.Column("nursing_water", sa.String(length=200), nullable=True),
        sa.Column("nursing_diet", sa.Text(), nullable=True),
        # Mental health
        sa.Column("nursing_psqi", sa.String(length=100), nullable=True),
        sa.Column("nursing_psqi_drug", sa.String(length=200), nullable=True),
        sa.Column("nursing_depression", sa.String(length=100), nullable=True),
        sa.Column("nursing_depression_anxiety", sa.String(length=200), nullable=True),
        sa.Column("nursing_support", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_nursing_followups_patient_id"), "nursing_followups", ["patient_id"], unique=False
    )
    op.create_index(op.f("ix_nursing_followups_stage"), "nursing_followups", ["stage"], unique=False)

    # Create terminology_overrides table
    op.create_table(
        "terminology_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("scope_type", sa.String(length=20), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("term_key", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("display_value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_type", "scope_id", "term_key", "locale", name="uq_terminology_override"),
    )
    op.create_index(
        op.f("ix_terminology_overrides_scope_type"), "terminology_overrides", ["scope_type"], unique=False
    )
    op.create_index(
        op.f("ix_terminology_overrides_scope_id"), "terminology_overrides", ["scope_id"], unique=False
    )
    op.create_index(
        op.f("ix_terminology_overrides_term_key"), "terminology_overrides", ["term_key"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop terminology_overrides
    op.drop_index(op.f("ix_terminology_overrides_term_key"), table_name="terminology_overrides")
    op.drop_index(op.f("ix_terminology_overrides_scope_id"), table_name="terminology_overrides")
    op.drop_index(op.f("ix_terminology_overrides_scope_type"), table_name="terminology_overrides")
    op.drop_table("terminology_overrides")

    # Drop nursing_followups
    op.drop_index(op.f("ix_nursing_followups_stage"), table_name="nursing_followups")
    op.drop_index(op.f("ix_nursing_followups_patient_id"), table_name="nursing_followups")
    op.drop_table("nursing_followups")

    # Drop clinical_followups
    op.drop_index(op.f("ix_clinical_followups_stage"), table_name="clinical_followups")
    op.drop_index(op.f("ix_clinical_followups_patient_id"), table_name="clinical_followups")
    op.drop_table("clinical_followups")

    # Drop surgery_indicators
    op.drop_index(op.f("ix_surgery_indicators_patient_id"), table_name="surgery_indicators")
    op.drop_table("surgery_indicators")

    # Drop basic_info
    op.drop_index(op.f("ix_basic_info_patient_id"), table_name="basic_info")
    op.drop_table("basic_info")
