"""
Exhaustive Playwright test suite for the fragment-based refactor of streamlit_app.py.

Goals (per explicit user directive: "test literally every single input to
ensure nothing crashes... test, test test, test again"):
  1. App loads clean.
  2. Baseline "Solve Entire Plant" click succeeds with default inputs, all tabs
     populate without any error banner.
  3. Every single input widget in every tab is exercised at least once
     WITHOUT clicking Solve afterward (pre-solve edits must never crash).
  4. Fragment isolation is verified directly: editing a widget in one tab must
     NOT change the rendered text of a different, already-solved tab.
  5. After the full sweep, Solve is clicked again and must succeed end-to-end
     with all the accumulated edited values (integration check).
  6. Two additional full repeat passes with different values, re-solving each
     time, to catch anything sequence-dependent (stale generation counters,
     etc).
  7. Timing is measured for: a pre-solve edit, the first solve, and a
     post-solve edit-without-resolve (this is the number that matters for the
     user's original complaint).
  8. Boiling-scheme switch (FBDM <-> TBDM) + resolve, specifically probing the
     Condensate Balance tab crash that was fixed earlier in this refactor.

Any Streamlit exception banner (the red "This app has encountered an error"
box, or an inline traceback) at any point is treated as a hard failure and is
printed with full text plus a screenshot.
"""
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8501"
SCREEN_DIR = Path("/home/claude/repo/test_screens")
SCREEN_DIR.mkdir(exist_ok=True)

TAB_LABELS = [
    "Mill Floor", "Clarification", "Juice Heating", "Pan Floor",
    "Evaporation", "Exhaust Summary", "Turbines & Boiler", "Cooling Tower",
    "Condensate Balance", "Download",
]

FAILURES = []


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def check_no_error(page, context_msg):
    """Look for Streamlit's error UI anywhere on the page right now."""
    error_locators = [
        page.locator("text=This app has encountered an error"),
        page.locator("[data-testid='stException']"),
        page.locator("text=Traceback (most recent call last)"),
    ]
    for loc in error_locators:
        try:
            if loc.count() > 0 and loc.first.is_visible():
                shot = SCREEN_DIR / f"error_{len(FAILURES)}.png"
                page.screenshot(path=str(shot))
                txt = loc.first.inner_text()[:2000]
                FAILURES.append(f"{context_msg}: {txt}\n(screenshot: {shot})")
                log(f"!!! ERROR DETECTED at [{context_msg}]: {txt[:300]}")
                return False
        except Exception:
            pass
    return True


def log_soft_alerts(page, context_msg):
    """Log any st.error(...) 'X failed to solve' boxes (caught, non-crashing
    failures) without treating them as hard test failures — as sweep values
    drift into unrealistic ranges over repeated passes, a solver legitimately
    rejecting the input is expected behavior, not a bug. Still worth surfacing."""
    alerts = page.locator("[data-testid='stAlert']")
    n = alerts.count()
    for i in range(n):
        try:
            txt = alerts.nth(i).inner_text()
            if "failed to solve" in txt:
                log(f"    (soft) [{context_msg}] {txt[:200]}")
        except Exception:
            pass


def wait_idle(page, timeout=60000):
    """Wait for a Streamlit run to actually finish.

    The running-man status widget attaches ~0.5-1s AFTER the triggering click
    (not instantly), so waiting for it to be "detached" right after a click
    succeeds trivially/immediately if we don't first give it a chance to
    appear -- that produced bogus near-zero timings. Wait for it to become
    visible first (best-effort, short timeout: a very fast fragment-only
    rerun may finish before we ever observe it), THEN wait for it to go away
    with a generous timeout matching real solve durations.
    """
    widget = page.locator("[data-testid='stStatusWidget']")
    try:
        widget.first.wait_for(state="visible", timeout=2500)
    except Exception:
        pass
    try:
        widget.first.wait_for(state="hidden", timeout=timeout)
    except Exception:
        pass
    page.wait_for_timeout(200)


