r"""채점 - "스크린샷만" (--inputs strict, 2026-10-19) 실행을 옛 판과 견준다. 사람 파일을 읽는 채점 쪽이다
(strict 를 켜지 않는다).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/strict_report.py
        → results/detect/20261019-strict/summary.md

1. 이어 붙이기 자동 판정 - strict/groups.json (설정 A · B · C) 과 stitch.GROUPS
2. 흐름 D4 - 20261013-d4 (이름표 있음) 대 20261019-strict/flow (이름표 없음), 짝마다 정답 (compare_flow.json)
3. 의미 층 - 20261013-d3b (v1 + 로고 규칙 고정 이름) 대 20261019-strict/semantic (v2, 규칙 없음), 홈 · 은행.
   바뀐 요소 (kind 가 바뀌었거나 v2 칸이 찬 것), 그림 이름이 정답(aria-label)과 같은 수 - 정답 그림 자리마다 닿은
   요소(compare.judge_capture, 자리 옮기기 local) 의 image_name 또는 icon.name 가운데 하나라도 같으면 맞음
4. 유료 호출 - 세 실행의 토큰 · 비용
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import compare as C  # noqa: E402
import stitch as S  # noqa: E402

R = os.path.join(ROOT, "results", "detect")
ST = os.path.join(R, "20261019-strict")
TRUTH = os.path.join(R, "20261013-d3b", "truth.json")
UNITS = {"01a+01b+01c": ("home(01a+01b+01c)", "홈"), "05a+05b+05c": ("bank(05a+05b+05c)", "은행")}


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def answers(folder, unit):
    return {e["id"]: e for e in load(os.path.join(folder, unit + ".semantic.json"))["elements"]}


def slot_names(det_dir, sem_dir, units, truth):
    """단위마다 정답 그림 자리 [{label, action, names, rule}] - 닿은 요소의 이름들."""
    states = {s["state"]: s for s in truth["states"]}
    dets = C.load_units(det_dir)
    pairs = C.pairing(truth, dets)
    out = {}
    for name in units:
        det = dets[name]
        st = states[pairs[name][0]["state"]]
        ans = answers(sem_dir, name)
        rows = []
        for r in C.judge_capture(det, st)["rows"]:
            if r["kind"] != "slot":
                continue
            names = []
            for i in r["els"]:
                g = ans.get(i) or {}
                for n in (g.get("image_name"), (g.get("icon") or {}).get("name")):
                    if n and n not in names:
                        names.append(n)
            rows.append({"label": r["label"], "action": r["action"], "names": names, "rule": bool(r.get("named"))})
        out[name] = rows
    return out


def count(rows, logos=False):
    rs = [r for r in rows if (r["action"] == "pick-bank") == logos] if logos is not None else rows
    return sum(r["label"] in r["names"] for r in rs), len(rs)


def main():
    truth = load(TRUTH)
    md = ["# 스크린샷만 (--inputs strict) 실행 견주기 (2026-10-19)\n",
          "만드는 줄의 입력은 캡처 PNG(파일 이름 순)뿐 - 이름표 · 이어 붙이기 묶음 · 과제 이름 · 로고 규칙(LOGO_HEAD) 없이. "
          "채점(정답지 · 이름표로 짝짓기)은 옛 판과 같다. 검출(OmniParser · OCR)은 D2.5 final 그대로이고 로고 규칙 이름만 "
          "지웠다 (`detect/_strict.json`).\n"]

    # 1. 이어 붙이기
    g = load(os.path.join(ST, "groups.json"))
    md.append("## 1. 이어 붙이기 자동 판정\n")
    md.append("stitch.GROUPS (연구자): %s\n" % " · ".join("+".join(v) for v in S.GROUPS.values()))
    md.append(C.table(["설정", "기준", "나온 묶음", "GROUPS 와 같나"],
                      [[k, json.dumps(v["config"], ensure_ascii=False), " · ".join(n for n, _ in v["groups"]),
                        "같음" if sorted(c for _, c in v["groups"]) == sorted(S.GROUPS.values()) else "다름"]
                       for k, v in g.items()]))
    md.append("\n이웃 짝마다 (설정 B - 기본):\n")
    md.append(C.table(["짝", "같은 화면", "어긋남", "방법", "근거 수"],
                      [["%s → %s" % (p["a"], p["b"]), "예" if p["same"] else "-", p["shift"] or "-",
                        p["method"] or "-", p["evidence"] or "-"] for p in g["B"]["pairs"]]))

    # 2. 흐름
    old = load(os.path.join(R, "20261013-d4", "compare_flow.json"))
    new = load(os.path.join(ST, "flow", "compare_flow.json"))
    md.append("\n## 2. 흐름 D4 - 이름표 있음 (20261013-d4) 대 없음 (strict)\n")
    md.append("의미 층 역할은 둘 다 20261013-d3b (이름표 효과만 보려고 같게 둔다 - 그 역할은 과제 이름 · 단위 이름이 든 "
              "v1 프롬프트로 만든 것이다).\n")
    fmt = lambda p: "%s · %s%s" % (p.get("tap_text") or "-", p["kind"], "" if p["tap_ok"] and p["kind_ok"] else " ✗")
    rows = []
    for a, b in zip(old["pairs"], new["pairs"]):
        t, first = b["truth"], b["truth"].get("first") or {}
        what = "숫자 키" if first.get("key") else (first.get("text") or first.get("aria") or "-")
        rows.append(["%s → %s" % (a["from"][:-4], a["to"][:-4]), fmt(a), fmt(b), "%s · %s" % (what, t["kind"])])
    md.append(C.table(["짝", "전 (이름표 있음)", "후 (이름표 없음)", "정답"], rows))
    md.append("\n| | 전 | 후 |\n|---|---|---|\n| 누른 것 맞음 | %d/18 | %d/18 |\n| kind 맞음 | %d/18 | %d/18 |\n"
              "| 둘 다 맞음 | %d/18 | %d/18 |\n" % (old["totals"]["tap_ok"], new["totals"]["tap_ok"],
                                                old["totals"]["kind_ok"], new["totals"]["kind_ok"],
                                                old["totals"]["both_ok"], new["totals"]["both_ok"]))

    # 3. 의미 층
    md.append("\n## 3. 의미 층 - v1 + 로고 규칙 (20261013-d3b) 대 v2 strict (홈 · 은행)\n")
    before = slot_names(os.path.join(R, "20261013-d25", "final"), os.path.join(R, "20261013-d3b"),
                        [v[0] for v in UNITS.values()], truth)
    after = slot_names(os.path.join(ST, "detect"), os.path.join(ST, "semantic"), list(UNITS), truth)
    rows = []
    for u, (old_u, label) in UNITS.items():
        b, a = before[old_u], after[u]
        if label == "은행":
            rows.append([label + " - 은행 로고", "%d/%d" % count(b, True), "%d/%d" % count(a, True)])
            rows.append([label + " - 그 밖", "%d/%d" % count(b, False), "%d/%d" % count(a, False)])
        rows.append([label + " 전체", "%d/%d" % count(b, None), "%d/%d" % count(a, None)])
    md.append("그림 이름 = 정답 aria-label (닿은 요소의 image_name · icon.name 가운데 같은 글이 있으면 맞음. 전은 로고 규칙의 "
              "고정 이름 포함):\n")
    md.append(C.table(["", "전 (로고 규칙 + v1)", "후 (strict v2)"], rows))
    md.append("\n### 바뀐 요소 (kind 가 바뀌었거나 icon · text_is_icon · text_fixed 가 찬 것)\n")
    ch = []
    for u, (old_u, label) in UNITS.items():
        det = {e["id"]: e for e in C.load_units(os.path.join(ST, "detect"))[u]["elements"]}
        o, n = answers(os.path.join(R, "20261013-d3b"), old_u), answers(os.path.join(ST, "semantic"), u)
        for i, e in n.items():
            ok = o.get(i, {}).get("kind")
            if ok != e["kind"] or e.get("text_is_icon") or e.get("text_fixed") or \
                    (e.get("icon") and e["kind"] != "image"):
                ic = e.get("icon") or {}
                ch.append([label, i, (det[i].get("text") or "-")[:24], "%s → %s" % (ok, e["kind"]),
                           ic.get("name") or "-", "예" if e.get("text_is_icon") else "-", e.get("text_fixed") or "-"])
    md.append(C.table(["단위", "id", "원래 text", "kind (전 → 후)", "icon", "text_is_icon", "text_fixed"], ch))

    # 4. 유료
    sem = load(os.path.join(ST, "semantic", "_semantic.json"))
    flow = load(os.path.join(ST, "flow", "flow.proposed.json"))
    llm = load(os.path.join(ST, "llm", "_llm.json"))
    pay = [["의미 층 v2 (홈 · 은행)", sum(u["attempts"] for u in sem["units"].values()), sem["totals"]["prompt_tokens"],
            sem["totals"]["completion_tokens"], "%.4f" % sem["totals"]["cost_usd"],
            "%.4f" % sum(u["estimate"]["cost_usd_with_reasoning"] for u in sem["units"].values())],
           ["흐름 D4 strict (18쌍, 글만)", len(flow["attempts"]),
            sum((x["usage"] or {}).get("prompt") or 0 for x in flow["attempts"]),
            sum((x["usage"] or {}).get("completion") or 0 for x in flow["attempts"]), "%.4f" % flow["cost_usd"],
            "%.4f" % flow["estimate"]["cost_usd_with_reasoning"]],
           ["LLM 시안 strict (홈)", sum(u["attempts"] for u in llm["units"].values()),
            sum(u["prompt_tokens"] for u in llm["units"].values()),
            sum(u["completion_tokens"] for u in llm["units"].values()), "%.4f" % llm["spent_usd"],
            "%.4f" % sum(u["estimate_usd"] for u in llm["units"].values())]]
    tot = sum(float(r[4]) for r in pay)
    md.append("\n## 4. 유료 호출 (gpt-6.1-sol)\n")
    md.append(C.table(["무엇", "호출", "입력 토큰", "출력 토큰", "실제 USD", "어림 USD (생각 = 답)"],
                      pay + [["합계", sum(r[1] for r in pay), "", "", "%.4f" % tot, ""]]))
    with io.open(os.path.join(ST, "summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md[-2:]))
    for u, (old_u, label) in UNITS.items():
        print(label, "전", count(before[old_u], None), "후", count(after[u], None))


if __name__ == "__main__":
    main()
