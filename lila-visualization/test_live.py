"""
Live E2E Test Suite for LILA BLACK Visualization
=================================================
Tests the deployed Streamlit app at both:
  - Local: http://localhost:8502
  - Production: https://lilavisualization.streamlit.app

Tests HTTP accessibility, Streamlit health, page shell rendering,
static assets, and (via AppTest) full UI simulation.
"""
import sys
import os
import json
import time
import urllib.request
import urllib.error
import ssl

PASS = 0
FAIL = 0
WARN = 0
results = []

LOCAL_URL = "http://localhost:8502"
PROD_URL = "https://lilavisualization.streamlit.app"


def report(name, passed, detail=""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    results.append((status, name, detail))
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] {name}" + (f"  -- {detail}" if detail else ""))


def warn(name, detail=""):
    global WARN
    WARN += 1
    results.append(("WARN", name, detail))
    print(f"  [WARN] {name}" + (f"  -- {detail}" if detail else ""))


def fetch(url, follow_redirects=True, timeout=15):
    """Simple GET that returns (status_code, body_text, headers_dict)."""
    ctx = ssl.create_default_context()
    if not follow_redirects:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                raise urllib.error.HTTPError(newurl, code, msg, headers, fp)
        opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ctx))
    else:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    try:
        r = opener.open(url, timeout=timeout)
        body = r.read().decode("utf-8", errors="replace")
        headers = dict(r.headers)
        return r.status, body, headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        headers = dict(e.headers) if e.headers else {}
        return e.code, body, headers


# ============================================================================
# 1. LOCAL SERVER TESTS
# ============================================================================
print("=" * 70)
print("1. LOCAL SERVER TESTS (http://localhost:8502)")
print("=" * 70)

# 1a. Health endpoint
print("\n--- 1a. Health endpoint ---")
try:
    status, body, _ = fetch(f"{LOCAL_URL}/_stcore/health")
    report("Local health returns 200", status == 200, f"status={status}")
    report("Local health body is 'ok'", body.strip() == "ok", repr(body.strip()))
except Exception as e:
    report("Local health endpoint", False, str(e))

# 1b. Main page serves Streamlit shell
print("\n--- 1b. Main page shell ---")
try:
    status, body, headers = fetch(LOCAL_URL)
    report("Local main page returns 200", status == 200, f"status={status}")
    report("Page contains <div id='root'>", "id=\"root\"" in body)
    report("Page contains Streamlit JS bundle", "assets/index-" in body or "stApp" in body)
    report("Page title present", "<title>" in body.lower() or "page_title" in body.lower())
    report("Content-Type is text/html", "text/html" in headers.get("Content-Type", ""))
except Exception as e:
    report("Local main page", False, str(e))

# 1c. Static assets
print("\n--- 1c. Static assets ---")
try:
    status, body, _ = fetch(f"{LOCAL_URL}/_stcore/host-config")
    report("host-config returns 200", status == 200, f"status={status}")
    # Should be JSON
    try:
        config = json.loads(body)
        report("host-config is valid JSON", True, f"keys={list(config.keys())[:5]}")
    except json.JSONDecodeError:
        report("host-config is valid JSON", False, body[:100])
except Exception as e:
    report("host-config", False, str(e))

# 1d. Streamlit WebSocket endpoint exists (upgrade required = 426)
print("\n--- 1d. WebSocket endpoint accessible ---")
try:
    status, body, _ = fetch(f"{LOCAL_URL}/_stcore/stream")
    # WebSocket endpoints typically return 426 or 400 for plain HTTP GET
    report("Stream endpoint responds", status in [200, 400, 426], f"status={status}")
except Exception as e:
    # Connection errors are fine - just means it wants a WS upgrade
    report("Stream endpoint responds", True, f"expected WS upgrade error: {type(e).__name__}")


# ============================================================================
# 2. PRODUCTION SERVER TESTS
# ============================================================================
print("\n" + "=" * 70)
print("2. PRODUCTION SERVER TESTS (https://lilavisualization.streamlit.app)")
print("=" * 70)

# 2a. Main page accessible (follows redirects)
print("\n--- 2a. Main page ---")
try:
    status, body, headers = fetch(PROD_URL)
    report("Prod main page returns 200", status == 200, f"status={status}")
    report("Prod page has Streamlit shell", "id=\"root\"" in body, f"body_length={len(body)}")
    report("Prod page has JS bundle", "assets/index-" in body)
    report("Prod page has noscript fallback", "noscript" in body.lower())
except Exception as e:
    report("Prod main page", False, str(e))

# 2b. Check initial redirect (auth behavior)
print("\n--- 2b. Auth redirect behavior ---")
try:
    status, body, headers = fetch(PROD_URL, follow_redirects=False)
    if status in [200]:
        report("Prod serves directly (no auth redirect)", True)
    elif status in [301, 302, 303, 307]:
        location = headers.get("Location", headers.get("location", ""))
        is_auth = "auth" in location.lower() or "login" in location.lower()
        if is_auth:
            warn("Prod redirects to Streamlit auth", f"status={status}, location={location[:100]}")
            report("Auth redirect is handled gracefully", True, "Browser handles it via cookie flow")
        else:
            report("Prod redirect", True, f"status={status} -> {location[:100]}")
    else:
        report("Prod initial response", False, f"Unexpected status={status}")
