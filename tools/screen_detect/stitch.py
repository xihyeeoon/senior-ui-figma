r"""스크롤 조각 잇기 - 한 화면을 스크롤하며 찍은 캡처 여러 장을 한 장 좌표계로 (시험 D2 규칙 3).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/stitch.py
        [--dir results/detect/20261012-d2] [--captures inputs/captures/transfer]

detect.py 의 <dir>/<캡처>.json 과 캡처 PNG 를 읽어 GROUPS 의 화면마다

    <dir>/stitched/<화면>.json         이은 요소 목록 (detect.py 와 같은 모양 + fragments)
    <dir>/overlay/stitched/<화면>.png  이어 붙인 확인 그림

을 쓴다. 어느 캡처가 한 화면의 조각인지는 연구자가 정한다 (GROUPS - 캡처 이름 순이 스크롤 순).

이웃한 두 조각 A → B 마다

  1. 고정 띠 - 같은 높이의 화소 줄이 같은 것(줄 평균 차 < BAND_DIFF)을 위에서부터 · 아래에서부터
     센다. 상태바 · 시트 머리 · 탭바처럼 스크롤해도 그 자리에 있는 것이다.
  2. 세로 어긋남 - 두 조각의 고정 띠 밖에 있는 OCR 글 가운데 같은 글 · 같은 x(± ANCHOR_X) ·
     같은 너비(± ANCHOR_X)인 짝을 닻으로, B 의 글이 A 보다 얼마나 위에 있는지(yA - yB > 0)의
     최빈값(± ANCHOR_TOL 안의 중앙값)을 쓴다. 닻이 없으면 화소로 찾는다 (겹치는 띠 밖 줄의 평균
     차가 가장 작은 어긋남) - 어느 쪽으로 정했는지 method 에 남긴다.
     글 닻이 없으면 먼저 잘린 칸(shift_by_boxes)으로, 그것도 없으면 화소로 찾는다 - 칸이 되풀이되는
     목록에서는 한 줄 어긋난 자리도 비슷해 보이므로 화소는 뒤 순서다. 화소로도 어느 줄도 어긋나지
     않는 자리가 없으면 두 조각이 겹치지 않았다고 보고 잇는다 ("겹침 없음 가정").

요소는 조각마다 offset 만큼 내려 놓는다. 앞 조각이 아닌 조각의 위 고정 띠 안 요소와 마지막이
아닌 조각의 아래 고정 띠 안 요소는 다른 조각에 같은 것이 있으므로 뺀다 (dropped_fixed). 겹치는
부분에서 같은 요소(글: 같은 글 · 중심 MERGE_PX 안, 그 밖: 같은 종류 · IoU MERGE_IOU 이상)는
하나로 합친다 - 이름 붙은 것, 넓은 것(덜 잘린 것)을 남긴다 (merged). 조각 경계에서 잘려 어느
조각에서도 이름이 붙지 않은 로고 후보는 이은 좌표에서 이름을 붙인다 (name_across).
"""
import argparse
import io
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import detect as D  # noqa: E402  (확인 그림을 같은 모양으로 그린다)

GROUPS = {"home": ["01a", "01b", "01c"],
          "bank": ["05a", "05b", "05c"],
          "bank-tab-sec": ["06a", "06b", "06c"]}

BAND_DIFF = 2.0      # 같은 줄로 보는 화소 평균 차 (0~255)
ANCHOR_X = 8         # 닻 짝의 x · 너비 차 (캡처 픽셀)
ANCHOR_TOL = 6       # 최빈 어긋남에서 이만큼 안의 닻을 함께 쓴다
MERGE_PX = 20        # 같은 글로 합치는 중심 거리
MERGE_IOU = 0.5      # 같은 박스로 합치는 IoU
PIXEL_SURE = 3.0     # 화소로 맞춘 자리에서 겹친 줄마다의 평균 차가 모두 이 이하여야 맞은 것
PIXEL_ROWS = 20      # 화소로 맞출 때 겹친 줄이 적어도 이만큼
NAME_DX = 30         # 이은 화면에서 이름 붙이기 - 로고와 칸 글의 가로 중심 차
NAME_DY = 20         # 그리고 세로 거리가 이름 붙은 로고들의 중앙값에서 벗어나도 되는 만큼


