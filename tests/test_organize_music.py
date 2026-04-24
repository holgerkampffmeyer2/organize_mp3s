#!/usr/bin/env python3
"""
Unit tests for the MP3/M4A organizer.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

try:
    import pytest
except ImportError:
    pytest = None

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

    def setUp(self):
        """Clear label cache before each test."""
        if hasattr(organize_music, '_label_cache'):
            organize_music._label_cache.clear()

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
        """Test when genre is found via MusicBrainz (iTunes and Bandcamp fail)."""
        organize_music._genre_cache.clear()
        organize_music._bandcamp_cache.clear()
        itunes_resp = MagicMock()
        itunes_resp.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 0
        }).encode()
        
        bandcamp_resp = MagicMock()
        bandcamp_resp.__enter__.return_value.read.return_value = '<html></html>'
        
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
            'release-group': {'tags': [{'name': 'electronic', 'count': 5}]}
        }).encode()

        mock_urlopen.side_effect = [itunes_resp, bandcamp_resp, mb_search_resp, mb_rg_resp, mb_tag_resp]

        result = organize_music.get_genre_online("Test Artist", "Test Title")
        self.assertEqual(result, "Electronic")
        self.assertEqual(mock_urlopen.call_count, 5)

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


class TestGetGenreFromBandcamp(unittest.TestCase):
    """Tests for get_genre_from_bandcamp function."""

    def setUp(self):
        """Clear Bandcamp cache before each test to ensure test isolation."""
        if hasattr(organize_music, '_bandcamp_cache'):
            organize_music._bandcamp_cache.clear()

    def test_parse_bandcamp_house_genre(self):
        """Test parsing House genre from Bandcamp HTML."""
        html = '<html><a class="tag">house</a><a class="tag">tech house</a></html>'
        genre, label = organize_music._parse_bandcamp_search_results(html, "Artist", "Title")
        self.assertEqual(genre, "House")

    def test_parse_bandcamp_techno_genre(self):
        """Test parsing Techno genre from Bandcamp HTML."""
        html = '<html><a class="tag">techno</a></html>'
        genre, label = organize_music._parse_bandcamp_search_results(html, "Artist", "Title")
        self.assertEqual(genre, "Techno")

    def test_parse_bandcamp_no_results(self):
        """Test parsing when no results."""
        html = '<html>No results</html>'
        genre, label = organize_music._parse_bandcamp_search_results(html, "Artist", "Title")
        self.assertIsNone(genre)
        self.assertIsNone(label)

    def test_parse_bandcamp_afro_house(self):
        """Test parsing Afro House genre."""
        html = '<html><a class="tag">afro house</a></html>'
        genre, label = organize_music._parse_bandcamp_search_results(html, "Artist", "Title")
        self.assertEqual(genre, "House")

    def test_parse_bandcamp_electronic_fallback(self):
        """Test parsing Electronic genre."""
        html = '<html><a class="tag">electronic</a></html>'
        genre, label = organize_music._parse_bandcamp_search_results(html, "Artist", "Title")
        self.assertEqual(genre, "Electronic")

    def test_bandcamp_cache(self):
        """Test that Bandcamp results are cached."""
        organize_music._bandcamp_cache["test:title"] = ("House", "Test Label")
        
        genre, label = organize_music.get_genre_from_bandcamp("Test", "Title")
        self.assertEqual(genre, "House")
        self.assertEqual(label, "Test Label")


class TestExtractParentGenreExtended(unittest.TestCase):
    """Additional tests for _extract_parent_genre with extended genres."""

    def test_afro_house(self):
        result = organize_music._extract_parent_genre("Afro House")
        self.assertEqual(result, "house")

    def test_melodic_house(self):
        result = organize_music._extract_parent_genre("Melodic House")
        self.assertEqual(result, "house")

    def test_organic_house(self):
        result = organize_music._extract_parent_genre("Organic House")
        self.assertEqual(result, "house")

    def test_ambient(self):
        result = organize_music._extract_parent_genre("Ambient")
        self.assertEqual(result, "ambient")

    def test_dubstep(self):
        result = organize_music._extract_parent_genre("Dubstep")
        self.assertEqual(result, "dubstep")

    def test_breakbeat(self):
        result = organize_music._extract_parent_genre("Breakbeat")
        self.assertEqual(result, "breakbeat")

    def test_experimental(self):
        result = organize_music._extract_parent_genre("Experimental")
        self.assertEqual(result, "experimental")


class TestLookupLabelOnlineBandcamp(unittest.TestCase):
    """Tests for lookup_label_online with Bandcamp fallback."""

    def setUp(self):
        """Clear label cache before each test."""
        if hasattr(organize_music, '_label_cache'):
            organize_music._label_cache.clear()

    @patch('organize_music.get_genre_from_bandcamp')
    @patch('urllib.request.urlopen')
    def test_label_found_on_itunes(self, mock_urlopen, mock_bandcamp):
        """Test label found via iTunes."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'resultCount': 1,
            'results': [{'label': 'Test Label'}]
        }).encode()
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        result = organize_music.lookup_label_online("Artist", "Title")
        self.assertEqual(result, "Test Label")
        mock_bandcamp.assert_not_called()

    @patch('organize_music.get_genre_from_bandcamp')
    @patch('urllib.request.urlopen')
    def test_label_fallback_to_bandcamp(self, mock_urlopen, mock_bandcamp):
        """Test label fallback to Bandcamp when iTunes fails."""
        mock_urlopen.side_effect = Exception("Network error")
        mock_bandcamp.return_value = (None, "Feather Records")

        result = organize_music.lookup_label_online("Artist", "Title")
        self.assertEqual(result, "Feather Records")


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


class TestNormalizeGenre(unittest.TestCase):
    """Tests for _normalize_genre function."""

    def test_drum_and_bass_normalization(self):
        result = organize_music._normalize_genre("drum and bass")
        self.assertEqual(result, "DRUM N BASS")

    def test_drum_amp_bass_normalization(self):
        result = organize_music._normalize_genre("drum & bass")
        self.assertEqual(result, "DRUM N BASS")

    def test_edm_normalization(self):
        result = organize_music._normalize_genre("electronic dance music")
        self.assertEqual(result, "EDM")

    def test_idm_normalization(self):
        result = organize_music._normalize_genre("intelligent dance music")
        self.assertEqual(result, "IDM")

    def test_uk_garage_normalization(self):
        result = organize_music._normalize_genre("uk garage")
        self.assertEqual(result, "UKG")

    def test_title_case_for_regular_genre(self):
        result = organize_music._normalize_genre("jazz")
        self.assertEqual(result, "Jazz")

    def test_empty_string(self):
        result = organize_music._normalize_genre("")
        self.assertEqual(result, "")

    def test_none(self):
        result = organize_music._normalize_genre(None)
        self.assertEqual(result, "")

    def test_already_normalized(self):
        result = organize_music._normalize_genre("Techno")
        self.assertEqual(result, "Techno")


