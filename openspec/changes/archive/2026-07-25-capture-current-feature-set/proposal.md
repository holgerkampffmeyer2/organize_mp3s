## Why

The project currently implements automated MP3/M4A file organization with online genre and label lookup, metadata-based sorting, fuzzy matching, and metadata enrichment, but lacks formal OpenSpec specifications documenting this feature set. Capturing the current features as OpenSpec specifications enables structured versioning, requirement tracking, and reliable delta spec synchronization.

## What Changes

- Introduce formal OpenSpec specifications for the MP3/M4A organizer project.
- Document existing capabilities: file discovery & batch processing, metadata management & online lookup (SoundCloud, iTunes, Bandcamp, MusicBrainz), and organization sorting (genre/label mapping, subgenre hierarchy, fuzzy matching, dry-run mode, enrichment).

## Capabilities

### New Capabilities
- `file-discovery`: Scanning source directories for MP3 and M4A audio files.
- `metadata-management`: Extracting metadata via ffprobe, online genre/label lookup with confidence scoring, metadata mismatch detection, and tag enrichment.
- `organization-sorting`: Sorting files based on configurable genre maps and label maps, subgenre hierarchy mapping, fuzzy synonym matching, dry-run vs move modes, and JSON audit/result logging.

### Modified Capabilities
<!-- None -->

## Impact
- No changes to application code; purely documentation and formal specification of existing behavior.
