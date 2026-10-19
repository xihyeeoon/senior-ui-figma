r"""그림 자리 놓침 진단 - 정답의 그림 자리 가운데 의미 층이 image 로 잡지 못한 것을 단계별로 따라간다.

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/miss_diag.py
        [--dir results/detect/20261013-d25/final] [--semantic results/detect/20261013-d3b]
        [--out results/detect/20261019-miss]

읽기만 한다 - 기본 실행 경로(detect.py · compare.py)와 앞 결과는 바꾸지 않는다. 쓰는 것은 <out>/ 뿐.
유료 호출 없음 - 의미 층은 다시 돌리지 않고 <semantic>/ 의 답을 읽는다. 검출기(icon_detect_v3)만
GPU 로 다시 돌린다 (설명 모델 · OCR 은 쓰지 않는다 - OCR 은 <dir> 위의 _ocr.json 을 읽는다).

1. 놓친 것 - compare.py 와 같은 셈 (정답 그림 자리마다 닿는 요소 가운데 kind=image 가 없으면 놓침).
   놓친 것마다 옮긴 정답 자리, 닿은 요소와 그 kind, 자리 곁의 최종 요소를 적는다.
2. 원 출력 따라가기 - 놓친 자리의 캡처마다 검출기를 다시 돌려 단계별로 그 자리의 박스가 남았는지:
     raw      NMS 전 (원본 · CLAHE 사본, 점수 문턱 conf)
     nms      검출기 NMS (IoU CFG nms) 뒤 - 지웠으면 지운 박스
     pass     원본 · 사본 합치기 (IoU PASS_IOU) 뒤 - 같은 박스로 합쳐졌으면 남은 쪽
     overlap  겹친 박스 정리 (detect.merge 의 첫 규칙) 뒤 - 지웠으면 지운 까닭이 된 박스
     intext   OCR 글 박스 안 박스 버림 (detect.merge 의 둘째 규칙) 뒤 - 지웠으면 그 글
     final    최종 JSON 에 같은 자리(IoU 0.5)의 요소가 있나
   "그 자리의 박스" = 중심이 옮긴 자리(변마다 NEAR/2 넓힘) 안이고 넓이가 자리의 MAX_AREA 배 이하인 것
   (칸 박스는 빼고 그림 자체만). 점수 문턱 conf 0.1 (기본값) 과 0.01 (민감도) 두 번.
   --text 08:보내기 처럼 주면 그 OCR 글을 감싸는 박스(글 넓이의 INSIDE 이상이 박스 안)를 같은 단계로
   따라간다 (박스 재현율의 놓침).
3. 가상 설정 (--virtual) - 기본 설정을 바꾸지 않고 <out>/<이름>/ 에만 detect → flags → stitch →
   compare 를 다시 돌린다 (detect.py 는 그대로, 이 프로세스에서 함수만 바꿔 끼운다):
     base      바꾸지 않음 (같은 코드 · 같은 OCR 캐시로 다시 - 견줄 바탕)
     softnms   검출기 NMS 를 Soft-NMS 로 (가우스, sigma SOFT_SIGMA) - 겹친 박스의 점수를 깎되 지우지
               않고, 깎인 점수가 점수 문턱(conf) 아래인 것만 버린다
     kind      "종류가 다르면 안 지우기" - 한 박스가 다른 박스 안에 들고(작은 쪽 넓이의 INSIDE 이상)
               넓이가 KIND_RATIO 배 이하면 칸과 그 안의 아이콘 · 로고로 보고 NMS 에서 서로 지우지 않는다
               (겹친 박스 정리는 IoU 규칙이라 이런 짝을 지우지 않는다 - 바꿀 것이 없다)
     textkeep  (요청 밖 참고) OCR 글 박스 안 박스 버림을 두 글자 이하 글에서는 하지 않는다 - 아이콘을
               글자로 읽은 것("8+")이 아이콘 박스를 지우지 않게
   의미 층은 다시 돌리지 않는다 - 견주기는 박스 수준(그 자리에 박스 · 그림 후보가 있나, compare 의
   박스 재현율 · 남는 박스)이다. 확인 그림(overlay/)은 지운다 (README - 설정 시험은 final 것만 남긴다).
"""
import argparse
import io
import json
import math
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import compare as C  # noqa: E402
import detect as D  # noqa: E402

