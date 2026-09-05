"""Acquire, release, then acquire a second time and release again."""

import ftplib


def telemetry_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = ftplib.FTP(host)
    try:
        client.login(user, secret)
    finally:
        client.close()
    retry = ftplib.FTP(host)
    try:
        retry.login(user, secret)
    finally:
        retry.close()
    return payload
