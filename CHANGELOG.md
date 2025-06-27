# Changelog

## [2.1.0] - 2025-06-27

### Added
- Comprehensive AI assistant guide (CLAUDE.md)
- Domain models for type safety (Customer, Vehicle, Offer)
- Complete test suite with unit and integration tests
- Test runner script (`run_tests.py`)
- Migration helpers for transitioning from dictionaries to domain models
- Circuit breaker monitoring API endpoints
- Configuration migration guide

### Changed
- Consolidated all configuration to single source (config/schema.py)
- Simplified README to be more concise and actionable
- Updated all documentation to be clear and non-redundant
- Improved constants.py to use config facade

### Fixed
- IVA calculation bug in smart_search.py (was multiplying by 0.16 instead of 1.16)
- Completed SearchRequest model definition
- Added missing newlines to files
- Config value inconsistencies across files

### Removed
- Duplicate API documentation files
- Outdated refactoring reports
- Confusing architecture documentation (consolidated into single file)

## [2.0.0] - 2024-12-15

### Added
- Service layer architecture
- Two-stage filtering for performance
- Smart caching with TTL
- Domain models foundation
- Comprehensive configuration system
- Financial audit trail
- Decimal precision support

### Changed
- Eliminated global DataFrames
- Moved to on-demand data queries
- Refactored to service-oriented architecture

### Removed
- Legacy global state
- Pre-loaded dataframes
- Hardcoded configuration values

## [1.0.0] - 2024-06-25

### Added
- Initial release
- Basic offer generation
- Customer management
- Payment calculations
- Web interface