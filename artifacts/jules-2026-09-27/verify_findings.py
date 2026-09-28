import ast
import json
import logging
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from starlette.middleware.cors import CORSMiddleware
from youtube_extension.backend.services.database_cleanup_service import DatabaseCleanupService, RetentionPolicy

root = Path(__file__).resolve().parents[2]
results = {}
# Execute only the actual CORS configuration nodes, avoiding unrelated service startup.
for relative in ['src/youtube_extension/backend/main.py', 'src/youtube_extension/main.py']:
    tree = ast.parse((root / relative).read_text())
    cors_call = next(n.value for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and any(isinstance(a, ast.Name) and a.id == 'CORSMiddleware' for a in n.value.args))
    env = {'os': os, 'urlparse': urlparse, 'logger': logging.getLogger('cors-check')}
    if relative == 'src/youtube_extension/main.py':
        first = next(i for i,n in enumerate(tree.body) if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id == '_ENVIRONMENT' for t in n.targets))
        last = next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Expr) and n.value is cors_call)
        with patch.dict(os.environ, {'ENVIRONMENT':'production','CORS_ALLOWED_ORIGINS':'*,null,http://localhost:3000'}):
            exec(compile(ast.Module(body=tree.body[first:last], type_ignores=[]), str(root/relative), 'exec'), env)
    kwargs = {k.arg:eval(compile(ast.Expression(k.value),str(root/relative),'eval'),env) for k in cors_call.keywords}
    middleware = CORSMiddleware(lambda *args: None, **kwargs)
    assert middleware.is_allowed_origin('https://uvai.io')
    assert not middleware.is_allowed_origin('https://untrusted.example')
    assert not middleware.is_allowed_origin('https://uvai.io.untrusted.example')
    assert not middleware.is_allowed_origin('null')
    results[relative] = {'allowed_origins':kwargs['allow_origins'], 'arbitrary_origin_rejected':True,'localhost_allowed':middleware.is_allowed_origin('http://localhost:3000')}
assert results['src/youtube_extension/main.py']['localhost_allowed'] is False

with TemporaryDirectory() as d:
    db = Path(d)/'test.db'
    old = (datetime.now(timezone.utc)-timedelta(days=60)).isoformat()
    recent = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE events (timestamp TEXT)')
        conn.executemany('INSERT INTO events VALUES (?)', [(old,)]*5+[(recent,)])
    statements=[]
    real_connect=sqlite3.connect
    def traced_connect(*args,**kwargs):
        conn=real_connect(*args,**kwargs)
        conn.set_trace_callback(statements.append)
        return conn
    svc=DatabaseCleanupService(config_path=str(Path(d)/'absent.json'))
    with patch('sqlite3.connect', side_effect=traced_connect):
        result=svc.cleanup_table(str(db), RetentionPolicy('events',30,batch_size=2))
    assert result.success and result.records_deleted == 5
    pragma=[s for s in statements if s.upper().startswith('PRAGMA TABLE_INFO')]
    deletes=[s for s in statements if s.upper().startswith('DELETE')]
    assert len(pragma)==1 and len(deletes)==3
    with real_connect(db) as conn:
        assert conn.execute('SELECT timestamp FROM events').fetchall()==[(recent,)]
    results['schema_cleanup']={'schema_queries':len(pragma),'delete_batches':len(deletes),'deleted':5,'retained':1}
print(json.dumps(results,indent=2))
