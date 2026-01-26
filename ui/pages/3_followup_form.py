"""Follow-up Registration Form page for Streamlit UI."""

import streamlit as st
from datetime import date

# Import from parent app
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app import api_request, init_session_state, render_sidebar, t

# Page configuration
st.set_page_config(
    page_title="Follow-up Registration",
    page_icon="📋",
    layout="wide",
)

# Initialize session state
init_session_state()

# Render sidebar
render_sidebar()

# Form step state
if "form_step" not in st.session_state:
    st.session_state.form_step = 1

if "form_data" not in st.session_state:
    st.session_state.form_data = {}


def next_step() -> None:
    """Move to next form step."""
    if st.session_state.form_step < 4:
        st.session_state.form_step += 1


def prev_step() -> None:
    """Move to previous form step."""
    if st.session_state.form_step > 1:
        st.session_state.form_step -= 1


def render_step_indicator() -> None:
    """Render the step indicator at the top of the form."""
    steps = [
        t("followup.form.step1"),
        t("followup.form.step2"),
        t("followup.form.step3"),
        t("followup.form.step4"),
    ]

    cols = st.columns(4)
    for i, (col, step_name) in enumerate(zip(cols, steps), 1):
        with col:
            if i == st.session_state.form_step:
                st.markdown(f"**:blue[{i}. {step_name}]**")
            elif i < st.session_state.form_step:
                st.markdown(f":green[{i}. {step_name}] :white_check_mark:")
            else:
                st.markdown(f":gray[{i}. {step_name}]")

    st.divider()


def render_step1_basic_info() -> dict:
    """Render Step 1: Basic Information form.

    Returns:
        Dictionary of form data
    """
    st.subheader(t("followup.form.step1"))

    data = st.session_state.form_data.get("basic_info", {})

    col1, col2 = st.columns(2)

    with col1:
        patient_name = st.text_input(
            t("patient.list.name"),
            value=data.get("patient_name", ""),
            key="basic_patient_name",
        )
        gender = st.selectbox(
            t("patient.list.gender"),
            options=["male", "female", "other"],
            format_func=lambda x: t(f"patient.gender.{x}"),
            index=["male", "female", "other"].index(data.get("gender", "male")),
            key="basic_gender",
        )
        age = st.number_input(
            t("patient.list.dob") + " (Age)",
            min_value=0,
            max_value=150,
            value=data.get("age", 0),
            key="basic_age",
        )
        height = st.number_input(
            "Height (cm)",
            min_value=0.0,
            max_value=300.0,
            value=float(data.get("height", 0) or 0),
            key="basic_height",
        )
        weight = st.number_input(
            "Weight (kg)",
            min_value=0.0,
            max_value=500.0,
            value=float(data.get("weight", 0) or 0),
            key="basic_weight",
        )

    with col2:
        daily_water_intake = st.number_input(
            "Daily Water Intake (ml)",
            min_value=0,
            max_value=10000,
            value=data.get("daily_water_intake", 0) or 0,
            key="basic_water",
        )
        diet_preference = st.selectbox(
            "Diet Preference",
            options=["", "low_sodium", "low_oxalate", "low_purine", "normal"],
            index=0 if not data.get("diet_preference") else
                ["", "low_sodium", "low_oxalate", "low_purine", "normal"].index(
                    data.get("diet_preference", "")
                ),
            key="basic_diet",
        )
        lifestyle = st.selectbox(
            "Lifestyle",
            options=["", "sedentary", "moderate", "active"],
            index=0 if not data.get("lifestyle") else
                ["", "sedentary", "moderate", "active"].index(
                    data.get("lifestyle", "")
                ),
            key="basic_lifestyle",
        )

    st.divider()
    st.write("**Medical History**")

    col3, col4 = st.columns(2)

    with col3:
        family_history_of_stone = st.checkbox(
            "Family History of Stone",
            value=data.get("family_history_of_stone", False),
            key="basic_family_stone",
        )
        repeated_urinary_infection = st.checkbox(
            "Repeated Urinary Infection",
            value=data.get("repeated_urinary_infection", False),
            key="basic_repeated_infection",
        )
        long_term_catheter = st.checkbox(
            "Long-term Catheter Use",
            value=data.get("long_term_catheter", False),
            key="basic_catheter",
        )

    with col4:
        diabetes = st.checkbox(
            "Diabetes",
            value=data.get("diabetes", False),
            key="basic_diabetes",
        )
        immunodeficiency = st.checkbox(
            "Immunodeficiency",
            value=data.get("immunodeficiency", False),
            key="basic_immunodeficiency",
        )
        neurogenic_bladder = st.checkbox(
            "Neurogenic Bladder",
            value=data.get("neurogenic_bladder", False),
            key="basic_neurogenic",
        )

    medical_history = st.text_area(
        "Medical History Notes",
        value=data.get("medical_history", ""),
        key="basic_medical_history",
    )

    return {
        "patient_name": patient_name,
        "gender": gender,
        "age": age,
        "height": height if height > 0 else None,
        "weight": weight if weight > 0 else None,
        "daily_water_intake": daily_water_intake if daily_water_intake > 0 else None,
        "diet_preference": diet_preference if diet_preference else None,
        "lifestyle": lifestyle if lifestyle else None,
        "family_history_of_stone": family_history_of_stone,
        "repeated_urinary_infection": repeated_urinary_infection,
        "long_term_catheter": long_term_catheter,
        "diabetes": diabetes,
        "immunodeficiency": immunodeficiency,
        "neurogenic_bladder": neurogenic_bladder,
        "medical_history": medical_history if medical_history else None,
    }


