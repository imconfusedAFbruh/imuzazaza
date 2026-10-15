"""Fail closed for every transition other than the two reviewed exact pairs."""
import ast
from pathlib import Path
from legacy_inference_compat_v121 import TRANSITIONS, dependency_matches


def test_exact_transitions():
    for name, (old, new) in TRANSITIONS.items():
        assert dependency_matches(name, old, new)
        assert dependency_matches(name, old, old)
        assert not dependency_matches('other.py', old, new)
        assert not dependency_matches(name, '0'*64, new)
        assert not dependency_matches(name, old, '0'*64)
        assert not dependency_matches(name, new, old)


def test_prediction_bodies_unchanged():
    root = Path(__file__).resolve().parent
    for name in ('observed_ridge_inference.py', 'dynamic_blend_inference_v34.py'):
        before = ast.parse((root/'research_state/v121_package_failure'/name).read_text())
        after = ast.parse((root/name).read_text())
        def predictions(tree):
            return [ast.dump(node) for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == 'predict']
        assert predictions(before) == predictions(after)


if __name__ == '__main__':
    test_exact_transitions()
    test_prediction_bodies_unchanged()
    print('Exact transition rejection and unchanged prediction checks passed')