def norm(s):
    return re.sub(r"[\W_]+", "", (s or "").lower())


def bands(a, b):
    """두 조각의 (위 고정 띠 높이, 아래 고정 띠 높이) - 같은 줄이 이어지는 만큼."""
    import numpy as np
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).mean(axis=1)
    same = diff < BAND_DIFF
    top = int(np.argmin(same)) if not same.all() else len(same)
    bottom = int(np.argmin(same[::-1])) if not same.all() else len(same)
    return top, bottom


def shift_by_text(ea, eb, top, bottom, h):
    """닻 글로 찾은 어긋남 (없으면 None) 과 쓴 닻 수."""
    def free(e):
        cy = e["box"][1] + e["box"][3] / 2
        return e["kind"] == "text" and top <= cy <= h - bottom and len(norm(e["text"])) >= 2
    votes = []
    for a in filter(free, ea):
        for b in filter(free, eb):
            if (norm(a["text"]) == norm(b["text"]) and abs(a["box"][0] - b["box"][0]) <= ANCHOR_X
                    and abs(a["box"][2] - b["box"][2]) <= ANCHOR_X):
                d = a["box"][1] - b["box"][1]
                if d > 0:
                    votes.append(d)
    if not votes:
        return None, 0
    mode = max(votes, key=lambda d: sum(abs(d - v) <= ANCHOR_TOL for v in votes))
    near = [v for v in votes if abs(v - mode) <= ANCHOR_TOL]
    return int(round(statistics.median(near))), len(near)


def shift_by_boxes(ea, eb, top, bottom, h):
    """잘린 칸으로 찾은 어긋남 (없으면 None) 과 쓴 짝 수. 겹치는 글이 없을 때 - 목록의 한 줄이
    A 에서는 아래가(로고만), B 에서는 위가(이름만) 잘려 보이면, 같은 x · 너비의 잘리지 않은
    칸 높이로 그 칸의 B 쪽 윗변을 짐작해 A 의 윗변과 맞춘다."""
    boxes = [e for e in ea + eb if e["kind"] == "box"]
    cut_a = [e for e in ea if e["kind"] == "box" and e["box"][1] + e["box"][3] >= h - bottom - 3
             and e["box"][1] > top]
    cut_b = [e for e in eb if e["kind"] == "box" and e["box"][1] <= top + 3
             and e["box"][1] + e["box"][3] < h - bottom]
    votes = []
    for a in cut_a:
        for b in cut_b:
            if abs(a["box"][0] - b["box"][0]) > ANCHOR_X or abs(a["box"][2] - b["box"][2]) > ANCHOR_X:
                continue
            full = [o["box"][3] for o in boxes if o is not a and o is not b
                    and abs(o["box"][0] - a["box"][0]) <= ANCHOR_X
                    and abs(o["box"][2] - a["box"][2]) <= ANCHOR_X
                    and o["box"][3] > max(a["box"][3], b["box"][3]) + 3]
            if full:
                d = a["box"][1] - (b["box"][1] + b["box"][3] - statistics.median(full))
                if d > 0:
                    votes.append(d)
    if not votes:
        return None, 0
    mode = max(votes, key=lambda d: sum(abs(d - v) <= ANCHOR_TOL for v in votes))
    near = [v for v in votes if abs(v - mode) <= ANCHOR_TOL]
    return int(round(statistics.median(near))), len(near)


def shift_by_pixels(a, b, top, bottom):
    """화소로 찾은 어긋남 (없으면 None). A 의 띠 밖 줄 y+d 와 B 의 줄 y 를 겹쳐, 줄마다의 평균 차가
    모두 PIXEL_SURE 이하인(어느 줄도 어긋나지 않은) d 가운데 전체 평균 차가 가장 작은 것.
    겹친 줄이 PIXEL_ROWS 보다 적은 d 는 보지 않는다."""
    import numpy as np
    h = a.shape[0]
    lo, hi = top, h - bottom
    best = None
    for d in range(1, hi - lo - PIXEL_ROWS + 1):
        n = hi - lo - d
        rows = np.abs(a[lo + d:hi].astype(np.int16) - b[lo:lo + n].astype(np.int16)).mean(axis=1)
        if rows.max() <= PIXEL_SURE and (best is None or rows.mean() < best[1]):
            best = (d, rows.mean())
    return best[0] if best else None


