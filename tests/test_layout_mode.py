r"""배치 단계 (--mode layout, 2026-10-13) - 프롬프트의 갈래와 흐름 고정 검사 (검사 M).

재설계를 "① 흐름 단축 → ② 레이아웃 재구성" 두 단계로 나눈다. --mode layout 이 ② 다.

  1. 프롬프트 - full (기본) 은 전과 바이트까지 같다 (기준값 prompt/*.txt 는 test_baseline 이
     본다). layout 이면 세 프롬프트에 흐름 고정 · 배치 허락 두 문장이 들어가고, 진단·계획의
     "원본 구조를 지킬 필요 없다" 는 그 두 문장으로 바뀐다.
  2. 흐름 고정 판정 (flow_fixed.judge) - 원본 흐름의 정답 경로를 처음 닿은 차례의 화면
     목록으로 줄이고, 생성물의 것을 계획의 from 으로 원본 이름에 맞춰 견준다.
  3. 루프 - layout 이면 다르면 fatal (M), full 이면 metrics.flow_fixed 에 기록만 한다.
"""
import io
import json
import os

import pytest

import _api
from test_restructure_bugs import (GOOD_DIAGNOSIS, GOOD_REPLY, fake_run_env,  # noqa: F401
                                   is_plan_prompt, out_root, reply_text, run_dirs)
from test_visual_refine import plan_reply, run_with

P = _api.prompt_module
loop = _api.loop_module
FF = loop.FF

# 사용자가 준 두 문장 그대로 (2026-10-13)
FLOW_FIXED = ("- 이 단계는 흐름을 바꾸지 않는다. 원본의 화면과 그 차례, 화면마다 하는 일 (입력 · 선택 · "
              "확인) 을 그대로 둔다. 화면을 합치거나 나누거나 없애지 않는다. 오류 표시는 원본처럼 그 "
              "화면 위에 띄우거나 그 화면 안에 보여도 된다.")
LAYOUT_FREE = ("- 화면 배치는 자유다. 세로 목록만 쓸 필요는 없다. 아이콘과 이름을 함께 둔 격자, 관련 "
               "메뉴를 묶은 카드, 탭처럼 고령자가 찾기 쉬운 배치를 골라도 된다.")
FREE_SCREENS = "- 화면을 몇 개로 나눌지, 어떤 순서로 둘지는 자유다. 원본 구조를 지킬 필요 없다."
RULES = FLOW_FIXED + "\n" + LAYOUT_FREE + "\n"
TASKS = ["transfer", "bill"]
LOADERS = ["load_plan_template", "load_template", "load_refine_template"]


# ===================================================================== #
# 1. 프롬프트의 갈래
# ===================================================================== #
def test_the_blocks_are_the_two_sentences_word_for_word():
    assert P.load_block("FLOW_FIXED") == FLOW_FIXED + "\n"
    assert P.load_block("LAYOUT_FREE") == LAYOUT_FREE + "\n"
    assert P.mode_rules("layout") == RULES
    assert P.mode_rules("full") == ""
    assert P.MODES == ("full", "layout") and P.DEFAULT_MODE == "full"


@pytest.mark.parametrize("task", TASKS)
@pytest.mark.parametrize("loader", LOADERS)
def test_full_is_the_default_and_carries_neither_sentence(task, loader):
    f = getattr(P, loader)
    assert f(task) == f(task, mode="full")
    text = f(task)
    assert FLOW_FIXED not in text and LAYOUT_FREE not in text
    assert "{{MODE_" not in text


@pytest.mark.parametrize("task", TASKS)
def test_layout_plan_swaps_the_free_screens_line_for_the_two_sentences(task):
    full, layout = P.load_plan_template(task), P.load_plan_template(task, mode="layout")
    assert FREE_SCREENS in full and FREE_SCREENS not in layout
    assert RULES in layout
    # 다른 곳은 한 글자도 다르지 않다
    assert layout.replace(RULES, FREE_SCREENS + "\n") == full


