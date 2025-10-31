"""
Tests for analysis.py module.
"""
import pytest
from analysis import (
    calculate_basic_metrics,
    calculate_ats_ou_rates,
    generate_parlay_suggestions
)


class TestCalculateBasicMetrics:
    """Test basic metrics calculation."""
    
    def test_empty_results(self):
        """Test behavior with empty results."""
        report = {"results": []}
        metrics = calculate_basic_metrics(report)
        
        assert metrics["avg_points_for"] is None
        assert metrics["avg_points_against"] is None
    
    def test_valid_results(self):
        """Test calculation with valid game results."""
        report = {
            "results": [
                {"team_points": "110", "opp_points": "105"},
                {"team_points": "95", "opp_points": "100"},
                {"team_points": "120", "opp_points": "115"}
            ]
        }
        
        metrics = calculate_basic_metrics(report)
        
        # (110 + 95 + 120) / 3 = 108.33
        assert abs(metrics["avg_points_for"] - 108.33333333333333) < 0.01
        # (105 + 100 + 115) / 3 = 106.67
        assert abs(metrics["avg_points_against"] - 106.66666666666667) < 0.01
    
    def test_invalid_data_handling(self):
        """Test handling of invalid point values."""
        report = {
            "results": [
                {"team_points": "110", "opp_points": "105"},
                {"team_points": "invalid", "opp_points": "100"},
                {"team_points": "120", "opp_points": "115"}
            ]
        }
        
        metrics = calculate_basic_metrics(report)
        
        # Should only count valid games (2 out of 3)
        assert abs(metrics["avg_points_for"] - 115.0) < 0.01  # (110 + 120) / 2
        assert abs(metrics["avg_points_against"] - 110.0) < 0.01  # (105 + 115) / 2
    
    def test_missing_results_key(self):
        """Test behavior when results key is missing."""
        report = {}
        metrics = calculate_basic_metrics(report)
        
        assert metrics["avg_points_for"] is None
        assert metrics["avg_points_against"] is None


class TestCalculateAtsOuRates:
    """Test ATS and O/U rates calculation."""
    
    def test_empty_lines(self):
        """Test behavior with empty betting lines."""
        report = {"lines": []}
        rates = calculate_ats_ou_rates(report)
        
        assert rates["ats_rate"] is None
        assert rates["ou_rate"] is None
    
    def test_valid_lines(self):
        """Test calculation with valid betting lines."""
        report = {
            "lines": [
                {"ats": "W", "ou": "O"},
                {"ats": "L", "ou": "U"},
                {"ats": "W", "ou": "O"},
                {"ats": "W", "ou": "U"},
                {"ats": "L", "ou": "O"}
            ]
        }
        
        rates = calculate_ats_ou_rates(report)
        
        assert rates["ats_rate"] == "3W-2L"  # 3 wins, 2 losses
        assert rates["ou_rate"] == "3O-2U"   # 3 overs, 2 unders
    
    def test_more_than_ten_games(self):
        """Test that only last 10 games are considered."""
        lines_data = [{"ats": "W", "ou": "O"} for _ in range(15)]
        report = {"lines": lines_data}
        
        rates = calculate_ats_ou_rates(report)
        
        assert rates["ats_rate"] == "10W-0L"
        assert rates["ou_rate"] == "10O-0U"
    
    def test_missing_lines_key(self):
        """Test behavior when lines key is missing."""
        report = {}
        rates = calculate_ats_ou_rates(report)
        
        assert rates["ats_rate"] is None
        assert rates["ou_rate"] is None


class TestGenerateParlaysuggestions:
    """Test parlay suggestions generation."""
    
    def test_empty_data(self):
        """Test behavior with empty data."""
        report = {"lines": [], "injuries": []}
        suggestions = generate_parlay_suggestions(report)
        
        assert len(suggestions) == 0
    
    def test_over_tendency(self):
        """Test suggestions when team tends to go over."""
        report = {
            "lines": [
                {"ou": "O", "ats": "W"},
                {"ou": "O", "ats": "W"},
                {"ou": "O", "ats": "L"},
                {"ou": "U", "ats": "W"},
                {"ou": "U", "ats": "L"}
            ],
            "injuries": []
        }
        
        suggestions = generate_parlay_suggestions(report)
        
        # Should suggest over (3/5 overs) and cover (3/5 covers)
        total_leg = next((leg for leg in suggestions if leg["type"] == "total"), None)
        spread_leg = next((leg for leg in suggestions if leg["type"] == "spread"), None)
        
        assert total_leg["bet"] == "over"
        assert spread_leg["bet"] == "cover"
    
    def test_under_tendency(self):
        """Test suggestions when team tends to go under."""
        report = {
            "lines": [
                {"ou": "U", "ats": "L"},
                {"ou": "U", "ats": "L"},
                {"ou": "U", "ats": "L"},
                {"ou": "O", "ats": "W"},
                {"ou": "O", "ats": "W"}
            ],
            "injuries": []
        }
        
        suggestions = generate_parlay_suggestions(report)
        
        # Should suggest under (3/5 unders) and fade (3/5 losses)
        total_leg = next((leg for leg in suggestions if leg["type"] == "total"), None)
        spread_leg = next((leg for leg in suggestions if leg["type"] == "spread"), None)
        
        assert total_leg["bet"] == "under"
        assert spread_leg["bet"] == "fade"
    
    def test_injury_suggestions(self):
        """Test player prop suggestions based on injuries."""
        report = {
            "lines": [{"ou": "O", "ats": "W"}],
            "injuries": [
                {"player": "LeBron James"},
                {"player": "Anthony Davis"}
            ]
        }
        
        suggestions = generate_parlay_suggestions(report)
        
        # Should include player prop suggestion
        player_prop = next((leg for leg in suggestions if leg["type"] == "player_prop"), None)
        assert player_prop is not None
        assert "LeBron James" in player_prop["note"]
        assert "Anthony Davis" in player_prop["note"]


if __name__ == "__main__":
    pytest.main([__file__])