r"""비교 페이지 (tools/compare_page.py, 2026-10-15).

가짜 실행 폴더 하나 - 원본 HTML 을 그대로 최종 빌드로, 원본 흐름을 그대로 흐름 명세로, 원본 화면설계서를
그대로 화면설계서로 둔 실행 (원칙 ga, applied 있음) - 로 페이지를 만든다.

  기본       걷기를 가짜로 바꿔 끼운다 (그림은 작은 PNG). 페이지가 만들어지는지, 깨진 그림 0, 요약표
             칸이 다 차는지, 원칙 적용표 · 바꾼 것, 없는 실행은 그 열에 이유를 적고 계속하는지,
             결과 폴더는 읽기만 하는지
  browser    실제로 걷는다. 같은 빌드이므로 실행 열의 숫자가 원본 열과 같아야 한다

  .\.venv\Scripts\python.exe -m pytest tests/test_compare_page.py
  .\.venv\Scripts\python.exe -m pytest tests/test_compare_page.py -m browser
"""
import hashlib
import io
import json
import os
import re
import shutil
import sys

import pytest

import _api

ROOT = _api.ROOT_DIR
sys.path.insert(0, os.path.join(ROOT, "tools"))
import compare_page as CP  # noqa: E402

T = _api.tasks_module
PR = _api.principles_module
# 가장 작은 PNG (1x1 투명)
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


@pytest.fixture
def work(request):
    d = os.path.join(ROOT, ".pytest-outputs", "compare-" + request.node.name[:40])
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def fake_run(work):
    """원본 그대로인 통과한 실행 폴더."""
    d = os.path.join(work, "20261015-000000")
    os.makedirs(os.path.join(d, "storyboard"))
    task = T.load_task("transfer")
    shutil.copy2(T.abs_path(task["original"]), os.path.join(d, "attempt_1.html"))
    shutil.copy2(T.abs_path(task["flow"]), os.path.join(d, "attempt_1.flow.json"))
    shutil.copy2(CP.CR.REFERENCE["transfer"], os.path.join(d, "storyboard", "storyboard.json"))
    screens = CP.FF.first_visits(CP.FF.original_steps("transfer"))
    plan = {"screens": [{"name": s, "purpose": "원본 그대로", "from": [s],
                         "applied": [{"id": "S02", "how": "%s 의 홍보 카드를 접었다" % s}]}
                        for s in screens],
            "changes": [{"id": "C1", "what": "바꾸지 않는다", "why": "시험", "addresses": [],
                         "from_screens": ["home"], "to_screens": ["home"]}]}
    io.open(os.path.join(d, "attempt_1.plan.json"), "w", encoding="utf-8").write(
        json.dumps(plan, ensure_ascii=False))
    audit = {"passed": True, "fatal": [], "warning": [],
             "metrics": {"entrances_kept": 31, "entrances_original": 31, "images_kept": 60,
                         "images_original": 60, "choice_groups_original": {"pick-bank": 67},
                         "choice_values_selectable": {"pick-bank": 67},
                         "error_paths": {"wrong-account": {"appeared": True, "recovered": True}},
                         "flow_fixed": {"same": True}}}
    io.open(os.path.join(d, "attempt_1.audit.json"), "w", encoding="utf-8").write(json.dumps(audit))
    rec = PR.record(PR.load("ga"))
    summary = {"run_dir": d, "task": "transfer", "passed": True, "mode": "layout", "mock": None,
               "model": "gpt-6.1-sol", "stage": "wireframe",
               "final": {"attempt": 1, "html": "x/attempt_1.html", "flow": "x/attempt_1.flow.json"},
               "attempts": [{"n": 1}], "git": {"commit": "abcdef1234567", "dirty": False},
               "see": {"source": "captures"}, "refine": {"budget": 0},
               "cost": {"total_usd": 0.5}, "principles": rec,
               "original_sha256": T.original_sha256("transfer"),
               "repro": {"prompt_template_sha256": "0" * 64}}
    io.open(os.path.join(d, "summary.json"), "w", encoding="utf-8").write(
        json.dumps(summary, ensure_ascii=False))
    return d


def fake_walker(cols, screens, out):
    res = {}
    for col in cols:
        res[col["key"]] = got = {}
        if col.get("error"):
            continue
        for i, s in enumerate(screens):
            f = "%s_%s.png" % (col["key"], s)
            io.open(os.path.join(out, f), "wb").write(PNG)
            got[s] = {"screen": s, "built": s, "height": 844 + i, "file": f,
                      "first_viewport_pressables": 5, "first_list": [], "pressables": 7,
                      "min_target": {"h": 48, "w": 100, "text": "다음", "action": "next"},
                      "under44": 0, "min_font": {"px": 16, "text": "글"}, "text_elems": 9,
                      "under16": 0, "min_contrast": {"ratio": 7.1, "text": "글", "px": 16}}
    return res


def tree_digest(d):
    h = hashlib.sha256()
    for base, _dirs, files in sorted(os.walk(d)):
        for f in sorted(files):
            p = os.path.join(base, f)
            h.update(p.encode("utf-8"))
            h.update(open(p, "rb").read())
    return h.hexdigest()


