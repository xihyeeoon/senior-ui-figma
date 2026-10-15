r"""문헌 원칙 (`--principles none|ga|na`, 2026-10-15).

실행 ④ (20261013-170616, --mode layout · --captures · 원칙 없음) 와 모든 조건을 같게 두고 문헌 원칙만
넣어 차이를 보려는 준비다. 원칙은 prompts/principles/<조건>.json 에 있고 (README 가 칸 뜻), 글의
자리는 docs/restructure-prompt.md 의 "원칙" 절이다.

  1. 원칙 파일 - 모양 · id 순서 · ga 의 아홉 항목이 na 의 같은 항목과 글자까지 같은지 · 바꾸지 않은
     항목은 db_text = given_text
  2. 프롬프트에 넣기 - none 은 그대로 · ga 9줄 · na 27줄 · given_text 만 들어가고 db_text · source ·
     strength · change 는 들어가지 않음 · 진단·계획은 "규칙 목록은 주지 않는다." 한 문장만 [목표 +
     머리말 + 원칙 줄] 로 바뀜 · 계획 형식의 applied 한 줄 · 생성 · 다듬기는 과제 설명 바로 뒤 (applied
     문장은 뺌) · 글은 docs/restructure-prompt.md 한 곳

  .\.venv\Scripts\python.exe -m pytest tests/test_principles.py
"""
import io
import re
import json
import os

import pytest

import _api

ROOT = _api.ROOT_DIR
DIR = os.path.join(ROOT, "prompts", "principles")
GA_IDS = ["S02", "S03", "S04", "S06", "S08", "S09", "S17", "S22", "C01"]
NA_IDS = ["S%02d" % i for i in range(1, 28) if i != 7] + ["C01"]
KEYS = ["id", "given_text", "db_text", "change", "source", "strength"]
SOURCE_DB = "guideline-db-1014 (조율 채팅 프로젝트 문서, 세 리뷰 논문에서 뽑아 원문 대조)"


def read(cond):
    return json.load(io.open(os.path.join(DIR, "%s.json" % cond), encoding="utf-8"))


# ===================================================================== #
# 1. 원칙 파일
# ===================================================================== #
@pytest.mark.parametrize("cond, ids", [("ga", GA_IDS), ("na", NA_IDS)])
def test_the_file_has_the_agreed_shape_and_order(cond, ids):
    data = read(cond)
    assert list(data) == ["condition", "source_db", "items"]
    assert data["condition"] == cond
    assert data["source_db"] == SOURCE_DB
    assert [it["id"] for it in data["items"]] == ids
    for it in data["items"]:
        assert list(it) == KEYS, it["id"]
        assert all(isinstance(it[k], str) and it[k].strip() for k in KEYS[:5]), it["id"]
        assert it["strength"] in (1, 2, 3, "보조"), it["id"]


def test_na_has_no_s07_because_it_changes_the_flow():
    assert "S07" not in [it["id"] for it in read("na")["items"]]
    assert len(NA_IDS) == 27


def test_ga_items_are_the_na_items_letter_for_letter():
    na = {it["id"]: it for it in read("na")["items"]}
    for it in read("ga")["items"]:
        assert it == na[it["id"]]


@pytest.mark.parametrize("cond", ["ga", "na"])
def test_change_says_how_the_db_text_was_changed(cond):
    for it in read(cond)["items"]:
        c = it["change"]
        assert c == "그대로" or c.startswith("예시만: ") or c.startswith("바꿈: "), it["id"]
        # 바꾸지 않은 항목은 DB 문장 그대로다. 바꾼 항목은 DB 문장이 따로 남는다
        assert (it["db_text"] == it["given_text"]) == (c == "그대로"), it["id"]


def test_the_rewritten_items_keep_functions():
    """기능 보존 원칙으로 바꾼 셋 (S01 · S02 · S04) 은 지우라는 말을 주지 않는다."""
    na = {it["id"]: it for it in read("na")["items"]}
    for i in ("S01", "S02"):
        assert "지우지는 않는다." in na[i]["given_text"]
        assert "뺀다" in na[i]["db_text"] or "빼거나" in na[i]["db_text"]
    assert "덜 눈에 띄게" in na["S04"]["given_text"]
    assert "드러내지 않는다" in na["S04"]["db_text"]
    # 흐름 고정 단계 - 화면 수를 줄이라는 말은 뺐다
    assert "화면 수" not in na["S06"]["given_text"]
    assert "화면 수를 줄인다" in na["S06"]["db_text"]


