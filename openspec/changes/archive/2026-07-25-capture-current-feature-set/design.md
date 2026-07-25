## Context

The repository is an established Python CLI tool and Python package for organizing MP3 and M4A audio files based on metadata, online genre/label lookup, subgenre hierarchies, and fuzzy matching. It includes robust unit tests (`tests/test_organize_music.py`) and modular architecture.

## Goals / Non-Goals

**Goals:**
- Formalize the existing feature set into OpenSpec specifications (`specs/`).
- Document all core functional areas: file discovery, metadata management & online lookup, and organization sorting & mapping.

**Non-Goals:**
- Refactoring existing implementation code as part of this specification proposal.

## Decisions

- **Modular Specifications**: Divide specs into separate capability files (`file-discovery`, `metadata-management`, `organization-sorting`) mirroring the system architecture.
- **OpenSpec Convention**: Follow spec-driven development standards with standard ADDED requirements and scenarios.

## Risks / Trade-offs

- [Out of sync documentation] → Mitigation: Ensure specs accurately reflect current implementation and test coverage.