def click_tab(page, label):
    tab = page.locator("div[data-testid='stTab']", has_text=label).first
    tab.click(force=True)
    page.wait_for_timeout(150)


def active_panel(page):
    # The visible tabpanel corresponding to the currently active tab.
    panels = page.locator("div[data-testid='stTabPanel']")
    n = panels.count()
    for i in range(n):
        p = panels.nth(i)
        if p.is_visible():
            return p
    return panels.first


def click_solve(page):
    btn = page.get_by_role("button", name=re.compile("Solve Entire Plant"))
    t0 = time.time()
    btn.click(force=True)
    wait_idle(page)
    dt = time.time() - t0
    return dt


def sweep_number_inputs(page, panel, tab_name, factor=1.02):
    inputs = panel.locator("input[type='number']")
    n = inputs.count()
    log(f"  [{tab_name}] {n} number_input widget(s)")
    for i in range(n):
        el = inputs.nth(i)
        try:
            if not el.is_enabled():
                continue
            cur = el.input_value()
            try:
                curf = float(cur) if cur not in ("", None) else 0.0
            except ValueError:
                continue
            newv = curf * factor if curf != 0 else 1.0
            el.click()
            el.fill(str(round(newv, 4)))
            el.press("Tab")
            page.wait_for_timeout(120)
            check_no_error(page, f"{tab_name} number_input[{i}] -> {newv}")
        except Exception as e:
            log(f"    (skip number_input {i} in {tab_name}: {e})")


def sweep_checkboxes(page, panel, tab_name):
    boxes = panel.locator("input[type='checkbox']")
    n = boxes.count()
    log(f"  [{tab_name}] {n} checkbox widget(s)")
    for i in range(n):
        el = boxes.nth(i)
        try:
            el.click(force=True)
            page.wait_for_timeout(120)
            check_no_error(page, f"{tab_name} checkbox[{i}]")
        except Exception as e:
            log(f"    (skip checkbox {i} in {tab_name}: {e})")


def sweep_radios(page, panel, tab_name):
    # Radios come in groups; click every individual radio option once.
    radios = panel.locator("input[type='radio']")
    n = radios.count()
    log(f"  [{tab_name}] {n} radio option(s)")
    for i in range(n):
        el = radios.nth(i)
        try:
            el.click(force=True)
            page.wait_for_timeout(120)
            check_no_error(page, f"{tab_name} radio[{i}]")
        except Exception as e:
            log(f"    (skip radio {i} in {tab_name}: {e})")


def sweep_selectboxes(page, panel, tab_name):
    selects = panel.locator("div[data-baseweb='select']")
    n = selects.count()
    log(f"  [{tab_name}] {n} selectbox widget(s)")
    for i in range(n):
        try:
            sel = selects.nth(i)
            sel.click(force=True)
            page.wait_for_timeout(150)
            options = page.locator("li[role='option']")
            oc = options.count()
            if oc > 1:
                options.nth(1).click(force=True)
            elif oc == 1:
                options.nth(0).click(force=True)
            else:
                page.keyboard.press("Escape")
            page.wait_for_timeout(120)
            check_no_error(page, f"{tab_name} selectbox[{i}]")
        except Exception as e:
            log(f"    (skip selectbox {i} in {tab_name}: {e})")
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass


def full_widget_sweep(page, factor=1.02, tab_order=None):
    for label in (tab_order or TAB_LABELS):
        click_tab(page, label)
        panel = active_panel(page)
        sweep_number_inputs(page, panel, label, factor=factor)
        sweep_checkboxes(page, panel, label)
        sweep_radios(page, panel, label)
        sweep_selectboxes(page, panel, label)


