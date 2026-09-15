"""The Gate 2 mobile (ETC1S) timing sample: the walk-near ARCH groups, printed as job ids on one line.

The brief asks for the ETC1S variants of "the hero-near set". Measured (export/out/gate2/probe.json), that set as
the plan defines it is EMPTY: cam01 stands 100 m out in the lagoon and the nearest group inside its frame is the
backdrop lamp post at 36.2 m, so nothing is "inside the cam01 frame within 30 m". The walkthrough's own stations
do come close, so the sample is the ARCH groups within 30 m of any of the six QA stations.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate2_common as g2  # noqa: E402

NEAR_M = 30.0
jobs = g2.read_jobs()["jobs"]
sample = [j["id"] for j in jobs
          if j["cls"] == g2.CLS_ARCH and (j.get("station_min_d_m") or 1e9) <= NEAR_M]
print(" ".join(sorted(sample)))