MAX_AREA = 4.0     # 그 자리의 박스로 보는 넓이 상한 (옮긴 자리 넓이의 배수) - 칸 박스를 뺀다
CONFS = (0.1, 0.01)
SOFT_SIGMA = 0.5   # Soft-NMS 가우스 폭 (Bodla et al. 2017 의 기본값)
KIND_RATIO = 0.5   # 작은 박스 넓이가 큰 박스의 이 배 이하면 다른 종류 (칸 대 아이콘)
SHORT_TEXT = 2     # textkeep - 이 글자 수 이하 글 안의 박스는 버리지 않는다
VIRTUAL = ("base", "softnms", "kind", "textkeep")


def missed(dets, sem, truth):
    """compare.roles 와 같은 셈으로 놓친 그림 자리 [{unit, state, label, rect, els, kinds}]."""
    states = {s["state"]: s for s in truth["states"]}
    pairs = C.pairing(truth, dets)
    pick = {n: pairs[n][0]["state"] for n in dets}
    by = {}
    for n in dets:
        st = states[pick[n]]
        per = C.judge_capture(dets[n], st)
        frame = C.Frame(st, dets[n])
        slots = {s["label"]: s for s in st["image_slots"]}
        ans = sem.get(n) or {}
        for r in per["rows"]:
            if r["kind"] != "slot":
                continue
            m = by.setdefault((pick[n], r["key"]), {"state": pick[n], "label": r["label"],
                                                    "hits": [], "units": []})
            m["units"].append({"unit": n, "rect": frame.map(slots[r["label"]]),
                               "in_frame": r["in_frame"], "els": r["els"],
                               "kinds": {i: (ans.get(i) or {}).get("kind") for i in r["els"]}})
            m["hits"] += [(ans.get(i) or {}).get("kind") for i in r["els"]]
    return [m for m in by.values() if "image" not in m["hits"]], len(by)


def captures_of(det, rect, name, size_of):
    """이은 화면 좌표의 자리 → [(캡처, 그 캡처 좌표의 자리)]. 낱장이면 그대로."""
    if "fragments" not in det:
        return [(name, rect)]
    cy = rect[1] + rect[3] / 2
    out = []
    for f in det["fragments"]:
        h = size_of(f["capture"])[1]
        if f["offset"] <= cy < f["offset"] + h:
            out.append((f["capture"], [rect[0], rect[1] - f["offset"], rect[2], rect[3]]))
    return out


def at(box, rect):
    """box(xyxy) 가 그 자리의 박스인가."""
    x, y, w, h = rect
    c = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    k = C.NEAR / 2
    return (x - k <= c[0] <= x + w + k and y - k <= c[1] <= y + h + k
            and D.area(box) <= MAX_AREA * w * h)


def r4(b):
    return [int(round(v)) for v in b]