def summary_table(page):
    body = page.split('<h2 id="summary">', 1)[1].split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    rows = re.findall(r"<tr><th>(.*?)</th>(.*?)</tr>", body)
    return {k: re.findall(r"<td>(.*?)</td>", v) for k, v in rows}


def broken_images(out, page):
    return [src for src in re.findall(r'<img src="([^"]+)"', page)
            if not os.path.exists(os.path.join(out, src))]


def test_a_page_from_a_fake_run(work):
    run = fake_run(work)
    before = tree_digest(run)
    path = CP.build([run], "t", out_root=os.path.join(work, "out"), walker=fake_walker)
    out = os.path.dirname(path)
    page = io.open(path, encoding="utf-8").read()
    assert broken_images(out, page) == []
    # 원본 칸의 더미앱 캡처 (home 은 스크롤 조각 셋)
    assert all('src="cap_%s"' % f in page for f in ("01a.png", "01b.png", "01c.png", "09a.png"))
    table = summary_table(page)
    assert list(table) == CP.SUMMARY_ROWS
    for k, cells in table.items():
        assert len(cells) == 2, k
        assert all(c.strip() and "잴 수 없음" not in c and "?" not in c for c in cells), (k, cells)
    assert table["조건"][1] == "ga · 커밋 abcdef1 · 모드 layout · 캡처"
    # 원본을 그대로 둔 실행 - 원본 닮음은 1, 격자 · 탭은 원본과 같다
    assert table["원본 닮음 (요소 · 무리, 화면 평균 · 최저)"][1] == "요소 1.00 · 1.00 / 무리 1.00 · 1.00"
    assert table["격자 · 탭 (원본에도 · 새로 · 없어짐)"][0] == \
        table["격자 · 탭 (원본에도 · 새로 · 없어짐)"][1]
    assert table["검사 결과"][1] == "fatal 0 ✓ · K 31/31 · L 60/60 · I 67/67 · J 1/1 · M 같다"
    assert table["시도 수 · 금액"][1] == "1 · $0.50"
    # 원칙 적용표 · 바꾼 것
    assert "home 의 홍보 카드를 접었다" in page and "prompts/principles/ga.json" in page
    assert "<td>home</td><td>C1</td><td>바꾸지 않는다</td>" in page
    # 재는 규칙 · 조건 · sha
    assert "재는 규칙" in page and PR.record(PR.load("ga"))["sha256"] in page
    # 결과 폴더는 읽기만 한다
    assert tree_digest(run) == before
    data = json.load(io.open(os.path.join(out, "metrics.json"), encoding="utf-8"))
    assert data["screens"][0] == "home" and len(data["screens"]) == 8


def test_a_missing_run_is_noted_in_its_column(work):
    run = fake_run(work)
    path = CP.build([run, "no-such-run"], "t", out_root=os.path.join(work, "out"),
                    walker=fake_walker)
    page = io.open(path, encoding="utf-8").read()
    assert broken_images(os.path.dirname(path), page) == []
    assert "실행 폴더가 없다" in page
    table = summary_table(page)
    assert all(len(c) == 3 for c in table.values())
    assert table["조건"][2].startswith("읽지 못함")


def test_a_run_without_principles_says_so(work):
    run = fake_run(work)
    s = json.load(io.open(os.path.join(run, "summary.json"), encoding="utf-8"))
    del s["principles"]
    io.open(os.path.join(run, "summary.json"), "w", encoding="utf-8").write(json.dumps(s))
    path = CP.build([run], "t", out_root=os.path.join(work, "out"), walker=fake_walker)
    page = io.open(path, encoding="utf-8").read()
    assert "<p>원칙 없음</p>" in page
    assert summary_table(page)["조건"][1].startswith("none · ")


@pytest.mark.browser
def test_walking_the_original_as_a_run_gives_the_original_numbers(work):
    run = fake_run(work)
    path = CP.build([run], "t", out_root=os.path.join(work, "out"))
    out = os.path.dirname(path)
    page = io.open(path, encoding="utf-8").read()
    assert broken_images(out, page) == []
    m = json.load(io.open(os.path.join(out, "metrics.json"), encoding="utf-8"))["metrics"]
    for screen, o in m["orig"].items():
        r = m["r1"][screen]
        assert "error" not in o and "error" not in r, screen
        for k in ("height", "pressables", "first_viewport_pressables", "text_elems",
                  "min_font", "min_target", "min_contrast"):
            assert o[k] == r[k], (screen, k)
    # 10/13 점검 (outputs/review-1013) 과 같은 원본 숫자 - 높이는 화면이 창에 들 때 844
    assert m["orig"]["home"]["height"] == 1648 and m["orig"]["done"]["height"] == 844
    assert m["orig"]["home"]["first_viewport_pressables"] == 17
    table = summary_table(page)
    assert table["home 높이 · 화면 높이 합 (px)"] == ["1648 · 8194", "1648 · 8194"]
