#!/usr/bin/env python3
"""Read-only browser login probe for ISPmanager.

Uses Playwright and staging environment secrets. It authenticates through the
real web UI, observes whether an authenticated control-panel page is reached,
and performs no create/update/delete actions. No screenshots or credentials are
printed.
"""
from __future__ import annotations

import os
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

base = os.environ["ISP_MANAGER_URL"].strip().rstrip("/") + "/"
user = os.environ["ISP_MANAGER_USER"].strip()
password = os.environ["ISP_MANAGER_PASSWORD"].strip()

candidates = [
    urljoin(base, "ispmgr"),
    urljoin(base, "manager/ispmgr"),
    base,
]

USER_SELECTORS = [
    'input[name="username"]',
    'input[name="login"]',
    'input[autocomplete="username"]',
    'input[placeholder*="user" i]',
    'input[placeholder*="login" i]',
    'input[placeholder*="польз" i]',
    'input[placeholder*="логин" i]',
    'input[type="text"]',
    'input:not([type])',
]
PASS_SELECTORS = [
    'input[name="password"]',
    'input[autocomplete="current-password"]',
    'input[placeholder*="password" i]',
    'input[placeholder*="парол" i]',
    'input[type="password"]',
]


def find_first(frame, selectors):
    for selector in selectors:
        try:
            locator = frame.locator(selector)
            if locator.count() > 0:
                return locator.first
        except Exception:
            pass
    return None


def safe_page_diag(page) -> str:
    try:
        parsed = urlparse(page.url)
        title = page.title()[:80]
        frame_count = len(page.frames)
        input_meta = []
        for frame in page.frames:
            try:
                for i in range(min(frame.locator("input").count(), 8)):
                    loc = frame.locator("input").nth(i)
                    input_meta.append(
                        {
                            "type": (loc.get_attribute("type") or "text")[:24],
                            "name": (loc.get_attribute("name") or "")[:40],
                            "autocomplete": (loc.get_attribute("autocomplete") or "")[:40],
                            "placeholder": (loc.get_attribute("placeholder") or "")[:60],
                        }
                    )
            except Exception:
                pass
        return (
            f"url={parsed.scheme}://{parsed.netloc}{parsed.path}; "
            f"title={title!r}; frames={frame_count}; inputs={input_meta[:12]}"
        )
    except Exception as exc:
        return f"diagnostic-failed:{exc.__class__.__name__}"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(ignore_https_errors=False)
    last_error = ""

    for url in candidates:
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1500)

            chosen = None
            for frame in page.frames:
                user_box = find_first(frame, USER_SELECTORS)
                pass_box = find_first(frame, PASS_SELECTORS)
                if user_box is not None and pass_box is not None:
                    chosen = (frame, user_box, pass_box)
                    break

            if chosen is None:
                body = page.locator("body").inner_text(timeout=5000).lower()
                if any(token in body for token in ("сайты", "websites", "базы данных", "databases")):
                    print("ISPmanager browser probe")
                    print("- web login: authenticated")
                    print("- mutation: not attempted")
                    print("BROWSER PROBE PASS")
                    browser.close()
                    raise SystemExit(0)
                last_error = "login fields not found; " + safe_page_diag(page)
                continue

            _, user_box, pass_box = chosen
            user_box.fill(user)
            pass_box.fill(password)
            pass_box.press("Enter")
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                page.wait_for_timeout(3000)

            body = page.locator("body").inner_text(timeout=5000).lower()
            current = page.url.lower()

            invalid_tokens = (
                "invalid username or password",
                "неверный логин",
                "неверный пароль",
                "incorrect login",
                "wrong password",
            )
            if any(token in body for token in invalid_tokens):
                last_error = "web UI rejected credentials; " + safe_page_diag(page)
                continue

            authenticated_tokens = (
                "сайты",
                "websites",
                "базы данных",
                "databases",
                "файлы",
                "file manager",
                "dashboard",
            )
            if any(token in body for token in authenticated_tokens) and "auth" not in current:
                print("ISPmanager browser probe")
                print("- web login: authenticated")
                print("- mutation: not attempted")
                print("BROWSER PROBE PASS")
                browser.close()
                raise SystemExit(0)

            last_error = "authenticated panel markers not observed; " + safe_page_diag(page)
        except Exception as exc:
            last_error = f"{exc.__class__.__name__}; " + safe_page_diag(page)

    browser.close()

print("ISPmanager browser probe")
print("- web login: not confirmed")
print(f"- diagnostic: {last_error}")
print("- mutation: not attempted")
raise SystemExit("BROWSER PROBE FAILED")