class Trace:
    """검출기를 단계별로 다시 돌린다 (detect.detect_all · merge 와 같은 순서)."""

    def __init__(self, device):
        sys.path.insert(0, D.OMNIPARSER)
        from util.yolov9 import YOLOv9Detector
        import torch
        from torchvision.ops import nms
        self.torch, self.nms = torch, nms
        self.det = YOLOv9Detector(model_path=D.DETECT_WEIGHTS, device=device)

    def raw(self, image, conf):
        """NMS 전 박스 [(xyxy, 점수)] - predict 의 NMS 를 IoU 1.0 으로 꺼서."""
        r = self.det.predict(image, conf=conf, iou=1.0, imgsz=D.IMGSZ, max_det=10 ** 6)[0].boxes
        return [([float(v) for v in b], float(s)) for b, s in zip(r.xyxy.tolist(), r.conf.tolist())]

    def run(self, image, texts, conf):
        """단계마다 박스 목록과, 지운 박스마다 지운 까닭."""
        passes = [("detector", image)] + ([("detector:clahe", D.clahe(image))] if D.CFG["clahe"] else [])
        raw, after_nms, why = [], [], {}
        for src, im in passes:
            bs = self.raw(im, conf)
            if not bs:
                continue
            t = self.torch.tensor([b for b, _ in bs])
            s = self.torch.tensor([v for _, v in bs])
            keep = self.nms(t, s, D.CFG["nms"]).tolist()
            kept = [bs[k] for k in keep]
            for b, v in bs:
                item = (tuple(b), v, src)
                raw.append(item)
                if (b, v) in kept:
                    after_nms.append(item)
                else:
                    # 지운 박스 = 점수가 더 높고 IoU 가 문턱을 넘는 남은 박스 가운데 점수가 가장 높은 것
                    by = max((k for k in kept if D.iou(b, k[0]) > D.CFG["nms"] and k[1] >= v),
                             key=lambda k: k[1], default=None)
                    why[item] = ("nms", by and (r4(by[0]), round(by[1], 3), src,
                                                round(D.iou(b, by[0]), 2)))
        rank = {"detector": 3, "detector:clahe": 1}
        after_pass = []
        for item in sorted(after_nms, key=lambda f: (rank[f[2]], f[1]), reverse=True):
            same = next((k for k in after_pass if D.iou(item[0], k[0]) >= D.PASS_IOU), None)
            if same is None:
                after_pass.append(item)
            else:
                why[item] = ("pass", (r4(same[0]), round(same[1], 3), same[2],
                                      round(D.iou(item[0], same[0]), 2)))
        ov = D.overlap if D.CFG["overlap"] == "omniparser" else D.iou
        after_ov, after_text = [], []
        for item in after_pass:
            b1 = item[0]
            by = [k for k in after_pass if k is not item and ov(b1, k[0]) > D.OVERLAP_IOU
                  and D.area(b1) > D.area(k[0])]
            if by:
                k = max(by, key=lambda k: ov(b1, k[0]))
                why[item] = ("overlap", (r4(k[0]), round(k[1], 3), k[2], round(ov(b1, k[0]), 2)))
                continue
            after_ov.append(item)
            inside = [t for t in texts if D.inside(b1, t["xyxy"])]
            if inside:
                why[item] = ("intext", inside[0]["text"])
                continue
            after_text.append(item)
        return {"raw": raw, "nms": after_nms, "pass": after_pass, "overlap": after_ov,
                "intext": after_text}, why


STAGES = ("raw", "nms", "pass", "overlap", "intext")


def trace_spot(stages, why, rect, final_boxes):
    """그 자리의 박스가 단계마다 몇 개 남았나, 가장 점수 높은 것, 끝까지 간 것이 없으면 어디서 왜."""
    out = {}
    for k in STAGES:
        hits = [it for it in stages[k] if at(it[0], rect)]
        out[k] = {"n": len(hits),
                  "best": max(([r4(it[0]), round(it[1], 3), it[2]] for it in hits),
                              key=lambda x: x[1], default=None)}
    lost = {}
    for it in stages["raw"]:
        if at(it[0], rect) and it in why:
            lost.setdefault(why[it][0], []).append({"box": r4(it[0]), "score": round(it[1], 3),
                                                    "src": it[2], "by": why[it][1]})
    for k in lost:
        lost[k] = sorted(lost[k], key=lambda x: -x["score"])[:5]
    out["lost"] = lost
    out["final"] = [e["id"] for e in final_boxes if at(D.xyxy(e["box"]), rect)]
    return out


