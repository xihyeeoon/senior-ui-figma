r"""구역 검출 다지기 - M1(색 영역 나누기)의 놓침 · 넘침 가르기, 흔들림 시험, 구역 묶음 꼴 (2026-10-19).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/regions_robust.py miss
    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/regions_robust.py shake
    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/regions_robust.py tree

기본 검출 경로는 바꾸지 않는다 - 따로 부르는 단계다. 유료 호출 없음, OmniParser · OCR 도 다시 돌리지 않는다
(요소는 D2.5 final 그대로). 구역 정답지는 results/detect/20261019-regions/truth_regions.json, 쓰는 곳은
results/detect/20261019-robust/.

miss   M1 색 차이 2 · 원본 캡처의 놓친 정답 구역과 정답에 없는 구역을 miss/marks.json (그림을 보고 가른 표시 -
       정답지는 고치지 않는다) 대로 세고, 종류마다 색을 달리해 miss/<단위>.png 에 그린다. marks.json 에 없는
       놓침 · 넘침이 있으면 멈춘다 (표시가 지금 결과와 맞는지).
shake  흔들림 시험 - 원본 캡처 19장의 사본 다섯 가지(원본 · JPEG 90 · JPEG 75 · 0.75배 · 0.75배 + JPEG 75)에
       M1 을 색 차이 2 · 3 · 4 로. 사본은 _copies/ (커밋하지 않는다 - .gitignore). 줄이면 정답 구역 · D2.5 요소
       상자 · 이은 화면의 조각 자리도 같은 비율로 옮기고, 최소 크기(CSS 40x24)도 그 배율로 화소로 바꾼다.
       원본 + 색 차이 2 가 바탕 16/17 · 정답에 없는 구역 31 로 다시 나오지 않으면 멈춘다. JPEG 75 + 색 차이 2 의
       바탕 재현율이 12/17 아래이거나 정답에 없는 구역이 62 를 넘으면, 그 사본과 원본에 중앙값 흐림 3x3 을 한
       뒤 색 차이 2 · 4 로 한 번 더 (그 밖의 앞처리는 하지 않는다). 바탕 재현율이 원본보다 3 이상 떨어진 첫 줄의
       홈 01a 그림 하나만 shake/ 에 남긴다.
tree   M1 색 차이 2 · 원본으로 단위마다 구역 나무 - tree/<단위>.regions.json (구역 id · 상자 · 부모 · 깊이 · 안에 든
       요소 id, 요소는 중심을 감싼 가장 작은 구역에만) 와 셈, 의미 층 group 과 견주기, 홈 01a 나무 글.
"""
import argparse
import copy
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import compare as C  # noqa: E402
import detect as D  # noqa: E402
import regions as RG  # noqa: E402
import truth_regions as TRG  # noqa: E402

FINAL = os.path.join(ROOT, "results", "detect", "20261013-d25", "final")
SEMANTIC = os.path.join(ROOT, "results", "detect", "20261013-d3b")
CAPTURES = os.path.join(ROOT, "inputs", "captures", "transfer")
TRUTH = os.path.join(ROOT, "results", "detect", "20261019-regions", "truth_regions.json")
OUT = os.path.join(ROOT, "results", "detect", "20261019-robust")

VARIANTS = {"원본": (1.0, None), "JPEG 90": (1.0, 90), "JPEG 75": (1.0, 75),
            "0.75배": (0.75, None), "0.75배 + JPEG 75": (0.75, 75)}
DIFFS = (2, 3, 4)
EXPECT = {"box": [16, 17], "extra": 31}          # 직전 결과 (20261019-regions, M1-diff2)
BLUR_IF = {"box_below": 12, "extra_over": 62}    # JPEG 75 + 색 차이 2 가 이러면 중앙값 흐림 한 번
DROP = 3                                          # 바탕 재현율이 이만큼 떨어진 첫 줄의 그림을 남긴다
CONTAIN_PX = 2                                    # 나무 - 이만큼 넘쳐도 감싼 것으로 본다

KIND_COLORS = {"picture": (220, 30, 30), "keypad": (110, 110, 110), "overlay": (130, 60, 200),
               "double": (0, 150, 170), "rule_missed": (240, 130, 0), "other": (150, 120, 60)}
