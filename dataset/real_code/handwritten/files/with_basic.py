"""Read a config blob off disk."""


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()
