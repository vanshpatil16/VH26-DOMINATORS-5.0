"""Fetch a URL through closing()."""

import contextlib
from urllib.request import urlopen


def fetch(url):
    with contextlib.closing(urlopen(url)) as response:
        return response.read()
