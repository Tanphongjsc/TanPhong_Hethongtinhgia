"""Test-only recording runner. Never installed in Django runtime settings."""
from collections import Counter
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import threading
from unittest.mock import patch
import unittest

from django.conf import settings
from django.test import Client
from apps.master_data.testing import CostingTestRunner


class SurfaceDOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = Counter()
        self.controls = []
        self.statuses = set()
        self.invalid = 0
        self.text = []
        self.labels = set()
        self.scoped_headers = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags[tag] += 1
        if tag in ("input", "select", "textarea"):
            self.controls.append({key: values[key] for key in ("id", "name", "type", "disabled", "readonly", "aria-invalid") if key in values})
        if values.get("aria-invalid") == "true":
            self.invalid += 1
        if "data-status" in values:
            self.statuses.add(values["data-status"])
        if tag == "label" and "for" in values:
            self.labels.add(values["for"])
        if tag == "th" and "scope" in values:
            self.scoped_headers += 1

    def handle_data(self, text):
        if text.strip():
            self.text.append(text.strip())


class DeepUICoverageRunner(CostingTestRunner):
    def run_suite(self, suite, **kwargs):
        self.folder = Path(settings.BASE_DIR) / "artifacts/ui-deep-coverage"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.phase = os.environ.get("UI_COVERAGE_PHASE", "after")
        if self.phase not in ("before", "after", "targeted"):
            raise RuntimeError("Unknown evidence phase.")
        self.events = []
        self.lock = threading.Lock()
        self.current_test = ""
        original_request = Client.request
        original_start = unittest.TestResult.startTest

        def start(result, test):
            self.current_test = test.id()
            return original_start(result, test)

        def request(client, **request_args):
            response = original_request(client, **request_args)
            self.record(response)
            return response

        with patch.object(unittest.TestResult, "startTest", start), patch.object(Client, "request", request):
            result = super().run_suite(suite, **kwargs)
        summary = {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                   "skipped": len(result.skipped), "requests": len(self.events),
                   "route_names": sorted({row["route"] for row in self.events}),
                   "templates": sorted({name for row in self.events for name in row["templates"]})}
        (self.folder / f"{self.phase}-requests.json").write_text(json.dumps(self.events, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.folder / f"{self.phase}-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return result

    def record(self, response):
        try:
            request = response.wsgi_request
            match = request.resolver_match
            route_name = (match.view_name or "(root redirect)") if match is not None else "(unmatched URL)"
            templates = sorted({str(t.name) for t in getattr(response, "templates", ()) if t.name and
                                (Path(settings.BASE_DIR) / "templates" / t.name).exists()})
            html = response.content.decode(response.charset or "utf-8") if "text/html" in response.get("Content-Type", "") else ""
            dom = SurfaceDOM()
            dom.feed(html)
            visible = " ".join(dom.text)
            states = []
            if dom.invalid:
                states.append("INVALID FORM")
            if response.status_code >= 400:
                states.append("ERROR")
            if any("disabled" in c for c in dom.controls):
                states.append("DISABLED")
            if any("readonly" in c for c in dom.controls):
                states.append("READONLY")
            if any(s in visible for s in ("Chưa có", "Không có kết quả", "chưa có thành phần", "chưa có công đoạn")):
                states.append("EMPTY / FILTER NO RESULT")
            if dom.tags["tr"] > 2:
                states.append("POPULATED")
            states += sorted(dom.statuses)
            row = {"test": self.current_test, "route": route_name,
                   "path": request.path, "method": request.method, "query_keys": sorted(request.GET),
                   "post_keys": sorted(request.POST), "htmx": request.headers.get("HX-Request") == "true",
                   "status": response.status_code, "templates": templates, "states": sorted(set(states)),
                   "dom": {"controls": len(dom.controls), "invalid_fields": dom.invalid,
                           "rows": dom.tags["tr"], "tables": dom.tags["table"], "scoped_headers": dom.scoped_headers,
                           "labelled_controls": sum(c.get("id") in dom.labels for c in dom.controls),
                           "max_text_length": max(map(len, dom.text), default=0)}}
            with self.lock:
                self.events.append(row)
        except (AttributeError, LookupError, UnicodeError, ValueError):
            # Streaming/non-UI responses are audited by route inventory separately.
            return