def trace_text(stages, why, tb, final_boxes):
    """OCR 글 tb 를 감싸는 박스가 단계마다 몇 개 남았나 (trace_spot 과 같은 꼴)."""
    holds = lambda b: D.inside(tb["xyxy"], b)
    out = {}
    for k in STAGES:
        hits = [it for it in stages[k] if holds(it[0])]
        out[k] = {"n": len(hits),
                  "best": max(([r4(it[0]), round(it[1], 3), it[2]] for it in hits),
                              key=lambda x: x[1], default=None)}
    lost = {}
    for it in stages["raw"]:
        if holds(it[0]) and it in why:
            lost.setdefault(why[it][0], []).append({"box": r4(it[0]), "score": round(it[1], 3),
                                                    "src": it[2], "by": why[it][1]})
    out["lost"] = {k: sorted(v, key=lambda x: -x["score"])[:5] for k, v in lost.items()}
    out["final"] = [e["id"] for e in final_boxes if e["kind"] == "box" and holds(D.xyxy(e["box"]))]
    return out


# --------------------------------------------------------------------------- #
# 가상 설정 - detect.py 의 함수를 이 프로세스에서만 바꿔 끼운다
# --------------------------------------------------------------------------- #
def soft_nms(boxes, sigma, floor):
    """[(xyxy, 점수)] → 가우스 Soft-NMS 뒤 점수가 floor 이상인 것."""
    left = [list(b) for b in boxes]
    out = []
    while left:
        k = max(range(len(left)), key=lambda i: left[i][1])
        b, s = left.pop(k)
        out.append((b, s))
        left = [[c, t * math.exp(-D.iou(b, c) ** 2 / sigma)] for c, t in left]
        left = [x for x in left if x[1] >= floor]
    return out


def kind_nms(boxes, thr):
    """NMS 와 같되, 한 박스가 다른 박스 안에 든 칸 · 아이콘 짝(different_kind)은 서로 지우지 않는다."""
    out = []
    for b, s in sorted(boxes, key=lambda x: -x[1]):
        if all(D.iou(b, k) <= thr or different_kind(b, k) for k, _ in out):
            out.append((b, s))
    return out


def different_kind(a, b):
    small, big = (a, b) if D.area(a) <= D.area(b) else (b, a)
    return D.area(small) <= KIND_RATIO * D.area(big) and D.inside(small, big)


def patch(name):
    if name in ("softnms", "kind"):
        def detect(self, path):
            r = self.det.predict(path, conf=D.CFG["conf"], iou=1.0, imgsz=self.imgsz,
                                 max_det=10 ** 6)[0].boxes
            bs = [([float(v) for v in b], float(s)) for b, s in zip(r.xyxy.tolist(), r.conf.tolist())]
            return (soft_nms(bs, SOFT_SIGMA, D.CFG["conf"]) if name == "softnms"
                    else kind_nms(bs, D.CFG["nms"]))
        D.Models.detect = detect
    elif name == "textkeep":
        D.merge = _merge_textkeep


def _merge_textkeep(det, texts):
    """detect.merge 와 같되 둘째 규칙(글 박스 안 박스 버림)을 SHORT_TEXT 글자 이하 글에서는 하지 않는다."""
    keep = []
    ov = D.overlap if D.CFG["overlap"] == "omniparser" else D.iou
    for i, (b1, s1) in enumerate(det):
        if any(i != j and ov(b1, b2) > D.OVERLAP_IOU and D.area(b1) > D.area(b2)
               for j, (b2, _) in enumerate(det)):
            continue
        if any(D.inside(b1, t["xyxy"]) for t in texts if len(t["text"].strip()) > SHORT_TEXT):
            continue
        keep.append((b1, s1))
    owner = {}
    for ti, t in enumerate(texts):
        hits = [k for k, (b, _) in enumerate(keep) if D.inside(t["xyxy"], b)]
        if hits:
            owner[ti] = min(hits, key=lambda k: D.area(keep[k][0]))
    return keep, owner


def run(args):
    r = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    if r.returncode:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit("실패: %s" % " ".join(args))


