r"""그림 자리 보존 (검사 L) - 연구자 결정 2026-10-12.

원본의 로고 · 아이콘 자리(role="img" + aria-label "<무엇> 로고/아이콘", 회색 상자 pic -
test_image_slots.py)는 "이 위치에 이 크기로 이런 그림이 들어간다" 는 설계 정보다. 실행
20261008-131136 (시도 2) · 20261012-132226 (시도 1) 은 그것을 모두 지웠다 (role="img" 0개,
은행 로고 67개도). 판정 규칙:

  - 원본을 걷는 동안 (정답 경로 · reveal) 그려져 보인 그림 자리의 이름 집합 O, 생성물을
    같은 방식으로 걸으며 보인 이름 집합 B. 누를 수 있든 없든 센다
  - O 에 있고 B 에 없으면 지운 것 - fatal (와이어프레임 · 스타일 두 단계 모두)
  - B 에만 있으면 새 그림 자리 - 기록만 (images_new). 원본 문서에는 있지만 원본을 걷는
    동안 보이지 않은 것([증권사] 탭)도 기록만 (images_not_in_original)
  - 크기 · 위치는 판정하지 않고 생성 쪽에서 처음 보인 상자를 기록만 한다 (images_box)

손으로 만든 스냅샷으로 판정만 본다 (1절). 프롬프트의 두 줄 (2절), mock (3절), 실제로 걷는 것은
4절(-m browser)이다.

  .\.venv\Scripts\python.exe -m pytest tests/test_images_kept.py
  .\.venv\Scripts\python.exe -m pytest -m browser tests/test_images_kept.py
"""
import asyncio
import copy
import io
import json
import os

import pytest

import _api
from test_audit_bugs import done_row, flow, row, snap

ROOT = _api.ROOT_DIR
L = _api.l_images_module


# ===================================================================== #
# 1. 판정 (손으로 만든 스냅샷)
# ===================================================================== #
NAMES = ["메시지 아이콘", "신한은행 로고", "카메라 아이콘", "국민 로고"]


def images(names=NAMES, hidden=(), visit="start", box=(10, 20, 32, 32)):
    """`{이름: {visible, box, visit, reveal}}` - drive 가 남기는 모양."""
    return {n: ({"visible": True, "box": list(box), "visit": visit, "reveal": 0}
                if n not in hidden else {"visible": False, "box": None})
            for n in names}


def judge(rep_images, orig_images=None, revealed=None, stage=None):
    f = flow(["start", "done"])
    orig = snap({"start": row("start"), "done": done_row()},
                images_seen=images() if orig_images is None else orig_images)
    rep = snap({"start": row("start"), "done": done_row()}, images_seen=rep_images)
    if revealed is not None:
        rep["revealed"] = revealed
    report = _api.audit(orig, rep, "<html></html>", "<html></html>", f)
    return _api.apply_stage(report, stage) if stage else report


def l_fatals(report):
    return [x for x in report["fatal"] if x.get("check") == "L"]


def test_a_build_without_the_image_slots_fails():
    report = judge({})
    ls = l_fatals(report)
    assert report["passed"] is False and len(ls) == 1, report["fatal"]
    m = report["metrics"]
    assert (m["images_original"], m["images_kept"]) == (4, 0)
    assert ls[0]["missing"] == m["images_missing"] == NAMES       # 원본에서 본 순서
    # 실패 안내문은 지운 이름을 나열하고 기술 계약의 문장을 그대로 담는다
    assert "메시지 아이콘, 신한은행 로고, 카메라 아이콘, 국민 로고" in ls[0]["detail"]
    assert L.RULE in ls[0]["detail"]


def test_a_build_that_keeps_every_slot_passes_wherever_they_are():
    """위치 · 크기 · 화면은 바뀌어도 된다 - 이름이 걷는 동안 보이면 있다."""
    report = judge(images(visit="done", box=(0, 600, 48, 48)))
    assert l_fatals(report) == [] and report["metrics"]["images_kept"] == 4
    assert report["metrics"]["images_box"]["국민 로고"] == {"box": [0, 600, 48, 48],
                                                           "screen": "done"}


def test_one_missing_slot_is_named():
    report = judge(images(names=NAMES[:3]))
    assert report["metrics"]["images_missing"] == ["국민 로고"]
    assert "1개" in l_fatals(report)[0]["detail"]


def test_a_slot_that_is_never_visible_in_the_build_is_missing():
    report = judge(images(hidden=("카메라 아이콘",)))
    assert report["metrics"]["images_missing"] == ["카메라 아이콘"]


def test_a_slot_shown_after_a_reveal_counts():
    report = judge(images(hidden=NAMES),
                   revealed={"pick-bank": {"at": "start", "choices": {},
                                           "images_seen": images(visit="start")}})
    assert l_fatals(report) == [], report["fatal"]


