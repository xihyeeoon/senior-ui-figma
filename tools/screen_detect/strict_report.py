r"""채점 - "스크린샷만" (--inputs strict) 실행을 옛 판과 같은 셈으로 견준다. 사람 파일을 읽는 채점 쪽이다
(strict 를 켜지 않는다).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/strict_report.py
        [--root results/detect/20261019-strict2] → <root>/summary.md (+ <root>/check/ 잘라 낸 그림)

판 셋 (있는 것만):
  v1 + 로고 규칙   검출 20261013-d25/final · 의미 층 20261013-d3b · 흐름 20261013-d4 (이름표 있음)
  직전 strict      20261019-strict (검출은 D2.5 에서 로고 규칙 이름만 지움 · 의미 층 v2 홈 · 은행만 · 흐름 글만)
  strict2          20261019-strict2 (검출을 로고 규칙 없이 다시 · 의미 층 v2 (icon 규칙) 단위 전부 · 흐름 그림 포함)
셈 (10/19 고친 것): 정답 그림 자리마다 닿은 요소(compare.judge_capture, 자리 옮기기 local, 그림 자리는 닻 범위에 걸치면
캡처 안) 의 image_name · icon.name 가운데 하나라도 정답 aria-label 과 같으면 맞음 - 띄어쓰기 · 끝말 "로고" / "아이콘"
차이는 같게 본다 (compare.name_key). 의미 층을 안 돌렸거나 실패한 단위는 0 으로 세고 "답 없는 단위 있음" 으로 적는다.
"""
import argparse
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
TRUTH = os.path.join(R, "20261013-d3b", "truth.json")
VERSIONS = [("v1 + 로고 규칙", os.path.join(R, "20261013-d25", "final"), os.path.join(R, "20261013-d3b"),
             os.path.join(R, "20261013-d4")),
            ("직전 strict", os.path.join(R, "20261019-strict", "detect"), os.path.join(R, "20261019-strict", "semantic"),
             os.path.join(R, "20261019-strict", "flow")),
            ("strict2", os.path.join(R, "20261019-strict2", "detect"), os.path.join(R, "20261019-strict2", "semantic"),
             os.path.join(R, "20261019-strict2", "flow")),
            # strict3 (10/19 저녁) - 검출은 strict2 그대로, 의미 층은 은행만 다시 (칸 짝 검사를 경고로), 흐름 다시
            ("strict3", os.path.join(R, "20261019-strict2", "detect"), os.path.join(R, "20261019-strict3", "semantic"),
             os.path.join(R, "20261019-strict3", "flow"))]
GROUPS = [("홈", "01a+01b+01c"), ("은행", "05a+05b+05c"), ("증권사", "06a+06b+06c")]


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def caps_of(name, det):
    return "+".join(det.get("captures") or [name])


def sem_file(folder, name, det):
    """의미 층 답 파일 - 같은 이름, 없으면 같은 캡처 묶음의 옛 이름."""
    p = os.path.join(folder, name + ".semantic.json")
    if os.path.exists(p):
        return p
    for f in os.listdir(folder):
        if f.endswith("(%s).semantic.json" % caps_of(name, det)):
            return os.path.join(folder, f)
    return None


def slot_rows(det_dir, sem_dir, truth):
    """캡처 묶음 → [{label, names, ran}] - 정답 그림 자리마다 닿은 요소의 이름들."""
    states = {s["state"]: s for s in truth["states"]}
    dets = C.load_units(det_dir)
    pairs = C.pairing(truth, dets)
    out = {}
    for name, det in dets.items():
        f = sem_file(sem_dir, name, det)
        res = load(f) if f else {}
        ran = res.get("status") == "ok"          # 의미 층을 안 돌렸거나 출력 검사에 두 번 걸려 실패한 단위는 답이 없다
        ans = {e["id"]: e for e in res.get("elements") or []}
        rows = []
        for r in C.judge_capture(det, states[pairs[name][0]["state"]])["rows"]:
            if r["kind"] != "slot":
                continue
            names = []
            for i in r["els"]:
                g = ans.get(i) or {}
                for n in (g.get("image_name"), (g.get("icon") or {}).get("name")):
                    if n and n not in names:
                        names.append(n)
            rows.append({"label": r["label"], "names": names, "ran": ran,
                         "ok": C.name_key(r["label"]) in [C.name_key(n) for n in names]})
        out[caps_of(name, det)] = rows
    return out


def group_counts(rows):
    out, rest, ran_rest = {}, [], True
    for label, caps in GROUPS:
        rs = rows.get(caps, [])
        out[label] = (sum(r["ok"] for r in rs), len(rs), all(r["ran"] for r in rs) if rs else True)
    for caps, rs in rows.items():
        if caps not in [c for _, c in GROUPS]:
            rest += rs
    out["나머지"] = (sum(r["ok"] for r in rest), len(rest), all(r["ran"] for r in rest) if rest else True)
    allr = [r for rs in rows.values() for r in rs]
    out["전체"] = (sum(r["ok"] for r in allr), len(allr), all(r["ran"] for r in allr))
    return out