def iou(p, q):
    ax, ay, aw, ah = p
    bx, by, bw, bh = q
    i = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0, min(ay + ah, by + bh) - max(ay, by))
    u = aw * ah + bw * bh - i
    return i / u if u else 0


def same(e, f):
    if e["kind"] != f["kind"]:
        return False
    if e["kind"] == "text":
        ce = (e["box"][0] + e["box"][2] / 2, e["box"][1] + e["box"][3] / 2)
        cf = (f["box"][0] + f["box"][2] / 2, f["box"][1] + f["box"][3] / 2)
        return (norm(e["text"]) == norm(f["text"])
                and abs(ce[0] - cf[0]) <= MERGE_PX and abs(ce[1] - cf[1]) <= MERGE_PX)
    return iou(e["box"], f["box"]) >= MERGE_IOU


def better(e, f):
    """합칠 때 남길 쪽이 e 인가 - 이름 붙은 것, 그다음 넓은 것(덜 잘린 것)."""
    return (bool(e.get("name")), e["box"][2] * e["box"][3]) >= \
           (bool(f.get("name")), f["box"][2] * f["box"][3])


def name_across(out):
    """조각 경계에서 잘린 칸 - 로고는 앞 조각에, 칸 글은 뒤 조각에 보여 어느 조각에서도 이름이
    붙지 않은 그림 후보에 이은 좌표에서 이름을 붙인다 (D2 규칙 2 를 이은 화면에 한 번 더). 이미
    이름 붙은 후보들의 "로고 중심 → 칸 글 중심" 세로 거리의 중앙값만큼 아래, 같은 열(가로 중심
    ± NAME_DX)에 있고 아직 어느 로고의 칸 글도 아닌 글이 있으면 "<그 글> 로고". 이름 붙은 후보가
    GRID_MIN 개 이상인 화면(로고 목록)에서만. 붙인 이름 수를 돌려준다."""
    cen = lambda e: (e["box"][0] + e["box"][2] / 2, e["box"][1] + e["box"][3] / 2)
    texts = {e["id"]: e for e in out if e["kind"] == "text"}
    cands = [e for e in out if e["kind"] == "img_candidate"]
    pairs = [(c, texts[c["label"]]) for c in cands if c.get("name") and c.get("label") in texts]
    if len(pairs) < D.GRID_MIN:
        return 0
    gap = statistics.median(cen(t)[1] - cen(c)[1] for c, t in pairs)
    used = {t["id"] for _, t in pairs}
    n = 0
    for c in cands:
        if c.get("name"):
            continue
        cx, cy = cen(c)
        near = [t for t in texts.values() if t["id"] not in used
                and abs(cen(t)[0] - cx) <= NAME_DX and abs(cen(t)[1] - cy - gap) <= NAME_DY]
        if near:
            t = min(near, key=lambda t: abs(cen(t)[1] - cy - gap))
            c.update(name="%s 로고" % t["text"].strip(), label=t["id"], named_in="stitched")
            used.add(t["id"])
            n += 1
    return n


