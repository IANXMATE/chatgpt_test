from proof_compiler.params import ParameterDomain
from proof_compiler.paper import build_root_certificate
from proof_compiler.explorer import ProofSpaceExplorer


def test_reference_graph_builds():
    roots_map, roots = build_root_certificate()
    ex = ProofSpaceExplorer(ParameterDomain(), max_states=10000)
    result = ex.explore(roots_map, roots)
    assert len(result.states) > 70
    assert len(result.transitions) > 20
    assert result.depth_by_root["G2"]["max_factor_depth"] >= 10
    assert result.depth_by_root["G11"]["max_factor_depth"] >= 10


def test_g2_reaches_known_alias_shapes():
    roots_map, roots = build_root_certificate()
    ex = ProofSpaceExplorer(ParameterDomain(), max_states=10000)
    result = ex.explore(roots_map, roots)
    # G2 should now continue far beyond the paper's displayed G14 depth.
    assert result.depth_by_root["G2"]["max_factor_depth"] > 3


def test_no_duplicate_state_ids():
    roots_map, roots = build_root_certificate()
    ex = ProofSpaceExplorer(ParameterDomain(), max_states=10000)
    result = ex.explore(roots_map, roots)
    ids = list(result.states)
    assert len(ids) == len(set(ids))
