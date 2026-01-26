"""Tests for i18n API endpoints."""


class TestGetTranslations:
    """Tests for getting translations."""

    def test_get_translations_chinese(self, client) -> None:
        """Test getting Chinese translations (public endpoint)."""
        response = client.get("/api/i18n/zh-CN")
        assert response.status_code == 200
        data = response.json()
        assert data["locale"] == "zh-CN"
        assert "translations" in data
        assert "patient" in data["translations"]
        assert "lab_result" in data["translations"]

    def test_get_translations_english(self, client) -> None:
        """Test getting English translations."""
        response = client.get("/api/i18n/en")
        assert response.status_code == 200
        data = response.json()
        assert data["locale"] == "en"
        assert "translations" in data
        assert "patient" in data["translations"]

    def test_get_translations_unsupported_locale(self, client) -> None:
        """Test getting translations for unsupported locale fails."""
        response = client.get("/api/i18n/fr-FR")
        assert response.status_code == 400
        assert "Unsupported locale" in response.json()["detail"]


class TestSubmitTranslationFeedback:
    """Tests for submitting translation feedback."""

    def test_submit_feedback(self, client, auth_headers: dict[str, str]) -> None:
        """Test submitting translation feedback successfully."""
        response = client.post(
            "/api/i18n/feedback",
            json={
                "translation_key": "patient.timeline.title",
                "locale": "zh-CN",
                "original_value": "患者时间线",
                "suggested_value": "病人时间轴",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["translation_key"] == "patient.timeline.title"
        assert data["locale"] == "zh-CN"
        assert data["suggested_value"] == "病人时间轴"
        assert data["status"] == "pending"
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data

    def test_submit_feedback_unsupported_locale(
        self, client, auth_headers: dict[str, str]
    ) -> None:
        """Test submitting feedback with unsupported locale fails."""
        response = client.post(
            "/api/i18n/feedback",
            json={
                "translation_key": "patient.timeline.title",
                "locale": "fr-FR",
                "original_value": "Patient Timeline",
                "suggested_value": "Chronologie du patient",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Unsupported locale" in response.json()["detail"]

    def test_submit_feedback_unauthenticated(self, client) -> None:
        """Test submitting feedback without authentication fails."""
        response = client.post(
            "/api/i18n/feedback",
            json={
                "translation_key": "patient.timeline.title",
                "locale": "zh-CN",
                "original_value": "患者时间线",
                "suggested_value": "病人时间轴",
            },
        )
        assert response.status_code == 401


class TestListTranslationFeedback:
    """Tests for listing translation feedback."""

    def test_list_feedback_as_admin(
        self, client, admin_auth_headers: dict[str, str]
    ) -> None:
        """Test listing feedback as admin."""
        response = client.get("/api/i18n/feedback", headers=admin_auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_feedback_as_non_admin(
        self, client, auth_headers: dict[str, str]
    ) -> None:
        """Test listing feedback as non-admin fails."""
        response = client.get("/api/i18n/feedback", headers=auth_headers)
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    def test_list_feedback_with_filters(
        self, client, auth_headers: dict[str, str], admin_auth_headers: dict[str, str]
    ) -> None:
        """Test listing feedback with status and locale filters."""
        # Submit some feedback
        client.post(
            "/api/i18n/feedback",
            json={
                "translation_key": "patient.timeline.title",
                "locale": "zh-CN",
                "original_value": "患者时间线",
                "suggested_value": "病人时间轴",
            },
            headers=auth_headers,
        )
        client.post(
            "/api/i18n/feedback",
            json={
                "translation_key": "patient.fields.name",
                "locale": "en",
                "original_value": "Name",
                "suggested_value": "Patient Name",
            },
            headers=auth_headers,
        )

        # List all feedback
        response = client.get("/api/i18n/feedback", headers=admin_auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Filter by locale
        response = client.get(
            "/api/i18n/feedback?locale=zh-CN", headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["locale"] == "zh-CN"

        # Filter by status
        response = client.get(
            "/api/i18n/feedback?status_filter=pending", headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "pending" for item in data)

    def test_list_feedback_pagination(
        self, client, auth_headers: dict[str, str], admin_auth_headers: dict[str, str]
    ) -> None:
        """Test listing feedback with pagination."""
        # Submit 5 feedback entries
        for i in range(5):
            client.post(
                "/api/i18n/feedback",
                json={
                    "translation_key": f"test.key.{i}",
                    "locale": "zh-CN",
                    "original_value": f"Original {i}",
                    "suggested_value": f"Suggested {i}",
                },
                headers=auth_headers,
            )

        # Get first 2
        response = client.get("/api/i18n/feedback?limit=2", headers=admin_auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Skip first 2, get next 2
        response = client.get(
            "/api/i18n/feedback?skip=2&limit=2", headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_feedback_unauthenticated(self, client) -> None:
        """Test listing feedback without authentication fails."""
        response = client.get("/api/i18n/feedback")
        assert response.status_code == 401


class TestUpdateTranslationFeedback:
    """Tests for updating translation feedback status."""

    def test_update_feedback_approve(
        self, client, auth_headers: dict[str, str], admin_auth_headers: dict[str, str]
    ) -> None:
        """Test approving translation feedback as admin."""
        # Submit feedback
        create_response = client.post(
            "/api/i18n/feedback",
            json={
                "translation_key": "patient.timeline.title",
                "locale": "zh-CN",
                "original_value": "患者时间线",
                "suggested_value": "病人时间轴",
            },
            headers=auth_headers,
        )
        feedback_id = create_response.json()["id"]

        # Approve feedback
        response = client.patch(
            f"/api/i18n/feedback/{feedback_id}",
            json={"status": "approved"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["reviewed_by"] is not None
        assert data["reviewed_at"] is not None

    def test_update_feedback_reject(
        self, client, auth_headers: dict[str, str], admin_auth_headers: dict[str, str]
    ) -> None:
        """Test rejecting translation feedback as admin."""
        # Submit feedback
        create_response = client.post(
            "/api/i18n/feedback",
            json={
                "translation_key": "patient.timeline.title",
                "locale": "zh-CN",
                "original_value": "患者时间线",
                "suggested_value": "病人时间轴",
            },
            headers=auth_headers,
        )
        feedback_id = create_response.json()["id"]

        # Reject feedback
        response = client.patch(
            f"/api/i18n/feedback/{feedback_id}",
            json={"status": "rejected"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_update_feedback_as_non_admin(
        self, client, auth_headers: dict[str, str]
    ) -> None:
        """Test updating feedback as non-admin fails."""
        # Submit feedback
        create_response = client.post(
            "/api/i18n/feedback",
            json={
                "translation_key": "patient.timeline.title",
                "locale": "zh-CN",
                "original_value": "患者时间线",
                "suggested_value": "病人时间轴",
            },
            headers=auth_headers,
        )
        feedback_id = create_response.json()["id"]

        # Try to update as non-admin
        response = client.patch(
            f"/api/i18n/feedback/{feedback_id}",
            json={"status": "approved"},
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    def test_update_feedback_not_found(
        self, client, admin_auth_headers: dict[str, str]
    ) -> None:
        """Test updating non-existent feedback fails."""
        response = client.patch(
            "/api/i18n/feedback/00000000-0000-0000-0000-000000000000",
            json={"status": "approved"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    def test_update_feedback_unauthenticated(self, client) -> None:
        """Test updating feedback without authentication fails."""
        response = client.patch(
            "/api/i18n/feedback/00000000-0000-0000-0000-000000000000",
            json={"status": "approved"},
        )
        assert response.status_code == 401
