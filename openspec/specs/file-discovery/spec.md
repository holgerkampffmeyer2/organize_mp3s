# file-discovery Specification

## Purpose
TBD - created by archiving change capture-current-feature-set. Update Purpose after archive.
## Requirements
### Requirement: Scan Source Directory
The system SHALL scan the specified source directory (defaulting to current directory) for audio files.

#### Scenario: Scan default directory
- **WHEN** user runs organizer without arguments
- **THEN** system scans current directory for MP3 and M4A files

#### Scenario: Scan custom directory
- **WHEN** user passes a directory path argument
- **THEN** system scans specified directory for MP3 and M4A files