@pytest.mark.parametrize("task", TASKS)
@pytest.mark.parametrize("loader", ["load_template", "load_refine_template"])
def test_layout_generation_and_refine_only_add_the_two_sentences(task, loader):
    f = getattr(P, loader)
    full, layout = f(task), f(task, mode="layout")
    assert layout.count(RULES) == 1
    assert layout.replace(RULES, "") == full
    assert "{{MODE_" not in layout


def test_layout_sentences_sit_in_the_task_section():
    gen = P.load_template("transfer", mode="layout")
    # "계획에 없는 큰 변경" 문장 바로 뒤, 2절(기술 계약) 앞
    assert gen.index("배치 같은 세부는 네가 정한다.\n" + FLOW_FIXED) < gen.index("## 2.")
    refine = P.load_refine_template("transfer", mode="layout")
    assert refine.index(FLOW_FIXED) < refine.index("## 2.")
    plan = P.load_plan_template("transfer", mode="layout")
    assert plan.index(FLOW_FIXED) < plan.index("## 2.")


def test_an_unknown_mode_stops():
    with pytest.raises(ValueError):
        P.load_template("transfer", mode="flow")


def test_the_cli_takes_mode_and_defaults_to_full():
    ap = _api.restructure_parser()
    assert ap.parse_args([]).mode == "full"
    assert ap.parse_args(["--mode", "layout"]).mode == "layout"
    with pytest.raises(SystemExit):
        ap.parse_args(["--mode", "flow"])


# ===================================================================== #
# 2. 흐름 고정 판정 (브라우저 없음)
# ===================================================================== #
ORIGINAL = ["home", "recipient", "account", "bank", "amount", "confirm", "password", "done"]
# 이름을 바꾼 화면 · 오류 화면을 합친 화면 - 원본 흐름과 같다
RENAMED = {"start": ["home"], "who": ["recipient"], "acct": ["account", "err-account"],
           "bank": ["bank"], "amt": ["amount"], "check": ["confirm", "err-bank"],
           "pin": ["password"], "sent": ["done"]}
PATH = ["start", "who", "acct", "bank", "amt", "check", "pin", "sent"]


def steps(*names):
    return [{"screen": n} for n in names]


def plan_of(came):
    return {"screens": [{"name": n, "purpose": n, "from": f} for n, f in came.items()]}


def test_the_original_path_of_the_transfer_task():
    orig = FF.original_steps("transfer")
    # 원본 흐름은 계좌 화면에 두 번 머문다 (키패드 열림) - 처음 닿은 차례로 줄이면 8화면
    assert [s["screen"] for s in orig].count("account") == 2
    assert FF.first_visits(orig) == ORIGINAL


def test_renamed_screens_and_merged_error_screens_keep_the_flow():
    got = FF.judge(steps(*ORIGINAL), steps(*PATH), plan_of(RENAMED))
    assert got["same"] is True and got["problems"] == []
    assert got["mapped"] == ORIGINAL and got["built"] == PATH
    assert got["original_moves"] == got["built_moves"] == 7


def test_staying_on_a_screen_or_coming_back_is_not_a_new_step():
    """원본 흐름은 은행 시트를 닫고 계좌 화면으로 돌아온 걸음을 적지 않는다."""
    built = steps("start", "who", "acct", "acct", "bank", "acct", "amt", "check", "pin", "sent")
    got = FF.judge(FF.original_steps("transfer"), built, plan_of(RENAMED))
    assert got["same"] is True
    assert got["original_steps"] == 9 and got["built_steps"] == 10


def test_a_swapped_order_is_a_changed_flow():
    """실행 20261013-130053 - 은행을 계좌번호보다 먼저 고르게 바꿨다."""
    built = steps("start", "who", "bank", "acct", "amt", "check", "pin", "sent")
    got = FF.judge(steps(*ORIGINAL), built, plan_of(RENAMED))
    assert got["same"] is False
    assert got["problems"] == ["화면 차례가 다르다"]


