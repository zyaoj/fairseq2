"""Tests for terminology override API endpoints."""


class TestTerminologyResolve:
    """Tests for resolving terminology with hierarchical overrides."""

    def test_resolve_terminology_base_only(self, client, auth_headers: dict[str, str]) -> None:
        """Test resolving terminology without any overrides."""
        response = client.post(
            "/api/terminology/resolve",
            json={
                "term_keys": ["common.save", "common.cancel"],
                "locale": "zh-CN",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "resolutions" in data
        # Without overrides, source should be 'base'
        for term_key, resolution in data["resolutions"].items():
            assert resolution["source"] == "base"
            assert resolution["term_key"] == term_key

    def test_resolve_terminology_unsupported_locale(self, client, auth_headers: dict[str, str]) -> None:
        """Test resolving terminology with unsupported locale."""
        response = client.post(
            "/api/terminology/resolve",
            json={
                "term_keys": ["common.save"],
                "locale": "fr-FR",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Unsupported locale" in response.json()["detail"]

    def test_resolve_terminology_unauthenticated(self, client) -> None:
        """Test that resolving terminology requires authentication."""
        response = client.post(
            "/api/terminology/resolve",
            json={
                "term_keys": ["common.save"],
                "locale": "zh-CN",
            },
        )
        assert response.status_code == 401


class TestTerminologyCreate:
    """Tests for creating terminology overrides."""

    def _get_current_user_id(self, client, auth_headers: dict[str, str]) -> str:
        """Helper to get the current user's ID."""
        response = client.get("/api/auth/me", headers=auth_headers)
        return response.json()["id"]

    def test_create_user_override(self, client, auth_headers: dict[str, str]) -> None:
        """Test creating a user-level terminology override."""
        user_id = self._get_current_user_id(client, auth_headers)

        response = client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": user_id,
                "term_key": "stone_location.left_kidney",
                "locale": "zh-CN",
                "display_value": "我的左肾",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["scope_type"] == "user"
        assert data["scope_id"] == user_id
        assert data["term_key"] == "stone_location.left_kidney"
        assert data["display_value"] == "我的左肾"

    def test_create_user_override_for_other_user_fails(self, client, auth_headers: dict[str, str]) -> None:
        """Test that users cannot create overrides for other users."""
        other_user_id = "00000000-0000-0000-0000-000000000001"

        response = client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": other_user_id,
                "term_key": "stone_location.left_kidney",
                "locale": "zh-CN",
                "display_value": "Custom text",
            },
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "Cannot create override for another user" in response.json()["detail"]

    def test_create_hospital_override_requires_admin(self, client, auth_headers: dict[str, str]) -> None:
        """Test that only admins can create hospital-level overrides."""
        response = client.post(
            "/api/terminology",
            json={
                "scope_type": "hospital",
                "scope_id": "00000000-0000-0000-0000-000000000001",
                "term_key": "stone_location.left_kidney",
                "locale": "zh-CN",
                "display_value": "Hospital term",
            },
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "Only admins can create hospital-level overrides" in response.json()["detail"]

    def test_create_hospital_override_as_admin(
        self, client, admin_auth_headers: dict[str, str]
    ) -> None:
        """Test that admins can create hospital-level overrides."""
        response = client.post(
            "/api/terminology",
            json={
                "scope_type": "hospital",
                "scope_id": "00000000-0000-0000-0000-000000000001",
                "term_key": "stone_location.left_kidney",
                "locale": "zh-CN",
                "display_value": "Hospital term",
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 201

    def test_create_override_unsupported_locale(self, client, auth_headers: dict[str, str]) -> None:
        """Test creating override with unsupported locale."""
        user_id = self._get_current_user_id(client, auth_headers)

        response = client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": user_id,
                "term_key": "stone_location.left_kidney",
                "locale": "fr-FR",
                "display_value": "Custom term",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Unsupported locale" in response.json()["detail"]

    def test_create_override_upsert(self, client, auth_headers: dict[str, str]) -> None:
        """Test that creating an override for the same key updates it."""
        user_id = self._get_current_user_id(client, auth_headers)

        # Create first override
        response1 = client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": user_id,
                "term_key": "stone_location.left_kidney",
                "locale": "zh-CN",
                "display_value": "First value",
            },
            headers=auth_headers,
        )
        assert response1.status_code == 201
        first_id = response1.json()["id"]

        # Create second override for the same key (should update)
        response2 = client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": user_id,
                "term_key": "stone_location.left_kidney",
                "locale": "zh-CN",
                "display_value": "Updated value",
            },
            headers=auth_headers,
        )
        assert response2.status_code == 201
        # Should be the same record (upsert)
        assert response2.json()["id"] == first_id
        assert response2.json()["display_value"] == "Updated value"


class TestTerminologyList:
    """Tests for listing terminology overrides."""

    def _get_current_user_id(self, client, auth_headers: dict[str, str]) -> str:
        """Helper to get the current user's ID."""
        response = client.get("/api/auth/me", headers=auth_headers)
        return response.json()["id"]

    def test_list_my_overrides_empty(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing user overrides when none exist."""
        response = client.get("/api/terminology/my-overrides", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_my_overrides(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing user's own overrides."""
        user_id = self._get_current_user_id(client, auth_headers)

        # Create two overrides
        for i in range(2):
            client.post(
                "/api/terminology",
                json={
                    "scope_type": "user",
                    "scope_id": user_id,
                    "term_key": f"term_{i}",
                    "locale": "zh-CN",
                    "display_value": f"Value {i}",
                },
                headers=auth_headers,
            )

        response = client.get("/api/terminology/my-overrides", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_my_overrides_with_locale_filter(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing user overrides with locale filter."""
        user_id = self._get_current_user_id(client, auth_headers)

        # Create overrides in different locales
        client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": user_id,
                "term_key": "term_zh",
                "locale": "zh-CN",
                "display_value": "中文",
            },
            headers=auth_headers,
        )
        client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": user_id,
                "term_key": "term_en",
                "locale": "en",
                "display_value": "English",
            },
            headers=auth_headers,
        )

        # Filter by locale
        response = client.get(
            "/api/terminology/my-overrides?locale=zh-CN",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["locale"] == "zh-CN"

    def test_list_hospital_overrides_no_hospital(self, client, auth_headers: dict[str, str]) -> None:
        """Test listing hospital overrides when user has no hospital."""
        response = client.get("/api/terminology/hospital-overrides", headers=auth_headers)
        assert response.status_code == 400
        assert "No hospital assigned" in response.json()["detail"]


class TestTerminologyUpdate:
    """Tests for updating terminology overrides."""

    def _get_current_user_id(self, client, auth_headers: dict[str, str]) -> str:
        """Helper to get the current user's ID."""
        response = client.get("/api/auth/me", headers=auth_headers)
        return response.json()["id"]

    def _create_user_override(
        self, client, auth_headers: dict[str, str], user_id: str
    ) -> str:
        """Helper to create a user override and return its ID."""
        response = client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": user_id,
                "term_key": "test_term",
                "locale": "zh-CN",
                "display_value": "Original value",
            },
            headers=auth_headers,
        )
        return response.json()["id"]

    def test_update_own_override(self, client, auth_headers: dict[str, str]) -> None:
        """Test updating user's own override."""
        user_id = self._get_current_user_id(client, auth_headers)
        override_id = self._create_user_override(client, auth_headers, user_id)

        response = client.put(
            f"/api/terminology/{override_id}",
            json={"display_value": "Updated value"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["display_value"] == "Updated value"

    def test_update_not_found(self, client, auth_headers: dict[str, str]) -> None:
        """Test updating non-existent override."""
        response = client.put(
            "/api/terminology/00000000-0000-0000-0000-000000000000",
            json={"display_value": "Updated value"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestTerminologyDelete:
    """Tests for deleting terminology overrides."""

    def _get_current_user_id(self, client, auth_headers: dict[str, str]) -> str:
        """Helper to get the current user's ID."""
        response = client.get("/api/auth/me", headers=auth_headers)
        return response.json()["id"]

    def _create_user_override(
        self, client, auth_headers: dict[str, str], user_id: str
    ) -> str:
        """Helper to create a user override and return its ID."""
        response = client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": user_id,
                "term_key": "test_term",
                "locale": "zh-CN",
                "display_value": "Original value",
            },
            headers=auth_headers,
        )
        return response.json()["id"]

    def test_delete_own_override(self, client, auth_headers: dict[str, str]) -> None:
        """Test deleting user's own override."""
        user_id = self._get_current_user_id(client, auth_headers)
        override_id = self._create_user_override(client, auth_headers, user_id)

        response = client.delete(
            f"/api/terminology/{override_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify it's deleted
        response = client.get("/api/terminology/my-overrides", headers=auth_headers)
        assert response.json() == []

    def test_delete_not_found(self, client, auth_headers: dict[str, str]) -> None:
        """Test deleting non-existent override."""
        response = client.delete(
            "/api/terminology/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_delete_unauthenticated(self, client) -> None:
        """Test that deleting requires authentication."""
        response = client.delete(
            "/api/terminology/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


class TestTerminologyHierarchy:
    """Tests for hierarchical terminology resolution."""

    def _get_current_user_id(self, client, auth_headers: dict[str, str]) -> str:
        """Helper to get the current user's ID."""
        response = client.get("/api/auth/me", headers=auth_headers)
        return response.json()["id"]

    def test_user_override_takes_precedence(self, client, auth_headers: dict[str, str]) -> None:
        """Test that user override takes precedence over base."""
        user_id = self._get_current_user_id(client, auth_headers)

        # Create a user override
        client.post(
            "/api/terminology",
            json={
                "scope_type": "user",
                "scope_id": user_id,
                "term_key": "common.save",
                "locale": "zh-CN",
                "display_value": "用户自定义保存",
            },
            headers=auth_headers,
        )

        # Resolve the term
        response = client.post(
            "/api/terminology/resolve",
            json={
                "term_keys": ["common.save"],
                "locale": "zh-CN",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        resolution = data["resolutions"]["common.save"]
        assert resolution["source"] == "user"
        assert resolution["display_value"] == "用户自定义保存"
