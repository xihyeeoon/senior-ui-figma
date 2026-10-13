r"""배치 단계 (--mode layout, 2026-10-13) - 프롬프트의 갈래와 흐름 고정 검사 (검사 M).

재설계를 "① 흐름 단축 → ② 레이아웃 재구성" 두 단계로 나눈다. --mode layout 이 ② 다.

  1. 프롬프트 - full (기본) 은 전과 바이트까지 같다 (기준값 prompt/*.txt 는 test_baseline 이
     본다). layout 이면 세 프롬프트에 흐름 고정 · 배치 허락 두 문장이 들어가고, 진단·계획의
     "원본 구조를 지킬 필요 없다" 는 그 두 문장으로 바뀐다.
"""
import pytest

import _api

P = _api.prompt_module

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
