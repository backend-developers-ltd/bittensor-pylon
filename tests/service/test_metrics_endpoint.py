"""
Tests for metrics endpoint authentication.
"""

import pytest
from litestar.testing import AsyncTestClient

from pylon._internal.common.settings import settings


class TestMetricsEndpoint:
    """Test metrics endpoint authentication."""

    @pytest.mark.asyncio
    async def test_metrics_without_token_config_returns_403(self, test_client: AsyncTestClient, monkeypatch):
        """
        Test that metrics endpoint returns 403 when PYLON_METRICS_TOKEN is not configured.
        """
        # Temporarily unset the metrics token
        monkeypatch.setattr(settings, "pylon_metrics_token", None)

        response = await test_client.get("/metrics")

        assert response.status_code == 403
        assert response.json()["detail"] == "Metrics endpoint is not configured"

    @pytest.mark.asyncio
    async def test_metrics_without_authorization_header_returns_401(self, test_client: AsyncTestClient, monkeypatch):
        """
        Test that metrics endpoint returns 401 when Authorization header is missing.
        """
        # Set a valid metrics token
        monkeypatch.setattr(settings, "pylon_metrics_token", "test-metrics-token")

        response = await test_client.get("/metrics")

        assert response.status_code == 401
        assert response.json()["detail"] == "Authorization header is required"

    @pytest.mark.asyncio
    async def test_metrics_with_invalid_authorization_format_returns_401(
        self, test_client: AsyncTestClient, monkeypatch
    ):
        """
        Test that metrics endpoint returns 401 when Authorization header format is invalid.
        """
        # Set a valid metrics token
        monkeypatch.setattr(settings, "pylon_metrics_token", "test-metrics-token")

        # Test various invalid formats
        invalid_headers = [
            "invalid-format",
            "Bearer",  # Missing token
            "Basic dGVzdDp0ZXN0",  # Wrong auth type
            "Bearer token with spaces",  # Multiple parts after Bearer
            "",  # Empty header
        ]

        for auth_header in invalid_headers:
            response = await test_client.get("/metrics", headers={"Authorization": auth_header})

            assert response.status_code == 401
            # Different invalid formats may produce different error messages
            detail = response.json()["detail"]
            assert any(
                expected in detail
                for expected in [
                    "Invalid Authorization header format",
                    "Authorization header is required",
                    "Invalid authorization token",
                ]
            )

    @pytest.mark.asyncio
    async def test_metrics_with_wrong_token_returns_401(self, test_client: AsyncTestClient, monkeypatch):
        """
        Test that metrics endpoint returns 401 when Bearer token is incorrect.
        """
        # Set a valid metrics token
        monkeypatch.setattr(settings, "pylon_metrics_token", "correct-token")

        response = await test_client.get("/metrics", headers={"Authorization": "Bearer wrong-token"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authorization token"

    @pytest.mark.asyncio
    async def test_metrics_with_correct_token_returns_200(self, test_client: AsyncTestClient, monkeypatch):
        """
        Test that metrics endpoint returns 200 when Bearer token is correct.
        """
        # Set a valid metrics token
        test_token = "correct-metrics-token"
        monkeypatch.setattr(settings, "pylon_metrics_token", test_token)

        response = await test_client.get("/metrics", headers={"Authorization": f"Bearer {test_token}"})

        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

        # Should contain Prometheus metrics format
        content = response.text
        assert "# HELP" in content or "# TYPE" in content

    @pytest.mark.asyncio
    async def test_metrics_with_case_insensitive_bearer(self, test_client: AsyncTestClient, monkeypatch):
        """
        Test that metrics endpoint accepts case-insensitive 'Bearer' keyword.
        """
        # Set a valid metrics token
        test_token = "case-test-token"
        monkeypatch.setattr(settings, "pylon_metrics_token", test_token)

        # Test different cases
        case_variants = ["Bearer", "bearer", "BEARER", "BeArEr"]

        for variant in case_variants:
            response = await test_client.get("/metrics", headers={"Authorization": f"{variant} {test_token}"})

            assert response.status_code == 200, f"Failed for case variant: {variant}"

    @pytest.mark.asyncio
    async def test_metrics_token_with_special_characters(self, test_client: AsyncTestClient, monkeypatch):
        """
        Test that metrics endpoint works with tokens containing special characters.
        """
        # Set a token with special characters
        special_token = "tok3n-with_spec!al.ch@rs#$%"
        monkeypatch.setattr(settings, "pylon_metrics_token", special_token)

        response = await test_client.get("/metrics", headers={"Authorization": f"Bearer {special_token}"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_empty_token_config_returns_403(self, test_client: AsyncTestClient, monkeypatch):
        """
        Test that metrics endpoint returns 403 when PYLON_METRICS_TOKEN is empty string.
        """
        # Set empty string (falsy but not None)
        monkeypatch.setattr(settings, "pylon_metrics_token", "")

        response = await test_client.get("/metrics")

        assert response.status_code == 403
        assert response.json()["detail"] == "Metrics endpoint is not configured"

    @pytest.mark.asyncio
    async def test_metrics_endpoint_includes_pylon_metrics(self, test_client: AsyncTestClient, monkeypatch):
        """
        Test that metrics endpoint includes pylon-specific metrics.
        """
        # Set a valid metrics token
        test_token = "metrics-content-test"
        monkeypatch.setattr(settings, "pylon_metrics_token", test_token)

        response = await test_client.get("/metrics", headers={"Authorization": f"Bearer {test_token}"})

        assert response.status_code == 200
        content = response.text

        # Should contain pylon-specific metrics (defined in metrics.py)
        expected_metrics = [
            "pylon_bittensor_operation_duration_seconds",
            "pylon_bittensor_errors_total",
        ]

        for metric in expected_metrics:
            assert metric in content, f"Expected metric {metric} not found in response"
