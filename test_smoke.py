"""
Smoke test for the Turning the Page Digital Hub (room.html).

Covers: section navigation, opening a bulletin board item, the staff
add/edit/delete flow for a board post, and the custom confirm-dialog fix
(delete must work even when the browser's native window.confirm() is
unavailable, since that's exactly the failure mode this dialog replaced).

Run with:
    pip install playwright
    playwright install chromium
    python3 test_smoke.py

Set PLAYWRIGHT_CHROMIUM to a specific chromium binary if you have one
pre-installed elsewhere (e.g. /opt/pw-browsers/chromium in some sandboxes).
"""
from playwright.sync_api import sync_playwright
import subprocess, time, os, sys

PORT = 8791
HERE = os.path.dirname(os.path.abspath(__file__))
CHROMIUM = os.environ.get("PLAYWRIGHT_CHROMIUM") or (
    "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None
)

srv = subprocess.Popen(["python3", "-m", "http.server", str(PORT)], cwd=HERE,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.6)

failures = []
def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)

MOCK_CLAUDE = """
    window.confirm = function(){ throw new Error('window.confirm is blocked in this context — the page must not depend on it'); };
    window.claude = {
      use: function(name){
        if (name === 'user') { return Promise.resolve({ canEdit: function(){ return Promise.resolve(true); } }); }
        if (name === 'artifact') {
          return Promise.resolve({
            publish: function(html){ window.__lastPublishedHtml = html; return Promise.resolve({version:'v_test'}); }
          });
        }
        return Promise.resolve(null);
      }
    };
"""

try:
    with sync_playwright() as p:
        launch_kwargs = {"executable_path": CHROMIUM} if CHROMIUM else {}
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.add_init_script(MOCK_CLAUDE)
        page.goto(f"http://localhost:{PORT}/room.html")
        page.wait_for_timeout(400)

        # --- navigation ---
        page.click('.hotspot[data-view="bulletin-board"]')
        page.wait_for_timeout(300)
        check("bulletin board view visible", page.eval_on_selector(
            '#view-bulletin-board', "el => !el.hidden"))

        # --- opening an existing board item ---
        page.click('[aria-label^="Children\'s Book and Learning Festival"]')
        page.wait_for_timeout(200)
        check("photo modal opens for an existing board item",
              page.eval_on_selector('#photo-modal', "el => !el.hidden"))
        check("staff edit/delete controls visible in editor mode",
              page.eval_on_selector('#board-modal-editor-actions',
                                     "el => getComputedStyle(el).display !== 'none'"))
        page.click('#modal-close')
        page.wait_for_timeout(150)

        # --- add a new bulletin board post ---
        page.click('#add-post-btn')
        page.wait_for_timeout(150)
        page.fill('#ed-post-title', 'Smoke Test Post')
        page.fill('#ed-post-caption', 'Created by test_smoke.py')
        page.click('#ed-post-save-btn')
        page.wait_for_timeout(300)
        published = page.evaluate("() => window.__lastPublishedHtml")
        check("publish() called after adding a post", published is not None)
        check("published HTML contains the new post",
              published is not None and 'Smoke Test Post' in published)

        # --- delete it via the CUSTOM confirm dialog (native confirm is blocked above) ---
        page.click('[aria-label^="Smoke Test Post"]')
        page.wait_for_timeout(200)
        page.click('#board-modal-delete')
        page.wait_for_timeout(150)
        check("custom confirm dialog appears (not native window.confirm)",
              page.eval_on_selector('#confirm-modal', "el => !el.hidden"))
        page.click('#confirm-modal-yes')
        page.wait_for_timeout(300)
        titles = page.eval_on_selector_all(
            '.pin-flyer', "els => els.map(e => e.getAttribute('aria-label'))")
        check("post removed from the board after confirming delete",
              not any('Smoke Test Post' in t for t in titles))
        check("pre-existing items untouched by the add/delete cycle",
              any('TTP Newsletter' in t for t in titles) and
              any("Children" in t for t in titles))

        check("no uncaught page errors", len(errors) == 0)
        if errors:
            print("Page errors:", errors)

        browser.close()
finally:
    srv.terminate()
    srv.wait()

print()
if failures:
    print(f"{len(failures)} check(s) FAILED:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
else:
    print("All checks passed.")
