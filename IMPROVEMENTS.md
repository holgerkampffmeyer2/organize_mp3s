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

- Total tests: 132
- All tests passing

---

## Recent Optimizations (2025-04-03)

### Performance
- **Single ffprobe call** - replaced 5+ separate calls with one JSON-based extraction
- **Unified iTunes lookup** - `_lookup_itunes_all_metadata()` returns label, genre, album, year, track in one API call
- **Early-exit for label mapping** - skips genre lookup when label already maps to destination
- **Deduplicated enrichment writes** - genre not written twice in early-exit path

### Code Quality
- **Removed dead Discogs code** - stub without token was never functional
- **Removed duplicate `get_genre_from_metadata`** - was defined twice
- **Genre normalization from wav-to-aac-converter** - consistent `_normalize_genre` and `_is_electronic_genre` logic

### API Efficiency
| Before | After |
|--------|-------|
| 5+ ffprobe subprocess calls | 1 ffprobe call (JSON) |
| 3 separate iTunes API calls | 1 unified iTunes call |
| Genre lookup always executed | Early-exit when label maps |