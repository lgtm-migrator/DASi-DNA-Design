import bisect


def sort_with_keys(a, key):
    s = sorted(a, key=key)
    keys = [key(x) for x in s]
    return s, keys


def bisect_between(a, low, high):
    """
    Returns the start (inclusive) and end (exclusive) indices
    for a sorted array using a key function.

    :param a: sorted array (does not check)
    :param low: low key
    :param high: high key
    :param key: key function
    :return: tuple of start (inclusive) and end (exclusive) indices
    """
    i = bisect.bisect_left(a, low)
    j = bisect.bisect_right(sorted(a[i:]), high)
    return i, j + i


def bisect_slice_between(a, keys, low, high):
    i, j = bisect_between(keys, low, high)
    return a[i:j]

