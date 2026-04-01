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
"Natural Rhythm": "House"
```

## Current Results

| Metric | Value |
|--------|-------|
| Files organized | ~37 |
| Remaining (label_missing) | 7 |
| Remaining (missing_metadata) | 2 |
| Remaining (label_not_mapped) | 1 |

## 🚧 Open Issues

### 1. Files Not Yet Organized (10 remaining)
1. **Corey James & David Pietras - Arlanda** - no label/genre found online
2. **Dawiid & Josef K & Broseph - Chapo** - no label/genre found online
3. **Kiano - Feelings** - no label/genre found online
4. **Kryder, Tom Staar & The Wulf - De Puta Madre** - no label/genre found online
5. **Regilio & Simon Kidzoo - Soledad** - no label/genre found online
6. **Salt Queen - ARE U OK** - label "Salt Queen" found but not in config
7. **TDK & kali-mist - Do the Damn Thing** - missing artist metadata
8. **Kiro Prime - Calderon** - missing artist metadata
9. **Various "target_exists"** - files already in destination folders

### 2. SoundCloud Integration Missing
The track "Eminem, Nate Dogg - Shake That (Jordan Dae Remix)" has Genre=House on SoundCloud but we couldn't detect it via our current lookups. Could add SoundCloud scraping.

### 3. Salt Queen Label Not Mapped
Label found via online lookup but not in config. Either add to config or add auto-detection logic.

---

## 🔜 Future Improvements

### Priority 1: Quick Wins
1. **Add Salt Queen to label_map** → House
2. **Add more genre mappings** for uncovered genres

### Priority 2: Better Online Sources
1. **SoundCloud genre scraping** - for tracks not on Bandcamp
2. **iTunes improved search** - better matching for remixes

### Priority 3: Advanced Features
1. **Persistent cache** - SQLite for genre/label lookups
2. **Fuzzy genre matching** - handle misspellings
3. **Auto-add unknown labels** - detect label from filename patterns
4. **Configurable priority** - control label vs genre priority in config

---

## Test Coverage

- Total tests: 102
- Coverage includes:
  - Bandcamp JSON-LD parsing
  - Genre hierarchy extraction
  - Metadata tag extraction (timeout, errors)
  - Edge cases for genre/label lookup
  - Process file flow with mocks