r"""화면설계서의 그림 자리 칸 (storyboard.json schema 3, 2026-10-12).

장마다 그 상태에서 그려져 보인 그림 자리(role="img" + aria-label)를 `images` 에 둔다 - Figma
플러그인이 이것으로 "이 자리에 이 크기로 이런 그림" 상자를 그린다.

    "images": [{"no": "g1", "name": "<aria-label>", "box": [x, y, w, h], "original": bool,
                "in": "<항목 no>"?}, …]

  - box 는 items 의 box 와 같은 좌표 (장 왼쪽 위 기준, 스크롤 아래까지 포함한 장 전체, scale 이전)
  - 문서 순서, 장마다 g1 부터. 크기 0 · 숨김 · 이름 없는 자리는 빼고, 없으면 []
  - original = 원본을 걷는 동안 보인 이름 집합(검사 L 의 O, l_images.original_names)에 있는가
  - 누를 수 있는 요소 안이면 "in" = 그 항목 번호 (무리의 일원이면 무리)

  .\.venv\Scripts\python.exe -m pytest tests/test_storyboard_images.py
  .\.venv\Scripts\python.exe -m pytest -m browser tests/test_storyboard_images.py
"""
import copy
import io
import json
import os
import shutil

import pytest

import _api

B = _api.storyboard_build
RENDER = _api.storyboard_render
R = _api.storyboard_regions
W = _api.storyboard_walk

ROOT = _api.ROOT_DIR
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures", "storyboard")
BASE = os.path.join(HERE, "baseline", "storyboard")
L = _api.l_images_module


# ===================================================================== #
# 1. 칸을 만드는 규칙 (걷기 없이)
# ===================================================================== #
def raw_item(index, action, box):
    return {"index": index, "action": action, "id": None, "tag": "button", "value": action,
            "text": action, "aria": None, "disabled": False, "box": box}


def test_images_are_numbered_marked_and_tied_to_their_item():
    raw = [raw_item(0, "go-b", [20, 100, 80, 40]),
           raw_item(1, "pick", [20, 160, 60, 40]), raw_item(2, "pick", [20, 210, 60, 40])]
    items = B.itemize(raw, ["pick"])
    got = {"images": [{"name": "카드 그림", "box": [20, 20, 120, 60], "in_index": None},
                      {"name": "다음 아이콘", "box": [26, 110, 20, 20], "in_index": 0},
                      {"name": "가 로고", "box": [26, 164, 32, 32], "in_index": 1},
                      {"name": "나 로고", "box": [26, 214, 32, 32], "in_index": 2}]}
    out = B.images_of(got, items, raw, {"카드 그림", "가 로고"})
    by_no = {it["action"]: it["no"] for it in items}
    assert out == [
        {"no": "g1", "name": "카드 그림", "box": [20, 20, 120, 60], "original": True},
        {"no": "g2", "name": "다음 아이콘", "box": [26, 110, 20, 20], "original": False,
         "in": by_no["go-b"]},
        {"no": "g3", "name": "가 로고", "box": [26, 164, 32, 32], "original": True,
         "in": by_no["pick"]},                             # 무리의 일원 - 무리의 번호
        {"no": "g4", "name": "나 로고", "box": [26, 214, 32, 32], "original": False,
         "in": by_no["pick"]}]
    # 칸의 모양 - 정확히 이 키들 ("in" 은 있을 때만)
    assert all(set(r) <= {"no", "name", "box", "original", "in"} for r in out)


def test_a_sheet_without_images_has_an_empty_list():
    assert B.images_of({}, [], [], set()) == []
    assert B.images_of({"images": []}, [], [], {"x"}) == []


def test_an_image_in_an_element_that_is_not_an_item_has_no_in():
    """가려져 항목이 되지 않은 요소 안의 그림 자리 - "in" 이 없다."""
    out = B.images_of({"images": [{"name": "x", "box": [0, 0, 9, 9], "in_index": 7}]},
                      [], [], set())
    assert out == [{"no": "g1", "name": "x", "box": [0, 0, 9, 9], "original": False}]


def test_the_original_names_come_from_check_L():
    """설계서와 검사 L 이 같은 함수로 "원본의 그림 자리" 를 가른다."""
    assert B.original_names is L.original_names
    snap = {"images_seen": {"가 로고": {"visible": True}, "숨은 로고": {"visible": False}}}
    assert L.original_names(snap) == ["가 로고"]
    assert L.original_names({}) == []


def test_the_schema_is_3():
    assert B.SCHEMA == 3


def schema2(data):
    """schema 3 설계서를 schema 2 모양으로 (images 를 뺀다)."""
    old = copy.deepcopy(data)
    old["schema"] = 2
    # 기준값은 실행마다 바뀌는 칸을 자리만 남겼다 (capture_baseline.strip_storyboard) - 그리기용
    old["generated"] = {"at": "2026-10-12 00:00:00", "tool_commit": None,
                        "seconds": {"pictures": 1.0, "clicks": 1.0, "total": 2.0}}
    for sh in old["sheets"]:
        sh.pop("images", None)
    return old


@pytest.mark.parametrize("name", ["mock_pass", "refine_102041", "bill_sol_4"])
def test_schema_2_files_still_render_and_can_be_reused(name, tmp_path):
    """schema 2 파일(images 가 없다)을 읽는 코드 - 그리기 · --regions-from 의 읽기 · 재사용."""
    data = json.load(io.open(os.path.join(BASE, "%s.json" % name), encoding="utf-8"))
    old = schema2(data)
    page = RENDER.render(old)
    assert "<html" in page.lower()
    path = tmp_path / "storyboard.json"
    path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    saved = R.read_saved(str(path))
    sheets = copy.deepcopy(data["sheets"])
    for sh in sheets:
        sh["regions"] = []
    R.reuse(sheets, saved, str(path), log=lambda m: None)
    assert [s["regions"] for s in sheets] == [s["regions"] for s in data["sheets"]]


