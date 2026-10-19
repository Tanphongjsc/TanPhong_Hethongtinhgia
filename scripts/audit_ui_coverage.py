"""Read-only route/template inventory and test-only coverage evidence."""
import ast
from collections import Counter
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/ui-deep-coverage"
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    os.environ["APP_ENV"] = "test"
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"
    import django
    django.setup()
    from django.urls import URLResolver, get_resolver
    from scripts.audit_ui_contract import form_contracts
    from apps.master_data.navigation import DESTINATIONS
    routes = []

    def walk(patterns, prefix="", namespace=""):
        for pattern in patterns:
            path = prefix + str(pattern.pattern)
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns, path, namespace + (pattern.namespace + ":" if pattern.namespace else ""))
                continue
            callback = inspect.unwrap(pattern.callback)
            name = namespace + (pattern.name or "")
            fn = callback.__name__
            methods = None
            try:
                source = inspect.getsource(callback)
                tree = ast.parse(inspect.cleandoc(source) if source.startswith(" ") else source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id == "require_POST":
                        methods = ["POST"]
                    if isinstance(node, ast.Name) and node.id == "require_GET":
                        methods = ["GET"]
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "require_http_methods":
                        methods = ast.literal_eval(node.args[0])
            except (OSError, TypeError, SyntaxError):
                source = ""
            if path in ("health/", "ready/"):
                kind, methods = "HEALTH/TECHNICAL", ["GET"]
            elif not name:
                kind, methods = "NON_UI", ["GET"]
            elif name.endswith(("_activate", "_deactivate", "_calculate")):
                kind, methods = ("CALCULATION_ACTION" if name.endswith("_calculate") else "ACTION_POST"), ["POST"]
            elif name.endswith("_test"):
                kind, methods = "CALCULATION_ACTION", methods or ["POST"]
            elif name.endswith(("_options", "_resources", "_sources")):
                kind, methods = "DEPENDENT_OPTIONS", methods or ["GET"]
            elif name.endswith("_catalogue"):
                kind, methods = "HTMX_PARTIAL_GET", methods or ["GET"]
            elif name.endswith(("_list", "_compare")):
                kind, methods = "LIST_PAGE", methods or ["GET"]
            elif name.endswith(("_create", "_edit", "_rerun", "_close", "_remove")):
                editor = any(s in name for s in ("packaging_line_", "routing_operation_", "scheme_line_"))
                kind = "DRAWER_CONTENT" if editor else "FORM_PAGE"
                methods = methods or ["GET", "POST"]
            else:
                kind, methods = "DETAIL_PAGE", methods or ["GET"]
            routes.append({"name": name or "(root redirect)", "path": path, "view": f"{callback.__module__}.{fn}",
                           "classification": kind, "methods": methods, "defaults": pattern.default_args})
    walk(get_resolver().url_patterns)
    templates = []
    findings = []
    files = sorted((ROOT / "templates").rglob("*.html")) + sorted((ROOT / "apps").glob("**/templates/**/*.html"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        template = relative.split("/templates/", 1)[-1] if "/templates/" in relative else relative.removeprefix("templates/")
        if "components" in path.parts:
            kind = "COMPONENT"
        elif "layouts" in path.parts:
            kind = "LAYOUT"
        elif path.stem in ("400", "403", "404", "500") or "base/error" in relative:
            kind = "ERROR"
        elif "partials" in path.parts:
            kind = "PARTIAL"
        elif re.search(r"{%\s*extends", text):
            kind = "FULL PAGE"
        else:
            kind = "HTMX FRAGMENT"
        refs = re.findall(r'{%\s*(?:include|extends)\s+["\']([^"\']+)', text)
        templates.append({"path": relative, "name": template, "classification": kind,
                          "extends": bool(re.search(r"{%\s*extends", text)), "references": refs,
                          "dynamic_includes": re.findall(r"{%\s*include\s+([a-z_]\w*)", text),
                          "sha256": digest(path), "lines": len(text.splitlines())})
        for number, line in enumerate(text.splitlines(), 1):
            rules = (
                ("NOSCRIPT_BUTTON", r"<noscript><button\b"),
                ("LEGACY_ROW_ACTION", r'class="px-2 py-1 text-slate-600 hover:underline"'),
                ("INLINE_STYLE", r"\bstyle="),
                ("LARGE_RADIUS_SHADOW", r"\b(?:rounded-2xl|rounded-3xl|shadow-lg|shadow-xl)\b"),
                ("RAW_SVG", r"<svg\b"),
                ("RAW_LOADING", r"<span[^>]*htmx-indicator[^>]*role=.status."),
                ("PALETTE_UTILITY", r"\b(?:border|bg|text)-(?:slate|brand|red|emerald|amber|blue)-\d+"),
                ("EMPTY_FRAGMENT", r"{%\s*empty\s*%}"),
            )
            for rule, regex in rules:
                if re.search(regex, line):
                    category = "LEGACY" if rule == "LEGACY_ROW_ACTION" or (rule == "NOSCRIPT_BUTTON" and "ui-button" not in line) else (
                        "VALID DESIGN SYSTEM" if rule in ("PALETTE_UTILITY", "RAW_SVG") else "SPECIAL CASE")
                    findings.append({"path": relative, "line": number, "rule": rule, "classification": category,
                                     "excerpt": line[:500]})
    forms = form_contracts()
    counts = {"templates": len(templates), "full_page_extends": sum(t["extends"] for t in templates),
              "partials": sum("/partials/" in t["path"] for t in templates),
              "components": sum(t["classification"] == "COMPONENT" for t in templates),
              "layouts": sum(t["classification"] == "LAYOUT" for t in templates),
              "routes": len(routes), "GET_routes": sum("GET" in r["methods"] for r in routes),
              "user_facing_routes": sum(r["classification"] not in ("NON_UI", "HEALTH/TECHNICAL") for r in routes),
              "user_facing_GET_routes": sum("GET" in r["methods"] and r["classification"] not in ("NON_UI", "HEALTH/TECHNICAL") for r in routes),
              "forms": len(forms) - 1, "navigation": len(DESTINATIONS)}
    return {"counts": counts, "routes": routes, "templates": templates, "style_matches": findings}


def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "phase-baseline.json"
    if target.exists():
        raise RuntimeError("Never overwrite the phase baseline.")
    paths = sorted((ROOT / "apps").rglob("*.py")) + sorted((ROOT / "config").rglob("*.py"))
    paths += [ROOT / "manage.py", ROOT / "static/js/app.js", ROOT / "static/js/htmx-config.js",
              ROOT / "docs/ui-redesign/ui-contract-baseline.json"]
    data = {"files": {p.relative_to(ROOT).as_posix(): digest(p) for p in paths},
            "templates": {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in (ROOT / "templates").rglob("*.html")}}
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def check_phase():
    data = json.loads((OUT / "phase-baseline.json").read_text(encoding="utf-8"))
    changed = [rel for rel, sha in data["files"].items() if digest(ROOT / rel) != sha]
    return {"frozen_files": len(data["files"]), "changed": changed}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    action = sys.argv[1] if len(sys.argv) > 1 else "inventory"
    if action == "freeze":
        freeze()
    elif action == "check":
        report = check_phase()
        print(json.dumps(report))
        raise SystemExit(bool(report["changed"]))
    else:
        data = inventory()
        (OUT / "inventory.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(data["counts"], indent=2))
        print("Legacy candidates:", sum(f["classification"] == "LEGACY" for f in data["style_matches"]))
