"""Opaque markers keep source positions independent of Markdown rendering."""
from uuid import uuid4

from ..core.models import InlineImage


class ImageCollector:
    def __init__(self):
        self.images = []

    def add(self, data, mime_type, label, *, html=False):
        token = "HYBRIDIMAGE" + uuid4().hex.upper()
        self.images.append(InlineImage(token, data, mime_type, label, html))
        return token
