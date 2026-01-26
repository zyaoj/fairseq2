"""Follow-up Schedule Dashboard page for Streamlit UI."""

import streamlit as st

# Import from parent app
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app import api_request, init_session_state, render_sidebar, t

# Page configuration
st.set_page_config(
    page_title="Follow-up Schedule",
    page_icon="📅",
    layout="wide",
)

# Initialize session state
init_session_state()

# Render sidebar
render_sidebar()

# Status icons
STATUS_ICONS = {
    "overdue": "🔴",
    "due": "🟡",
    "pending": "🔵",
    "completed": "🟢",
}

# Type icons
TYPE_ICONS = {
    "clinical": "🩺",
    "nursing": "💉",
}


def display_followup_card(followup: dict, show_patient: bool = True) -> None:
    """Display a single follow-up card.

    Args:
        followup: Follow-up data dictionary
        show_patient: Whether to show patient info
    """
    with st.container():
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

        with col1:
            if show_patient:
                patient_name = followup.get("patient_name", "--")
                st.write(f"**{t('followup.schedule.patient')}:** {patient_name}")

            followup_type = followup.get("followup_type", "clinical")
            type_icon = TYPE_ICONS.get(followup_type, "📋")
            type_label = t(f"followup.{followup_type}.title", followup_type)
            st.write(f"{type_icon} {type_label}")

        with col2:
            stage_name = followup.get("stage_name", "")
            st.write(f"**{t('followup.schedule.stage')}:** {stage_name}")

            expected_date = followup.get("expected_date", "--")
            st.write(f"**{t('followup.schedule.due_date')}:** {expected_date}")

        with col3:
            days_until = followup.get("days_until_due", 0)
            status = followup.get("status", "pending")

            if status == "overdue":
                st.error(f"{abs(days_until)} days overdue")
            elif status == "due":
                if days_until == 0:
                    st.warning("Due today")
                else:
                    st.warning(f"Due in {days_until} days")
            elif status == "completed":
                completed_date = followup.get("completed_date", "")
                st.success(f"Completed: {completed_date}")
            else:
                st.info(f"In {days_until} days")

        with col4:
            patient_id = followup.get("patient_id")
            if patient_id and status != "completed":
                if st.button(
                    t("common.view"),
                    key=f"view_{patient_id}_{followup.get('followup_type')}_{followup.get('stage')}",
                    use_container_width=True,
                ):
                    st.session_state.selected_patient_id = patient_id
                    st.switch_page("pages/3_followup_form.py")

        st.divider()


def render_summary_metrics(schedule_data: dict) -> None:
    """Render summary metrics cards.

    Args:
        schedule_data: Schedule response data
    """
    col1, col2, col3 = st.columns(3)

    with col1:
        total_overdue = schedule_data.get("total_overdue", 0)
        st.metric(
            label=f"{STATUS_ICONS['overdue']} {t('followup.schedule.overdue')}",
            value=total_overdue,
            delta=None,
        )

    with col2:
        total_due = schedule_data.get("total_due", 0)
        st.metric(
            label=f"{STATUS_ICONS['due']} {t('followup.schedule.upcoming')}",
            value=total_due,
            delta=None,
        )

    with col3:
        total_upcoming = schedule_data.get("total_upcoming", 0)
        st.metric(
            label=f"{STATUS_ICONS['pending']} Upcoming (30 days)",
            value=total_upcoming,
            delta=None,
        )


def render_overdue_section(followups: list[dict]) -> None:
    """Render overdue follow-ups section.

    Args:
        followups: List of overdue follow-ups
    """
    st.subheader(f"{STATUS_ICONS['overdue']} {t('followup.schedule.overdue')}")

    if not followups:
        st.success("No overdue follow-ups")
        return

    st.warning(f"{len(followups)} follow-ups are overdue and need attention")

    for fu in followups:
        display_followup_card(fu)


def render_due_section(followups: list[dict]) -> None:
    """Render due follow-ups section.

    Args:
        followups: List of due follow-ups
    """
    st.subheader(f"{STATUS_ICONS['due']} {t('followup.schedule.upcoming')}")

    if not followups:
        st.info("No follow-ups due in the next 7 days")
        return

    st.info(f"{len(followups)} follow-ups due in the next 7 days")

    for fu in followups:
        display_followup_card(fu)


def render_upcoming_section(followups: list[dict]) -> None:
    """Render upcoming follow-ups section.

    Args:
        followups: List of upcoming follow-ups
    """
    st.subheader(f"{STATUS_ICONS['pending']} Upcoming (30 days)")

    if not followups:
        st.info("No upcoming follow-ups in the next 30 days")
        return

    for fu in followups:
        display_followup_card(fu)


