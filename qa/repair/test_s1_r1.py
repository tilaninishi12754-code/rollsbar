"""Local-only S1-R1 acceptance. Uses existing PHP, isolated fixtures, no network."""
from pathlib import Path
import ast
import json
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PHP = Path(os.environ.get("ROLLSBAR_PHP", ROOT / "qa/.runtime/php/php.exe"))
THEME = ROOT / "wordpress/wp-content/themes/rollsbar-theme"
RESULTS = ROOT / "qa/visual-results/s1-r1"
RESULTS.mkdir(parents=True, exist_ok=True)
results = []


def run(label, args, expected=0, contains=None):
    result = subprocess.run([str(x) for x in args], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", timeout=90)
    output = result.stdout + result.stderr
    ok = result.returncode == expected and (contains is None or contains in output)
    ok = ok and not re.search(r"(?:Warning|Fatal error|Deprecated|Parse error):", output)
    results.append(dict(case=label, pass_=ok, exit_code=result.returncode, output=output.strip()))
    print(f"{'PASS' if ok else 'FAIL'} {label}")
    if not ok:
        raise AssertionError(output)
    return result.stdout


def main():
    ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for path in [ROOT / "wordpress/deploy/verify-staging-legal-pages.php",
                 ROOT / "wordpress/deploy/legal-footer-contract.php",
                 ROOT / "wordpress/deploy/shrimp-options-repair.php",
                 ROOT / "wordpress/deploy/repair-staging-shrimp-options.php",
                 *sorted((ROOT / "qa/repair").glob("*.php"))]:
        run("lint:" + path.name, [PHP, "-l", path])

    original = {name: (THEME / name).read_bytes() for name in ["footer.php", "page-otzyvy.php"]}
    footer = original["footer.php"].decode("utf-8")
    review = original["page-otzyvy.php"].decode("utf-8")
    fixture = ROOT / "qa/repair/legal-fixture.php"
    with tempfile.TemporaryDirectory(prefix="legal-", dir=RESULTS) as folder:
        # TemporaryDirectory only removes its own newly created directory.
        temp = Path(folder)
        def legal(case, expected=1, message=None, footer_text=footer, review_text=review, verifier=None):
            (temp / "footer.php").write_text(footer_text, encoding="utf-8")
            (temp / "page-otzyvy.php").write_text(review_text, encoding="utf-8")
            run("legal:" + case, [PHP, fixture, case, temp] + ([verifier] if verifier else []), expected, message)

        legal("baseline", 0, "PAYMENT LAUNCH MODE RUNTIME PASS")
        legal("internal-page", 0, "LEGAL / PAYMENT READINESS RUNTIME PASS")
        # Reproduce the original S1 false-positive using the exact accepted source.
        old = subprocess.check_output(["git", "show", "22ad41e3d03ec1a9efae0bde2560a4895d6e2708:wordpress/deploy/verify-staging-legal-pages.php"], cwd=ROOT)
        old_file = temp / "old-verifier.php"
        old_file.write_bytes(old)
        legal("old-verifier-reproduction", message="Footer is missing legal link: /publichnaya-oferta/", verifier=old_file)
        slugs = ["dostavka-i-oplata", "rekvizity-prodavca", "publichnaya-oferta", "oplata-i-vozvrat", "politika-konfidencialnosti", "cookies", "bezopasnost-onlajn-oplaty"]
        for slug in slugs:
            changed, n = re.subn(r"\s*array\( '" + re.escape(slug) + r"', '[^']+' \),", "", footer)
            assert n == 1
            legal("missing-" + slug, message=f"Footer is missing legal link: /{slug}/", footer_text=changed)
        legal("wrong-destination", message="Footer is missing legal link: /publichnaya-oferta/",
              footer_text=footer.replace("array( 'publichnaya-oferta',", "array( 'wrong-offer',"))
        legal("commented-navigation", message="Footer is missing legal link:",
              footer_text=footer.replace('<nav class="rollsbar-footer__links"', '<!-- <nav class="rollsbar-footer__links"').replace("</nav>", "</nav> -->"))
        legal("stale-footer", message="Static .html link leaked into WordPress footer",
              footer_text=footer.replace("</nav>", '<a href="offer.html">Old offer</a></nav>'))
        legal("missing-review-consent", message="Review form does not render",
              review_text=review.replace('name="privacy_consent"', 'name="removed_consent"'))
        for case, message in {
            "wrong-terms": "WooCommerce terms page is not wired",
            "wrong-privacy": "WordPress privacy policy page is not wired",
            "missing-page": "Legal page is missing: pravovaya-informaciya",
            "draft-page": "Legal page is not published: pravovaya-informaciya",
            "empty-page": "Legal page has empty content",
            "stale-page": "Static .html link leaked into WordPress legal page",
            "sber-russian": "Unverified acquiring provider leaked",
            "sber-latin": "Unverified acquiring provider leaked",
            "missing-checkout-consent": "Required checkout privacy-consent field is not registered",
            "optional-checkout-consent": "Checkout privacy-consent field must be a required checkbox",
            "missing-delivery-disclosure": "Delivery page does not disclose deferred polygon enforcement",
            "missing-requisites": "Seller requisites are incomplete",
        }.items():
            legal(case, message=message)
    assert all((THEME / name).read_bytes() == data for name, data in original.items())

    run("shrimp-repair", [PHP, ROOT / "qa/repair/shrimp-contract.php"], contains='"pass": true')
    run("shrimp-selector", [PHP, ROOT / "qa/repair/shrimp-selection-contract.php", ROOT], contains='"pass":true')
    for name in ["cart-contract.php", "b12-contract.php", "b15-contact-contract.php"]:
        run(name, [PHP, ROOT / "qa/visual" / name, ROOT])

    # Same literal-secret patterns as the existing migration static workflow.
    patterns = [re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
                re.compile(r'''\bclient_secret\s*=\s*["'](?!\$|<)[^"']{6,}["']''', re.I),
                re.compile(r'''\bapi[_-]?key\s*=\s*["'](?!\$|<)[^"']{8,}["']''', re.I),
                re.compile(r'''\bpassword\s*=\s*["'](?!\$|<)[^"']{6,}["']''', re.I),
                re.compile(r"\bsk-[A-Za-z0-9]{20,}")]
    findings = []
    for base in [ROOT / "wordpress", ROOT / "qa/repair"]:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {".md", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".zip"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeError:
                continue
            for num, line in enumerate(text.splitlines(), 1):
                if any(pattern.search(line) for pattern in patterns):
                    findings.append(f"{path.relative_to(ROOT)}:{num}")  # Never print suspect content.
    assert not findings, findings
    results.append(dict(case="secret-pattern-scan", pass_=True))
    run("diff-check", ["git", "diff", "--check"])
    # No application/workflow/marker/backup/catalog changes, including untracked.
    changed = subprocess.check_output(["git", "diff", "--name-only", "22ad41e3d03ec1a9efae0bde2560a4895d6e2708"], cwd=ROOT, text=True).splitlines()
    changed += subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    allowed = {"wordpress/deploy/verify-staging-legal-pages.php", "wordpress/deploy/legal-footer-contract.php", "wordpress/deploy/shrimp-options-repair.php", "wordpress/deploy/repair-staging-shrimp-options.php", "wordpress/docs/S1_R1_REPORT.md"}
    assert all(p in allowed or p.startswith("qa/repair/") for p in changed), changed
    results.append(dict(case="scope-preserved", pass_=True))
    print(f"S1-R1 LOCAL PASS: {len(results)} checks; no live DB/network")


if __name__ == "__main__":
    try:
        main()
    finally:
        (RESULTS / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
