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
- Wikisource: select books by page name with `--wikisource-pages`, stable across feed updates unlike `--books` positions (#73)
- Cache optimized EPUB and HTML images under an S3 bucket (`--optimization-cache`), keyed by the input image content so Project Gutenberg's frequent file rebuilds no longer defeat the cache (#32)
- One More Library: add the `onemorelibrary` source (aliases `OML`), scraping public-domain EPUB/PDF books with `--categories` and `--oml-ids` filters (#94)
- Show Creative Commons licenses as a localized name linking to the license, instead of the raw value of the source (e.g. a bare `http://creativecommons.org/licenses/by-sa/3.0` for Wikisource). The scraper reduces license URIs, short codes and names to an identifier (`licenseId` in the book JSON) shared by all sources (#17)
- UI: bring back the interface language switcher (`config.json` now carries the distinct book languages and a stable ZIM name). A ZIM built with a single language defaults its interface to that language instead of the browser's; a multi-language ZIM still defaults to the browser's. The switcher is a searchable, translate-icon-triggered list of native + English language names, with the browser and ZIM languages pinned first, and persists the choice per ZIM instead of globally (#35)
- UI: only offer a language in the interface switcher once its translation is at least 80% complete, counted per source (`common` + that source's own namespace) rather than combined across every source, so a barely-started translation isn't offered and adding a new source's untranslated strings can't silently drop an already-translated language from unrelated ZIMs (#113)
- UI: filter books, authors and collections by book language from a single control in the breadcrumbs bar, applied everywhere (books list, authors list, collections, home's popular/selected sections, author and collection detail pages). Author and collection previews now carry a per-language book count/popularity breakdown so filtered counts stay accurate without extra fetches (#101)

### Changed

- Gutenberg: scrape only the catalog entries typed `Text`. The dump also lists ~1250 audio recordings, images and datasets whose info page is all the mirror has; they used to be downloaded, fail in every format, and be dropped again with 1128 "could not be downloaded in any format" warnings in every run's log (#129)
- UI: upgrade to Vuetify 4, migrating to the Material Design 3 typography classes, grid alignment utility classes, and restoring the CSS reset the new version dropped (#26)
- UI: replace book grid borders with rounded card backgrounds, highlighted on hover, in book grid, book list, book carousel and author carousel (#61, #82)
- Gutenberg: replace `--with-author-details` with `--with-author-bio` and `--with-author-portrait` (#66)
- Author details: fetch biographies and portraits in the language the ZIM is built in, resolved through Wikipedia's interlanguage links, and keep the English picture when the localized article has none (#65, #84)
- Gutenberg: prefer the cover declared by the downloaded EPUB over Project Gutenberg's ~200px `cover.medium.jpg` thumbnail, which yields sharper covers without an extra download; the thumbnail stays as fallback (#68)
- Fine tune UI display (margins, ...) (#85)
- UI: blur background content behind ZimInfoDialog (#87)
- Rename the ambiguous `Creator.name`/`first_name`/`last_name` to `display_name` (the formatted string shown to readers) and `sort_name` (the last name alone, used only to sort, never displayed), dropping the unused decomposed first/last name fields; the JSON/UI `name` field is now `displayName` (#64)
- UI: when the application fails to start, explain that reloading is unlikely to help and point to the more limited No-JavaScript interface instead (#119)
- One More Library and Open Textbook Library: emit one broad collection per book instead of hundreds of leaf categories. OML uses the category above the book's own, OTL resolves every subject to its root through the published subject tree because textbook records often omit the ancestors; document the collection policy, give both sources dedicated category icons, and drop the OTL subject translations that no longer correspond to an emitted collection (#117)

### Fixed

- UI: cap the book-language filter dropdown's height with a scrollbar instead of letting it grow unbounded, and add the same type-to-filter search box the interface-language switcher already had (#145)
- Gutenberg: stop a corrupted book file (an HTML error page served with a 200 status, a truncated transfer) from dropping the whole book. Downloaded EPUB/PDF content is validated before it is stored, an unreadable EPUB costs its format instead of the book, and a readable EPUB that cannot be optimized is kept unoptimized instead of re-raising into the pipeline's generic handler (#135)
- UI: fix breadcrumbs always ellipsizing the second item regardless of available space, and let every item (including the current page's, which can be an arbitrarily long book title or author name) ellipsize instead of overflowing when space is tight, on both desktop and mobile (#143)
- Keep the original extension when appending `.webp` to converted image output filenames, so two source images sharing a basename but differing only in extension (e.g. `001.jpg` and `001.png`) no longer collide on the same ZIM path and silently drop one of the two (#133)
- UI: make the empty state message readable in both themes by using the normal text color inside the tinted alert, rounding its corners, and switching the `info` accent to the existing palette blues (the dark theme also gets its own info/error/success/warning colors instead of reusing the light ones) (#123)
- Wikisource: ignore non-image metadata covers in EPUBs and use declared-only covers so books without a cover fall back to the placeholder instead of extracting the site logo (#16)
- Remove leftover `common` translation keys (`uiLanguage`, `chooseLanguage`, `anyCatalog`, `search`, `mainLanguages`, `otherLanguages`, `navigateTo`, `sortBy`) from removed features, which were counting against every translator's completion percentage for no reason (#112)
- UI: switch layout disposition to RTL when an RTL language is selected, and convert physical margins/paddings to logical properties (#86)
- Resolve ZIM language metadata for ISO 639-3 codes with no ISO 639-1 equivalent (e.g. `grc`/Ancient Greek) without having to hardcode each one, and fix `fur`/Friulian being mislabeled as the unrelated `fvr`/Fur language (#102)
- Gutenberg: stop failing to build the `mul` ZIM when any book carries an unmappable language code (`myn`, `nai`); such codes are now dropped from ZIM language metadata, with a warning logged, instead of blocking the whole build (#121)
- Gutenberg: stop rejecting the whole HTML zip for books that bundle images, stylesheets or audio under a subfolder other than `images/` (e.g. `music/`, `style/`+`img/`); any subfolder layout is now extracted under the book's own ZIM folder, with every reference to it rewritten accordingly, instead of only `images/` being allowed and the rest silently falling back to a worse format (#131)

- Promote Wikisource `issued` to standard `published` metadata (#10)
- Wikisource: stop offering the withdrawn `xhtml` format, and fail early when a requested format is not offered by ws-export (#11)
- About page: render the introduction and mission paragraphs a source declares, instead of a fixed number, so a source with no mission no longer prints raw translation keys (#18, #19)
- Fix UI browser language detection: use all preferred browser languages and stop persisting the auto-detected language (#50)
- UI: sort collections alphabetically by display name in sidebar (#48)
- Gutenberg: prefer the bundled cover asset over a `<link rel="icon">` href, which PG sometimes mistags with an unrelated illustration (#49)
- Open Textbook Library: trust the container's system CA store, which includes the `emSign ECC Root CA - G3` issuer of open.umn.edu that `certifi` does not ship, and re-enable the OTL integration tests (#83)
- Gutenberg: stop scrambling author names with a free-text suffix (e.g. "active 1799-1828"), displaying it in parentheses after the name instead of folding it into the first name (#64)
- Gutenberg: place a recognized title before the name ("Sir Thomas Browne", "Lady Frances Balfour") and a generational suffix after it ("Horatio Alger Jr.") instead of in parentheses; any other suffix (dates, "Saint", other titles, ...) still defaults to parentheses (#64)
- Stop mentioning the author twice in a book's full-text search index entry when the book has no description (#64)
- Wikisource: drop the `base_url` and `engine` state the metadata port never used, and let each source declare its metadata constructor kwargs through `metadata_options` (#9)

## [1.0.0] - 2026-09-25

- initial version of `papers` scraper, successor of `gutenberg` scraper with support for multiple sources and a brand new Vue.JS UI
