#!/usr/bin/env python3
"""
MP3/M4A Organizer Script

Organizes audio files by moving them to genre-specific folders based on online lookup
of artist and title (from metadata or filename). If artist/title missing, file left in place.
If online lookup fails or genre not mapped, file left in place and logged.

Features:
- Recursive scanning of source directory
- Extracts artist and title from file metadata (ffprobe) or filename fallback
- Online lookup via iTunes API (primary) and MusicBrainz API (fallback)
- Normalizes genre and maps via config.json (keys can be comma-separated lists)
- Dry-run mode (--dry-run or -n) to see what would happen without moving files
- Creates a JSON log of non-processed files (normal mode) or audit log (dry-run)
- Timeout for HTTP requests and ffprobe calls to prevent hanging

Dependencies:
- ffprobe (from FFmpeg) for reading metadata
- Python 3.x (standard library: json, os, subprocess, pathlib, typing, urllib)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.error
import urllib.parse


def load_config(config_path: Path) -> Dict[str, str]:
    """Load genre mapping from config.json."""
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with config_path.open('r') as f:
        config = json.load(f)
    
    # Build a mapping from genre (lowercase) to destination directory
    genre_to_dest: Dict[str, str] = {}
    for genre_key, dest in config.get('genre_map', {}).items():
        # Split by commas, strip whitespace, and map each genre (lowercase) to dest
        for genre in [g.strip() for g in genre_key.split(',')]:
            if genre:  # ignore empty strings
                genre_to_dest[genre.lower()] = dest
    return genre_to_dest


def get_artist_title_from_file(file_path: Path, timeout: int = 5) -> Tuple[Optional[str], Optional[str]]:
    """Extract artist and title tags from audio file using ffprobe.
    
    Returns (artist, title). If missing, returns (None, None) for that field.
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_entries', 'format_tags', str(file_path)],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            return (None, None)
        
        data = json.loads(result.stdout)
        tags = data.get('format', {}).get('tags', {})
        artist = tags.get('artist') or tags.get('ARTIST')
        title = tags.get('title') or tags.get('TITLE')
        # Clean up
        if artist:
            artist = artist.strip()
            if not artist:
                artist = None
        if title:
            title = title.strip()
            if not title:
                title = None
        return (artist, title)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return (None, None)


