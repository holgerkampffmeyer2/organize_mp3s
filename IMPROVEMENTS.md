# Improvements for MP3/M4A Organizer

## ✅ Implemented Improvements

### 1. Genre Hierarchy / Subgenre Fallback (DONE)
Added `_extract_parent_genre()` function that maps subgenres to parent genres:
- `Electro House` → `House`
- `Progressive House` / `Progessive House` → `House`
- `Deep House` → `House`
- `Future House` → `House`
- `Dance` → `House`
- `Electronic` → `House`
- etc.

### 2. Priority Change (DONE)
Changed logic in `determine_destination()`:
- **Before**: Label mapping was tried first; genre mapping only if no label_map configured OR no label available
- **After**: Label mapping first (if label exists), then genre mapping as fallback

### 3. Extended Genre Mappings (DONE)
Added to `config.json`:
```json
"Electro House": "House",
"Progressive House": "House",
"Deep House": "House",
"Future House": "House",
"Tropical House": "House",
"Dance": "House",
"Electronic": "House"
```

## Results

| Metric | Before | After |
|--------|--------|-------|
| Files sorted | 2 | 14 |
| Files remaining | 17 | 5 |

## Remaining Files (5)

These files have no genre metadata and would require online lookup:
1. Corey James & David Pietras - Arlanda
2. Dawiid & Josef K & Broseph - Chapo
3. Kiano - Feelings
4. Kryder, Tom Staar & The Wulf - De Puta Madre
5. Regilio & Simon Kidzoo - Soledad
6. Kiro Prime - Calderon (missing artist metadata)

## Future Improvements

1. **Online Genre Lookup Fallback**: When no genre in metadata, query iTunes/MusicBrainz
2. **Configurable Priority**: Add `priority` option in config.json to control label vs genre priority
3. **More Genre Hierarchies**: Add Techno → House, Trance → Trance, DnB → DnB mappings

---

## 🚀 Planned Improvements (Phase 1 - Bandcamp Integration)

### Problem
The track "Carmelo Galati - Deeper Love (Joy Afro Mix)" failed to organize because:
- No label in metadata
- iTunes lookup didn't find genre/label
- Bandcamp has the track with explicit genre: **House/Tech House/Afro House** and label: **Feather Records**

### Solution: Add Bandcamp as Genre/Label Source

#### Implementation Plan

**1. Add Bandcamp Genre Lookup Function**
```python
def get_genre_from_bandcamp(artist: str, title: str) -> Optional[str]:
    """
    Lookup genre and label via Bandcamp search.
    Bandcamp is excellent for electronic music genres.
    
    Returns:
        Tuple of (genre, label) or (None, None)
    """
```

**2. Extended Genre Hierarchy**
Add more parent genre mappings in `_extract_parent_genre()`:
- `Afro House` → `House`
- `Disco House` → `House`
- `Tech House` → `House`
- `Deep House` → `House`
- `Future House` → `House`
- `Melodic House` → `House`
- `Organic House` → `House`

**3. Online Lookup Chain Update**
Current: iTunes → MusicBrainz → Discogs
New: iTunes → Bandcamp → MusicBrainz → Discogs

**4. Label Lookup Enhancement**
- Add Bandcamp as label source fallback
- Parse label from Bandcamp metadata

#### Code Changes Required

| File | Changes |
|------|---------|
| `organize_music.py` | Add `get_genre_from_bandcamp()`, update `get_genre_online()`, extend `_extract_parent_genre()` |
| `tests/test_organize_music.py` | Add tests for Bandcamp lookup |

#### Risk Assessment
- **Bandcamp scraping**: Low risk - uses public search API
- **Rate limiting**: Medium - add delays between requests
- **HTML parsing**: Low - use simple regex or beautifulsoup if needed

#### Timeline
- Implementation: ~1-2 hours
- Testing: ~30 minutes
- Total: ~2-3 hours

---

## 📋 Future Phases (Not in Scope for Phase 1)

### Phase 2: Multi-Source Confidence
- Add Discogs API (needs token)
- Genre confidence scores from multiple sources
- Voting mechanism for genre selection

### Phase 3: Advanced Features
- Persistent SQLite cache for genre/label lookups
- Fuzzy genre matching
- Auto-generate config.json genre mappings
