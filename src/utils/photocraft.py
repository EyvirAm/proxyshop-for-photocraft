"""
* Utils: Photocraft CLI & Headless JSON-RPC Backend
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from photoshop.api import Application

_logger = logging.getLogger(__name__)


def find_photocraft_cli() -> str:
    """Locate the photocraft-cli binary from env, system install, local repo, or PATH."""
    env_cli = os.getenv("PHOTOCRAFT_CLI")
    if env_cli and Path(env_cli).exists():
        return env_cli

    program_files = Path(os.getenv("ProgramFiles", r"C:\Program Files"))
    local_appdata = Path(os.getenv("LOCALAPPDATA", r"C:\Users\usuario\AppData\Local"))
    repo_root = Path(__file__).resolve().parents[3] / "photocraft-repo"
    candidates = [
        program_files / "PhotoCraft" / "photocraft-cli.exe",
        local_appdata / "Programs" / "PhotoCraft" / "photocraft-cli.exe",
        repo_root / "target" / "release" / "photocraft-cli.exe",
        repo_root / "target" / "debug" / "photocraft-cli.exe",
        repo_root / "target" / "release" / "photocraft-cli",
        repo_root / "target" / "debug" / "photocraft-cli",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    which_cli = shutil.which("photocraft-cli")
    if which_cli:
        return which_cli

    return env_cli or "photocraft-cli"


class PhotocraftRpcServer:
    """Manages a persistent `photocraft-cli serve` stdio JSON-lines session."""

    def __init__(self, cli_path: str, workspace_root: Path | None = None) -> None:
        self.cli_path = cli_path
        self.workspace_root = workspace_root or Path.cwd().resolve()
        self._proc: subprocess.Popen[str] | None = None
        self._req_id = 0

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> bool:
        if self.is_alive():
            return True
        if not (Path(self.cli_path).exists() or shutil.which(self.cli_path)):
            return False
        root_str = str(self.workspace_root)
        cmd = [
            self.cli_path,
            "serve",
            "--automation-read-root",
            root_str,
            "--automation-write-root",
            root_str,
        ]
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            return True
        except Exception as e:
            _logger.debug(f"Could not start photocraft-cli serve: {e}")
            self._proc = None
            return False

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if not self.start() or self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            return None
        self._req_id += 1
        payload = {
            "id": self._req_id,
            "method": method,
            "params": params or {},
        }
        try:
            self._proc.stdin.write(json.dumps(payload) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if not line:
                return None
            resp = json.loads(line)
            if not resp.get("ok"):
                _logger.debug(f"Photocraft RPC ({method}) returned error: {resp.get('error')}")
            return resp
        except Exception as e:
            _logger.debug(f"Photocraft RPC request failed ({method}): {e}")
            return None

    def close(self) -> None:
        if self._proc is not None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None


class PhotocraftHandler(Application):
    """Photocraft backend handler replacing Adobe Photoshop COM automation."""

    _initialized: bool = False

    def __init__(self, cli_path: str | None = None, version: str | None = None) -> None:
        if getattr(self, "_initialized", False):
            return
        super().__init__(version=version)
        self.cli_path = cli_path or find_photocraft_cli()
        self.workspace_root = Path(__file__).resolve().parents[2]
        self._rpc = PhotocraftRpcServer(self.cli_path, self.workspace_root)
        self._initialized = True
        _logger.info(f"Initialized PhotocraftHandler with CLI: {self.cli_path}")

    def has_cli_binary(self) -> bool:
        return bool(Path(self.cli_path).exists() or shutil.which(self.cli_path))

    def run_command(self, args: list[str]) -> str:
        cmd = [self.cli_path, *args]
        _logger.debug(f"Running Photocraft command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            _logger.error(f"Photocraft command failed: {e.stderr}")
            raise OSError(f"Photocraft error: {e.stderr}") from e
        except FileNotFoundError as e:
            _logger.error(f"Photocraft CLI executable not found at {self.cli_path}")
            raise OSError(f"Photocraft CLI not found: {self.cli_path}") from e

    def check_connection(self) -> bool:
        """Verify that Photocraft backend (CLI or headless Python engine) is operational."""
        if self.has_cli_binary():
            try:
                out = self.run_command(["commands", "--json"])
                return bool(out)
            except Exception:
                return False
        return True

    def inspect_document(self, input_path: str | Path, compact: bool = True) -> dict[str, Any]:
        """Inspect a document via `photocraft-cli info <file>` or headless fallback."""
        path = Path(input_path)
        if self.has_cli_binary() and path.exists():
            args = ["info", str(path)]
            if compact:
                args.append("--compact")
            out = self.run_command(args)
            return json.loads(out)
        doc = self.load(path)
        return {
            "name": doc.name,
            "width": doc.width,
            "height": doc.height,
            "resolution": doc.resolution,
            "layers": [layer.name for layer in doc.artLayers],
            "groups": [grp.name for grp in doc.layerSets],
        }

    def export_document(
        self, input_path: str | Path, output_path: str | Path, format: str = "png"
    ) -> str:
        """Convert/export a document using `photocraft-cli convert <in> <out> --format <ext>` or fallback."""
        in_p = Path(input_path)
        out_p = Path(output_path)
        if self.has_cli_binary() and in_p.exists():
            return self.run_command(
                ["convert", str(in_p), str(out_p), "--format", format]
            )
        doc = self.load(in_p)
        doc.saveAs(str(out_p))
        return str(out_p)

    # --- Internal RPC hooks called by Document / ArtLayer / Application ---

    def _stage_input_rel_path(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(self.workspace_root).as_posix()
        except ValueError:
            tmp_dir = self.workspace_root / "tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            staged = tmp_dir / resolved.name
            if resolved != staged:
                shutil.copy2(resolved, staged)
            return staged.relative_to(self.workspace_root).as_posix()

    def photocraft_open(self, path: Path) -> dict[str, Any] | None:
        if not self.has_cli_binary():
            return None
        # Close any previously open documents in the session
        sess = self._rpc.request("session.list", {})
        if sess and sess.get("ok") and isinstance(sess.get("result"), dict):
            docs = sess["result"].get("documents", [])
            for _ in range(len(docs)):
                self._rpc.request("doc.close", {})
        rel = self._stage_input_rel_path(path)
        resp = self._rpc.request("doc.open", {"path": rel})
        if resp and resp.get("ok"):
            insp = self._rpc.request("doc.inspect", {})
            if insp and insp.get("ok") and isinstance(insp.get("result"), dict):
                return insp["result"]
        return None

    def photocraft_new(self, width: int, height: int) -> bool:
        if not self.has_cli_binary():
            return False
        resp = self._rpc.request(
            "doc.new",
            {"width": width, "height": height, "mode": "rgb", "depth": 8, "background": "white"},
        )
        return bool(resp and resp.get("ok"))

    def photocraft_place(self, path: Path) -> dict[str, Any] | None:
        if not self.has_cli_binary() or not path.exists():
            return None
        rel = self._stage_input_rel_path(path)
        resp = self._rpc.request("doc.place", {"path": rel, "fit": False})
        if resp and resp.get("ok") and isinstance(resp.get("result"), dict):
            return resp["result"]
        return None

    def photocraft_save(self, out_path: Path, src_path: Path | None = None) -> bool:
        if not self.has_cli_binary():
            return False
        resolved_out = out_path.resolve()
        resolved_out.parent.mkdir(parents=True, exist_ok=True)
        try:
            rel_out = resolved_out.relative_to(self.workspace_root).as_posix()
            resp = self._rpc.request("doc.save", {"path": rel_out})
            if resp and resp.get("ok") and resolved_out.exists():
                return True
        except ValueError:
            tmp_dir = self.workspace_root / "tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            staged_out = tmp_dir / resolved_out.name
            rel_out = staged_out.relative_to(self.workspace_root).as_posix()
            resp = self._rpc.request("doc.save", {"path": rel_out})
            if resp and resp.get("ok") and staged_out.exists():
                shutil.move(str(staged_out), str(resolved_out))
                return True
        return False

    def photocraft_close(self, doc: Any = None) -> None:
        if self.has_cli_binary() and self._rpc.is_alive():
            self._rpc.request("doc.close", {})

    def photocraft_execute(self, command: str, params: dict[str, Any]) -> Any:
        if not self.has_cli_binary():
            return None
        resp = self._rpc.request("engine.execute", {"command": command, "params": params})
        if resp and resp.get("ok"):
            return resp.get("result")
        return None