KIND_NAMES = {"picture": "그림 · 사진 안", "keypad": "숫자판 · 키보드 칸", "overlay": "덮개 · 팝업",
              "double": "같은 상자의 겹친 테두리", "rule_missed": "정답 규칙이 빠뜨린 실제 바탕 상자",
              "other": "기타"}
MISS_COLORS = {"a": (30, 90, 230), "b": (0, 0, 0), "c": (0, 170, 80)}


def load():
    tr = json.load(io.open(TRUTH, encoding="utf-8"))
    dets = C.load_units(FINAL)
    return tr, dets, {n: RG.unit_truth(tr, n) for n in dets}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# --------------------------------------------------------------------------- #
# miss - 놓침 · 넘침 가르기
# --------------------------------------------------------------------------- #
def cmd_miss():
    tr, dets, truths = load()
    marks = json.load(io.open(os.path.join(OUT, "miss", "marks.json"), encoding="utf-8"))
    images = {n: TRG.unit_image(d, CAPTURES) for n, d in dets.items()}
    res = RG.run_config("m1", {"diff": 2, "min": 1.0}, images, dets, truths, CAPTURES, {})
    miss_mark = {(m["unit"], m["id"]): m for m in marks["missed"]}
    extra_mark = {(m["unit"], tuple(m["box"])): m for m in marks["extra"]}
    missed, extras, unmarked = [], [], []
    for n, s in res.items():
        tb = [t["box"] for t in truths[n]]
        for t, h in zip(truths[n], s["hits"]):
            if not h:
                m = miss_mark.get((n, t["id"]))
                (missed if m else unmarked).append(dict(m or {"unit": n, "id": t["id"]},
                                                        control=t["control"], box=t["box"]))
        for f in s["boxes"]:
            if not any(RG.match(t, f) for t in tb):
                m = extra_mark.get((n, tuple(f)))
                (extras if m else unmarked).append(m or {"unit": n, "box": f})
    if unmarked or len(missed) != len(marks["missed"]) or len(extras) != len(marks["extra"]):
        raise SystemExit("표시가 지금 결과와 맞지 않는다: %s" % unmarked)

    # 그림 - 놓친 정답(a 파랑 · b 검정 · c 초록, 정답 자리)과 넘침(종류 색)
    for n in res:
        regs = [{"box": m["box"], "col": MISS_COLORS[m["mark"]], "t": "놓침 %s %s" % (m["mark"], m["id"])}
                for m in missed if m["unit"] == n]
        regs += [{"box": m["box"], "col": KIND_COLORS[m["kind"]], "t": KIND_NAMES[m["kind"]]}
                 for m in extras if m["unit"] == n]
        if regs:
            TRG.draw_regions(images[n], regs, os.path.join(OUT, "miss", "%s.png" % n),
                             lambda r: r["col"], lambda r: r["t"])

    t = RG.totals(res)
    n_ctrl = sum(1 for m in missed if m["control"])
    a = {k: sum(1 for m in missed if m["mark"] == "a" and m["control"] == (k == "control"))
         for k in ("box", "control")}
    c = {k: sum(1 for m in missed if m["mark"] == "c" and m["control"] == (k == "control"))
         for k in ("box", "control")}
    sub = lambda v, k, d: [v[0], v[1] - d[k]]
    md = ["# 놓침 · 넘침 가르기 (M1 색 차이 2 · 원본 캡처)\n",
          "표시: `miss/marks.json` (그림을 보고 가른 것 - 정답지는 고치지 않았다). 그림 `miss/<단위>.png` - 놓친 "
          "정답 구역은 정답 자리에 (a 파랑 · b 검정 · c 초록), 넘침은 종류 색.\n",
          "## 놓친 정답 구역 (%d - 바탕 %d · 조작 %d)\n" % (len(missed), len(missed) - n_ctrl, n_ctrl),
          C.table(["단위", "id", "바탕/조작", "무엇", "가름", "이유"],
                  [[m["unit"], m["id"], "조작" if m["control"] else "바탕", m["what"], m["mark"], m["why"]]
                   for m in missed]),
          "\na = 정답 자리 어긋남 (찾은 상자는 실제 상자와 맞음), b = 진짜 놓침, c = 더미앱에 그 상자가 없음.\n",
          C.table(["", "바탕 재현율", "조작 재현율"],
                  [["그대로", RG.pc(t["box"]), RG.pc(t["control"])],
                   ["a 를 뺀 것", RG.pc(sub(t["box"], "box", a)), RG.pc(sub(t["control"], "control", a))],
                   ["a · c 를 뺀 것", RG.pc([t["box"][0], t["box"][1] - a["box"] - c["box"]]),
                    RG.pc([t["control"][0], t["control"][1] - a["control"] - c["control"]])]]),
          "\n## 정답에 없는 구역 (%d) - 종류별\n" % len(extras),
          C.table(["종류", "수", "갈래 (note)"],
                  [[KIND_NAMES[k], sum(1 for m in extras if m["kind"] == k),
                    " · ".join(sorted({m["note"].split(" - ")[0] for m in extras if m["kind"] == k}))]
                   for k in KIND_NAMES]),
          "\n### 정답 규칙이 빠뜨린 실제 바탕 상자\n",
          C.table(["단위", "상자 [x, y, w, h]", "무엇"],
                  [[m["unit"], m["box"], m["note"]] for m in extras if m["kind"] == "rule_missed"]
                  or [["-", "-", "-"]]),
          "\n### 넘침 전부\n",
          C.table(["단위", "상자", "종류", "note"],
                  [[m["unit"], m["box"], KIND_NAMES[m["kind"]], m["note"]] for m in extras])]
    write(os.path.join(OUT, "miss", "summary.md"), "\n".join(md) + "\n")
    print("\n".join(md[2:6]))


