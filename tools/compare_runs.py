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
  재현본 탓 표현  진단 (계획을 세운 시도의 attempt_N.diagnosis.json) 전문에서 REPLICA_WORDS 의 낱말을
                센 합과 낱말별 수. 렌더 그림은 사람이 만든 재현본이라 아이콘이 회색 네모다 - 그것을
                근거로 쓴 진단을 세려는 것이다. 한 번 센 글자를 다시 세지 않는 것은 아니다 ("빈 상자"
                는 "상자" 에도 든다 - E 보고 7절의 비교 명령과 같은 세기)
  원본 순서 같음 (요소 · 무리, 화면 평균 · 최저)
                정답 경로 화면마다 원본과 생성의 짝지은 누를 수 있는 요소 · 무리의 위→아래 순서가
                같은 정도 (최장 공통 부분열 / 짝지은 수, 1 이면 같다) 의 화면 평균과 최저.
                senior_ui/storyboard/likeness.py - 짝짓기 · 무리 나누기 규칙은 거기 머리말. 원본 쪽은
                REFERENCE 의 원본 화면설계서다. 기록만 한다 (판정에 쓰지 않는다)
  격자·탭 (원본에도 · 새로 · 없어짐)
                같은 화면들에서 격자 · 탭 단위를 원본에도 있음 · 새로 생김 · 원본에 있었는데 없어짐으로
                나눈 수의 합. 판정 규칙은 likeness.py 머리말 ("격자 · 탭 판정")

  --screens 를 주면 표 아래에 실행마다 화면별 표를 하나씩 더 찍는다.
"""
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from senior_ui.restructure import flow_fixed as FF  # noqa: E402
from senior_ui.storyboard import likeness as LK  # noqa: E402

# 과제마다 원본을 빌드로 둔 화면설계서 (tools/reference_storyboard.py) - 원본 닮음의 원본 쪽
REFERENCE = {"transfer": os.path.join(ROOT, "results", "reference", "original-transfer",
                                      "storyboard", "storyboard.json")}


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


# 재현본 탓 표현 - E 보고 (2026-10-12) 7절의 비교 명령에 있던 목록에서 "회색" 을 뺐다
# (2026-10-13). 실행 20261013-130053 의 "회색" 8건은 모두 글자색 ("작은 회색 글씨" · "회색 다음
# 버튼") 이고 재현본 탓이 아니었다.
REPLICA_WORDS = ["네모", "사각형", "그림만", "아이콘만", "X 표", "X표", "엑스", "자리표시", "빈 상자",
                 "상자", "기능명이 없", "이름이 없", "알 수 없는 그림", "같은 모양"]


def diagnosis_of(run):
    """계획을 세운 시도의 진단 (가장 앞 시도의 것, 보통 시도 1). 없으면 None."""
    found = [int(m.group(1)) for m in
             (re.match(r"attempt_(\d+)\.diagnosis\.json$", f) for f in os.listdir(run)) if m]
    return load(os.path.join(run, "attempt_%d.diagnosis.json" % min(found))) if found else None


def replica_words(run):
    """진단 전문에서 REPLICA_WORDS 의 수. "합 n (낱말 수 · …)", 진단이 없으면 "-"."""
    diag = diagnosis_of(run)
    if diag is None:
        return "-"
    text = json.dumps(diag, ensure_ascii=False)
    counts = [(w, text.count(w)) for w in REPLICA_WORDS if text.count(w)]
    total = sum(c for _w, c in counts)
    return "%d (%s)" % (total, " · ".join("%s %d" % wc for wc in counts)) if counts else "0"


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


def likeness(run, summary, came, reference=None):
    """원본 닮음 (likeness.run_report). 원본 · 실행의 화면설계서가 없으면 None."""
    task = summary.get("task") or "transfer"
    ref = reference or REFERENCE.get(task)
    built = os.path.join(run, "storyboard", "storyboard.json")
    if not ref or not os.path.exists(ref) or not os.path.exists(built):
        return None
    return LK.run_report(load(ref), load(built), came,
                         FF.first_visits(FF.original_steps(task)))


def _num(v):
    return "-" if v is None else "%.2f" % v


def likeness_cells(rep):
    """표의 두 칸 - 순서 같음 (요소 · 무리의 평균 · 최저), 격자·탭 (원본에도 · 새로 · 없어짐)."""
    if rep is None:
        return ["-", "-"]
    s = rep["summary"]
    order = "요소 %s · %s / 무리 %s · %s" % (_num(s["elements"]["mean"]), _num(s["elements"]["min"]),
                                         _num(s["blocks"]["mean"]), _num(s["blocks"]["min"]))
    units = " / ".join("%s %d · %d · %d" % (name, s["units"][k]["kept"], s["units"][k]["new"],
                                            s["units"][k]["gone"])
                       for k, name in (("grid", "격자"), ("tab", "탭")))
    return [order, units]


def screen_table(run, rep):
    """실행 하나의 화면별 원본 닮음 표 (마크다운 줄들)."""
    name = os.path.basename(os.path.normpath(run))
    if rep is None:
        return ["%s: 화면설계서가 없다" % name]
    out = ["%s" % name, "",
           "| 화면 (생성) | 짝 | 요소 순서 같음 | 무리 순서 같음 | 격자 원본에도 · 새로 · 없어짐 "
           "| 탭 원본에도 · 새로 · 없어짐 | 안쪽을 못 잰 무리 |", "|---|---|---|---|---|---|---|"]
    for r in rep["screens"]:
        u = r["units"]
        out.append("| %s%s | %d | %s | %s | %d · %d · %d | %d · %d · %d | %s |" % (
            r["screen"], "" if r["built"] == r["screen"] else " (%s)" % r["built"], r["paired"],
            _num(r["elements"]), _num(r["blocks"]), u["grid"]["kept"], u["grid"]["new"],
            u["grid"]["gone"], u["tab"]["kept"], u["tab"]["new"], u["tab"]["gone"],
            ", ".join(r["unmeasured"]) or "-"))
    if rep["missing"]:
        out.append("")
        out.append("견주지 못한 원본 화면: %s" % ", ".join(rep["missing"]))
    return out


def row(run, reports=None):
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
            summary.get("mode") or "full", flow_fixed(run, summary, m), replica_words(run)]         + likeness_cells(_keep(reports, run, likeness(run, summary, came)))


def _keep(reports, run, rep):
    if reports is not None:
        reports[run] = rep
    return rep


HEAD = ["실행", "커밋", "입구", "펼침 뒤로", "다른 화면", "모인 화면", "가리키는 버튼",
        "스크롤 평균·최대", "선택지 원본에 보임 → 생성에서 고를 수 있음", "reveal 한 선택지 무리",
        "단계", "흐름 고정", "재현본 탓 표현",
        "원본 순서 같음 (요소 · 무리, 화면 평균 · 최저)", "격자·탭 (원본에도 · 새로 · 없어짐)"]


def main(argv):
    screens = "--screens" in argv
    argv = [a for a in argv if a != "--screens"]
    if not argv:
        print(__doc__.strip())
        return 2
    reports = {}
    print("| %s |" % " | ".join(HEAD))
    print("|%s" % ("---|" * len(HEAD)))
    for run in argv:
        print("| %s |" % " | ".join(row(run, reports)))
    print()
    print("스크롤은 생성 쪽에서 입구가 있는 화면 안에서 잰 값이다 (옮겼으면 옮긴 화면 기준).")
    if screens:
        for run in argv:
            print()
            print("\n".join(screen_table(run, reports.get(run))))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
