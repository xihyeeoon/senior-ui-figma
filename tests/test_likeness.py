r"""원본 닮음 지표 (senior_ui/storyboard/likeness.py, 2026-10-13) - 기록만, 판정에 쓰지 않는다.

두 화면설계서 (원본을 빌드로 둔 것 · 재구성 실행의 것) 의 같은 화면의 장을 견준다.

  - 요소 순서 같음: 누를 수 있는 요소를 action 으로 (없으면 글로) 짝짓고, 위→아래 순서의 최장
    공통 부분열 길이 / 짝지은 수
  - 무리 순서 같음: 세로 틈으로 나눈 무리를 짝지은 요소로 원본 무리에 맞춰 같은 식으로
  - 격자 · 탭: 원본에도 있음 / 새로 생김 / 원본에 있었는데 없어짐

  .\.venv\Scripts\python.exe -m pytest tests/test_likeness.py
"""
import pytest

import _api

LK = _api.sb_likeness


def el(action, x, y, w=100, h=48, text=None, result="screen", no=None, detail=None):
    res = {"kind": result}
    if result == "same":
        res["detail"] = detail or "새로 보임: '%s' 외 2줄" % action
    return {"kind": "element", "action": action, "text": text or action, "aria": None,
            "box": [x, y, w, h], "no": no or action, "result": res}


def sheet(screen, items, images=(), main=True):
    return {"id": "scr-" + screen, "screen": screen, "main": main, "kind": "visit",
            "items": list(items), "images": list(images)}


# ===================================================================== #
# 1. 짝짓기 · 순서
# ===================================================================== #
def test_pairs_by_action_then_by_text():
    orig = [el("a", 0, 0), el(None, 0, 60, text="도움말"), el("b", 0, 120)]
    built = [el("b", 0, 0), el("x", 0, 60, text="도움말"), el("a", 0, 120), el("new", 0, 180)]
    pairs = LK.pair(orig, built)
    # a ↔ a, b ↔ b (action), 도움말 ↔ 도움말 (글 - 원본에 action 이 없다), new 는 짝이 없다
    assert sorted(pairs) == [(0, 2), (1, 1), (2, 0)]


def test_the_kth_of_an_action_pairs_with_the_kth():
    orig = [el("pick", 0, 0, no="p1"), el("pick", 0, 60, no="p2")]
    built = [el("pick", 0, 0, no="q1"), el("pick", 0, 60, no="q2")]
    assert sorted(LK.pair(orig, built)) == [(0, 0), (1, 1)]


def test_the_same_order_is_1_and_a_reversed_order_is_1_over_n():
    orig = [el("a", 0, 0), el("b", 0, 60), el("c", 0, 120), el("d", 0, 180)]
    same = [el("a", 0, 10), el("b", 0, 70), el("c", 0, 130), el("d", 0, 190)]
    rev = [el("d", 0, 0), el("c", 0, 60), el("b", 0, 120), el("a", 0, 180)]
    assert LK.element_order(orig, same, LK.pair(orig, same)) == 1.0
    assert LK.element_order(orig, rev, LK.pair(orig, rev)) == 0.25


def test_moving_one_element_to_the_top_costs_one():
    orig = [el("a", 0, 0), el("b", 0, 60), el("c", 0, 120), el("d", 0, 180)]
    built = [el("d", 0, 0), el("a", 0, 60), el("b", 0, 120), el("c", 0, 180)]
    assert LK.element_order(orig, built, LK.pair(orig, built)) == 0.75


def test_left_to_right_counts_within_a_row():
    orig = [el("a", 0, 0), el("b", 120, 0)]
    built = [el("b", 0, 2), el("a", 120, 0)]
    assert LK.element_order(orig, built, LK.pair(orig, built)) == 0.5


def test_nothing_paired_has_no_value():
    assert LK.element_order([el("a", 0, 0)], [el("b", 0, 0)], []) is None


