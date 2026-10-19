from __future__ import annotations

import inspect
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ComplexityInfo:
    key: str
    title: str
    aliases: tuple[str, ...]
    category: str
    best: str
    average: str
    worst: str
    space: str
    summary: str
    notes: tuple[str, ...]
    example: str


COMPLEXITY_DB: tuple[ComplexityInfo, ...] = (
    ComplexityInfo(
        key="list",
        title="CPython `list` (Dynamic Array)",
        aliases=("list", "array", "dynamic array"),
        category="Built-in Data Structure",
        best="O(1) index / append",
        average="O(1) index, append, pop()",
        worst="O(n) insert(0, x), pop(0), `x in lst`",
        space="O(n) contiguous over-allocated pointer array",
        summary="CPython's `list` is a dynamically resized array of `PyObject*` pointers (not a linked list). Indexing and end-operations are $O(1)$, while shifting from the front is $O(n)$.",
        notes=(
            "`lst[i]` / `lst[i] = x`: **O(1)**",
            "`lst.append(x)` / `lst.pop()`: **O(1)** amortized",
            "`lst.insert(0, x)` / `lst.pop(0)`: **O(n)** (use `collections.deque` for O(1) left-ops)",
            "`x in lst` / `lst.index(x)` / `lst.remove(x)`: **O(n)** linear scan",
            "`lst[a:b]`: **O(b - a)** slice copy",
            "`lst.sort()` / `sorted(lst)`: **O(n log n)** worst, **O(n)** best (Timsort / Powersort)",
        ),
        example=inspect.cleandoc(
            r"""
            from collections import deque

            # Use deque instead of list.pop(0) for queues:
            queue = deque([1, 2, 3])
            queue.append(4)          # O(1)
            first = queue.popleft()  # O(1)

            queue = deque([1, 2, 3])
            queue.append(4)          # O(1)
            first = queue.popleft()  # O(1)
            """
        ),
    ),
    ComplexityInfo(
        key="dict",
        title="CPython `dict` (Compact Open-Addressed Hash Table)",
        aliases=("dict", "dictionary", "hashmap", "hash table", "mapping", "counter"),
        category="Built-in Data Structure",
        best="O(1) lookup / insert / delete",
        average="O(1) lookup / insert / delete",
        worst="O(n) on pathological hash collisions",
        space="O(n) compact table (preserves insertion order since Python 3.7)",
        summary="CPython's `dict` uses a compact hash table separating a sparse index array from a dense entries array, preserving insertion order with low memory overhead.",
        notes=(
            "`d[k]` / `d.get(k)` / `k in d`: **O(1)** average, **O(n)** worst",
            "`d[k] = v` / `del d[k]` / `d.pop(k)`: **O(1)** amortized",
            "`d1 | d2`: **O(len(d1) + len(d2))**",
            "Iteration (`for k, v in d.items()`): **O(n)** in insertion order",
        ),
        example="# Fast O(n) total frequency counting\nfrom collections import Counter\ncounts = Counter(words)",
    ),
    ComplexityInfo(
        key="set",
        title="CPython `set` & `frozenset` (Hash Set)",
        aliases=("set", "frozenset", "hashset"),
        category="Built-in Data Structure",
        best="O(1) membership `x in s`",
        average="O(1) `add`, `remove`, `discard`, `in`",
        worst="O(n) on hash collisions",
        space="O(n) open-addressed hash table",
        summary="Unordered collection of unique hashable elements with $O(1)$ average membership testing and fast algebraic set operations.",
        notes=(
            "`x in s` / `s.add(x)` / `s.discard(x)`: **O(1)** average",
            "Union `s | t`: **O(len(s) + len(t))**",
            "Intersection `s & t`: **O(min(len(s), len(t)))** (iterates over the smaller set!)",
            "Difference `s - t`: **O(len(s))**",
        ),
        example="seen = set(large_list)  # O(n) build\nmatches = [x for x in queries if x in seen]  # O(1) per query!",
    ),
    ComplexityInfo(
        key="str",
        title="CPython `str` (Immutable Unicode Array — PEP 393)",
        aliases=("str", "string", "bytes", "join"),
        category="Built-in Data Structure",
        best="O(1) index `s[i]` / `len(s)`",
        average="O(n) slice, `''.join()`, substring `in`",
        worst="O(n * m) worst-case substring search",
        space="O(n) compact 1-, 2-, or 4-byte per code point buffer",
        summary="CPython strings store code points in a fixed-width array (1 byte Latin-1, 2 bytes UCS-2, or 4 bytes UCS-4), enabling $O(1)$ indexing by character position.",
        notes=(
            "`s[i]` / `len(s)` / `hash(s)` (cached): **O(1)**",
            "`''.join(parts)`: **O(total length)** — always prefer over `s += part` in loops",
            "`sub in s` / `s.find(sub)`: **O(n)** average via fast Boyer-Moore-Horspool / Two-Way algorithm",
        ),
        example="# Join a list of strings in O(n) instead of repeated concatenation:\noutput = ''.join(chunks)",
    ),
    ComplexityInfo(
        key="deque",
        title="`collections.deque` (Doubly-Linked Block Queue)",
        aliases=("deque", "queue", "collections.deque"),
        category="Standard Library Data Structure",
        best="O(1) append/pop at both ends",
        average="O(1) ends, O(n) random middle index",
        worst="O(n) `d[len(d) // 2]`, `remove(x)`",
        space="O(n) doubly-linked list of fixed-size 64-element blocks",
        summary="Implemented in C as a doubly-linked list of fixed-length pointer blocks, offering true $O(1)$ appends and pops on both ends.",
        notes=(
            "`append(x)` / `appendleft(x)`: **O(1)**",
            "`pop()` / `popleft()`: **O(1)**",
            "`rotate(k)`: **O(k)**",
            "`d[i]` (random access in the middle): **O(n)**",
        ),
        example=inspect.cleandoc(
            """
            from collections import deque

            window = deque(maxlen=3)  # bounded sliding window

            for x in [1, 2, 3, 4]:
                window.append(x)  # automatically drops oldest in O(1)
            """
        ),
    ),
    ComplexityInfo(
        key="heapq",
        title="`heapq` (Binary Min-Heap)",
        aliases=("heap", "heapq", "priority queue", "heappush", "heappop"),
        category="Standard Library Algorithm / Structure",
        best="O(1) peek `heap[0]`, O(n) `heapify`",
        average="O(log n) `heappush` / `heappop`",
        worst="O(log n) `heappush` / `heappop`",
        space="O(1) auxiliary (operates in-place on a `list`)",
        summary="Maintains the min-heap invariant (`heap[k] <= heap[2*k+1]` and `heap[k] <= heap[2*k+2]`) directly inside a standard Python `list`.",
        notes=(
            "Smallest item `heap[0]`: **O(1)**",
            "`heapq.heappush(h, x)` / `heapq.heappop(h)`: **O(log n)**",
            "`heapq.heapify(lst)`: **O(n)** bottom-up Floyd construction (faster than $n$ pushes!)",
            "`heapq.nlargest(k, it)` / `nsmallest(k, it)`: **O(n log k)**",
        ),
        example=inspect.cleandoc(
            """
            import heapq

            nums = [5, 1, 8, 3]

            heapq.heapify(nums)          # O(n) in-place
            lowest = heapq.heappop(nums) # -> 1 in O(log n)
            heapq.heappush(nums, 2)      # O(log n)
            """
        ),
    ),
    ComplexityInfo(
        key="timsort",
        title="Timsort / Powersort (`list.sort` & `sorted`)",
        aliases=("sort", "sorted", "timsort", "powersort", "sorting", "mergesort"),
        category="Sorting Algorithm",
        best="O(n) (already or mostly sorted data)",
        average="O(n log n)",
        worst="O(n log n)",
        space="O(n) worst-case temporary merge buffer (up to n // 2 pointers)",
        summary="Python's hybrid stable sort (Timsort, with Powersort merge policy since Python 3.11) exploits natural monotonic runs in real-world data and uses binary insertion sort on short runs.",
        notes=(
            "**Stable**: Equal elements strictly preserve their relative input order",
            "Uses `key=` (Schwartzian transform): computes `key(x)` once per item (**O(n)** key calls)",
            "In-place `list.sort()` avoids allocating a new outer list compared to `sorted()`",
        ),
        example="# Sort users by score descending, then username ascending (leveraging stability)\nusers.sort(key=lambda u: (-u.score, u.username.casefold()))",
    ),
    ComplexityInfo(
        key="quicksort",
        title="Quicksort (Partition-Exchange Sort)",
        aliases=("quicksort", "qsort", "quick sort"),
        category="Sorting Algorithm",
        best="O(n log n)",
        average="O(n log n)",
        worst="O(n²) (unbalanced pivots; avoided via random/median-of-3 pivot)",
        space="O(log n) auxiliary recursion stack (in-place partitioning)",
        summary="Divide-and-conquer sort that partitions elements around a pivot into `< pivot`, `== pivot`, and `> pivot`. Fast in cache, though not stable by default.",
        notes=(
            "3-way Dutch National Flag partitioning handles duplicate keys in **O(n)**",
            "In Python, built-in C `list.sort()` (Timsort) is almost always faster than a pure-Python Quicksort",
        ),
        example=inspect.cleandoc(
            """
            def quicksort(arr: list[int]) -> list[int]:
                if len(arr) <= 1:
                    return arr
                pivot = arr[len(arr) // 2]

                left = [x for x in arr if x < pivot]
                mid = [x for x in arr if x == pivot]
                right = [x for x in arr if x > pivot]

                return quicksort(left) + mid + quicksort(right)
            """
        ),
    ),
    ComplexityInfo(
        key="binary-search",
        title="Binary Search (`bisect`)",
        aliases=("bisect", "binary search", "bsearch", "bisect_left", "bisect_right"),
        category="Searching Algorithm",
        best="O(1)",
        average="O(log n)",
        worst="O(log n) comparisons",
        space="O(1) iterative",
        summary="Finds the insertion point for a target in a sorted sequence by repeatedly halving the search interval.",
        notes=(
            "`bisect.bisect_left(a, x)` / `bisect_right(a, x)`: **O(log n)** search",
            "`bisect.insort(a, x)`: **O(log n)** search + **O(n)** list shift = **O(n)** total",
            "Supports `key=` parameter in Python 3.10+",
        ),
        example=inspect.cleandoc(
            """
            import bisect

            def index_of(sorted_items: list[int], target: int) -> int:
                i = bisect.bisect_left(sorted_items, target)
                return i if i < len(sorted_items) and sorted_items[i] == target else -1
            """
        ),
    ),
    ComplexityInfo(
        key="bfs",
        title="Breadth-First Search (BFS) & Depth-First Search (DFS)",
        aliases=("bfs", "dfs", "breadth-first search", "depth-first search", "graph traversal"),
        category="Graph Algorithm",
        best="O(V + E)",
        average="O(V + E)",
        worst="O(V + E)",
        space="O(V) visited set & queue/stack",
        summary="Traverses vertices $V$ and edges $E$. BFS uses a FIFO `collections.deque` to find shortest paths in unweighted graphs; DFS uses a LIFO stack or recursion.",
        notes=(
            "Always use `collections.deque` for BFS (`popleft()` is **O(1)**; `list.pop(0)` makes BFS **O(V²)**!)",
            "Mark nodes `visited` when **enqueuing** (not when popping) to avoid duplicate queue entries",
        ),
        example=inspect.cleandoc(
            r"""
            from collections import deque

            def bfs(adj: dict[int, list[int]], start: int) -> set[int]:
                visited = {start}
                queue = deque([start])
                while queue:
                    node = queue.popleft()
                    for nxt in adj.get(node, ()):
                        if nxt not in visited:
                            visited.add(nxt)
                            queue.append(nxt)
                return visited
            """
        ),
    ),
    ComplexityInfo(
        key="dijkstra",
        title="Dijkstra's Shortest Path Algorithm",
        aliases=("dijkstra", "shortest path"),
        category="Graph Algorithm",
        best="O(E + V log V)",
        average="O((V + E) log V) with binary heap",
        worst="O((V + E) log V)",
        space="O(V + E)",
        summary="Finds shortest paths from a source vertex to all other vertices in a graph with non-negative edge weights using a min-heap (`heapq`).",
        notes=(
            "Requires **non-negative** edge weights (use Bellman-Ford $O(V \\cdot E)$ if negative weights exist)",
            "Skip stale heap entries with `if d > dist[u]: continue` rather than decrease-key",
        ),
        example=inspect.cleandoc(
            r"""
            import heapq

            def dijkstra(adj: dict[int, list[tuple[int, int]]], src: int) -> dict[int, int]:
                dist = {src: 0}
                pq = [(0, src)]
                while pq:
                    d, u = heapq.heappop(pq)
                    if d > dist.get(u, float('inf')):
                        continue
                    for v, w in adj.get(u, ()):
                        if d + w < dist.get(v, float('inf')):
                            dist[v] = d + w
                            heapq.heappush(pq, (d + w, v))
                return dist
            """
        ),
    ),
    ComplexityInfo(
        key="union-find",
        title="Disjoint Set Union (Union-Find / DSU)",
        aliases=("union-find", "dsu", "disjoint set", "kruskal"),
        category="Graph / Set Data Structure",
        best="O(1)",
        average="O(\N{GREEK SMALL LETTER ALPHA}(n)) ≈ O(1) amortized",
        worst="O(\N{GREEK SMALL LETTER ALPHA}(n)) with path compression + union by rank/size",
        space="O(n) parent & size arrays",
        summary="Tracks elements partitioned into disjoint subsets with near-constant $O(\\alpha(n))$ time for `find` and `union`, where $\\alpha$ is the inverse Ackermann function ($\\alpha(n) \\le 4$).",
        notes=(
            "**Path compression** flattens tree pointers during `find(x)`",
            "**Union by size/rank** attaches the smaller tree under the larger tree's root",
        ),
        example=inspect.cleandoc(
            """
            class DisjointSet:
                def __init__(self, n: int) -> None:
                    self.parent = list(range(n))
                    self.size = [1] * n

                def find(self, x: int) -> int:
                    while self.parent[x] != x:
                        self.parent[x] = self.parent[self.parent[x]]
                        x = self.parent[x]
                    return x
            """
        ),
    ),
    ComplexityInfo(
        key="big-o",
        title="Big-O Complexity Classes Cheat Sheet",
        aliases=("big-o", "bigo", "overview", "cheatsheet", "time complexity", "asymptotic"),
        category="Asymptotic Reference",
        best="O(1) Constant",
        average="O(log n) -> O(n) -> O(n log n)",
        worst="O(n²) -> O(2^n) -> O(n!)",
        space="Varies by algorithm",
        summary="Comparison of common asymptotic growth rates and typical maximum input size $n$ solvable within ~1 second in Python.",
        notes=(
            "`O(1)` Constant — dict/set lookup, list index/append ($n$: any)",
            "`O(log n)` Logarithmic — `bisect`, binary heap push/pop ($n \\approx 10^{18}$)",
            "`O(n)` Linear — single pass, `min`/`max`/`sum`, `heapify` ($n \\approx 10^7$)",
            "`O(n log n)` Linearithmic — `sorted()`, Timsort, divide & conquer ($n \\approx 10^6$)",
            "`O(n²)` Quadratic — nested loops, bubble/insertion sort ($n \\approx 3{,}000$)",
            "`O(2^n)` Exponential — subsets / bitmask backtracking ($n \\le 22$)",
            "`O(n!)` Factorial — `itertools.permutations` ($n \\le 10$)",
        ),
        example="# Rule of thumb in CPython: ~10^7 simple loop operations per second.\n# Built-in C functions (sum, min, set intersection, list.sort) are 10x-50x faster than Python loops.",
    ),
)
