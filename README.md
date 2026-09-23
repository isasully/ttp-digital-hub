# Turning the Page — Digital Hub

An illustrated, 2D "room" website for Turning the Page's family literacy programs. Visitors click hotspots in a drawn room (a bookshelf, a science lab table, a bulletin board, etc.) to open each section. Staff can sign in with edit access to add, edit, and delete content directly on the live site — books, apps, science activities, and bulletin board posts — through a lightweight in-page editor, with no separate CMS.

**Live site:** published as a Claude Artifact at https://claude.ai/artifact/RmidPWZhz6JEbHk5ZnGkB1

## How this is built

The entire site — markup, styles, and behavior — is one self-contained file, `room.html`. There's no build step and no server: it's published directly as a [Claude Artifact](https://claude.ai/code/artifacts), which hosts it at a stable URL and re-renders it on every publish. Images (book covers, the bookshelf background, flyers, staff-uploaded photos) are embedded directly in the file as base64 `data:` URIs, which is why the file is a few megabytes.

### Editable content blocks

Each section's data (the book list, the app list, science activities, bulletin board posts) is a plain JS array wrapped in comment markers like:

```js
// ===EDITABLE:BOOKS:START===
var books = [ ... ];
// ===EDITABLE:BOOKS:END===
```

When a staff member adds/edits/deletes something in the browser, the page fetches its own current HTML, finds these markers, splices in a freshly serialized array, and republishes the whole document via the Artifact `publish` capability. This is also how *you* (or a future Claude session) should make bulk edits: find the block, edit the array, leave the markers alone.

### Staff editing mode

Editing UI (add/edit/delete buttons, upload controls) is gated behind an `editor-mode` class on `<body>`, toggled based on `window.claude.use('user').canEdit()`. Everything with class `editor-only` is hidden from ordinary visitors and only shown to someone with write access to the Artifact.

Deletions use a custom on-page confirmation dialog (`#confirm-modal`), not the browser's native `confirm()` — native dialogs can be silently blocked in the sandboxed context the Artifact runs in, which caused a real bug (trash buttons silently doing nothing) before this was fixed. Don't reintroduce `window.confirm()`/`alert()`/`prompt()` for anything user-facing.

## Workflow for making changes

This project doesn't live in a persistent server — it lives in this git history plus whatever's currently published to the Artifact URL above. A Claude session's local sandbox is wiped between sessions, so **the published Artifact is the actual source of truth**, not any particular session's working directory. Every editing session should:

1. **Pull the live version first.** Use the Artifact tool's `read` action on the URL above to fetch the current published HTML — don't assume last session's local copy is still current (it might not even still exist).
2. **Edit it.** Prefer the `Edit` tool for surgical changes; for edits touching large embedded base64 image blocks, a small Python script that does a targeted string replace is usually safer than pasting huge base64 strings through the edit tool or into a prompt.
3. **Test before publishing.** See below.
4. **Publish.** Use the Artifact tool's `publish` action with the same URL. If it's rejected as stale, re-`read` the URL first — someone (staff, or another session) may have published a newer version in the meantime.
5. **Commit and push to this repo.** This is what gives you real version history and rollback, since the Artifact platform's own version history isn't something this project relies on. Commit message should say what changed and why.

### Testing

There's no permanent CI here — tests are plain Python scripts using Playwright, run manually before publishing. `test_smoke.py` in this repo covers the core flows (navigation between sections, opening a bulletin board item, the staff add/edit/delete flow, and the confirm-dialog fix). Run it with:

```bash
pip install playwright
playwright install chromium   # or point PLAYWRIGHT_BROWSERS_PATH at a pre-installed one
python3 test_smoke.py
```

It spins up a local HTTP server for `room.html`, mocks `window.claude` (including staff edit access), and drives the page with a real headless browser. When you add a new feature, add a test for it in the same style rather than only checking visually — this file is the only thing standing between "the site" and "whatever the last session's Playwright screenshot showed."

## Rolling back

Because every meaningful change is committed here, you can see exactly what changed and when with `git log -p -- room.html`, and revert to any prior state with `git checkout <commit> -- room.html` followed by re-publishing that version to the Artifact. The Artifact platform's own version numbers (visible in publish results, e.g. "Version 37") are not a reliable rollback mechanism on their own — this repo is.

## Embedding on the Turning the Page WordPress site

Not yet finalized. Options under consideration, roughly in order of effort:

1. **A plain link/button** on the WordPress site pointing at the Artifact URL above. Lowest effort, zero compatibility risk, always shows the current published version.
2. **An `<iframe>` embed** of the Artifact URL on a WordPress page. Needs testing — claude.ai may block being framed by another origin.
3. **Self-hosting** a copy of `room.html` directly on WordPress's own hosting, for full control and guaranteed embeddability, at the cost of needing a manual (or eventually scripted) re-upload step whenever the site changes, since it would no longer track the Artifact automatically.