def test_the_baselines_carry_the_images_field():
    for name in ("mock_pass", "refine_102041", "bill_sol_4"):
        data = json.load(io.open(os.path.join(BASE, "%s.json" % name), encoding="utf-8"))
        assert data["schema"] == 3
        assert all(isinstance(sh.get("images"), list) for sh in data["sheets"]), name


# ===================================================================== #
# 2. 실제로 걷는다 (pytest -m browser) - fixtures/storyboard/images.html
# ===================================================================== #
OUT = os.path.join(ROOT, ".pytest-outputs", "storyboard_images")
FLOW = {"name": "images", "derived_from_original": False, "required_ids": [],
        "steps": [{"screen": "a"}, {"screen": "b", "click": "#go-b"}],
        "expect": {}, "error_paths": [], "truth": {}}


@pytest.fixture(scope="module")
def walked_sheets(server):
    import capture_baseline as C
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    src = os.path.join(FIX, "images.html")
    wire = os.path.join(OUT, "wireframe.html")
    io.open(wire, "w", encoding="utf-8", newline="\n").write(
        W.wire_copy(io.open(src, encoding="utf-8").read()))
    rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")
    url = "%s/%s" % (C.BASE_URL, rel(src))
    # 원본도 같은 페이지 - 원본 걷기(survey)가 검사 L 과 같은 수집으로 이름을 모으는지 본다
    states, walked = B.inspect(url, "%s/%s" % (C.BASE_URL, rel(wire)), FLOW, ["pick"],
                               os.path.join(OUT, "shots"), log=lambda m: None,
                               original=(url, FLOW))
    run = {"task": "transfer", "plan_data": {"screens": [{"name": "a", "purpose": "a."},
                                                         {"name": "b", "purpose": "b."}]}}
    sheets, _ = B.assemble(run, FLOW, states, walked, ["pick"])
    # 원본에 "아래 로고" 가 없었던 것으로 다시 - 새 그림은 original false
    w2 = copy.deepcopy(walked)
    w2["original"]["images_seen"].pop("아래 로고")
    sheets2, _ = B.assemble(run, FLOW, states, w2, ["pick"])
    return {"walked": walked, "sheets": {s["id"]: s for s in sheets},
            "sheets2": {s["id"]: s for s in sheets2}}


@pytest.mark.browser
def test_the_original_walk_collects_the_names_like_check_L(walked_sheets):
    got = L.original_names(walked_sheets["walked"]["original"])
    assert got == ["카드 그림", "다음 아이콘", "가 로고", "나 로고", "아래 로고"]


@pytest.mark.browser
def test_a_sheet_lists_its_drawn_image_slots(walked_sheets):
    a = walked_sheets["sheets"]["scr-a"]
    imgs = a["images"]
    # 문서 순서 · 숨은 것 · 이름 없는 것은 빠진다
    assert [g["no"] for g in imgs] == ["g1", "g2", "g3", "g4", "g5"]
    assert [g["name"] for g in imgs] == ["카드 그림", "다음 아이콘", "가 로고", "나 로고", "아래 로고"]
    assert all(g["original"] for g in imgs)
    items = {it["action"]: it for it in a["items"]}
    # 버튼 안의 아이콘 · 선택지 안의 로고는 그 항목 (무리는 무리의 번호)
    assert [g.get("in") for g in imgs] == [None, items["go-b"]["no"], items["pick"]["no"],
                                           items["pick"]["no"], None]
    assert [g["box"][2:] for g in imgs] == [[120, 60], [20, 20], [32, 32], [32, 32], [32, 32]]


@pytest.mark.browser
def test_the_box_is_in_the_same_frame_as_the_items(walked_sheets):
    a = walked_sheets["sheets"]["scr-a"]
    imgs = {g["name"]: g for g in a["images"]}
    items = {it["action"]: it for it in a["items"]}
    # 버튼 안의 아이콘은 그 버튼의 상자 안에 있다 - 같은 좌표계
    bx, by, bw, bh = items["go-b"]["box"]
    x, y, w, h = imgs["다음 아이콘"]["box"]
    assert bx <= x and by <= y and x + w <= bx + bw and y + h <= by + bh
    # 스크롤 아래의 것도 장 전체 기준 - 창(844px) 아래에 있고 장 안에 든다
    low = imgs["아래 로고"]["box"]
    assert low[1] > 844 and low[1] + low[3] <= a["size"][1]
    assert low[1] > 1500


@pytest.mark.browser
def test_a_sheet_without_image_slots_has_an_empty_list(walked_sheets):
    assert walked_sheets["sheets"]["scr-b"]["images"] == []


@pytest.mark.browser
def test_a_name_the_original_did_not_show_is_not_original(walked_sheets):
    imgs = {g["name"]: g for g in walked_sheets["sheets2"]["scr-a"]["images"]}
    assert imgs["아래 로고"]["original"] is False
    assert imgs["카드 그림"]["original"] is True


@pytest.mark.browser
def test_the_public_sheet_keeps_the_images_field(walked_sheets):
    pub = B.public([walked_sheets["sheets"]["scr-a"]])[0]
    assert pub["images"] == walked_sheets["sheets"]["scr-a"]["images"]
