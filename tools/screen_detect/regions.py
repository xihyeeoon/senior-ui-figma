r"""구역 찾기 시험 - 캡처에서 바탕 상자(카드 · 배너 · 시트 · 버튼 바탕)를 찾아 구역 정답지와 견준다 (2026-10-19).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/regions.py
        [--dir results/detect/20261013-d25/final] [--out results/detect/20261019-regions]

기본 검출 경로(detect.py)와 결과는 바꾸지 않는다 - 따로 부르는 단계다. 유료 호출 없음. 구역 정답지는
truth_regions.py 가 먼저 만든 <out>/truth_regions.json 을 읽는다. 단위(이은 화면 3 + 낱장 10)마다 센다.

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
                모두 12px 안. 바탕 상자(control=false)와 조작 상자(버튼 · 칸)를 따로도 센다
  정답에 없는 구역  찾은 구역 가운데 어느 정답 구역과도 맞지 않는 것
  묶음 정확도   D2.5 final 의 요소(박스 · 글 줄 · 그림 후보) 가운데 중심이 정답 구역 안인 것마다, 그것을 담은
                가장 작은 정답 구역과 가장 작은 찾은 구역이 맞으면 맞음
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
    tb = [t["box"] for t in truth]
    hit = [any(match(t["box"], f) for f in found) for t in truth]
    extra = [f for f in found if not any(match(t, f) for t in tb)]
    group = []
    for e in elements:
        c = C.centre(e["box"])
        t = innermost(c, tb)
        if t is None:
            continue
        f = innermost(c, found)
        group.append(bool(f) and match(t, f))
    return {"truth": len(truth), "hit": sum(hit),
            "hit_box": [sum(h for h, t in zip(hit, truth) if not t["control"]),
                        sum(not t["control"] for t in truth)],
            "hit_control": [sum(h for h, t in zip(hit, truth) if t["control"]),
                            sum(t["control"] for t in truth)],
            "found": len(found), "extra": len(extra),
            "group": [sum(group), len(group)], "hits": hit}


def best_iou(t, found):
    return max((D.iou(D.xyxy(t), D.xyxy(f)) for f in found), default=0.0)


def pc(v):
    return "%d/%d (%.0f%%)" % (v[0], v[1], 100.0 * v[0] / v[1]) if v[1] else "-"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261013-d25", "final"))
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "detect", "20261019-regions"))
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args(argv)
    tr = json.load(io.open(os.path.join(a.out, "truth_regions.json"), encoding="utf-8"))
    reg_of = {s["state"]: {r["id"]: r for r in s["regions"]} for s in tr["states"]}
    dets = C.load_units(a.dir)
    images = {n: TRG.unit_image(d, a.captures) for n, d in dets.items()}
    cache = {}
    res = {}
    for cfg, (method, p) in CONFIGS.items():
        res[cfg] = {}
        for n, det in dets.items():
            u = tr["units"][n]
            truth = [dict(r, **{k: reg_of[u["state"]][r["id"]][k] for k in ("text", "cls")})
                     for r in u["regions"] if r["in_unit"]]
            found = (m1(images[n], p["diff"], p["min"]) if method == "m1"
                     else m2(det, a.captures, p["block_only"], cache))
            s = score(truth, found, [e for e in det["elements"]
                                     if e["kind"] in ("box", "text", "img_candidate")])
            if n.startswith("home"):
                for key, want in (("irp", "membership"), ("ddanggyo", "땡겨요")):
                    t = next(t for t in truth if want in t["cls"] or t["text"].startswith(want))
                    s[key] = {"truth": t["id"], "hit": any(match(t["box"], f) for f in found),
                              "best_iou": round(best_iou(t["box"], found), 2)}
            s["boxes"] = found
            res[cfg][n] = s
            if not a.no_figures:
                tb = [t["box"] for t in truth]
                regs = [{"box": f, "ok": any(match(t, f) for t in tb)} for f in found]
                regs += [{"box": t, "truth": True} for t in tb]
                TRG.draw_regions(images[n], regs, os.path.join(a.out, "found", cfg, "%s.png" % n),
                                 lambda r: (0, 170, 80) if r.get("truth")
                                 else (30, 90, 230) if r["ok"] else (240, 130, 0),
                                 lambda r: None)
        print(cfg, flush=True)

    tot = lambda cfg, k: [sum(res[cfg][n][k][i] for n in dets) for i in (0, 1)]
    rows = []
    for cfg in CONFIGS:
        h = res[cfg][next(n for n in dets if n.startswith("home"))]
        rows.append([cfg, pc([sum(res[cfg][n]["hit"] for n in dets), sum(res[cfg][n]["truth"] for n in dets)]),
                     pc(tot(cfg, "hit_box")), pc(tot(cfg, "hit_control")),
                     "%d / %d" % (sum(res[cfg][n]["extra"] for n in dets), sum(res[cfg][n]["found"] for n in dets)),
                     pc(tot(cfg, "group")),
                     "%s (%.2f)" % ("예" if h["irp"]["hit"] else "아니오", h["irp"]["best_iou"]),
                     "%s (%.2f)" % ("예" if h["ddanggyo"]["hit"] else "아니오", h["ddanggyo"]["best_iou"])])
    md = ["# 구역 검출 시험 (2026-10-19)\n",
          "구역 정답지 `truth_regions.json` (truth_regions.py) 대 캡처에서 찾은 구역 (regions.py). 단위 %d개 "
          "(이은 화면 3 + 낱장 10). 맞음 = IoU %.1f 이상 또는 네 변이 모두 %dpx 안. 최소 크기 CSS %dx%d "
          "(캡처 %.0fx%.0f px), M1 의 사각형 채움 %.2f.\n"
          % (len(dets), MATCH_IOU, MATCH_PX, MIN_CSS[0], MIN_CSS[1], *min_px(1.0), RECT_FILL),
          C.table(["방법 (기준값)", "구역 재현율", "바탕 상자", "조작 상자 (버튼 · 칸)",
                   "정답에 없는 구역 / 찾은 구역", "묶음 정확도", "IRP 배너 (IoU)", "땡겨요 카드 (IoU)"], rows),
          "\n묶음 정확도 = D2.5 final 의 요소 가운데 중심이 정답 구역 안인 것마다, 담은 가장 작은 정답 구역과 "
          "가장 작은 찾은 구역이 맞은 비율.\n",
          "\n## 단위별 구역 재현율 · 정답에 없는 구역\n"]
    md.append(C.table(["단위", "상태", "정답 구역"] + list(CONFIGS),
                      [[n, tr["units"][n]["state"], res["M1-diff2"][n]["truth"]]
                       + ["%d · +%d" % (res[c][n]["hit"], res[c][n]["extra"]) for c in CONFIGS]
                       for n in dets]))
    md.append("\n칸 = 맞은 정답 구역 · 정답에 없는 구역. 그림: `found/<방법>/<단위>.png` (파랑 = 정답과 맞음, "
              "주황 = 정답에 없음, 초록 = 정답 구역), 정답만: `truth_figures/<단위>.png`.\n")
    with io.open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    with io.open(os.path.join(a.out, "regions.json"), "w", encoding="utf-8") as f:
        json.dump({"configs": {k: {"method": v[0], **v[1]} for k, v in CONFIGS.items()},
                   "settings": {"min_css": MIN_CSS, "sx": SX, "rect_fill": RECT_FILL,
                                "match_iou": MATCH_IOU, "match_px": MATCH_PX, "same_iou": SAME_IOU,
                                "uied": D.UIED_PARAMS},
                   "results": res}, f, ensure_ascii=False, indent=1)
    print("\n".join(md[2:3]))


if __name__ == "__main__":
    main()
