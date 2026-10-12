r"""캡처 대응표의 빈 틀 (python -m senior_ui.restructure.captures_template, 2026-10-12).

폴더의 PNG 를 이름순으로 나열하고 label 이 빈 (taps 는 빈 배열인) captures.json 을 만든다.
참고용으로 렌더 그림의 이름표를 보인다. label 과 taps 를 짐작해 채우지 않고, 있으면 덮어쓰지 않는다.

  .\.venv\Scripts\python.exe -m pytest tests/test_captures_template.py
"""
import io
import json
import os

import pytest

import _api
from test_visual_refine import make_png

CAP = _api.captures_module
TEMPLATE_CMD = _api.captures_template_module


# ===================================================================== #
# 빈 틀 만들기
# ===================================================================== #
def test_the_template_lists_pngs_and_guesses_nothing(tmp_path, capsys):
    d = tmp_path / "caps"
    for f in ("02.png", "01b.png", "01a.png"):
        make_png(os.path.join(str(d), f), 10, 10)
    io.open(os.path.join(str(d), "note.txt"), "w").write("x")
    plan_prompt = tmp_path / "plan_prompt.txt"
    plan_prompt.write_text("앞\n[그림 1/2] 원본 화면 home  <그림: a.png 390x844 · 예상 1토큰>\n"
                           "[그림 2/2] 원본 오류 상태 x — 잘못된 값을 넣은 직후  <그림: b.png>\n",
                           encoding="utf-8")
    code = TEMPLATE_CMD.main([str(d), "--task", "transfer", "--labels-from", str(plan_prompt)])
    assert code == 0
    data = json.load(io.open(os.path.join(str(d), "captures.json"), encoding="utf-8"))
    assert data == {"task": "transfer", "source": "",
                    "images": [{"file": f, "label": "", "taps": []}
                               for f in ("01a.png", "01b.png", "02.png")]}
    out = capsys.readouterr().out
    assert "[그림 1/2] 원본 화면 home" in out and "[그림 2/2] 원본 오류 상태 x" in out
    # 빈 label 그대로는 실행에 쓸 수 없다 - 연구자가 채운다
    with pytest.raises(CAP.CapturesError):
        CAP.load(os.path.join(str(d), "captures.json"), "transfer")
    # 있으면 덮어쓰지 않는다
    assert TEMPLATE_CMD.main([str(d), "--task", "transfer",
                              "--labels-from", str(plan_prompt)]) == 1


def test_the_template_dry_run_writes_nothing(tmp_path):
    d = tmp_path / "caps"
    make_png(os.path.join(str(d), "01.png"), 10, 10)
    assert TEMPLATE_CMD.main([str(d), "--task", "transfer", "--dry-run"]) == 0
    assert not os.path.exists(os.path.join(str(d), "captures.json"))
