# Enhancements

Ideas to work through after the build (after L1–L8). Newest last. See `SPEC.md`
§0 for the working protocol and §9 for the task list.

**Format:** id, date, title, description, related spec task (if any), status.

---

## Open

### ENH-001 — Historical / multi-season data

- **Date:** 2026-09-18
- **Requested by:** league owner
- **Description:** Fetch and render past seasons, not just the current one. The
  ESPN endpoint accepts any season — confirmed live, seasons **2022–2025 all
  return data** — so this is a loop over seasons, storing each season's
  `raw-<season>.json` and `standings-<season>.json`.
- **Related spec task:** L9 (Multi-season archive) — already in the spec as
  optional, and not to start before L1–L8 are done.
- **Status:** tracked; deferred until L1–L8 are complete.

### ENH-002 — Season picker (dropdown to select league year)

- **Date:** 2026-09-18
- **Requested by:** league owner
- **Description:** A picklist / combobox / dropdown on the page to choose which
  league year to view. Depends on ENH-001 (multi-season data) existing first.
- **Related spec task:** part of L9 ("a loop plus a season picker").
- **Status:** tracked; deferred until ENH-001 / L9.
