"""Handle-pinned Windows filesystem primitives for the installer.

The public helpers in this module reject every reparse point in a path, pin
existing directory ancestry without FILE_SHARE_DELETE, and perform final file
replacement or deletion through an open handle.  The module is imported only
on Windows; it deliberately has no third-party dependencies.
"""

from __future__ import annotations

import ctypes
import os
import secrets
from contextlib import AbstractContextManager
from ctypes import wintypes
from pathlib import Path
from typing import Callable


if os.name != "nt":  # pragma: no cover - parsed on POSIX, imported on Windows
    raise ImportError("windows_fs is available only on Windows")


class UnsafePathError(OSError):
    """A path crossed a reparse point or a non-directory component."""


FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_WRITE_THROUGH = 0x80000000
FILE_READ_ATTRIBUTES = 0x00000080
FILE_TRAVERSE = 0x00000020
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
DELETE = 0x00010000
SYNCHRONIZE = 0x00100000
CREATE_NEW = 1
OPEN_EXISTING = 3
FILE_RENAME_INFO_CLASS = 3
FILE_DISPOSITION_INFO_CLASS = 4
FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
ERROR_FILE_NOT_FOUND = 2
ERROR_PATH_NOT_FOUND = 3
ERROR_FILE_EXISTS = 80
ERROR_ALREADY_EXISTS = 183
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = [
        ("FileAttributes", wintypes.DWORD),
        ("ReparseTag", wintypes.DWORD),
    ]


class _FILE_DISPOSITION_INFO(ctypes.Structure):
    _fields_ = [("DeleteFile", wintypes.BOOLEAN)]


class _FILE_RENAME_INFO(ctypes.Structure):
    _fields_ = [
        ("ReplaceIfExists", wintypes.BOOLEAN),
        ("RootDirectory", wintypes.HANDLE),
        ("FileNameLength", wintypes.DWORD),
        ("FileName", wintypes.WCHAR * 1),
    ]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HANDLE,
]
kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CreateDirectoryW.argtypes = [wintypes.LPCWSTR, wintypes.LPVOID]
kernel32.CreateDirectoryW.restype = wintypes.BOOL
kernel32.GetFileInformationByHandleEx.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
]
kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
kernel32.SetFileInformationByHandle.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
]
kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
kernel32.ReadFile.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    wintypes.LPVOID,
]
kernel32.ReadFile.restype = wintypes.BOOL
kernel32.WriteFile.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    wintypes.LPVOID,
]
kernel32.WriteFile.restype = wintypes.BOOL
kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
kernel32.FlushFileBuffers.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


def _win_error(path: Path | None = None) -> OSError:
    error = ctypes.get_last_error()
    exc = ctypes.WinError(error)
    if path is not None:
        exc.filename = os.fspath(path)
    return exc


def _error_number(exc: OSError) -> int | None:
    return getattr(exc, "winerror", None) or exc.errno


def _is_missing(exc: OSError) -> bool:
    return _error_number(exc) in {ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND}


def _local_absolute(path: Path) -> Path:
    result = Path(os.path.abspath(path))
    if not result.is_absolute() or not result.drive:
        raise UnsafePathError(f"Windows mutation requires an absolute local path: {path}")
    if result.drive.startswith("\\\\") or result.anchor.startswith("\\\\"):
        raise UnsafePathError(f"Windows mutation does not support UNC paths: {result}")
    return result


def _close(handle: int | None) -> None:
    if handle not in {None, INVALID_HANDLE_VALUE}:
        kernel32.CloseHandle(handle)


def _attributes(handle: int, path: Path) -> _FILE_ATTRIBUTE_TAG_INFO:
    result = _FILE_ATTRIBUTE_TAG_INFO()
    if not kernel32.GetFileInformationByHandleEx(
        handle,
        FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(result),
        ctypes.sizeof(result),
    ):
        raise _win_error(path)
    return result