def render_patient_followup_view(patient_id: str) -> None:
    """Render follow-up schedule for a specific patient.

    Args:
        patient_id: Patient UUID
    """
    # Load patient info
    patient_response = api_request("GET", f"/patients/{patient_id}")
    if patient_response and patient_response.status_code == 200:
        patient = patient_response.json()
        patient_name = f"{patient.get('last_name', '')} {patient.get('first_name', '')}"
        st.subheader(f"Patient: {patient_name}")

    # Load next follow-up info
    response = api_request("GET", f"/patients/{patient_id}/next-followup")

    if not response or response.status_code != 200:
        st.error(t("common.error") + ": Could not load follow-up schedule")
        return

    data = response.json()

    if not data.get("surgery_date"):
        st.warning("No surgery date recorded. Cannot calculate follow-up schedule.")
        return

    st.write(f"**Surgery Date:** {data.get('surgery_date')}")
    st.divider()

    # Show next follow-ups
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**{TYPE_ICONS['clinical']} Next Clinical Follow-up:**")
        next_clinical = data.get("next_clinical")
        if next_clinical:
            display_followup_card(next_clinical, show_patient=False)
        else:
            st.success("All clinical follow-ups completed")

    with col2:
        st.write(f"**{TYPE_ICONS['nursing']} Next Nursing Follow-up:**")
        next_nursing = data.get("next_nursing")
        if next_nursing:
            display_followup_card(next_nursing, show_patient=False)
        else:
            st.success("All nursing follow-ups completed")

    # Show all pending follow-ups
    st.divider()
    st.subheader("All Pending Follow-ups")

    all_followups = data.get("all_followups", [])
    if not all_followups:
        st.success("All follow-ups have been completed")
    else:
        # Group by type
        clinical_followups = [f for f in all_followups if f.get("followup_type") == "clinical"]
        nursing_followups = [f for f in all_followups if f.get("followup_type") == "nursing"]

        tab1, tab2 = st.tabs([
            f"{TYPE_ICONS['clinical']} {t('followup.clinical.title')} ({len(clinical_followups)})",
            f"{TYPE_ICONS['nursing']} {t('followup.nursing.title')} ({len(nursing_followups)})",
        ])

        with tab1:
            for fu in clinical_followups:
                display_followup_card(fu, show_patient=False)

        with tab2:
            for fu in nursing_followups:
                display_followup_card(fu, show_patient=False)


def main() -> None:
    """Main page content."""
    st.header(t("followup.schedule.title"))

    # Check authentication
    if not st.session_state.user:
        st.warning(t("auth.login.title") + " - Please login to access this page.")
        return

    # Check if viewing specific patient
    patient_id = st.session_state.get("selected_patient_id")

    # View mode toggle
    col1, col2 = st.columns([4, 1])

    with col1:
        if patient_id:
            st.info(f"Viewing schedule for selected patient")

    with col2:
        view_mode = st.radio(
            "View",
            options=["all", "patient"],
            format_func=lambda x: "All Patients" if x == "all" else "Selected Patient",
            index=1 if patient_id else 0,
            horizontal=True,
            label_visibility="collapsed",
        )

    st.divider()

    if view_mode == "patient" and patient_id:
        render_patient_followup_view(patient_id)
    else:
        # Load schedule for all patients
        days_ahead = st.slider(
            "Days ahead",
            min_value=7,
            max_value=90,
            value=30,
            step=7,
            help="Number of days ahead to show upcoming follow-ups",
        )

        response = api_request(
            "GET",
            "/followup-schedule",
            params={"days_ahead": days_ahead},
        )

        if not response or response.status_code != 200:
            st.error(t("common.error") + ": Could not load follow-up schedule")
            return

        schedule_data = response.json()

        # Summary metrics
        render_summary_metrics(schedule_data)

        st.divider()

        # Tabs for different statuses
        tab1, tab2, tab3 = st.tabs([
            f"{STATUS_ICONS['overdue']} {t('followup.schedule.overdue')} ({schedule_data.get('total_overdue', 0)})",
            f"{STATUS_ICONS['due']} {t('followup.schedule.upcoming')} ({schedule_data.get('total_due', 0)})",
            f"{STATUS_ICONS['pending']} Upcoming ({schedule_data.get('total_upcoming', 0)})",
        ])

        with tab1:
            render_overdue_section(schedule_data.get("overdue", []))

        with tab2:
            render_due_section(schedule_data.get("due", []))

        with tab3:
            render_upcoming_section(schedule_data.get("upcoming", []))

    # Back button
    st.divider()
    if st.button(t("common.back"), key="back_button"):
        st.switch_page("pages/1_patient_search.py")


if __name__ == "__main__":
    main()