class TestIsElectronicGenre(unittest.TestCase):
    """Tests for _is_electronic_genre function."""

    def test_techno_is_electronic(self):
        self.assertTrue(organize_music._is_electronic_genre("Techno"))

    def test_house_is_electronic(self):
        self.assertTrue(organize_music._is_electronic_genre("House"))

    def test_electronic_is_electronic(self):
        self.assertTrue(organize_music._is_electronic_genre("Electronic"))

    def test_drum_and_bass_is_electronic(self):
        self.assertTrue(organize_music._is_electronic_genre("Drum and Bass"))

    def test_edm_is_electronic(self):
        self.assertTrue(organize_music._is_electronic_genre("EDM"))

    def test_electro_house_is_electronic(self):
        self.assertTrue(organize_music._is_electronic_genre("Electro House"))

    def test_subgenre_contains_electronic_keyword(self):
        self.assertTrue(organize_music._is_electronic_genre("Deep House"))

    def test_jazz_is_not_electronic(self):
        self.assertFalse(organize_music._is_electronic_genre("Jazz"))

    def test_rock_is_not_electronic(self):
        self.assertFalse(organize_music._is_electronic_genre("Rock"))

    def test_pop_is_not_electronic(self):
        self.assertFalse(organize_music._is_electronic_genre("Pop"))

    def test_empty_string(self):
        self.assertFalse(organize_music._is_electronic_genre(""))

    def test_none(self):
        self.assertFalse(organize_music._is_electronic_genre(None))

    def test_case_insensitive(self):
        self.assertTrue(organize_music._is_electronic_genre("TECHNO"))

    def test_label_indicator_short_genre(self):
        self.assertTrue(organize_music._is_electronic_genre("Trax Records"))


class TestExtractMetadataTag(unittest.TestCase):
    """Tests for _extract_metadata_tag function."""

    @patch('subprocess.run')
    def test_tag_found(self, mock_run):
        """Test when tag is found in metadata."""
        mock_run.return_value.stdout = "Test Value\n"
        mock_run.return_value.returncode = 0

        result = organize_music._extract_metadata_tag(Path("test.mp3"), "artist")
        self.assertEqual(result, "Test Value")

    @patch('subprocess.run')
    def test_tag_not_found(self, mock_run):
        """Test when tag is not found."""
        mock_run.return_value.stdout = ""
        mock_run.return_value.returncode = 1

        result = organize_music._extract_metadata_tag(Path("test.mp3"), "artist")
        self.assertIsNone(result)

    @patch('subprocess.run')
    def test_tag_whitespace_only(self, mock_run):
        """Test when tag is whitespace only."""
        mock_run.return_value.stdout = "   \n"
        mock_run.return_value.returncode = 0

        result = organize_music._extract_metadata_tag(Path("test.mp3"), "artist")
        self.assertIsNone(result)

    @patch('subprocess.run')
    def test_timeout_expired(self, mock_run):
        """Test when subprocess times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 1)

        result = organize_music._extract_metadata_tag(Path("test.mp3"), "artist")
        self.assertIsNone(result)

    @patch('subprocess.run')
    def test_called_process_error(self, mock_run):
        """Test when subprocess raises CalledProcessError."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

        result = organize_music._extract_metadata_tag(Path("test.mp3"), "artist")
        self.assertIsNone(result)

    @patch('subprocess.run')
    def test_file_not_found(self, mock_run):
        """Test when ffprobe is not found."""
        mock_run.side_effect = FileNotFoundError("ffprobe")

        result = organize_music._extract_metadata_tag(Path("test.mp3"), "artist")
        self.assertIsNone(result)


class TestFindGenreDestinationEdgeCases(unittest.TestCase):
    """Additional edge case tests for find_genre_destination."""

    def test_empty_genre_to_dest(self):
        """Test with empty genre mapping."""
        result = organize_music.find_genre_destination("Test Genre", {})
        self.assertIsNone(result)

    def test_whitespace_only_genre(self):
        """Test with whitespace-only genre."""
        genre_to_dest = {"Test Genre": "/path/to/dest"}
        result = organize_music.find_genre_destination("   ", genre_to_dest)
        self.assertIsNone(result)

    def test_genre_not_in_mapping(self):
        """Test when genre is not in mapping."""
        genre_to_dest = {"Other Genre": "/path/to/dest"}
        result = organize_music.find_genre_destination("Test Genre", genre_to_dest)
        self.assertIsNone(result)

    def test_none_genre(self):
        """Test with None genre."""
        genre_to_dest = {"Test Genre": "/path/to/dest"}
        result = organize_music.find_genre_destination(None, genre_to_dest)
        self.assertIsNone(result)

    def test_subgenre_fallback_chain(self):
        """Test that subgenre hierarchy chain works."""
        genre_to_dest = {"House": "/path/to/house"}
        result = organize_music.find_genre_destination("Deep Electro House", genre_to_dest)
        self.assertEqual(result, "/path/to/house")

    def test_comma_separated_partial_match(self):
        """Test comma-separated key matching."""
        genre_to_dest = {"House, Techno": "/path/to/edm"}
        result = organize_music.find_genre_destination("Techno", genre_to_dest)
        self.assertEqual(result, "/path/to/edm")


class TestDetermineFailureReasonEdgeCases(unittest.TestCase):
    """Additional edge case tests for determine_failure_reason."""

    def test_label_mapped_but_not_found(self):
        """Test when label exists but not in mapping."""
        result = organize_music.determine_failure_reason("Unknown Label", {"Other Label": "/dest"}, None)
        self.assertEqual(result, "label_not_mapped")

    def test_no_label_mapping_configured_genre_available(self):
        """Test when no label mapping but genre available."""
        result = organize_music.determine_failure_reason(None, {}, "Test Genre")
        self.assertEqual(result, "genre_not_mapped")

    def test_label_mapping_empty_but_label_exists(self):
        """Test when label mapping is empty dict but label exists."""
        result = organize_music.determine_failure_reason("Some Label", {}, "Test Genre")
        self.assertEqual(result, "label_not_mapped")  # No label mapping, so can't use label

    def test_label_and_mapping_exist_but_label_not_mapped(self):
        """Test when label and mapping exist but label not in mapping."""
        result = organize_music.determine_failure_reason("Unmapped Label", {"Mapped Label": "/dest"}, None)
        self.assertEqual(result, "label_not_mapped")


