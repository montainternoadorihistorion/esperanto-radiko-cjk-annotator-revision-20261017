# Independent local review

Reviewed source: `fe1e11218f125218189d1dea6e45e7afbf4cb15e`, compared with `15f9b8aef376109fb0c064d9f4a052f35a58fc52`.

No material issue found. The production diff is confined to the six manual/download pages; the seventh changed file records the decision. Conversion engines, edition handling, assignments, identifiers, dictionaries and original download data are unchanged. AST comparisons confirm that download payload/filename expressions and manual-page functions are unchanged. The source-link guard checks 22 distinct paths in each language/edition, including the three downloadable auxiliary JSON files.

The independent tests launched each language in a fresh Python process through the real main entrypoint and used Streamlit AppTest navigation to the existing pages. Upload/download transport was instrumented; imports, saving edits, edition selection, original UI calls and link checks ran through production code.

All six language/edition states passed:

- 36 small download payloads matched their selected source files byte for byte; names, labels and SHA-256 hashes are recorded.
- 18 large data links matched selected asset paths and Git blobs at the reviewed commit; 12 source/ZIP URLs used that same commit.
- Each session imported `semajn/o` and `las/is` (including deliberately stale imported glyph data), added `greg/ant/a`, then changed the imported `las/is` decomposition to `las/i/s` through the actual save button. Imported glyphs were rebuilt correctly. All three session entries survived edition switching and navigation to the data page.
- 12 edition transitions retained the entered draft and saved edits. The 18 backup comparisons covered the selected edition, the other edition and the return to the original edition. Returned backup bytes were identical; `las` used `放` for current and `留` for legacy, and edition/signature metadata and names matched.
- 12 navigation targets rendered correctly. Six actual manual-to-data transitions retained the saved session entries. Downloaded bundled `user_corrections.json` remained the unchanged baseline and excluded session additions/edits.
- Actual visible text contained the localized raw-data explanation, reproduction requirements, old-edition caveat, custom-JSON caveat, bundled/session distinction and fixed-source caption.

`app_test.py` produced `app_JA.json`, `app_ZH.json` and `app_KO.json`. `aggregate.py` checks the source diff and rendered guidance and writes `summary.json`. AppTest is a local UI test; it is not a Cloud/browser download test or a new exhaustive conversion audit. The source guard path enumeration separately uses its AST in an isolated recording harness; actual fixed URLs and committed asset blobs are verified by the page tests.

Two test-harness assumptions were corrected before the final passing run: page files must be reached from the main entrypoint for Streamlit navigation; result filenames incorporate the session-aware result signature rather than the assignment signature alone. Stream-backed downloads are recorded without changing their position. No application change resulted from these harness corrections.

## Independent review of saved Cloud evidence

The parent agent exercised the deployed Cloud pages at source commit `a9427afff3e1f3e591a36db04bf759d8b6cfcf3e`. `cloud_evidence_review.py` independently rehashed all 42 saved native browser downloads. The 36 data downloads matched the selected original assets byte for byte. Six manual backups exactly matched a newly built `las/is` correction, including new/old glyphs, annotations, edition metadata, content-derived names and signatures. Bundled correction files remained the baseline and differed from session backups. Chrome's filename collision suffixes are retained in evidence and excluded only when comparing the application-supplied name.

Six settled data-page states verified localized guidance, selected edition and source/ZIP/data link paths. The source record contains 12 observations; final verification uses the last record for each language/edition, at zero-based indices 6–11. Earlier captures taken during the edition rerun temporarily combined a newly selected control with prior links; all were preserved and were superseded by settled captures. This was a capture-timing issue and required no application change. Six manual-page text records also show the correct `放`/`留` preview, saved `las/is` entry and backup/navigation labels. Three recorded return-navigation checks preserve the selected current edition and saved entry.

The final independent results and source record hashes are in `cloud_evidence_review.json`. This reviewer did not operate the browser or perform HTTP/ZIP checks; those are separate parent/audit-agent evidence. No Cloud upload was tested in this turn; imports were tested locally through AppTest.
