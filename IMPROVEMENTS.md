# Improvements for MP3/M4A Organizer

## Current Results

| Metric | Value |
|--------|-------|
| Files organized | 21 |
| Remaining | 1 (missing_metadata_artist) |

## 🚧 Open Issues

### 1. File with Missing Metadata
- **TDK &kali-mist - Do the Damn Thing** - Artist not in file metadata

---

## 🔜 Future Improvements

### Priority 1: Quick Wins
- Add more label mappings for new tracks

### Priority 2: Better Online Sources
- **SoundCloud genre scraping** - fallback for unlisted tracks

### Priority 3: Advanced Features
- **Persistent cache** - SQLite for genre/label lookups
- **Auto-add unknown labels** - detect from filename patterns
- **Configurable priority** - control label vs genre priority

---

## Test Coverage

- Total tests: 114
- All tests passing