#!/usr/bin/env python3
"""
Auto-Enqueue: queue agent tasks for enriched vacancies.

Usage:
    python auto_enqueue.py              # queue all enriched vacancies with score >= 70
    python auto_enqueue.py --score=60   # custom score threshold
    python auto_enqueue.py --all        # include already-queued vacancies (re-queue)

Creates agent_tasks entries that the Chrome Extension polls and auto-fills.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from auto_enrich import auto_enqueue_enriched


if __name__ == "__main__":
    score_threshold = 70

    for arg in sys.argv:
        if arg.startswith("--score="):
            try:
                score_threshold = int(arg.split("=")[1])
            except ValueError:
                pass

    queued = auto_enqueue_enriched(score_threshold)
    print(f"\n📬 Queued {queued} tasks for browser extension.")
