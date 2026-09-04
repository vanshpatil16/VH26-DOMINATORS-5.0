"""Reuse one HTTP session across a batch of requests."""

import requests


def fetch_all(urls):
    with requests.Session() as session:
        return [session.get(url).status_code for url in urls]
