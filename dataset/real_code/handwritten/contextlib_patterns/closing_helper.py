"""closing() adapts anything with a close() to the with protocol."""

from contextlib import closing
from urllib.request import urlopen


def head_bytes(url, count=128):
    with closing(urlopen(url)) as response:
        return response.read(count)
