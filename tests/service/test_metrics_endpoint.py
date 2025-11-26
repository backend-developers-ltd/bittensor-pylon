import pytest
from litestar.testing import AsyncTestClient

from pylon._internal.common.settings import settings


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_without_token_config_returns_403(self, test_client: AsyncTestClient, monkeypatch):
        monkeypatch.setattr(settings, "metrics_token", None)

        response = await test_client.get("/metrics")

        assert response.status_code == 403
        assert response.json()["detail"] == "Metrics endpoint is not configured"

    @pytest.mark.asyncio
    async def test_metrics_without_authorization_header_returns_403(self, test_client: AsyncTestClient, monkeypatch):
        monkeypatch.setattr(settings, "metrics_token", "test-metrics-token")

        response = await test_client.get("/metrics")

        assert response.status_code == 403
        assert response.json()["detail"] == "Authorization header is required"

    @pytest.mark.asyncio
    async def test_metrics_with_invalid_authorization_format_returns_403(
        self, test_client: AsyncTestClient, monkeypatch
    ):
        monkeypatch.setattr(settings, "metrics_token", "test-metrics-token")

        # Test various invalid formats
        invalid_headers = [
            "invalid-format",
            "Bearer",
            "Basic dGVzdDp0ZXN0",
            "Bearer token with spaces",
            "",
        ]

        for auth_header in invalid_headers:
            response = await test_client.get("/metrics", headers={"Authorization": auth_header})

            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_metrics_with_wrong_token_returns_403(self, test_client: AsyncTestClient, monkeypatch):
        monkeypatch.setattr(settings, "metrics_token", "correct-token")

        response = await test_client.get("/metrics", headers={"Authorization": "Bearer wrong-token"})

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid authorization token"

    @pytest.mark.asyncio
    async def test_metrics_with_correct_token_returns_200(self, test_client: AsyncTestClient, monkeypatch):
        test_token = "correct-metrics-token"
        monkeypatch.setattr(settings, "metrics_token", test_token)

        response = await test_client.get("/metrics", headers={"Authorization": f"Bearer {test_token}"})

        assert response.status_code == 200

        # Should contain Prometheus metrics
        content = response.text
        assert "# HELP" in content or "# TYPE" in content

    @pytest.mark.asyncio
    async def test_metrics_endpoint_includes_pylon_metrics(self, test_client: AsyncTestClient, monkeypatch):
        test_token = "metrics-content-test"
        monkeypatch.setattr(settings, "metrics_token", test_token)

        response = await test_client.get("/metrics", headers={"Authorization": f"Bearer {test_token}"})

        assert response.status_code == 200
        content = response.text

        expected_metrics = [
            "pylon_bittensor_operation_duration_seconds",
            "pylon_bittensor_fallback_total",
        ]

        for metric in expected_metrics:
            assert metric in content, f"Expected metric {metric} not found in response"
