from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
REPORT = ROOT / "reports" / "final-test-report.md"


@dataclass
class Check:
    name: str
    command: str
    input_text: str
    output: str
    exit_code: int

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def run_command(name: str, command: list[str], cwd: Path) -> Check:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    return Check(
        name=name,
        command=" ".join(command),
        input_text=f"cwd={cwd}",
        output=output or "(no output)",
        exit_code=completed.returncode,
    )


def run_http_check(name: str, url: str, validator) -> Check:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.status
        validator(status, body)
        output = f"HTTP {status}\n{body[:2000]}"
        return Check(name, f"GET {url}", url, output, 0)
    except Exception as exc:  # noqa: BLE001
        return Check(name, f"GET {url}", url, f"{type(exc).__name__}: {exc}", 1)


def assert_health(status: int, body: str) -> None:
    if status != 200:
        raise AssertionError(f"expected HTTP 200, got {status}")
    payload = json.loads(body)
    if not payload.get("request_id"):
        raise AssertionError("health response has no request_id")


def assert_compare(status: int, body: str) -> None:
    if status != 200:
        raise AssertionError(f"expected HTTP 200, got {status}")
    required = ['name="left"', 'name="right"', "打开页面时不会自动加载任何公司"]
    for marker in required:
        if marker not in body:
            raise AssertionError(f"compare page missing marker: {marker}")
    if 'value="NVDA"' in body or 'value="AMD"' in body:
        raise AssertionError("compare page still contains default ticker values")


def assert_sec_ask(status: int, body: str) -> None:
    if status != 200:
        raise AssertionError(f"expected HTTP 200, got {status}")
    if body.count("<textarea") != 1:
        raise AssertionError("SEC ask page must contain exactly one textarea")
    if 'id="sec-ticker"' in body:
        raise AssertionError("SEC ask page still contains a separate ticker input")
    for marker in ("研究标的和问题", "同一个问题框"):
        if marker not in body:
            raise AssertionError(f"SEC ask page missing marker: {marker}")


def render_report(checks: list[Check], started_at: str) -> str:
    passed = sum(check.passed for check in checks)
    lines = [
        "# 最终测试 Agent 报告",
        "",
        f"- 执行时间：{started_at}",
        f"- 工作目录：{ROOT}",
        f"- 结果：**{passed}/{len(checks)} 通过**",
        "- 测试范围：后端 pytest/Ruff/mypy、前端 lint/typecheck/build、本地 Backend/Frontend 页面冒烟检查。",
        "- 外部 API：未调用；页面检查仅访问本机 127.0.0.1 服务。",
        "",
        "## 检查明细",
        "",
    ]
    for check in checks:
        result = "PASS" if check.passed else "FAIL"
        lines.extend(
            [
                f"### {result} · {check.name}",
                "",
                f"- 命令：{check.command}",
                f"- 输入：{check.input_text}",
                f"- 退出状态：{check.exit_code}",
                "- 字面输出：",
                "TEXT",
                check.output[:8000],
                "TEXT",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run final local quality and UI smoke checks.")
    parser.add_argument("--smoke-only", action="store_true", help="Only run local HTTP smoke checks.")
    parser.add_argument("--quality-only", action="store_true", help="Run only quality commands.")
    parser.add_argument("--append", action="store_true", help="Append this run to the existing report.")
    args = parser.parse_args()

    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    checks: list[Check] = []

    if not args.smoke_only:
        checks.extend(
            [
                run_command(
                    "Backend pytest",
                    [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "pytest", "-q"],
                    BACKEND,
                ),
                run_command(
                    "Backend Ruff",
                    [str(ROOT / ".venv" / "Scripts" / "ruff.exe"), "check", "app", "tests"],
                    BACKEND,
                ),
                run_command(
                    "Backend mypy",
                    [str(ROOT / ".venv" / "Scripts" / "mypy.exe"), "app"],
                    BACKEND,
                ),
                run_command("Frontend lint", ["npm.cmd", "run", "lint"], FRONTEND),
                run_command("Frontend typecheck", ["npm.cmd", "run", "typecheck"], FRONTEND),
                run_command("Frontend build", ["npm.cmd", "run", "build"], FRONTEND),
            ]
        )

    if not args.quality_only:
        checks.extend(
            [
                run_http_check("Backend health", "http://127.0.0.1:8000/health", assert_health),
                run_http_check("Compare initial form", "http://127.0.0.1:3000/compare", assert_compare),
                run_http_check("SEC ask single prompt", "http://127.0.0.1:3000/sec-ask", assert_sec_ask),
            ]
        )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_report(checks, started_at)
    if args.append and REPORT.exists():
        rendered = REPORT.read_text(encoding="utf-8") + "\n\n---\n\n" + rendered
    REPORT.write_text(rendered, encoding="utf-8")
    print(f"Report: {REPORT}")
    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL'} {check.name} (exit {check.exit_code})")
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
