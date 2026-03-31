#!/usr/bin/env python3
"""
Unit tests for the MP3/M4A organizer.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

import organize_music


class TestGetLabelFromMetadata(unittest.TestCase):
    """Tests for get_label_from_metadata function."""

    @patch('subprocess.run')
    def test_label_found(self, mock_run):
        """Test when label is found in metadata."""
        mock_run.return_value.stdout = "Test Label\n"
        mock_run.return_value.returncode = 0

        result = organize_music.get_label_from_metadata(Path("test.mp3"), None)
        self.assertEqual(result, "Test Label")

    @patch('subprocess.run')
    def test_label_not_found(self, mock_run):
        """Test when label is not found in metadata."""
        mock_run.return_value.stdout = ""
        mock_run.return_value.returncode = 1

        result = organize_music.get_label_from_metadata(Path("test.mp3"), None)
        self.assertIsNone(result)

    @patch('subprocess.run')
    def test_label_with_source_tag(self, mock_run):
        """Test when label_source_tag is provided."""
        mock_run.return_value.stdout = "Test Label\n"
        mock_run.return_value.returncode = 0

        result = organize_music.get_label_from_metadata(Path("test.mp3"), "TPUB")
        # Should have called ffprobe with TPUB tag
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("format_tags=TPUB", args)
        self.assertEqual(result, "Test Label")


class TestLookupLabelOnline(unittest.TestCase):
    """Tests for lookup_label_online function."""

    @patch('urllib.request.urlopen')
    def test_label_found_online(self, mock_urlopen):
        """Test when label is found via online lookup."""
        # Mock the iTunes search response (context manager)
        search_cm = MagicMock()
        search_cm.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 1,
            'results': [{'trackId': 12345}]
        }).encode()

        # Mock the iTunes lookup response (context manager)
        lookup_cm = MagicMock()
        lookup_cm.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 1,
            'results': [{'label': 'Test Label'}]
        }).encode()

        # Make urlopen return the search response first, then the lookup response
        mock_urlopen.side_effect = [search_cm, lookup_cm]

        result = organize_music.lookup_label_online("Test Artist", "Test Title")
        self.assertEqual(result, "Test Label")
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch('urllib.request.urlopen')
    def test_label_not_found_online(self, mock_urlopen):
        """Test when label is not found via online lookup."""
        # Mock the response (context manager)
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 0
        }).encode()
        mock_urlopen.return_value = mock_cm

        result = organize_music.lookup_label_online("Test Artist", "Test Title")
        self.assertIsNone(result)

    @patch('urllib.request.urlopen')
    def test_label_online_exception(self, mock_urlopen):
        """Test when an exception occurs during online lookup."""
        mock_urlopen.side_effect = Exception("Network error")

        result = organize_music.lookup_label_online("Test Artist", "Test Title")
        self.assertIsNone(result)


class TestFindLabelDestination(unittest.TestCase):
    """Tests for find_label_destination function."""

    def test_label_mapped_exact(self):
        """Test when label exactly matches a key in the mapping."""
        label_to_dest = {"Test Label": "/path/to/dest"}
        result = organize_music.find_label_destination("Test Label", label_to_dest)
        self.assertEqual(result, "/path/to/dest")

    def test_label_mapped_case_insensitive(self):
        """Test when label matches case-insensitively."""
        label_to_dest = {"Test Label": "/path/to/dest"}
        result = organize_music.find_label_destination("test label", label_to_dest)
        self.assertEqual(result, "/path/to/dest")

    def test_label_mapped_comma_separated(self):
        """Test when label matches a part of a comma-separated key."""
        label_to_dest = {"Genre1, Genre2": "/path/to/dest"}
        result = organize_music.find_label_destination("Genre2", label_to_dest)
        self.assertEqual(result, "/path/to/dest")

    def test_label_special_case_drum_bass(self):
        """Test the special case for drum and bass."""
        label_to_dest = {"Drum n Base": "/path/to/dest"}
        result = organize_music.find_label_destination("DRUM and BASS Music", label_to_dest)
        self.assertEqual(result, "/path/to/dest")

    def test_label_not_mapped(self):
        """Test when label is not found in mapping."""
        label_to_dest = {"Other Label": "/path/to/dest"}
        result = organize_music.find_label_destination("Test Label", label_to_dest)
        self.assertIsNone(result)


class TestGetGenreFromMetadata(unittest.TestCase):
    """Tests for get_genre_from_metadata function."""

    @patch('subprocess.run')
    def test_genre_found(self, mock_run):
        """Test when genre is found in metadata."""
        mock_run.return_value.stdout = "Test Genre\n"
        mock_run.return_value.returncode = 0

        result = organize_music.get_genre_from_metadata(Path("test.mp3"))
        self.assertEqual(result, "Test Genre")

    @patch('subprocess.run')
    def test_genre_not_found(self, mock_run):
        """Test when genre is not found in metadata."""
        mock_run.return_value.stdout = ""
        mock_run.return_value.returncode = 1

        result = organize_music.get_genre_from_metadata(Path("test.mp3"))
        self.assertIsNone(result)


class TestGetGenreOnline(unittest.TestCase):
    """Tests for get_genre_online function."""

    def setUp(self):
        """Clear genre cache before each test to ensure test isolation."""
        if hasattr(organize_music, '_genre_cache'):
            organize_music._genre_cache.clear()

    @patch('urllib.request.urlopen')
    def test_genre_found_itunes(self, mock_urlopen):
        """Test when genre is found via iTunes."""
        # Mock the response (context manager)
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 1,
            'results': [{'primaryGenreName': 'Test Genre'}]
        }).encode()
        mock_urlopen.return_value = mock_cm

        result = organize_music.get_genre_online("Test Artist", "Test Title")
        self.assertEqual(result, "Test Genre")

    @patch('urllib.request.urlopen')
    def test_genre_found_musicbrainz(self, mock_urlopen):
        """Test when genre is found via MusicBrainz (iTunes fails)."""
        # Mock the responses (context managers)
        itunes_resp = MagicMock()
        itunes_resp.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 0
        }).encode()
        
        mb_search_resp = MagicMock()
        mb_search_resp.__enter__.return_value.read.return_value = json.dumps({
            'recordings': [{'id': 'recording-id'}]
        }).encode()
        
        mb_rg_resp = MagicMock()
        mb_rg_resp.__enter__.return_value.read.return_value = json.dumps({
            'release-groups': [{'id': 'rg-id'}]
        }).encode()
        
        mb_tag_resp = MagicMock()
        mb_tag_resp.__enter__.return_value.read.return_value = json.dumps({
            'release-group': {'tags': [{'name': 'Test Genre'}]}
        }).encode()

        mock_urlopen.side_effect = [itunes_resp, mb_search_resp, mb_rg_resp, mb_tag_resp]

        result = organize_music.get_genre_online("Test Artist", "Test Title")
        self.assertEqual(result, "Test Genre")
        self.assertEqual(mock_urlopen.call_count, 4)

    @patch('urllib.request.urlopen')
    def test_genre_not_found_online(self, mock_urlopen):
        """Test when genre is not found via online lookup."""
        # Mock the response (context manager)
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 0
        }).encode()
        mock_urlopen.return_value = mock_cm

        result = organize_music.get_genre_online("Test Artist", "Test Title")
        self.assertIsNone(result)

    @patch('urllib.request.urlopen')
    def test_genre_online_exception(self, mock_urlopen):
        """Test when an exception occurs during online lookup."""
        mock_urlopen.side_effect = Exception("Network error")

        result = organize_music.get_genre_online("Test Artist", "Test Title")
        self.assertIsNone(result)


class TestFindGenreDestination(unittest.TestCase):
    """Tests for find_genre_destination function."""

    def test_genre_mapped_exact(self):
        """Test when genre exactly matches a key in the mapping."""
        genre_to_dest = {"Test Genre": "/path/to/dest"}
        result = organize_music.find_genre_destination("Test Genre", genre_to_dest)
        self.assertEqual(result, "/path/to/dest")

    def test_genre_mapped_case_insensitive(self):
        """Test when genre matches case-insensitively."""
        genre_to_dest = {"Test Genre": "/path/to/dest"}
        result = organize_music.find_genre_destination("test genre", genre_to_dest)
        self.assertEqual(result, "/path/to/dest")

    def test_genre_mapped_comma_separated(self):
        """Test when genre matches a part of a comma-separated key."""
        genre_to_dest = {"Genre1, Genre2": "/path/to/dest"}
        result = organize_music.find_genre_destination("Genre2", genre_to_dest)
        self.assertEqual(result, "/path/to/dest")

    def test_genre_special_case_drum_bass(self):
        """Test the special case for drum and bass."""
        genre_to_dest = {"Drum n Base": "/path/to/dest"}
        result = organize_music.find_genre_destination("DRUM and BASS Music", genre_to_dest)
        self.assertEqual(result, "/path/to/dest")

    def test_genre_not_mapped(self):
        """Test when genre is not found in mapping."""
        genre_to_dest = {"Other Genre": "/path/to/dest"}
        result = organize_music.find_genre_destination("Test Genre", genre_to_dest)
        self.assertIsNone(result)

    def test_genre_subgenre_hierarchy_electro_house(self):
        """Test that Electro House maps to House via parent genre."""
        genre_to_dest = {"House": "/path/to/house"}
        result = organize_music.find_genre_destination("Electro House", genre_to_dest)
        self.assertEqual(result, "/path/to/house")

    def test_genre_subgenre_hierarchy_progressive_house(self):
        """Test that Progressive House maps to House via parent genre."""
        genre_to_dest = {"House": "/path/to/house"}
        result = organize_music.find_genre_destination("Progressive House", genre_to_dest)
        self.assertEqual(result, "/path/to/house")

    def test_genre_subgenre_hierarchy_techno(self):
        """Test that Deep Techno maps to Techno via parent genre."""
        genre_to_dest = {"Techno": "/path/to/techno"}
        result = organize_music.find_genre_destination("Deep Techno", genre_to_dest)
        self.assertEqual(result, "/path/to/techno")


class TestExtractParentGenre(unittest.TestCase):
    """Tests for _extract_parent_genre function."""

    def test_electro_house(self):
        self.assertEqual(organize_music._extract_parent_genre("Electro House"), "house")

    def test_progressive_house(self):
        self.assertEqual(organize_music._extract_parent_genre("Progressive House"), "house")

    def test_techno(self):
        self.assertEqual(organize_music._extract_parent_genre("Deep Techno"), "techno")

    def test_drum_n_bass(self):
        self.assertEqual(organize_music._extract_parent_genre("Drum and Bass"), "drum n bass")

    def test_trance(self):
        self.assertEqual(organize_music._extract_parent_genre("Progressive Trance"), "trance")

    def test_edm(self):
        self.assertEqual(organize_music._extract_parent_genre("EDM"), "edm")

    def test_dance(self):
        self.assertEqual(organize_music._extract_parent_genre("Dance"), "dance")

    def test_electronic(self):
        self.assertEqual(organize_music._extract_parent_genre("Electronic"), "electronic")

    def test_no_match(self):
        self.assertIsNone(organize_music._extract_parent_genre("Jazz"))

    def test_empty_string(self):
        self.assertIsNone(organize_music._extract_parent_genre(""))

    def test_none(self):
        self.assertIsNone(organize_music._extract_parent_genre(None))


class TestDetermineDestination(unittest.TestCase):
    """Tests for determine_destination function."""

    def test_label_mapping_used(self):
        """Test when label mapping is used."""
        label_to_dest = {"Test Label": "/path/to/label/dest"}
        genre_to_dest = {"Test Genre": "/path/to/genre/dest"}
        dest_dir, used_label, used_genre, detected_genre, detected_label = organize_music.determine_destination(
            "Test Label", "Test Genre", label_to_dest, genre_to_dest
        )
        self.assertEqual(dest_dir, "/path/to/label/dest")
        self.assertTrue(used_label)
        self.assertFalse(used_genre)
        self.assertEqual(detected_genre, "Test Genre")
        self.assertEqual(detected_label, "Test Label")

    def test_label_mapping_not_used_genre_used(self):
        """Test when label mapping is not used but genre mapping is used."""
        label_to_dest = {}  # No label mapping configured
        genre_to_dest = {"Test Genre": "/path/to/genre/dest"}
        dest_dir, used_label, used_genre, detected_genre, detected_label = organize_music.determine_destination(
            None, "Test Genre", label_to_dest, genre_to_dest
        )
        self.assertEqual(dest_dir, "/path/to/genre/dest")
        self.assertFalse(used_label)
        self.assertTrue(used_genre)
        self.assertEqual(detected_genre, "Test Genre")
        self.assertIsNone(detected_label)

    def test_label_mapping_exhausted_genre_fallback(self):
        """Test when label mapping is exhausted, genre is used as fallback."""
        label_to_dest = {"Other Label": "/some/other/dest"}  # "Test Label" is NOT in the mapping
        genre_to_dest = {"Test Genre": "/path/to/genre/dest"}
        dest_dir, used_label, used_genre, detected_genre, detected_label = organize_music.determine_destination(
            "Test Label", "Test Genre", label_to_dest, genre_to_dest
        )
        # Since label is not mapped, genre is used as fallback
        self.assertEqual(dest_dir, "/path/to/genre/dest")
        self.assertFalse(used_label)
        self.assertTrue(used_genre)
        self.assertEqual(detected_genre, "Test Genre")
        self.assertEqual(detected_label, "Test Label")

    def test_label_mapping_exhausted_no_label_no_label_mapping(self):
        """Test when there's no label and no label mapping configured, so we try genre mapping."""
        label_to_dest = {}  # No label mapping configured
        genre_to_dest = {"Test Genre": "/path/to/genre/dest"}
        dest_dir, used_label, used_genre, detected_genre, detected_label = organize_music.determine_destination(
            None, "Test Genre", label_to_dest, genre_to_dest
        )
        self.assertEqual(dest_dir, "/path/to/genre/dest")
        self.assertFalse(used_label)
        self.assertTrue(used_genre)
        self.assertEqual(detected_genre, "Test Genre")
        self.assertIsNone(detected_label)

    def test_no_label_no_genre(self):
        """Test when there's no label and no genre."""
        label_to_dest = {}
        genre_to_dest = {}
        dest_dir, used_label, used_genre, detected_genre, detected_label = organize_music.determine_destination(
            None, None, label_to_dest, genre_to_dest
        )
        self.assertIsNone(dest_dir)
        self.assertFalse(used_label)
        self.assertFalse(used_genre)
        self.assertIsNone(detected_genre)
        self.assertIsNone(detected_label)


