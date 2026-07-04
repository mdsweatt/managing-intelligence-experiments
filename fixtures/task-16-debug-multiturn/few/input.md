We have a small utility that's misbehaving. Here is the function and the failing test.

```python
# intervals.py
def merge_intervals(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current in intervals[1:]:
        last = merged[-1]
        if current[0] < last[1]:
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)
    return merged
```

```python
# test_intervals.py
def test_merge():
    assert merge_intervals([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]
    assert merge_intervals([(1, 4), (4, 5)]) == [(1, 5)]   # adjacent should merge
    assert merge_intervals([]) == []
```

Running the test:

```
    assert merge_intervals([(1, 4), (4, 5)]) == [(1, 5)]
AssertionError: [(1, 4), (4, 5)] != [(1, 5)]
```
