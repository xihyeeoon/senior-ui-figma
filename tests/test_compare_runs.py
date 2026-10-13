r"""tools/compare_runs.py 의 칸 둘 - 재현본 탓 표현 (2026-10-13) · 흐름 고정.

  .\.venv\Scripts\python.exe -m pytest tests/test_compare_runs.py
"""
import importlib.util
import json
import os

import _api

SPEC = importlib.util.spec_from_file_location(
    "compare_runs", os.path.join(_api.ROOT, "tools", "compare_runs.py"))
CR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CR)


def write(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def test_grey_is_not_a_replica_word(tmp_path):
    """'회색' 은 글자색을 말할 때가 많다 (20261013-130053 의 8건 모두) - 세지 않는다."""
    assert "회색" not in CR.REPLICA_WORDS
    write(str(tmp_path), "attempt_1.diagnosis.json",
          [{"id": "D1", "evidence": "작은 회색 글씨 옆에 같은 모양의 네모 그림 둘"},
           {"id": "D2", "evidence": "회색 다음 버튼"}])
    assert CR.replica_words(str(tmp_path)) == "2 (네모 1 · 같은 모양 1)"


def test_the_earliest_diagnosis_is_read_and_none_is_a_dash(tmp_path):
    assert CR.replica_words(str(tmp_path)) == "-"
    write(str(tmp_path), "attempt_3.diagnosis.json", [{"evidence": "네모"}])
    write(str(tmp_path), "attempt_2.diagnosis.json", [{"evidence": "평범한 글"}])
    assert CR.replica_words(str(tmp_path)) == "0"


def test_the_flow_column_rejudges_a_run_without_the_metric(tmp_path):
    """검사 M 이 생기기 전의 실행 - 흐름 명세 · 계획으로 다시 판정한다."""
    d = str(tmp_path)
    names = ["home", "recipient", "account", "bank", "amount", "confirm", "password", "done"]
    write(d, "attempt_1.flow.json", {"steps": [{"screen": n} for n in names]})
    write(d, "attempt_1.plan.json", {"screens": [{"name": n, "from": [n]} for n in names]})
    summary = {"task": "transfer", "final": {"attempt": 1}}
    assert CR.flow_fixed(d, summary, {}) == "같다"
    write(d, "attempt_1.flow.json", {"steps": [{"screen": n} for n in names[:2] + names[3:]]})
    assert CR.flow_fixed(d, summary, {}).startswith("다르다 (")
    # 지표가 있으면 그것을 읽는다
    assert CR.flow_fixed(d, summary, {"flow_fixed": {"same": True, "problems": []}}) == "같다"
