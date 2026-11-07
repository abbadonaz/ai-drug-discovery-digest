"""Atomic individual writes and staged multi-file replacement with rollback."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path
import tempfile
from typing import Mapping


def stage_bytes(target: Path, content: bytes, suffix=".stage") -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", suffix=suffix, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return temporary
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def atomic_write_text(path, text: str):
    target = Path(path)
    staged = stage_bytes(target, text.encode("utf-8"))
    try:
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)


class PublicationRollbackError(RuntimeError):
    """Rollback failed; retained backup paths must be inspected before retry."""


def replace_files(contents: Mapping[Path, str], validate):
    """Validate all staged bytes before replacement; restore on caught failures.

    Mapping order is commit order. Put a completion manifest last. Each replace
    is atomic; the group is not. Backups survive if rollback cannot complete.
    """
    staged, backups, replaced = {}, {}, []
    retain_backups = False
    try:
        for target, text in contents.items():
            staged[target] = stage_bytes(target, text.encode("utf-8"))
            staged_text = staged[target].read_text(encoding="utf-8")
            if staged_text != text:
                raise ValueError(f"Staged content differs from generated output: {target}")
            validate(target, staged_text)
            backups[target] = stage_bytes(target, target.read_bytes(), ".backup") if target.exists() else None
        try:
            for target, temporary in staged.items():
                os.replace(temporary, target)
                replaced.append(target)
        except BaseException as error:
            failures = []
            for target in reversed(replaced):
                try:
                    backup = backups[target]
                    if backup is None:
                        target.unlink(missing_ok=True)
                    else:
                        os.replace(backup, target)
                except OSError:
                    failures.append(str(target))
            if failures:
                retain_backups = True
                raise PublicationRollbackError(
                    f"Rollback failed for {failures}; inspect retained .backup files and publication lock"
                ) from error
            raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
        if not retain_backups:
            for backup in backups.values():
                if backup is not None:
                    backup.unlink(missing_ok=True)


_locks = ContextVar("publication_locks", default=())


@contextmanager
def publication_lock(path):
    """Cooperating runs serialize; stale crash/rollback-failure locks fail closed."""
    path = Path(path).resolve()
    if path in _locks.get():
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    token = _locks.set((*_locks.get(), path))
    retain = False
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"pid={os.getpid()}\n")
            stream.flush()
            os.fsync(stream.fileno())
        yield
    except PublicationRollbackError:
        retain = True
        raise
    finally:
        _locks.reset(token)
        if not retain:
            path.unlink(missing_ok=True)