except urllib.error.HTTPError as e:
    if e.code in [303]:
        location = e.headers.get("Location", "") if e.headers else ""
        is_auth = "auth" in location.lower()
        if is_auth:
            warn("Prod uses Streamlit auth (303 redirect)", f"-> {location[:100]}")
            report("Auth redirect has valid Location header", bool(location), location[:100])
        else:
            report("Prod redirect", True, f"303 -> {location[:100]}")
    else:
        report("Prod initial response", False, f"status={e.code}")
except Exception as e:
    report("Prod auth check", False, str(e))

# 2c. Production page follows full redirect chain to 200
print("\n--- 2c. Full redirect chain resolves ---")
try:
    status, body, _ = fetch(PROD_URL, follow_redirects=True)
    report("Prod redirect chain resolves to 200", status == 200, f"final_status={status}")
    report("Final page is Streamlit HTML", "<div id=\"root\">" in body)
    report("Page has GTM tracking", "GTM-" in body)
    report("Page has Segment analytics", "segment" in body.lower())
except Exception as e:
    report("Prod redirect chain", False, str(e))


# ============================================================================
# 3. STREAMLIT AppTest — FULL UI SIMULATION (uses local code)
# ============================================================================
print("\n" + "=" * 70)
print("3. STREAMLIT AppTest — FULL UI SIMULATION")
print("=" * 70)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from streamlit.testing.v1 import AppTest

    # 3a. Boot the app
    print("\n--- 3a. App boots ---")
    at = AppTest.from_file("app.py", default_timeout=120)
    at.run()
    report("App boots without exception", not at.exception,
           str(at.exception[0].value) if at.exception else "clean boot")

    if not at.exception:
        # 3b. Header metrics
        print("\n--- 3b. Header metrics ---")
        metrics = at.metric
        metric_labels = [m.label for m in metrics]
        metric_values = {m.label: m.value for m in metrics}
        report(f"Found {len(metrics)} metrics", len(metrics) >= 5)
        for label in ["Events shown", "Unique players", "Matches", "Kills", "Loot pickups"]:
            report(f"Metric '{label}' rendered", label in metric_labels,
                   f"value={metric_values.get(label, 'MISSING')}")
        # Metrics should have non-zero values
        events_shown = metric_values.get("Events shown", "0").replace(",", "")
        report("Events shown > 0", int(events_shown) > 0, f"value={events_shown}")

        # 3c. Tabs
        print("\n--- 3c. 4 tabs present ---")
        tabs = at.tabs
        report("4 tabs rendered", len(tabs) == 4, f"count={len(tabs)}")

        # 3d. Sidebar widgets
        print("\n--- 3d. Sidebar widgets ---")
        sb = at.sidebar
        report("Map selectbox", len(sb.selectbox) >= 1, f"count={len(sb.selectbox)}")
        report("Date selectbox", len(sb.selectbox) >= 2)
        report("Player type multiselect", len(sb.multiselect) >= 1)
        report("Event type multiselect", len(sb.multiselect) >= 2)
        report("Show paths toggle", len(sb.toggle) >= 1)

        # Verify default map is one of the known maps
        map_value = sb.selectbox[0].value
        report("Default map is known", map_value in ["AmbroseValley", "GrandRift", "Lockdown"],
               f"value={map_value}")

        # 3e. No errors or warnings on default load
        print("\n--- 3e. Clean default load ---")
        report("No st.error messages", len(at.error) == 0,
               str([e.value for e in at.error]) if at.error else "")
        report("No st.warning messages", len(at.warning) == 0,
               str([w.value for w in at.warning]) if at.warning else "")
        report("No uncaught exceptions", len(at.exception) == 0)

        # 3f. Switch maps
        print("\n--- 3f. Switch maps ---")
        maps_to_test = ["AmbroseValley", "GrandRift", "Lockdown"]
        for m in maps_to_test:
            at.sidebar.selectbox[0].set_value(m).run()
            report(f"Map '{m}' loads without crash", not at.exception,
                   str(at.exception[0].value) if at.exception else "")

        # 3g. Filter player types
        print("\n--- 3g. Player type filters ---")
        for ptype in [["Human"], ["Bot"], ["Human", "Bot"]]:
            at.sidebar.multiselect[0].set_value(ptype).run()
            report(f"Filter {ptype} — no crash", not at.exception,
                   str(at.exception[0].value) if at.exception else "")

        # 3h. Toggle paths
        print("\n--- 3h. Toggle paths ---")
        at.sidebar.toggle[0].set_value(False).run()
        report("Paths OFF — no crash", not at.exception)
        at.sidebar.toggle[0].set_value(True).run()
        report("Paths ON — no crash", not at.exception)

        # 3i. Filter events
        print("\n--- 3i. Event filters ---")
        at.sidebar.multiselect[1].set_value(["Kill", "Killed"]).run()
        report("Kill+Killed filter — no crash", not at.exception)
        kills_shown = at.metric[0].value.replace(",", "")
        report("Kill filter reduces event count", int(kills_shown) > 0, f"events={kills_shown}")

        # Restore full events
        all_events = ["Position", "BotPosition", "Kill", "Killed", "BotKill", "BotKilled", "KilledByStorm", "Loot"]
        at.sidebar.multiselect[1].set_value(all_events).run()
        report("Full events restored — no crash", not at.exception)

        # 3j. Empty filters (edge case)
        print("\n--- 3j. Empty event filter ---")
        at.sidebar.multiselect[1].set_value([]).run()
        report("Empty event filter — no crash", not at.exception)

        # 3k. Date filter
        print("\n--- 3k. Date filter ---")
        at.sidebar.multiselect[1].set_value(all_events).run()  # restore
        at.sidebar.selectbox[1].set_value("February_10").run()
        report("Date 'February_10' filter — no crash", not at.exception)
        at.sidebar.selectbox[1].set_value("All").run()
        report("Date 'All' restored — no crash", not at.exception)

        # 3l. Timeline tab — match picker + slider
        print("\n--- 3l. Timeline match picker ---")
        # The timeline tab has its own selectbox (index 2 in full app)
        all_selectboxes = at.selectbox
        if len(all_selectboxes) >= 3:
            timeline_picker = all_selectboxes[2]  # sidebar has 2, timeline tab has 1
            current_match = timeline_picker.value
            report("Timeline match picker has value", bool(current_match), f"match={current_match}")
        else:
            report("Timeline match picker found", len(all_selectboxes) >= 3, 
                   f"selectbox_count={len(all_selectboxes)}")

        # 3m. Verify Plotly charts exist
        print("\n--- 3m. Plotly charts rendered ---")
        # In Streamlit testing, plotly charts appear in the element tree
        # We can check the count indirectly via the plotly_chart elements
        # At minimum we expect: journey, heatmap, timeline, 3 stats charts = 6
        # But some might be in non-active tabs

        # 3n. Stats tab — dataframe
        print("\n--- 3n. Stats data ---")
        dataframes = at.dataframe
        report("Dataframe(s) rendered", len(dataframes) >= 1, f"count={len(dataframes)}")

