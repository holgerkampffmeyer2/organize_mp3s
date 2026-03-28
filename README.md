# MP3/M4A Organizer

![Illustration](./assets/organize_mp3s.png)

AI-agent driven MP3/M4A organization with online genre lookup, metadata-based sorting, and configurable destination mapping. Designed to be controlled by AI coding assistants like [opencode](https://opencode.ai) or Claude Code.

## How It Works

An AI agent reads `AGENT.md` and executes the organization workflow:

```
AI Agent reads AGENT.md → Pre-flight Check → Executes organize_music.py → Monitors results → Verifies output
```

The agent handles:
- Prerequisites check (ffmpeg, python3)
- File discovery and batch processing decisions
- Metadata extraction from files
- Online genre lookup: iTunes → MusicBrainz
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
```

- `source_directory`: The directory to scan for audio files (defaults to current directory if not provided).
- The script will create `organization_results.json` (normal mode) or `organization_audit.json` (dry-run) in the source directory.

## Prerequisites

```bash
sudo apt update
sudo apt install ffmpeg python3
```

## Technical Details

- **Metadata Source**: Artist and title from file metadata (ffprobe)
- **Genre Lookup**: iTunes Search API (primary), MusicBrainz API (fallback)
- **Timeouts**: 5 seconds for ffprobe, 10 seconds for HTTP requests
- **Output**: Files moved to genre-specific folders as defined in config.json
- **Logging**: JSON log of non-processed files (normal) or audit log (dry-run)

## Configuration

Create a `config.json` file in the same directory as the script:

```json
{
  "genre_map": {
    "Drum n Base": "/path/to/drum-n-base",
    "House": "/path/to/house",
    "Techno, Trance": "/path/to/electronic"
  }
}
```

## File Structure

```
organize_mp3s/
├── AGENT.md           # AI agent workflow instructions (this file)
├── README.md          # This file
├── organize_music.py  # Python organizer script
├── config.json        # Genre to folder mapping
├── tests/             # Unit tests
│   ├── __init__.py
│   └── test_organize_music.py
├── *.mp3              # Source MP3 files
├── *.m4a              # Source M4A files
└── organization_*.json # Log files (generated)
```

## For AI Agents

See [AGENT.md](AGENT.md) for complete workflow instructions including:
- Pre-flight Check
- Execution steps
- Result verification

## License

MIT

**Holger Kampffmeyer** (DJ Hulk)

- Website: [holger-kampffmeyer.de](https://holger-kampffmeyer.de)
- Email: holger.kampffmeyer+dj@gmail.com
- Instagram: [@djhulk_de](https://instagram.com/djhulk_de)
- YouTube: [@djhulk_de](https://youtube.com/@djhulk_de)
- Mixcloud: [holger-kampffmeyer](https://mixcloud.com/holger-kampffmeyer)
- LinkedIn: [holger-kampffmeyer](https://linkedin.com/in/holger-kampffmeyer-390b6789)

---

**Note**: This tool is designed to be used with AI coding assistants but can also be run manually via the command line.