"""The leaky snippet is data, not code."""

TEMPLATE = "handle = open(path)"

BAD_EXAMPLE = """
connection = sqlite3.connect(path)
return connection.execute(query)
"""


def render(path):
    with open(path, encoding="utf-8") as handle:
        return TEMPLATE + handle.read()