def test_the_readme_explains_the_fields():
    text = io.open(os.path.join(DIR, "README.md"), encoding="utf-8").read()
    for word in KEYS + ["strength 는 프롬프트에 넣지 않는다", "change", "Gomez-Hernandez",
                        "Nurgalieva", "Mattick", "kb/README.md"]:
        assert word in text, word


# ===================================================================== #
# 2. 프롬프트에 넣기
# ===================================================================== #
# 글은 docs/restructure-prompt.md 한 곳에 있다. 아래는 연구자가 준 전문 그대로다 - 블록이 바뀌면
# 이 시험이 먼저 안다.
P = _api.prompt_module
PR = _api.principles_module
T = _api.tasks_module
TASKS = ("transfer", "bill")
MODES = ("full", "layout")
GOAL = ("목표: {{AUDIENCE}}가 이 과제를 혼자 끝낼 수 있는 화면을 만든다. 좋은 화면은 다음과 같다.\n"
        "1. 각 화면에서 지금 할 일과 다음에 누를 것 하나가 한눈에 보인다.\n"
        "2. 지금 단계에서 쓰지 않는 것은 접히거나 덜 눈에 띄는 자리에 있다. 지우지는 않는다 — 원본에서 "
        "할 수 있던 일은 모두 할 수 있어야 한다.\n"
        "3. 단순하지만 기능과 보기 좋음을 지운 '시니어 모드' 는 아니다.\n"
        "글자 크기 · 누르는 영역 · 대비 같은 요소 수준은 네 판단대로 하라. 이 지면은 화면의 짜임 — 무엇을 "
        "위에 두고, 무엇을 접고, 무엇을 옮길지 — 에 쓴다. 아래 원칙은 그 판단의 근거다. 원칙이 기능 보존 "
        "약속 (입구 · 선택지 · 오류 경로 · 그림 자리를 지우지 않기) 과 부딪치면 약속이 먼저다.")
HEAD = {"ga": ("아래 원칙을 모든 화면에 적용하라.",
               " 계획의 화면마다 applied 에 원칙마다 이 화면에서 어떻게 적용했는지 한 줄씩 적어라 "
               "(해당 없으면 '해당 없음 — 이유')."),
        "na": ("아래 원칙 가운데 화면마다 맞는 것을 골라 적용하라.",
               " 계획의 화면마다 applied 에 고른 원칙마다 왜 골랐는지와 어떻게 적용했는지 적어라.",
               " 서로 부딪치는 원칙이 있다 — S14 와 S15 (조작 위치), S01 · S02 와 C01 (지나친 단순화), "
               "S27 (익숙한 조작을 바꾸는 것). 둘 다 적용하려 하지 말고 그 화면에 맞는 쪽을 골라 이유를 "
               "적어라.")}
LINE = re.compile(r"^- (?:S\d\d|C01): ", re.M)
DIAGNOSE = ("각 화면에서 {{AUDIENCE}}가 어디서 멈추고, 무엇을 잘못 누르고,\n"
            "  무엇을 못 읽을지를 원본에서 직접 보고 적어라.")
GENERAL = "원본에서 가리킬 수 없는 일반론은 적지 마라."


def aud(text, task):
    return T.fill_audience(text, T.load_task(task)["audience"])


def plan_head(cond):
    return "".join(HEAD[cond])


def build_head(cond):
    """생성 · 다듬기에는 applied 를 적으라는 문장이 없다 - 계획을 쓰지 않는 단계다."""
    return "".join(h for h in HEAD[cond] if "applied" not in h)


def principle_lines(cond):
    return "\n".join("- %s: %s" % (it["id"], it["given_text"]) for it in read(cond)["items"])


def templates(task, mode, cond):
    kw = {} if cond is None else {"principles": cond}
    return {"plan": P.load_plan_template(task, mode=mode, **kw),
            "generate": P.load_template(task, mode=mode, **kw),
            "refine": P.load_refine_template(task, mode=mode, **kw)}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("task", TASKS)
def test_none_is_the_prompt_without_the_option(task, mode):
    """none 은 아무것도 넣지 않는다. 9d1a33e 와의 바이트 비교는 기준값 (tests/baseline/prompt ·
    bill/prompt) 과 보고의 sha 표가 한다."""
    before, none = templates(task, mode, None), templates(task, mode, "none")
    assert before == none
    for name, t in none.items():
        assert "{{" not in t.replace("{{ORIGINAL_HTML}}", "").replace("{{RETRY_BLOCK}}", "") \
            .replace("{{CHOICES}}", "").replace("{{ERRORS}}", "").replace("{{PLAN}}", "") \
            .replace("{{ORIGINAL_SHOTS}}", "").replace("{{ORIGINAL_SCREENS}}", "") \
            .replace("{{CURRENT_HTML}}", "").replace("{{CURRENT_FLOW}}", "") \
            .replace("{{BUILD_SHOTS}}", ""), name
        assert "applied" not in t and "목표:" not in t, name
    assert "- 규칙 목록은 주지 않는다. " + aud(DIAGNOSE, task) in none["plan"]


