# MP3/M4A Organizer

![Illustration](./assets/organize_mp3s.png)

![Test](https://github.com/holgerkampffmeyer2/organize_mp3s/actions/workflows/test.yml/badge.svg?branch=main)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/holgerkampffmeyer2/organize_mp3s)
[![License](https://img.shields.io/github/license/holgerkampffmeyer2/organize_mp3s)](https://github.com/holgerkampffmeyer2/organize_mp3s)

AI-agent driven MP3/M4A organization with online genre lookup, metadata-based sorting, and configurable destination mapping. Designed to be controlled by AI coding assistants like [opencode](https://opencode.ai) or Claude Code.

## Quick Start

```bash
# One-line install (Linux/macOS)
curl -fsSL https://raw.githubusercontent.com/holgerkampffmeyer2/organize_mp3s/main/install.sh | bash

# Or run directly
python3 organize_music.py [source_directory]
```

## How It Works

An AI agent reads `AGENT.md` and executes the organization workflow:

```
AI Agent reads AGENT.md → Pre-flight Check → Executes organize_music.py → Monitors results → Verifies output
```

The agent handles:
- Prerequisites check (ffmpeg, python3)
- SoundCloud client ID validation (optional, for enhanced matching)
- File discovery and batch processing decisions
- Metadata extraction from files
- Online genre lookup: SoundCloud (confidence match) → iTunes → Bandcamp → MusicBrainz
- Online label lookup: SoundCloud (confidence match) → iTunes → Bandcamp
- Error recovery and retries
- Verification of organization results

## Usage

### Via AI Agent (Recommended)

Open an AI coding assistant in this directory and prompt:

```
Organize all MP3 and M4A files using the workflow from AGENT.md.
```

### Via Command Line

```bash
# Normal mode (actually moves files)
python3 organize_music.py [source_directory]

# Dry-run mode (only shows what would be done, no files moved)
python3 organize_music.py --dry-run [source_directory]
# or
python3 organize_music.py -n [source_directory]

# Metadata enrichment mode (enriches missing metadata tags from online sources)
python3 organize_music.py --enrich-metadata [source_directory]
# or
python3 organize_music.py -e [source_directory]
```

- `source_directory`: The directory to scan for audio files (defaults to current directory if not provided).
- The script will create `organization_results.json` (normal mode) or `organization_audit.json` (dry-run) in the source directory.

## Prerequisites

```bash
sudo apt update
sudo apt install ffmpeg python3
```

## Technical Details

- **Metadata Source**: Artist and title from file metadata (single ffprobe call); Label from file metadata or online lookup
- **SoundCloud Integration**: Optional client ID in `.env` for enhanced track matching via confidence scoring (validates artist/title match before using other sources)
- **Genre/Label Lookup**: SoundCloud (confidence match) → iTunes Search API (primary, single unified call) → Bandcamp (fallback) → MusicBrainz (tags)
- **Label Lookup**: SoundCloud (confidence match) → iTunes Search API (when metadata missing, with track ID lookup) → Bandcamp fallback
- **Confidence Scoring**: SoundCloud results validated with word-level containment + fuzzy matching (configurable threshold, default 0.6)
- **Sorting Priority**: Label mapping first, then Genre mapping as fallback
- **Early-Exit Optimization**: When label already maps to destination, genre lookup is skipped (saves API calls)
- **Subgenre Hierarchy**: Subgenres automatically map to parent genres (e.g., "Electro House" → "House")
- **Fuzzy Genre Matching**: Configurable threshold (default 0.8) with 30+ genre synonyms (e.g., "hip hop" → "Hip-Hop/Rap", "dnb" → "Drum n Bass")
- **Metadata Mismatch Detection**: Compares metadata artist/title against filename using fuzzy matching. When mismatch detected (similarity < 0.6), uses filename values for online lookups instead of wrong metadata. Mismatch details logged with similarity scores and included in result JSON.
- **Metadata Enrichment**: Optional feature to write missing metadata (label, genre, album, year) from online sources back to audio files (via CLI `--enrich-metadata` or config `enrich_metadata: true`)
- **Move Control**: Configurable `move: true|false` option to enable/disable file movement (default: true). When `move: false`, the script determines destinations but doesn't move files.
- **Execution Order**: 1) dry-run check, 2) metadata enrichment (if enabled), 3) file movement (if enabled)
- **Timeouts**: 5 seconds for ffprobe (single call), 10 seconds for HTTP requests
- **Output**: Files moved to genre-specific or label-specific folders as defined in config.json
- **Logging**: JSON log of non-processed files (normal) or audit log (dry-run)
- **Caching**: In-memory cache for online lookups to avoid repeated API calls

## Configuration

### SoundCloud Setup (Optional)

For enhanced track matching via SoundCloud API:

```bash
cp .env.example .env
# Edit .env and add your SoundCloud client ID
```

To get a client ID: Open SoundCloud in your browser, play a track, open DevTools (F12) → Network tab, reload, find a request with `?client_id=`, copy the value.

### config.json

```json
{
  "genre_map": {
    "Drum n Base": "/path/to/drum-n-base",
    "House": "/path/to/house",
    "Techno, Trance": "/path/to/electronic"
  },
  "label_map": {
    "Ninja Tune": "/path/to/ninja-tune",
    "Warp Records": "/path/to/warp",
    "Planet Mu": "/path/to/planet-mu"
  },
  "label_source_tag": "label",
  "fuzzy_threshold": 0.8,
  "soundcloud_confidence_threshold": 0.6,
  "enrich_metadata": false,
  "move": true,
  "metadata": {
    "sources": ["soundcloud", "itunes", "bandcamp", "musicbrainz"]
  }
}
```

- Add more genres or labels as needed.
- The `label_map` works the same way as `genre_map` (keys can be comma-separated lists).
- If `label_source_tag` is provided, the script will try to read that specific tag (and its uppercase variant) for the label.
- If `label_source_tag` is not provided, the script checks common label-related tags: 'label', 'Label', 'TPUB', 'publisher'.
- **Subgenre Support**: Subgenres like "Electro House", "Progressive House", "Dance", "Electronic" automatically map to "House" if configured.
- **SoundCloud**: Set `soundcloud_confidence_threshold` (default 0.6) to control how strict SoundCloud matching is.
- **Metadata Sources**: `metadata.sources` controls the lookup order (default: SoundCloud → iTunes → Bandcamp → MusicBrainz).

## File Structure

```
organize_mp3s/
├── .github/workflows/   # CI/CD workflows
│   ├── test.yml         # Unit tests on push/PR
│   └── release.yml      # Build binaries + GitHub Release
├── organize_mp3s/       # Python package
│   └── __init__.py      # Version
├── pyinstaller/         # PyInstaller build config
│   └── organize.spec
├── tests/               # Unit tests
│   └── test_organize_music.py
├── assets/              # Images
├── .env.example         # SoundCloud client ID template
├── .gitignore
├── AGENTS.md            # AI agent workflow instructions
├── README.md            # This file
├── LICENSE              # MIT
├── config.json          # Genre/label to folder mapping
├── install.sh           # One-line install script
├── organize_music.py    # Main organizer script
├── pyproject.toml       # Python package config
├── *.mp3 / *.m4a        # Source files
└── organization_*.json  # Log files (generated)
```

## Release Workflow

To create a new release:

1. **Bump version** in `organize_mp3s/__init__.py`:
   ```python
   __version__ = "1.1.0"
   ```

2. **Commit and push**:
   ```bash
   git add -A && git commit -m "chore: bump version to 1.1.0"
   git push
   ```

3. **Create tag and push**:
   ```bash
   git tag v1.1.0
   git push --tags
   ```

This triggers the GitHub Actions `release.yml` workflow which builds standalone binaries for Linux (amd64) and macOS (arm64, x86_64) with bundled ffmpeg.

## For AI Agents

See [AGENTS.md](AGENTS.md) for complete workflow instructions including:
- Pre-flight Check
- Execution steps
- Result verification

## License

MIT

---

**Holger Kampffmeyer** (DJ Hulk)

- Website: [holger-kampffmeyer.de](https://holger-kampffmeyer.de)
- Email: holger.kampffmeyer+dj@gmail.com
- Instagram: [@djhulk_de](https://instagram.com/djhulk_de)
- YouTube: [@djhulk_de](https://youtube.com/@djhulk_de)
- Mixcloud: [holger-kampffmeyer](https://mixcloud.com/holger-kampffmeyer)
- LinkedIn: [holger-kampffmeyer](https://linkedin.com/in/holger-kampffmeyer-390b6789)


**Note**: This tool is designed to be used with AI coding assistants but can also be run manually via the command line.