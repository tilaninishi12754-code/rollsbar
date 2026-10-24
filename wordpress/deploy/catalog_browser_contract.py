"""Current integrated DOM contract, independently testable without a browser."""
from collections import Counter


def verify_catalog(main, hits, representations, canonical):
    assert len(canonical) == len(set(canonical)) == 118, 'canonical identity count'
    assert len(main) == 118 and set(main) == set(canonical), 'main catalog identity mismatch'
    assert len(hits) == len(set(hits)) == 8, 'Hits count/identity mismatch'
    assert set(hits) <= set(main), 'Hits must reference main canonical identities'
    assert len(representations) == 126, 'representation count mismatch'
    assert Counter(representations) == Counter(main) + Counter(hits), 'representation membership mismatch'
    assert len(set(representations)) == 118, 'unique representation identities'