# --------------------------------------------------------------------------- #
# shake - 흔들림 시험
# --------------------------------------------------------------------------- #
def make_copies(dst):
    """사본 다섯 가지 - _copies/<사본>/<캡처>.png (JPEG 은 저장했다가 다시 읽어 PNG 로 둔다)."""
    from PIL import Image
    names = sorted(f[:-4] for f in os.listdir(CAPTURES) if f.endswith(".png"))
    for v, (k, q) in VARIANTS.items():
        d = os.path.join(dst, v)
        os.makedirs(d, exist_ok=True)
        for n in names:
            im = Image.open(os.path.join(CAPTURES, n + ".png")).convert("RGB")
            if k != 1.0:
                im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
            if q:
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=q)
                buf.seek(0)
                im = Image.open(buf).convert("RGB")
            im.save(os.path.join(d, n + ".png"))


def scale_box(b, k):
    return [round(v * k) for v in b]


def scaled(dets, truths, k):
    """줄인 사본의 단위 - 요소 상자 · 단위 크기 · 이은 화면 조각 자리 · 정답 구역을 k 배."""
    ds, ts = {}, {}
    for n, d in dets.items():
        d = copy.deepcopy(d)
        for e in d["elements"]:
            e["box"] = scale_box(e["box"], k)
        d["size"] = scale_box(d["size"], k)
        for f in d.get("fragments") or []:
            for key in ("offset", "top_band", "bottom_band"):
                f[key] = round(f[key] * k)
        ds[n] = d
        ts[n] = [dict(t, box=scale_box(t["box"], k)) for t in truths[n]]
    return ds, ts


def unit_images(dets, folder, blur=False):
    from PIL import Image, ImageFilter
    out = {}
    for n, d in dets.items():
        if "fragments" in d:
            import stitch
            imgs = [Image.open(os.path.join(folder, f["capture"] + ".png")).convert("RGB")
                    for f in d["fragments"]]
            im = stitch.compose(d["fragments"], imgs)
        else:
            im = Image.open(os.path.join(folder, os.path.basename(d["capture"]))).convert("RGB")
        out[n] = im.filter(ImageFilter.MedianFilter(3)) if blur else im
    return out


