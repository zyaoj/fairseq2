"""Word Document Management page for Streamlit UI."""

import streamlit as st

# Import from parent app
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app import api_request, init_session_state, render_sidebar, t

# Page configuration
st.set_page_config(
    page_title="Document Management",
    page_icon="📄",
    layout="wide",
)

# Initialize session state
init_session_state()

# Render sidebar
render_sidebar()


def render_generate_section() -> None:
    """Render the document generation section."""
    st.subheader(t("documents.generate.title"))

    # Get patient ID from session or let user select
    patient_id = st.session_state.get("selected_patient_id")

    col1, col2 = st.columns(2)

    with col1:
        if patient_id:
            # Load patient info
            response = api_request("GET", f"/patients/{patient_id}")
            if response and response.status_code == 200:
                patient = response.json()
                patient_name = f"{patient.get('last_name', '')} {patient.get('first_name', '')}"
                st.write(f"**{t('documents.generate.select_patient')}:** {patient_name}")
                st.write(f"**{t('patient.list.mrn')}:** {patient.get('mrn', '--')}")
            else:
                st.warning(t("patient.search.no_results"))
                patient_id = None
        else:
            st.info(t("documents.generate.select_patient") + " - Please select a patient first.")

            if st.button(t("patient.search.title"), key="go_to_search"):
                st.switch_page("pages/1_patient_search.py")

    with col2:
        # Section selection
        section_options = [
            "basic_info",
            "surgery_indicator",
            "clinical_followups",
            "nursing_followups",
        ]
        section_labels = {
            "basic_info": t("followup.form.step1"),
            "surgery_indicator": t("followup.form.step2"),
            "clinical_followups": t("followup.form.step3"),
            "nursing_followups": t("followup.form.step4"),
        }
        selected_sections = st.multiselect(
            t("documents.generate.select_template"),
            options=section_options,
            default=section_options,
            format_func=lambda x: section_labels.get(x, x),
        )

    st.divider()

    if patient_id and selected_sections:
        if st.button(
            t("documents.generate.button"),
            use_container_width=True,
            type="primary",
        ):
            with st.spinner(t("documents.generate.downloading")):
                # Build query params for include_sections
                params = {"include_sections": selected_sections}
                response = api_request(
                    "POST",
                    f"/documents/generate/{patient_id}",
                    params=params,
                )

                if response and response.status_code == 200:
                    st.success(t("documents.generate.success"))

                    # Get filename from Content-Disposition header
                    content_disp = response.headers.get("Content-Disposition", "")
                    filename = "document.docx"
                    if "filename=" in content_disp:
                        filename = content_disp.split("filename=")[-1].strip('"')

                    # Create download button for the generated document
                    st.download_button(
                        label=f"📥 Download {filename}",
                        data=response.content,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                elif response:
                    error_detail = response.json().get("detail", "Unknown error")
                    st.error(f"{t('common.error')}: {error_detail}")
                else:
                    st.error(t("common.error"))


def render_parse_section() -> None:
    """Render the document parsing section."""
    st.subheader(t("documents.parse.title"))

    uploaded_file = st.file_uploader(
        t("documents.parse.upload"),
        type=["docx"],
        accept_multiple_files=False,
    )

    col1, col2 = st.columns(2)

    with col1:
        use_llm = st.checkbox(
            "Use AI extraction (recommended)",
            value=True,
            help="Use Claude AI for more accurate data extraction",
        )

    with col2:
        # Section selection for parsing
        section_options = [
            "basic_info",
            "surgery_indicator",
            "clinical_followups",
            "nursing_followups",
        ]
        section_labels = {
            "basic_info": t("followup.form.step1"),
            "surgery_indicator": t("followup.form.step2"),
            "clinical_followups": t("followup.form.step3"),
            "nursing_followups": t("followup.form.step4"),
        }
        selected_sections = st.multiselect(
            "Sections to extract",
            options=section_options,
            default=section_options,
            format_func=lambda x: section_labels.get(x, x),
            key="parse_sections",
        )

    if uploaded_file is not None:
        if st.button(
            t("documents.parse.button"),
            use_container_width=True,
            type="primary",
        ):
            with st.spinner(t("documents.parse.processing")):
                # Prepare file for upload
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
                params = {
                    "use_llm": use_llm,
                    "sections": selected_sections,
                }

                # Note: api_request doesn't support files directly, so we use a direct request
                import requests
                url = "http://localhost:8000/api/documents/parse"
                headers = {}
                if st.session_state.access_token:
                    headers["Authorization"] = f"Bearer {st.session_state.access_token}"

                try:
                    response = requests.post(
                        url,
                        files=files,
                        params=params,
                        headers=headers,
                        timeout=120,
                    )

                    if response.status_code == 200:
                        st.success(t("documents.parse.success"))
                        result = response.json()

                        # Store in session for preview
                        st.session_state.parsed_data = result.get("extracted_data", {})

                    else:
                        error_detail = response.json().get("detail", "Unknown error")
                        st.error(f"{t('common.error')}: {error_detail}")

                except requests.exceptions.RequestException as e:
                    st.error(f"{t('common.error')}: {str(e)}")

    # Show parsed data preview
    if "parsed_data" in st.session_state and st.session_state.parsed_data:
        st.divider()
        st.subheader(t("documents.parse.preview"))

        parsed_data = st.session_state.parsed_data

        # Create tabs for each entity type
        entity_tabs = []
        entity_data = []

        if "basic_info" in parsed_data:
            entity_tabs.append(t("followup.form.step1"))
            entity_data.append(("basic_info", parsed_data["basic_info"]))

        if "surgery_indicator" in parsed_data:
            entity_tabs.append(t("followup.form.step2"))
            entity_data.append(("surgery_indicator", parsed_data["surgery_indicator"]))

        if "clinical_followups" in parsed_data:
            entity_tabs.append(t("followup.form.step3"))
            entity_data.append(("clinical_followups", parsed_data["clinical_followups"]))

        if "nursing_followups" in parsed_data:
            entity_tabs.append(t("followup.form.step4"))
            entity_data.append(("nursing_followups", parsed_data["nursing_followups"]))

        if entity_tabs:
            tabs = st.tabs(entity_tabs)

            for tab, (entity_type, data) in zip(tabs, entity_data):
                with tab:
                    if isinstance(data, list):
                        # For follow-ups (list of stages)
                        for item in data:
                            with st.expander(f"Stage {item.get('stage', '?')}", expanded=True):
                                st.json(item)
                    else:
                        st.json(data)

            # Option to import data to a patient
            st.divider()
            patient_id = st.session_state.get("selected_patient_id")

            if patient_id:
                if st.button("Import to Selected Patient", use_container_width=True):
                    success = True

                    for entity_type, data in entity_data:
                        if entity_type == "basic_info":
                            response = api_request("PUT", f"/patients/{patient_id}/basic-info", data=data)
                            if not response or response.status_code not in (200, 201):
                                success = False
                                st.error(f"Failed to import {entity_type}")

                        elif entity_type == "surgery_indicator":
                            response = api_request("PUT", f"/patients/{patient_id}/surgery", data=data)
                            if not response or response.status_code not in (200, 201):
                                success = False
                                st.error(f"Failed to import {entity_type}")

                        elif entity_type == "clinical_followups":
                            for stage_data in data:
                                stage = stage_data.get("stage")
                                if stage:
                                    response = api_request(
                                        "PUT",
                                        f"/patients/{patient_id}/clinical-followups/{stage}",
                                        data=stage_data,
                                    )
                                    if not response or response.status_code not in (200, 201):
                                        success = False
                                        st.error(f"Failed to import clinical follow-up stage {stage}")

                        elif entity_type == "nursing_followups":
                            for stage_data in data:
                                stage = stage_data.get("stage")
                                if stage:
                                    response = api_request(
                                        "PUT",
                                        f"/patients/{patient_id}/nursing-followups/{stage}",
                                        data=stage_data,
                                    )
                                    if not response or response.status_code not in (200, 201):
                                        success = False
                                        st.error(f"Failed to import nursing follow-up stage {stage}")

                    if success:
                        st.success("Data imported successfully!")
                        st.session_state.parsed_data = {}
                        st.rerun()
            else:
                st.info("Select a patient to import this data")


def render_templates_section() -> None:
    """Render the templates list section."""
    st.subheader(t("documents.templates.title"))

    # Fetch available templates
    response = api_request("GET", "/documents/templates")

    if response and response.status_code == 200:
        data = response.json()
        templates = data.get("templates", [])
        hospital_id = data.get("hospital_id")

        if hospital_id:
            st.caption(f"Hospital: {hospital_id}")

        if not templates:
            st.info("No templates available")
        else:
            for template in templates:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.write(f"**{template.get('name', 'Unknown')}**")
                        source = template.get("source", "base")
                        if source == "hospital":
                            st.caption(f"🏥 Hospital-specific template")
                        else:
                            st.caption(f"📁 Base template")

                    with col2:
                        st.write(template.get("path", ""))

                    with col3:
                        template_name = template.get("name", "")
                        if st.button(
                            t("documents.templates.download"),
                            key=f"download_{template_name}",
                        ):
                            download_response = api_request(
                                "GET",
                                f"/documents/templates/{template_name}/download",
                            )

                            if download_response and download_response.status_code == 200:
                                st.download_button(
                                    label=f"📥 {template_name}.docx",
                                    data=download_response.content,
                                    file_name=f"{template_name}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    key=f"download_btn_{template_name}",
                                )
                            elif download_response:
                                st.error(f"Failed to download: {download_response.json().get('detail', '')}")

                    st.divider()
    elif response:
        st.error(f"{t('common.error')}: {response.json().get('detail', '')}")
    else:
        st.error(t("common.error") + ": Could not fetch templates")


def main() -> None:
    """Main page content."""
    st.header(t("documents.title"))

    # Check authentication
    if not st.session_state.user:
        st.warning(t("auth.login.title") + " - Please login to access this page.")
        return

    # Create tabs for different operations
    tab1, tab2, tab3 = st.tabs([
        t("documents.generate.title"),
        t("documents.parse.title"),
        t("documents.templates.title"),
    ])

    with tab1:
        render_generate_section()

    with tab2:
        render_parse_section()

    with tab3:
        render_templates_section()

    # Back button
    st.divider()
    if st.button(t("common.back"), key="back_button"):
        st.switch_page("pages/1_patient_search.py")


if __name__ == "__main__":
    main()
