# Improvements for MP3/M4A Organizer

## ✅ Implemented Improvements

### 1. Genre Hierarchy / Subgenre Fallback (DONE)
Added `_extract_parent_genre()` function that maps subgenres to parent genres:
- `Electro House` → `House`
- `Progressive House` → `House`
- `Deep House` → `House`
- `Future House` → `House`
- `Dance` → `House`
- `Electronic` → `House`
- `Afro House` → `House`
- `Tech House` → `House`
- `Ambient` → `Ambient`
- `Dubstep` → `Dubstep`
- `Breakbeat` → `Breakbeat`
- `Experimental` → `Experimental`

### 2. Bandcamp Integration (DONE)
- Added `get_genre_from_bandcamp()` function
- Parses JSON-LD schema for genre keywords
- Direct URL fallback for artist pages
- Label extraction from Bandcamp metadata

### 3. Improved Genre Fallback Logic (DONE)
- Online genre lookup when metadata genre not in config
- Title cleaning: removes artist prefix for better online lookups
- Added to config: `Hip-Hop/Rap` → `House`

### 4. Extended Genre Mappings (DONE)
Current `config.json` genre_map:
```json
"Drum n Base": "DnB",
"House": "House",
"Deep Techno": "House",
"Techno": "House",
"Tech House": "House",
"Electro House": "House",
"Progressive House": "House",
"Deep House": "House",
"Future House": "House",
"Tropical House": "House",
"Dance": "House",
"Electronic": "House",
"Hip-Hop/Rap": "House"
```

### 5. Extended Label Mappings (DONE)
```json
"MixCult Records": "House",
"SHODAN RECORDS": "House",
"Warner Music Group": "House",
"Music is 4 Lovers": "House",
"Unchained Soul Records": "DnB",
"Feather Records": "House",
"Sephia": "DnB",
"Samples From Mars": "House",
"Tankfloor": "House",
"Natural Rhythm": "House",
"Salt Queen": "House"
```

### 6. Fuzzy Genre Matching (DONE)
- Added `_find_fuzzy_genre()` with difflib (built-in)
- Added `GENRE_SYNONYMS` dict with 30+ genre synonyms
- Threshold: 80% similarity
- Covers: hip hop, dnb, edm, drum & bass variants, etc.

## Current Results

| Metric | Value |
|--------|-------|
| Files organized | 21 |
| Remaining (missing_metadata) | 1 |

## 🚧 Open Issues

### 1. Files Not Yet Organized (1 remaining)
1. **TDK & kali-mist - Do the Damn Thing** - missing artist metadata in file

(Alle 5 "label_missing" Tracks wurden heute organisiert - sie waren bereits in den Zielordnern)

---

## 🔜 Future Improvements

### Priority 1: Quick Wins
1. **Add more label mappings** for uncovered tracks (falls neue auftauchen)

### Priority 2: Better Online Sources
1. **SoundCloud genre scraping** - falls weitere Tracks nicht gefunden werden

### Priority 3: Advanced Features
1. **Persistent cache** - SQLite für Genre/Label Lookups
2. **Auto-add unknown labels** - Label aus Filename erkennen
3. **Configurable priority** - Label vs Genre Priorität konfigurierbar

---

## Test Coverage

- Total tests: 114
- Coverage includes:
  - Bandcamp JSON-LD parsing
  - Genre hierarchy extraction
  - Fuzzy genre matching
  - Genre synonyms
  - Metadata tag extraction (timeout, errors)
  - Edge cases for genre/label lookup
  - Process file flow with mocks