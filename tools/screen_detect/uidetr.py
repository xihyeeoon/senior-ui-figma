r"""UI-DETR-1 단독 비교 (2026-10-19) - 검출 단계만 OmniParser 대신 UI-DETR-1 상자로.

    $env:NO_ALBUMENTATIONS_UPDATE = "1"
    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/uidetr.py --inputs strict
        [--out results/detect/20261019-uidetr/detect]

UI-DETR-1 = racineai/UI-DETR-1 (Hugging Face, sha 0f0dda5, MIT) - RF-DETR-M 를 UI 요소로 미세조정한 종류 구분 없는
검출기. 가중치 model.pth 는 레포 밖 C:\Users\xihye\tools\UI-DETR-1\ (OmniParser 가중치와 같은 방식). 모델 코드는
rfdetr 1.5.0 (Roboflow, Apache-2.0 - transformers 4.45.2 와 같이 설 수 있는 마지막 판, venvs\detect 에 설치).

설정은 고르지 않는다 - 모델 카드의 Quick Start 그대로: RFDETRMedium(resolution=1600), predict(threshold=0.3). (모델
카드의 벤치마크는 0.35, rfdetr 라이브러리 기본값은 0.5 - 쓰지 않았다.) DETR 이라 NMS 가 없다.

검출 상자만 바꾸고 나머지는 strict2 와 같다: OCR (같은 캐시 results/detect/20261013-d25/_ocr.json), 아이콘 글 규칙,
겹친 박스 정리 (IoU 0.7) · 글 안 박스 버림, Florence 설명, 칸 안 그림 후보 규칙 (strict - 로고 규칙 꺼짐). 우리 쪽 덧붙임인
대비 사본 (CLAHE) 한 번 더 검출은 하지 않는다 - UI-DETR-1 을 기본 설정으로 한 번만. detect.elements_of 를 그대로 부르고
검출 함수만 바꿔 끼운다. 뒤의 flags · stitch · compare 는 같은 명령으로 (README).
"""
import argparse
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import detect as D  # noqa: E402
import strict as ST  # noqa: E402

WEIGHTS = os.path.join(D.TOOLS, "UI-DETR-1", "model.pth")
REPO = "racineai/UI-DETR-1@0f0dda5ec55a9a873f2937dd755863df6218ef80"
RESOLUTION = 1600     # 모델 카드 Quick Start
THRESHOLD = 0.3       # 모델 카드 Quick Start


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "detect", "20261019-uidetr", "detect"))
    ap.add_argument("--ocr-cache", default=os.path.join(ROOT, "results", "detect", "20261013-d25", "_ocr.json"))
    ST.add_arg(ap)
    a = ap.parse_args(argv)
    ST.from_args(a)
    os.environ.setdefault("NO_ALBUMENTATIONS_UPDATE", "1")
    import torch
    from PIL import Image
    from rfdetr.detr import RFDETRMedium
    import rfdetr
    # 검출만 바꾼다 - 대비 사본 · 조각 · 고전 검출은 끈다 (UI-DETR-1 한 번)
    D.CFG.update(clahe=False, tiles=0, classic=False)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    t = time.time()
    model = RFDETRMedium(pretrain_weights=WEIGHTS, resolution=RESOLUTION)
    models = D.Models(device)          # Florence 설명은 strict2 와 같은 것을 쓴다 (YOLO 는 부르지 않는다)
    load_sec = time.time() - t
    seconds = {}

    def detect(image):
        t0 = time.time()
        det = model.predict(image, threshold=THRESHOLD)
        seconds["last"] = time.time() - t0
        return [([float(v) for v in b], float(s)) for b, s in zip(det.xyxy.tolist(), det.confidence.tolist())]
    models.detect = detect
    ocr = json.load(io.open(a.ocr_cache, encoding="utf-8"))
    names = a.names or sorted(f[:-4] for f in os.listdir(a.captures) if f.endswith(".png"))
    first = Image.open(os.path.join(a.captures, names[0] + ".png")).convert("RGB")
    detect(first)                      # 첫 호출 데우기 (시간에 넣지 않는다)
    os.makedirs(a.out, exist_ok=True)
    per = {}
    for n in names:
        p = os.path.join(a.captures, n + ".png")
        image = Image.open(p).convert("RGB")
        els, moved, times = D.elements_of(image, ocr["images"][n + ".png"]["items"], models)
        per[n] = {"uidetr_seconds": round(seconds["last"], 3), "raw_boxes": times["raw_boxes"],
                  "boxes": sum(e["kind"] == "box" for e in els), "img_candidates": sum(e["kind"] == "img_candidate" for e in els),
                  "caption_seconds": round(times["caption"], 3)}
        with io.open(os.path.join(a.out, n + ".json"), "w", encoding="utf-8") as f:
            json.dump({"capture": os.path.relpath(p, ROOT).replace("\\", "/"), "size": list(image.size),
                       "elements": els, "icon_from_ocr": moved}, f, ensure_ascii=False, indent=1)
        D.overlay(image, els, os.path.join(a.out, "overlay", n + ".png"))
        print(n, per[n], flush=True)
    run = {"captures": os.path.relpath(a.captures, ROOT).replace("\\", "/"),
           "detector": {"model": REPO, "code": "rfdetr %s RFDETRMedium" % getattr(rfdetr, "__version__", "1.5.0"),
                        "weights": WEIGHTS, "resolution": RESOLUTION, "threshold": THRESHOLD,
                        "license": "MIT (가중치) · Apache-2.0 (rfdetr)"},
           "settings": {"box_threshold": THRESHOLD, "nms_iou": 0, "nms": "없음 (DETR)", "overlap_iou": D.OVERLAP_IOU, "imgsz": RESOLUTION,
                        "tiles": 0, "clahe": False, "classic": False, "overlap_rule": D.CFG["overlap"],
                        "ocr_from_cache": True, "text_threshold": D.TEXT_THRESHOLD, "inside": D.INSIDE,
                        "icon_rule": {"side": D.ICON_SIDE, "aspect": D.ICON_ASPECT, "gap": D.ICON_GAP,
                                      "peer_height": D.ICON_PEER_H, "pad": D.ICON_PAD},
                        "logo_rule": "off (strict)" if ST.STRICT else D.LOGO_HEAD.pattern},
           "torch": {"version": torch.__version__, "device": device,
                     "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None},
           # OCR 은 strict2 와 같은 캐시 - 그 기록을 옮겨 둔다 (compare.py 가 읽는다)
           "ocr": {k: ocr[k] for k in ("models", "device", "versions")},
           "cpu": D.cpu_name(), "model_load_seconds": round(load_sec, 1),
           "per_image_seconds_mean": {"detect": round(sum(v["uidetr_seconds"] for v in per.values()) / len(per), 3),
                                      "caption": round(sum(v["caption_seconds"] for v in per.values()) / len(per), 3),
                                      "ocr": 0.0,
                                      "total": round(sum(v["uidetr_seconds"] + v["caption_seconds"]
                                                         for v in per.values()) / len(per), 3)},
           "images": per}
    with io.open(os.path.join(a.out, "_run.json"), "w", encoding="utf-8") as f:
        json.dump(run, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
