r"""재구성 실행끼리 과제 밖 입구 거리 · 선택지 수를 나란히 놓는다.

판정이 아니라 기록용이다 - 합격선 · 기준선을 두지 않는다.

    python tools/compare_runs.py <실행 폴더> [<실행 폴더> …]

실행 폴더는 results/runs/<id> 든 outputs/restructure_auto/<id> 든 된다. 결과는 마크다운
표 하나다. 최종 시도(summary 의 final.attempt, 없으면 마지막 시도)의 audit · plan 을 읽는다.

  입구          검사 K 가 남긴 입구 / 원본에서 보인 입구
  펼침 뒤로     생성 쪽 펼치기(reveal) 횟수가 원본보다 많은 입구 수
  다른 화면     입구를 원본에서 본 화면 o 와 생성에서 본 화면 b ('#' 앞) 가 다른 입구 수.
                b == o 이거나 b 의 plan.screens[].from 이 정확히 [o] 하나면(이름만 바뀐 화면,
                예 confirm → review) 옮기지 않은 것으로 본다. from 에서 이름이 err- 로 시작하는
                화면은 빼고 본다 (예 review 의 from ['confirm', 'err-bank'] → ['confirm'])
  모인 화면     옮긴 입구가 가장 많이 간 생성 화면과 그 수 (예 services 22)
  가리키는 버튼 "n/옮긴 수 · 묶음 m/옮긴 수". 옮긴 입구 가운데, o 에 해당하는 생성 장
                (sheet.screen 이 o 이거나 o 에서 이름만 바뀐 화면)에 result 가 화면 b 로 가는
                요소가 있는 수. 글(text, 없으면 aria)이 입구 label 과 같거나 action 이 입구
                action 과 같으면 n 에, 그런 요소는 없고 다른 요소(예 '다른 서비스 보기' ·
                '전체메뉴' · 탭)만 b 로 가면 묶음 입구로 이어짐으로 m 에 센다.
                storyboard/storyboard.json 이 없으면 -
  스크롤        입구마다 (생성 scroll_px - 원본 scroll_px) 의 평균 · 최대. 생성 쪽은 입구가 있는
                화면 안에서 잰 값이다 (옮겼으면 옮긴 화면 기준)
  선택지        원본을 걷는 동안 보인 값의 수 → 그 무리에서 생성 쪽이 고를 수 있게 보인 값의 수
                (choice_values_shown_in_original → choice_values_selectable, reveal 뒤 포함)
  reveal 한 선택지 무리   흐름 명세의 reveal 중 oos- 가 아닌 것
  단계          summary 의 mode (칸이 없으면 full - --mode 가 생기기 전의 실행도 full 이다)
  흐름 고정     생성물의 정답 경로가 원본의 화면 차례를 그대로 밟는가 (검사 M,
                senior_ui/restructure/flow_fixed.py). 감사 지표 flow_fixed 가 있으면 그것을, 없으면
                (그 검사가 생기기 전의 실행) 같은 판정을 그 시도의 흐름 명세 · 계획으로 다시 한다.
                "같다" 또는 "다르다 (까닭)"
"""
import collections
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from senior_ui.restructure import flow_fixed as FF  # noqa: E402


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


def renamed(came, b, o):
    """생성 화면 b 가 원본 화면 o 그대로이거나 o 에서 이름만 바뀐 화면인가 (from 의 err- 는 뺀다)."""
    return b == o or [f for f in came.get(b) or [] if not f.startswith("err-")] == [o]


def moved_entrances(run):
    """(summary, 감사 지표, 입구 거리, 그중 다른 화면으로 옮긴 것, 생성 화면 → plan from)."""
    summary = load(os.path.join(run, "summary.json"))
    n = final_attempt(summary)
    m = load(os.path.join(run, "attempt_%d.audit.json" % n))["metrics"]
    came = {sc["name"]: list(sc.get("from") or [])
            for sc in plan_of(run, n).get("screens") or []}
    ed = [d for d in m.get("entrance_distance") or [] if d.get("original") and d.get("build")]
    moved = [d for d in ed
             if not renamed(came, visit(d["build"]["visit"]), visit(d["original"]["visit"]))]
    return summary, m, ed, moved, came


