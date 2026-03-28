#!/usr/bin/env python3
"""
Unit tests for the organize_music.py script.
"""

import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Import the functions from the script
# Since the script is in the parent directory, we add it to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from organize_music import (
    load_config,
    get_artist_title_from_file,
    parse_artist_title_from_filename,
    lookup_genre_online_itunes,
    lookup_genre_online_musicbrainz,
    lookup_genre_online,
    normalize_genre,
    find_destination,
    process_files
)


class TestLoadConfig(unittest.TestCase):
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_load_config_valid(self, mock_open, mock_is_file):
        config_data = {
            "genre_map": {
                "Drum n Base": "/path/to/dnb",
                "House": "/path/to/house",
                "Techno, Trance": "/path/to/electronic"
            }
        }
        mock_open.return_value.read.return_value = json.dumps(config_data)
        config = load_config(Path("dummy.json"))
        expected = {
            "drum n base": "/path/to/dnb",
            "house": "/path/to/house",
            "techno": "/path/to/electronic",
            "trance": "/path/to/electronic"
        }
        self.assertEqual(config, expected)

    def test_load_config_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_config(Path("nonexistent.json"))

    @patch("pathlib.Path.is_file", return_value=True)
    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_load_config_empty_genre_map(self, mock_open, mock_is_file):
        config_data = {"genre_map": {}}
        mock_open.return_value.read.return_value = json.dumps(config_data)
        config = load_config(Path("dummy.json"))
        self.assertEqual(config, {})


