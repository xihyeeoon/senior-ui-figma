r"""캡처 입력 (--captures, 2026-10-12) - 진단·계획의 원본 그림을 연구자의 캡처로.

  - 주지 않으면 프롬프트는 전과 바이트까지 같다 (기준값 시험 + 여기서 소개 글)
  - 주면 그림 수 · 순서 · 이름표(label 그대로, 조각이면 " · 조각 i/n") · 소개 글
    (CAPTURES_SHOTS_INTRO) · 가로 390 으로 줄인 크기 · 조각 규칙(렌더 그림과 같은 see_parts)
  - summary 의 see 기록 (source · 대응표 경로와 sha256 · 그림마다 file · sha256 · 크기 · 조각),
    plan_prompt 기록의 그림 줄에 캡처 파일 이름, run.log 의 "보기: 캡처 N장"
  - taps 는 읽지 않는다 - 있어도 프롬프트가 같다
  - 파일 없음 · task 다름 · label 빔 · taps 모양 틀림 · PNG 아님 · --see off 와 함께 -> cannot_start

캡처는 시험 안에서 만든 작은 가짜 PNG 다 (레포의 더미앱 캡처에 기대지 않는다). 모델 · 서버 ·
브라우저는 부르지 않는다 (test_restructure_bugs 의 fake_run_env).

  .\.venv\Scripts\python.exe -m pytest tests/test_see_captures.py
"""
import io
import json
import os

import pytest

import _api
from test_restructure_bugs import (fake_run_env, is_plan_prompt, make_args,  # noqa: F401
                                   out_root, run_dirs)
from test_visual_refine import (PLAN_THEN_GOOD, images, make_png, recording_model,
                                summary_of)

loop = _api.loop_module
model = _api.model_module
P = _api.prompt_module
CAP = _api.captures_module

# 진단·계획 프롬프트의 대역 - 그림 절이 들어갈 자리가 있다
PLAN_WITH_SHOTS = ("PLAN_TEMPLATE {{ORIGINAL_HTML}} {{RETRY_BLOCK}} {{CHOICES}} "
                   "{{ORIGINAL_SCREENS}}\n{{ORIGINAL_SHOTS}}")

# (파일, 가로, 세로, label) - 줄이면 390x866 (조각 2), 390x600 (1), 390x2000 (조각 3),
# 390x6000 (조각 4 + 남는 높이)
SHOTS = [("a.png", 824, 1830, "원본 화면 home — 맨 위"),
         ("b.png", 780, 1200, "원본 화면 recipient"),
         ("c.png", 195, 1000, "원본 화면 bank — 목록"),
         ("d.png", 390, 6000, "원본 오류 상태 wrong-bank — 잘못된 값을 넣은 직후")]


def captures(root, shots=SHOTS, task="transfer", taps=None, **over):
    """root 에 가짜 PNG 와 captures.json 을 만들고 그 경로를 돌려준다."""
    os.makedirs(str(root), exist_ok=True)
    items = []
    for f, w, h, label in shots:
        make_png(os.path.join(str(root), f), w, h)
        items.append({"file": f, "label": label})
    if taps is not None:
        for it, t in zip(items, taps):
            it["taps"] = t
    data = dict({"task": task, "source": "시험용 가짜 캡처", "images": items}, **over)
    path = os.path.join(str(root), "captures.json")
    io.open(path, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False))
    return path


RENDER = None


def run_captures(env, out_root, tmp_path, path, **kw):
    """--captures 로 루프를 한 번 돌린다. 렌더 그림 둘은 따로 있다 (보내지 않아야 한다)."""
    render = images(tmp_path / "render", 2)
    env.setattr(loop, "load_plan_template", lambda task=None: PLAN_WITH_SHOTS)
    env.setattr(loop, "see_images", lambda shots, labels, ids=(): list(
        render if labels is loop.ORIGINAL_LABELS else []))
    sent = []
    env.setattr(loop, "call_model", recording_model(sent, PLAN_THEN_GOOD))
    kw.setdefault("refine", 0)
    code = loop.run(make_args(out_root, captures=path, **kw))
    summary, d = summary_of(out_root)
    return code, summary, sent, d