class TestProcessFileEdgeCases(unittest.TestCase):
    """Additional edge case tests for process_file."""

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.lookup_label_online')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    def test_missing_artist(self, mock_extract, mock_exists, mock_failure_reason, mock_determine_dest,
                            mock_genre_online, mock_genre_metadata, mock_label_online, mock_label_metadata):
        """Test when artist is missing from metadata."""
        mock_extract.return_value = {'artist': None, 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {}, "genre_map": {}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'leave')
        self.assertEqual(result['reason'], 'missing_metadata_artist')

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.lookup_label_online')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    def test_missing_title(self, mock_extract, mock_exists, mock_failure_reason, mock_determine_dest,
                          mock_genre_online, mock_genre_metadata, mock_label_online, mock_label_metadata):
        """Test when title is missing from metadata."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': None, 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {}, "genre_map": {}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'leave')
        self.assertEqual(result['reason'], 'missing_metadata_title')

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.lookup_label_online')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    def test_config_without_label_map(self, mock_extract, mock_exists, mock_failure_reason, mock_determine_dest,
                                     mock_genre_online, mock_genre_metadata, mock_label_online, mock_label_metadata):
        """Test when config does not contain label_map."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_determine_dest.return_value = (None, False, False, None, None)
        mock_failure_reason.return_value = "lookup_failed"

        result = organize_music.process_file(
            Path("test.mp3"),
            {"genre_map": {}},  # No label_map
            dry_run=True
        )

        # Should not error, just continue without label mapping
        self.assertIn(result['action'], ['move', 'leave'])

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.lookup_label_online')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    def test_config_without_genre_map(self, mock_extract, mock_exists, mock_failure_reason, mock_determine_dest,
                                      mock_genre_online, mock_genre_metadata, mock_label_online, mock_label_metadata):
        """Test when config does not contain genre_map."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_determine_dest.return_value = (None, False, False, None, None)
        mock_failure_reason.return_value = "lookup_failed"

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {}},  # No genre_map
            dry_run=True
        )

        # Should not error, just continue without genre mapping
        self.assertIn(result['action'], ['move', 'leave'])

    @patch('organize_music._extract_all_metadata')
    def test_processing_exception(self, mock_extract):
        """Test when an exception occurs during processing."""
        mock_extract.side_effect = Exception("Unexpected error")

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {}, "genre_map": {}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'leave')
        self.assertIn('processing_error', result['reason'])

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.lookup_label_online')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.find_genre_destination')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    def test_label_from_metadata_used(self, mock_extract, mock_exists, mock_failure_reason, mock_determine_dest,
                                      mock_find_genre, mock_genre_online, mock_genre_metadata, mock_label_online, mock_label_metadata):
        """Test when label is found in metadata."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': 'Test Genre',
                                      'date': None, 'label': 'Test Label', 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_label_metadata.return_value = "Test Label"
        mock_label_online.return_value = None  # Should not be called
        mock_genre_metadata.return_value = "Test Genre"
        mock_find_genre.return_value = "/dest/path"  # Genre is mapped, so online lookup won't be called
        mock_genre_online.return_value = None  # Should not be called
        mock_determine_dest.return_value = ("/dest/path", True, False, "Test Genre", "Test Label")
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {}},
            dry_run=True
        )

        self.assertEqual(result['label'], "Test Label")
        mock_label_online.assert_not_called()  # Online lookup skipped since metadata found
        mock_genre_online.assert_not_called()  # Online lookup skipped since metadata found


class TestProcessFile(unittest.TestCase):
    """Tests for process_file function."""

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    @patch('organize_music._lookup_itunes_all_metadata')
    def test_file_processed_successfully(self, mock_itunes, mock_extract, mock_exists, mock_failure_reason, mock_determine_dest,
                                          mock_genre_online, mock_genre_metadata, mock_label_metadata):
        """Test when a file is successfully processed (would be moved)."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_itunes.return_value = {'label': 'Test Label', 'genre': 'Test Genre', 'album': None,
                                     'year': None, 'track_number': None, 'artist': None, 'title': None}
        
        mock_label_metadata.return_value = None
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "Test Genre"
        mock_determine_dest.return_value = ("/dest/path", True, False, "Test Genre", "Test Label")
        mock_exists.return_value = False
        mock_failure_reason.return_value = "label_not_mapped"

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {"Test Genre": "/dest/path"}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'move')
        self.assertEqual(result['destination'], "/dest/path/test.mp3")
        self.assertEqual(result['label'], "Test Label")
        self.assertEqual(result['genre'], "Test Genre")

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    @patch('organize_music._lookup_itunes_all_metadata')
    def test_file_not_moved_due_to_target_exists(self, mock_itunes, mock_extract, mock_exists, mock_failure_reason, mock_determine_dest,
                                                  mock_genre_online, mock_genre_metadata, mock_label_metadata):
        """Test when a file is not moved because target already exists."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_itunes.return_value = {'label': 'Test Label', 'genre': 'Test Genre', 'album': None,
                                     'year': None, 'track_number': None, 'artist': None, 'title': None}
        
        mock_label_metadata.return_value = None
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "Test Genre"
        mock_determine_dest.return_value = ("/dest/path", True, False, "Test Genre", "Test Label")
        mock_exists.return_value = True
        mock_failure_reason.return_value = "target_exists"

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {"Test Genre": "/dest/path"}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'leave')
        self.assertEqual(result['reason'], 'target_exists')


class TestDetermineFailureReason(unittest.TestCase):
    """Tests for determine_failure_reason function."""

    def test_label_not_mapped(self):
        """Test when label is present but not mapped."""
        reason = organize_music.determine_failure_reason("Test Label", {"Other Label": "/dest"}, None)
        self.assertEqual(reason, "label_not_mapped")

    def test_label_missing(self):
        """Test when label mapping is configured but label is missing, and no genre."""
        reason = organize_music.determine_failure_reason(None, {"Test Label": "/dest"}, None)
        self.assertEqual(reason, "lookup_failed")

    def test_genre_not_mapped(self):
        """Test when genre is present but not mapped."""
        reason = organize_music.determine_failure_reason(None, {}, "Test Genre")
        self.assertEqual(reason, "genre_not_mapped")

    def test_lookup_failed(self):
        """Test when both label and genre are missing."""
        reason = organize_music.determine_failure_reason(None, {}, None)
        self.assertEqual(reason, "lookup_failed")


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
        label_to_dest = {}
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
        label_to_dest = {"Other Label": "/some/other/dest"}
        genre_to_dest = {"Test Genre": "/path/to/genre/dest"}
        dest_dir, used_label, used_genre, detected_genre, detected_label = organize_music.determine_destination(
            "Test Label", "Test Genre", label_to_dest, genre_to_dest
        )
        self.assertEqual(dest_dir, "/path/to/genre/dest")
        self.assertFalse(used_label)
        self.assertTrue(used_genre)
        self.assertEqual(detected_genre, "Test Genre")
        self.assertEqual(detected_label, "Test Label")

    def test_label_mapping_exhausted_no_label_no_label_mapping(self):
        """Test when there's no label and no label mapping configured."""
        label_to_dest = {}
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


class TestProcessFile(unittest.TestCase):
    """Tests for process_file function."""

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    @patch('organize_music._lookup_itunes_all_metadata')
    def test_file_processed_successfully(self, mock_itunes, mock_extract, mock_exists, mock_failure_reason, mock_determine_dest,
                                          mock_genre_online, mock_genre_metadata, mock_label_metadata):
        """Test when a file is successfully processed (would be moved)."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_itunes.return_value = {'label': 'Test Label', 'genre': 'Test Genre', 'album': None,
                                     'year': None, 'track_number': None, 'artist': None, 'title': None}
        
        mock_label_metadata.return_value = None
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "Test Genre"
        mock_determine_dest.return_value = ("/dest/path", True, False, "Test Genre", "Test Label")
        mock_exists.return_value = False  # Target file does not exist
        mock_failure_reason.return_value = "label_not_mapped"  # Should not be used if dest is found

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {"Test Genre": "/dest/path"}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'move')
        self.assertEqual(result['destination'], "/dest/path/test.mp3")
        self.assertEqual(result['label'], "Test Label")
        self.assertEqual(result['genre'], "Test Genre")

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('organize_music.determine_failure_reason')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    @patch('organize_music._lookup_itunes_all_metadata')
    def test_file_not_moved_due_to_target_exists(self, mock_itunes, mock_extract, mock_exists, mock_failure_reason, mock_determine_dest,
                                                  mock_genre_online, mock_genre_metadata, mock_label_metadata):
        """Test when a file is not moved because target already exists."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_itunes.return_value = {'label': 'Test Label', 'genre': 'Test Genre', 'album': None,
                                     'year': None, 'track_number': None, 'artist': None, 'title': None}
        
        mock_label_metadata.return_value = None
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "Test Genre"
        mock_determine_dest.return_value = ("/dest/path", True, False, "Test Genre", "Test Label")
        mock_exists.return_value = True  # Target file exists
        mock_failure_reason.return_value = "target_exists"

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {"Test Genre": "/dest/path"}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'leave')
        self.assertEqual(result['reason'], 'target_exists')


