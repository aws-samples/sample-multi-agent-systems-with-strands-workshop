# This orchestrator runtime has been removed.
#
# Pattern 2 (Parallel Fork-Join) uses a deterministic GraphBuilder DAG with no
# LLM routing decisions. A deployed runtime container adds cost and complexity
# for no benefit in this pattern.
#
# The coordination logic now lives in ../chain.py — a simple Python script
# that uses Strands GraphBuilder for the fork-join topology.
#
# See: ../chain.py