def detect_table(md):
    """검출 전 (D2.5) → 후 (strict2) - score/detect-*/compare.json (compare.py --truth 로 만든 것)."""
    sc = os.path.join(R, "20261019-strict2", "score")
    rows, keep = [], {}
    for n in ("final", "strict2"):
        p = os.path.join(sc, "detect-%s" % n, "compare.json")
        if not os.path.exists(p):
            return
        c = load(p)
        slots = {}
        for unit, pc in c["per_capture"].items():
            for r in pc["rows"]:
                if r["kind"] == "slot":
                    k = (c["proposed"][unit], r["label"])
                    slots[k] = slots.get(k) or bool(r.get("named") or r.get("near"))
        keep[n] = (c, slots)
    (ca, sa), (cb, sb) = keep["final"], keep["strict2"]
    cnt = lambda c: sum(p.get("img_candidates", 0) for p in c["per_capture"].values())
    br = lambda c, k: "%d/%d" % tuple(c["row"]["box_recall"][k])
    rows = [["그림 자리에 닿은 후보 (/90)", "%d/%d" % (sum(sa.values()), len(sa)), "%d/%d" % (sum(sb.values()), len(sb))],
            ["칸 안 그림 후보 (단위 합)", cnt(ca), cnt(cb)],
            ["그림 자리 후보 (글 없는 박스 + 칸 안 후보)", ca["row"]["candidates"], cb["row"]["candidates"]],
            ["검출 박스", ca["row"]["boxes"], cb["row"]["boxes"]]]
    rows += [["박스 재현율 - " + nm, br(ca, k), br(cb, k)]
             for k, nm in (("button", "버튼"), ("entrance", "입구"), ("choice", "선택지"), ("field", "입력칸"))]
    md.append("\n## 1. 검출 - D2.5 final 대 strict2 (로고 규칙 없이 다시, 같은 설정 · 같은 OCR 캐시)\n")
    md.append(C.table(["", "전 (D2.5)", "후 (strict2)"], rows))
    lost = [k for k in sa if sa[k] and not sb.get(k)]
    gain = [k for k in sb if sb[k] and not sa.get(k)]
    md.append("\n후보를 잃은 그림 자리: %s. 얻은 그림 자리: %s.\n"
              % (", ".join("%s %s" % k for k in lost) or "없음", ", ".join("%s %s" % k for k in gain) or "없음"))


def flow_table(md):
    have = [(nm, os.path.join(f, "compare_flow.json")) for nm, _, _, f in VERSIONS
            if os.path.exists(os.path.join(f, "compare_flow.json"))]
    if not have:
        return
    data = [(nm, load(p)) for nm, p in have]
    names = {"v1 + 로고 규칙": "이름표 있음 (D4)", "직전 strict": "이름표 없음 · 글만", "strict2": "이름표 없음 · 그림 포함",
             "strict3": "strict3 (은행 고침 · 그림 포함)"}
    md.append("\n## 3. 흐름 D4\n")
    fmt = lambda p: "%s · %s%s" % (p.get("tap_text") or "-", p["kind"], "" if p["tap_ok"] and p["kind_ok"] else " ✗")
    rows = []
    for k, base in enumerate(data[-1][1]["pairs"]):
        t, first = base["truth"], base["truth"].get("first") or {}
        what = "숫자 키" if first.get("key") else (first.get("text") or first.get("aria") or "-")
        rows.append(["%s → %s" % (base["from"][:-4], base["to"][:-4])] + [fmt(d["pairs"][k]) for _, d in data]
                    + ["%s · %s" % (what, t["kind"])])
    md.append(C.table(["짝"] + [names[n] for n, _ in data] + ["정답"], rows))
    md.append("\n" + C.table(["", *[names[n] for n, _ in data]],
                             [[lab] + ["%d/18" % d["totals"][key] for _, d in data]
                              for lab, key in (("누른 것 맞음", "tap_ok"), ("kind 맞음", "kind_ok"),
                                               ("둘 다 맞음", "both_ok"))]))


def dirs_of(root):
    """그 판의 (검출 폴더, 의미 층 폴더) - VERSIONS 에서 이름이 root 와 같은 판."""
    v = next((v for v in VERSIONS if os.path.basename(root).endswith(v[0])), None)
    return (v[1], v[2]) if v else (os.path.join(root, "detect"), os.path.join(root, "semantic"))