def _open_existing(path: Path, access: int, *, directory: bool) -> int:
    flags = FILE_FLAG_OPEN_REPARSE_POINT
    if directory:
        flags |= FILE_FLAG_BACKUP_SEMANTICS
    handle = kernel32.CreateFileW(
        os.fspath(path),
        access,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        flags,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        raise _win_error(path)
    try:
        info = _attributes(handle, path)
        if info.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
            raise UnsafePathError(f"path traverses a Windows reparse point: {path}")
        is_directory = bool(info.FileAttributes & FILE_ATTRIBUTE_DIRECTORY)
        if directory != is_directory:
            expected = "directory" if directory else "regular file"
            raise UnsafePathError(f"path component is not a {expected}: {path}")
        return handle
    except Exception:
        _close(handle)
        raise


def _create_directory(path: Path) -> None:
    if kernel32.CreateDirectoryW(os.fspath(path), None):
        return
    error = ctypes.get_last_error()
    if error not in {ERROR_ALREADY_EXISTS, ERROR_FILE_EXISTS}:
        raise _win_error(path)


class PinnedParent(AbstractContextManager["PinnedParent"]):
    """Open and retain every directory handle down to a target's parent."""

    def __init__(self, target: Path, *, create: bool):
        self.target = _local_absolute(target)
        self.parent = self.target.parent
        self.leaf = self.target.name
        if not self.leaf or self.leaf in {".", ".."}:
            raise UnsafePathError(f"target needs a filename: {self.target}")
        self.handles: list[int] = []
        self._pin(create=create)

    @property
    def handle(self) -> int:
        return self.handles[-1]

    def _pin(self, *, create: bool) -> None:
        drive_root = Path(self.parent.anchor)
        current = drive_root
        try:
            directory_access = FILE_TRAVERSE | FILE_READ_ATTRIBUTES | SYNCHRONIZE
            self.handles.append(_open_existing(current, directory_access, directory=True))
            for part in self.parent.relative_to(drive_root).parts:
                current = current / part
                try:
                    handle = _open_existing(current, directory_access, directory=True)
                except OSError as exc:
                    if not create or not _is_missing(exc):
                        raise
                    _create_directory(current)
                    handle = _open_existing(current, directory_access, directory=True)
                self.handles.append(handle)
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        while self.handles:
            _close(self.handles.pop())

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


def _read_handle(handle: int, path: Path, max_bytes: int | None = None) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        buffer = ctypes.create_string_buffer(1024 * 1024)
        read = wintypes.DWORD()
        if not kernel32.ReadFile(handle, buffer, len(buffer), ctypes.byref(read), None):
            raise _win_error(path)
        if read.value == 0:
            break
        total += read.value
        if max_bytes is not None and total > max_bytes:
            raise OSError(f"file exceeds the {max_bytes}-byte safety limit: {path}")
        chunks.append(buffer.raw[: read.value])
    return b"".join(chunks)


def read_regular(path: Path, max_bytes: int | None = None) -> bytes:
    with PinnedParent(path, create=False):
        handle = _open_existing(_local_absolute(path), GENERIC_READ, directory=False)
        try:
            return _read_handle(handle, path, max_bytes)
        finally:
            _close(handle)


def read_regular_if_exists(path: Path, max_bytes: int | None = None) -> bytes | None:
    try:
        return read_regular(path, max_bytes)
    except OSError as exc:
        if _is_missing(exc):
            return None
        raise


def _write_handle(handle: int, path: Path, data: bytes) -> None:
    view = memoryview(data)
    while view:
        chunk = view[: 1024 * 1024]
        written = wintypes.DWORD()
        buffer = (ctypes.c_char * len(chunk)).from_buffer_copy(chunk)
        if not kernel32.WriteFile(handle, buffer, len(chunk), ctypes.byref(written), None):
            raise _win_error(path)
        if written.value <= 0:
            raise OSError(f"zero-byte write while creating {path}")
        view = view[written.value :]
    if not kernel32.FlushFileBuffers(handle):
        raise _win_error(path)


def _create_new_file(path: Path, access: int = GENERIC_WRITE | DELETE) -> int:
    handle = kernel32.CreateFileW(
        os.fspath(path),
        access,
        0,
        None,
        CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_WRITE_THROUGH,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        raise _win_error(path)
    return handle


def _mark_delete(handle: int, path: Path) -> None:
    info = _FILE_DISPOSITION_INFO(1)
    if not kernel32.SetFileInformationByHandle(
        handle,
        FILE_DISPOSITION_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        raise _win_error(path)


def _rename_pinned(handle: int, path: Path) -> None:
    # The Win32 SetFileInformationByHandle surface rejects RootDirectory on the
    # supported desktop path.  Use its documented full-name form while every
    # directory in that full name remains pinned without FILE_SHARE_DELETE.
    encoded = os.fspath(path).encode("utf-16-le")
    offset = _FILE_RENAME_INFO.FileName.offset
    # FILE_RENAME_INFO is declared with FileName[1].  Windows expects the full
    # structure size plus the variable filename bytes, including room for a
    # trailing wide NUL even though FileNameLength itself excludes that NUL.
    size = ctypes.sizeof(_FILE_RENAME_INFO) + len(encoded) + ctypes.sizeof(wintypes.WCHAR)
    buffer = ctypes.create_string_buffer(size)
    info = _FILE_RENAME_INFO.from_buffer(buffer)
    info.ReplaceIfExists = 1
    info.RootDirectory = None
    info.FileNameLength = len(encoded)
    ctypes.memmove(ctypes.addressof(buffer) + offset, encoded, len(encoded))
    if not kernel32.SetFileInformationByHandle(
        handle,
        FILE_RENAME_INFO_CLASS,
        buffer,
        size,
    ):
        raise _win_error(path)


def atomic_write(
    path: Path,
    data: bytes,
    safety_check: Callable[[], None] | None = None,
) -> None:
    target = _local_absolute(path)
    with PinnedParent(target, create=True) as parent:
        temporary = parent.parent / f".{parent.leaf}.{secrets.token_hex(12)}.tmp"
        handle = _create_new_file(temporary)
        renamed = False
        try:
            _write_handle(handle, temporary, data)
            if safety_check is not None:
                safety_check()
            _rename_pinned(handle, target)
            renamed = True
        finally:
            if not renamed:
                try:
                    _mark_delete(handle, temporary)
                except OSError:
                    pass
            _close(handle)


def exclusive_write(path: Path, data: bytes) -> None:
    target = _local_absolute(path)
    with PinnedParent(target, create=True):
        handle = _create_new_file(target, GENERIC_WRITE | DELETE)
        complete = False
        try:
            _write_handle(handle, target, data)
            complete = True
        finally:
            if not complete:
                try:
                    _mark_delete(handle, target)
                except OSError:
                    pass
            _close(handle)


def delete_regular(
    path: Path,
    safety_check: Callable[[], None] | None = None,
) -> None:
    target = _local_absolute(path)
    with PinnedParent(target, create=False):
        if safety_check is not None:
            safety_check()
        handle = _open_existing(target, GENERIC_READ | DELETE, directory=False)
        try:
            _mark_delete(handle, target)
        finally:
            _close(handle)


def ensure_directory(path: Path) -> None:
    marker = _local_absolute(path) / ".pitcrew-directory-marker"
    with PinnedParent(marker, create=True):
        pass


def make_unique_directory(base: Path, prefix: str) -> Path:
    base = _local_absolute(base)
    ensure_directory(base)
    for _ in range(100):
        candidate = base / f"{prefix}{secrets.token_hex(12)}"
        with PinnedParent(candidate, create=False):
            if kernel32.CreateDirectoryW(os.fspath(candidate), None):
                handle = _open_existing(
                    candidate,
                    FILE_TRAVERSE | FILE_READ_ATTRIBUTES | SYNCHRONIZE,
                    directory=True,
                )
                _close(handle)
                return candidate
            error = ctypes.get_last_error()
            if error not in {ERROR_ALREADY_EXISTS, ERROR_FILE_EXISTS}:
                raise _win_error(candidate)
    raise OSError(f"cannot allocate an exclusive directory below {base}")
