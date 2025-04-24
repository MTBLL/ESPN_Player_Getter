import sys
import pytest
from unittest.mock import patch, MagicMock

from espn_player_getter.cli import parse_args, run_scraper


def test_parse_args():
    """Test argument parsing with default values."""
    # Test with no arguments
    with patch.object(sys, 'argv', ['espn_player_getter']):
        args = parse_args()
        assert args.output == "data/espn_players.json"
        assert args.no_headless is False
        assert args.limit == 500

    # Test with custom arguments
    with patch.object(sys, 'argv', [
        'espn_player_getter', 
        '-o', 'custom_output.json',
        '--no-headless',
        '--limit', '100'
    ]):
        args = parse_args()
        assert args.output == "custom_output.json"
        assert args.no_headless is True
        assert args.limit == 100


@patch('espn_player_getter.cli.ESPNScraper')
@patch('espn_player_getter.cli.save_players')
def test_run_scraper_success(mock_save_players, mock_scraper_class):
    """Test successful execution of the scraper."""
    # Setup mocks
    mock_scraper = MagicMock()
    mock_scraper_class.return_value.__enter__.return_value = mock_scraper
    mock_players = [MagicMock(), MagicMock()]
    mock_scraper.scrape_players.return_value = mock_players
    
    # Test with default arguments
    with patch.object(sys, 'argv', ['espn_player_getter']):
        exit_code = run_scraper()
        
        # Verify scraper was called with correct parameters
        mock_scraper_class.assert_called_once()
        mock_scraper.scrape_players.assert_called_once()
        
        # Verify players were saved
        mock_save_players.assert_called_once_with(mock_players, "data/espn_players.json")
        
        # Verify exit code
        assert exit_code == 0


@patch('espn_player_getter.cli.ESPNScraper')
def test_run_scraper_error(mock_scraper_class):
    """Test error handling in the scraper."""
    # Setup mock to raise an exception
    mock_scraper = MagicMock()
    mock_scraper_class.return_value.__enter__.return_value = mock_scraper
    mock_scraper.scrape_players.side_effect = Exception("Test error")
    
    # Test with default arguments
    with patch.object(sys, 'argv', ['espn_player_getter']):
        with patch('sys.stderr'):  # Suppress error output
            exit_code = run_scraper()
            
            # Verify exit code indicates error
            assert exit_code == 1