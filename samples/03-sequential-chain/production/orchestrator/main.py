# This orchestrator runtime has been removed.
#
# Pattern 1 (Sequential Chain) uses a deterministic fixed pipeline with no
# LLM routing decisions. A deployed runtime container adds cost and complexity
# for no benefit in this pattern.
#
# The coordination logic now lives in ../chain.py — a simple Python script
# that uses Strands GraphBuilder to call the three specialist runtimes locally.
#
# See: ../chain.py
