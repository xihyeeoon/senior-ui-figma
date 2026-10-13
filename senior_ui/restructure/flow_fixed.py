r"""흐름 고정 검사 (검사 M, 2026-10-13) - 생성물의 정답 경로가 원본의 화면 차례를 그대로 밟는가.

재설계를 두 단계로 나눈다 - ① 흐름 단축 → ② 레이아웃 재구성. `--mode layout` 이 ② 이고,
프롬프트에 "이 단계에서 고정하는 것은 흐름뿐이다 …" (docs/restructure-prompt.md 의 FLOW_FIXED,
두 줄) 를 넣는다. 이 검사는 그 문장이 지켜졌는지 본다. `--mode layout` 에서는 fatal, `--mode full`
에서는 기록만 한다 (검사 리포트의 metrics.flow_fixed) - 앞 실행들이 흐름을 얼마나 바꿨는지도
같은 잣대로 잴 수 있게.

브라우저를 띄우지 않는다. 읽는 것은 셋이다.

    원본    과제의 원본 흐름 (tasks/<과제>.json 의 flow) 의 steps
    생성물  모델이 쓴 흐름 명세의 steps
    계획    plan.screens[].from - 생성 화면이 어느 원본 화면에서 왔나

판정:

    1. 두 흐름의 steps 를 **처음 닿은 차례** 의 화면 이름 목록으로 줄인다. 같은 화면에 머문
       걸음 (원본의 "키패드 열림" 처럼 상태만 바뀐 걸음) 과 이미 지난 화면으로 돌아온 걸음
       (은행 시트를 닫고 계좌 화면으로) 은 새 화면이 아니다. 원본 흐름은 돌아온 걸음을 적지
       않는다 - 같은 길을 적은 생성 흐름이 그 걸음을 적었다고 떨어지지 않게 하려는 것이다.
    2. 생성 화면마다 계획의 from 에서 `err-` 로 시작하는 이름을 뺀다 (오류 화면은 그 화면에
       합쳐도 된다). 남은 것이 원본 화면 하나면 그 화면이다 (이름만 바뀐 화면).
       둘 이상이면 화면을 합친 것, 없으면 원본에 없던 화면, 계획에 없는 화면이면 맞출 수 없다.
    3. 맞춘 목록이 원본 목록과 같아야 한다 - 화면 수 (걸음 수 = 화면 수 - 1) 와 차례가 모두.
       한 원본 화면을 두 생성 화면으로 나누면 같은 원본 이름이 두 번 나오므로 여기서 걸린다.

오류 경로는 보지 않는다 - 오류를 어디서 어떻게 알리는지는 화면 배치의 일이다 (FLOW_FIXED 의
마지막 문장).
"""
import json

from senior_ui import tasks as T

from .prompt import load_block

# 리포트의 fatal 에 붙는 검사 이름. 검사기(senior_ui/audit)의 A~L 다음 글자다 - 검사기 밖에서
# 붙이지만 리포트 · 재시도 블록 · 막힘 판정은 다른 fatal 과 같은 모양으로 읽는다.
CHECK = "M"
ERROR_PREFIX = "err-"


def rule_sentence():
    """FLOW_FIXED 블록의 문장 - 프롬프트에 넣은 것과 글자까지 같다. 블록의 줄마다 앞의 "- " 를
    떼고 한 줄로 잇는다 (안내문은 한 줄이다 - 재시도 블록의 failure_line)."""
    lines = [ln.strip() for ln in load_block("FLOW_FIXED").splitlines() if ln.strip()]
    return " ".join(ln[2:] if ln.startswith("- ") else ln for ln in lines)


def original_steps(task=None):
    """과제의 원본 흐름의 steps."""
    with open(T.abs_path(T.load_task(task)["flow"]), encoding="utf-8") as f:
        return json.load(f).get("steps") or []


def first_visits(steps):
    """steps 의 화면 이름을 처음 닿은 차례로 (겹치지 않게). 이름이 없는 걸음은 건너뛴다."""
    out = []
    for st in steps or []:
        name = st.get("screen") if isinstance(st, dict) else None
        if isinstance(name, str) and name and name not in out:
            out.append(name)
    return out


