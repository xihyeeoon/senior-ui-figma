r"""구역 찾기 시험 - 캡처에서 바탕 상자(카드 · 배너 · 시트 · 버튼 바탕)를 찾아 구역 정답지와 견준다 (2026-10-19).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/regions.py
        [--dir results/detect/20261013-d25/final] [--out results/detect/20261019-regions]

기본 검출 경로(detect.py)와 결과는 바꾸지 않는다 - 따로 부르는 단계다. 유료 호출 없음. 구역 정답지는
truth_regions.py 가 먼저 만든 truth_regions.json (--truth-regions) 을 읽는다. 단위(이은 화면 3 + 낱장 10)마다 센다.

M1 색 영역 나누기 (학습 모델 없음, OpenCV) - 단위 그림(이은 화면은 stitch.compose 로 이은 그림)에서
  이웃 화소(오른쪽 · 아래)와 채널 차가 DIFF 보다 큰 화소를 경계로 보고, 경계가 아닌 화소의 이어진 영역(4-이웃)
  마다 바깥 윤곽을 채운 넓이가 둘레 상자의 RECT_FILL 이상(사각형 · 둥근 모서리 상자)이고 가로 · 세로가
  최소 크기 이상이면 구역이다. 영역 안의 구멍(글 · 아이콘 · 안쪽 상자)은 채워서 본다 - 카드 안에 배너가
  있어도 카드는 하나다. 대비가 낮아도(흰 바탕 위 #F5F6F9 처럼 채널 차 10) 화소 값이 다르면 경계가 된다.
M2 UIED (MulongXie/UIED @ 0a9862a, Apache-2.0, 레포 밖 C:\Users\xihye\tools\UIED - detect.py --classic 과
  같은 것) - 기울기 이진화 → 선 지우기 → 연결 요소 → 거르기 → 겹친 것 합치기 → 블록 알아보기
  (compo_block_recognition) 까지 돌린 요소 전부("all")와 블록으로 알아본 것만("block"). UIED 는 그림을 높이
  800 으로 줄이므로 캡처마다 돌리고 이은 화면에서는 조각의 offset 만큼 내려 합친다 (뒤 조각의 위 고정 띠 ·
  앞 조각의 아래 고정 띠 안은 빼고, IoU 0.7 넘게 겹친 것은 하나로).
두 방법 모두 화면 전체 바탕(가로 95% · 세로 90% 이상, 이은 화면은 단위 높이의 90%)과 최소 크기 아래는 뺀다.

재는 것 (단위마다 + 합계)
  구역 재현율   정답 구역(그 단위 안에 옮겨진 것) 가운데 찾은 구역과 맞는 것 - IoU 0.7 이상 또는 네 변이
                모두 12px 안. 바탕 상자(control=false)와 조작 상자(버튼 · 칸)는 늘 따로 센다 (10/19 연구자
                결정 - 주 숫자는 바탕 상자 재현율과 묶음 (가). 합친 숫자는 표의 맨 끝 칸)
  정답에 없는 구역  찾은 구역 가운데 어느 정답 구역과도 맞지 않는 것
  묶음 (가) 바탕  D2.5 final 의 요소(박스 · 글 줄 · 그림 후보)마다 감싸는 가장 작은 정답 바탕 상자 B 를 정하고,
                요소를 감싸는 찾은 구역들 가운데 B 와 맞는 것이 있으면 맞음. B 가 없는 요소는 감싸는 찾은
                구역 가운데 정답 바탕 상자와 맞는 것이 하나도 없으면 맞음 (M1 은 바탕 · 조작을 가리지 못하므로
                "가장 작은 찾은 구역" 대신 "감싸는 구역들 안에 있나")
  묶음 (나) 전부  중심이 정답 구역 안인 요소마다, 그것을 담은 가장 작은 정답 구역(바탕 · 조작)과 가장 작은
                찾은 구역이 맞으면 맞음
  IRP 배너 · 땡겨요 카드 - 홈의 그 두 정답 구역이 잡혔나 (가장 잘 맞는 찾은 구역의 IoU)
쓰는 것: <out>/regions.json, <out>/summary.md, <out>/found/<방법>/<단위>.png (찾은 구역 - 파랑 = 정답과 맞음,
주황 = 정답에 없음, 얇은 초록 = 정답 구역).
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
import detect as D  # noqa: E402
import truth_regions as TRG  # noqa: E402

SX = 824 / C.VIEW[0]                   # 캡처 픽셀 / CSS 픽셀 (캡처 가로 824)
MIN_CSS = (40, 24)                     # 정답지와 같은 최소 크기
RECT_FILL = 0.85
MATCH_IOU, MATCH_PX = 0.7, 12
SAME_IOU = 0.7                         # M2 - 조각 사이에서 같은 구역으로 합치는 IoU
# 시험한 설정 - M1 은 색 차이 세 값과 최소 크기 두 배 하나 (README · summary 에 그대로 적는다)
CONFIGS = {
    "M1-diff2": ("m1", {"diff": 2, "min": 1.0}),
    "M1-diff6": ("m1", {"diff": 6, "min": 1.0}),
    "M1-diff12": ("m1", {"diff": 12, "min": 1.0}),
    "M1-diff6-min2x": ("m1", {"diff": 6, "min": 2.0}),
    "M2-uied-all": ("m2", {"block_only": False}),
    "M2-uied-block": ("m2", {"block_only": True}),
}


def min_px(k):
    return MIN_CSS[0] * SX * k, MIN_CSS[1] * SX * k


def not_screen(box, size):
    return not (box[2] >= 0.95 * size[0] and box[3] >= 0.9 * size[1])


# --------------------------------------------------------------------------- #
# M1 색 영역 나누기
# --------------------------------------------------------------------------- #
def m1(image, diff, min_k):
    import cv2
    import numpy as np
    a = np.asarray(image).astype(np.int16)
    h, w = a.shape[:2]
    dx = np.abs(a[:, 1:] - a[:, :-1]).max(axis=2) > diff
    dy = np.abs(a[1:] - a[:-1]).max(axis=2) > diff
    edge = np.zeros((h, w), bool)
    edge[:, 1:] |= dx
    edge[:, :-1] |= dx
    edge[1:] |= dy
    edge[:-1] |= dy
    n, lab, stats, _ = cv2.connectedComponentsWithStats((~edge).astype(np.uint8), connectivity=4)
    mw, mh = min_px(min_k)
    out = []
    for i in range(1, n):
        x, y, bw, bh, _ = stats[i]
        if bw < mw or bh < mh:
            continue
        mask = (lab[y:y + bh, x:x + bw] == i).astype(np.uint8)
        cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filled = np.zeros_like(mask)
        cv2.drawContours(filled, cs, -1, 1, thickness=-1)
        if filled.sum() < RECT_FILL * bw * bh:
            continue
        # 경계 화소 한 줄을 넣어 상자 바깥 변까지
        box = [int(x) - 1, int(y) - 1, int(bw) + 2, int(bh) + 2]
        if not_screen(box, (w, h)):
            out.append(box)
    return out


# --------------------------------------------------------------------------- #
# M2 UIED
# --------------------------------------------------------------------------- #
def uied(image, block_only):
    """UIED 요소 [x, y, w, h] (캡처 픽셀) - detect.classic_boxes 와 같은 단계, 블록 알아보기 뒤 전부 또는 블록만."""
    import cv2
    import numpy as np
    if D.UIED not in sys.path:
        sys.path.insert(0, D.UIED)
    import detect_compo.lib_ip.ip_preprocessing as pre
    import detect_compo.lib_ip.ip_detection as det
    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    k = D.UIED_PARAMS["resize"] / h
    org = cv2.resize(bgr, (int(w * k), D.UIED_PARAMS["resize"]))
    binary = pre.binarization(org, grad_min=D.UIED_PARAMS["min-grad"])
    det.rm_line(binary, show=False)
    compos = det.component_detection(binary, min_obj_area=D.UIED_PARAMS["min-ele-area"])
    compos = det.compo_filter(compos, min_area=D.UIED_PARAMS["min-ele-area"], img_shape=binary.shape)
    compos = det.merge_intersected_compos(compos)
    det.compo_block_recognition(binary, compos)
    out = []
    for c in compos:
        if block_only and c.category != "Block":
            continue
        x0, y0, x1, y1 = (v / k for v in c.put_bbox())
        out.append([int(round(x0)), int(round(y0)), int(round(x1 - x0)), int(round(y1 - y0))])
    return out


def m2(det, captures, block_only, cache):
    from PIL import Image
    frags = det.get("fragments") or [{"capture": None, "offset": 0, "top_band": 0, "bottom_band": 0}]
    mw, mh = min_px(1.0)
    out = []
    for i, f in enumerate(frags):
        name = f["capture"] or os.path.splitext(os.path.basename(det["capture"]))[0]
        if (name, block_only) not in cache:
            img = Image.open(os.path.join(captures, name + ".png")).convert("RGB")
            cache[(name, block_only)] = (uied(img, block_only), img.size)
        boxes, (w, h) = cache[(name, block_only)]
        lo = 0 if i == 0 else f["top_band"]
        hi = h if i == len(frags) - 1 else h - f["bottom_band"]
        for x, y, bw, bh in boxes:
            if bw < mw or bh < mh or y + bh / 2 < lo or y + bh / 2 > hi:
                continue
            b = [x, y + f["offset"], bw, bh]
            if not any(D.iou(D.xyxy(b), D.xyxy(o)) > SAME_IOU for o in out):
                out.append(b)
    return [b for b in out if not_screen(b, det["size"])]


# --------------------------------------------------------------------------- #
# 재기
# --------------------------------------------------------------------------- #
def match(a, b):
    if D.iou(D.xyxy(a), D.xyxy(b)) >= MATCH_IOU:
        return True
    return all(abs(p - q) <= MATCH_PX for p, q in zip(D.xyxy(a), D.xyxy(b)))


def innermost(pt, boxes):
    inside = [b for b in boxes if C.within(pt, b)]
    return min(inside, key=lambda b: b[2] * b[3]) if inside else None


def score(truth, found, elements):
    """한 단위의 셈. truth [{box, control, …}] (그 단위 안의 정답 구역), found [[x, y, w, h]], elements 는
    D2.5 요소. 바탕 상자(control=false)와 조작 상자를 늘 따로 센다 (10/19 연구자 결정)."""
    tb = [t["box"] for t in truth]
    bg = [t["box"] for t in truth if not t["control"]]
    hit = [any(match(t["box"], f) for f in found) for t in truth]
    extra = [f for f in found if not any(match(t, f) for t in tb)]
    group, group_bg, group_in = [], [], []
    for e in elements:
        c = C.centre(e["box"])
        around = [f for f in found if C.within(c, f)]
        # (가) 바탕 묶음 - 요소를 감싸는 가장 작은 정답 바탕 상자 B 와 맞는 찾은 구역이 감싸는 구역들 가운데
        # 있으면 맞음. B 가 없으면, 감싸는 찾은 구역 가운데 정답 바탕 상자와 맞는 것이 하나도 없으면 맞음
        b = innermost(c, bg)
        if b is not None:
            group_bg.append(any(match(b, f) for f in around))
            group_in.append(group_bg[-1])
        else:
            group_bg.append(not any(match(t, f) for f in around for t in bg))
        # (나) 전부 - 담은 가장 작은 정답 구역(바탕 · 조작 모두)과 가장 작은 찾은 구역이 맞나
        t = innermost(c, tb)
        if t is not None:
            f = innermost(c, found)
            group.append(bool(f) and match(t, f))
    return {"truth": len(truth), "hit": sum(hit),
            "hit_box": [sum(h for h, t in zip(hit, truth) if not t["control"]),
                        sum(not t["control"] for t in truth)],
            "hit_control": [sum(h for h, t in zip(hit, truth) if t["control"]),
                            sum(t["control"] for t in truth)],
            "found": len(found), "extra": len(extra),
            "group_bg": [sum(group_bg), len(group_bg)], "group_bg_in": [sum(group_in), len(group_in)],
            "group": [sum(group), len(group)], "hits": hit}


def best_iou(t, found):
    return max((D.iou(D.xyxy(t), D.xyxy(f)) for f in found), default=0.0)


def pc(v):
    return "%d/%d (%.0f%%)" % (v[0], v[1], 100.0 * v[0] / v[1]) if v[1] else "-"


def unit_truth(tr, n):
    """단위 n 의 정답 구역 (그 단위 안에 옮겨진 것) - 글 · 클래스를 붙여서."""
    reg = {s["state"]: {r["id"]: r for r in s["regions"]} for s in tr["states"]}
    u = tr["units"][n]
    return [dict(r, **{k: reg[u["state"]][r["id"]][k] for k in ("text", "cls")})
            for r in u["regions"] if r["in_unit"]]


def find(method, p, image, det, captures, cache):
    if method == "m1":
        return m1(image, p["diff"], p["min"])
    return m2(det, captures, p["block_only"], cache)


def run_config(method, p, images, dets, truths, captures, cache, figdir=None):
    """설정 하나를 단위마다 돌려 센다. images · dets · truths 는 단위 이름으로 (사본이면 줄인 좌표 그대로)."""
    out = {}
    for n, det in dets.items():
        truth = truths[n]
        found = find(method, p, images[n], det, captures, cache)
        s = score(truth, found, [e for e in det["elements"]
                                 if e["kind"] in ("box", "text", "img_candidate")])
        if n.startswith("home"):
            for key, want in (("irp", "membership"), ("ddanggyo", "땡겨요")):
                t = next(t for t in truth if want in t["cls"] or t["text"].startswith(want))
                s[key] = {"truth": t["id"], "hit": any(match(t["box"], f) for f in found),
                          "best_iou": round(best_iou(t["box"], found), 2)}
        s["boxes"] = found
        out[n] = s
        if figdir:
            draw_found(images[n], truth, found, os.path.join(figdir, "%s.png" % n))
    return out


def draw_found(image, truth, found, path):
    tb = [t["box"] for t in truth]
    regs = [{"box": f, "ok": any(match(t, f) for t in tb)} for f in found]
    regs += [{"box": t, "truth": True} for t in tb]
    TRG.draw_regions(image, regs, path,
                     lambda r: (0, 170, 80) if r.get("truth")
                     else (30, 90, 230) if r["ok"] else (240, 130, 0),
                     lambda r: None)


def totals(res):
    """단위 합계 - 바탕 · 조작 · 정답에 없는 구역 · 묶음 (가)(나) · 합친 재현율 · 홈 두 곳."""
    s = lambda k: [sum(r[k][i] for r in res.values()) for i in (0, 1)]
    home = next((r for n, r in res.items() if n.startswith("home")), None)
    return {"box": s("hit_box"), "control": s("hit_control"),
            "extra": sum(r["extra"] for r in res.values()), "found": sum(r["found"] for r in res.values()),
            "group_bg": s("group_bg"), "group_bg_in": s("group_bg_in"), "group": s("group"),
            "all": [sum(r["hit"] for r in res.values()), sum(r["truth"] for r in res.values())],
            "irp": home and home["irp"], "ddanggyo": home and home["ddanggyo"]}


def yes(x):
    return "%s (%.2f)" % ("예" if x["hit"] else "아니오", x["best_iou"]) if x else "-"


HEAD = ["바탕 재현율", "조작 재현율", "정답에 없는 구역 / 찾은 구역", "묶음 (가) 바탕", "묶음 (나) 전부",
        "IRP 배너 (IoU)", "땡겨요 카드 (IoU)", "합친 재현율"]


def total_row(t):
    return [pc(t["box"]), pc(t["control"]), "%d / %d" % (t["extra"], t["found"]),
            "%s · B 안 %s" % (pc(t["group_bg"]), pc(t["group_bg_in"])),
            pc(t["group"]), yes(t["irp"]), yes(t["ddanggyo"]), pc(t["all"])]


GROUPING = ("묶음 (가) 바탕 = D2.5 final 의 요소(박스 · 글 줄 · 그림 후보)마다 감싸는 가장 작은 정답 바탕 상자 B 를 "
            "정하고, 요소를 감싸는 찾은 구역들 가운데 B 와 맞는 것이 있으면 맞음. B 가 없는 요소는 감싸는 찾은 구역 "
            "가운데 정답 바탕 상자와 맞는 것이 하나도 없으면 맞음 (\"B 안\" = B 가 있는 요소만). 묶음 (나) 전부 = 중심이 정답 구역(바탕 · 조작) "
            "안인 요소마다 담은 가장 작은 정답 구역과 가장 작은 찾은 구역이 맞으면 맞음.")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261013-d25", "final"))
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    ap.add_argument("--truth-regions", default=os.path.join(ROOT, "results", "detect", "20261019-regions",
                                                            "truth_regions.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "detect", "20261019-regions"))
    ap.add_argument("--configs", nargs="*", choices=list(CONFIGS), help="돌릴 설정 (없으면 전부)")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args(argv)
    tr = json.load(io.open(a.truth_regions, encoding="utf-8"))
    dets = C.load_units(a.dir)
    images = {n: TRG.unit_image(d, a.captures) for n, d in dets.items()}
    truths = {n: unit_truth(tr, n) for n in dets}
    names = a.configs or list(CONFIGS)
    cache, res = {}, {}
    for cfg in names:
        method, p = CONFIGS[cfg]
        res[cfg] = run_config(method, p, images, dets, truths, a.captures, cache,
                              None if a.no_figures else os.path.join(a.out, "found", cfg))
        print(cfg, flush=True)
    tot = {cfg: totals(res[cfg]) for cfg in names}
    md = ["# 구역 검출 시험 (2026-10-19)\n",
          "구역 정답지 `%s` (truth_regions.py) 대 캡처에서 찾은 구역 (regions.py). 단위 %d개 "
          "(이은 화면 3 + 낱장 10). 맞음 = IoU %.1f 이상 또는 네 변이 모두 %dpx 안. 최소 크기 CSS %dx%d "
          "(캡처 %.0fx%.0f px), M1 의 사각형 채움 %.2f. 바탕 상자와 조작 상자(버튼 · 칸)는 따로 센다 - 합친 "
          "숫자는 맨 끝 칸.\n"
          % (os.path.relpath(a.truth_regions, ROOT).replace("\\", "/"), len(dets), MATCH_IOU, MATCH_PX,
             MIN_CSS[0], MIN_CSS[1], *min_px(1.0), RECT_FILL),
          C.table(["방법 (기준값)"] + HEAD, [[cfg] + total_row(tot[cfg]) for cfg in names]),
          "\n" + GROUPING + "\n",
          "\n## 단위별 - 바탕 · 조작 · 정답에 없는 구역\n"]
    md.append(C.table(["단위", "상태", "정답 바탕 · 조작"] + names,
                      [[n, tr["units"][n]["state"], "%d · %d" % (res[names[0]][n]["hit_box"][1],
                                                               res[names[0]][n]["hit_control"][1])]
                       + ["%d · %d · +%d" % (res[c][n]["hit_box"][0], res[c][n]["hit_control"][0],
                                             res[c][n]["extra"]) for c in names]
                       for n in dets]))
    md.append("\n칸 = 맞은 바탕 상자 · 맞은 조작 상자 · 정답에 없는 구역. 그림: `found/<방법>/<단위>.png` (파랑 = "
              "정답과 맞음, 주황 = 정답에 없음, 초록 = 정답 구역).\n")
    os.makedirs(a.out, exist_ok=True)
    with io.open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    with io.open(os.path.join(a.out, "regions.json"), "w", encoding="utf-8") as f:
        json.dump({"truth_regions": os.path.relpath(a.truth_regions, ROOT).replace("\\", "/"),
                   "configs": {k: {"method": CONFIGS[k][0], **CONFIGS[k][1]} for k in names},
                   "settings": {"min_css": MIN_CSS, "sx": SX, "rect_fill": RECT_FILL,
                                "match_iou": MATCH_IOU, "match_px": MATCH_PX, "same_iou": SAME_IOU,
                                "uied": D.UIED_PARAMS},
                   "totals": tot, "results": res}, f, ensure_ascii=False, indent=1)
    print(md[2])


if __name__ == "__main__":
    main()