@pytest.mark.parametrize("cond", ["ga", "na"])
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("task", TASKS)
def test_every_given_text_goes_in_and_nothing_else(task, mode, cond):
    items = read(cond)["items"]
    for name, t in templates(task, mode, cond).items():
        for it in items:
            assert "- %s: %s\n" % (it["id"], it["given_text"]) in t, (name, it["id"])
            if it["db_text"] != it["given_text"]:
                assert it["db_text"] not in t, (name, it["id"])
            assert it["source"] not in t, (name, it["id"])
            # "그대로" 는 프롬프트의 다른 문장에도 있는 낱말이라 바꾼 기록만 본다
            assert it["change"] == "그대로" or it["change"] not in t, (name, it["id"])
        for word in ("strength", "보조", "db_text", "guideline-db", "source_db"):
            assert word not in t, (name, word)
        assert len(LINE.findall(t)) == {"ga": 9, "na": 27}[cond], name
        assert "{{" not in aud(GOAL, task) and aud(GOAL, task) in t, name


@pytest.mark.parametrize("cond", ["ga", "na"])
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("task", TASKS)
def test_the_plan_prompt_swaps_only_the_no_rules_sentence(task, mode, cond):
    t = templates(task, mode, cond)["plan"]
    assert "규칙 목록은 주지 않는다." not in t
    block = "%s\n\n%s\n%s\n\n- %s" % (aud(GOAL, task), plan_head(cond), principle_lines(cond),
                                      aud(DIAGNOSE, task))
    assert block in t
    assert GENERAL in t
    # 나머지는 none 과 같다 - 그 한 문장 자리와 계획 형식의 applied 한 줄만 다르다
    none = templates(task, mode, "none")["plan"]
    assert t.replace(block, "").replace(applied_line(cond), "") ==         none.replace("- 규칙 목록은 주지 않는다. " + aud(DIAGNOSE, task), "")


def applied_line(cond):
    if cond == "ga":
        return (',\n       "applied": [{"id": "<원칙 id>", '
                '"how": "<이 화면에서 어떻게 적용했는지 한 줄>"}]')
    return (',\n       "applied": [{"id": "<원칙 id>", "why": "<이 화면에 왜 골랐는지>", '
            '"how": "<이 화면에서 어떻게 적용했는지 한 줄>"}]')


@pytest.mark.parametrize("cond", ["ga", "na"])
@pytest.mark.parametrize("task", TASKS)
def test_the_plan_form_has_the_optional_applied_field(task, cond):
    t = templates(task, "layout", cond)["plan"]
    assert '"from": ["<바탕이 된 원본 data-screen>"]' + applied_line(cond) + "}" in t


@pytest.mark.parametrize("cond", ["ga", "na"])
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("task", TASKS)
def test_generate_and_refine_get_the_same_block_after_the_task(task, mode, cond):
    ts = templates(task, mode, cond)
    block = "%s\n\n%s\n%s\n\n" % (aud(GOAL, task), build_head(cond), principle_lines(cond))
    desc = T.load_task(task)["description"]
    for name, after in (("generate", '아래 "계획" 은 이 원본을 진단해 세운 것이다.'),
                        ("refine", "아래 그림들은 네가 만든 재설계를")):
        t = ts[name]
        assert "## 1. 과제\n\n%s\n\n%s%s" % (desc, block, after) in t, name
        assert "applied" not in t, name
        # 원칙을 빼면 none 과 같다
        assert t.replace(block, "") == templates(task, mode, "none")[name], name


def test_the_texts_live_in_the_prompt_file_only():
    """글은 docs/restructure-prompt.md 한 곳 - 코드에 문장을 두지 않는다."""
    doc = io.open(os.path.join(ROOT, "docs", "restructure-prompt.md"), encoding="utf-8").read()
    for name in ("PRINCIPLES_GOAL", "PRINCIPLES_HEAD_GA", "PRINCIPLES_HEAD_NA"):
        assert "<!-- %s -->" % name in doc and "<!-- /%s -->" % name in doc
    code = io.open(os.path.join(ROOT, "senior_ui", "restructure", "prompt.py"),
                   encoding="utf-8").read()
    assert "좋은 화면은 다음과 같다" not in code and "모든 화면에 적용하라" not in code


