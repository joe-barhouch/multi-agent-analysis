import importlib.util
import pathlib
import sys

import pytest

# Ensure project root is on sys.path for `src` imports
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load the module directly to avoid importing package-level side effects
MODULE_PATH = PROJECT_ROOT / "src" / "agents" / "database_manager.py"
spec = importlib.util.spec_from_file_location("dbm", str(MODULE_PATH))
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load module from {MODULE_PATH}")
dbm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dbm)

validate_sql_query = dbm.validate_sql_query
SQLSecurityError = dbm.SQLSecurityError


def assert_allow(q: str):
    assert validate_sql_query(q) == q.strip()


def assert_block(q: str, msg_contains: str | None = None):
    with pytest.raises(SQLSecurityError) as e:
        validate_sql_query(q)
    if msg_contains:
        assert msg_contains in str(e.value).lower()


@pytest.mark.parametrize(
    "query",
    [
        "SELECT 1",
        (
            """
            WITH a AS (
              SELECT 1 AS x
            ), b AS (
              SELECT 2 AS x
            )
            SELECT * FROM a UNION ALL SELECT * FROM b
            """
        ),
        "SELECT 'DROP' AS word",
        "SELECT 1 -- DROP TABLE x",
        'SELECT "DROP" AS c',
        "SELECT ';' AS semi",
        "SELECT * FROM (SELECT 1) s",
    ],
)
def test_allowed_queries(query: str):
    assert_allow(query)


@pytest.mark.parametrize(
    ("query", "msg"),
    [
        ("SELECT 1; SELECT 2", "single sql statement"),
        ("DELETE FROM t", "dangerous sql operation 'delete'"),
        ("DROP TABLE t", "dangerous sql operation 'drop'"),
        ("INSERT INTO t VALUES (1)", "only select queries"),
        (
            "WITH x AS (SELECT 1) SELECT * FROM x; DELETE FROM y",
            "single sql statement",
        ),
        (
            "SELECT * FROM t UNION SELECT * FROM u WHERE 1=1; DROP TABLE x",
            "single sql statement",
        ),
    ],
)
def test_blocked_queries(query: str, msg: str):
    assert_block(query, msg)
