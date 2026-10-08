"""Collect distributable assets; raw Tailwind input is build source only."""
from django.contrib.staticfiles.finders import FileSystemFinder


class BuiltAssetFinder(FileSystemFinder):
    def list(self, ignore_patterns):
        yield from super().list([*ignore_patterns, "src"])