def cmd_shake():
    tr, dets, truths = load()
    copies = os.path.join(OUT, "_copies")
    make_copies(copies)
    rows, res_all, fig = [], {}, None
    base_box = None

    def one(v, diff, blur=False):
        k = VARIANTS[v][0]
        ds, ts = scaled(dets, truths, k) if k != 1.0 else (dets, truths)
        ims = unit_images(ds, os.path.join(copies, v), blur)
        res = RG.run_config("m1", {"diff": diff, "min": k}, ims, ds, ts, CAPTURES, {})
        return res, RG.totals(res), ims, ts

    for v in VARIANTS:
        for diff in DIFFS:
            res, t, ims, ts = one(v, diff)
            if v == "원본" and diff == 2:
                if t["box"] != EXPECT["box"] or t["extra"] != EXPECT["extra"]:
                    raise SystemExit("원본 + 색 차이 2 가 직전 결과와 다르다: 바탕 %s · 넘침 %d" % (t["box"], t["extra"]))
                base_box = t["box"][0]
            rows.append({"variant": v, "diff": diff, "blur": False, "totals": t})
            res_all["%s|%d" % (v, diff)] = res
            if fig is None and base_box is not None and t["box"][0] <= base_box - DROP:
                fig = (v, diff, res, ims, ts)
            print(v, diff, t["box"], t["extra"], flush=True)
    j75 = next(r["totals"] for r in rows if r["variant"] == "JPEG 75" and r["diff"] == 2)
    blurred = j75["box"][0] < BLUR_IF["box_below"] or j75["extra"] > BLUR_IF["extra_over"]
    if blurred:
        for v in ("JPEG 75", "원본"):
            for diff in (2, 4):
                res, t, ims, ts = one(v, diff, blur=True)
                rows.append({"variant": v, "diff": diff, "blur": True, "totals": t})
                res_all["%s|%d|blur" % (v, diff)] = res
                print(v, diff, "blur", t["box"], t["extra"], flush=True)
    figpath = None
    if fig:
        from PIL import Image
        v, diff, res, ims, ts = fig
        n = next(n for n in dets if n.startswith("home"))
        # 이은 홈 그림의 맨 위는 01a 통째 (stitch.compose) - 01a 사본의 높이만큼 자른다
        h01a = Image.open(os.path.join(copies, v, "01a.png")).height
        figpath = os.path.join(OUT, "shake", "home_01a_%s_diff%d.png" % (
            v.replace(" ", "").replace(".", "").replace("+", "_"), diff))
        RG.draw_found(ims[n], ts[n], res[n]["boxes"], figpath)
        im = Image.open(figpath)
        im.crop((0, 0, im.width, min(im.height, h01a))).save(figpath)

    yes = lambda x: "예" if x and x["hit"] else "아니오"
    md = ["# 흔들림 시험 (M1 만)\n",
          "원본 캡처 19장의 사본 다섯 가지 × 색 차이 %s. 사본은 `_copies/` (커밋하지 않음). 줄인 사본은 Pillow "
          "LANCZOS, JPEG 은 Pillow 기본(4:2:0). 정답 구역 · D2.5 요소 · 이은 화면 조각 자리도 같은 배율, 최소 "
          "크기는 CSS 40x24 를 배율까지 반영해 화소로. 원본 + 색 차이 2 는 직전 결과(바탕 16/17 · 넘침 31)와 같음을 "
          "확인했다.\n" % " · ".join(map(str, DIFFS)),
          C.table(["사본", "색 차이", "앞처리", "바탕 재현율", "조작 재현율", "정답에 없는 구역", "묶음 (가)",
                   "IRP · 땡겨요"],
                  [[r["variant"], r["diff"], "중앙값 3x3" if r["blur"] else "-", RG.pc(r["totals"]["box"]),
                    RG.pc(r["totals"]["control"]), r["totals"]["extra"], RG.pc(r["totals"]["group_bg"]),
                    "%s · %s" % (yes(r["totals"]["irp"]), yes(r["totals"]["ddanggyo"]))] for r in rows]),
          "\n앞처리 조건 (JPEG 75 + 색 차이 2 의 바탕 < %d/17 또는 넘침 > %d): %s.\n"
          % (BLUR_IF["box_below"], BLUR_IF["extra_over"],
             "걸려서 중앙값 흐림 3x3 을 JPEG 75 와 원본에 한 번 더 돌렸다" if blurred else "걸리지 않아 돌리지 않았다"),
          "그림: %s\n" % (("`%s` (바탕 재현율이 원본보다 %d 이상 떨어진 첫 줄 - %s · 색 차이 %d, 홈 01a 부분)"
                          % (os.path.relpath(figpath, OUT).replace("\\", "/"), DROP, fig[0], fig[1]))
                         if fig else "없음 (원본보다 %d 이상 떨어진 줄이 없다)" % DROP)]
    write(os.path.join(OUT, "shake", "summary.md"), "\n".join(md) + "\n")
    with io.open(os.path.join(OUT, "shake", "shake.json"), "w", encoding="utf-8") as f:
        json.dump({"variants": {k: {"scale": v[0], "jpeg": v[1]} for k, v in VARIANTS.items()},
                   "diffs": DIFFS, "blur_rule": BLUR_IF, "blurred": blurred, "rows": rows},
                  f, ensure_ascii=False, indent=1)
    print("\n".join(md[2:5]))