def test_merging_two_original_screens_is_a_changed_flow():
    came = dict(RENAMED, acct=["account", "bank"])
    del came["bank"]
    built = steps("start", "who", "acct", "amt", "check", "pin", "sent")
    got = FF.judge(steps(*ORIGINAL), built, plan_of(came))
    assert got["same"] is False
    assert "원본 화면 account + bank 를 합친 화면 acct" in got["problems"]
    assert "걸음 수가 다르다 (원본 7 · 생성물 6)" in got["problems"]


def test_splitting_an_original_screen_is_a_changed_flow():
    came = dict(RENAMED, acct2=["account"])
    built = steps("start", "who", "acct", "acct2", "bank", "amt", "check", "pin", "sent")
    got = FF.judge(steps(*ORIGINAL), built, plan_of(came))
    assert got["same"] is False
    assert "원본 화면 account 를 나눈 화면 acct · acct2" in got["problems"]


def test_dropping_a_screen_is_a_changed_flow():
    built = steps("start", "who", "acct", "bank", "amt", "pin", "sent")
    got = FF.judge(steps(*ORIGINAL), built, plan_of(RENAMED))
    assert got["same"] is False
    assert "정답 경로에서 빠진 원본 화면 confirm" in got["problems"]


@pytest.mark.parametrize("came, why", [
    ({"guide": []}, "원본에 없던 화면 guide (계획의 from 이 비었다)"),
    ({"guide": ["err-account"]}, "원본에 없던 화면 guide (계획의 from 이 비었다)"),
    ({}, "계획에 없는 화면 guide"),
])
def test_a_new_or_unplanned_screen_on_the_path_is_a_changed_flow(came, why):
    built = steps("start", "guide", "who", "acct", "bank", "amt", "check", "pin", "sent")
    got = FF.judge(steps(*ORIGINAL), built, plan_of(dict(RENAMED, **came)))
    assert got["same"] is False and why in got["problems"]
    assert "?guide" in got["mapped"]


def test_a_screen_off_the_path_is_not_judged():
    """정답 경로 밖의 화면 (다른 메뉴를 모은 화면 · 오류만 보이는 화면) 은 보지 않는다."""
    came = dict(RENAMED, services=["home"], oops=["err-bank"])
    assert FF.judge(steps(*ORIGINAL), steps(*PATH), plan_of(came))["same"] is True


def report():
    return {"passed": True, "fatal": [], "warning": [],
            "metrics": {"fatal_total": 0, "fatal_root": 0, "fatal_derived": 0}}


def test_full_only_records_it():
    bad = FF.judge(steps(*ORIGINAL), steps("start", "sent"), plan_of(RENAMED))
    rep = FF.apply(report(), bad, "full")
    assert rep["passed"] is True and rep["fatal"] == []
    assert rep["metrics"]["flow_fixed"]["same"] is False
    assert rep["metrics"]["flow_fixed"]["judged"] is False
    assert rep["metrics"]["fatal_total"] == 0


def test_layout_makes_a_changed_flow_fatal_and_quotes_the_rule():
    bad = FF.judge(steps(*ORIGINAL), steps("start", "sent"), plan_of(RENAMED))
    rep = FF.apply(report(), bad, "layout")
    assert rep["passed"] is False
    (f,) = rep["fatal"]
    assert f["check"] == "M" and f["keep_detail"] is True
    assert FLOW_FIXED[2:] in f["detail"]
    assert "원본 home → recipient → account" in f["detail"]
    assert rep["metrics"]["fatal_total"] == 1 and rep["metrics"]["fatal_root"] == 1
    assert rep["metrics"]["flow_fixed"]["judged"] is True


