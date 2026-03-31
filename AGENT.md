# MP3/M4A Organizer Algorithm (Implemented in organize_music.py)

## Overview
This script organizes MP3 and M4A files by moving them to genre-specific or label-specific folders based on online lookup of artist and title (extracted from file metadata).
If artist or title metadata is missing, the file is left in place and logged.
If online lookup fails to find a genre or label, the file is left in place and logged.
If the genre or label is not mapped in config.json, the file is left in place and logged.
If the target file already exists, the file is left in place and logged.

## Configuration
- `config.json`: JSON file mapping genres and labels to target directories.
  - Keys can be comma-separated lists of genres or labels (e.g., "Techno, House").
  - Example:
    ```json
    {
      "genre_map": {
        "Drum n Base": "/path/to/dnb",
        "House": "/path/to/house",
        "Techno, Trance": "/path/to/electronic"
      },
      "label_map": {
        "Ninja Tune": "/path/to/ninja-tune",
        "Warp Records": "/path/to/warp",
        "Planet Mu": "/path/to/planet-mu"
      },
      "label_source_tag": "label"  // Optional: specify which tag to use for label (e.g., 'TPUB')
    }
    ```
  - Add more genres or labels as needed.
  - If `label_source_tag` is provided, the script will try to read that specific tag (and its uppercase variant) for the label.
  - If `label_source_tag` is not provided, the script checks common label-related tags: 'label', 'Label', 'TPUB', 'publisher'.

## Algorithm Steps
1. **Scan Directory**: Recursively find all `.mp3` and `.m4a` files in the source directory (default: current directory).
2. **Extract Metadata**:
    - Attempt to read `artist` and `title` tags from file using `ffprobe` (with timeout).
    - Attempt to read `label` tag from file using `ffprobe` (with timeout), either from a specific tag if configured or from common label tags.
    - If artist or title tag is missing or unreadable → leave file, log as `missing_metadata_<field>`.
3. **Online Lookup**:
    - Query iTunes Search API: `https://itunes.apple.com/search?term=<artist>+<title>&limit=1` for genre.
    - If iTunes fails or returns no genre, fallback to MusicBrainz API:
         * Search for recording by artist and title.
         * Get the first release-group of that recording and use its first tag as genre.
    - If label not found in metadata and label mapping is configured, query iTunes Search API for label:
         * First search for track by artist and title to get trackId.
         * Then lookup track by trackId to get label field.
    - If genre lookup fails → leave file, log as `lookup_failed`.
4. **Label/Genre Normalization & Mapping**:
    - Normalize label/genre to lowercase.
    - Special case: if label/genre contains both "drum" and "bass" → map to "Drum n Base" (if present in config).
    - **Priority**: Label mapping is checked first (if label available and label_map configured).
    - Otherwise, look for exact match in `config.json` genre_map or label_map (keys are normalized to lowercase).
    - If no mapping found → leave file, log as `genre_not_mapped` or `label_not_mapped`.
5. **Destination Check**:
    - Construct destination path: `<dest_dir>/<filename>`.
    - If target file already exists → leave file, log as `target_exists`.
6. **Move File** (unless in dry-run mode):
    - Create destination directory if it does not exist.
    - Move file to destination, preserving filename.
    - Note: Successful moves are **not** logged (only non-processed files are logged).
7. **Logging**:
    - In normal mode: Creates `organization_results.json` with entries for files not moved.
    - In dry-run mode (`--dry-run` or `-n`): Creates `organization_audit.json` with entries for all files, indicating what action would have been taken.
    - Log entries include: file path, artist, title, detected genre (if available), detected label (if available), reason (or action/destination in dry-run).

## Usage
```bash
# Normal mode (actually moves files)
python3 organize_music.py [source_directory]

# Dry-run mode (only shows what would be done)
python3 organize_music.py --dry-run [source_directory]
# or
python3 organize_music.py -n [source_directory]
```

## Dependencies
- `ffprobe` (from FFmpeg) for reading metadata.
- Python 3.x (standard library: json, os, subprocess, pathlib, typing, urllib).

## Extensibility
- To add new genres, add entries to `config.json` genre_map.
- The script already supports comma-separated genre keys for mapping multiple genres to the same destination.

## Notes
- The script uses a timeout of 5 seconds for `ffprobe` calls and 10 seconds for HTTP requests to prevent hanging.
- All paths are resolved to absolute paths in the log files for clarity.
- Online lookup relies on third-party APIs (iTunes and MusicBrainz) which have their own rate limits and availability.