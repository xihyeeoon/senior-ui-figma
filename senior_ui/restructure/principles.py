r"""문헌 원칙 (`--principles none|ga|na`, 2026-10-15).

실행 ④ (20261013-170616) 는 원칙 없이 모델 자체 판단으로 만든 것이다. 같은 조건에 문헌 원칙만
넣어 차이를 보려고 원칙을 프롬프트에 넣는 옵션을 둔다.

  none  원칙 없음 (기본) - 아무 파일도 읽지 않는다. 프롬프트는 이 옵션이 생기기 전과 바이트까지 같다
  ga    고정 원칙 9개 - 모든 화면에 적용하라고 준다
  na    화면 수준 원칙 24개 + C01 (S07 · S20 · S21 없음) - 모델이 화면마다 고른다

원칙은 prompts/principles/<조건>.json 에 있다 (칸 뜻은 그 폴더의 README). 프롬프트에 들어가는
것은 id 와 given_text 뿐이다 - db_text · change · source · strength 는 기록이고 넣지 않는다.
원칙을 둘러싼 글 (목표 · 머리말) 과 넣는 자리는 docs/restructure-prompt.md 의 "원칙" 절이고, 그것을
채우는 일은 prompt.py 가 한다. 여기서는 파일을 읽고 모양을 본다.
"""
import io
import json
import os

from senior_ui.config import ROOT
from senior_ui.tasks import file_sha256

CONDITIONS = ("none", "ga", "na")
DEFAULT = "none"
DIR = os.path.join(ROOT, "prompts", "principles")
ITEM_KEYS = ("id", "given_text", "db_text", "change", "source", "strength")


def path_of(condition):
    return os.path.join(DIR, "%s.json" % condition)


def load(condition):
    """`{"condition", "file", "sha256", "items"}`. none 이면 None.

    파일이 없거나 JSON 이 깨졌거나 모양이 틀리면 ValueError (없으면 OSError) - 루프는 모델을
    부르기 전에 그것으로 멈춘다 (cannot_start). 원칙이 말없이 빠진 채로 돌면 그 실행은 none 과
    같은 프롬프트로 돌고도 ga · na 로 기록된다."""
    if condition not in CONDITIONS:
        raise ValueError("모르는 원칙 조건 %r (있는 것: %s)" % (condition, ", ".join(CONDITIONS)))
    if condition == DEFAULT:
        return None
    path = path_of(condition)
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError("원칙 파일 %s 이 JSON 으로 읽히지 않는다: %s" % (path, e))
    problems = shape_problems(data, condition)
    if problems:
        raise ValueError("원칙 파일 %s 의 모양이 틀렸다: %s" % (path, "; ".join(problems)))
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    return {"condition": condition, "file": rel, "sha256": file_sha256(path),
            "items": data["items"]}


def shape_problems(data, condition):
    """파일 모양의 문제 목록 (없으면 빈 목록)."""
    if not isinstance(data, dict):
        return ["최상위가 객체가 아니다"]
    out = []
    if data.get("condition") != condition:
        out.append("condition 이 %r 이 아니다 (지금 %r)" % (condition, data.get("condition")))
    items = data.get("items")
    if not isinstance(items, list) or not items:
        return out + ["items 가 비어 있지 않은 목록이 아니다"]
    seen = set()
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            out.append("items[%d] 가 객체가 아니다" % i)
            continue
        missing = [k for k in ITEM_KEYS if k not in it]
        if missing:
            out.append("items[%d] 에 %s 가 없다" % (i, ", ".join(missing)))
            continue
        if not (isinstance(it["given_text"], str) and it["given_text"].strip()):
            out.append("items[%d].given_text 가 빈 글이다" % i)
        if it["id"] in seen:
            out.append("id %s 가 겹친다" % it["id"])
        seen.add(it["id"])
    return out


def lines(items):
    """프롬프트에 들어가는 원칙 줄 - `- <id>: <given_text>` 를 한 줄씩."""
    return "\n".join("- %s: %s" % (it["id"], it["given_text"]) for it in items)


def record(loaded):
    """summary.json 의 `principles` 칸 - 조건 · 파일 · sha256 (줄끝 LF 로 맞춘 것)."""
    return {"condition": loaded["condition"], "file": loaded["file"],
            "sha256": loaded["sha256"]}