def semantic_tables(md, root):
    det_dir, sem = dirs_of(root)
    if not os.path.isdir(sem):
        return
    det = C.load_units(det_dir)
    fixed, icons = [], []
    for name, d in det.items():
        f = sem_file(sem, name, d)
        if not f:
            continue
        els = {e["id"]: e for e in d["elements"]}
        for e in load(f).get("elements") or []:
            if e.get("text_fixed"):
                fixed.append([name, e["id"], els[e["id"]].get("text"), e["text_fixed"], e.get("note") or ""])
            if e.get("icon") or e.get("text_is_icon"):
                icons.append([name, e["id"], (els[e["id"]].get("text") or "-")[:20], e["kind"],
                              (e.get("icon") or {}).get("name") or "-", "예" if e.get("text_is_icon") else "-"])
    md.append("\n## 4. 의미 층 v2 - text_fixed 로 바뀐 글 전부\n")
    md.append(C.table(["단위", "id", "원래 text", "text_fixed", "note"], fixed or [["-"] * 5]))
    md.append("\n## 5. 의미 층 v2 - icon · text_is_icon 이 붙은 요소\n")
    md.append(C.table(["단위", "id", "text", "kind", "icon", "text_is_icon"], icons or [["-"] * 6]))


def crop_check(root):
    """"아이엠뱅크(대." 칸을 캡처에서 잘라 둔다 (연구자가 text_fixed "…(대..." 를 눈으로 확인)."""
    from PIL import Image
    out = []
    det = C.load_units(dirs_of(root)[0])
    for name, d in det.items():
        els = {e["id"]: e for e in d["elements"]}
        for e in d["elements"]:
            if e["kind"] == "text" and (e.get("text") or "").startswith("아이엠뱅크"):
                cap = e.get("capture") or name
                off = next((f["offset"] for f in d.get("fragments") or [] if f["capture"] == cap), 0)
                cell = els.get(e.get("in_box")) or e
                x, y, w, h = cell["box"]
                im = Image.open(os.path.join(ROOT, "inputs", "captures", "transfer", cap + ".png")).convert("RGB")
                c = im.crop((max(0, x - 8), max(0, y - off - 8), x + w + 8, y - off + h + 8))
                c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
                path = os.path.join(root, "check", "%s_%s.png" % (name, e["id"].replace(":", "_")))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                c.save(path)
                out.append((name, e["id"], e["text"], os.path.relpath(path, ROOT).replace(os.sep, "/")))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(R, "20261019-strict2"))
    a = ap.parse_args(argv)
    truth = load(TRUTH)
    md = ["# 스크린샷만 (--inputs strict) 견주기 - %s\n" % os.path.basename(a.root),
          "채점은 사람 파일(정답지 · 이름표 짝짓기)을 쓴다. 만드는 줄은 `--inputs strict` (감사 훅을 켠 채) 로 돌았다.\n"]
    detect_table(md)

    md.append("\n## 2. 그림 이름이 정답과 같은 수 (같은 새 셈, 판마다)\n")
    md.append("닿은 요소의 image_name · icon.name 가운데 하나라도 정답 aria-label 과 같으면 맞음 (띄어쓰기 · 끝말 로고/아이콘 "
              "차이는 같게). \"답 없는 단위 있음\" = 그 판에서 의미 층을 안 돌렸거나 출력 검사에 두 번 걸려 실패한 단위가 있다 (0 으로 셈).\n")
    counts = []
    for nm, d, s, _ in VERSIONS:
        if os.path.isdir(d) and os.path.isdir(s):
            counts.append((nm, group_counts(slot_rows(d, s, truth))))
    cell = lambda v: "%d/%d%s" % (v[0], v[1], "" if v[2] else " (답 없는 단위 있음)")
    md.append(C.table(["", *[nm for nm, _ in counts]],
                      [[g] + [cell(c[g]) for _, c in counts] for g in ("홈", "은행", "증권사", "나머지", "전체")]))
    misses = slot_rows(VERSIONS[-1][1], VERSIONS[-1][2], truth) if os.path.isdir(VERSIONS[-1][2]) else {}
    md.append("\n%s 에서 틀린 그림 자리:\n" % VERSIONS[-1][0])
    md.append(C.table(["캡처 묶음", "정답", "닿은 요소의 이름"],
                      [[k, r["label"], " · ".join(r["names"]) or "(닿은 이름 없음)"]
                       for k, rs in misses.items() for r in rs if not r["ok"]] or [["-"] * 3]))
    flow_table(md)
    semantic_tables(md, a.root)
    crops = crop_check(a.root)
    md.append("\n## 6. 잘라 둔 칸 (연구자 확인용)\n")
    md.append(C.table(["캡처 묶음", "id", "OCR 글", "그림"], [list(x) for x in crops] or [["-"] * 4]))
    with io.open(os.path.join(a.root, "summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    for nm, c in counts:
        print(nm, {g: c[g][:2] for g in c})


if __name__ == "__main__":
    main()
