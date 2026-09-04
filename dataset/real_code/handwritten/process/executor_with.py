"""ThreadPoolExecutor shuts down on block exit."""

import concurrent.futures


def fan_out(work, items):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        return list(executor.map(work, items))