def storyboard_sheets(run):
    path = os.path.join(run, "storyboard", "storyboard.json")
    return load(path).get("sheets") or [] if os.path.exists(path) else None


def pointing(sheets, came, d):
    """옮긴 입구 d 를 원래 화면에서 옮긴 화면 b 로 보내는 요소.

    "same" 같은 글이나 같은 action 의 요소가 있다, "bundle" 그런 것은 없고 다른 요소만 b 로
    간다 (묶음 입구로 이어짐), 둘 다 없으면 None."""
    o, b = visit(d["original"]["visit"]), visit(d["build"]["visit"])
    found = None
    for sheet in sheets:
        if not renamed(came, sheet.get("screen"), o):
            continue
        for it in sheet.get("items") or []:
            res = it.get("result") or {}
            if res.get("kind") != "screen" or res.get("to") != b:
                continue
            if ((it.get("text") or it.get("aria")) == d["label"]
                    or (it.get("action") and it.get("action") == d.get("action"))):
                return "same"
            found = "bundle"
    return found


def flow_fixed(run, summary, m):
    """흐름 고정 판정 - 감사 지표에 있으면 그것, 없으면 그 시도의 흐름 명세 · 계획으로 다시."""
    got = m.get("flow_fixed")
    if got is None:
        n = final_attempt(summary)
        steps = load(os.path.join(run, "attempt_%d.flow.json" % n)).get("steps") or []
        got = FF.judge(FF.original_steps(summary.get("task")), steps, plan_of(run, n))
    return "같다" if got["same"] else "다르다 (%s)" % "; ".join(got["problems"])


def row(run):
    summary, m, ed, moved, came = moved_entrances(run)
    folded = [d for d in ed
              if (d["build"].get("reveal") or 0) > (d["original"].get("reveal") or 0)]
    gathered = collections.Counter(visit(d["build"]["visit"]) for d in moved).most_common(1)
    sheets = storyboard_sheets(run)
    kinds = [] if sheets is None else [pointing(sheets, came, d) for d in moved]
    ds = [(d["build"].get("scroll_px") or 0) - (d["original"].get("scroll_px") or 0) for d in ed]
    shown = m.get("choice_values_shown_in_original") or {}
    sel = m.get("choice_values_selectable") or {}
    groups = [a for a in m.get("reveal") or {} if not a.startswith("oos-")]
    return [os.path.basename(os.path.normpath(run)),
            ((summary.get("git") or {}).get("commit") or "?")[:7],
            "%s/%s" % (m.get("entrances_kept"), m.get("entrances_original")),
            str(len(folded)), str(len(moved)),
            "%s %d" % gathered[0] if gathered else "-",
            "-" if sheets is None
            else "%d/%d · 묶음 %d/%d" % (kinds.count("same"), len(moved),
                                         kinds.count("bundle"), len(moved)),
            "%+d · %+d" % (round(sum(ds) / len(ds)), max(ds)) if ds else "-",
            "%d → %d" % (sum(shown.values()), sum(sel.get(a, 0) for a in shown)),
            ", ".join(groups) or "-",
            summary.get("mode") or "full", flow_fixed(run, summary, m)]


HEAD = ["실행", "커밋", "입구", "펼침 뒤로", "다른 화면", "모인 화면", "가리키는 버튼",
        "스크롤 평균·최대", "선택지 원본에 보임 → 생성에서 고를 수 있음", "reveal 한 선택지 무리",
        "단계", "흐름 고정"]


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    print("| %s |" % " | ".join(HEAD))
    print("|%s" % ("---|" * len(HEAD)))
    for run in argv:
        print("| %s |" % " | ".join(row(run)))
    print()
    print("스크롤은 생성 쪽에서 입구가 있는 화면 안에서 잰 값이다 (옮겼으면 옮긴 화면 기준).")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
