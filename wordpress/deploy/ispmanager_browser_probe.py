#!/usr/bin/env python3
"""Read-only browser login probe for ISPmanager.

Uses Playwright and staging environment secrets. It authenticates through the
real web UI, observes whether an authenticated control-panel page is reached,
and performs no create/update/delete actions. No screenshots or credentials are
printed.
"""
from __future__ import annotations

import os
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

base = os.environ["ISP_MANAGER_URL"].strip().rstrip("/") + "/"
user = os.environ["ISP_MANAGER_USER"].strip()
password = os.environ["ISP_MANAGER_PASSWORD"].strip()

candidates = [
    urljoin(base, "ispmgr"),
    urljoin(base, "manager/ispmgr"),
    base,
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(ignore_https_errors=False)
    last_error = ""

    for url in candidates:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            user_selectors = [
                'input[name="username"]',
                'input[name="login"]',
                'input[type="text"]',
            ]
            pass_selectors = [
                'input[name="password"]',
                'input[type="password"]',
            ]

            user_box = next((page.locator(s).first for s in user_selectors if page.locator(s).count()), None)
            pass_box = next((page.locator(s).first for s in pass_selectors if page.locator(s).count()), None)

            if user_box is None or pass_box is None:
                # Already authenticated would be unexpected in a fresh browser,
                # but still check for known panel navigation text.
                body = page.locator("body").inner_text(timeout=5000).lower()
                if any(token in body for token in ("сайты", "websites", "базы данных", "databases")):
                    print("ISPmanager browser probe")
                    print("- web login: authenticated")
                    print("- mutation: not attempted")
                    print("BROWSER PROBE PASS")
                    browser.close()
                    raise SystemExit(0)
                last_error = "login fields not found"
                continue

            user_box.fill(user)
            pass_box.fill(password)
            pass_box.press("Enter")
            page.wait_for_load_state("domcontentloaded", timeout=20000)
            page.wait_for_timeout(2500)

            body = page.locator("body").inner_text(timeout=5000).lower()
            current = page.url.lower()

            invalid_tokens = (
                "invalid username or password",
                "неверный логин",
                "неверный пароль",
                "incorrect login",
            )
            if any(token in body for token in invalid_tokens):
                last_error = "web UI rejected credentials"
                continue

            authenticated_tokens = (
                "сайты",
                "websites",
                "базы данных",
                "databases",
                "файлы",
                "file manager",
            )
            if any(token in body for token in authenticated_tokens) and "auth" not in current:
                print("ISPmanager browser probe")
                print("- web login: authenticated")
                print("- mutation: not attempted")
                print("BROWSER PROBE PASS")
                browser.close()
                raise SystemExit(0)

            last_error = "authenticated panel markers not observed"
        except Exception as exc:
            last_error = exc.__class__.__name__

    browser.close()

print("ISPmanager browser probe")
print("- web login: not confirmed")
print(f"- diagnostic: {last_error}")
print("- mutation: not attempted")
raise SystemExit("BROWSER PROBE FAILED")
