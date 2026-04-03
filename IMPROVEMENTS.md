# Improvements for MP3/M4A Organizer

## Current Results

| Metric | Value |
|--------|-------|
| Files organized | 26 |
| Remaining | 0 |

## 🚧 Open Issues

### 1. Files with Unfindable Labels
These tracks returned no label from iTunes or Bandcamp (likely promo/pre-release):
- **Alboe - Last Push (Extended Mix)**
- **Klubbheads Present Dayne W Johnson - Dreaming (Dub Mix)**
- **Klubbheads Present Dayne W Johnson - Dreaming (Extended Mix)**
- **KREAM & SCRIPT - Turn Up The Dose (Extended Mix)**

### 2. Files with Missing Metadata
- **TDK & kali-mist - Do the Damn Thing oi** - Artist not in file metadata
- **BAND4BAND (Kurt Joseph Bootleg)** - Title not in file metadata
- **Central Cee & 21 Savage - GBP (Jay Phoenix Remix)** - Artist not in file metadata (duplicate with wrong metadata exists)

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

- Total tests: 155
- All tests passing

---

## Recent Changes

### Metadata Mismatch Detection (2026-04-03)
- **Compare metadata vs filename** - detects wrong artist/title tags using fuzzy matching
- **Automatic fallback** - uses filename artist/title for online lookups when mismatch detected
- **Logging** - warns with similarity scores for both artist and title
- **Audit trail** - mismatch details included in result JSON under `metadata_mismatch`
- **23 new tests** - covering filename parsing, normalization, mismatch detection, and integration

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