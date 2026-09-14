"""MinHash signatures and LSH banding in NumPy, followed by exact Jaccard verification.

LSH only proposes candidate pairs. Every reported similarity is the exact Jaccard of the
two token sets, so LSH affects recall (missed pairs), never the reported values.
With 16 bands of 4 hashes the 50% detection point is near Jaccard 0.50.
"""

import zlib
from collections import defaultdict
from itertools import combinations

import numpy as np

PRIME = np.uint64((1 << 31) - 1)


def signatures(token_sets, num_perm=64, seed=20260914):
    rng = np.random.default_rng(seed)
    a = rng.integers(1, (1 << 31) - 1, size=num_perm, dtype=np.uint64)
    b = rng.integers(0, (1 << 31) - 1, size=num_perm, dtype=np.uint64)

    vocab = {}
    flat, offsets = [], []
    for tokens in token_sets:
        offsets.append(len(flat))
        for token in tokens:
            if token not in vocab:
                vocab[token] = zlib.crc32(token.encode()) & 0x7FFFFFFF
            flat.append(vocab[token])
    x = np.array(flat, dtype=np.uint64)[:, None]
    hashed = (a[None, :] * x + b[None, :]) % PRIME
    return np.minimum.reduceat(hashed, np.array(offsets), axis=0)


def candidate_pairs(sigs, bands=16, max_bucket=3000):
    rows = sigs.shape[1] // bands
    pairs, skipped = set(), 0
    for band in range(bands):
        buckets = defaultdict(list)
        chunk = np.ascontiguousarray(sigs[:, band * rows : (band + 1) * rows])
        for index, key in enumerate(map(bytes, chunk)):
            buckets[key].append(index)
        for members in buckets.values():
            if len(members) > max_bucket:
                skipped += 1
                continue
            pairs.update(combinations(members, 2))
    return pairs, skipped


def jaccard(x: frozenset, y: frozenset) -> float:
    return len(x & y) / len(x | y)


def similar_pairs(token_sets, threshold=0.5):
    """Return {(i, j): jaccard} for all verified pairs at or above threshold (i < j)."""
    sigs = signatures(token_sets)
    pairs, skipped = candidate_pairs(sigs)
    verified = {}
    for i, j in pairs:
        score = jaccard(token_sets[i], token_sets[j])
        if score >= threshold:
            verified[(i, j)] = score
    return verified, {"candidates": len(pairs), "oversized_buckets_skipped": skipped}