def test_blocks_are_split_by_a_vertical_gap_and_their_order_is_compared():
    # 원본 무리 셋: [a b] [c] [d] - 생성은 [d] 를 맨 위로
    orig = [el("a", 0, 0), el("b", 0, 50), el("c", 0, 200), el("d", 0, 400)]
    built = [el("d", 0, 0), el("a", 0, 200), el("b", 0, 250), el("c", 0, 400)]
    assert [len(b) for b in LK.blocks(orig)] == [2, 1, 1]
    assert LK.block_order(orig, built, LK.pair(orig, built)) == pytest.approx(2 / 3, abs=1e-4)
    assert LK.block_order(orig, orig, LK.pair(orig, orig)) == 1.0


# ===================================================================== #
# 2. 격자 · 탭
# ===================================================================== #
def row(prefix, y, n, w=80, gap=8, h=48, result="screen", x0=0):
    return [el("%s%d" % (prefix, i), x0 + i * (w + gap), y, w=w, h=h, result=result)
            for i in range(n)]


def test_a_row_of_equal_buttons_is_a_grid_and_stacked_rows_are_one_grid():
    items = row("m", 0, 4) + row("n", 60, 4)
    units = LK.units(sheet("s", items))
    assert [(u["kind"], len(u["members"])) for u in units] == [("grid", 8)]


def test_far_apart_or_unequal_buttons_are_not_a_grid():
    """머리 띠의 [이전] · [취소] 처럼 멀리 떨어진 둘, 크기가 다른 둘은 격자가 아니다."""
    far = [el("back", 0, 0, w=80), el("close", 300, 0, w=80)]
    unequal = [el("a", 0, 100, w=80), el("b", 88, 100, w=200)]
    taller = [el("c", 0, 200, w=80), el("d", 88, 200, w=80, h=90)]
    assert LK.units(sheet("s", far + unequal + taller)) == []


def test_a_row_that_switches_content_in_place_is_a_tab():
    """고른 탭은 눌러도 그대로 (none), 다른 탭은 제자리에서 내용을 바꾼다 (same)."""
    tabs = [el("tab-a", 0, 0, w=180, result="none"), el("tab-b", 188, 0, w=180, result="same")]
    nav = row("nav", 700, 5, w=70, result="none")      # 모두 "none" - 바꾸는 것이 없으니 격자
    # 모두 "same" - 메뉴마다 제자리에 안내를 띄우는 버튼 줄 (실행 20261013-152332 의 홈) 은 격자
    notices = row("menu", 300, 4, w=70, result="same")
    # 비밀번호 숫자판 아래 줄 - [재배열] 은 순서만 바꾸고 [지우기] 는 그대로: 새 내용이 없으니 격자
    keys = [el("shuffle", 0, 500, w=120, result="same", detail="보이는 글의 순서가 바뀜"),
            el("del", 128, 500, w=120, result="none")]
    kinds = [u["kind"] for u in LK.units(sheet("s", tabs + notices + keys + nav))]
    assert kinds == ["tab", "grid", "grid", "grid"]


def test_a_row_that_turned_from_grid_into_tab_is_kept():
    """원본의 아래 띠 (눌러도 그대로 - 격자) 가 생성에서 탭처럼 바뀐 것 - 같은 줄이므로 원본에도 있음."""
    orig = sheet("home", row("nav", 700, 5, w=70, result="none"))
    built = sheet("home", [el("nav0", 0, 700, w=70, result="none")]
                  + [el("nav%d" % i, i * 78, 700, w=70, result="same") for i in range(1, 5)])
    got = LK.compare_units(orig, built, LK.pair(orig["items"], built["items"]))
    assert got == {"grid": {"kept": 0, "new": 0, "gone": 0}, "tab": {"kept": 1, "new": 0, "gone": 0}}


