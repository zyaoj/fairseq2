"""Settings page for Streamlit UI."""

import streamlit as st

# Import from parent app
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app import api_request, init_session_state, render_sidebar, t

# Page configuration
st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide",
)

# Initialize session state
init_session_state()

# Render sidebar
render_sidebar()


def render_language_section() -> None:
    """Render language settings section."""
    st.subheader(t("settings.language.title"))

    st.info(t("settings.language.description"))

    # Note: Language switching is handled in the sidebar
    # This section provides additional context
    col1, col2 = st.columns(2)

    with col1:
        current_locale = st.session_state.locale
        locale_display = {"zh-CN": "中文", "en": "English"}
        st.write(f"**{t('settings.language.current')}:** {locale_display.get(current_locale, current_locale)}")

    with col2:
        st.write(f"**{t('settings.language.supported')}:** 中文, English")


def render_terminology_section() -> None:
    """Render terminology override section."""
    st.subheader(t("settings.terminology.title"))

    st.info(t("settings.terminology.description"))

    # Load user's overrides
    response = api_request("GET", "/terminology/my-overrides")

    if response and response.status_code == 200:
        overrides = response.json()

        if overrides:
            st.write(f"**{t('settings.terminology.custom_terms')}:** {len(overrides)}")

            # Display existing overrides in a table-like format
            for override in overrides:
                with st.container():
                    col1, col2, col3 = st.columns([2, 3, 1])

                    with col1:
                        st.write(f"**{override.get('term_key', '')}**")
                        st.caption(f"Locale: {override.get('locale', '')}")

                    with col2:
                        st.write(override.get("display_value", ""))

                    with col3:
                        override_id = override.get("id")
                        if st.button(
                            t("common.delete"),
                            key=f"delete_{override_id}",
                            type="secondary",
                        ):
                            delete_response = api_request(
                                "DELETE",
                                f"/terminology/{override_id}",
                            )
                            if delete_response and delete_response.status_code == 204:
                                st.success(t("common.success"))
                                st.rerun()
                            elif delete_response:
                                st.error(f"{t('common.error')}: {delete_response.json().get('detail', '')}")

                    st.divider()
        else:
            st.info(t("settings.terminology.no_overrides"))

    elif response:
        st.error(f"{t('common.error')}: {response.json().get('detail', '')}")

    # Add new override form
    st.divider()
    st.write(f"**{t('settings.terminology.add_override')}**")

    with st.form("add_terminology_form"):
        col1, col2 = st.columns(2)

        with col1:
            term_key = st.text_input(
                t("settings.terminology.term_key"),
                placeholder="e.g., stone_location.left_kidney",
                help="The key for the terminology you want to customize",
            )

        with col2:
            display_value = st.text_input(
                t("settings.terminology.display_value"),
                placeholder="e.g., 左侧肾脏",
                help="Your custom display text for this term",
            )

        submitted = st.form_submit_button(t("common.save"), use_container_width=True)

        if submitted:
            if not term_key or not display_value:
                st.error(t("common.error") + ": Missing required fields")
            else:
                response = api_request(
                    "POST",
                    "/terminology",
                    data={
                        "term_key": term_key,
                        "display_value": display_value,
                        "locale": st.session_state.locale,
                        "scope_type": "user",
                    },
                )

                if response and response.status_code in (200, 201):
                    st.success(t("common.success"))
                    st.rerun()
                elif response:
                    st.error(f"{t('common.error')}: {response.json().get('detail', '')}")