class TestFindFuzzyGenre(unittest.TestCase):
    """Tests for fuzzy genre matching."""

    def test_synonym_hip_hop(self):
        """Test genre synonym matching for hip hop."""
        genre_map = {"Hip-Hop/Rap": "House", "Electronic": "House"}
        result = organize_music._find_fuzzy_genre("hip hop", genre_map)
        self.assertEqual(result, "House")

    def test_synonym_dnb(self):
        """Test genre synonym matching for drum and bass."""
        genre_map = {"Drum n Bass": "DnB"}
        result = organize_music._find_fuzzy_genre("dnb", genre_map)
        self.assertEqual(result, "DnB")

    def test_synonym_liquid(self):
        """Test genre synonym matching for liquid."""
        genre_map = {"Drum n Bass": "DnB"}
        result = organize_music._find_fuzzy_genre("liquid", genre_map)
        self.assertEqual(result, "DnB")

    def test_fuzzy_match_techno(self):
        """Test fuzzy matching for similar genre names."""
        genre_map = {"Techno": "House", "Tech House": "House"}
        result = organize_music._find_fuzzy_genre("Techno ", genre_map)
        self.assertEqual(result, "House")

    def test_no_match_below_threshold(self):
        """Test that low similarity genres don't match."""
        genre_map = {"House": "House", "Techno": "House"}
        result = organize_music._find_fuzzy_genre("Jazz", genre_map, threshold=0.75)
        self.assertIsNone(result)

    def test_empty_input(self):
        """Test empty genre input."""
        result = organize_music._find_fuzzy_genre("", {"House": "House"})
        self.assertIsNone(result)

    def test_empty_map(self):
        """Test empty genre map."""
        result = organize_music._find_fuzzy_genre("House", {})
        self.assertIsNone(result)

    def test_exact_match_preferred(self):
        """Test that exact matches are preferred over fuzzy."""
        genre_map = {"House": "House"}
        result = organize_music._find_fuzzy_genre("House", genre_map)
        self.assertEqual(result, "House")

    def test_fuzzy_house_variant(self):
        """Test fuzzy matching for 'progressive house'."""
        genre_map = {"House": "House", "Progressive House": "House"}
        result = organize_music._find_fuzzy_genre("prog house", genre_map)
        self.assertEqual(result, "House")

    def test_afro_house_synonym(self):
        """Test afro house synonym."""
        genre_map = {"House": "House"}
        result = organize_music._find_fuzzy_genre("afro house", genre_map)
        self.assertEqual(result, "House")


class TestGenreDestinationWithFuzzy(unittest.TestCase):
    """Test find_genre_destination with fuzzy matching enabled."""

    def test_fuzzy_match_integration(self):
        """Test that fuzzy matching works within find_genre_destination."""
        genre_map = {"Hip-Hop/Rap": "House", "House": "House"}
        
        # Should find via fuzzy matching (synonym -> exact match)
        result = organize_music.find_genre_destination("hip hop", genre_map)
        self.assertEqual(result, "House")

    def test_synonym_fallback_integration(self):
        """Test that synonyms work within find_genre_destination."""
        genre_map = {"Electronic": "House"}
        
        result = organize_music.find_genre_destination("edm", genre_map)
        self.assertEqual(result, "House")