def test_new_slots_are_recorded_not_judged():
    report = judge(images(names=NAMES + ["돋보기 그림"]))
    assert l_fatals(report) == []
    assert report["metrics"]["images_new"] == ["돋보기 그림"]


def test_a_slot_the_original_does_not_show_is_not_counted():
    """[증권사] 탭의 로고처럼 원본 문서에는 있지만 원본을 걷는 동안 보이지 않은 것."""
    report = judge(images(names=NAMES[:3]),
                   orig_images=images(hidden=("국민 로고",)))
    m = report["metrics"]
    assert l_fatals(report) == [] and m["images_original"] == 3
    assert m["images_not_in_original"] == ["국민 로고"]


def test_a_snapshot_from_before_the_collection_stands_down():
    f = flow(["start", "done"])
    s = snap({"start": row("start"), "done": done_row()})
    report = _api.audit(s, copy.deepcopy(s), "<html></html>", "<html></html>", f)
    assert l_fatals(report) == []
    assert any(x.startswith("L/") for x in report["metrics"]["checks_stood_down"])


@pytest.mark.parametrize("stage", ["wireframe", "styled"])
def test_L_is_judged_at_both_stages(stage):
    assert "L" in _api.audit_stage_module.STAGES[stage]["checks"]
    assert len(l_fatals(judge({}, stage=stage))) == 1


def test_the_stuck_key_counts_the_missing_names():
    """같은 실패의 되풀이(막힘)는 (검사 · 대상 · 개수) 로 본다 - missing 이 있어야 센다."""
    f = l_fatals(judge(images(names=NAMES[:1])))[0]
    assert f["missing"] == NAMES[1:]


# ===================================================================== #
# 2. 프롬프트 - 기술 계약 한 줄과 세 프롬프트의 한 줄
# ===================================================================== #
CONTRACT_LINE = ("원본의 그림 자리 (role=\"img\" 와 aria-label 을 가진 요소 — 로고 · 아이콘 · "
                 "사진이 들어갈 자리) 는 지우지 마라. aria-label 은 원본 그대로 둔다. 위치 · 크기 · "
                 "묶음은 바꿔도 된다. 그림 자리는 CSS 로 크기를 준 상자로 그린다 (그림 파일 · 외부 "
                 "자원 · 이모지 · 글자로 흉내 내지 않는다). 이름 글을 곁에 더하는 것은 자유다. 새 "
                 "그림이 필요하면 같은 형식 (role=\"img\" + aria-label \"<무엇> 아이콘/로고/그림\") "
                 "으로 더해도 된다. 선택지마다 붙은 그림 자리 (은행 로고 등) 는 그 선택지마다 둔다.")
PIC_LINE = ("원본의 그림 자리 (로고 · 아이콘) 는 그림이 들어갈 자리를 뜻하는 설계 정보다. "
            "장식으로 보고 지우지 마라 — 위치 · 크기는 바꿔도 된다.")
MENU = "다만 없애지 마라."


@pytest.mark.parametrize("task", ["transfer", "bill"])
def test_the_prompts_carry_the_contract_line_and_the_menu_line(task):
    p = _api.prompt_module
    for t in (p.load_plan_template(task), p.load_template(task),
              p.load_refine_template(task)):
        flat = " ".join(t.split())
        assert flat.count(PIC_LINE) == 1
        # 메뉴 문장 바로 뒤의 줄이다
        assert flat.index(PIC_LINE) == flat.index(MENU) + len(MENU) + len(" - ")
    # 기술 계약(생성 · 재시도 · 다듬기가 함께 쓴다) - 과제 밖 입구 줄 바로 뒤
    for t in (p.load_template(task), p.load_refine_template(task)):
        flat = " ".join(t.split())
        assert flat.count(CONTRACT_LINE) == 1
        assert flat.index("흐름 명세의 걸음이나 `reveal` 로 닿을 수 있어야 한다. - "
                          + CONTRACT_LINE) >= 0
    assert CONTRACT_LINE not in " ".join(p.load_plan_template(task).split())


def test_the_failure_text_quotes_the_contract_line():
    """재시도 때 모델이 받는 글이 기술 계약의 문장과 같다."""
    assert L.RULE == CONTRACT_LINE


# ===================================================================== #
# 3. mock - 통과하는 mock 은 원본의 그림 자리를 두고, images-dropped 만 지운다
# ===================================================================== #
M = _api.model_module


def test_the_mock_builds_carry_the_slots_except_images_dropped():
    assert "images-dropped" in M.MODES and M.IMAGE_MODES == {"images-dropped"}
    for mode in M.MODES:
        html = M.mock_build(mode)
        assert (M.IMAGES_BLOCK_ID in html) is (mode != "images-dropped"), mode
    # images-dropped 는 pass 와 그림 자리 블록 · 그 CSS · 채우는 스크립트만 다르다
    assert M.mock_build("images-dropped") == (
        M.mock_build("pass").replace(M.image_block(), "").replace(M.IMAGES_CSS, "")
        .replace(M.image_script(), ""))