class TestGetArtistTitleFromFile(unittest.TestCase):
    @patch("subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps({
            "format": {
                "tags": {
                    "artist": "Test Artist",
                    "title": "Test Title"
                }
            }
        })
        artist, title = get_artist_title_from_file(Path("dummy.mp3"))
        self.assertEqual(artist, "Test Artist")
        self.assertEqual(title, "Test Title")

    @patch("subprocess.run")
    def test_missing_artist(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps({
            "format": {
                "tags": {
                    "title": "Test Title"
                }
            }
        })
        artist, title = get_artist_title_from_file(Path("dummy.mp3"))
        self.assertIsNone(artist)
        self.assertEqual(title, "Test Title")

    @patch("subprocess.run")
    def test_empty_strings(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps({
            "format": {
                "tags": {
                    "artist": "   ",
                    "title": "   "
                }
            }
        })
        artist, title = get_artist_title_from_file(Path("dummy.mp3"))
        self.assertIsNone(artist)
        self.assertIsNone(title)

    @patch("subprocess.run")
    def test_ffprobe_error(self, mock_run):
        mock_run.return_value.returncode = 1
        artist, title = get_artist_title_from_file(Path("dummy.mp3"))
        self.assertIsNone(artist)
        self.assertIsNone(title)

    @patch("subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("ffprobe", 5)
        artist, title = get_artist_title_from_file(Path("dummy.mp3"))
        self.assertIsNone(artist)
        self.assertIsNone(title)


class TestParseArtistTitleFromFilename(unittest.TestCase):
    def test_standard_format(self):
        artist, title = parse_artist_title_from_filename("Artist - Title.mp3")
        self.assertEqual(artist, "Artist")
        self.assertEqual(title, "Title")

    def test_no_dash(self):
        artist, title = parse_artist_title_from_filename("JustTitle.mp3")
        self.assertIsNone(artist)
        self.assertEqual(title, "JustTitle")

    def test_empty_artist(self):
        artist, title = parse_artist_title_from_filename(" - Title.mp3")
        self.assertIsNone(artist)
        self.assertEqual(title, "Title")

    def test_empty_title(self):
        artist, title = parse_artist_title_from_filename("Artist - .mp3")
        self.assertEqual(artist, "Artist")
        self.assertIsNone(title)

    def test_multiple_dashes(self):
        artist, title = parse_artist_title_from_filename("Artist - Title - Remix.mp3")
        self.assertEqual(artist, "Artist")
        self.assertEqual(title, "Title - Remix")


class TestNormalizeGenre(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_genre("  TeChNo  "), "techno")
        self.assertEqual(normalize_genre("DRUM N BASS"), "drum n bass")


class TestFindDestination(unittest.TestCase):
    def setUp(self):
        self.genre_to_dest = {
            "house": "/path/to/house",
            "drum n base": "/path/to/dnb",
            "techno": "/path/to/techno"
        }

    def test_exact_match(self):
        dest = find_destination("House", self.genre_to_dest)
        self.assertEqual(dest, "/path/to/house")

    def test_drum_n_base_special_case(self):
        # When genre contains both drum and bass, it should map to drum n base if present
        dest = find_destination("Tech Drum Bass Remix", self.genre_to_dest)
        self.assertEqual(dest, "/path/to/dnb")

    def test_drum_n_base_not_in_config(self):
        # If drum n base is not in config, fall back to normal lookup (which will fail)
        genre_to_dest_no_dnb = {"house": "/path/to/house"}
        dest = find_destination("Drum and Bass", genre_to_dest_no_dnb)
        self.assertIsNone(dest)

    def test_no_match(self):
        dest = find_destination("Unknown Genre", self.genre_to_dest)
        self.assertIsNone(dest)


class TestLookupGenreOnline(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_itunes_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__.return_value.read.return_value = json.dumps({
            "results": [{
                "primaryGenreName": "House"
            }]
        })
        mock_urlopen.return_value = mock_response

        genre = lookup_genre_online_itunes("Artist", "Title")
        self.assertEqual(genre, "House")

    @patch("urllib.request.urlopen")
    def test_itunes_failure(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Network error")
        genre = lookup_genre_online_itunes("Artist", "Title")
        self.assertIsNone(genre)

    @patch("urllib.request.urlopen")
    def test_musicbrainz_success_recording_with_release_group_tag(self, mock_urlopen):
        # First call: search for recording
        # Second call: get recording with releases and release-groups
        # Third call: get release-group by id
        responses = [
            json.dumps({"recordings": [{"id": "mbid1"}]}),
            json.dumps({
                "release-groups": [{
                    "tags": [{"name": "Techno"}]
                }]
            })
        ]
        mocks = []
        for r in responses:
            m = MagicMock()
            m.__enter__.return_value.read.return_value = r.encode()
            m.__exit__.return_value = None
            mocks.append(m)
        mock_urlopen.side_effect = mocks

        genre = lookup_genre_online_musicbrainz("Artist", "Title")
        self.assertEqual(genre, "Techno")

    @patch("urllib.request.urlopen")
    def test_musicbrainz_fallback_to_release(self, mock_urlopen):
        # First call: recording search
        # Second call: recording detail has no release-groups but has releases
        # Third call: release-group from first release
        responses = [
            json.dumps({"recordings": [{"id": "mbid1"}]}),
            json.dumps({
                "releases": [{
                    "release-group": {"id": "rgid1"}
                }]
            }),
            json.dumps({
                "tags": [{"name": "House"}]
            })
        ]
        mocks = []
        for r in responses:
            m = MagicMock()
            m.__enter__.return_value.read.return_value = r.encode()
            m.__exit__.return_value = None
            mocks.append(m)
        mock_urlopen.side_effect = mocks

        genre = lookup_genre_online_musicbrainz("Artist", "Title")
        self.assertEqual(genre, "House")

    @patch("urllib.request.urlopen")
    def test_musicbrainz_no_tags(self, mock_urlopen):
        mock1 = MagicMock()
        mock1.__enter__.return_value.read.return_value = json.dumps({"recordings": [{"id": "mbid1"}]}).encode()
        mock1.__exit__.return_value = None
        
        mock2 = MagicMock()
        mock2.__enter__.return_value.read.return_value = json.dumps({"release-groups": []}).encode()
        mock2.__exit__.return_value = None
        
        mock_urlopen.side_effect = [mock1, mock2]
        
        genre = lookup_genre_online_musicbrainz("Artist", "Title")
        self.assertIsNone(genre)

    @patch("organize_music.lookup_genre_online_itunes")
    @patch("organize_music.lookup_genre_online_musicbrainz")
    def test_lookup_genre_online_itunes_priority(self, mock_musicbrainz, mock_itunes):
        mock_itunes.return_value = "iTunes Genre"
        mock_musicbrainz.return_value = "MusicBrainz Genre"
        genre = lookup_genre_online("Artist", "Title")
        self.assertEqual(genre, "iTunes Genre")
        mock_musicbrainz.assert_not_called()

    @patch("organize_music.lookup_genre_online_itunes")
    @patch("organize_music.lookup_genre_online_musicbrainz")
    def test_lookup_genre_online_fallback(self, mock_musicbrainz, mock_itunes):
        mock_itunes.return_value = None
        mock_musicbrainz.return_value = "Fallback Genre"
        genre = lookup_genre_online("Artist", "Title")
        self.assertEqual(genre, "Fallback Genre")


class TestProcessFiles(unittest.TestCase):
    def setUp(self):
        self.source_dir = Path("/tmp/test_source")
        self.source_dir.mkdir(exist_ok=True)
        # Create a dummy file
        (self.source_dir / "test.mp3").touch()

        self.genre_to_dest = {
            "house": "/tmp/test_dest/house"
        }

    def tearDown(self):
        # Clean up
        import shutil
        if self.source_dir.exists():
            shutil.rmtree(self.source_dir)
        # Note: we don't clean the destination because we mock the move

    @patch("organize_music.get_artist_title_from_file")
    @patch("organize_music.lookup_genre_online")
    @patch("organize_music.find_destination")
    def test_process_files_move(self, mock_find_dest, mock_lookup, mock_get_artist_title):
        # Setup metadata
        mock_get_artist_title.return_value = ("Artist", "Title")
        mock_lookup.return_value = "House"
        mock_find_dest.return_value = "/tmp/test_dest/house"

        # We'll mock the actual move and directory creation to avoid touching the filesystem
        with patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.rename") as mock_rename:
            log_entries = process_files(self.source_dir, self.genre_to_dest, dry_run=False)
            # Since we moved the file, we expect no log entries (only non-moved are logged)
            self.assertEqual(len(log_entries), 0)
            mock_rename.assert_called_once()

    @patch("organize_music.get_artist_title_from_file")
    @patch("organize_music.lookup_genre_online")
    @patch("organize_music.find_destination")
    def test_process_files_genre_not_mapped(self, mock_find_dest, mock_lookup, mock_get_artist_title):
        mock_get_artist_title.return_value = ("Artist", "Title")
        mock_lookup.return_value = "UnknownGenre"
        mock_find_dest.return_value = None  # Not mapped

        log_entries = process_files(self.source_dir, self.genre_to_dest, dry_run=False)
        self.assertEqual(len(log_entries), 1)
        self.assertEqual(log_entries[0]["reason"], "genre_not_mapped")

    @patch("organize_music.get_artist_title_from_file")
    @patch("organize_music.lookup_genre_online")
    @patch("organize_music.find_destination")
    def test_process_files_target_exists(self, mock_find_dest, mock_lookup, mock_get_artist_title):
        mock_get_artist_title.return_value = ("Artist", "Title")
        mock_lookup.return_value = "House"
        mock_find_dest.return_value = "/tmp/test_dest/house"

        # Make the target file exist
        with patch("pathlib.Path.is_file", return_value=True):
            log_entries = process_files(self.source_dir, self.genre_to_dest, dry_run=False)
            self.assertEqual(len(log_entries), 1)
            self.assertEqual(log_entries[0]["reason"], "target_exists")

    @patch("organize_music.get_artist_title_from_file")
    def test_process_files_missing_metadata(self, mock_get_artist_title):
        mock_get_artist_title.return_value = (None, "Title")  # missing artist
        log_entries = process_files(self.source_dir, self.genre_to_dest, dry_run=False)
        self.assertEqual(len(log_entries), 1)
        self.assertEqual(log_entries[0]["reason"], "missing_metadata_artist")


if __name__ == "__main__":
    unittest.main()