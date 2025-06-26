# Changelog

All notable changes to the Trade-Up Engine project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-06-25

### Added
- Comprehensive test structure with unit and integration tests
- Professional README with detailed setup instructions
- API documentation in `docs/API.md`
- Setup script for easy installation
- `.env.example` template for configuration
- Proper error handling with JSON responses for API endpoints
- Development dependencies (pytest, black, isort, mypy)
- Changelog to track version history

### Changed
- Updated all dependencies to latest stable versions
- Reorganized test files into proper test directory structure
- Improved error handling across the application
- Enhanced .gitignore to exclude sensitive and generated files
- Standardized import patterns throughout the codebase

### Fixed
- Config page now works correctly with proper key mappings
- Inventory page template rendering issues
- Import consistency issues across modules
- Security issue with .env file in version control

### Removed
- Test and debug files from root directory
- Duplicate `api/` directory at root level
- Unnecessary config files (scenario_results.json, unified_config.py)
- All `__pycache__` directories and `.pyc` files
- Oddly named files from automated PRs

### Security
- Removed credentials from version control
- Added .env to .gitignore
- Created .env.example with placeholder values

## [1.5.0] - 2024-06-24

### Changed
- Major refactoring of amortization calculations
- Updated to use audited calculation formula from risk team
- Separated IVA calculation for better accuracy

### Fixed
- Amortization table columns now add up correctly
- Custom configuration values properly applied
- Frontend/backend API synchronization issues