class TestWriteMetadataTag(unittest.TestCase):
    """Tests for _write_metadata_tag function."""

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.replace')
    def test_write_tag_success(self, mock_replace, mock_exists, mock_run):
        """Test successful metadata tag write."""
        mock_run.return_value.returncode = 0
        mock_exists.return_value = False

        result = organize_music._write_metadata_tag(Path("test.mp3"), "genre", "House")
        self.assertTrue(result)
        mock_replace.assert_called_once()

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_write_tag_failure_ffmpeg_error(self, mock_exists, mock_run):
        """Test when ffmpeg fails to write tag."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error message"
        mock_exists.return_value = False

        result = organize_music._write_metadata_tag(Path("test.mp3"), "genre", "House")
        self.assertFalse(result)

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_write_tag_cleans_temp_file_on_failure(self, mock_remove, mock_exists, mock_run):
        """Test that temp file is cleaned up on failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error"
        mock_exists.side_effect = [True, False]  # Temp file exists

        result = organize_music._write_metadata_tag(Path("test.mp3"), "genre", "House")
        self.assertFalse(result)
        mock_remove.assert_called_once()

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_write_tag_timeout(self, mock_exists, mock_run):
        """Test when subprocess times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 1)
        mock_exists.return_value = False

        result = organize_music._write_metadata_tag(Path("test.mp3"), "genre", "House")
        self.assertFalse(result)

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.replace')
    def test_write_tag_special_characters(self, mock_replace, mock_exists, mock_run):
        """Test writing tag with special characters."""
        mock_run.return_value.returncode = 0
        mock_exists.return_value = False

        result = organize_music._write_metadata_tag(Path("test.mp3"), "title", "Test's Title & More")
        self.assertTrue(result)


class TestGetAdditionalMetadataOnline(unittest.TestCase):
    """Tests for get_additional_metadata_online function."""

    @patch('urllib.request.urlopen')
    def test_metadata_found(self, mock_urlopen):
        """Test when additional metadata is found."""
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 1,
            'results': [{
                'collectionName': 'Test Album',
                'trackNumber': 5,
                'releaseDate': '2024-03-15T00:00:00Z'
            }]
        }).encode()
        mock_urlopen.return_value = mock_cm

        result = organize_music.get_additional_metadata_online("Artist", "Title")
        
        self.assertEqual(result['album'], "Test Album")
        self.assertEqual(result['track_number'], 5)
        self.assertEqual(result['year'], "2024")

    @patch('urllib.request.urlopen')
    def test_no_results(self, mock_urlopen):
        """Test when no results found."""
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 0
        }).encode()
        mock_urlopen.return_value = mock_cm

        result = organize_music.get_additional_metadata_online("Artist", "Title")
        
        self.assertIsNone(result['album'])
        self.assertIsNone(result['track_number'])
        self.assertIsNone(result['year'])

    @patch('urllib.request.urlopen')
    def test_partial_results(self, mock_urlopen):
        """Test when only some fields are available."""
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 1,
            'results': [{
                'collectionName': 'Test Album'
                # No trackNumber, no releaseDate
            }]
        }).encode()
        mock_urlopen.return_value = mock_cm

        result = organize_music.get_additional_metadata_online("Artist", "Title")
        
        self.assertEqual(result['album'], "Test Album")
        self.assertIsNone(result['track_number'])
        self.assertIsNone(result['year'])

    @patch('urllib.request.urlopen')
    def test_exception_handling(self, mock_urlopen):
        """Test when an exception occurs."""
        mock_urlopen.side_effect = Exception("Network error")

        result = organize_music.get_additional_metadata_online("Artist", "Title")
        
        self.assertIsNone(result['album'])
        self.assertIsNone(result['track_number'])
        self.assertIsNone(result['year'])

    @patch('urllib.request.urlopen')
    def test_short_release_date(self, mock_urlopen):
        """Test when release date format is short."""
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = json.dumps({
            'resultCount': 1,
            'results': [{
                'releaseDate': '2024'
            }]
        }).encode()
        mock_urlopen.return_value = mock_cm

        result = organize_music.get_additional_metadata_online("Artist", "Title")
        
        self.assertEqual(result['year'], "2024")


class TestProcessFileMetadataEnrichment(unittest.TestCase):
    """Tests for metadata enrichment in process_file."""

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music._write_metadata_tag')
    @patch('organize_music.determine_destination')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    @patch('organize_music._lookup_itunes_all_metadata')
    def test_enrich_metadata_label_and_genre(
        self, mock_itunes, mock_extract, mock_exists, mock_determine, mock_write,
        mock_genre_online, mock_genre_metadata, mock_label_metadata
    ):
        """Test enriching label and genre when missing in metadata."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_itunes.return_value = {'label': 'Test Label', 'genre': 'House', 'album': 'Test Album',
                                     'year': '2024', 'track_number': 1, 'artist': None, 'title': None}

        mock_label_metadata.return_value = None
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "House"
        mock_write.return_value = True
        mock_determine.return_value = ("/dest/path", True, False, "House", "Test Label")
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {"House": "/dest/path"}, "enrich_metadata": True},
            dry_run=False,  # dry_run=False to allow enrichment
            enrich_metadata=True
        )

        self.assertEqual(set(result['enriched_tags']), {'label', 'genre', 'album', 'year'})
        self.assertEqual(mock_write.call_count, 4)

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music._write_metadata_tag')
    @patch('organize_music.determine_destination')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    def test_no_enrichment_when_metadata_exists(
        self, mock_extract, mock_exists, mock_determine, mock_write,
        mock_genre_online, mock_genre_metadata, mock_label_metadata
    ):
        """Test no enrichment when metadata already exists."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': 'Existing Album', 'genre': 'Existing Genre',
                                      'date': '2020', 'label': 'Existing Label', 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}

        mock_label_metadata.return_value = "Existing Label"
        mock_genre_metadata.return_value = "Existing Genre"
        mock_genre_online.return_value = "Online Genre"
        mock_determine.return_value = ("/dest/path", True, False, "Existing Genre", "Existing Label")
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Existing Label": "/dest/path"}, "genre_map": {"Existing Genre": "/dest/path"}, "enrich_metadata": True},
            dry_run=True,
            enrich_metadata=True
        )

        self.assertEqual(result['enriched_tags'], [])
        mock_write.assert_not_called()

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music._write_metadata_tag')
    @patch('organize_music.determine_destination')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    def test_enrichment_disabled_by_default(
        self, mock_extract, mock_exists, mock_determine, mock_write,
        mock_genre_online, mock_genre_metadata, mock_label_metadata
    ):
        """Test no enrichment when not enabled."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}

        mock_label_metadata.return_value = None
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "House"
        mock_determine.return_value = ("/dest/path", True, False, "House", "Test Label")
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {"House": "/dest/path"}},
            dry_run=True,
            enrich_metadata=False  # Disabled via CLI
        )

        self.assertEqual(result['enriched_tags'], [])
        mock_write.assert_not_called()

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.get_additional_metadata_online')
    @patch('organize_music._write_metadata_tag')
    @patch('organize_music.determine_destination')
    @patch('pathlib.Path.exists')
    @patch('organize_music._extract_all_metadata')
    @patch('organize_music._lookup_itunes_all_metadata')
    def test_enrichment_enabled_via_config(
        self, mock_itunes, mock_extract, mock_exists, mock_determine, mock_write,
        mock_additional, mock_genre_online, mock_genre_metadata,
        mock_label_metadata
    ):
        """Test enrichment enabled via config.json."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_itunes.return_value = {'label': 'Test Label', 'genre': 'House', 'album': 'Test Album',
                                     'year': '2024', 'track_number': 1, 'artist': None, 'title': None}

        mock_label_metadata.return_value = None
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "House"
        mock_additional.return_value = {'album': 'Test Album', 'year': '2024', 'track_number': 1}
        mock_write.return_value = True
        mock_determine.return_value = ("/dest/path", True, False, "House", "Test Label")
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {
                "label_map": {"Test Label": "/dest/path"},
                "genre_map": {"House": "/dest/path"},
                "enrich_metadata": True
            },
            dry_run=False,
            enrich_metadata=False  # CLI flag not needed since config enables it
        )

        self.assertEqual(set(result['enriched_tags']), {'label', 'genre', 'album', 'year'})
        self.assertEqual(mock_write.call_count, 4)

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.lookup_label_online')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music._write_metadata_tag')
    @patch('organize_music.determine_destination')
    @patch('pathlib.Path.exists')
    @patch('subprocess.run')
    def test_no_enrichment_when_metadata_exists_with_subprocess(
        self, mock_subprocess, mock_exists, mock_determine, mock_write,
        mock_genre_online, mock_genre_metadata, mock_label_online, mock_label_metadata
    ):
        """Test no enrichment when metadata already exists (using subprocess mock)."""
        def subprocess_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            if any('artist' in arg for arg in args[0]):
                mock_result.stdout = "Test Artist\n"
            elif any('title' in arg for arg in args[0]):
                mock_result.stdout = "Test Title\n"
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        mock_label_metadata.return_value = "Existing Label"
        mock_label_online.return_value = "Online Label"
        mock_genre_metadata.return_value = "Existing Genre"
        mock_genre_online.return_value = "Online Genre"
        mock_determine.return_value = ("/dest/path", True, False, "Existing Genre", "Existing Label")
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Existing Label": "/dest/path"}, "genre_map": {"Existing Genre": "/dest/path"}, "enrich_metadata": True},
            dry_run=True,
            enrich_metadata=True
        )

        self.assertEqual(result['enriched_tags'], [])
        mock_write.assert_not_called()

    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.lookup_label_online')
    @patch('organize_music.get_genre_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music._write_metadata_tag')
    @patch('organize_music.determine_destination')
    @patch('pathlib.Path.exists')
    @patch('subprocess.run')
    def test_enrichment_disabled_by_default_with_subprocess(
        self, mock_subprocess, mock_exists, mock_determine, mock_write,
        mock_genre_online, mock_genre_metadata, mock_label_online, mock_label_metadata
    ):
        """Test no enrichment when not enabled (using subprocess mock)."""
        def subprocess_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            if any('artist' in arg for arg in args[0]):
                mock_result.stdout = "Test Artist\n"
            elif any('title' in arg for arg in args[0]):
                mock_result.stdout = "Test Title\n"
            return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        mock_label_metadata.return_value = None
        mock_label_online.return_value = None
        mock_genre_metadata.return_value = None
        mock_genre_online.return_value = "House"
        mock_determine.return_value = ("/dest/path", True, False, "House", None)
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/dest/path"}, "genre_map": {"House": "/dest/path"}},
            dry_run=True,
            enrich_metadata=False
        )

        self.assertEqual(result['enriched_tags'], [])
        mock_write.assert_not_called()


class TestGenreFallbackWhenNoLabel(unittest.TestCase):
    """Tests for genre fallback when no label is found."""

    @patch('organize_music._extract_all_metadata')
    @patch('organize_music._lookup_itunes_all_metadata')
    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('pathlib.Path.exists')
    def test_genre_fallback_when_label_missing(
        self, mock_exists, mock_determine, mock_genre_online,
        mock_label_metadata, mock_itunes, mock_extract
    ):
        """Test that genre is used when label is not available."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': 'House',
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_itunes.return_value = {'label': None, 'genre': 'House', 'album': None,
                                     'year': None, 'track_number': None, 'artist': None, 'title': None}

        mock_label_metadata.return_value = None
        mock_genre_online.return_value = None
        mock_determine.return_value = ("/dest/path", False, True, "House", None)
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Some Label": "/dest/path"}, "genre_map": {"House": "/dest/path"}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'move')
        self.assertEqual(result['destination'], '/dest/path/test.mp3')
        self.assertEqual(result['genre'], 'House')
        mock_determine.assert_called_once()

    @patch('organize_music._extract_all_metadata')
    @patch('organize_music._lookup_itunes_all_metadata')
    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('pathlib.Path.exists')
    def test_genre_fallback_with_online_lookup(
        self, mock_exists, mock_determine, mock_genre_online,
        mock_label_metadata, mock_itunes, mock_extract
    ):
        """Test genre fallback with online genre lookup when metadata genre not mapped."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': None, 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_itunes.return_value = {'label': None, 'genre': None, 'album': None,
                                     'year': None, 'track_number': None, 'artist': None, 'title': None}

        mock_label_metadata.return_value = None
        mock_genre_online.return_value = "House"
        mock_determine.return_value = ("/dest/path", False, True, "House", None)
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Some Label": "/dest/path"}, "genre_map": {"House": "/dest/path"}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'move')
        self.assertEqual(result['genre'], 'House')

    @patch('organize_music._extract_all_metadata')
    @patch('organize_music._lookup_itunes_all_metadata')
    @patch('organize_music.get_label_from_metadata')
    @patch('organize_music.get_genre_online')
    @patch('organize_music.determine_destination')
    @patch('pathlib.Path.exists')
    def test_label_priority_over_genre(
        self, mock_exists, mock_determine, mock_genre_online,
        mock_label_metadata, mock_itunes, mock_extract
    ):
        """Test that label is used when available, even if genre also available."""
        mock_extract.return_value = {'artist': 'Test Artist', 'title': 'Test Title', 'album': None, 'genre': None,
                                      'date': None, 'label': 'Test Label', 'Label': None, 'TPUB': None,
                                      'publisher': None, 'track': None}
        mock_itunes.return_value = {'label': 'Test Label', 'genre': 'House', 'album': None,
                                     'year': None, 'track_number': None, 'artist': None, 'title': None}

        mock_label_metadata.return_value = "Test Label"
        mock_genre_online.return_value = "House"
        mock_determine.return_value = ("/label/dest/path", True, False, "House", "Test Label")
        mock_exists.return_value = False

        result = organize_music.process_file(
            Path("test.mp3"),
            {"label_map": {"Test Label": "/label/dest/path"}, "genre_map": {"House": "/genre/dest/path"}},
            dry_run=True
        )

        self.assertEqual(result['action'], 'move')
        self.assertEqual(result['destination'], '/label/dest/path/test.mp3')
        self.assertEqual(result['label'], 'Test Label')


class TestDetermineFailureReasonNewLogic(unittest.TestCase):
    """Tests for determine_failure_reason with the new logic."""

    def test_label_map_configured_but_no_label_genre_mapped(self):
        """Test when label_map is configured but no label found, and genre is mapped."""
        reason = organize_music.determine_failure_reason(None, {"Test Label": "/dest"}, "House")
        self.assertEqual(reason, "genre_not_mapped")

    def test_label_map_configured_but_no_label_genre_not_mapped(self):
        """Test when label_map is configured, no label, and genre not mapped."""
        reason = organize_music.determine_failure_reason(None, {"Test Label": "/dest"}, "Unknown Genre")
        self.assertEqual(reason, "genre_not_mapped")

    def test_label_map_configured_no_label_no_genre(self):
        """Test when label_map is configured but no label and no genre."""
        reason = organize_music.determine_failure_reason(None, {"Test Label": "/dest"}, None)
        self.assertEqual(reason, "lookup_failed")


class TestSubstringMatch(unittest.TestCase):
    """Tests for _check_substring_match function."""

    def test_exact_match(self):
        """Test when metadata title exactly matches filename title."""
        is_match, score = organize_music._check_substring_match("Locked In", "Locked In")
        self.assertTrue(is_match)
        self.assertEqual(score, 1.0)

    def test_meta_in_filename(self):
        """Test when metadata title is contained in filename title."""
        is_match, score = organize_music._check_substring_match("Locked In", "Lost In The Abyss - 02 Locked In")
        self.assertTrue(is_match)
        self.assertEqual(score, 1.0)

    def test_filename_in_meta(self):
        """Test when filename title is contained in metadata title."""
        is_match, score = organize_music._check_substring_match("Way Of The Wub", "Way Of The Wub")
        self.assertTrue(is_match)
        self.assertEqual(score, 1.0)

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        is_match, score = organize_music._check_substring_match("locked in", "LOCKED IN")
        self.assertTrue(is_match)
        self.assertEqual(score, 1.0)

    def test_with_punctuation(self):
        """Test matching with punctuation differences."""
        is_match, score = organize_music._check_substring_match("Can't Let You Go", "Can't Let You Go")
        self.assertTrue(is_match)

    def test_word_overlap_majority(self):
        """Test when majority of words match (70%+)."""
        is_match, score = organize_music._check_substring_match("Way Of The Wub", "Second Opinion LP - 06 Way Of The Wub")
        self.assertTrue(is_match)
        self.assertEqual(score, 1.0)

    def test_no_match_different_words(self):
        """Test when there's no word overlap."""
        is_match, score = organize_music._check_substring_match("Song A", "Song B")
        self.assertFalse(is_match)

    def test_empty_strings(self):
        """Test with empty strings."""
        is_match, score = organize_music._check_substring_match("", "")
        self.assertFalse(is_match)

    def test_partial_word_match_below_threshold(self):
        """Test when fewer than 70% of words match."""
        is_match, score = organize_music._check_substring_match("One Two Three", "Four Five Six")
        self.assertFalse(is_match)