@pytest.mark.parametrize("cond", ["ga", "na"])
def test_principles_are_not_tied_to_the_mode(cond):
    for task in TASKS:
        full, layout = templates(task, "full", cond), templates(task, "layout", cond)
        for name in full:
            assert principle_lines(cond) in full[name] and principle_lines(cond) in layout[name]


def test_an_unknown_condition_stops():
    with pytest.raises(ValueError):
        P.load_template("transfer", principles="xx")


# ===================================================================== #
# 3. 명령 줄 · 루프 (모델 · 서버 · 브라우저는 부르지 않는다 - test_restructure_bugs 의 fake_run_env)
# ===================================================================== #
from test_restructure_bugs import (GOOD_PLAN_REPLY, GOOD_REPLY, PLAN_TEMPLATE,  # noqa: E402,F401
                                   fake_run_env, is_plan_prompt, make_args, out_root,
                                   run_dirs)

loop = _api.loop_module


def test_the_option_defaults_to_none():
    ap = _api.restructure_parser()
    assert ap.parse_args([]).principles == "none"
    assert ap.parse_args(["--principles", "na"]).principles == "na"
    with pytest.raises(SystemExit):
        ap.parse_args(["--principles", "xx"])


def recording_templates(monkeypatch, seen):
    """루프가 템플릿을 무엇으로 불렀는지 적는다. 템플릿은 fake_run_env 의 대역 그대로다."""
    def fake(kind, text):
        def load(task=None, **kw):
            seen.append((kind, kw))
            return text
        return load
    monkeypatch.setattr(loop, "load_template",
                        fake("generate", "TEMPLATE {{ORIGINAL_HTML}} {{RETRY_BLOCK}} {{CHOICES}}"))
    monkeypatch.setattr(loop, "load_plan_template", fake("plan", PLAN_TEMPLATE))
    monkeypatch.setattr(loop, "load_refine_template", fake("refine", "REFINE"))


def run_with(monkeypatch, out_root, calls, **kw):
    def call_model(model_, prompt, *a, **k):
        calls.append(prompt)
        text = GOOD_PLAN_REPLY if is_plan_prompt(prompt) else GOOD_REPLY
        return {"text": text, "finish_reason": "stop", "seconds": 0.0, "usage": None}
    monkeypatch.setattr(loop, "call_model", call_model)
    code = loop.run(make_args(out_root, **kw))
    d = run_dirs(out_root)[-1]
    summary = json.load(io.open(os.path.join(d, "summary.json"), encoding="utf-8"))
    log = io.open(os.path.join(d, "run.log"), encoding="utf-8").read().splitlines()
    return code, summary, log


@pytest.mark.parametrize("cond", ["ga", "na"])
def test_the_loop_asks_for_the_templates_with_the_principles(fake_run_env, out_root, cond):
    seen, calls = [], []
    recording_templates(fake_run_env, seen)
    code, summary, _log = run_with(fake_run_env, out_root, calls, principles=cond)
    assert code == 0 and calls
    assert sorted(k for k, _ in seen) == ["generate", "plan", "refine"]
    assert all(kw == {"principles": cond} for _, kw in seen)


def test_none_asks_for_the_templates_as_before(fake_run_env, out_root):
    """none 은 인자를 넘기지 않고 전과 똑같이 부른다 - 단계(--mode)와 같은 규칙."""
    seen, calls = [], []
    recording_templates(fake_run_env, seen)
    code, _summary, _log = run_with(fake_run_env, out_root, calls, principles="none")
    assert code == 0
    assert all(kw == {} for _, kw in seen)


@pytest.mark.parametrize("broken", ["missing", "not-json", "wrong-shape"])
def test_a_missing_or_broken_file_stops_before_the_model(fake_run_env, out_root, tmp_path,
                                                         broken):
    if broken == "not-json":
        (tmp_path / "ga.json").write_text("{\"condition\": \"ga\", ", encoding="utf-8")
    elif broken == "wrong-shape":
        (tmp_path / "ga.json").write_text(json.dumps({"condition": "ga", "items": [{"id": "S02"}]}),
                                          encoding="utf-8")
    fake_run_env.setattr(PR, "DIR", str(tmp_path))
    calls = []
    code, summary, _log = run_with(fake_run_env, out_root, calls, principles="ga")
    assert code == 2 and summary["stopped_reason"] == "cannot_start"
    assert calls == []
    assert "ga.json" in summary["error"]