def test_a_choice_group_is_a_grid_when_its_logos_stand_in_columns():
    group = {"kind": "group", "action": "pick-bank", "text": "신한", "aria": None,
             "box": [0, 0, 360, 600], "no": "e5", "result": {"kind": "screen"}}
    two_cols = [{"name": "%d 로고" % i, "box": [20 + 180 * (i % 2), 10 + 70 * (i // 2), 32, 32],
                 "in": "e5"} for i in range(6)]
    one_col = [dict(g, box=[20, 10 + 70 * i, 32, 32]) for i, g in enumerate(two_cols)]
    assert [u["kind"] for u in LK.units(sheet("s", [group], two_cols))] == ["grid"]
    assert LK.units(sheet("s", [group], one_col)) == []
    # 안쪽을 잴 수 없는 무리 (숫자판 등, 그림 자리가 없다) 는 세지 않고 남긴다
    assert LK.units(sheet("s", [group])) == []
    assert LK.unmeasured(sheet("s", [group])) == ["pick-bank"]


def test_grids_and_tabs_are_sorted_into_kept_new_and_gone():
    orig = sheet("home", row("i", 0, 4) + [el("solo", 0, 300)]
                 + [el("t1", 0, 600, w=180, result="none"),
                    el("t2", 188, 600, w=180, result="same")])
    built = sheet("home", [el("i0", 0, 0), el("i1", 0, 60), el("i2", 0, 120), el("i3", 0, 180)]
                  + row("new", 400, 3)
                  + [el("t1", 0, 600, w=180, result="none"),
                     el("t2", 188, 600, w=180, result="same")])
    got = LK.compare_units(orig, built, LK.pair(orig["items"], built["items"]))
    # 아이콘 줄은 세로로 풀렸고 (없어짐), 새 격자 하나, 탭은 그대로
    assert got == {"grid": {"kept": 0, "new": 1, "gone": 1}, "tab": {"kept": 1, "new": 0, "gone": 0}}


def test_a_group_the_build_does_not_let_us_measure_is_not_counted_as_gone():
    """원본 은행 목록은 로고가 세 열 (격자) - 생성 쪽에 로고가 없으면 안쪽 배치를 모른다."""
    group = {"kind": "group", "action": "pick-bank", "text": "신한", "aria": None,
             "box": [0, 0, 360, 600], "no": "e1", "result": {"kind": "screen"}}
    logos = [{"name": "%d 로고" % i, "box": [20 + 120 * (i % 3), 10 + 70 * (i // 3), 32, 32],
              "in": "e1"} for i in range(6)]
    orig, built = sheet("bank", [group], logos), sheet("bank", [dict(group)])
    got = LK.compare_units(orig, built, LK.pair(orig["items"], built["items"]))
    assert got["grid"] == {"kept": 0, "new": 0, "gone": 0}


# ===================================================================== #
# 3. 실행 하나 - 화면을 원본 이름에 맞춘다
# ===================================================================== #
def board(*sheets_):
    return {"sheets": list(sheets_)}


def test_a_run_compares_main_sheets_of_path_screens_by_their_original_name():
    orig = board(sheet("home", [el("a", 0, 0), el("b", 0, 60)]),
                 sheet("done", [el("ok", 0, 0)]),
                 sheet("home", [el("b", 0, 0), el("a", 0, 60)], main=False))
    built = board(sheet("start", [el("b", 0, 0), el("a", 0, 60)]),
                  sheet("sent", [el("ok", 0, 0)]),
                  sheet("menu", [el("x", 0, 0)]))
    came = {"start": ["home"], "sent": ["done", "err-x"], "menu": []}
    rep = LK.run_report(orig, built, came, path=["home", "done"])
    assert [r["screen"] for r in rep["screens"]] == ["home", "done"]
    assert rep["screens"][0]["built"] == "start" and rep["screens"][0]["elements"] == 0.5
    assert rep["summary"]["elements"] == {"mean": 0.75, "min": 0.5, "screens": 2}


def test_a_screen_the_run_does_not_have_is_left_out():
    orig = board(sheet("home", [el("a", 0, 0)]), sheet("bank", [el("b", 0, 0)]))
    built = board(sheet("home", [el("a", 0, 0)]))
    rep = LK.run_report(orig, built, {"home": ["home"]}, path=["home", "bank"])
    assert [r["screen"] for r in rep["screens"]] == ["home"]
    assert rep["missing"] == ["bank"]