# --------------------------------------------------------------------------- #
# tree - 구역 묶음 꼴
# --------------------------------------------------------------------------- #
def holds(outer, inner):
    return (outer[0] - CONTAIN_PX <= inner[0] and outer[1] - CONTAIN_PX <= inner[1]
            and inner[0] + inner[2] <= outer[0] + outer[2] + CONTAIN_PX
            and inner[1] + inner[3] <= outer[1] + outer[3] + CONTAIN_PX)


def build_tree(boxes, elements):
    area = lambda b: b[2] * b[3]
    regs = [{"id": "g%d" % i, "box": b} for i, b in enumerate(sorted(boxes, key=lambda b: (b[1], b[0])))]
    for r in regs:
        outer = [o for o in regs if o is not r and area(o["box"]) > area(r["box"]) and holds(o["box"], r["box"])]
        r["parent"] = min(outer, key=lambda o: area(o["box"]))["id"] if outer else None
    by = {r["id"]: r for r in regs}
    for r in regs:
        d, p = 1, r["parent"]
        while p:
            d, p = d + 1, by[p]["parent"]
        r["depth"] = d
        r["elements"] = []
    loose = []
    for e in elements:
        c = C.centre(e["box"])
        inside = [r for r in regs if C.within(c, r["box"])]
        if inside:
            min(inside, key=lambda r: area(r["box"]))["elements"].append(e["id"])
        else:
            loose.append(e["id"])
    return regs, loose


def partial_pairs(regs):
    n = 0
    for i, a in enumerate(regs):
        for b in regs[i + 1:]:
            if D.inter(D.xyxy(a["box"]), D.xyxy(b["box"])) > 0 and not holds(a["box"], b["box"]) \
                    and not holds(b["box"], a["box"]):
                n += 1
    return n


def group_stats(n, regs, els, ans, text, skip):
    """의미 층 group 과 구역 - 요소가 든 가장 작은 구역(skip 에 든 구역이면 없음)으로 센다."""
    where = {i: r["id"] for r in regs if r["id"] not in skip for i in r["elements"]}
    groups = {}
    for e in els:
        g = (ans.get(e["id"]) or {}).get("group")
        if g:
            groups.setdefault(g, []).append(e["id"])
    same = total = pairs = 0
    examples = []
    for ids in groups.values():
        if len(ids) < 2:
            continue
        spots = [where.get(i) for i in ids]
        same += max(spots.count(x) for x in set(spots))
        total += len(ids)
    for r in regs:
        if r["id"] in skip:
            continue
        got = [(i, (ans.get(i) or {}).get("group")) for i in r["elements"]]
        got = [x for x in got if x[1]]
        for k, (i, gi) in enumerate(got):
            for j, gj in got[k + 1:]:
                if gi != gj:
                    pairs += 1
                    if len(examples) < 3:
                        examples.append({"unit": n, "region": r["id"], "a": [i, text[i], gi],
                                         "b": [j, text[j], gj]})
    return {"same": same, "total": total, "pairs": pairs, "examples": examples}


