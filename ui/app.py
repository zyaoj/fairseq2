"""Main Streamlit application entry point."""

import json
from pathlib import Path
from typing import Any

import requests
import streamlit as st

# Configuration
API_BASE_URL = "http://localhost:8000/api"
DEFAULT_LOCALE = "zh-CN"
SUPPORTED_LOCALES = ["zh-CN", "en"]

# Path to UI translations
I18N_DIR = Path(__file__).parent / "i18n"


def load_translations(locale: str) -> dict[str, Any]:
    """Load translations for the given locale.

    Args:
        locale: Locale code (e.g., "zh-CN", "en")

    Returns:
        Dictionary of translations
    """
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE

    locale_file = I18N_DIR / f"{locale}.json"
    if not locale_file.exists():
        return {}

    with open(locale_file, encoding="utf-8") as f:
        return json.load(f)


def t(key: str, default: str | None = None) -> str:
    """Get translation for a key.

    Uses dot notation to access nested keys (e.g., "patient.search.title").

    Args:
        key: Dot-notation translation key
        default: Default value if key not found

    Returns:
        Translated string
    """
    translations = st.session_state.get("translations", {})

    keys = key.split(".")
    value: Any = translations
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default if default is not None else key

    if isinstance(value, str):
        return value
    return default if default is not None else key


def init_session_state() -> None:
    """Initialize session state with default values."""
    if "locale" not in st.session_state:
        st.session_state.locale = DEFAULT_LOCALE

    if "translations" not in st.session_state:
        st.session_state.translations = load_translations(st.session_state.locale)

    if "access_token" not in st.session_state:
        st.session_state.access_token = None

    if "user" not in st.session_state:
        st.session_state.user = None


def change_locale(new_locale: str) -> None:
    """Change the current locale and reload translations.

    Args:
        new_locale: New locale code
    """
    if new_locale in SUPPORTED_LOCALES:
        st.session_state.locale = new_locale
        st.session_state.translations = load_translations(new_locale)


def api_request(
    method: str,
    endpoint: str,
    data: dict | None = None,
    params: dict | None = None,
    files: dict | None = None,
) -> requests.Response | None:
    """Make an API request to the backend.

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE)
        endpoint: API endpoint (e.g., "/patients")
        data: JSON body data
        params: Query parameters
        files: Files for multipart upload

    Returns:
        Response object or None if request failed
    """
    url = f"{API_BASE_URL}{endpoint}"
    headers = {}

    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            if files:
                response = requests.post(
                    url, headers=headers, data=data, files=files, timeout=60
                )
            else:
                response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return None

        return response

    except requests.exceptions.ConnectionError:
        st.error(t("common.error") + ": " + "Cannot connect to API server")
        return None
    except requests.exceptions.Timeout:
        st.error(t("common.error") + ": " + "Request timed out")
        return None


def login(username: str, password: str) -> bool:
    """Authenticate user with the backend.

    Args:
        username: Username
        password: Password

    Returns:
        True if login successful, False otherwise
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=30,
        )

        if response.status_code == 200:
            token_data = response.json()
            st.session_state.access_token = token_data["access_token"]

            # Fetch user info
            user_response = api_request("GET", "/auth/me")
            if user_response and user_response.status_code == 200:
                st.session_state.user = user_response.json()

            return True
        else:
            return False

    except requests.exceptions.RequestException:
        return False


def logout() -> None:
    """Log out the current user."""
    st.session_state.access_token = None
    st.session_state.user = None


def render_sidebar() -> None:
    """Render the sidebar with language switcher and auth controls."""
    with st.sidebar:
        # App title
        st.title(t("app.title"))
        st.caption(t("app.subtitle"))

        st.divider()

        # Language switcher
        st.subheader(t("sidebar.language"))
        locale_options = {"zh-CN": "中文", "en": "English"}
        current_locale = st.session_state.locale

        selected_locale = st.selectbox(
            t("settings.language.select"),
            options=list(locale_options.keys()),
            format_func=lambda x: locale_options[x],
            index=list(locale_options.keys()).index(current_locale),
            key="locale_selector",
        )

        if selected_locale != current_locale:
            change_locale(selected_locale)
            st.rerun()

        st.divider()

        # Authentication section
        if st.session_state.user:
            # Logged in state
            st.subheader(t("sidebar.user"))
            st.write(f"👤 {st.session_state.user.get('username', 'Unknown')}")

            if st.session_state.user.get("hospital_id"):
                st.write(f"🏥 {st.session_state.user.get('hospital_id')}")

            if st.button(t("sidebar.logout"), use_container_width=True):
                logout()
                st.rerun()
        else:
            # Login form
            st.subheader(t("sidebar.login"))

            with st.form("login_form"):
                username = st.text_input(t("auth.login.username"))
                password = st.text_input(t("auth.login.password"), type="password")
                submit = st.form_submit_button(
                    t("auth.login.button"), use_container_width=True
                )

                if submit:
                    if login(username, password):
                        st.success(t("common.success"))
                        st.rerun()
                    else:
                        st.error(t("auth.login.error"))


def main() -> None:
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="Urology Data Platform",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state
    init_session_state()

    # Render sidebar
    render_sidebar()

    # Main content
    st.header(t("nav.home"))

    if st.session_state.user:
        # Show dashboard content for logged-in users
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(label=t("nav.patient_search"), value="--")

        with col2:
            st.metric(label=t("followup.schedule.upcoming"), value="--")

        with col3:
            st.metric(label=t("followup.schedule.overdue"), value="--")

        st.divider()

        st.info(
            "👈 " + t("common.no_data") + " - Use the sidebar to navigate to different pages."
        )
    else:
        # Show login prompt for unauthenticated users
        st.warning("👈 " + t("auth.login.title") + " - Please login using the sidebar.")


if __name__ == "__main__":
    main()