# ===================================================================== #
# 1. 그림 - 수 · 순서 · 이름표 · 소개 글 · 크기 · 조각
# ===================================================================== #
LABELS = ["원본 화면 home — 맨 위 · 조각 1/2", "원본 화면 home — 맨 위 · 조각 2/2",
          "원본 화면 recipient",
          "원본 화면 bank — 목록 · 조각 1/3", "원본 화면 bank — 목록 · 조각 2/3",
          "원본 화면 bank — 목록 · 조각 3/3",
          "원본 오류 상태 wrong-bank — 잘못된 값을 넣은 직후 · 조각 1/4",
          "원본 오류 상태 wrong-bank — 잘못된 값을 넣은 직후 · 조각 2/4",
          "원본 오류 상태 wrong-bank — 잘못된 값을 넣은 직후 · 조각 3/4",
          "원본 오류 상태 wrong-bank — 잘못된 값을 넣은 직후 · 조각 4/4"]


def test_the_plan_call_sees_the_captures_in_order(fake_run_env, out_root, tmp_path):
    path = captures(tmp_path / "cap", )
    code, summary, sent, d = run_captures(fake_run_env, out_root, tmp_path, path)
    assert code == 0
    plan, gen = sent
    assert [im["label"] for im in plan["images"]] == LABELS
    assert gen["images"] == []                                  # 생성에는 그림이 없다
    sizes = [model.png_size(im["path"]) for im in plan["images"]]
    assert sizes == [(390, 844), (390, 844), (390, 600)] + [(390, 844)] * 7
    # 줄인 그림은 실행 폴더가 아니라 산출물 폴더에
    assert all(not im["path"].startswith(d) for im in plan["images"])
    assert all(os.sep + "see-captures" + os.sep in im["path"] for im in plan["images"])
    # 소개 글은 캡처의 것
    assert P.CAPTURES_SHOTS_INTRO in plan["prompt"]
    assert P.ORIGINAL_SHOTS_INTRO not in plan["prompt"]


def test_the_slices_follow_the_render_rule():
    """창 높이 844 씩, 100px 겹치게, 마지막 장은 맨 아래에 맞춰, 최대 4장."""
    see_parts = _api.drive_module.see_parts
    assert see_parts(866 - 844, 844) == (2, 744, 0)
    assert see_parts(2000 - 844, 844) == (3, 744, 0)
    parts, step, more = see_parts(6000 - 844, 844)
    assert (parts, step) == (4, 744) and more == 6000 - 844 - 3 * 744


def test_prepare_records_each_capture(tmp_path):
    path = captures(tmp_path / "cap")
    cap = CAP.load(path, "transfer")
    imgs, records = CAP.prepare(cap, str(tmp_path / "sent"))
    assert [r["file"] for r in records] == ["a.png", "b.png", "c.png", "d.png"]
    assert [(r["size"], r["scaled"], r["sent"], r["parts"]) for r in records] == [
        ([824, 1830], [390, 866], [390, 844], 2),
        ([780, 1200], [390, 600], [390, 600], 1),
        ([195, 1000], [390, 2000], [390, 844], 3),
        ([390, 6000], [390, 6000], [390, 844], 4)]
    assert records[3]["more_px"] == 6000 - 844 - 3 * 744
    assert records[0]["sha256"] == CAP.sha256_of(os.path.join(str(tmp_path / "cap"), "a.png"))
    assert [r["label"] for r in records] == [s[3] for s in SHOTS]
    # 그림마다 원래 캡처 파일 - 기록 줄에 남는다
    assert {im["source"] for im in imgs} == {CAP.rel(os.path.join(str(tmp_path / "cap"), f))
                                             for f, *_ in SHOTS}