def render_step2_surgery_info() -> dict:
    """Render Step 2: Surgery Information form.

    Returns:
        Dictionary of form data
    """
    st.subheader(t("followup.form.step2"))

    data = st.session_state.form_data.get("surgery_indicator", {})

    col1, col2 = st.columns(2)

    with col1:
        clinical_diagnosis = st.text_input(
            "Clinical Diagnosis",
            value=data.get("clinical_diagnosis", ""),
            key="surgery_diagnosis",
        )

        stone_location_options = [
            "left_kidney",
            "right_kidney",
            "left_ureter",
            "right_ureter",
            "bladder",
        ]
        stone_location = st.multiselect(
            "Stone Location",
            options=stone_location_options,
            default=data.get("stone_location", []),
            key="surgery_stone_location",
        )

        stone_size = st.text_input(
            "Stone Size",
            value=data.get("stone_size", ""),
            key="surgery_stone_size",
        )

        hydronephrosis_options = ["none", "mild", "moderate", "severe"]
        hydronephrosis_degree = st.selectbox(
            "Hydronephrosis Degree",
            options=hydronephrosis_options,
            index=hydronephrosis_options.index(
                data.get("hydronephrosis_degree", "none")
            ),
            key="surgery_hydronephrosis",
        )

    with col2:
        surgery_date = st.date_input(
            "Surgery Date",
            value=data.get("surgery_date") or date.today(),
            key="surgery_date",
        )

        surgery_method = st.selectbox(
            "Surgery Method",
            options=["", "PCNL", "RIRS", "URS", "ESWL", "Open"],
            index=0,
            key="surgery_method",
        )

    st.divider()
    st.write("**Pre-operative Lab Values**")

    col3, col4, col5 = st.columns(3)

    with col3:
        alt_before = st.number_input(
            "ALT (U/L)",
            min_value=0.0,
            value=float(data.get("alt_value_before", 0) or 0),
            key="surgery_alt_before",
        )
        ast_before = st.number_input(
            "AST (U/L)",
            min_value=0.0,
            value=float(data.get("ast_value_before", 0) or 0),
            key="surgery_ast_before",
        )

    with col4:
        scr_before = st.number_input(
            "Serum Creatinine (umol/L)",
            min_value=0.0,
            value=float(data.get("scr_value_before", 0) or 0),
            key="surgery_scr_before",
        )
        bun_before = st.number_input(
            "BUN (mmol/L)",
            min_value=0.0,
            value=float(data.get("bun_value_before", 0) or 0),
            key="surgery_bun_before",
        )

    with col5:
        wbc_before = st.number_input(
            "WBC (10^9/L)",
            min_value=0.0,
            value=float(data.get("wbc_value_before", 0) or 0),
            key="surgery_wbc_before",
        )
        hgb_before = st.number_input(
            "Hemoglobin (g/L)",
            min_value=0.0,
            value=float(data.get("hgb_value_before", 0) or 0),
            key="surgery_hgb_before",
        )

    st.divider()
    st.write("**Post-operative Lab Values**")

    col6, col7, col8 = st.columns(3)

    with col6:
        alt_after = st.number_input(
            "ALT (U/L)",
            min_value=0.0,
            value=float(data.get("alt_value_after", 0) or 0),
            key="surgery_alt_after",
        )
        ast_after = st.number_input(
            "AST (U/L)",
            min_value=0.0,
            value=float(data.get("ast_value_after", 0) or 0),
            key="surgery_ast_after",
        )

    with col7:
        scr_after = st.number_input(
            "Serum Creatinine (umol/L)",
            min_value=0.0,
            value=float(data.get("scr_value_after", 0) or 0),
            key="surgery_scr_after",
        )
        bun_after = st.number_input(
            "BUN (mmol/L)",
            min_value=0.0,
            value=float(data.get("bun_value_after", 0) or 0),
            key="surgery_bun_after",
        )

    with col8:
        wbc_after = st.number_input(
            "WBC (10^9/L)",
            min_value=0.0,
            value=float(data.get("wbc_value_after", 0) or 0),
            key="surgery_wbc_after",
        )
        hgb_after = st.number_input(
            "Hemoglobin (g/L)",
            min_value=0.0,
            value=float(data.get("hgb_value_after", 0) or 0),
            key="surgery_hgb_after",
        )

    return {
        "clinical_diagnosis": clinical_diagnosis if clinical_diagnosis else None,
        "stone_location": stone_location if stone_location else None,
        "stone_size": stone_size if stone_size else None,
        "hydronephrosis_degree": hydronephrosis_degree,
        "surgery_date": str(surgery_date),
        "surgery_method": surgery_method if surgery_method else None,
        "alt_value_before": alt_before if alt_before > 0 else None,
        "ast_value_before": ast_before if ast_before > 0 else None,
        "scr_value_before": scr_before if scr_before > 0 else None,
        "bun_value_before": bun_before if bun_before > 0 else None,
        "wbc_value_before": wbc_before if wbc_before > 0 else None,
        "hgb_value_before": hgb_before if hgb_before > 0 else None,
        "alt_value_after": alt_after if alt_after > 0 else None,
        "ast_value_after": ast_after if ast_after > 0 else None,
        "scr_value_after": scr_after if scr_after > 0 else None,
        "bun_value_after": bun_after if bun_after > 0 else None,
        "wbc_value_after": wbc_after if wbc_after > 0 else None,
        "hgb_value_after": hgb_after if hgb_after > 0 else None,
    }