def origin_of(name, came):
    """생성 화면 하나의 원본 화면. `(원본 이름 또는 None, 문제 또는 None)`."""
    if name not in came:
        return None, "계획에 없는 화면 %s" % name
    froms = [s for s in came[name] if isinstance(s, str) and not s.startswith(ERROR_PREFIX)]
    if len(froms) == 1:
        return froms[0], None
    if not froms:
        return None, "원본에 없던 화면 %s (계획의 from 이 비었다)" % name
    return None, "원본 화면 %s 를 합친 화면 %s" % (" + ".join(froms), name)


def judge(orig_steps, built_steps, plan):
    """흐름 고정 판정. 돌려주는 것 (metrics.flow_fixed 그대로):

        same            원본과 같은 화면 차례인가
        original        원본의 화면 차례 (처음 닿은 차례)
        built           생성물의 화면 차례 (생성 이름)
        mapped          생성물의 화면 차례를 계획의 from 으로 원본 이름에 맞춘 것 (맞출 수 없는
                        화면은 그 생성 이름 앞에 "?")
        original_moves · built_moves   걸음 수 (화면 수 - 1)
        original_steps · built_steps   흐름 명세의 steps 수 (기록만 - 같은 화면 안의 걸음도 센다)
        problems        같지 않은 까닭, 사람이 읽는 글
    """
    came = {sc.get("name"): list(sc.get("from") or [])
            for sc in (plan or {}).get("screens") or [] if isinstance(sc, dict)}
    orig = first_visits(orig_steps)
    built = first_visits(built_steps)
    mapped, problems = [], []
    for name in built:
        o, why = origin_of(name, came)
        mapped.append(o if o else "?" + name)
        if why:
            problems.append(why)
    split = sorted({o for o in mapped if not o.startswith("?") and mapped.count(o) > 1})
    for o in split:
        problems.append("원본 화면 %s 를 나눈 화면 %s" % (
            o, " · ".join(b for b, m in zip(built, mapped) if m == o)))
    gone = [o for o in orig if o not in mapped]
    if gone:
        problems.append("정답 경로에서 빠진 원본 화면 %s" % " · ".join(gone))
    if len(built) != len(orig):
        problems.append("걸음 수가 다르다 (원본 %d · 생성물 %d)"
                        % (len(orig) - 1, max(len(built) - 1, 0)))
    if not problems and mapped != orig:
        problems.append("화면 차례가 다르다")
    return {"same": not problems and mapped == orig,
            "original": orig, "built": built, "mapped": mapped,
            "original_moves": max(len(orig) - 1, 0), "built_moves": max(len(built) - 1, 0),
            "original_steps": len(orig_steps or []), "built_steps": len(built_steps or []),
            "problems": problems}


def detail(result):
    """fatal 의 안내문. 무엇이 다른지, 그리고 프롬프트의 흐름 고정 문장 그대로."""
    mapped = ("" if result["mapped"] == result["built"]
              else ", 계획의 from 으로 원본 이름에 맞추면 %s" % " → ".join(result["mapped"]))
    return ("정답 경로의 화면 차례가 원본과 다르다: %s. 원본 %s (걸음 %d) · 생성물 %s (걸음 %d%s). "
            "%s 화면 이름은 바꿔도 된다 - 계획의 screens[].from 에 원본 화면 하나를 적으면 된다. "
            "계획을 고쳐야 하면 반성의 plan_changes 에 적어라."
            % ("; ".join(result["problems"]), " → ".join(result["original"]),
               result["original_moves"], " → ".join(result["built"]), result["built_moves"],
               mapped, rule_sentence()))


def apply(report, result, mode):
    """검사 리포트에 판정을 붙인다. layout 이면 같지 않을 때 fatal 하나를 더하고 통과를 거둔다.
    full 이면 metrics 에 기록만 한다. 리포트를 그 자리에서 고치고 돌려준다."""
    m = report.setdefault("metrics", {})
    m["flow_fixed"] = dict(result, mode=mode, judged=(mode == "layout"))
    if mode != "layout" or result["same"]:
        return report
    report.setdefault("fatal", []).append({
        "check": CHECK, "screen": None, "detail": detail(result),
        # 재시도 블록이 이 안내문을 줄이지 않는다 (prompt.retry_block) - 끝의 문장이 안내다
        "keep_detail": True})
    report["passed"] = False
    for key in ("fatal_total", "fatal_root"):
        if isinstance(m.get(key), int):
            m[key] += 1
    return report
