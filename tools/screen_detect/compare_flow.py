r"""흐름 추정(flow.py)을 원본 재현 HTML 의 실제 연결과 견준다 (스크린샷 입력 시험 D4).

    $py = "C:\Users\xihye\venvs\detect\Scripts\python.exe"
    & $py tools/screen_detect/truth.py --out results/detect/<날짜>-d4/truth.json   # timeline 이 든 판
    & $py tools/screen_detect/compare_flow.py --dir results/detect/<날짜>-d4

정답: truth.json 의 timeline - 원본을 원본 흐름(flows/original.json)대로 걸으며 도착한 상태와 누른 것을
순서대로 적은 것 (오류 경로는 따로). 캡처의 이름표(label)를 정답의 상태로 옮기고(state_of), 캡처 짝 사이에
실제로 누른 것을 찾는다 (truth_pair):

  - 뒤 캡처가 오류 상태   → error_path. 앞 캡처의 상태가 그 오류 경로가 갈라지는 상태면 누른 것은 그
                            경로의 첫 누름, 아니면 없음 (앞 캡처에서 그 오류로 가는 누름이 없다)
  - 같은 상태 · 둘 다 "스크롤" → scroll, 누른 것 없음
  - 그 밖                 → 앞 상태의 마지막 도착부터 뒤 상태의 첫 도착까지 누른 것. 하나(숫자 키 하나 포함)
                            이고 사이에 다른 상태가 없으면 tap, 아니면 skipped (값 넣기는 키 수만큼 누른 것).
                            같은 상태의 다른 모습(입력 전 · 입력 중)은 그 상태의 첫 도착부터 마지막 도착까지

맞음:
  누른 것 - 정답에 누른 것이 없으면 추정도 null 이어야 맞다. 정답의 첫 누름이 숫자 키(또는 값 넣기)면 추정한
            요소가 숫자판 키(의미 층 kind keypad_key, 또는 한두 자리 숫자)면 맞다 - 정답의 값(32000 ·
            비밀번호)과 더미앱의 값(10000)이 달라 글로는 견줄 수 없다. 그 밖에는 글로 - 공백 · 기호를 뺀 글이
            정답의 글 · aria-label 과 비슷함 0.8 이상이거나 한쪽이 다른 쪽을 품으면 맞다.
  kind   - 같으면 맞다.

쓰는 것: <dir>/summary.md, <dir>/compare_flow.json.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import compare as C  # noqa: E402
import flow as F  # noqa: E402

BUCKETS = [(0.0, 0.5), (0.5, 0.8), (0.8, 1.01)]
LOW = 0.8             # "낮은 confidence" 의 경계 - 이 아래


def state_of(label, states):
    """연구자의 이름표 → 정답의 상태 이름.

    "원본 오류 상태 <id> …" → error:<id>. "원본 화면 <방문> …" → 그 방문. 이름표가 "[증권사] 탭" 이면
    <방문>+tab-sec (흐름 밖 걸음). 이름표가 "… 입력" · "… 입력 중" 으로 끝나는 모습(값을 넣은 뒤 아직 그
    화면)이면 그 방문 뒤 같은 화면에 머문 마지막 상태 (금액을 넣은 금액 화면 = confirm~1), 없으면 그 방문."""
    m = re.match(r"원본 오류 상태 (\S+)", label)
    if m:
        return "error:" + m.group(1)
    m = re.match(r"원본 화면 (\S+)", label)
    if not m:
        return None
    v = m.group(1)
    names = [s["state"] for s in states]
    if "[증권사]" in label and v + "+tab-sec" in names:
        return v + "+tab-sec"
    tail = label.split("—")[-1].strip()
    if re.search(r"입력( 중)?$", tail) and v in names:
        screen = states[names.index(v)]["screen"]
        after = [s["state"] for s in states[names.index(v) + 1:] if s["screen"] == screen
                 and "~" in s["state"]]
        return after[-1] if after else v
    return v if v in names else None


def presses(events):
    """도착 사이의 누름 [{text, aria, key, action, n}] - type 은 키 n 개."""
    out = []
    for e in events:
        if "press" in e:
            out.append({"action": e["press"], "text": e.get("text"), "aria": e.get("aria"),
                        "img": e.get("img"), "key": bool(e.get("key")), "n": 1})
        elif "type" in e:
            out.append({"action": "type", "text": e["type"], "aria": None, "img": None, "key": True,
                        "n": e["presses"]})
    return out


def truth_pair(a_label, b_label, A, B, tl):
    """캡처 짝의 정답 {kind, first (첫 누름 또는 None), presses, between}."""
    main = tl["main"]
    if B and B.startswith("error:"):
        log = tl.get(B, [])
        start = log[0]["arrive"] if log and "arrive" in log[0] else None
        ps = presses(log[:next((i for i, e in enumerate(log) if e.get("arrive") == B), len(log))])
        first = ps[0] if A == start and ps else None
        return {"kind": "error_path", "first": first, "presses": sum(p["n"] for p in ps),
                "note": "오류 경로 %s (갈라지는 상태 %s)" % (B, start)}
    arr = [(i, e["arrive"]) for i, e in enumerate(main) if "arrive" in e]
    if A == B:
        if "스크롤" in a_label and "스크롤" in b_label:
            return {"kind": "scroll", "first": None, "presses": 0, "note": "같은 상태"}
        idx = [i for i, s in arr if s == A]
        seg = main[idx[0] + 1:idx[-1]]
    else:
        jb = next((i for i, s in arr if s == B), None)
        ia = max((i for i, s in arr if s == A and (jb is None or i < jb)), default=None)
        if ia is None or jb is None:
            return {"kind": "unknown", "first": None, "presses": 0, "note": "정답 걸음에서 짝을 못 찾음"}
        seg = main[ia + 1:jb]
    ps = presses(seg)
    between = [e["arrive"] for e in seg if "arrive" in e and e["arrive"] not in (A, B)]
    n = sum(p["n"] for p in ps)
    kind = "tap" if n == 1 and not between else "skipped"
    return {"kind": kind, "first": ps[0] if ps else None, "presses": n,
            "note": "누름 %d번%s" % (n, (" · 사이 상태 " + ", ".join(between)) if between else "")}


def is_key(text, role):
    return (role or {}).get("kind") == "keypad_key" or bool(re.fullmatch(r"\d{1,2}", (text or "").strip()))


def tap_right(p, t, roles):
    first = t["first"]
    if first is None:
        return p["tap"] is None
    if p["tap"] is None:
        return False
    if first["key"]:
        return is_key(p["tap_text"], roles.get(p["tap"]))
    got = C.norm(p["tap_text"])
    for want in (first.get("text"), first.get("aria"), first.get("img")):
        w = C.norm(want)
        if w and got and (C.ratio(w, got) >= C.FOUND or w in got or got in w):
            return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="flow.py 의 결과 폴더 (truth.json 을 함께 둔다)")
    ap.add_argument("--truth", help="정답지 (기본 <dir>/truth.json)")
    a = ap.parse_args(argv)
    res = json.load(io.open(os.path.join(a.dir, "flow.proposed.json"), encoding="utf-8"))
    truth = json.load(io.open(a.truth or os.path.join(a.dir, "truth.json"), encoding="utf-8"))
    # 채점 쪽 - 스크린샷만(strict) 실행은 captures.json 을 읽지 않았으므로 짝짓기용 이름표를 기본 자리에서 읽는다
    ref, path = res["captures"].split(":", 1) if res.get("captures") else (F.CAPTURES_REF, F.CAPTURES_PATH)
    caps = F.read_captures(ref, path)
    label = {im["file"]: im["label"] for im in caps["images"]}
    units = C.load_units(os.path.join(ROOT, res["elements"]))
    umap = F.unit_of(units)
    roles = {}
    for u in units:
        r = json.load(io.open(os.path.join(ROOT, res["roles"], u + ".semantic.json"), encoding="utf-8"))
        roles.update({e["id"]: e for e in r["elements"] or []})
    st = truth["states"]
    rows = []
    for p in res["pairs"] or []:
        A, B = state_of(label[p["from"]], st), state_of(label[p["to"]], st)
        t = truth_pair(label[p["from"]], label[p["to"]], A, B, truth["timeline"])
        rows.append(dict(p, state_from=A, state_to=B, truth=t,
                         tap_ok=tap_right(p, t, roles), kind_ok=p["kind"] == t["kind"]))
    n = len(rows)
    tot = {"pairs": n, "tap_ok": sum(r["tap_ok"] for r in rows),
           "kind_ok": sum(r["kind_ok"] for r in rows),
           "both_ok": sum(r["tap_ok"] and r["kind_ok"] for r in rows)}
    buckets = []
    for lo, hi in BUCKETS:
        rs = [r for r in rows if isinstance(r["confidence"], (int, float)) and lo <= r["confidence"] < hi]
        buckets.append({"range": "%.1f~%.1f" % (lo, min(hi, 1.0)), "n": len(rs),
                        "wrong": sum(not (r["tap_ok"] and r["kind_ok"]) for r in rs)})
    low = [r for r in rows if r["confidence"] < LOW]
    tot["low_wrong"] = [sum(not (r["tap_ok"] and r["kind_ok"]) for r in low), len(low)]
    high = [r for r in rows if r["confidence"] >= LOW]
    tot["high_wrong"] = [sum(not (r["tap_ok"] and r["kind_ok"]) for r in high), len(high)]

    def show(first):
        if not first:
            return "-"
        if first["key"]:
            return "숫자 키" + (" (값 넣기)" if first["action"] == "type" else "")
        return "%s (%s)" % (first.get("text") or first.get("aria") or first.get("img"), first["action"])
    ok = lambda b: "맞음" if b else "**틀림**"
    md = ["# 흐름 추정 시험 D4 (%s)\n" % os.path.basename(a.dir.rstrip("/\\")),
          "캡처 순서와 이름표(`%s`), 요소(`%s`)와 의미 층 역할(`%s`)로 모델(`%s`, reasoning %s)이 캡처 짝마다 "
          "누른 것을 추정했다. 보낸 것: %s. 프롬프트 `%s` (%s). 상태 %s · 시도 %d · 쓴 돈 $%.4f.\n"
          % (res["captures"], res["elements"], res["roles"], res["model"], res["reasoning_effort"],
             res["sent"], res["prompt_file"], res["prompt_sha"], res["status"], len(res["attempts"]),
             res.get("cost_usd") or 0),
          "정답: 원본 재현 HTML 을 원본 흐름대로 걸은 timeline (`truth.json`). 이름표 → 상태, 짝 사이에 실제로 "
          "누른 것 (compare_flow.py 머리말).\n",
          "## 합계\n",
          C.table(["항목", "값"], [
              ["누른 것 맞음", "%d/%d" % (tot["tap_ok"], n)],
              ["kind 맞음", "%d/%d" % (tot["kind_ok"], n)],
              ["둘 다 맞음", "%d/%d" % (tot["both_ok"], n)],
              ["confidence < %.1f 에서 틀린 짝" % LOW, "%d/%d" % tuple(tot["low_wrong"])],
              ["confidence ≥ %.1f 에서 틀린 짝" % LOW, "%d/%d" % tuple(tot["high_wrong"])]]),
          "\n" + C.table(["confidence", "짝", "틀린 짝"], [[b["range"], b["n"], b["wrong"]] for b in buckets]),
          "\n## 짝마다 (연구자 검토용)\n",
          C.table(["짝", "상태", "추정: 누른 것 (글)", "kind", "conf", "정답: 누른 것", "정답 kind",
                   "누른 것", "kind", "근거"],
                  [["%s → %s" % (r["from"][:-4], r["to"][:-4]), "%s → %s" % (r["state_from"], r["state_to"]),
                    "%s (%s)" % (r["tap_text"], r["tap"]) if r["tap"] else "-", r["kind"],
                    "%.2f" % r["confidence"], show(r["truth"]["first"]),
                    "%s · %s" % (r["truth"]["kind"], r["truth"]["note"]), ok(r["tap_ok"]), ok(r["kind_ok"]),
                    r.get("reason") or ""] for r in rows])]
    if res.get("attempts"):
        md.append("\n## 토큰 · 비용\n")
        md.append(C.table(["시도", "입력 토큰", "출력 토큰 (생각)", "비용 USD", "문제"],
                          [[x["n"], (x["usage"] or {}).get("prompt"),
                            "%s (%s)" % ((x["usage"] or {}).get("completion"), (x["usage"] or {}).get("reasoning")),
                            "%.4f" % (x["cost_usd"] or 0), "; ".join(x["problems"]) or "-"]
                           for x in res["attempts"]]))
    with io.open(os.path.join(a.dir, "summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    with io.open(os.path.join(a.dir, "compare_flow.json"), "w", encoding="utf-8") as f:
        json.dump({"totals": tot, "buckets": buckets, "pairs": rows}, f, ensure_ascii=False, indent=1)
    print("누른 것 %d/%d · kind %d/%d · 둘 다 %d/%d" % (tot["tap_ok"], n, tot["kind_ok"], n, tot["both_ok"], n))


if __name__ == "__main__":
    main()
