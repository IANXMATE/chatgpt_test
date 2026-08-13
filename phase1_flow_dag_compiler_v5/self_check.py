from proof_compiler.params import ParameterDomain
from proof_compiler.paper import build_root_certificate
from proof_compiler.explorer import ProofSpaceExplorer
from proof_compiler.flow_model import build_flow_blueprint
from proof_compiler.chain_analysis import analyze_unique_rewrite_chains
from proof_compiler.conflict_analysis import analyze_bundle_conflicts

root_states, roots = build_root_certificate()
ex = ProofSpaceExplorer(ParameterDomain(), max_states=200000)
structural = ex.explore(root_states, roots)

flow = build_flow_blueprint(structural.states, structural.transitions)
chains = analyze_unique_rewrite_chains(
    structural.states, structural.transitions
)
conf = analyze_bundle_conflicts(flow["bundle_rules"])

assert len(structural.states) == 137
assert len(structural.transitions) == 67
assert "lambda_source__P4_2_alpha_one_third" in {
    v["name"] for v in flow["flow_variables"]
}
assert any(
    r["name"] == "paper_G2_to_G1_G13_G6_G14"
    for r in flow["linear_rewrite_rules"]
)
assert any(
    "x_cancel" in v["name"]
    for v in flow["flow_variables"]
)
assert len(chains["chains"]) > 0

print("SELF-CHECK OK")
print("states =", len(structural.states))
print("transitions =", len(structural.transitions))
print("flow vars =", len(flow["flow_variables"]))
print("chains =", len(chains["chains"]))
print("crossing bundle conflicts =", conf["crossing_count"])
