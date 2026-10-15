r"""문헌 원칙 (`--principles none|ga|na`, 2026-10-15).

실행 ④ (20261013-170616, --mode layout · --captures · 원칙 없음) 와 모든 조건을 같게 두고 문헌 원칙만
넣어 차이를 보려는 준비다. 원칙은 prompts/principles/<조건>.json 에 있고 (README 가 칸 뜻), 글의
자리는 docs/restructure-prompt.md 의 "원칙" 절이다.

  1. 원칙 파일 - 모양 · id 순서 · ga 의 아홉 항목이 na 의 같은 항목과 글자까지 같은지 · 바꾸지 않은
     항목은 db_text = given_text

  .\.venv\Scripts\python.exe -m pytest tests/test_principles.py
"""
import io
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
