# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6] - 2026-02-16

### Changed

- Updated compatibility for Textual 8 APIs and typing.

## [0.1.5] - 2026-02-12

### Added

- Display download progress in megabytes in the main view.

### Fixed

- Re-centered the progress bar in the updated responsive layout.

### Changed

- Improved responsive behavior of the main layout and column proportions.
- Polished modal styling and help screen density/alignment for better readability.

## [0.1.4] - 2026-01-19

### Fixed

- Centered the progress bar container.
- Constrained progress bar width to prevent layout overflow.

## [0.1.3] - 2026-01-09

### Changed

- Improved library fetching performance by requesting pages concurrently.

## [0.1.2] - 2026-01-06

### Added

- Added a shared search helper module.
- Added test configuration and development dependencies.
- Added test coverage for filter/search helpers, cache and URL helpers, library parsing, table utilities, email extraction, and filter debounce behavior.

### Changed

- Refactored existing search/filter logic to use shared helpers.
- Improved packaging and CI setup for project distribution.

## [0.1.1] - 2026-01-06

### Added

- Added playback speed controls with up/down key bindings.
- Added an `f` key binding to toggle finished/unfinished status.
- Added responsive table columns and a redesigned top bar/help experience.
- Added a stats screen with listening/account statistics and persisted email config.
- Added a debounced filter view with cached search and refresh toggle.

### Changed

- Refined UI layout and styling with a broad responsive redesign.
- Updated behavior so finished books are removed from cache.

### Fixed

- Corrected Python version and installation compatibility details for Audible/pipx environments.

## [0.1.0] - 2025-12-25

FIRST VERSION