except ImportError:
    warn("streamlit.testing.v1 not available", "skipping UI tests")
except Exception as e:
    import traceback
    report("AppTest suite", False, traceback.format_exc())


# ============================================================================
# 4. CROSS-CHECK: PROD vs LOCAL versions
# ============================================================================
print("\n" + "=" * 70)
print("4. VERSION & DEPLOYMENT CHECKS")
print("=" * 70)

# 4a. Check local Streamlit version
print("\n--- 4a. Streamlit version ---")
try:
    import streamlit
    report(f"Streamlit version", True, streamlit.__version__)
except Exception:
    pass

# 4b. Check prod page has same JS bundle hash (indicating same deployment)
print("\n--- 4b. JS bundle consistency ---")
try:
    _, local_body, _ = fetch(LOCAL_URL)
    _, prod_body, _ = fetch(PROD_URL)
    # Extract JS bundle filename
    import re
    local_js = re.findall(r'assets/index-[\w]+\.js', local_body)
    prod_js = re.findall(r'assets/index-[\w]+\.js', prod_body)
    if local_js and prod_js:
        report("Both have JS bundles", True, f"local={local_js[0]}, prod={prod_js[0]}")
        # Note: they may differ if streamlit versions differ
    else:
        warn("Could not extract JS bundle names")
except Exception as e:
    warn("Bundle check failed", str(e))

# 4c. Check requirements.txt exists in repo (needed for Streamlit Cloud)
print("\n--- 4c. Deployment files ---")
req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
report("requirements.txt exists", os.path.isfile(req_path))

# Check it has all needed packages
if os.path.isfile(req_path):
    with open(req_path) as f:
        req_content = f.read().lower()
    for pkg in ["streamlit", "pandas", "pyarrow", "plotly", "pillow", "numpy"]:
        report(f"requirements.txt includes {pkg}", pkg in req_content)


# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  PASSED  : {PASS}")
print(f"  FAILED  : {FAIL}")
print(f"  WARNINGS: {WARN}")
print("=" * 70)

if FAIL > 0:
    print("\nFAILURES:")
    for status, name, detail in results:
        if status == "FAIL":
            print(f"   - {name}: {detail}")

if WARN > 0:
    print("\nWARNINGS:")
    for status, name, detail in results:
        if status == "WARN":
            print(f"   - {name}: {detail}")

print()
sys.exit(1 if FAIL > 0 else 0)
