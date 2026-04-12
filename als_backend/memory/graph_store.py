# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Graph Store (JSON file persistence)
# ──────────────────────────────────────────────────────────────
#
# Improvements:
#   - FileLock on every read/write (prevents concurrent corruption)
#   - Schema error recovery (corrupt JSON → fresh graph instead of crash)
#   - Save is atomic within the same lock context as load
# ──────────────────────────────────────────────────────────────

import json
import logging
import os
import time
from pathlib import Path

from filelock import FileLock, Timeout
from pydantic import ValidationError

from models import GraphState
from seed.concept_graph import build_initial_graph, merge_seed_into_existing

log = logging.getLogger(__name__)


class GraphStore:
    """Load / save / reset student graphs as JSON files with file locking."""

    def __init__(self, store_dir: str) -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, student_id: str) -> Path:
        return self.store_dir / f"graph_{student_id}.json"

    def _lock(self, student_id: str) -> FileLock:
        lock_path = self.store_dir / f"graph_{student_id}.lock"
        return FileLock(str(lock_path), timeout=10)

    def load(self, student_id: str) -> GraphState:
        """Load a student graph from disk, or create a fresh one.

        Uses a file lock to prevent concurrent read/write corruption.
        Recovers gracefully from schema validation errors (returns fresh graph).
        """
        path = self._path(student_id)
        lock = self._lock(student_id)

        try:
            with lock:
                if path.exists():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        graph = GraphState(**data)
                    except (json.JSONDecodeError, ValidationError, KeyError) as e:
                        log.error(
                            f"Corrupt graph file for student '{student_id}': {e}. "
                            f"Resetting to fresh graph."
                        )
                        graph = build_initial_graph(student_id)
                        self._write(path, graph)

                    # Merge any newly-added seed concepts (hot-add without wiping scores)
                    graph = merge_seed_into_existing(graph)
                    return graph
                else:
                    graph = build_initial_graph(student_id)
                    self._write(path, graph)
                    return graph

        except Timeout:
            log.error(f"Could not acquire file lock for student '{student_id}' within 10s.")
            # Return a fresh graph as a safe fallback — don't crash the request
            return build_initial_graph(student_id)

    def save(self, student_id: str, graph: GraphState) -> None:
        """Persist the graph state to disk under a file lock."""
        path = self._path(student_id)
        lock = self._lock(student_id)

        try:
            with lock:
                self._write(path, graph)
        except Timeout:
            log.error(f"Could not acquire file lock for save (student '{student_id}'). Data not persisted.")

    def _write(self, path: Path, graph: GraphState) -> None:
        """Write graph to disk. Must be called while holding the file lock."""
        # Write to a temp file then rename — atomic on most OSes
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(graph.model_dump(), f, indent=2)
        tmp.replace(path)

    def reset_session(self, graph: GraphState) -> GraphState:
        """Reset session-scoped fields without touching lifetime data."""
        from models import SessionState
        for node in graph.nodes:
            node.session_activated = False
        graph.session_concept_ids = []
        graph.session_start_ts = time.time()
        # Initialize/Reset SessionState
        graph.session_state = SessionState()
        return graph
