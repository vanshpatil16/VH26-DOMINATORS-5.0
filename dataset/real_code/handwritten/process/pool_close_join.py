"""A worker pool that is always closed and joined."""

import multiprocessing


def square_all(values):
    pool = multiprocessing.Pool(processes=2)
    try:
        return pool.map(abs, values)
    finally:
        pool.close()
        pool.join()
