import os, sys
from pathlib import Path
import subprocess
from typing import Tuple, Optional, List

# ---- 内部状態（--format 対応可否をキャッシュ）----
_FORMAT_SUPPORTED: Optional[bool] = None

def _detect_format_flag(repo_root: Path) -> bool:
    """
    `python -m scripts.ask --help` の出力から `--format` の有無を検出。
    一度検出したらモジュール内でキャッシュする。
    """
    global _FORMAT_SUPPORTED
    if _FORMAT_SUPPORTED is not None:
        return _FORMAT_SUPPORTED

    env = os.environ.copy()
    # 念のため PYTHONPATH にリポジトリルートを追加
    env["PYTHONPATH"] = (
        str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
        if env.get("PYTHONPATH") else str(repo_root)
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "scripts.ask", "--help"],
            cwd=str(repo_root),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=15,
        )
        help_text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        _FORMAT_SUPPORTED = ("--format" in help_text)
    except Exception:
        _FORMAT_SUPPORTED = False
    return _FORMAT_SUPPORTED


def _run_ask(
    query: str,
    storage: str = "storage",
    k: int = 4,
    llm_backend: str = "openai",      # 'openai' | 'internlm2' | 'none'
    llm_model: Optional[str] = "gpt-5-mini",
    rerank: bool = True,
    fmt: Optional[str] = None,        # 'concise' | 'full' | None（None は未指定）
    timeout: int = 120
) -> Tuple[str, str, int]:
    """
    子プロセスを .venv の Python（sys.executable）で起動し、
    作業ディレクトリをリポジトリルートに固定して `scripts.ask` を実行する。
    - fmt が指定されていても、ask.py が --format 非対応なら無視する。
    """
    repo_root = Path(__file__).resolve().parents[1]

    cmd: List[str] = [
        sys.executable, "-m", "scripts.ask",
        "--storage", storage,
        "--k", str(k),
        "--llm-backend", llm_backend,
        "--q", query,
    ]
    # --format は対応している時だけ付与
    if fmt and _detect_format_flag(repo_root):
        cmd += ["--format", fmt]

    if llm_backend != "none" and llm_model:
        cmd += ["--llm-model", llm_model]
    if not rerank:
        cmd.append("--no-rerank")

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
        if env.get("PYTHONPATH") else str(repo_root)
    )

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.stdout.strip(), proc.stderr.strip(), proc.returncode


def ask_with_evidence(
    query: str,
    storage: str = "storage",
    k: int = 4,
    llm_backend: str = "openai",
    llm_model: Optional[str] = "gpt-5-mini",
    rerank: bool = True,
) -> Tuple[str, str]:
    """
    可能なら 2 回呼び出し：
      1) concise：簡潔な「回答」
      2) full   ：「根拠断片（ソース）」一覧
    ただし ask.py が --format 非対応なら 1 回のみ呼び出し、回答をそのまま返す（証拠は空）。
    """
    repo_root = Path(__file__).resolve().parents[1]
    if _detect_format_flag(repo_root):
        answer, err1, rc1 = _run_ask(
            query, storage, k, llm_backend, llm_model, rerank, fmt="concise"
        )
        evidence, err2, rc2 = _run_ask(
            query, storage, k, llm_backend, llm_model, rerank, fmt="full"
        )
        merged_err = "\n".join(x for x in [err1, err2] if x)
        if merged_err:
            evidence = (evidence + "\n\n[stderr]\n" + merged_err).strip()
        return answer, evidence
    else:
        # 非対応：一回だけ実行。stderr は evidence として畳み込んで見えるようにする。
        answer, err, rc = _run_ask(
            query, storage, k, llm_backend, llm_model, rerank, fmt=None
        )
        evidence = ""
        if err:
            evidence = "[stderr]\n" + err
        return answer, evidence