class TestCheckMetadataMismatchWithSubstring(unittest.TestCase):
    """Tests for _check_metadata_mismatch with substring matching."""

    def test_title_substring_in_filename(self):
        """Test when metadata title is substring of filename title."""
        result = organize_music._check_metadata_mismatch(
            Path("Artist - Album - 01 Title.mp3"),
            "Artist",
            "Title",
            threshold=0.6
        )
        self.assertFalse(result['title_mismatch'])
        self.assertEqual(result['title_similarity'], 1.0)

    def test_title_exact_match(self):
        """Test when metadata title exactly matches filename title."""
        result = organize_music._check_metadata_mismatch(
            Path("Artist - Title.mp3"),
            "Artist",
            "Title",
            threshold=0.6
        )
        self.assertFalse(result['title_mismatch'])
        self.assertEqual(result['title_similarity'], 1.0)

    def test_title_no_match(self):
        """Test when metadata title doesn't match at all."""
        result = organize_music._check_metadata_mismatch(
            Path("Artist - Song B.mp3"),
            "Artist",
            "Completely Different Title",
            threshold=0.6
        )
        self.assertTrue(result['title_mismatch'])
        self.assertLess(result['title_similarity'], 0.6)

    def test_title_levenshtein_fallback(self):
        """Test Levenshtein fallback for similar but non-substring titles."""
        result = organize_music._check_metadata_mismatch(
            Path("Artist - Amazing Song.mp3"),
            "Artist",
            "Amazing Song",  # Same, should match via substring
            threshold=0.6
        )
        self.assertFalse(result['title_mismatch'])


