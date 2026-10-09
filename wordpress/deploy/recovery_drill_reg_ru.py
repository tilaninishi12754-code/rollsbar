#!/usr/bin/env python3
"""REG.RU async-provisioning adapter for the RollsBar recovery drill.

ISPmanager exposes a newly created DB in a transient `pending` row before the
stable delete identifier (`elid` on this REG.RU account) appears. The core drill
is kept unchanged; this adapter replaces only create/cleanup operations with
polling-aware versions, then runs the same restore verification.
"""
from __future__ import annotations

import time

import recovery_drill as core

POLL_SECONDS = 2.0
READY_TIMEOUT_SECONDS = 90.0


def wait_for_db(sid: str, requested: str, *, require_delete_id: bool) -> dict[str, str] | None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    last: dict[str, str] | None = None
    while time.monotonic() < deadline:
        last = core.find_named(core.rows(core.api_call({"out": "xml", "func": "db", "auth": sid})), requested)
        if last is None:
            if not require_delete_id:
                return None
        else:
            pair = last.get("pair", "")
            delete_id = last.get("key", "") or last.get("elid", "")
            if pair and delete_id:
                return last
        time.sleep(POLL_SECONDS)
    return last


def find_actual_user(sid: str, requested: str, pair: str) -> str:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    last_count = 0
    while time.monotonic() < deadline:
        user_rows = core.rows(core.api_call({"out": "xml", "func": "db.users", "auth": sid, "elid": pair}))
        last_count = len(user_rows)
        for row in user_rows:
            name = row.get("name", "")
            if name == requested or name.endswith("_" + requested):
                return name
        if len(user_rows) == 1 and user_rows[0].get("name"):
            return user_rows[0]["name"]
        time.sleep(POLL_SECONDS)
    raise RuntimeError(f"Temporary recovery DB user not ready after polling; observed_users={last_count}")


def create_temp_db(sid: str, requested: str, password: str) -> tuple[str, str, str, str]:
    if not core.TEMP_NAME_RE.fullmatch(requested):
        raise RuntimeError("Unsafe recovery drill database name")
    if core.find_named(core.rows(core.api_call({"out": "xml", "func": "db", "auth": sid})), requested):
        raise RuntimeError("Recovery drill database name collision")

    core.api_call(
        {
            "out": "xml",
            "func": "db.edit",
            "auth": sid,
            "sok": "ok",
            "name": requested,
            "owner": core.USER,
            "server": "MySQL8",
            "charset": "utf8mb4",
            "user": "*",
            "username": requested,
            "password": password,
            "confirm": password,
            "remote_access": "off",
            "comment": "RollsBar temporary recovery drill",
        }
    )

    print("temporary_database_provisioning=waiting_for_stable_metadata")
    target = wait_for_db(sid, requested, require_delete_id=True)
    if target is None:
        raise RuntimeError("Temporary recovery database disappeared while provisioning")

    actual_db = target.get("name", "")
    pair = target.get("pair", "")
    delete_id = target.get("key", "") or target.get("elid", "")
    if not actual_db or not pair or not delete_id:
        pending = target.get("pending", "")
        safe_fields = ",".join(sorted(target))
        raise RuntimeError(
            f"Temporary recovery database did not become ready; pending={pending!r}; safe_fields={safe_fields}"
        )

    actual_user = find_actual_user(sid, requested, pair)
    print("temporary_database_provisioning=ready")
    return actual_db, actual_user, pair, delete_id


def cleanup_temp_db(
    sid: str,
    requested: str,
    actual_user: str = "",
    pair: str = "",
    delete_id: str = "",
) -> list[str]:
    errors: list[str] = []
    if not core.TEMP_NAME_RE.fullmatch(requested):
        return ["unsafe_requested_name=yes"]

    target = core.find_named(core.rows(core.api_call({"out": "xml", "func": "db", "auth": sid})), requested)
    if target is None:
        return []

    if not (target.get("key") or target.get("elid")):
        print("temporary_database_cleanup=waiting_for_stable_metadata")
        target = wait_for_db(sid, requested, require_delete_id=True)
        if target is None:
            return []

    pair = pair or target.get("pair", "")
    delete_id = delete_id or target.get("key", "") or target.get("elid", "")

    if not actual_user and pair:
        try:
            actual_user = find_actual_user(sid, requested, pair)
        except Exception:
            actual_user = ""

    if actual_user:
        try:
            params = {"out": "xml", "func": "db.users.delete", "auth": sid, "elid": actual_user}
            if pair:
                params["plid"] = pair
            core.api_call(params)
        except Exception:
            # DB deletion below is authoritative; some ISPmanager builds remove
            # the paired user automatically or reject standalone user deletion.
            pass

    if not delete_id:
        errors.append("db_delete_identifier_missing=yes")
    else:
        try:
            core.api_call({"out": "xml", "func": "db.delete", "auth": sid, "elid": delete_id})
        except Exception as exc:
            errors.append(f"db_delete={exc.__class__.__name__}")

    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        remaining = core.find_named(core.rows(core.api_call({"out": "xml", "func": "db", "auth": sid})), requested)
        if remaining is None:
            return errors
        time.sleep(POLL_SECONDS)
    errors.append("db_still_present=yes")
    return errors


core.create_temp_db = create_temp_db
core.cleanup_temp_db = cleanup_temp_db

if __name__ == "__main__":
    raise SystemExit(core.main())
