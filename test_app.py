"""
Tests for app.py module.
"""
import json
import pytest
from unittest.mock import patch, Mock, MagicMock
from http.server import HTTPServer
import threading
import time
import requests
from app import FullHandler, save_report, fetch_reports


class TestFullHandler:
    """Test HTTP handler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = FullHandler()
        self.handler.send_response = Mock()
        self.handler.send_header = Mock()
        self.handler.end_headers = Mock()
        self.handler.wfile = Mock()
        self.handler.headers = {}
    
    @patch('app.assemble_team_report')
    def test_handle_generate_report(self, mock_assemble):
        """Test report generation endpoint."""
        mock_assemble.return_value = {"team": "BOS", "results": []}
        self.handler.path = "/api/report/bos"
        
        self.handler.handle_generate_report("bos", False)
        
        self.handler.send_response.assert_called_with(200)
        self.handler.send_header.assert_called_with('Content-Type', 'application/json')
        mock_assemble.assert_called_with("BOS", season=2025)
    
    @patch('app.calculate_basic_metrics')
    @patch('app.calculate_ats_ou_rates')
    @patch('app.generate_parlay_suggestions')
    @patch('app.assemble_team_report')
    def test_handle_analysis(self, mock_assemble, mock_suggestions, mock_rates, mock_metrics):
        """Test analysis endpoint."""
        mock_assemble.return_value = {"team": "BOS", "results": []}
        mock_metrics.return_value = {"avg_points_for": 110.0}
        mock_rates.return_value = {"ats_rate": "3W-2L"}
        mock_suggestions.return_value = [{"type": "total", "bet": "over"}]
        
        self.handler.handle_analysis("bos")
        
        self.handler.send_response.assert_called_with(200)
        mock_assemble.assert_called_with("BOS", season=2025)
        mock_metrics.assert_called_once()
        mock_rates.assert_called_once()
        mock_suggestions.assert_called_once()
    
    @patch('builtins.open')
    def test_serve_full_page_success(self, mock_open):
        """Test serving the full HTML page successfully."""
        mock_file = Mock()
        mock_file.read.return_value = b"<html>Test</html>"
        mock_open.return_value.__enter__.return_value = mock_file
        
        self.handler.serve_full_page()
        
        self.handler.send_response.assert_called_with(200)
        self.handler.send_header.assert_called_with('Content-Type', 'text/html; charset=utf-8')
    
    @patch('builtins.open')
    def test_serve_full_page_not_found(self, mock_open):
        """Test serving page when file not found."""
        mock_open.side_effect = FileNotFoundError()
        
        self.handler.serve_full_page()
        
        self.handler.send_response.assert_called_with(500)


class TestSupabaseFunctions:
    """Test Supabase integration functions."""
    
    @patch('app.requests.post')
    @patch('app.SUPABASE_URL', 'https://test.supabase.co')
    @patch('app.SUPABASE_SERVICE_KEY', 'test-key')
    def test_save_report_success(self, mock_post):
        """Test successful report saving."""
        mock_post.return_value.status_code = 201
        
        save_report("bos", {"team": "BOS"}, "Bearer token")
        
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "reports" in call_args[1]["url"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer token"
    
    @patch('app.requests.post')
    def test_save_report_no_config(self, mock_post):
        """Test save report when Supabase not configured."""
        with patch('app.SUPABASE_URL', None):
            save_report("bos", {"team": "BOS"}, "Bearer token")
        
        mock_post.assert_not_called()
    
    @patch('app.requests.get')
    @patch('app.SUPABASE_URL', 'https://test.supabase.co')
    @patch('app.SUPABASE_SERVICE_KEY', 'test-key')
    def test_fetch_reports_success(self, mock_get):
        """Test successful reports fetching."""
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1, "team": "bos"}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetch_reports("Bearer token", "bos", "2025-01-01", "2025-01-31")
        
        assert len(result) == 1
        assert result[0]["team"] == "bos"
        mock_get.assert_called_once()
    
    @patch('app.requests.get')
    def test_fetch_reports_no_config(self, mock_get):
        """Test fetch reports when Supabase not configured."""
        with patch('app.SUPABASE_URL', None):
            result = fetch_reports("Bearer token")
        
        assert result == []
        mock_get.assert_not_called()
    
    @patch('app.requests.get')
    @patch('app.SUPABASE_URL', 'https://test.supabase.co')
    @patch('app.SUPABASE_SERVICE_KEY', 'test-key')
    def test_fetch_reports_request_error(self, mock_get):
        """Test fetch reports with request error."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        result = fetch_reports("Bearer token")
        
        assert result == []


class TestIntegration:
    """Integration tests for the complete application."""
    
    @pytest.fixture
    def mock_server_data(self):
        """Mock data for server tests."""
        return {
            "report": {"team": "BOS", "results": [{"date": "2025-01-01"}]},
            "metrics": {"avg_points_for": 110.0},
            "rates": {"ats_rate": "3W-2L"},
            "suggestions": [{"type": "total", "bet": "over"}]
        }
    
    @patch('app.assemble_team_report')
    @patch('app.calculate_basic_metrics')
    @patch('app.calculate_ats_ou_rates')
    @patch('app.generate_parlay_suggestions')
    def test_full_analysis_flow(self, mock_suggestions, mock_rates, mock_metrics, mock_assemble, mock_server_data):
        """Test the complete analysis flow."""
        mock_assemble.return_value = mock_server_data["report"]
        mock_metrics.return_value = mock_server_data["metrics"]
        mock_rates.return_value = mock_server_data["rates"]
        mock_suggestions.return_value = mock_server_data["suggestions"]
        
        handler = FullHandler()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        
        handler.handle_analysis("bos")
        
        # Verify all components were called
        mock_assemble.assert_called_once()
        mock_metrics.assert_called_once()
        mock_rates.assert_called_once()
        mock_suggestions.assert_called_once()
        
        # Verify response was sent
        handler.send_response.assert_called_with(200)


class TestPlayerStatsEndpoint:
    """Tests for the /api/game/<game_id>/players endpoint."""

    def setup_method(self):
        self.handler = FullHandler()
        self.handler.send_response = Mock()
        self.handler.send_header = Mock()
        self.handler.end_headers = Mock()
        self.handler.wfile = Mock()

    @patch('app.get_player_statistics_api_nba')
    def test_handle_player_stats(self, mock_stats):
        mock_stats.return_value = [
            {"player": "John Doe", "team": "CHI", "points": 25}
        ]

        self.handler.handle_player_stats("8133")

        self.handler.send_response.assert_called_with(200)
        mock_stats.assert_called_once_with("8133")


class TestRapidApiScoresEndpoint:
    def setup_method(self):
        self.handler = FullHandler()
        self.handler.send_response = Mock()
        self.handler.send_header = Mock()
        self.handler.end_headers = Mock()
        self.handler.wfile = Mock()

    @patch('app.get_scores_rapid')
    def test_handle_scores(self, mock_scores):
        mock_scores.return_value = {"fixtureId": "id1200", "home_score": 101, "away_score": 99}

        self.handler.handle_scores("id1200")

        self.handler.send_response.assert_called_with(200)
        mock_scores.assert_called_once_with("id1200")


if __name__ == "__main__":
    pytest.main([__file__])