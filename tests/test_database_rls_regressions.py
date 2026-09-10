import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database.py"


def _load_tenant_regex():
    tree = ast.parse(DATABASE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_TENANT_ID_RE":
                    pattern_node = node.value.args[0].args[0]
                    return ast.literal_eval(pattern_node)
    raise AssertionError("tenant regex not found")


def test_tenant_identifier_contract_is_strict():
    import re

    pattern = re.compile(_load_tenant_regex())
    assert pattern.fullmatch("tenant_0123456789abcdef")
    assert pattern.fullmatch("tenant-a.example:prod")
    assert not pattern.fullmatch("tenant with spaces")
    assert not pattern.fullmatch("tenant'; DROP TABLE users;--")
    assert not pattern.fullmatch("../tenant")
    assert not pattern.fullmatch("a" * 129)


def test_tenant_guc_uses_parameterized_set_config():
    source = DATABASE.read_text(encoding="utf-8")
    assert "SELECT set_config('app.tenant_id', %s, true)" in source
    assert "exec_driver_sql(f\"SET LOCAL {RLS_CONTEXT_PARAM}" not in source