def virtual(name, root, a):
    out = os.path.join(root, name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    tool = lambda t: os.path.join(HERE, t)
    ocr = a.ocr or os.path.join(os.path.dirname(a.dir), "_ocr.json")
    run([tool("miss_diag.py"), "--detect-as", name, "--out", out, "--ocr", ocr])
    run([tool("flags.py"), "--dir", out])
    run([tool("stitch.py"), "--dir", out])
    shutil.copy(os.path.join(a.dir, "truth.json"), os.path.join(out, "truth.json"))
    run([tool("compare.py"), "--dir", out])
    shutil.rmtree(os.path.join(out, "overlay"), ignore_errors=True)
    with io.open(os.path.join(out, "_virtual.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name, "soft_sigma": SOFT_SIGMA, "kind_ratio": KIND_RATIO,
                   "inside": D.INSIDE, "short_text": SHORT_TEXT,
                   "detect": "detect.py 기본값 (%s) + 바꿔 끼운 함수" % json.dumps(D.CFG)}, f,
                  ensure_ascii=False, indent=1)


def revived(diag, folder):
    """놓친 자리마다 가상 설정의 최종 요소(박스 · 그림 후보)가 그 자리에 있나 - 캡처 좌표로."""
    out = []
    for r in diag["rows"]:
        hit = []
        for c in r["captures"]:
            p = os.path.join(folder, c["capture"] + ".json")
            els = json.load(io.open(p, encoding="utf-8"))["elements"]
            hit += ["%s:%s" % (c["capture"], e["id"]) for e in els
                    if e["kind"] in ("box", "img_candidate") and at(D.xyxy(e["box"]), c["rect"])]
        out.append({"state": r["state"], "label": r["label"], "hit": hit})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261013-d25", "final"))
    ap.add_argument("--semantic", default=os.path.join(ROOT, "results", "detect", "20261013-d3b"))
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    ap.add_argument("--ocr", help="OCR 캐시 (기본 <dir>/../_ocr.json)")
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "detect", "20261019-miss"))
    ap.add_argument("--text", action="append", default=[], help="<캡처>:<글> - 그 글을 감싸는 박스도 따라간다")
    ap.add_argument("--virtual", nargs="*", choices=VIRTUAL, help="가상 설정 (이름이 없으면 전부)")
    ap.add_argument("--detect-as", choices=VIRTUAL, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    if a.detect_as:
        # 가상 설정의 detect 단계 (virtual() 이 부른다) - 함수를 바꿔 끼우고 detect.py 그대로
        patch(a.detect_as)
        D.main(["--out", a.out, "--ocr-cache", a.ocr])
        return

    from PIL import Image
    import torch
    truth = json.load(io.open(os.path.join(a.semantic, "truth.json"), encoding="utf-8"))
    dets = C.load_units(a.dir)
    sem, _ = C.load_semantic(a.semantic)
    miss, total = missed(dets, sem, truth)
    ocr = json.load(io.open(a.ocr or os.path.join(os.path.dirname(a.dir), "_ocr.json"),
                            encoding="utf-8"))
    run_ = json.load(io.open(os.path.join(a.dir, "_run.json"), encoding="utf-8"))["settings"]
    D.CFG.update(conf=run_["box_threshold"], nms=run_["nms_iou"], clahe=run_["clahe"],
                 overlap=run_["overlap_rule"])
    size_of = lambda c: Image.open(os.path.join(a.captures, c + ".png")).size
    single = lambda c: json.load(io.open(os.path.join(a.dir, c + ".json"), encoding="utf-8"))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tr = Trace(device)
    cache = {}

    def prepared(cap):
        image = Image.open(os.path.join(a.captures, cap + ".png")).convert("RGB")
        items = ocr["images"][cap + ".png"]["items"]
        texts = [t for t in items if t["score"] >= D.TEXT_THRESHOLD and t["text"].strip()]
        icons = D.icon_texts(texts)
        real = [t for i, t in enumerate(texts) if i not in icons]
        fin = [e for e in single(cap)["elements"] if e["kind"] in ("box", "img_candidate")]
        return image, real, fin

    def staged(cap, conf, image, real):
        if (cap, conf) not in cache:
            cache[(cap, conf)] = tr.run(image, real, conf)
        return cache[(cap, conf)]

    rows = []
    for m in miss:
        for u in m["units"]:
            det = dets[u["unit"]]
            near = []
            if u["rect"]:
                near = [{"id": e["id"], "kind": e["kind"], "box": e["box"], "text": e.get("text"),
                         "caption": e.get("caption"), "name": e.get("name"),
                         "flags": e.get("flags"),
                         "sem_kind": ((sem.get(u["unit"]) or {}).get(e["id"]) or {}).get("kind")}
                        for e in det["elements"] if C.within(C.centre(e["box"]), u["rect"], C.NEAR)]
            caps = []
            for cap, rect in (captures_of(det, u["rect"], u["unit"], size_of) if u["rect"] else []):
                image, real, fin = prepared(cap)
                spot = {"capture": cap, "rect": r4(rect)}
                for conf in CONFS:
                    spot["conf %g" % conf] = trace_spot(*staged(cap, conf, image, real), rect, fin)
                caps.append(spot)
            rows.append({"state": m["state"], "label": m["label"], "unit": u["unit"],
                         "rect": u["rect"] and r4(u["rect"]), "in_frame": u["in_frame"],
                         "els": u["els"], "kinds": u["kinds"], "near": near, "captures": caps})
    texts = []
    for spec in a.text:
        cap, want = spec.split(":", 1)
        image, real, fin = prepared(cap)
        tb = next(t for t in real if t["text"].strip() == want)
        row = {"capture": cap, "text": want, "box": r4(tb["xyxy"])}
        for conf in CONFS:
            row["conf %g" % conf] = trace_text(*staged(cap, conf, image, real), tb, fin)
        texts.append(row)

    os.makedirs(a.out, exist_ok=True)
    diag = {"dir": os.path.relpath(a.dir, ROOT).replace("\\", "/"),
            "semantic": os.path.relpath(a.semantic, ROOT).replace("\\", "/"),
            "settings": dict(D.CFG, pass_iou=D.PASS_IOU, overlap_iou=D.OVERLAP_IOU,
                             max_area=MAX_AREA, confs=list(CONFS), device=device),
            "slots": total, "missed": len(miss), "rows": rows, "texts": texts}
    for r in rows:
        print(r["state"], r["label"], r["els"], r["kinds"])
        for c in r["captures"]:
            for conf in CONFS:
                t = c["conf %g" % conf]
                print("   ", c["capture"], conf, {k: (t[k]["n"], t[k]["best"]) for k in STAGES},
                      "final", t["final"], "lost", {k: v[:2] for k, v in t["lost"].items()})
    for r in texts:
        print(r["capture"], r["text"], {c: {k: r[c][k]["n"] for k in STAGES} for c in r if c.startswith("conf")})
    print("slots", total, "missed", len(miss))

    if a.virtual is not None:
        names = a.virtual or list(VIRTUAL)
        for n in names:
            virtual(n, a.out, a)
            print("virtual", n, flush=True)
        diag["virtual"] = {}
        for n in VIRTUAL:
            d = os.path.join(a.out, n)
            if os.path.isfile(os.path.join(d, "compare.json")):
                row = json.load(io.open(os.path.join(d, "compare.json"), encoding="utf-8"))["row"]
                diag["virtual"][n] = {"row": row, "revived": revived(diag, d)}
        base = json.load(io.open(os.path.join(a.dir, "compare.json"), encoding="utf-8"))["row"]
        diag["virtual"]["final"] = {"row": base, "revived": revived(diag, a.dir)}
    with io.open(os.path.join(a.out, "diag.json"), "w", encoding="utf-8") as f:
        json.dump(diag, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
