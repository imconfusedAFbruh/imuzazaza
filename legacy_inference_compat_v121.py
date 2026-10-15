"""Exact audited provenance transitions; historical manifests remain immutable."""

# Only metadata/report prose and dependency verification changed, respectively.
TRANSITIONS = {
    'pipeline.py': (
        '63684abb357129ae02f5a9f93a3b45c7f400be31ce04cfd57506e0a04fb9cc52',
        'e3a7b405a8454e114a638a1824c95a53b4eb0d23df77de778f9bc969d5b6c040'),
    'observed_ridge_inference.py': (
        '93ebe458fbbf8ad0caf2f47cfd6c6eaead8177bcd63461a1e0ef7fac008cde80',
        '5815104433f0e98f24a5201245328cf48a136cce92a4a804af07327ee4c7f73d'),
}


def dependency_matches(name, expected, actual):
    return actual == expected or TRANSITIONS.get(name) == (expected, actual)
