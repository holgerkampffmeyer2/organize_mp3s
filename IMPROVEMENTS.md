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