class TestBandcampHTMLParsing(unittest.TestCase):
    """Tests for Bandcamp HTML parsing functions."""

    def test_parse_bandcamp_json_ld_with_keywords(self):
        """Test parsing JSON-LD with keywords."""
        html = '''
        <script type="application/ld+json">
        {"keywords": ["techno", "electronic", "dark"], "publisher": {"name": "Test Label"}}
        </script>
        '''
        genre, label = organize_music._parse_bandcamp_from_json_ld(html)
        self.assertEqual(genre, "Techno")
        self.assertEqual(label, "Test Label")

    def test_parse_bandcamp_json_ld_with_artist(self):
        """Test parsing JSON-LD with byArtist as label."""
        html = '''
        <script type="application/ld+json">
        {"keywords": ["house"], "byArtist": {"name": "Artist Name Records"}}
        </script>
        '''
        genre, label = organize_music._parse_bandcamp_from_json_ld(html)
        self.assertEqual(genre, "House")
        self.assertEqual(label, "Artist Name Records")

    def test_parse_bandcamp_json_ld_trance_keywords(self):
        """Test parsing trance from JSON-LD keywords."""
        html = '''
        <script type="application/ld+json">
        {"keywords": ["psytrance", "progressive trance"]}
        </script>
        '''
        genre, label = organize_music._parse_bandcamp_from_json_ld(html)
        self.assertEqual(genre, "Trance")

    def test_parse_bandcamp_json_ld_dnb_keywords(self):
        """Test parsing DnB from JSON-LD keywords."""
        html = '''
        <script type="application/ld+json">
        {"keywords": ["drum and bass", "neurofunk"]}
        </script>
        '''
        genre, label = organize_music._parse_bandcamp_from_json_ld(html)
        self.assertEqual(genre, "DnB")

    def test_parse_bandcamp_json_ld_fallback_house(self):
        """Test fallback to House when 'house' in keyword."""
        html = '''
        <script type="application/ld+json">
        {"keywords": ["some-genre-house"]}
        </script>
        '''
        genre, label = organize_music._parse_bandcamp_from_json_ld(html)
        self.assertEqual(genre, "House")

    def test_parse_bandcamp_json_ld_fallback_drum_bass(self):
        """Test fallback to DnB when 'drum' and 'bass' in keyword."""
        html = '''
        <script type="application/ld+json">
        {"keywords": ["deep-drum-bass-track"]}
        </script>
        '''
        genre, label = organize_music._parse_bandcamp_from_json_ld(html)
        self.assertEqual(genre, "DnB")

    def test_parse_bandcamp_json_ld_invalid_json(self):
        """Test handling of invalid JSON in JSON-LD."""
        html = '<script type="application/ld+json">{invalid</script>'
        genre, label = organize_music._parse_bandcamp_from_json_ld(html)
        self.assertIsNone(genre)
        self.assertIsNone(label)

    def test_extract_first_search_result_data_item_url(self):
        """Test extraction of track URL from data-item-url."""
        html = '<div data-item-url="https://artist.bandcamp.com/track/track-name">Test</div>'
        result = organize_music._extract_first_search_result(html)
        self.assertEqual(result, "https://artist.bandcamp.com/track/track-name")

    def test_extract_first_search_result_href_pattern(self):
        """Test extraction of track URL from href pattern."""
        html = '<a href="https://artist.bandcamp.com/track/track-name">Track</a>'
        result = organize_music._extract_first_search_result(html)
        self.assertEqual(result, "https://artist.bandcamp.com/track/track-name")

    def test_extract_first_search_result_no_track(self):
        """Test when no track URL found."""
        html = '<a href="https://artist.bandcamp.com/album/album-name">Album</a>'
        result = organize_music._extract_first_search_result(html)
        self.assertIsNone(result)

    def test_fetch_and_parse_track_page_success(self):
        """Test successful track page fetch and parse."""
        html = '''
        <script type="application/ld+json">
        {"keywords": ["techno"]}
        </script>
        '''
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = html.encode()
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            
            genre, label = organize_music._fetch_and_parse_track_page("https://artist.bandcamp.com/track/test")
            self.assertEqual(genre, "Techno")

    def test_fetch_and_parse_track_page_exception(self):
        """Test exception handling in track page fetch."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = Exception("Network error")
            
            genre, label = organize_music._fetch_and_parse_track_page("https://artist.bandcamp.com/track/test")
            self.assertIsNone(genre)
            self.assertIsNone(label)

    def test_try_direct_bandcamp_url_success(self):
        """Test successful direct Bandcamp URL."""
        html = '''
        <script type="application/ld+json">
        {"keywords": ["house"]}
        </script>
        '''
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = html.encode()
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            
            genre, label = organize_music._try_direct_bandcamp_url("Test Artist", "Test Title")
            self.assertEqual(genre, "House")

    def test_try_direct_bandcamp_url_all_fail(self):
        """Test when all direct URL patterns fail."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = Exception("Not found")
            
            genre, label = organize_music._try_direct_bandcamp_url("Test Artist", "Test Title")
            self.assertIsNone(genre)
            self.assertIsNone(label)


