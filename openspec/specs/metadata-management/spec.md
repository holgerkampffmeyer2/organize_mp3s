# metadata-management Specification

## Purpose
TBD - created by archiving change capture-current-feature-set. Update Purpose after archive.
## Requirements
### Requirement: Metadata Extraction
The system SHALL extract artist, title, genre, and label from audio files using ffprobe.

#### Scenario: Extract tags from file
- **WHEN** processing an audio file
- **THEN** system extracts embedded tags via a single ffprobe call

### Requirement: Online Lookup & Confidence Scoring
The system SHALL query online sources (SoundCloud, iTunes, Bandcamp, MusicBrainz) to lookup missing genres and labels with confidence scoring.

#### Scenario: SoundCloud confidence matching
- **WHEN** querying SoundCloud with a SoundCloud client ID
- **THEN** system validates results against confidence threshold (default 0.6)

### Requirement: Metadata Enrichment
The system SHALL support enriching audio files with missing metadata tags when requested via `--enrich-metadata` or config.

#### Scenario: Enrich missing tags
- **WHEN** running with enrichment enabled
- **THEN** missing label, genre, album, and year tags are written back to the audio file

