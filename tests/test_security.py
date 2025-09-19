from pathlib import Path
import pytest

from server_lib.security import safe_resolve_path, ForbiddenError


def test_safe_resolve_ok(tmp_path: Path):
    resources = tmp_path / "resources"
    target = resources / "sub" / "file.txt"
    target.parent.mkdir(parents=True)
    target.write_text("x")
    resolved = safe_resolve_path("sub/file.txt", resources)
    assert resolved == target.resolve()


def test_safe_resolve_traversal(tmp_path: Path):
    resources = tmp_path / "resources"
    resources.mkdir(parents=True)
    with pytest.raises(ForbiddenError):
        safe_resolve_path("../etc/passwd", resources)