def test_the_same_capture_gives_the_same_picture(tmp_path):
    """줄이는 필터를 고정했다 - 두 번 줄여도 바이트까지 같다."""
    path = captures(tmp_path / "cap")
    cap = CAP.load(path, "transfer")
    a, _ = CAP.prepare(cap, str(tmp_path / "one"))
    b, _ = CAP.prepare(cap, str(tmp_path / "two"))
    assert [open(x["path"], "rb").read() for x in a] == [open(x["path"], "rb").read() for x in b]
    assert CAP.RESAMPLE == "LANCZOS" and (CAP.WIDTH, CAP.HEIGHT) == (390, 844)


# ===================================================================== #
# 2. 기록 - summary · plan_prompt · run.log
# ===================================================================== #
def test_the_summary_records_where_the_pictures_came_from(fake_run_env, out_root, tmp_path):
    path = captures(tmp_path / "cap")
    _c, summary, _s, _d = run_captures(fake_run_env, out_root, tmp_path, path)
    see = summary["see"]
    assert see["on"] is True and see["source"] == "captures"
    assert see["on_source"] == "기본값 (켜짐)"
    assert see["captures"] == CAP.rel(path) and see["captures_sha256"] == CAP.sha256_of(path)
    assert see["original_images"] == len(LABELS) and see["rendered_images"] == 2
    assert [(i["file"], i["parts"], i["sent"]) for i in see["images"]] == [
        ("a.png", 2, [390, 844]), ("b.png", 1, [390, 600]), ("c.png", 3, [390, 844]),
        ("d.png", 4, [390, 844])]
    assert set(see["images"][0]) == {"file", "sha256", "size", "scaled", "sent", "parts",
                                     "more_px", "label"}


def test_the_saved_prompt_names_the_capture_files(fake_run_env, out_root, tmp_path):
    path = captures(tmp_path / "cap")
    _c, _s, _sent, d = run_captures(fake_run_env, out_root, tmp_path, path)
    saved = io.open(os.path.join(d, "attempt_1.plan_prompt.txt"), encoding="utf-8").read()
    a = CAP.rel(os.path.join(str(tmp_path / "cap"), "a.png"))
    assert "[그림 1/10] 원본 화면 home — 맨 위 · 조각 1/2  <그림: %s 390x844 · 예상 " % a in saved
    assert "see-captures" not in saved
    log = io.open(os.path.join(d, "run.log"), encoding="utf-8").read()
    assert ("보기: 캡처 4장 (%s)" % CAP.rel(path)) in log


def test_the_run_folder_gets_no_capture_copies(fake_run_env, out_root, tmp_path):
    path = captures(tmp_path / "cap")
    _c, _s, _sent, d = run_captures(fake_run_env, out_root, tmp_path, path)
    for _root, _dirs, files in os.walk(d):
        assert not any(f.startswith(("a.", "b.", "c.", "d.", "01_", "02_")) for f in files)


def test_taps_are_not_read(fake_run_env, out_root, tmp_path):
    """taps 는 스크린샷 입력 시험(feat/screen-detect)이 쓴다 - 있어도 프롬프트 · 그림이 같다."""
    plain = captures(tmp_path / "plain")
    tapped = captures(tmp_path / "tapped", taps=[[{"text": "이체", "to": "b.png"}],
                                                 [{"text": "다음", "to": "c.png"}], [], []])
    _c, _s, one, _d = run_captures(fake_run_env, out_root, tmp_path, plain)
    _c, _s, two, _d = run_captures(fake_run_env, out_root, tmp_path, tapped)
    assert one[0]["prompt"] == two[0]["prompt"]
    assert ([im["label"] for im in one[0]["images"]]
            == [im["label"] for im in two[0]["images"]])
    assert ([open(im["path"], "rb").read() for im in one[0]["images"]]
            == [open(im["path"], "rb").read() for im in two[0]["images"]])


