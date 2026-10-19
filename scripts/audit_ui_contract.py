"""Freeze UI contracts without connecting to the business database.

Capture once before a presentation rollout; compare afterwards. Existing Python
is byte-for-byte frozen. CSS classes/icons/local layout state are presentation.
"""
import argparse
import ast
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['APP_ENV'] = 'test'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.test_settings'

import django
django.setup()
from django import forms
from django.db import connections
from django.urls import URLResolver, get_resolver
from apps.master_data.navigation import SECTIONS, DESTINATIONS, NAVIGATION_LABELS


def scalar(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    if callable(value):
        return f'{value.__module__}.{getattr(value, "__qualname__", value.__class__.__name__)}'
    if isinstance(value, dict):
        return {str(k): scalar(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [scalar(v) for v in value]
    return str(value)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def routes(patterns, prefix='', namespace=''):
    result = []
    for pattern in patterns:
        route = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            scope = namespace + (pattern.namespace + ':' if pattern.namespace else '')
            result.extend(routes(pattern.url_patterns, route, scope))
        else:
            result.append({'path': route, 'name': namespace + (pattern.name or ''),
                           'view': f'{pattern.callback.__module__}.{pattern.callback.__name__}'})
    return result


def form_contracts():
    result = {}
    for path in sorted((ROOT / 'apps').rglob('*forms.py')):
        module_name = '.'.join(path.relative_to(ROOT).with_suffix('').parts)
        module = importlib.import_module(module_name)
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module_name or not issubclass(cls, forms.BaseForm):
                continue
            fields = {}
            for key, field in cls.base_fields.items():
                validators = []
                for validator in field.validators:
                    if hasattr(validator, 'deconstruct'):
                        validators.append(scalar(validator.deconstruct()))
                    else:
                        validators.append(scalar(validator))
                fields[key] = {'type': field.__class__.__name__, 'label': str(field.label),
                               'required': field.required, 'disabled': field.disabled,
                               'initial': scalar(field.initial), 'help': str(field.help_text),
                               'errors': scalar(field.error_messages), 'validators': validators,
                               'widget': field.widget.__class__.__name__,
                               'attrs': scalar(field.widget.attrs),
                               'min': scalar(getattr(field, 'min_value', None)),
                               'max': scalar(getattr(field, 'max_value', None)),
                               'digits': getattr(field, 'max_digits', None),
                               'places': getattr(field, 'decimal_places', None)}
                if isinstance(field, forms.ModelChoiceField):
                    fields[key]['relation'] = field.queryset.model._meta.label
                    fields[key]['empty_label'] = field.empty_label
                elif hasattr(field, 'choices'):
                    fields[key]['choices'] = scalar(list(field.choices))
            result[f'{module_name}.{name}'] = fields
    # This form creates its field in __init__; no ORM access is necessary.
    from apps.pricing.forms import ClosePeriodForm
    result['dynamic_close_fields'] = {
        resource: {k: {'type': f.__class__.__name__, 'label': str(f.label),
                       'required': f.required, 'disabled': f.disabled,
                       'initial': scalar(f.initial)}
                   for k, f in ClosePeriodForm(resource=resource).fields.items()}
        for resource in ('channel_fee_rule', 'tax_rule', 'fx_rate')}
    return result


ATTRS = re.compile(r'\b(hx-[\w-]+|id|name|value|method|action|href|for|role|aria-label)\s*=\s*([\"\'])(.*?)\2', re.S)


def template_contract(path):
    source = path.read_text(encoding='utf-8')
    # Only quoted HTML attributes; request attributes remain verbatim, including
    # Django expressions. Classes, tooltips and SVG presentation are excluded.
    attribute_source = re.sub(r'{%\s*include\s+"components/icon.html".*?%}', '', source, flags=re.S)
    attrs = Counter(f'{m[1]}={m[3]}' for m in ATTRS.finditer(attribute_source))
    business_source = re.sub(r'\bclass\s*=\s*([\"\']).*?\1', '', source, flags=re.S)
    bindings = Counter(re.sub(r'\s+', ' ', m[1].strip())
                       for m in re.finditer(r'{{(.*?)}}', business_source, re.S))
    blocks = Counter(re.sub(r'\s+', ' ', m[1].strip())
                     for m in re.finditer(r'{%(.*?)%}', business_source, re.S)
                     if m[1].strip().split()[0] not in ('load', 'include', 'block', 'endblock', 'extends'))
    return {'attributes': dict(attrs), 'bindings': dict(bindings), 'blocks': dict(blocks)}


def snapshot():
    # Any accidental query aborts the audit instead of reaching even localhost.
    def no_database(*args, **kwargs):
        raise RuntimeError('UI contract inventory must not query a database.')
    for connection in connections.all():
        connection.cursor = no_database
    paths = sorted([*(ROOT / 'apps').rglob('*.py'), *(ROOT / 'config').rglob('*.py'), ROOT / 'manage.py'])
    templates = sorted((ROOT / 'templates').rglob('*.html'))
    return {'python_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in paths},
            'routes': routes(get_resolver().url_patterns), 'forms': form_contracts(),
            'menu': scalar([SECTIONS, DESTINATIONS, NAVIGATION_LABELS]),
            'templates': {str(p.relative_to(ROOT)).replace('\\', '/'): template_contract(p) for p in templates},
            'counts': {'templates': len(templates),
                       'full_page_templates': sum(bool(re.search(r'{%\s*extends ', p.read_text(encoding='utf-8'))) for p in templates),
                       'partials': sum('partials' in p.parts for p in templates),
                       'components': sum(p.parent.name == 'components' for p in templates)}}


def compare(before, after):
    errors, presentation = [], []
    for key in ('routes', 'forms', 'menu'):
        if before[key] != after[key]:
            errors.append(f'{key}: contract changed')
    for path, value in before['python_sha256'].items():
        if after['python_sha256'].get(path) != value:
            errors.append(f'{path}: frozen Python changed')
    for path, contract in before['templates'].items():
        if path not in after['templates']:
            errors.append(f'{path}: existing template removed')
            continue
        current = after['templates'][path]
        old = Counter(contract['attributes'])
        new = Counter(current['attributes'])
        # New IDs/ARIA labels are visual/accessibility hooks. Existing request,
        # name/value/for/role attributes cannot be removed or changed.
        missing = old - new
        if missing:
            errors.append(f'{path}: removed/changed attributes {dict(missing)}')
        extra = new - old
        request_extra = {k: v for k, v in extra.items() if k.startswith(('hx-', 'name=', 'value=', 'method=', 'action='))}
        if request_extra:
            errors.append(f'{path}: new request attributes {request_extra}')
        for kind in ('bindings', 'blocks'):
            if contract[kind] != current[kind]:
                presentation.append({'template': path, 'kind': kind,
                                     'removed': dict(Counter(contract[kind]) - Counter(current[kind])),
                                     'added': dict(Counter(current[kind]) - Counter(contract[kind]))})
    return {'errors': errors, 'presentation_review': presentation,
            'counts_before': before['counts'], 'counts_after': after['counts'],
            'frozen_python_files': len(before['python_sha256']), 'routes': len(before['routes'])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('capture', 'compare'))
    parser.add_argument('--baseline', type=Path, default=ROOT / 'docs/ui-redesign/ui-contract-baseline.json')
    parser.add_argument('--report', type=Path, default=ROOT / 'artifacts/ui-redesign/contract-comparison.json')
    args = parser.parse_args()
    current = snapshot()
    if args.mode == 'capture':
        if args.baseline.exists():
            parser.error('Baseline already exists; never overwrite the pre-redesign evidence.')
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'counts': current['counts'], 'routes': len(current['routes']), 'forms': len(current['forms']) - 1}, indent=2))
    else:
        report = compare(json.loads(args.baseline.read_text(encoding='utf-8')), current)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        # Keep console JSON portable on Windows terminals using a legacy codepage.
        # The report file above retains readable UTF-8 Vietnamese labels.
        print(json.dumps(report, ensure_ascii=True, indent=2))
        raise SystemExit(bool(report['errors']))


if __name__ == '__main__':
    main()