def test_layout_keeps_a_kept_flow_passing():
    good = FF.judge(steps(*ORIGINAL), steps(*PATH), plan_of(RENAMED))
    rep = FF.apply(report(), good, "layout")
    assert rep["passed"] is True and rep["fatal"] == []


def test_the_retry_block_keeps_the_whole_rule_sentence():
    """brief_failure 는 200자에서 자른다 - 흐름 고정 안내문은 끝의 규칙 문장까지 간다."""
    bad = FF.judge(steps(*ORIGINAL), steps("start", "sent"), plan_of(RENAMED))
    rep = FF.apply(report(), bad, "layout")
    block = P.retry_block(rep, "<html></html>", "{}")
    assert FLOW_FIXED[2:] in block


# ===================================================================== #
# 3. 루프 (모델 · 검사기는 가짜)
# ===================================================================== #
def keeping_build():
    """원본 이체 흐름의 8화면을 이름만 바꿔 그대로 밟는 빌드 · 흐름 · 계획."""
    clicks = {n: "go-%s" % n for n in PATH[1:]}
    body = "\n".join('<section class="screen" data-screen="%s">%s</section>'
                     % (n, '<button data-action="%s">다음</button>' % clicks[PATH[i + 1]]
                        if i + 1 < len(PATH) else '<span id="dn-amt">32,000</span>')
                     for i, n in enumerate(PATH))
    html = ('<html><body><div id="phone">%s</div><script>window.__screen=function(){};'
            "document.getElementById('phone').addEventListener('click',function(e){"
            "const el=e.target; const a = el.dataset.action; %s});</script></body></html>"
            % (body, " else ".join("if(a==='%s'){}" % c for c in clicks.values())))
    flow = {"name": "auto", "required_ids": ["phone", "dn-amt"],
            "steps": [{"screen": PATH[0]}] + [
                {"screen": n, "click": "[data-action='%s']" % clicks[n]} for n in PATH[1:]],
            "expect": {}}
    plan = {"screens": [{"name": n, "purpose": n, "from": RENAMED[n]} for n in PATH],
            "changes": [{"id": "C1", "what": "격자로", "why": "찾게", "addresses": ["D1"],
                         "from_screens": ["home"], "to_screens": ["start"]}]}
    return reply_text(html, flow), plan


@pytest.fixture
def layout_env(fake_run_env):
    """fake_run_env 의 대역 템플릿은 단계 인자를 받지 않는다 (기본 단계는 넘기지 않는다).
    layout 실행에서는 받기만 하는 대역으로 바꾼다."""
    tpl, plan_tpl = loop.load_template, loop.load_plan_template
    fake_run_env.setattr(loop, "load_template", lambda task=None, **_kw: tpl(task))
    fake_run_env.setattr(loop, "load_plan_template", lambda task=None, **_kw: plan_tpl(task))
    return fake_run_env


def test_a_layout_run_that_changes_the_flow_fails_on_M(layout_env, out_root):
    """GOOD_REPLY 는 시작 · 끝 두 화면 - 원본의 8화면 흐름이 아니다."""
    code, s, sent, d = run_with(layout_env, out_root,
                                [(is_plan_prompt, plan_reply()), (lambda p: True, GOOD_REPLY)],
                                mode="layout", attempts=2)
    assert code == 1 and s["mode"] == "layout"
    assert [a.get("flow_fixed") for a in s["attempts"]] == [False, False]
    rep = json.load(io.open(os.path.join(d, "attempt_1.audit.json"), encoding="utf-8"))
    assert [f["check"] for f in rep["fatal"]] == ["M"]
    assert rep["metrics"]["flow_fixed"]["judged"] is True
    # 재시도 프롬프트의 [고칠 것] 에 규칙 문장이 통째로 간다
    retry = io.open(os.path.join(d, "attempt_2.prompt.txt"), encoding="utf-8").read()
    assert "[고칠 것]" in retry and FLOW_FIXED[2:] in retry
    log = io.open(os.path.join(d, "run.log"), encoding="utf-8").read()
    assert "mode=layout" in log and "flow_fixed: 다르다" in log