def cmd_tree():
    tr, dets, truths = load()
    sem, _ = C.load_semantic(SEMANTIC)
    images = {n: TRG.unit_image(d, CAPTURES) for n, d in dets.items()}
    rows, home = [], None
    cmp_ = {k: {"same": 0, "total": 0, "pairs": 0, "examples": []} for k in ("all", "narrow")}
    for n, det in dets.items():
        ans = sem.get(n) or {}
        els = [e for e in det["elements"] if e["kind"] in ("box", "text", "img_candidate")]
        boxes = RG.m1(images[n], 2, 1.0)
        regs, loose = build_tree(boxes, els)
        system = {e["id"] for e in els if "system_band" in (e.get("flags") or [])
                  or (ans.get(e["id"]) or {}).get("kind") == "system"}
        all_in = {r["id"]: [e["id"] for e in els if C.within(C.centre(e["box"]), r["box"])] for r in regs}
        write(os.path.join(OUT, "tree", "%s.regions.json" % n),
              json.dumps({"unit": n, "method": "M1 색 차이 2 · 원본", "regions": regs, "loose": loose},
                         ensure_ascii=False, indent=1))
        # 의미 층 group 과 견주기 - 구역 전부, 그리고 화면 너비 구역을 구역이 아닌 것으로 본 셈
        text = {e["id"]: (e.get("text") or e.get("name") or e.get("caption") or "")[:10] for e in els}
        wide = {r["id"] for r in regs if r["box"][2] >= 0.95 * det["size"][0]}
        for key, skip in (("all", set()), ("narrow", wide)):
            g = group_stats(n, regs, els, ans, text, skip)
            for k in ("same", "total", "pairs"):
                cmp_[key][k] += g[k]
            cmp_[key]["examples"] += g["examples"][:3 - len(cmp_[key]["examples"])]
        rows.append([n, len(regs), max((r["depth"] for r in regs), default=0),
                     sum(1 for i in loose if i not in system), partial_pairs(regs),
                     sum(1 for r in regs if not all_in[r["id"]])])
        if n.startswith("home"):
            home = (n, regs, text, det)
    # 홈 01a 나무 - 01a 조각 안의 구역만
    n, regs, text, det = home
    h01a = det["fragments"][1]["offset"]
    keep = [r for r in regs if r["box"][1] < h01a]
    by = {r["id"]: r for r in keep}
    lines = []

    def show(r, depth):
        words = " · ".join(text[i] for i in r["elements"] if text[i])[:60]
        lines.append("%s%s %s  %s" % ("  " * depth, r["id"], r["box"], words))
        for c in [c for c in keep if c["parent"] == r["id"]]:
            show(c, depth + 1)
    for r in [r for r in keep if not r["parent"] or r["parent"] not in by]:
        show(r, 0)
    write(os.path.join(OUT, "tree", "home_01a.txt"), "\n".join(lines) + "\n")
    md = ["# 구역 묶음 꼴 (M1 색 차이 2 · 원본 캡처)\n",
          "단위마다 `tree/<단위>.regions.json` - 구역 id · 상자 · 부모(자기를 감싸는 가장 작은 구역, 변마다 %dpx "
          "넘침 허용) · 깊이(맨 바깥 1) · 안에 든 D2.5 요소 id (요소는 중심을 감싼 가장 작은 구역에만). 기본 경로에 "
          "잇지 않는다.\n" % CONTAIN_PX,
          C.table(["단위", "구역", "가장 깊은 깊이", "어느 구역에도 안 든 요소 (상태바 · system 뺌)",
                   "감싸지 않고 일부만 겹친 쌍", "요소가 하나도 없는 구역"], rows),
          "\n## 의미 층 group 과 견주기 (`%s`)\n" % os.path.relpath(SEMANTIC, ROOT).replace("\\", "/"),
          "같은 group 비율 = 요소 둘 이상인 group 마다 가장 많이 모인 구역(어느 구역에도 안 든 것도 한 자리)에 든 "
          "요소의 비율. 다른 group 쌍 = 같은 구역에 바로 든 요소 가운데 group 이 있고 서로 다른 쌍. \"화면 너비 구역 "
          "뺌\" 은 가로가 단위의 95% 이상인 구역(화면 바탕 조각 · 시트 · 숫자판 판)을 구역이 아닌 것으로 본 셈.\n",
          C.table(["", "같은 group 이 같은 구역", "같은 구역인데 group 이 다른 쌍"],
                  [[label, RG.pc([cmp_[k]["same"], cmp_[k]["total"]]), cmp_[k]["pairs"]]
                   for k, label in (("all", "구역 전부"), ("narrow", "화면 너비 구역 뺌"))])]
    for k, label in (("all", "구역 전부"), ("narrow", "화면 너비 구역 뺌")):
        md.append("\n%s - 다른 group 쌍의 예:\n" % label)
        for x in cmp_[k]["examples"]:
            md.append("- %s %s: %s \"%s\" (%s) 대 %s \"%s\" (%s)" % (
                x["unit"], x["region"], x["a"][0], x["a"][1], x["a"][2], x["b"][0], x["b"][1], x["b"][2]))
    md += ["\n## 홈 01a 나무 (`tree/home_01a.txt`)\n", "```", *lines, "```"]
    write(os.path.join(OUT, "tree", "summary.md"), "\n".join(md) + "\n")
    print("\n".join(md))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["miss", "shake", "tree"])
    a = ap.parse_args(argv)
    {"miss": cmd_miss, "shake": cmd_shake, "tree": cmd_tree}[a.cmd]()


if __name__ == "__main__":
    main()