class TestMusicBrainzFallback(unittest.TestCase):
    """Tests for MusicBrainz API fallback in get_genre_online."""

    def setUp(self):
        """Clear genre and bandcamp cache before each test."""
        if hasattr(organize_music, '_genre_cache'):
            organize_music._genre_cache.clear()
        if hasattr(organize_music, '_bandcamp_cache'):
            organize_music._bandcamp_cache.clear()

    @patch('organize_music.get_genre_from_bandcamp')
    @patch('urllib.request.urlopen')
    def test_musicbrainz_fallback_electronic_tag(self, mock_urlopen, mock_bandcamp):
        """Test MusicBrainz returns electronic genre."""
        # iTunes returns no genre
        itunes_resp = MagicMock()
        itunes_resp.__enter__ = MagicMock(return_value=itunes_resp)
        itunes_resp.__exit__ = MagicMock(return_value=False)
        itunes_resp.read.return_value = json.dumps({'resultCount': 0}).encode()
        
        # Bandcamp returns no genre
        mock_bandcamp.return_value = (None, None)
        
        # MusicBrainz returns electronic genre
        mb_search_resp = MagicMock()
        mb_search_resp.__enter__ = MagicMock(return_value=mb_search_resp)
        mb_search_resp.__exit__ = MagicMock(return_value=False)
        mb_search_resp.read.return_value = json.dumps({'recordings': [{'id': 'rec-id-123'}]}).encode()
        
        mb_rg_resp = MagicMock()
        mb_rg_resp.__enter__ = MagicMock(return_value=mb_rg_resp)
        mb_rg_resp.__exit__ = MagicMock(return_value=False)
        mb_rg_resp.read.return_value = json.dumps({'release-groups': [{'id': 'rg-id-456'}]}).encode()
        
        mb_tag_resp = MagicMock()
        mb_tag_resp.__enter__ = MagicMock(return_value=mb_tag_resp)
        mb_tag_resp.__exit__ = MagicMock(return_value=False)
        mb_tag_resp.read.return_value = json.dumps({
            'release-group': {'tags': [{'name': 'electronic', 'count': 10}]}
        }).encode()
        
        mock_urlopen.side_effect = [itunes_resp, mb_search_resp, mb_rg_resp, mb_tag_resp]
        
        result = organize_music.get_genre_online("Unknown Artist", "Unknown Title")
        self.assertEqual(result, "Electronic")

    @patch('organize_music.get_genre_from_bandcamp')
    @patch('urllib.request.urlopen')
    def test_musicbrainz_fallback_non_electronic_tag(self, mock_urlopen, mock_bandcamp):
        """Test MusicBrainz returns non-electronic genre as fallback."""
        # iTunes returns no genre
        itunes_resp = MagicMock()
        itunes_resp.__enter__ = MagicMock(return_value=itunes_resp)
        itunes_resp.__exit__ = MagicMock(return_value=False)
        itunes_resp.read.return_value = json.dumps({'resultCount': 0}).encode()
        
        # Bandcamp returns no genre
        mock_bandcamp.return_value = (None, None)
        
        # MusicBrainz returns non-electronic genre
        mb_search_resp = MagicMock()
        mb_search_resp.__enter__ = MagicMock(return_value=mb_search_resp)
        mb_search_resp.__exit__ = MagicMock(return_value=False)
        mb_search_resp.read.return_value = json.dumps({'recordings': [{'id': 'rec-id-123'}]}).encode()
        
        mb_rg_resp = MagicMock()
        mb_rg_resp.__enter__ = MagicMock(return_value=mb_rg_resp)
        mb_rg_resp.__exit__ = MagicMock(return_value=False)
        mb_rg_resp.read.return_value = json.dumps({'release-groups': [{'id': 'rg-id-456'}]}).encode()
        
        mb_tag_resp = MagicMock()
        mb_tag_resp.__enter__ = MagicMock(return_value=mb_tag_resp)
        mb_tag_resp.__exit__ = MagicMock(return_value=False)
        mb_tag_resp.read.return_value = json.dumps({
            'release-group': {'tags': [{'name': 'rock', 'count': 5}]}
        }).encode()
        
        mock_urlopen.side_effect = [itunes_resp, mb_search_resp, mb_rg_resp, mb_tag_resp]
        
        result = organize_music.get_genre_online("Unknown Artist", "Unknown Title")
        self.assertEqual(result, "Rock")

    @patch('organize_music.get_genre_from_bandcamp')
    @patch('urllib.request.urlopen')
    def test_musicbrainz_exception_caught(self, mock_urlopen, mock_bandcamp):
        """Test MusicBrainz exception is caught gracefully."""
        mock_bandcamp.return_value = (None, None)
        
        def urlopen_side_effect(url, *args, **kwargs):
            if 'musicbrainz' in url:
                raise Exception("MusicBrainz error")
            itunes_resp = MagicMock()
            itunes_resp.__enter__ = MagicMock(return_value=itunes_resp)
            itunes_resp.__exit__ = MagicMock(return_value=False)
            itunes_resp.read.return_value = json.dumps({'resultCount': 0}).encode()
            return itunes_resp
        
        mock_urlopen.side_effect = urlopen_side_effect
        
        result = organize_music.get_genre_online("Unknown Artist", "Unknown Title")
        self.assertIsNone(result)


class TestExtractAllMetadataExceptions(unittest.TestCase):
    """Tests for _extract_all_metadata exception handling."""

    @patch('subprocess.run')
    def test_ffprobe_timeout(self, mock_run):
        """Test handling of ffprobe timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("ffprobe", 10)
        
        result = organize_music._extract_all_metadata(Path("test.mp3"))
        self.assertIsNone(result['artist'])
        self.assertIsNone(result['title'])

    @patch('subprocess.run')
    def test_ffprobe_called_process_error(self, mock_run):
        """Test handling of ffprobe CalledProcessError."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffprobe")
        
        result = organize_music._extract_all_metadata(Path("test.mp3"))
        self.assertIsNone(result['artist'])

    @patch('subprocess.run')
    def test_ffprobe_file_not_found(self, mock_run):
        """Test handling of ffprobe not found."""
        mock_run.side_effect = FileNotFoundError("ffprobe")
        
        result = organize_music._extract_all_metadata(Path("test.mp3"))
        self.assertIsNone(result['artist'])

    @patch('subprocess.run')
    def test_ffprobe_invalid_json(self, mock_run):
        """Test handling of invalid JSON in ffprobe output."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "not valid json"
        
        result = organize_music._extract_all_metadata(Path("test.mp3"))
        self.assertIsNone(result['artist'])

    @patch('subprocess.run')
    def test_ffprobe_returns_empty_tags(self, mock_run):
        """Test handling of empty tags in ffprobe output."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps({'format': {}})
        
        result = organize_music._extract_all_metadata(Path("test.mp3"))
        self.assertIsNone(result['artist'])


class TestWriteMetadataTagExceptions(unittest.TestCase):
    """Tests for _write_metadata_tag exception handling."""

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_ffmpeg_timeout(self, mock_exists, mock_run):
        """Test handling of ffmpeg timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 10)
        mock_exists.return_value = False
        
        result = organize_music._write_metadata_tag(Path("test.mp3"), "genre", "House")
        self.assertFalse(result)

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_ffmpeg_called_process_error(self, mock_exists, mock_run):
        """Test handling of ffmpeg error."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error message"
        mock_exists.return_value = False
        
        result = organize_music._write_metadata_tag(Path("test.mp3"), "genre", "House")
        self.assertFalse(result)

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_ffmpeg_file_not_found(self, mock_exists, mock_run):
        """Test handling of ffmpeg not found."""
        mock_run.side_effect = FileNotFoundError("ffmpeg")
        mock_exists.return_value = False
        
        result = organize_music._write_metadata_tag(Path("test.mp3"), "genre", "House")
        self.assertFalse(result)


class TestOrganizeMusicMainFunction(unittest.TestCase):
    """Tests for organize_music main function."""

    def test_no_audio_files_found(self):
        """Test when no audio files are found."""
        with patch('pathlib.Path.resolve') as mock_resolve:
            mock_resolve.return_value = Path("/test")
            
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data='{}')):
                    with patch.object(organize_music.logger, 'info') as mock_log:
                        organize_music.organize_music("/test", dry_run=True)
                        mock_log.assert_called_with("No MP3 or M4A files found.")

    def test_config_file_not_found(self):
        """Test when config.json is not found."""
        with patch('pathlib.Path.resolve') as mock_resolve:
            mock_resolve.return_value = Path("/test")
            
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(SystemExit):
                    organize_music.organize_music("/test")

    def test_config_invalid_json(self):
        """Test when config.json has invalid JSON."""
        with patch('pathlib.Path.resolve') as mock_resolve:
            mock_resolve.return_value = Path("/test")
            
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data='invalid json')):
                    with pytest.raises(SystemExit):
                        organize_music.organize_music("/test")


if __name__ == '__main__':
    unittest.main()