def test_without_captures_the_prompt_is_as_before(fake_run_env, out_root, tmp_path):
    """주지 않으면 전과 같다 - 렌더 그림 · 그 소개 글 · source render."""
    render = images(tmp_path / "render", 2)
    fake_run_env.setattr(loop, "load_plan_template", lambda task=None: PLAN_WITH_SHOTS)
    fake_run_env.setattr(loop, "see_images", lambda shots, labels, ids=(): list(
        render if labels is loop.ORIGINAL_LABELS else []))
    sent = []
    fake_run_env.setattr(loop, "call_model", recording_model(sent, PLAN_THEN_GOOD))
    loop.run(make_args(out_root, refine=0))
    summary, _d = summary_of(out_root)
    assert [im["path"] for im in sent[0]["images"]] == [im["path"] for im in render]
    assert P.ORIGINAL_SHOTS_INTRO in sent[0]["prompt"]
    assert P.CAPTURES_SHOTS_INTRO not in sent[0]["prompt"]
    assert summary["see"] == {"on": True, "on_source": "기본값 (켜짐)", "source": "render",
                              "original_images": 2}
    # 그림 절은 전의 함수 그대로다
    assert P.shots_section(render) == "## 원본 화면\n\n%s\n\n%s\n\n" % (
        P.ORIGINAL_SHOTS_INTRO, model.IMAGE_MARK)


# ===================================================================== #
# 3. 시작 전 확인 - 어기면 cannot_start (종료 2)
# ===================================================================== #
def cannot(env, out_root, tmp_path, path, **kw):
    code, summary, sent, _d = run_captures(env, out_root, tmp_path, path, **kw)
    assert code == 2 and summary["stopped_reason"] == "cannot_start", summary
    assert sent == []                                   # 모델을 부르지 않았다
    return summary["error"]


def test_a_missing_file_cannot_start(fake_run_env, out_root, tmp_path):
    path = captures(tmp_path / "cap")
    os.remove(os.path.join(str(tmp_path / "cap"), "c.png"))
    assert "파일이 없다" in cannot(fake_run_env, out_root, tmp_path, path)


def test_a_missing_table_cannot_start(fake_run_env, out_root, tmp_path):
    assert "대응표가 없다" in cannot(fake_run_env, out_root, tmp_path,
                                   str(tmp_path / "nowhere" / "captures.json"))


def test_another_task_cannot_start(fake_run_env, out_root, tmp_path):
    path = captures(tmp_path / "cap", task="bill")
    assert "task" in cannot(fake_run_env, out_root, tmp_path, path)


def test_an_empty_label_cannot_start(fake_run_env, out_root, tmp_path):
    path = captures(tmp_path / "cap", shots=SHOTS[:1] + [("b.png", 390, 844, "  ")])
    assert "label 이 비었다" in cannot(fake_run_env, out_root, tmp_path, path)


@pytest.mark.parametrize("taps,why", [
    ([{"text": "이체", "to": "z.png"}], "images 의 file 이 아니다"),
    ([{"text": "", "to": "b.png"}], "비지 않은 글"),
    ([{"to": "b.png"}], "비지 않은 글"),
    ({"text": "이체", "to": "b.png"}, "목록이 아니다"),
], ids=["to-not-a-file", "empty-text", "no-text", "not-a-list"])
def test_bad_taps_cannot_start(fake_run_env, out_root, tmp_path, taps, why):
    path = captures(tmp_path / "cap", taps=[taps])
    assert why in cannot(fake_run_env, out_root, tmp_path, path)


def test_a_file_that_is_not_png_cannot_start(fake_run_env, out_root, tmp_path):
    path = captures(tmp_path / "cap")
    io.open(os.path.join(str(tmp_path / "cap"), "b.png"), "wb").write(b"GIF89a....")
    assert "PNG 가 아니다" in cannot(fake_run_env, out_root, tmp_path, path)


def test_captures_with_see_off_cannot_start(fake_run_env, out_root, tmp_path):
    path = captures(tmp_path / "cap")
    assert "--see off" in cannot(fake_run_env, out_root, tmp_path, path, see="off")


def test_the_cli_takes_captures():
    args = _api.restructure_parser().parse_args(["--captures", "x/captures.json"])
    assert args.captures == "x/captures.json"
    assert _api.restructure_parser().parse_args([]).captures is None
