from agents.graph import ROOT, get_audit, get_graph
from agents import graph as graph_mod


def test_checkpoint_file_created():
    get_graph()
    path = ROOT / "data" / "graph_checkpoints.sqlite"
    assert path.exists()
    assert path.stat().st_size > 0


def test_pause_survives_graph_rebuild():
    graph_mod._GRAPH = None
    graph_mod._SAVER = None
    graph = get_graph()
    tid = "ckpt-smoke"
    config = {"configurable": {"thread_id": tid}}
    graph.update_state(config, {"memo": "held on disk", "decision": ""})

    graph_mod._GRAPH = None
    graph_mod._SAVER = None
    out = get_audit(tid)
    assert out["values"].get("memo") == "held on disk"