def render_step3_clinical_followup() -> dict:
    """Render Step 3: Clinical Follow-up form.

    Returns:
        Dictionary of form data for all clinical follow-up stages
    """
    st.subheader(t("followup.form.step3"))

    data = st.session_state.form_data.get("clinical_followups", {})

    # Tabs for each stage
    stage_tabs = st.tabs([
        t("followup.clinical.stages.1"),
        t("followup.clinical.stages.2"),
        t("followup.clinical.stages.3"),
        t("followup.clinical.stages.4"),
        t("followup.clinical.stages.5"),
    ])

    result = {}

    for stage_idx, tab in enumerate(stage_tabs, 1):
        with tab:
            stage_data = data.get(str(stage_idx), {})
            stage_key = f"clinical_{stage_idx}"

            col1, col2 = st.columns(2)

            with col1:
                followup_date = st.date_input(
                    t("followup.schedule.due_date"),
                    value=stage_data.get("followup_date") or date.today(),
                    key=f"{stage_key}_date",
                )

                recurrence = st.checkbox(
                    "Recurrence",
                    value=stage_data.get("followup_recurrence", False),
                    key=f"{stage_key}_recurrence",
                )

                imaging_options = ["", "CT", "Ultrasound", "X-ray", "MRI"]
                imaging = st.selectbox(
                    "Imaging Type",
                    options=imaging_options,
                    index=0,
                    key=f"{stage_key}_imaging",
                )

                stone_size = st.text_input(
                    "Stone Size (if any)",
                    value=stage_data.get("followup_stone_size", ""),
                    key=f"{stage_key}_stone_size",
                )

            with col2:
                alt_value = st.number_input(
                    "ALT (U/L)",
                    min_value=0.0,
                    value=float(stage_data.get("followup_alt", 0) or 0),
                    key=f"{stage_key}_alt",
                )
                ast_value = st.number_input(
                    "AST (U/L)",
                    min_value=0.0,
                    value=float(stage_data.get("followup_ast", 0) or 0),
                    key=f"{stage_key}_ast",
                )
                scr_value = st.number_input(
                    "Serum Creatinine (umol/L)",
                    min_value=0.0,
                    value=float(stage_data.get("followup_scr", 0) or 0),
                    key=f"{stage_key}_scr",
                )

            st.divider()
            st.write("**Medication**")

            col3, col4 = st.columns(2)

            with col3:
                medication = st.text_input(
                    "Medication Name",
                    value=stage_data.get("followup_medication", ""),
                    key=f"{stage_key}_medication",
                )
                medication_dose = st.text_input(
                    "Medication Dose",
                    value=stage_data.get("followup_medication_dose", ""),
                    key=f"{stage_key}_dose",
                )

            with col4:
                compliance_options = ["", "good", "partial", "poor"]
                compliance = st.selectbox(
                    "Compliance",
                    options=compliance_options,
                    index=0,
                    key=f"{stage_key}_compliance",
                )

            result[str(stage_idx)] = {
                "stage": stage_idx,
                "followup_date": str(followup_date),
                "followup_recurrence": recurrence,
                "followup_imaging": imaging if imaging else None,
                "followup_stone_size": stone_size if stone_size else None,
                "followup_alt": alt_value if alt_value > 0 else None,
                "followup_ast": ast_value if ast_value > 0 else None,
                "followup_scr": scr_value if scr_value > 0 else None,
                "followup_medication": medication if medication else None,
                "followup_medication_dose": medication_dose if medication_dose else None,
                "followup_compliance": compliance if compliance else None,
            }

    return result


