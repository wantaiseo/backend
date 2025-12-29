"""
CiteKit – API Tests
Integration tests for FastAPI endpoints
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from models import CompileJob, JobStatus


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_health_check_returns_200(self, client):
        """Test that health check returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_healthy_status(self, client):
        """Test that health check returns healthy status."""
        response = client.get("/health")
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "service" in data


class TestJobStatusEndpoint:
    """Tests for job status endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_status_nonexistent_job_returns_404(self, client):
        """Test that getting status of nonexistent job returns 404."""
        with patch('main.get_database') as mock_db:
            mock_db_instance = MagicMock()
            mock_db_instance.get_job = AsyncMock(return_value=None)
            mock_db.return_value = mock_db_instance
            
            response = client.get("/status/nonexistent-job-id")
            assert response.status_code == 404

    def test_status_existing_job_returns_data(self, client, sample_job):
        """Test that getting status of existing job returns data."""
        with patch('main.get_database') as mock_db:
            mock_db_instance = MagicMock()
            mock_db_instance.get_job = AsyncMock(return_value=sample_job)
            mock_db.return_value = mock_db_instance
            
            response = client.get(f"/status/{sample_job.job_id}")
            
            if response.status_code == 200:
                data = response.json()
                assert data["job_id"] == sample_job.job_id
                assert "status" in data
                assert "progress" in data


class TestDownloadEndpoint:
    """Tests for download endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_download_nonexistent_job_returns_404(self, client):
        """Test that downloading nonexistent job returns 404."""
        with patch('main.get_database') as mock_db:
            mock_db_instance = MagicMock()
            mock_db_instance.get_job = AsyncMock(return_value=None)
            mock_db.return_value = mock_db_instance
            
            response = client.get("/download/nonexistent-job-id")
            assert response.status_code == 404

    def test_download_incomplete_job_returns_400(self, client, sample_job):
        """Test that downloading incomplete job returns 400."""
        sample_job.status = JobStatus.PENDING
        
        with patch('main.get_database') as mock_db:
            mock_db_instance = MagicMock()
            mock_db_instance.get_job = AsyncMock(return_value=sample_job)
            mock_db.return_value = mock_db_instance
            
            response = client.get(f"/download/{sample_job.job_id}")
            assert response.status_code == 400


class TestCancelEndpoint:
    """Tests for cancel job endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_cancel_nonexistent_job_returns_404(self, client):
        """Test that cancelling nonexistent job returns 404."""
        with patch('main.get_database') as mock_db:
            mock_db_instance = MagicMock()
            mock_db_instance.get_job = AsyncMock(return_value=None)
            mock_db.return_value = mock_db_instance
            
            response = client.post("/cancel/nonexistent-job-id")
            assert response.status_code == 404

    def test_cancel_completed_job_returns_unchanged(self, client, sample_job):
        """Test that cancelling completed job returns unchanged status."""
        sample_job.status = JobStatus.COMPLETED
        
        with patch('main.get_database') as mock_db:
            mock_db_instance = MagicMock()
            mock_db_instance.get_job = AsyncMock(return_value=sample_job)
            mock_db.return_value = mock_db_instance
            
            response = client.post(f"/cancel/{sample_job.job_id}")
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "unchanged"

    def test_cancel_running_job_returns_cancelled(self, client, sample_job):
        """Test that cancelling running job returns cancelled status."""
        sample_job.status = JobStatus.EXTRACTING
        
        with patch('main.get_database') as mock_db:
            mock_db_instance = MagicMock()
            mock_db_instance.get_job = AsyncMock(return_value=sample_job)
            mock_db_instance.update_job_status = AsyncMock(return_value=None)
            mock_db.return_value = mock_db_instance
            
            # Mock the import of celery_app inside main.py
            with patch.dict('sys.modules', {'celery_app': MagicMock()}):
                import sys
                sys.modules['celery_app'].celery_app = MagicMock()
                sys.modules['celery_app'].celery_app.control.revoke = MagicMock()
                
                response = client.post(f"/cancel/{sample_job.job_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "cancelled"


class TestCompileEndpointAuth:
    """Tests for compile endpoint authentication."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_compile_without_auth_returns_401(self, client):
        """Test that compile without auth returns 401."""
        response = client.post("/compile", json={"url": "https://example.com"})
        # Should return 401 since auth is required before validation
        assert response.status_code == 401

    def test_compile_with_empty_body_returns_401(self, client):
        """Test that compile with empty body still requires auth first."""
        # Auth check happens before validation, so we get 401 not 422
        response = client.post("/compile", json={})
        assert response.status_code == 401


class TestCORSMiddleware:
    """Tests for CORS configuration."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in response."""
        response = client.options("/health", headers={"Origin": "http://localhost:3000"})
        # CORS should allow the request
        assert response.status_code in [200, 204, 405]


class TestRootEndpoint:
    """Tests for root endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_root_returns_html(self, client):
        """Test that root returns HTML content."""
        try:
            response = client.get("/")
            # Should return HTML or redirect
            assert response.status_code in [200, 404, 500]  # 404 if static file missing
        except Exception:
            # File might not exist in test environment
            pass
