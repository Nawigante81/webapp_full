"""
Tests for fetch_data.py module.
"""
import pytest
import requests
from unittest.mock import patch, Mock
from fetch_data import (
    get_team_game_results,
    get_closing_lines, 
    get_injury_report,
    assemble_team_report,
    make_request_with_retry
)


class TestMakeRequestWithRetry:
    """Test the retry mechanism for HTTP requests."""
    
    @patch('fetch_data.requests.get')
    @patch('fetch_data.time.sleep')
    def test_successful_request(self, mock_sleep, mock_get):
        """Test successful request on first attempt."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = make_request_with_retry("https://example.com")
        
        assert result == mock_response
        mock_get.assert_called_once()
        mock_sleep.assert_not_called()
    
    @patch('fetch_data.requests.get')
    @patch('fetch_data.time.sleep')
    def test_retry_on_failure(self, mock_sleep, mock_get):
        """Test retry mechanism on request failure."""
        mock_get.side_effect = [
            requests.exceptions.RequestException("Connection error"),
            requests.exceptions.RequestException("Connection error"),
            Mock()  # Successful response
        ]
        
        result = make_request_with_retry("https://example.com", max_retries=2)
        
        assert result is not None
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
    
    @patch('fetch_data.requests.get')
    @patch('fetch_data.time.sleep')
    def test_max_retries_exceeded(self, mock_sleep, mock_get):
        """Test behavior when max retries are exceeded."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        result = make_request_with_retry("https://example.com", max_retries=1)
        
        assert result is None
        assert mock_get.call_count == 2
        assert mock_sleep.call_count == 1


class TestGetTeamGameResults:
    """Test game results scraping functionality."""
    
    @patch('fetch_data.make_request_with_retry')
    def test_successful_parsing(self, mock_request):
        """Test successful parsing of game results."""
        mock_response = Mock()
        mock_response.text = """
        <table id="games">
            <tbody>
                <tr>
                    <th>1</th>
                    <td>2025-01-01</td>
                    <td>@ LAL</td>
                    <td>W</td>
                    <td>110</td>
                    <td>105</td>
                </tr>
            </tbody>
        </table>
        """
        mock_request.return_value = mock_response
        
        results = get_team_game_results("BOS", 2025)
        
        assert len(results) == 1
        assert results[0]["date"] == "2025-01-01"
        assert results[0]["opponent"] == "LAL"
        assert results[0]["home"] is False
        assert results[0]["team_points"] == "110"
        assert results[0]["opp_points"] == "105"
    
    @patch('fetch_data.make_request_with_retry')
    def test_no_response(self, mock_request):
        """Test behavior when request fails."""
        mock_request.return_value = None
        
        results = get_team_game_results("BOS", 2025)
        
        assert results == []
    
    @patch('fetch_data.make_request_with_retry')
    def test_no_table_found(self, mock_request):
        """Test behavior when games table is not found."""
        mock_response = Mock()
        mock_response.text = "<html><body>No games table</body></html>"
        mock_request.return_value = mock_response
        
        results = get_team_game_results("BOS", 2025)
        
        assert results == []


class TestGetClosingLines:
    """Test betting lines scraping functionality."""
    
    @patch('fetch_data.make_request_with_retry')
    def test_successful_parsing(self, mock_request):
        """Test successful parsing of betting lines."""
        mock_response = Mock()
        mock_response.text = """
        <table class="vi-spread-table">
            <tbody>
                <tr>
                    <td>Jan 1</td>
                    <td>vs LAL</td>
                    <td>-3.5</td>
                    <td>220.5</td>
                    <td>110-105</td>
                    <td>W</td>
                    <td>O</td>
                </tr>
            </tbody>
        </table>
        """
        mock_request.return_value = mock_response
        
        lines = get_closing_lines("celtics")
        
        assert len(lines) == 1
        assert lines[0]["date"] == "Jan 1"
        assert lines[0]["opponent"] == "LAL"
        assert lines[0]["spread"] == "-3.5"
        assert lines[0]["total"] == "220.5"
        assert lines[0]["ats"] == "W"
        assert lines[0]["ou"] == "O"


class TestAssembleTeamReport:
    """Test the main report assembly function."""
    
    @patch('fetch_data.get_injury_report')
    @patch('fetch_data.get_closing_lines')
    @patch('fetch_data.get_team_game_results')
    def test_successful_report_assembly(self, mock_games, mock_lines, mock_injuries):
        """Test successful assembly of team report."""
        mock_games.return_value = [{"date": "2025-01-01", "result": "W"}]
        mock_lines.return_value = [{"date": "Jan 1", "ats": "W"}]
        mock_injuries.return_value = []
        
        report = assemble_team_report("BOS", 2025)
        
        assert report["team"] == "BOS"
        assert len(report["results"]) == 1
        assert len(report["lines"]) == 1
        assert report["injuries"] == []
        
        # Verify VegasInsider mapping was used
        mock_lines.assert_called_with("celtics")
    
    @patch('fetch_data.get_injury_report')
    @patch('fetch_data.get_closing_lines')
    @patch('fetch_data.get_team_game_results')
    def test_unknown_team_mapping(self, mock_games, mock_lines, mock_injuries):
        """Test behavior with unknown team (should use lowercase abbreviation)."""
        mock_games.return_value = []
        mock_lines.return_value = []
        mock_injuries.return_value = []
        
        report = assemble_team_report("UNK", 2025)
        
        assert report["team"] == "UNK"
        mock_lines.assert_called_with("unk")  # Should use lowercase as fallback


if __name__ == "__main__":
    pytest.main([__file__])