"""Patient Search page for Streamlit UI."""

import streamlit as st

# Import from parent app
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app import api_request, init_session_state, render_sidebar, t

# Page configuration
st.set_page_config(
    page_title="Patient Search",
    page_icon="🔍",
    layout="wide",
)

# Initialize session state
init_session_state()

# Render sidebar
render_sidebar()


def display_patient_card(patient: dict) -> None:
    """Display a patient card with basic info.

    Args:
        patient: Patient data dictionary
    """
    with st.container():
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

        with col1:
            st.write(f"**{t('patient.list.mrn')}:** {patient.get('mrn', '--')}")
            st.write(
                f"**{t('patient.list.name')}:** "
                f"{patient.get('last_name', '')} {patient.get('first_name', '')}"
            )

        with col2:
            st.write(f"**{t('patient.list.dob')}:** {patient.get('date_of_birth', '--')}")

            gender = patient.get("gender", "")
            gender_display = t(f"patient.gender.{gender}", gender)
            st.write(f"**{t('patient.list.gender')}:** {gender_display}")

        with col3:
            if st.button(
                t("common.view"),
                key=f"view_{patient['id']}",
                use_container_width=True,
            ):
                st.session_state.selected_patient_id = patient["id"]
                st.switch_page("pages/2_patient_timeline.py")

        with col4:
            if st.button(
                t("common.edit"),
                key=f"edit_{patient['id']}",
                use_container_width=True,
            ):
                st.session_state.edit_patient_id = patient["id"]
                st.rerun()

        st.divider()


def render_patient_list(patients: list[dict]) -> None:
    """Render the list of patients.

    Args:
        patients: List of patient data dictionaries
    """
    if not patients:
        st.info(t("patient.search.no_results"))
        return

    st.write(f"**{t('patient.search.results')}:** {len(patients)}")
    st.divider()

    for patient in patients:
        display_patient_card(patient)


def render_create_patient_form() -> None:
    """Render the create patient form."""
    st.subheader(t("patient.create.title"))

    with st.form("create_patient_form"):
        col1, col2 = st.columns(2)

        with col1:
            mrn = st.text_input(t("patient.list.mrn"), key="new_mrn")
            first_name = st.text_input(t("patient.list.name") + " (First)", key="new_first_name")
            last_name = st.text_input(t("patient.list.name") + " (Last)", key="new_last_name")

        with col2:
            dob = st.date_input(t("patient.list.dob"), key="new_dob")
            gender = st.selectbox(
                t("patient.list.gender"),
                options=["male", "female", "other"],
                format_func=lambda x: t(f"patient.gender.{x}"),
                key="new_gender",
            )
            hospital_id = st.text_input(t("sidebar.hospital"), key="new_hospital_id")

        submitted = st.form_submit_button(t("common.save"), use_container_width=True)

        if submitted:
            if not mrn or not first_name or not last_name:
                st.error(t("common.error") + ": Missing required fields")
            else:
                response = api_request(
                    "POST",
                    "/patients/",
                    data={
                        "mrn": mrn,
                        "first_name": first_name,
                        "last_name": last_name,
                        "date_of_birth": str(dob),
                        "gender": gender,
                        "hospital_id": hospital_id or None,
                    },
                )

                if response and response.status_code == 201:
                    st.success(t("patient.create.success"))
                    st.session_state.show_create_form = False
                    st.rerun()
                elif response:
                    st.error(f"{t('patient.create.error')}: {response.json().get('detail', '')}")


def main() -> None:
    """Main page content."""
    st.header(t("patient.search.title"))

    # Check authentication
    if not st.session_state.user:
        st.warning(t("auth.login.title") + " - Please login to access this page.")
        return

    # Search section
    col1, col2, col3 = st.columns([4, 1, 1])

    with col1:
        search_query = st.text_input(
            t("patient.search.placeholder"),
            key="search_query",
            label_visibility="collapsed",
            placeholder=t("patient.search.placeholder"),
        )

    with col2:
        search_button = st.button(
            t("patient.search.button"),
            use_container_width=True,
            type="primary",
        )

    with col3:
        if st.button(t("patient.create.title"), use_container_width=True):
            st.session_state.show_create_form = not st.session_state.get(
                "show_create_form", False
            )
            st.rerun()

    # Create patient form (toggleable)
    if st.session_state.get("show_create_form", False):
        with st.expander(t("patient.create.title"), expanded=True):
            render_create_patient_form()

    st.divider()

    # Load and display patients
    if search_button or search_query or "patients_loaded" not in st.session_state:
        params = {}
        if search_query:
            params["search"] = search_query
        params["limit"] = 50

        response = api_request("GET", "/patients/", params=params)

        if response and response.status_code == 200:
            st.session_state.patients = response.json()
            st.session_state.patients_loaded = True
        elif response:
            st.error(f"{t('common.error')}: {response.json().get('detail', '')}")
            st.session_state.patients = []
        else:
            st.session_state.patients = []

    # Display patient list
    patients = st.session_state.get("patients", [])
    render_patient_list(patients)


if __name__ == "__main__":
    main()