class TestDetermineFailureReason(unittest.TestCase):
    """Tests for determine_failure_reason function."""

    def test_label_not_mapped(self):
        """Test when label is present but not mapped."""
        reason = organize_music.determine_failure_reason("Test Label", {"Other Label": "/dest"}, None)
        self.assertEqual(reason, "label_not_mapped")

    def test_label_missing(self):
        """Test when label mapping is configured but label is missing."""
        reason = organize_music.determine_failure_reason(None, {"Test Label": "/dest"}, None)
        self.assertEqual(reason, "label_missing")

    def test_genre_not_mapped(self):
        """Test when genre is present but not mapped."""
        reason = organize_music.determine_failure_reason(None, {}, "Test Genre")
        self.assertEqual(reason, "genre_not_mapped")

    def test_lookup_failed(self):
        """Test when both label and genre are missing."""
        reason = organize_music.determine_failure_reason(None, {}, None)
        self.assertEqual(reason, "lookup_failed")


class TestProcessFile(unittest.TestCase):
    """Tests for process_file function."""

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.lookup_label_online')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('subprocess.run')
    def test_file_processed_successfully(self, mock_subprocess, mock_exists, mock_failure_reason, mock_determine_dest,
                                         mock_genre_online, mock_genre_metadata, mock_label_online,
                                         mock_label_metadata):
        """Test when a file is successfully processed (would be moved)."""
        # Setup mocks for subprocess.run (artist, title, and genre metadata)
        def subprocess_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            # Check if this is the artist call
            if len(args) > 0 and isinstance(args[0], list) and any('artist' in arg for arg in args[0]):
                mock_result.stdout = "Test Artist\n"
            # Check if this is the title call
            elif len(args) > 0 and isinstance(args[0], list) and any('title' in arg for arg in args[0]):
                mock_result.stdout = "Test Title\n"
            # Check for genre metadata
            elif len(args) > 0 and isinstance(args[0], list) and any('genre' in arg for arg in args[0]):
                mock_result.stdout = ""  # No genre in metadata
            else:
                mock_result.stdout = ""
            return mock_result
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        # Setup mocks for other functions
        mock_label_metadata.return_value = None
        mock_label_online.return_value = "Test Label"
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "Test Genre"
        mock_determine_dest.return_value = ("/dest/path", True, False, "Test Genre", "Test Label")
        mock_exists.return_value = False  # Target file does not exist
        mock_failure_reason.return_value = "label_not_mapped"  # Should not be used if dest is found

        # Call the function
        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {"Test Genre": "/dest/path"}},
            dry_run=True
        )

        # Assertions
        self.assertEqual(result['action'], 'move')
        self.assertEqual(result['destination'], "/dest/path/test.mp3")
        self.assertEqual(result['label'], "Test Label")
        self.assertEqual(result['genre'], "Test Genre")

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.lookup_label_online')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('subprocess.run')
    def test_file_not_moved_due_to_target_exists(self, mock_subprocess, mock_exists, mock_failure_reason, mock_determine_dest,
                                                 mock_genre_online, mock_genre_metadata, mock_label_online,
                                                 mock_label_metadata):
        """Test when a file is not moved because target already exists."""
        # Setup mocks for subprocess.run (artist, title, and genre metadata)
        def subprocess_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            # Check if this is the artist call
            if len(args) > 0 and isinstance(args[0], list) and any('artist' in arg for arg in args[0]):
                mock_result.stdout = "Test Artist\n"
            # Check if this is the title call
            elif len(args) > 0 and isinstance(args[0], list) and any('title' in arg for arg in args[0]):
                mock_result.stdout = "Test Title\n"
            # Check for genre metadata
            elif len(args) > 0 and isinstance(args[0], list) and any('genre' in arg for arg in args[0]):
                mock_result.stdout = ""  # No genre in metadata
            else:
                mock_result.stdout = ""
            return mock_result
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        # Setup mocks
        mock_label_metadata.return_value = None
        mock_label_online.return_value = "Test Label"
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "Test Genre"
        mock_determine_dest.return_value = ("/dest/path", True, False, "Test Genre", "Test Label")
        mock_exists.return_value = True  # Target file exists
        mock_failure_reason.return_value = "target_exists"

        # Call the function
        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {"Test Genre": "/dest/path"}},
            dry_run=True
        )

        # Assertions
        self.assertEqual(result['action'], 'leave')
        self.assertEqual(result['reason'], 'target_exists')


if __name__ == '__main__':
    unittest.main()