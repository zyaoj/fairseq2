"""Patient Timeline page for Streamlit UI."""

import streamlit as st
import pandas as pd

# Import from parent app
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app import api_request, init_session_state, render_sidebar, t

# Page configuration
st.set_page_config(
    page_title="Patient Timeline",
    page_icon="📅",
    layout="wide",
)

# Initialize session state
init_session_state()

# Render sidebar
render_sidebar()

# Lifecycle phase order for display
PHASE_ORDER = [
    "consultation",
    "pre_surgery",
    "surgery",
    "post_surgery",
    "follow_up",
]

# Event type icons
EVENT_TYPE_ICONS = {
    "lab_result": "🧪",
    "imaging": "📷",
    "procedure": "🏥",
    "note": "📝",
    "followup": "📋",
}


def display_patient_header(patient: dict) -> None:
    """Display patient basic information header.

    Args:
        patient: Patient data dictionary
    """
    st.subheader(t("patient.detail.basic_info"))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.write(f"**{t('patient.list.mrn')}:** {patient.get('mrn', '--')}")

    with col2:
        name = f"{patient.get('last_name', '')} {patient.get('first_name', '')}"
        st.write(f"**{t('patient.list.name')}:** {name}")

    with col3:
        st.write(f"**{t('patient.list.dob')}:** {patient.get('date_of_birth', '--')}")

    with col4:
        gender = patient.get("gender", "")
        gender_display = t(f"patient.gender.{gender}", gender)
        st.write(f"**{t('patient.list.gender')}:** {gender_display}")

    st.divider()


def display_event_card(event: dict) -> None:
    """Display a single clinical event card.

    Args:
        event: Clinical event data dictionary
    """
    event_type = event.get("event_type", "note")
    icon = EVENT_TYPE_ICONS.get(event_type, "📄")
    event_type_label = t(f"timeline.event_types.{event_type}", event_type)

    with st.container():
        col1, col2 = st.columns([1, 4])

        with col1:
            st.write(f"**{event.get('event_date', '--')}**")
            st.caption(f"{icon} {event_type_label}")

        with col2:
            st.write(f"**{event.get('title', '--')}**")
            if event.get("description"):
                st.write(event["description"])

            # Show extraction status for lab results
            if event_type == "lab_result" and event.get("extraction_status"):
                status = event["extraction_status"]
                status_colors = {
                    "pending": "🟡",
                    "processing": "🔵",
                    "completed": "🟢",
                    "failed": "🔴",
                }
                status_icon = status_colors.get(status, "⚪")
                status_label = t(f"lab_result.status.{status}", status)
                st.caption(f"{status_icon} {status_label}")

                # Show extraction confidence if available
                if event.get("extraction_confidence"):
                    confidence = event["extraction_confidence"]
                    st.caption(
                        f"{t('lab_result.extraction_confidence')}: {confidence:.0%}"
                    )

        st.divider()


def display_phase_section(phase: str, events: list[dict]) -> None:
    """Display a phase section with its events.

    Args:
        phase: Lifecycle phase name
        events: List of events in this phase
    """
    phase_label = t(f"timeline.phases.{phase}", phase)

    with st.expander(f"📍 {phase_label} ({len(events)})", expanded=True):
        if not events:
            st.info(t("timeline.no_events"))
        else:
            # Sort events by date (newest first)
            sorted_events = sorted(
                events, key=lambda e: e.get("event_date", ""), reverse=True
            )
            for event in sorted_events:
                display_event_card(event)


def display_timeline(timeline_data: dict) -> None:
    """Display the full patient timeline.

    Args:
        timeline_data: Timeline data with events_by_phase
    """
    st.subheader(t("patient.detail.timeline"))

    events_by_phase = timeline_data.get("events_by_phase", {})

    # Display phases in order
    for phase in PHASE_ORDER:
        events = events_by_phase.get(phase, [])
        display_phase_section(phase, events)


def display_summary_section(patient_id: str) -> None:
    """Display the AI summary section.

    Args:
        patient_id: Patient UUID
    """
    st.subheader(t("patient.detail.summary"))

    # Check if we have a cached summary
    summary_key = f"summary_{patient_id}"

    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button(
            t("patient.detail.generate_summary"),
            use_container_width=True,
            type="primary",
        ):
            with st.spinner(t("common.loading")):
                response = api_request("GET", f"/patients/{patient_id}/summary")

                if response and response.status_code == 200:
                    st.session_state[summary_key] = response.json()
                elif response:
                    st.error(
                        f"{t('common.error')}: {response.json().get('detail', '')}"
                    )

    # Display summary if available
    if summary_key in st.session_state:
        summary_data = st.session_state[summary_key]
        if isinstance(summary_data, dict):
            st.markdown(summary_data.get("summary", ""))
        else:
            st.markdown(str(summary_data))
    else:
        st.info(t("common.no_data"))