def stitch(name, caps, folder, captures):
    import numpy as np
    from PIL import Image
    dets = [json.load(io.open(os.path.join(folder, c + ".json"), encoding="utf-8")) for c in caps]
    imgs = [Image.open(os.path.join(captures, c + ".png")).convert("RGB") for c in caps]
    grays = [np.asarray(i.convert("L")) for i in imgs]
    w, h = imgs[0].size
    frags = [{"capture": caps[0], "offset": 0, "top_band": 0, "bottom_band": 0,
              "shift": 0, "method": None, "anchors": 0, "overlap_rows": 0}]
    for k in range(1, len(caps)):
        top, bottom = bands(grays[k - 1], grays[k])
        d, n = shift_by_text(dets[k - 1]["elements"], dets[k]["elements"], top, bottom, h)
        method = "text"
        if d is None:
            d, n = shift_by_boxes(dets[k - 1]["elements"], dets[k]["elements"], top, bottom, h)
            method = "boxes"
        if d is None:
            d, method = shift_by_pixels(grays[k - 1], grays[k], top, bottom), "pixels"
        if d is None:
            # 맞는 겹침이 없다 - 겹치지 않았다고 보고 B 의 띠 밖 첫 줄을 A 의 띠 밖 끝 줄 바로 뒤에
            d, method = (h - bottom) - top, "겹침 없음 가정"
        frags[k - 1]["bottom_band"] = max(frags[k - 1]["bottom_band"], bottom)
        frags.append({"capture": caps[k], "offset": frags[k - 1]["offset"] + d, "top_band": top,
                      "bottom_band": 0, "shift": d, "method": method, "anchors": n,
                      "overlap_rows": (h - bottom) - top - d})
    # 마지막 조각은 아래 띠를 지우지 않는다 - 거기가 진짜 아래(탭바)다
    height = frags[-1]["offset"] + h

    canvas = Image.new("RGB", (w, height), "white")
    for f, im in zip(frags, imgs):
        lo, hi = f["top_band"], h - f["bottom_band"]
        if f is frags[0]:
            lo = 0
        if f is frags[-1]:
            hi = h
        canvas.paste(im.crop((0, lo, w, hi)), (0, f["offset"] + lo))

    out, alias, merged, dropped = [], {}, 0, 0
    for f, det in zip(frags, dets):
        c = f["capture"]
        for e in det["elements"]:
            cy = e["box"][1] + e["box"][3] / 2
            e = dict(e, id="%s:%s" % (c, e["id"]), capture=c)
            for key in ("in_box", "label"):
                if e.get(key):
                    e[key] = "%s:%s" % (c, e[key])
            if e.get("text_in"):
                e["text_in"] = ["%s:%s" % (c, t) for t in e["text_in"]]
            fixed_top = f is not frags[0] and cy < f["top_band"]
            fixed_bottom = f is not frags[-1] and cy > h - f["bottom_band"]
            if not (fixed_top or fixed_bottom):
                e["box"] = [e["box"][0], e["box"][1] + f["offset"], e["box"][2], e["box"][3]]
            hit = next((o for o in out if same(o, e)), None)
            if fixed_top or fixed_bottom:
                # 고정 띠 안 - 다른 조각의 같은 요소로 보낸다 (없으면 그냥 뺀다)
                dropped += 1
                alias[e["id"]] = hit["id"] if hit else None
                continue
            if hit is None:
                out.append(e)
                continue
            merged += 1
            if better(e, hit):
                alias[hit["id"]] = e["id"]
                out[out.index(hit)] = e
            else:
                alias[e["id"]] = hit["id"]

    def resolve(i):
        seen = set()
        while i in alias and i not in seen:
            seen.add(i)
            i = alias[i]
        return i
    keep = {e["id"] for e in out}
    for e in out:
        for key in ("in_box", "label"):
            if e.get(key):
                e[key] = resolve(e[key]) if resolve(e[key]) in keep else None
        if e.get("text_in"):
            e["text_in"] = [t for t in (resolve(t) for t in e["text_in"]) if t in keep]
    named = name_across(out)
    # 조각들의 아이콘 목록도 합쳐 남긴다 (기록)
    moved = [dict(m, capture=f["capture"]) for f, det in zip(frags, dets)
             for m in det.get("icon_from_ocr", [])]
    os.makedirs(os.path.join(folder, "stitched"), exist_ok=True)
    res = {"screen": name, "captures": caps, "size": [w, height], "fragments": frags,
           "merged": merged, "dropped_fixed": dropped, "named_across": named, "elements": out, "icon_from_ocr": moved,
           "settings": {"band_diff": BAND_DIFF, "anchor_x": ANCHOR_X, "anchor_tol": ANCHOR_TOL,
                        "merge_px": MERGE_PX, "merge_iou": MERGE_IOU}}
    with io.open(os.path.join(folder, "stitched", name + ".json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    shown = [dict(e, id=e["id"].replace(":", ".")) for e in out]
    D.overlay(canvas, shown, os.path.join(folder, "overlay", "stitched", name + ".png"))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261012-d2"))
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    a = ap.parse_args(argv)
    for name, caps in GROUPS.items():
        r = stitch(name, caps, a.dir, a.captures)
        print(name, r["size"], "merged", r["merged"], "dropped_fixed", r["dropped_fixed"],
              [(f["capture"], f["offset"], f["top_band"], f["bottom_band"], f["method"],
                f["anchors"]) for f in r["fragments"]])


if __name__ == "__main__":
    main()