def render_feedback_section() -> None:
    """Render translation feedback section."""
    st.subheader(t("settings.feedback.title"))

    st.info(t("settings.feedback.description"))

    # Feedback submission form
    with st.form("feedback_form"):
        col1, col2 = st.columns(2)

        with col1:
            translation_key = st.text_input(
                t("settings.feedback.translation_key"),
                placeholder="e.g., patient.timeline.title",
                help="The key for the translation you want to suggest an improvement for",
            )

        with col2:
            original_value = st.text_input(
                t("settings.feedback.original_value"),
                placeholder="e.g., 患者时间线",
                help="The current translation value",
            )

        suggested_value = st.text_area(
            t("settings.feedback.suggested_value"),
            placeholder="e.g., 患者病历时间线",
            help="Your suggested improvement",
        )

        submitted = st.form_submit_button(t("settings.feedback.submit"), use_container_width=True)

        if submitted:
            if not translation_key or not suggested_value:
                st.error(t("common.error") + ": Missing required fields")
            else:
                response = api_request(
                    "POST",
                    "/i18n/feedback",
                    data={
                        "translation_key": translation_key,
                        "locale": st.session_state.locale,
                        "original_value": original_value or "",
                        "suggested_value": suggested_value,
                    },
                )

                if response and response.status_code == 201:
                    st.success(t("settings.feedback.success"))
                elif response:
                    st.error(f"{t('common.error')}: {response.json().get('detail', '')}")


def render_hospital_overrides_section() -> None:
    """Render hospital-level terminology overrides section (admin only)."""
    user = st.session_state.get("user", {})

    # Check if user is admin
    if user.get("role") != "admin":
        return

    st.divider()
    st.subheader(t("settings.hospital.title"))

    st.info(t("settings.hospital.description"))

    # Load hospital overrides
    response = api_request("GET", "/terminology/hospital-overrides")

    if response and response.status_code == 200:
        overrides = response.json()

        if overrides:
            st.write(f"**Hospital overrides:** {len(overrides)}")

            for override in overrides:
                with st.container():
                    col1, col2, col3 = st.columns([2, 3, 1])

                    with col1:
                        st.write(f"**{override.get('term_key', '')}**")
                        st.caption(f"Locale: {override.get('locale', '')}")

                    with col2:
                        st.write(override.get("display_value", ""))

                    with col3:
                        override_id = override.get("id")
                        if st.button(
                            t("common.delete"),
                            key=f"delete_hospital_{override_id}",
                            type="secondary",
                        ):
                            delete_response = api_request(
                                "DELETE",
                                f"/terminology/{override_id}",
                            )
                            if delete_response and delete_response.status_code == 204:
                                st.success(t("common.success"))
                                st.rerun()

                    st.divider()
        else:
            st.info("No hospital-level overrides configured")

    # Add hospital override form
    st.write("**Add Hospital Override**")

    with st.form("add_hospital_terminology_form"):
        col1, col2 = st.columns(2)

        with col1:
            term_key = st.text_input(
                t("settings.terminology.term_key"),
                placeholder="e.g., stone_location.left_kidney",
                key="hospital_term_key",
            )

        with col2:
            display_value = st.text_input(
                t("settings.terminology.display_value"),
                placeholder="e.g., 左侧肾脏",
                key="hospital_display_value",
            )

        submitted = st.form_submit_button(t("common.save"), use_container_width=True)

        if submitted:
            if not term_key or not display_value:
                st.error(t("common.error") + ": Missing required fields")
            else:
                response = api_request(
                    "POST",
                    "/terminology",
                    data={
                        "term_key": term_key,
                        "display_value": display_value,
                        "locale": st.session_state.locale,
                        "scope_type": "hospital",
                    },
                )

                if response and response.status_code in (200, 201):
                    st.success(t("common.success"))
                    st.rerun()
                elif response:
                    st.error(f"{t('common.error')}: {response.json().get('detail', '')}")


def main() -> None:
    """Main page content."""
    st.header(t("settings.title"))

    # Check authentication
    if not st.session_state.user:
        st.warning(t("auth.login.title") + " - Please login to access this page.")
        return

    # Create tabs for different settings sections
    tab1, tab2, tab3 = st.tabs([
        t("settings.language.title"),
        t("settings.terminology.title"),
        t("settings.feedback.title"),
    ])

    with tab1:
        render_language_section()

    with tab2:
        render_terminology_section()
        render_hospital_overrides_section()

    with tab3:
        render_feedback_section()

    # Back button
    st.divider()
    if st.button(t("common.back"), key="back_button"):
        st.switch_page("pages/1_patient_search.py")


if __name__ == "__main__":
    main()