def test_the_mock_block_names_come_from_the_original():
    names = M.image_names()
    for name in ("메시지 아이콘", "신한은행 로고", "카메라 아이콘", "국민 로고"):
        assert name in names
    # 스크립트가 이름을 바꾸는 자리(확인 화면의 받는 은행 로고)와 [증권사] 탭의 로고는 뺀다
    assert "받는 은행 로고" not in names and "교보증권 로고" not in names
    assert len(names) == 22 + 38
    # 이름은 원문에 그대로 적지 않는다 - 검사 I 가 원문에서 은행 · 증권사 이름을 찾는다.
    # window.PRESERVED 도 읽지 않는다 (preserved-none 이 형식 검사에서 떨어지는 이유)
    script = M.image_script()
    assert "국민" not in script and "신한투자증권" not in script and "PRESERVED" not in script
    assert "BOA" not in script and "HSBC" not in script               # 로마자 이름도


# ===================================================================== #
# 4. 실제로 걷는다 (pytest -m browser)
# ===================================================================== #
# 원본을 걷는 동안 보이는 그림 자리 이름 (test_image_slots 의 화면별 수에서 겹치는 이름을
# 뺀 것 - 이체 확인 화면의 "신한 로고" 는 은행 목록의 것과 같은 이름이다)
ORIGINAL_NAMES = {"transfer": 19 + 3 + 38, "bill": None}


def final_audit(summary):
    path = os.path.join(summary["run_dir"],
                        "attempt_%d.audit.json" % summary["attempts"][-1]["n"])
    return json.load(io.open(path, encoding="utf-8"))


@pytest.mark.browser
@pytest.mark.parametrize("task", ["transfer", "bill"])
def test_original_against_itself_keeps_every_slot(server, task):
    import capture_baseline as C
    t = _api.load_task(task)
    f = _api.load_flow(None, task=task)
    html = io.open(_api.tasks_module.abs_path(t["original"]), encoding="utf-8").read()
    s = asyncio.run(_api.drive("%s/%s" % (C.BASE_URL, t["original"]), f))
    report = _api.audit(s, s, html, html, f)
    m = report["metrics"]
    assert l_fatals(report) == [] and m["images_missing"] == [] and m["images_new"] == []
    assert m["images_kept"] == m["images_original"] > 0
    if task == "transfer":
        assert m["images_original"] == ORIGINAL_NAMES["transfer"]
        # [증권사] 탭 29 + 확인 화면의 "받는 은행 로고" (보일 때는 고른 은행의 이름이다)
        assert len(m["images_not_in_original"]) == 29 + 1
        assert "받는 은행 로고" in m["images_not_in_original"]
        assert m["images_box"]["국민 로고"]["box"][2:] == [32, 32]


@pytest.mark.browser
@pytest.mark.parametrize("mode,passed", [("images-dropped", False), ("pass", True)])
def test_a_mock_build_is_judged_on_its_image_slots(server, mode, passed):
    import capture_baseline as C
    C.ensure_mock_input()
    summary, code = C.run_mock(["--mock", mode, "--attempts", "1", "--refine", "0"])
    report = final_audit(summary)
    m = report["metrics"]
    assert summary["passed"] is passed and code == (0 if passed else 1)
    assert m["images_original"] == ORIGINAL_NAMES["transfer"]
    if passed:
        assert m["images_kept"] == m["images_original"] and l_fatals(report) == []
    else:
        assert [f["check"] for f in report["fatal"]] == ["L"]
        assert m["images_kept"] == 0


# 그림 자리를 지운 두 실제 실행 - 지운 수가 원본에서 보인 수와 같다.
RUNS = [("20261008-131136", 2), ("20261012-132226", 1)]


@pytest.mark.browser
@pytest.mark.parametrize("run,n", RUNS, ids=[r for r, _ in RUNS])
def test_the_runs_that_dropped_every_slot_fail(server, run, n):
    import capture_baseline as C
    d = os.path.join(ROOT, "results", "runs", run)
    orig_html = io.open(os.path.join(ROOT, C.ORIGINAL_REL), encoding="utf-8").read()
    orig_url = "%s/%s" % (C.BASE_URL, C.ORIGINAL_REL)
    snap_ = asyncio.run(_api.drive(orig_url, _api.load_flow(None), errors=False))
    html_path = os.path.join(d, "attempt_%d.html" % n)
    url = "%s/results/runs/%s/attempt_%d.html" % (C.BASE_URL, run, n)
    report = _api.audit_call_module.run_audit(
        snap_, orig_html, html_path, os.path.join(d, "attempt_%d.flow.json" % n), url, None,
        "wireframe", original_url=orig_url, task="transfer")
    m = report["metrics"]
    assert m["images_original"] == ORIGINAL_NAMES["transfer"]
    assert m["images_kept"] == 0 and len(m["images_missing"]) == m["images_original"]
    assert len(l_fatals(report)) == 1