def display_lab_trends(patient_id: str) -> None:
    """Display lab value trends from clinical follow-ups.

    Args:
        patient_id: Patient UUID
    """
    st.subheader(t("timeline.lab_trends.title"))

    # Load clinical follow-ups
    response = api_request("GET", f"/patients/{patient_id}/clinical-followups")

    if not response or response.status_code != 200:
        st.info(t("timeline.lab_trends.no_data"))
        return

    data = response.json()
    followups = data.get("followups", [])

    if not followups:
        st.info(t("timeline.lab_trends.no_data"))
        return

    # Stage labels (from i18n)
    stage_labels = {
        1: t("followup.clinical.stages.1"),
        2: t("followup.clinical.stages.2"),
        3: t("followup.clinical.stages.3"),
        4: t("followup.clinical.stages.4"),
        5: t("followup.clinical.stages.5"),
    }

    # Prepare data for charts
    chart_data = []
    for fu in followups:
        stage = fu.get("stage", 0)
        chart_data.append({
            "stage": stage,
            "stage_label": stage_labels.get(stage, f"Stage {stage}"),
            "alt": fu.get("followup_alt"),
            "ast": fu.get("followup_ast"),
            "ggt": fu.get("followup_ggt"),
            "scr": fu.get("followup_scr"),
            "wbc": fu.get("followup_wbc"),
            "hb": fu.get("followup_hb"),
            "urine_ph": fu.get("followup_urine_ph"),
        })

    # Sort by stage
    chart_data.sort(key=lambda x: x["stage"])
    df = pd.DataFrame(chart_data)

    # Check if we have any lab values
    lab_columns = ["alt", "ast", "ggt", "scr", "wbc", "hb", "urine_ph"]
    has_any_data = any(df[col].notna().any() for col in lab_columns if col in df.columns)

    if not has_any_data:
        st.info(t("timeline.lab_trends.no_data"))
        return

    # Create tabs for different lab categories
    tab1, tab2, tab3, tab4 = st.tabs([
        t("timeline.lab_trends.liver_function"),
        t("timeline.lab_trends.kidney_function"),
        t("timeline.lab_trends.blood_count"),
        t("timeline.lab_trends.urinalysis"),
    ])

    with tab1:
        # Liver function: ALT, AST, GGT
        liver_cols = ["alt", "ast", "ggt"]
        liver_labels = {
            "alt": t("timeline.lab_trends.alt"),
            "ast": t("timeline.lab_trends.ast"),
            "ggt": t("timeline.lab_trends.ggt"),
        }
        _display_trend_chart(df, liver_cols, liver_labels, stage_labels)

    with tab2:
        # Kidney function: Creatinine
        kidney_cols = ["scr"]
        kidney_labels = {
            "scr": t("timeline.lab_trends.scr"),
        }
        _display_trend_chart(df, kidney_cols, kidney_labels, stage_labels)

    with tab3:
        # Blood count: WBC, Hemoglobin
        blood_cols = ["wbc", "hb"]
        blood_labels = {
            "wbc": t("timeline.lab_trends.wbc"),
            "hb": t("timeline.lab_trends.hb"),
        }
        _display_trend_chart(df, blood_cols, blood_labels, stage_labels)

    with tab4:
        # Urinalysis: pH
        urine_cols = ["urine_ph"]
        urine_labels = {
            "urine_ph": t("timeline.lab_trends.urine_ph"),
        }
        _display_trend_chart(df, urine_cols, urine_labels, stage_labels)


def _display_trend_chart(
    df: pd.DataFrame,
    columns: list[str],
    labels: dict[str, str],
    stage_labels: dict[int, str],
) -> None:
    """Display a trend chart for specified columns.

    Args:
        df: DataFrame with lab values
        columns: List of column names to plot
        labels: Dict mapping column names to display labels
        stage_labels: Dict mapping stage numbers to labels
    """
    # Filter to columns that have data
    valid_cols = [c for c in columns if c in df.columns and df[c].notna().any()]

    if not valid_cols:
        st.info(t("timeline.lab_trends.no_data"))
        return

    # Create chart data with stage labels as index
    chart_df = df[["stage"] + valid_cols].copy()
    chart_df["stage_label"] = chart_df["stage"].map(stage_labels)
    chart_df = chart_df.set_index("stage_label")[valid_cols]

    # Rename columns to use display labels
    chart_df.columns = [labels.get(c, c) for c in chart_df.columns]

    # Display line chart
    st.line_chart(chart_df)

    # Also show data table
    with st.expander(t("common.view") + " " + t("common.no_data").replace(t("common.no_data"), "data")):
        st.dataframe(chart_df, use_container_width=True)


def main() -> None:
    """Main page content."""
    st.header(t("timeline.title"))

    # Check authentication
    if not st.session_state.user:
        st.warning(t("auth.login.title") + " - Please login to access this page.")
        return

    # Get patient ID from session state or query params
    patient_id = st.session_state.get("selected_patient_id")

    if not patient_id:
        st.warning(t("patient.search.no_results") + " - Please select a patient first.")

        # Back button to patient search
        if st.button(t("common.back"), use_container_width=False):
            st.switch_page("pages/1_patient_search.py")
        return

    # Load patient data
    response = api_request("GET", f"/patients/{patient_id}")

    if not response or response.status_code != 200:
        st.error(t("common.error") + ": Could not load patient data.")
        return

    patient = response.json()

    # Display patient header
    display_patient_header(patient)

    # Create tabs for timeline, lab trends, and summary
    tab1, tab2, tab3 = st.tabs([
        t("patient.detail.timeline"),
        t("timeline.lab_trends.title"),
        t("patient.detail.summary"),
    ])

    with tab1:
        # Load timeline data
        timeline_response = api_request("GET", f"/patients/{patient_id}/timeline")

        if timeline_response and timeline_response.status_code == 200:
            timeline_data = timeline_response.json()
            display_timeline(timeline_data)
        else:
            st.info(t("timeline.no_events"))

    with tab2:
        display_lab_trends(patient_id)

    with tab3:
        display_summary_section(patient_id)

    # Back button
    st.divider()
    if st.button(t("common.back"), key="back_button"):
        st.switch_page("pages/1_patient_search.py")


if __name__ == "__main__":
    main()