def render_step4_nursing_followup() -> dict:
    """Render Step 4: Nursing Follow-up form.

    Returns:
        Dictionary of form data for all nursing follow-up stages
    """
    st.subheader(t("followup.form.step4"))

    data = st.session_state.form_data.get("nursing_followups", {})

    # Tabs for each stage
    stage_tabs = st.tabs([
        t("followup.nursing.stages.1"),
        t("followup.nursing.stages.2"),
        t("followup.nursing.stages.3"),
        t("followup.nursing.stages.4"),
        t("followup.nursing.stages.5"),
        t("followup.nursing.stages.6"),
    ])

    result = {}

    for stage_idx, tab in enumerate(stage_tabs, 1):
        with tab:
            stage_data = data.get(str(stage_idx), {})
            stage_key = f"nursing_{stage_idx}"

            col1, col2 = st.columns(2)

            with col1:
                followup_date = st.date_input(
                    t("followup.schedule.due_date"),
                    value=stage_data.get("followup_date") or date.today(),
                    key=f"{stage_key}_date",
                )

                nursing_mode_options = ["phone", "video", "home_visit"]
                nursing_mode = st.selectbox(
                    "Follow-up Mode",
                    options=nursing_mode_options,
                    index=0,
                    key=f"{stage_key}_mode",
                )

                discharge_drug = st.text_input(
                    "Discharge Drug",
                    value=stage_data.get("nursing_discharge_drug", ""),
                    key=f"{stage_key}_discharge_drug",
                )

                antibiotic = st.text_input(
                    "Antibiotic",
                    value=stage_data.get("nursing_antibiotic", ""),
                    key=f"{stage_key}_antibiotic",
                )

            with col2:
                urine_ph = st.number_input(
                    "Urine pH",
                    min_value=0.0,
                    max_value=14.0,
                    value=float(stage_data.get("nursing_urine_ph", 0) or 0),
                    key=f"{stage_key}_urine_ph",
                )

                urine_output = st.number_input(
                    "Urine Output (ml/day)",
                    min_value=0,
                    value=stage_data.get("nursing_urine_output", 0) or 0,
                    key=f"{stage_key}_urine_output",
                )

                urine_color_options = ["", "clear", "yellow", "dark", "bloody"]
                urine_color = st.selectbox(
                    "Urine Color",
                    options=urine_color_options,
                    index=0,
                    key=f"{stage_key}_urine_color",
                )

            st.divider()
            st.write("**Mental Health Assessment**")

            col3, col4 = st.columns(2)

            with col3:
                psqi = st.number_input(
                    "PSQI Score",
                    min_value=0,
                    max_value=21,
                    value=stage_data.get("nursing_psqi", 0) or 0,
                    key=f"{stage_key}_psqi",
                )
                depression = st.checkbox(
                    "Depression Symptoms",
                    value=stage_data.get("nursing_depression", False),
                    key=f"{stage_key}_depression",
                )

            with col4:
                support_options = ["", "good", "moderate", "poor"]
                support = st.selectbox(
                    "Social Support Level",
                    options=support_options,
                    index=0,
                    key=f"{stage_key}_support",
                )

            notes = st.text_area(
                "Notes",
                value=stage_data.get("notes", ""),
                key=f"{stage_key}_notes",
            )

            result[str(stage_idx)] = {
                "stage": stage_idx,
                "followup_date": str(followup_date),
                "nursing_mode": nursing_mode,
                "nursing_discharge_drug": discharge_drug if discharge_drug else None,
                "nursing_antibiotic": antibiotic if antibiotic else None,
                "nursing_urine_ph": urine_ph if urine_ph > 0 else None,
                "nursing_urine_output": urine_output if urine_output > 0 else None,
                "nursing_urine_color": urine_color if urine_color else None,
                "nursing_psqi": psqi if psqi > 0 else None,
                "nursing_depression": depression,
                "nursing_support": support if support else None,
                "notes": notes if notes else None,
            }

    return result