def parse_artist_title_from_filename(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Fallback: parse artist and title from filename assuming 'Artist - Title.ext'."""
    # Remove extension
    basename = filename.rsplit('.', 1)[0]
    # Try to split by ' - ' (dash surrounded by spaces)
    if ' - ' in basename:
        parts = basename.split(' - ', 1)
        artist = parts[0].strip()
        title = parts[1].strip()
        if not artist:
            artist = None
        if not title:
            title = None
        return (artist, title)
    else:
        # No dash: treat whole as title, artist unknown
        return (None, basename.strip() or None)


def lookup_genre_online_itunes(artist: str, title: str) -> Optional[str]:
    """Lookup genre via iTunes Search API."""
    try:
        query = urllib.parse.quote(f"{artist} {title}")
        url = f"https://itunes.apple.com/search?term={query}&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'MP3Organizer/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)
            results = data.get('results', [])
            if results:
                genre = results[0].get('primaryGenreName')
                if genre and genre.strip():
                    return genre.strip()
    except Exception:
        pass
    return None


def lookup_genre_online_musicbrainz(artist: str, title: str) -> Optional[str]:
    """Lookup genre via MusicBrainz API.
    Try to get first recording, then its release-group's first tag as genre."""
    try:
        # Search for recording
        query = urllib.parse.quote(f'artist:"{artist}" AND recording:"{title}"')
        url = f"https://musicbrainz.org/ws/2/recording/?query={query}&fmt=json&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'MP3Organizer/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)
            recordings = data.get('recordings', [])
            if not recordings:
                return None
            recording = recordings[0]
            # Get release-group ids from recording's releases? Simpler: get first release-group via artist and recording?
            # We'll try to get release-groups linked to the recording via 'release-groups' inc? Not in search.
            # Instead, get the first release from the recording's 'releases' list if present (need inc=releases).
            # Let's do a second request to get recording with inc=releases+release-groups.
            mbid = recording.get('id')
            if not mbid:
                return None
            url2 = f"https://musicbrainz.org/ws/2/recording/{mbid}?fmt=json&inc=releases+release-groups"
            req2 = urllib.request.Request(url2, headers={'User-Agent': 'MP3Organizer/1.0'})
            with urllib.request.urlopen(req2, timeout=10) as response2:
                data2 = json.load(response2)
                release_groups = data2.get('release-groups', [])
                if not release_groups:
                    # Try releases then get their release-group
                    releases = data2.get('releases', [])
                    if releases:
                        # Get release-group id from first release
                        rg_id = releases[0].get('release-group', {}).get('id')
                        if rg_id:
                            # Fetch that release-group
                            url3 = f"https://musicbrainz.org/ws/2/release-group/{rg_id}?fmt=json"
                            req3 = urllib.request.Request(url3, headers={'User-Agent': 'MP3Organizer/1.0'})
                            with urllib.request.urlopen(req3, timeout=10) as response3:
                                data3 = json.load(response3)
                                tags = data3.get('tags', [])
                                if tags:
                                    # Use first tag's name as genre
                                    return tags[0].get('name', '').strip()
                                return None
                    return None
                else:
                    # Use first release-group's tags
                    tags = release_groups[0].get('tags', [])
                    if tags:
                        return tags[0].get('name', '').strip()
                    return None
    except Exception:
        pass
    return None


def lookup_genre_online(artist: str, title: str) -> Optional[str]:
    """Try online sources in order: iTunes, MusicBrainz."""
    genre = lookup_genre_online_itunes(artist, title)
    if genre:
        return genre
    genre = lookup_genre_online_musicbrainz(artist, title)
    if genre:
        return genre
    return None


def normalize_genre(genre: str) -> str:
    """Normalize genre string for matching."""
    return genre.lower().strip()


def find_destination(genre: str, genre_to_dest: Dict[str, str]) -> Optional[str]:
    """Find destination directory for a genre.
    
    First checks for special case: if genre contains both 'drum' and 'bass',
    maps to 'Drum n Base' if present in config.
    Otherwise, looks for exact match in genre_to_dest.
    """
    genre_lower = normalize_genre(genre)
    
    # Special case for Drum n Base
    if 'drum' in genre_lower and 'bass' in genre_lower:
        if 'drum n base' in genre_to_dest:
            return genre_to_dest['drum n base']
        # If not, fall through to normal lookup
    
    # Normal lookup
    return genre_to_dest.get(genre_lower)


def create_log_entry(file_path: Path, artist: Optional[str], title: Optional[str], 
                    genre: Optional[str] = None, action: str = "", 
                    reason: str = "", destination: Optional[str] = None) -> Dict:
    """Create a standardized log entry."""
    entry = {
        "file": str(file_path.resolve()),
    }
    if artist is not None:
        entry["artist"] = artist
    if title is not None:
        entry["title"] = title
    if genre is not None:
        entry["detected_genre"] = genre
    if action:
        entry["action"] = action
    if reason:
        entry["reason"] = reason
    if destination is not None:
        entry["destination"] = destination
    return entry


def log_and_print(file_path: Path, artist: Optional[str], title: Optional[str],
                 genre: Optional[str], action: str, reason: str, 
                 destination: Optional[str], dry_run: bool,
                 log_entries: List[Dict]) -> None:
    """Handle logging and printing for both dry-run and normal modes."""
    entry = create_log_entry(file_path, artist, title, genre, action, reason, destination)
    log_entries.append(entry)
    
    # Print appropriate message
    if dry_run:
        action_text = "Would" + (" move" if action == "would_move" else " not move")
        reason_text = f" ({reason})" if reason else ""
        dest_text = f" to {destination}" if destination else ""
        print(f"  -> [DRY RUN] {action_text}{reason_text}{dest_text}.")
    else:
        action_text = "Leaving file in place" if action == "would_not_move" else "Moved successfully"
        reason_text = f" ({reason})" if reason else ""
        dest_text = f" to {destination}" if destination and action == "would_move" else ""
        print(f"  -> {action_text}{reason_text}{dest_text}.")


def process_files(
    source_dir: Path,
    genre_to_dest: Dict[str, str],
    dry_run: bool = False
) -> List[Dict]:
    """Process all MP3 and M4A files in source_dir (recursively).
    
    Returns a list of log entries for files that were not moved (or in dry-run,
    entries for all files with intended actions).
    """
    log_entries = []
    
    # Find all .mp3 and .m4a files recursively
    file_extensions = ('*.mp3', '*.m4a')
    files = []
    for ext in file_extensions:
        files.extend(source_dir.rglob(ext))
    
    if not files:
        print(f"No MP3 or M4A files found in {source_dir}")
        return log_entries
    
    print(f"Found {len(files)} files to process.")
    
    for file_path in files:
        print(f"Processing: {file_path}")
        
        # Get artist and title from file metadata (only from metadata, no filename fallback)
        artist, title = get_artist_title_from_file(file_path)
        
        missing = []
        if artist is None:
            missing.append("artist")
        if title is None:
            missing.append("title")
        if missing:
            reason = f"missing_metadata_{'_'.join(missing)}"
            print(f"  -> Missing metadata: {', '.join(missing)}.")
            log_and_print(file_path, artist, title, None, "would_not_move", reason, None, dry_run, log_entries)
            continue
        
        print(f"  -> Artist: '{artist}', Title: '{title}'")
        
        # Online lookup for genre
        genre = lookup_genre_online(artist, title)
        if genre is None:
            reason = "lookup_failed"
            print(f"  -> Online lookup failed to find genre.")
            log_and_print(file_path, artist, title, None, "would_not_move", reason, None, dry_run, log_entries)
            continue
        
        print(f"  -> Detected genre: '{genre}'")
        normalized_genre = normalize_genre(genre)
        
        # Determine destination folder
        dest_dir = find_destination(genre, genre_to_dest)
        if dest_dir is None:
            reason = "genre_not_mapped"
            print(f"  -> Genre '{genre}' not mapped in config.")
            log_and_print(file_path, artist, title, genre, "would_not_move", reason, None, dry_run, log_entries)
            continue
        
        # Construct destination path
        dest_file = Path(dest_dir) / file_path.name
        
        # Check if target file already exists
        if dest_file.is_file():
            reason = "target_exists"
            print(f"  -> Target file already exists: {dest_file}")
            log_and_print(file_path, artist, title, genre, "would_not_move", reason, None, dry_run, log_entries)
            continue
        
        # If we reach here, we would move the file (if not dry run)
        if dry_run:
            log_and_print(file_path, artist, title, genre, "would_move", "", str(Path(dest_dir).resolve()), dry_run, log_entries)
        else:
            try:
                # Create destination directory if it doesn't exist
                Path(dest_dir).mkdir(parents=True, exist_ok=True)
                # Move the file
                file_path.rename(dest_file)
                print(f"  -> Moved successfully to: {dest_file}")
                # Note: We do NOT log successful moves in the result log (only non-processed files)
            except Exception as e:
                print(f"  -> Error moving file: {e}")
                log_and_print(file_path, artist, title, genre, "would_not_move", "move_failed", None, dry_run, log_entries)
    
    return log_entries


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Organize MP3/M4A files by genre via online lookup.")
    parser.add_argument(
        "source_dir",
        nargs="?",
        default=".",
        help="Source directory to scan for audio files (default: current directory)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Perform a dry run (no files moved, only audit log generated)"
    )
    args = parser.parse_args()
    
    source_dir = Path(args.source_dir).resolve()
    script_dir = Path(__file__).parent
    config_file = script_dir / "config.json"
    
    try:
        genre_to_dest = load_config(config_file)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
    
    # Determine log file path
    if args.dry_run:
        log_file = source_dir / "organization_audit.json"
    else:
        log_file = source_dir / "organization_results.json"
    
    # Process files
    log_entries = process_files(source_dir, genre_to_dest, dry_run=args.dry_run)
    
    # Write log file
    with log_file.open('w') as f:
        json.dump(log_entries, f, indent=2)
    
    print(f"\nAll files processed.")
    if args.dry_run:
        print(f"Audit log written to: {log_file}")
    else:
        print(f"Result log written to: {log_file}")


if __name__ == "__main__":
    main()