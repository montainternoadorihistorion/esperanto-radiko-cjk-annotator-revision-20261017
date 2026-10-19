# Exact `@greganta@` / `@preganta@` correction

Adopted 2026-10-19 after the read-only review against baseline
`469806409ac3c3cc8f3368bdb24b792cead6f81c`.

## Decision and scope

The user approved the existing `greg / ant / a` and `preg / ant / a`
decompositions for the **exact lowercase payloads** `@greganta@` and
`@preganta@`. Both editions and all three bundled display modes in the
Japanese, Chinese and Korean apps use these decompositions. `@kordonita@`
already uses `kordon / it / a` and remains unchanged.

Before this change, the local replacement order found `gant` first, giving
`g + re + gant + a` and `pre + gant + a`. The resulting text could already be
reversed to the original Esperanto spelling. This correction fixes the root
boundaries and learning annotations, rather than addressing an inverse-key
failure. The selected edition's existing local atom renderings now produce
`群ᴳ在a` and `压ᴾᴳ在a`; the annotation mode uses the corresponding existing
`greg`, `preg` and `ant` glosses for each language.

## Implementation boundaries

* The final optional API argument `reviewed_local_decompositions=False` is an
  explicit opt-in. Standalone calls retain their prior behavior by default.
* Main-app and manual-preview calls enable it only when loading one of the
  canonical bundled files. Uploaded or copied JSON files do not opt in.
* Only recognized `@` payloads exactly equal to `greganta` or `preganta` are
  affected. Capitalization, plurals, longer words, surrounding spaces and
  multiword payloads retain their prior processing. Existing percent
  protection, email detection and marker parsing are unchanged.
* The helper reads the selected local roots. It does not hardcode a glyph,
  identifier or translated annotation. Missing or conflicting required atoms
  raise an error instead of silently creating a new assignment.
* Active local rendering and the compatibility local-list API share the same
  helper. Serial execution, both parallel fallbacks, worker processes and the
  app's automatic second pass all propagate the opt-in.
* Existing global manual corrections keep governing normal text; `@` still
  explicitly selects local processing. No global reordering or broader
  automatic-decomposition rule was added.

No assignment files, identifiers, JSON rule tables, inverse tables, HTML
recovery parser or normal-text segmentation were edited. The exact-global
allowlist was not extended: global exact rules are missing or unsuitable for
these local requests, and reusing the legacy `kordonita` identity rule would
remove its correct local decomposition.

## Validation

`tests/test_at_two_exact_fix.py` checks the opt-in/default boundary, canonical
paths, custom tables, missing/conflicting atoms, exact payload limits, marker
protection/collisions, compatibility API, global manual priority, serial and
parallel execution, both editions and all three languages/modes, root/ruby
content, plain inverse and standard-HTML recovery. It also checks propagation
through all main-app and manual-preview call sites, and normal text during
the real automatic second pass.

Independent review, corpus audit and deployment evidence are recorded
separately under this directory. These tests do not broaden the user-approved
scope to other inflections or to `@kordonita@`.
