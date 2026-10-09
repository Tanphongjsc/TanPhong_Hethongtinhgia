"""Read-only HTTP smoke checks. Never seed, calculate or submit business forms."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request
from uuid import UUID

PAGES = ("/", "/master-data/cost-elements/", "/product/items/", "/product/products/",
         "/product/skus/", "/bom/", "/bom/packaging/", "/formula-engine/formulas/",
         "/costing/runs/", "/pricing/scenarios/", "/pricing/scenarios/compare/")


class SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(req.full_url).netloc != urlsplit(newurl).netloc or urlsplit(req.full_url).scheme != urlsplit(newurl).scheme:
            raise ValueError("Smoke test không theo redirect khác origin; dùng base URL canonical.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        path = values.get("src") if tag == "script" else values.get("href") if tag == "link" and values.get("rel") == "stylesheet" else None
        if path and path.startswith("/static/"):
            self.paths.add(path)


def smoke(base_url, *, costing_run=None, costing_line=None, pricing_scenario=None, headers=None):
    parts = urlsplit(base_url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("Base URL phải là origin HTTP(S), không credentials/path/query.")
    base_url = base_url.rstrip("/")
    opener = build_opener(SameOriginRedirect())  # TLS verification is never disabled.
    checks, assets = [], set()

    default_headers = headers or {}

    def get(path, headers=None, *, kind="page"):
        try:
            with opener.open(Request(urljoin(base_url, path), headers={**default_headers, **(headers or {})}), timeout=20) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "")
                if kind == "probe":
                    valid = json.loads(data) == {"status": "ok"}
                elif kind == "asset":
                    valid = bool(data) and ("text/css" in content_type if path.endswith(".css") else "javascript" in content_type)
                else:
                    html = data.decode("utf-8")
                    valid = bool(data) and "text/html" in content_type and "Traceback (most recent call last)" not in html
                    valid = valid and "/login" not in response.url and "id=\"main-content\"" in html
                    if kind == "partial": valid = "<!doctype html>" not in html.lower() and "cost-element-table" in html
                    if kind == "page":
                        parser = Assets()
                        parser.feed(html)
                        assets.update(parser.paths)
                checks.append({"path": path, "kind": kind, "status": response.status, "pass": response.status == 200 and valid})
        except (HTTPError, URLError, ValueError, OSError):
            checks.append({"path": path, "kind": kind, "pass": False})

    for probe in ("/health/", "/ready/"): get(probe, kind="probe")
    for path in PAGES: get(path)
    if costing_run:
        public_id = UUID(str(costing_run))
        get(f"/costing/runs/{public_id}/", kind="history")
        get(f"/costing/runs/{public_id}/snapshot/", kind="history")
        if costing_line:
            get(f"/costing/runs/{public_id}/lines/{int(costing_line)}/trace/", kind="history")
    if pricing_scenario:
        get(f"/pricing/scenarios/{int(pricing_scenario)}/", kind="history")
    get("/master-data/cost-elements/?q=DEMO&per_page=25", {"HX-Request": "true"}, kind="partial")
    for path in sorted(assets): get(path, kind="asset")
    checks.append({"kind": "asset_count", "pass": len(assets) == 7, "count": len(assets)})
    return {"read_only": True, "passed": all(row["pass"] for row in checks), "checks": checks,
            "costing_history_checked": bool(costing_run), "pricing_history_checked": bool(pricing_scenario)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--report", help="Local output JSON; no credentials included.")
    parser.add_argument("--costing-run", type=UUID, help="UUID công khai của Run đã lưu; chỉ đọc lịch sử.")
    parser.add_argument("--costing-line", type=int, help="ID dòng thuộc Run trên để kiểm tra trace.")
    parser.add_argument("--pricing-scenario", type=int, help="ID kịch bản đã lưu để kiểm tra kết quả/nguồn/trace.")
    args = parser.parse_args()
    try:
        if args.costing_line and not args.costing_run:
            raise ValueError("--costing-line cần --costing-run.")
        if any(value is not None and value <= 0 for value in (args.costing_line, args.pricing_scenario)):
            raise ValueError("ID dòng/kịch bản phải là số nguyên dương.")
        report = smoke(args.base_url, costing_run=args.costing_run, costing_line=args.costing_line,
                       pricing_scenario=args.pricing_scenario)
    except ValueError as error:
        parser.error(str(error))
    content = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
    print(content)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