def test_a_layout_run_that_keeps_the_flow_passes(layout_env, out_root):
    text, plan = keeping_build()
    code, s, sent, d = run_with(layout_env, out_root,
                                [(is_plan_prompt, plan_reply(GOOD_DIAGNOSIS, plan)),
                                 (lambda p: True, text)], mode="layout", attempts=1)
    assert code == 0, s["attempts"]
    assert s["attempts"][0]["flow_fixed"] is True


def test_a_layout_run_sends_the_layout_prompts(fake_run_env, out_root):
    """대역 템플릿을 걷어내고 실제 템플릿으로 - 진단·계획과 생성 프롬프트에 두 문장이 간다."""
    fake_run_env.setattr(loop, "load_template", P.load_template)
    fake_run_env.setattr(loop, "load_plan_template",
                         lambda task=None, **kw: "PLAN_TEMPLATE " + P.load_plan_template(task, **kw))
    text, plan = keeping_build()
    code, s, sent, d = run_with(fake_run_env, out_root,
                                [(is_plan_prompt, plan_reply(GOOD_DIAGNOSIS, plan)),
                                 (lambda p: True, text)], mode="layout", attempts=1)
    plan_p, gen_p = sent[0]["prompt"], sent[1]["prompt"]
    for p in (plan_p, gen_p):
        assert RULES in p
    assert FREE_SCREENS not in plan_p
    assert s["repro"]["prompt_template_sha256"] != loop.repro(P.load_template("transfer"))[
        "prompt_template_sha256"]


def test_a_default_run_records_the_flow_check_but_does_not_judge_it(fake_run_env, out_root):
    code, s, sent, d = run_with(fake_run_env, out_root,
                                [(is_plan_prompt, plan_reply()), (lambda p: True, GOOD_REPLY)],
                                attempts=1)
    assert code == 0
    # full 실행의 summary 는 전과 같은 모양 - mode 칸도, 시도의 flow_fixed 칸도 없다
    assert "mode" not in s and "flow_fixed" not in s["attempts"][0]
    rep = json.load(io.open(os.path.join(d, "attempt_1.audit.json"), encoding="utf-8"))
    assert rep["passed"] is True
    ff = rep["metrics"]["flow_fixed"]
    assert ff["same"] is False and ff["judged"] is False and ff["mode"] == "full"


# ===================================================================== #
# 4. 실제로 걷는다 (pytest -m browser) - mock pass 를 layout 으로
# ===================================================================== #
@pytest.mark.browser
def test_the_mock_pass_build_changes_the_flow_and_layout_catches_it():
    """mock pass 는 Run 1 빌드 - 받는 사람 확인 화면(whoconfirm, from [])을 정답 경로에 더했다.
    full 이면 통과하는 빌드가 layout 에서는 검사 M 하나로만 떨어진다."""
    import capture_baseline as C
    C.ensure_mock_input()
    s, code = C.run_mock(["--mock", "pass", "--mode", "layout", "--attempts", "1"])
    assert code == 1 and s["mode"] == "layout" and s["attempts"][0]["flow_fixed"] is False
    rep = json.load(io.open(os.path.join(s["run_dir"], "attempt_1.audit.json"), encoding="utf-8"))
    assert [f["check"] for f in rep["fatal"]] == ["M"]
    ff = rep["metrics"]["flow_fixed"]
    assert "원본에 없던 화면 whoconfirm (계획의 from 이 비었다)" in ff["problems"]
    assert ff["original"] == ORIGINAL
    plan_prompt = io.open(os.path.join(s["run_dir"], "attempt_1.plan_prompt.txt"),
                          encoding="utf-8").read()
    assert RULES in plan_prompt and FREE_SCREENS not in plan_prompt
