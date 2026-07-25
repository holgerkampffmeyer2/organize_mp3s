# Organization & Sorting Specification

## ADDED Requirements

### Requirement: Genre & Label Mapping
The system SHALL sort audio files into destination folders defined in `config.json` via `genre_map` and `label_map`, prioritizing label maps.

#### Scenario: Sort by label map
- **WHEN** track label matches an entry in `label_map`
- **THEN** file is moved to the corresponding destination folder

#### Scenario: Sort by genre map fallback
- **WHEN** label does not match but genre matches `genre_map`
- **THEN** file is moved to the genre destination folder

### Requirement: Subgenre & Fuzzy Matching
The system SHALL automatically map subgenres to parent genres and resolve genre synonyms using fuzzy matching.

#### Scenario: Subgenre mapping
- **WHEN** track genre is a subgenre like "Electro House"
- **THEN** system maps it to parent genre "House"

### Requirement: Dry-Run Mode
The system SHALL support dry-run mode (`--dry-run` or `-n`) to simulate organization without moving files, generating an audit log.

#### Scenario: Run dry-run
- **WHEN** user executes with `--dry-run`
- **THEN** files are not moved and `organization_audit.json` is generated
