"""Private local SQLite store; one sanitized snapshot per trace."""
from contextlib import contextmanager
import json
import os
import sqlite3
from pathlib import Path
from observability.redaction import redact_mapping

class TraceStore:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv('PSI_TRACE_DB', '.psi-traces/traces.sqlite3'))
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS traces (id TEXT PRIMARY KEY, timestamp TEXT, data TEXT)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, trace):
        value = redact_mapping(trace.as_dict(), max_depth=20)
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO traces VALUES (?, ?, ?)', (value['trace_id'], value['timestamp'], json.dumps(value)))

    def get(self, trace_id):
        with self.connect() as db:
            row = db.execute('SELECT data FROM traces WHERE id=?', (trace_id,)).fetchone()
        if row is None:
            raise KeyError(trace_id)
        return json.loads(row[0])

    def list(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT data FROM traces ORDER BY timestamp DESC')]