def save_form_data(patient_id: str) -> bool:
    """Save all form data to the API.

    Args:
        patient_id: Patient UUID

    Returns:
        True if all saves succeeded, False otherwise
    """
    form_data = st.session_state.form_data
    success = True

    # Save basic info
    if "basic_info" in form_data:
        response = api_request(
            "PUT",
            f"/patients/{patient_id}/basic-info",
            data=form_data["basic_info"],
        )
        if not response or response.status_code not in (200, 201):
            st.error(f"{t('common.error')}: Failed to save basic info")
            success = False

    # Save surgery indicator
    if "surgery_indicator" in form_data:
        response = api_request(
            "PUT",
            f"/patients/{patient_id}/surgery",
            data=form_data["surgery_indicator"],
        )
        if not response or response.status_code not in (200, 201):
            st.error(f"{t('common.error')}: Failed to save surgery info")
            success = False

    # Save clinical follow-ups
    if "clinical_followups" in form_data:
        for stage, stage_data in form_data["clinical_followups"].items():
            response = api_request(
                "PUT",
                f"/patients/{patient_id}/clinical-followups/{stage}",
                data=stage_data,
            )
            if not response or response.status_code not in (200, 201):
                st.error(f"{t('common.error')}: Failed to save clinical follow-up stage {stage}")
                success = False

    # Save nursing follow-ups
    if "nursing_followups" in form_data:
        for stage, stage_data in form_data["nursing_followups"].items():
            response = api_request(
                "PUT",
                f"/patients/{patient_id}/nursing-followups/{stage}",
                data=stage_data,
            )
            if not response or response.status_code not in (200, 201):
                st.error(f"{t('common.error')}: Failed to save nursing follow-up stage {stage}")
                success = False

    return success


def main() -> None:
    """Main page content."""
    st.header(t("followup.title"))

    # Check authentication
    if not st.session_state.user:
        st.warning(t("auth.login.title") + " - Please login to access this page.")
        return

    # Get patient ID from session state
    patient_id = st.session_state.get("selected_patient_id")

    if not patient_id:
        st.warning(t("patient.search.no_results") + " - Please select a patient first.")

        # Back button to patient search
        if st.button(t("common.back"), use_container_width=False):
            st.switch_page("pages/1_patient_search.py")
        return

    # Load patient data for display
    response = api_request("GET", f"/patients/{patient_id}")

    if not response or response.status_code != 200:
        st.error(t("common.error") + ": Could not load patient data.")
        return

    patient = response.json()
    patient_name = f"{patient.get('last_name', '')} {patient.get('first_name', '')}"
    st.write(f"**{t('patient.list.name')}:** {patient_name} | **{t('patient.list.mrn')}:** {patient.get('mrn', '--')}")

    st.divider()

    # Render step indicator
    render_step_indicator()

    # Render current step form
    if st.session_state.form_step == 1:
        step_data = render_step1_basic_info()
        st.session_state.form_data["basic_info"] = step_data

    elif st.session_state.form_step == 2:
        step_data = render_step2_surgery_info()
        st.session_state.form_data["surgery_indicator"] = step_data

    elif st.session_state.form_step == 3:
        step_data = render_step3_clinical_followup()
        st.session_state.form_data["clinical_followups"] = step_data

    elif st.session_state.form_step == 4:
        step_data = render_step4_nursing_followup()
        st.session_state.form_data["nursing_followups"] = step_data

    # Navigation buttons
    st.divider()

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        if st.session_state.form_step > 1:
            if st.button(t("followup.form.previous"), use_container_width=True):
                prev_step()
                st.rerun()

    with col2:
        if st.button(t("followup.form.save_draft"), use_container_width=True):
            st.info("Draft saved to session (not persisted)")

    with col3:
        if st.session_state.form_step < 4:
            if st.button(
                t("followup.form.next"),
                use_container_width=True,
                type="primary",
            ):
                next_step()
                st.rerun()

    with col4:
        if st.session_state.form_step == 4:
            if st.button(
                t("followup.form.submit"),
                use_container_width=True,
                type="primary",
            ):
                with st.spinner(t("common.loading")):
                    if save_form_data(patient_id):
                        st.success(t("common.success"))
                        # Reset form state
                        st.session_state.form_step = 1
                        st.session_state.form_data = {}
                        st.rerun()

    # Back button
    st.divider()
    if st.button(t("common.back"), key="back_button"):
        st.switch_page("pages/1_patient_search.py")


if __name__ == "__main__":
    main()
