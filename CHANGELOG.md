# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
as of 2.0.0.

## [Unreleased]

### Added

- Add author biographies and portraits from Wikipedia with `--with-author-details` (#31)
- Add support for sources without popularity: the source declares it, `config.json` carries the flag, and the UI hides flames and the most popular book and falls back to alphabetical sorting (#14)
- Wikisource: add the library mission to the about page (#18)
- Use book cover component with fallback images everywhere (#22)
- Hide the "Collections" navigation item and homepage shelves when the ZIM only has a single collection (#3)
- Revisit book grid for a better design and less rendering issues (#46)

### Changed

- UI: replace book grid borders with rounded card backgrounds, highlighted on hover, in book grid, book list, book carousel and author carousel

### Fixed

- Promote Wikisource `issued` to standard `published` metadata (#10)
- Wikisource: stop offering the withdrawn `xhtml` format, and fail early when a requested format is not offered by ws-export (#11)
- About page: render the introduction and mission paragraphs a source declares, instead of a fixed number, so a source with no mission no longer prints raw translation keys (#18, #19)
- Fix UI browser language detection: use all preferred browser languages and stop persisting the auto-detected language (#50)
- UI: sort collections alphabetically by display name in sidebar (#48)
- Gutenberg: prefer the bundled cover asset over a `<link rel="icon">` href, which PG sometimes mistags with an unrelated illustration (#49)
- Gutenberg: fetch only author portraits without biographies for non-English ZIMs (#66)

## [1.0.0] - 2026-09-25

- initial version of `papers` scraper, successor of `gutenberg` scraper with support for multiple sources and a brand new Vue.JS UI
