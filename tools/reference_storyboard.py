r"""원본 HTML 자체를 빌드로 둔 화면설계서 - Figma 확인용 참고 자료 (2026-10-12).

재구성 실행이 아니다. 과제의 원본 HTML 을 그대로 "빌드" 로, 원본 흐름을 그대로 흐름 명세로 둔
실행 폴더를 잠깐 만들어, 검사기를 루프와 같은 길(audit_call.run_audit)로 한 번 돌리고(원본 대
원본이라 통과한다) 화면설계서를 만든다. 영역 묶기는 --mock (정해진 답 - 모델을 부르지 않는다),
PDF 는 만들지 않는다. 끝나면 storyboard/ 만 남기고 나머지(빌드 사본 · 흐름 · 검사 · summary)는
지운다 - 원본은 inputs/ 에 있다.

    python tools/reference_storyboard.py --task transfer --out results/reference/original-transfer

그림 자리(storyboard.json 의 sheets[].images, schema 3)가 원본에서 어디에 어떤 크기로 있는지를
Figma 플러그인으로 그려 볼 때 쓴다. 그림은 재현 HTML 을 찍은 것이다.
"""
import argparse
import asyncio
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from senior_ui import config                                   # noqa: E402
from senior_ui import tasks as T                               # noqa: E402
from senior_ui.audit import drive, load_flow                   # noqa: E402
from senior_ui.devserver import ensure_server                  # noqa: E402
from senior_ui.restructure import audit_call                   # noqa: E402
from senior_ui.storyboard.__main__ import main as storyboard   # noqa: E402

KEEP = "storyboard"


def _write(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=2))


def make_run(task, out, base):
    """원본을 빌드로 둔 실행 폴더를 out 에 만든다. 검사가 통과하지 않으면 멈춘다."""
    t = T.load_task(task)
    orig_rel = t["original"]
    html = io.open(T.abs_path(orig_rel), encoding="utf-8").read()
    flow = json.load(io.open(T.abs_path(t["flow"]), encoding="utf-8"))
    flow["name"] = "auto"
    p = lambda f: os.path.join(out, f)
    _write(p("attempt_1.html"), html)
    _write(p("attempt_1.flow.json"), flow)
    orig_url = "%s/%s" % (base, orig_rel)
    snap = asyncio.run(drive(orig_url, load_flow(None, task=task), errors=False))
    rel = os.path.relpath(p("attempt_1.html"), ROOT).replace(os.sep, "/")
    report = audit_call.run_audit(snap, html, p("attempt_1.html"), p("attempt_1.flow.json"),
                                  "%s/%s" % (base, rel), None, "wireframe",
                                  original_url=orig_url, task=task)
    _write(p("attempt_1.audit.json"), report)
    if not report.get("passed"):
        raise SystemExit("원본 대 원본 검사가 통과하지 않았다: %s"
                         % [f.get("check") for f in report.get("fatal") or []])
    _write(p("summary.json"), {
        "run_dir": out, "model": "original", "model_source": "reference", "mock": None,
        "task": task, "stage": "wireframe",
        "attempts": [{"n": 1, "stage": "audit", "passed": True, "problems": []}],
        "passed": True, "stopped_reason": None,
        "final": {"attempt": 1, "html": p("attempt_1.html"), "flow": p("attempt_1.flow.json"),
                  "audit": p("attempt_1.audit.json"), "plan": None, "diagnosis": None,
                  "model_html": p("attempt_1.html")},
        "git": {"commit": None, "branch": None, "dirty": None, "dirty_files": []},
        "refine": {"final_from": "generate", "final_label": "원본 (%s)" % orig_rel},
        "cost": None})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--task", default="transfer")
    ap.add_argument("--out", required=True, help="저장소 안의 폴더 (storyboard/ 가 여기에 남는다)")
    args = ap.parse_args(argv)
    out = os.path.abspath(args.out)
    if not config.inside_root(out):
        raise SystemExit("저장소 밖이다: %s" % out)
    os.makedirs(out, exist_ok=True)
    lines = []
    proc = ensure_server(lines.append, port=config.AUTO_PORT)
    try:
        make_run(args.task, out, config.base_url(getattr(proc, "port", None) or config.PORT))
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait()
    code = storyboard([out, "--mock", "--no-pdf"])
    for name in os.listdir(out):
        if name != KEEP and name.lower() != "readme.md":
            path = os.path.join(out, name)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    return code


if __name__ == "__main__":
    sys.exit(main())