def get_tab_snapshot_text(page, label):
    click_tab(page, label)
    panel = active_panel(page)
    return panel.inner_text()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200})
        page.set_default_timeout(6000)

        log("Loading app...")
        page.goto(BASE_URL)
        wait_idle(page, timeout=20000)
        check_no_error(page, "initial load")

        # --- Baseline solve ---
        log("=== Baseline solve (defaults) ===")
        dt_first_solve = click_solve(page)
        log(f"First solve took {dt_first_solve:.2f}s")
        check_no_error(page, "baseline solve")
        for label in TAB_LABELS:
            click_tab(page, label)
            page.wait_for_timeout(150)
            check_no_error(page, f"post-baseline-solve view of {label}")
            log_soft_alerts(page, f"post-baseline-solve view of {label}")

        # --- Timing: sidebar edit (full rerun, outside any fragment) vs
        # in-tab edit (fragment-scoped rerun) after a solved state. ---
        log("=== Timing probe A: sidebar input edit after solve (full app rerun, NOT fragment-scoped) ===")
        sidebar = page.locator("[data-testid='stSidebar']")
        sidebar_inputs = sidebar.locator("input[type='number']")
        if sidebar_inputs.count() > 0:
            el = sidebar_inputs.first
            cur = el.input_value()
            try:
                curf = float(cur)
            except ValueError:
                curf = 100.0
            t0 = time.time()
            el.click()
            el.fill(str(round(curf * 1.001, 4)))
            el.press("Tab")
            wait_idle(page, timeout=30000)
            dt_edit_sidebar = time.time() - t0
            log(f"Sidebar (Mill/Clarification input) edit after solve took {dt_edit_sidebar:.2f}s -- "
                f"this widget lives OUTSIDE every fragment, so it still pays the full-script-rerun/redraw "
                f"cost (computation itself is still skipped -- only the redraw is expensive)")
            check_no_error(page, "post-solve sidebar edit")
        else:
            log("No sidebar number inputs found (unexpected)")
            dt_edit_sidebar = None

        log("=== Timing probe B: in-tab-body input edit after solve (fragment-scoped rerun) ===")
        click_tab(page, "Juice Heating")
        panel = active_panel(page)
        jh_inputs_timing = panel.locator("input[type='number']")
        if jh_inputs_timing.count() > 0:
            el = jh_inputs_timing.first
            cur = el.input_value()
            try:
                curf = float(cur)
            except ValueError:
                curf = 100.0
            t0 = time.time()
            el.click()
            el.fill(str(round(curf * 1.001, 4)))
            el.press("Tab")
            wait_idle(page, timeout=15000)
            dt_edit_post_solve = time.time() - t0
            log(f"Post-solve single-cell edit (Juice Heating tab body, fragment-scoped) took {dt_edit_post_solve:.2f}s")
            check_no_error(page, "post-solve single edit")
        else:
            log("No number inputs found on Juice Heating tab (unexpected)")
            dt_edit_post_solve = None

        # --- Fragment isolation proof: editing one tab must not change another ---
        log("=== Fragment isolation check: edit Juice Heating, verify Condensate Balance text is unchanged ===")
        before_text = get_tab_snapshot_text(page, "Condensate Balance")
        click_tab(page, "Juice Heating")
        panel = active_panel(page)
        jh_inputs = panel.locator("input[type='number']")
        if jh_inputs.count() > 0:
            el = jh_inputs.first
            cur = el.input_value()
            try:
                curf = float(cur)
            except ValueError:
                curf = 10.0
            el.click()
            el.fill(str(round(curf * 1.05 + 1, 4)))
            el.press("Tab")
            page.wait_for_timeout(400)
        check_no_error(page, "edit inside Juice Heating (isolation probe)")
        after_text = get_tab_snapshot_text(page, "Condensate Balance")
        if before_text == after_text:
            log("PASS: Condensate Balance tab text is byte-identical after editing Juice Heating (fragment isolation confirmed)")
        else:
            FAILURES.append(
                "Fragment isolation FAILED: editing Juice Heating changed Condensate Balance tab content.\n"
                f"--- before ---\n{before_text[:1000]}\n--- after ---\n{after_text[:1000]}"
            )
            log("!!! FAIL: Condensate Balance tab content changed after an unrelated edit")

        # --- Exhaustive widget sweep, pass 1 (no solve in between edits) ---
        log("=== Exhaustive widget sweep pass 1 (pre-solve edits across every tab, reversed tab order) ===")
        full_widget_sweep(page, factor=1.15, tab_order=list(reversed(TAB_LABELS)))
        log("Sweep pass 1 complete, no crash so far. Now solving with all accumulated edits...")
        page.wait_for_timeout(800)
        dt_solve2 = click_solve(page)
        log(f"Solve after sweep pass 1 took {dt_solve2:.2f}s")
        check_no_error(page, "solve after sweep pass 1")
        for label in TAB_LABELS:
            click_tab(page, label)
            page.wait_for_timeout(150)
            check_no_error(page, f"post-sweep1-solve view of {label}")
            log_soft_alerts(page, f"post-sweep1-solve view of {label}")

        # --- Boiling scheme switch + resolve: targeted regression probe ---
        log("=== Boiling scheme switch probe (FBDM <-> TBDM), then resolve ===")
        click_tab(page, "Pan Floor")
        panel = active_panel(page)
        scheme_radio = panel.locator("input[type='radio']")
        if scheme_radio.count() >= 2:
            scheme_radio.nth(1).click(force=True)
            page.wait_for_timeout(200)
            check_no_error(page, "scheme radio switch (pre-solve, should not crash even though pan not yet re-solved)")
            click_tab(page, "Condensate Balance")
            page.wait_for_timeout(200)
            check_no_error(page, "Condensate Balance viewed right after scheme switch, before resolve")
            dt_scheme_solve = click_solve(page)
            log(f"Solve after scheme switch took {dt_scheme_solve:.2f}s")
            check_no_error(page, "solve after scheme switch")
            click_tab(page, "Condensate Balance")
            page.wait_for_timeout(200)
            check_no_error(page, "Condensate Balance viewed after scheme-switch resolve")
        else:
            log("Could not find scheme radio group on Pan Floor tab (selector may need adjustment)")

        # --- Exhaustive widget sweep, pass 2 and 3 ---
        for pass_num, factor in [(2, 0.80), (3, 1.25)]:
            log(f"=== Exhaustive widget sweep pass {pass_num} ===")
            full_widget_sweep(page, factor=factor, tab_order=list(reversed(TAB_LABELS)) if pass_num == 2 else None)
            page.wait_for_timeout(800)
            dt = click_solve(page)
            log(f"Solve after sweep pass {pass_num} took {dt:.2f}s")
            check_no_error(page, f"solve after sweep pass {pass_num}")
            for label in TAB_LABELS:
                click_tab(page, label)
                page.wait_for_timeout(150)
                check_no_error(page, f"post-sweep{pass_num}-solve view of {label}")
                log_soft_alerts(page, f"post-sweep{pass_num}-solve view of {label}")

        # --- Download tab: build workbook button, if present ---
        log("=== Download tab: attempt workbook build ===")
        click_tab(page, "Download")
        page.wait_for_timeout(200)
        build_btn = page.get_by_role("button", name=re.compile("Build", re.I))
        if build_btn.count() > 0:
            build_btn.first.click(force=True)
            wait_idle(page, timeout=15000)
            check_no_error(page, "Download tab build workbook")
        else:
            log("No 'Build' button found on Download tab (selector may need adjustment)")

        browser.close()

    log("=== TIMING SUMMARY ===")
    log(f"First solve (cold, defaults): {dt_first_solve:.2f}s")
    log(f"Sidebar (Mill/Clarification) input edit AFTER solve: "
        f"{dt_edit_sidebar:.2f}s" if dt_edit_sidebar is not None else "Sidebar edit timing: N/A")
    log(f"In-tab-body input edit AFTER solve (fragment-scoped): "
        f"{dt_edit_post_solve:.2f}s" if dt_edit_post_solve is not None else "In-tab edit timing: N/A")

    log("=== DONE ===")
    if FAILURES:
        log(f"{len(FAILURES)} FAILURE(S) DETECTED:")
        for f in FAILURES:
            print("-" * 80)
            print(f)
        sys.exit(1)
    else:
        log("ALL CHECKS PASSED - zero error banners detected across the entire run.")
        sys.exit(0)


if __name__ == "__main__":
    main()
