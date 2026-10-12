r"""재구성 실행끼리 과제 밖 입구 거리 · 선택지 수를 나란히 놓는다.

판정이 아니라 기록용이다 - 합격선 · 기준선을 두지 않는다.

    python tools/compare_runs.py <실행 폴더> [<실행 폴더> …]

실행 폴더는 results/runs/<id> 든 outputs/restructure_auto/<id> 든 된다. 결과는 마크다운
표 하나다. 최종 시도(summary 의 final.attempt, 없으면 마지막 시도)의 audit · plan 을 읽는다.

  입구          검사 K 가 남긴 입구 / 원본에서 보인 입구
  펼침 뒤로     생성 쪽 펼치기(reveal) 횟수가 원본보다 많은 입구 수
  다른 화면     원본에서 보인 화면이 생성 쪽 화면의 plan.screens[].from 에 없는 입구 수
  스크롤        입구마다 (생성 scroll_px - 원본 scroll_px) 의 평균 · 최대
  선택지        원본을 걷는 동안 보인 값의 수 → 그 무리에서 생성 쪽이 고를 수 있게 보인 값의 수
                (choice_values_shown_in_original → choice_values_selectable, reveal 뒤 포함)
  reveal 한 선택지 무리   흐름 명세의 reveal 중 oos- 가 아닌 것
"""
import io
import json
import os
import sys


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def final_attempt(summary):
    if summary.get("final"):
        return summary["final"]["attempt"]
    return summary["attempts"][-1]["n"]


def plan_of(run, n):
    """그 시도의 계획. 시도마다 남지 않았으면 그 앞의 가장 가까운 것."""
    for k in range(n, 0, -1):
        path = os.path.join(run, "attempt_%d.plan.json" % k)
        if os.path.exists(path):
            return load(path)
    return {}


def visit(v):
    return (v or "").split("#")[0]


def row(run):
    summary = load(os.path.join(run, "summary.json"))
    n = final_attempt(summary)
    m = load(os.path.join(run, "attempt_%d.audit.json" % n))["metrics"]
    came = {sc["name"]: set(sc.get("from") or [])
            for sc in plan_of(run, n).get("screens") or []}
    ed = [d for d in m.get("entrance_distance") or [] if d.get("original") and d.get("build")]
    folded = [d for d in ed
              if (d["build"].get("reveal") or 0) > (d["original"].get("reveal") or 0)]
    moved = [d for d in ed
             if visit(d["original"]["visit"]) not in came.get(visit(d["build"]["visit"]), set())]
    ds = [(d["build"].get("scroll_px") or 0) - (d["original"].get("scroll_px") or 0) for d in ed]
    shown = m.get("choice_values_shown_in_original") or {}
    sel = m.get("choice_values_selectable") or {}
    groups = [a for a in m.get("reveal") or {} if not a.startswith("oos-")]
    return [os.path.basename(os.path.normpath(run)),
            ((summary.get("git") or {}).get("commit") or "?")[:7],
            "%s/%s" % (m.get("entrances_kept"), m.get("entrances_original")),
            str(len(folded)), str(len(moved)),
            "%+d · %+d" % (round(sum(ds) / len(ds)), max(ds)) if ds else "-",
            "%d → %d" % (sum(shown.values()), sum(sel.get(a, 0) for a in shown)),
            ", ".join(groups) or "-"]


HEAD = ["실행", "커밋", "입구", "펼침 뒤로", "다른 화면", "스크롤 평균·최대",
        "선택지 원본에 보임 → 생성에서 고를 수 있음", "reveal 한 선택지 무리"]


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    print("| %s |" % " | ".join(HEAD))
    print("|%s" % ("---|" * len(HEAD)))
    for run in argv:
        print("| %s |" % " | ".join(row(run)))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
