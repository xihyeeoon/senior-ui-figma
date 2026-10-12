r"""캡처 PNG 에서 UI 요소를 검출한다 - 요소 층 (스크린샷 입력 시험 D1).

검출은 OmniParser v2 의 icon_detect_v3 (YOLOv9-E TorchScript, MIT), 글 없는 박스의 설명은
icon_caption (Florence-2, MIT), 글은 PaddleOCR (PP-OCRv5 검출 + korean_PP-OCRv5_mobile_rec).
검출기 코드 · 가중치 · 파이썬 환경은 레포 밖에 있다 (README.md).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/detect.py
        [--captures inputs/captures/transfer] [--out results/detect/20261012] [이름 …]

PNG 마다 <out>/<이름>.json 과 확인 그림 <out>/overlay/<이름>.png 를 쓴다. 요소 하나는

    {id, kind: "box" | "text", box: [x, y, w, h] (원본 PNG 픽셀), text, caption, score}

이고, box 에는 그 안에 든 OCR 글의 id 목록 text_in 이 더 붙는다 (text 는 그 글을 이은 것).
돌린 장치 · 판 · 한 장당 시간은 <out>/_run.json 에 남긴다.

paddle 과 torch 는 한 프로세스에 함께 올리지 못한다 - 둘이 가져오는 cuDNN DLL 이 서로
다르다 (paddle 을 먼저 올리면 torch 가, torch 를 먼저 올리면 paddle 이 WinError 127). 그래서
OCR 은 torch 를 막은 자식 프로세스(--stage ocr)에서 돌리고, 검출 · 설명은 이 프로세스에서
torch 로 돌린다. 판정이나 정답과의 비교는 하지 않는다 (compare.py).
"""
import argparse
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

TOOLS = r"C:\Users\xihye\tools"
OMNIPARSER = os.path.join(TOOLS, "OmniParser")
WEIGHTS = os.path.join(TOOLS, "OmniParser-v2.0-weights")
DETECT_WEIGHTS = os.path.join(WEIGHTS, "icon_detect_v3", "model.pt")
CAPTION_WEIGHTS = os.path.join(WEIGHTS, "icon_caption")
# Florence-2 의 처리기(토크나이저 · 이미지 전처리)와 모델 코드는 이 저장소에서 온다 -
# OmniParser 의 get_caption_model_processor 와 같다. 판을 박아 둔다.
FLORENCE_REPO = "microsoft/Florence-2-base"
FLORENCE_REV = "5ca5edf5bd017b9919c05d08aebef5e4c7ac3bac"
os.environ.setdefault("HF_HOME", os.path.join(TOOLS, "hf"))
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", os.path.join(TOOLS, "paddlex"))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

# OmniParser 의 기본값 (gradio_demo · omniparser.py): 박스 점수 0.05, 검출 NMS IoU 0.1,
# 겹친 박스 정리 0.7 (작은 것을 남긴다), 검출 입력 640, 설명은 64x64 로 줄인 조각에 <CAPTION>.
BOX_THRESHOLD = 0.05
NMS_IOU = 0.1
OVERLAP_IOU = 0.7
IMGSZ = 640
CAPTION_PROMPT = "<CAPTION>"
# OCR 글은 이 점수 아래면 버린다 - 아이콘을 글로 읽은 것("Q'", "ㅁ")이 대개 여기 걸린다.
TEXT_THRESHOLD = 0.5
OCR_DET = "PP-OCRv5_server_det"
OCR_REC = "korean_PP-OCRv5_mobile_rec"
# 박스 안에 들었다고 보는 겹침 - 글 박스 넓이의 80% 가 검출 박스 안 (OmniParser 의 is_inside)
INSIDE = 0.8

FONT = r"C:\Windows\Fonts\malgun.ttf"


# --------------------------------------------------------------------------- #
# OCR - 자식 프로세스 (torch 없이)
# --------------------------------------------------------------------------- #
def run_ocr(paths, out_json):
    sys.modules["torch"] = None          # paddlex → modelscope 가 torch 를 부르지 못하게
    import paddle
    import paddleocr
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(text_detection_model_name=OCR_DET, text_recognition_model_name=OCR_REC,
                    use_doc_orientation_classify=False, use_doc_unwarping=False,
                    use_textline_orientation=False)
    ocr.predict(paths[0])                # 첫 장은 데우기 - 시간에 넣지 않는다
    out = {"device": paddle.device.get_device(),
           "versions": {"paddlepaddle": paddle.__version__, "paddleocr": paddleocr.__version__},
           "models": [OCR_DET, OCR_REC], "images": {}}
    for p in paths:
        t = time.time()
        res = ocr.predict(p)[0]
        sec = time.time() - t
        items = [{"text": txt, "score": float(sc), "xyxy": [int(v) for v in box]}
                 for txt, sc, box in zip(res["rec_texts"], res["rec_scores"], res["rec_boxes"])]
        out["images"][os.path.basename(p)] = {"seconds": sec, "items": items}
    with io.open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)


def cpu_name():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
    except OSError:
        return platform.processor()


def omniparser_commit():
    try:
        return subprocess.run(["git", "-C", OMNIPARSER, "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def ocr_in_child(paths):
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="screen_detect_ocr_")
    os.close(fd)
    try:
        subprocess.run([sys.executable, os.path.abspath(__file__), "--stage", "ocr",
                        "--ocr-out", tmp] + paths, check=True)
        with io.open(tmp, encoding="utf-8") as f:
            return json.load(f)
    finally:
        os.remove(tmp)


# --------------------------------------------------------------------------- #
# 검출 · 설명 - 이 프로세스 (torch)
# --------------------------------------------------------------------------- #
def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def inter(a, b):
    return area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])


def overlap(a, b):
    """OmniParser remove_overlap_new 의 IoU - IoU 와 두 쪽의 덮인 비율 가운데 가장 큰 것."""
    i = inter(a, b)
    if not area(a) or not area(b):
        return 0
    return max(i / (area(a) + area(b) - i + 1e-6), i / area(a), i / area(b))


def inside(a, b):
    """a 의 넓이 INSIDE 이상이 b 안에 있다."""
    return area(a) > 0 and inter(a, b) / area(a) > INSIDE


def merge(det, texts):
    """검출 박스와 OCR 글을 합친다 - OmniParser remove_overlap_new 와 같은 규칙.

    - 크게 겹친 박스 둘 중 큰 것을 버린다 (OVERLAP_IOU)
    - 박스가 OCR 글 박스 안에 들면 그 박스는 글 자체이므로 버린다
    - OCR 글이 박스 안에 들면 그 박스에 붙인다 (text_in). 둘 이상의 박스 안이면 가장 작은 것
    OCR 글은 붙었든 아니든 text 요소로 모두 남긴다 - 글 재현율은 OCR 만 본다.
    """
    keep = []
    for i, (b1, s1) in enumerate(det):
        if any(i != j and overlap(b1, b2) > OVERLAP_IOU and area(b1) > area(b2)
               for j, (b2, _) in enumerate(det)):
            continue
        if any(inside(b1, t["xyxy"]) for t in texts):
            continue
        keep.append((b1, s1))
    owner = {}
    for ti, t in enumerate(texts):
        hits = [k for k, (b, _) in enumerate(keep) if inside(t["xyxy"], b)]
        if hits:
            owner[ti] = min(hits, key=lambda k: area(keep[k][0]))
    return keep, owner


def xywh(b):
    return [int(round(b[0])), int(round(b[1])), int(round(b[2] - b[0])), int(round(b[3] - b[1]))]


class Models:
    def __init__(self, device, imgsz=IMGSZ):
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor
        sys.path.insert(0, OMNIPARSER)
        from util.yolov9 import YOLOv9Detector
        self.torch = torch
        self.device = device
        self.imgsz = imgsz
        self.det = YOLOv9Detector(model_path=DETECT_WEIGHTS, device=device)
        dtype = torch.float16 if device == "cuda" else torch.float32
        self.proc = AutoProcessor.from_pretrained(FLORENCE_REPO, revision=FLORENCE_REV,
                                                  trust_remote_code=True)
        self.cap = AutoModelForCausalLM.from_pretrained(
            CAPTION_WEIGHTS, torch_dtype=dtype, trust_remote_code=True).to(device)
        self.dtype = dtype

    def detect(self, path):
        r = self.det.predict(path, conf=BOX_THRESHOLD, iou=NMS_IOU, imgsz=self.imgsz)[0].boxes
        return [([float(v) for v in b], float(s)) for b, s in zip(r.xyxy.tolist(), r.conf.tolist())]

    def caption(self, image, boxes):
        """OmniParser get_parsed_content_icon 과 같다 - 조각을 64x64 로 줄여 <CAPTION>."""
        if not boxes:
            return []
        crops = [image.crop(tuple(int(v) for v in b)).resize((64, 64)) for b in boxes]
        with self.torch.inference_mode():
            kw = {"do_resize": False} if self.device == "cuda" else {}
            inp = self.proc(images=crops, text=[CAPTION_PROMPT] * len(crops),
                            return_tensors="pt", **kw).to(self.device)
            ids = self.cap.generate(input_ids=inp["input_ids"],
                                    pixel_values=inp["pixel_values"].to(self.dtype),
                                    max_new_tokens=20, num_beams=1, do_sample=False)
        return [t.strip() for t in self.proc.batch_decode(ids, skip_special_tokens=True)]


def elements_of(image, ocr_items, models):
    """한 장의 요소 목록과 단계별 시간."""
    texts = [t for t in ocr_items if t["score"] >= TEXT_THRESHOLD and t["text"].strip()]
    t0 = time.time()
    det = models.detect(image)
    t1 = time.time()
    keep, owner = merge(det, texts)
    plain = [k for k in range(len(keep)) if k not in owner.values()]
    caps = dict(zip(plain, models.caption(image, [keep[k][0] for k in plain])))
    t2 = time.time()
    els = []
    tid = {}
    for ti, t in enumerate(texts):
        tid[ti] = "t%d" % ti
        els.append({"id": tid[ti], "kind": "text", "box": xywh(t["xyxy"]),
                    "text": t["text"], "caption": None, "score": round(t["score"], 4),
                    "in_box": None})
    for k, (b, s) in enumerate(keep):
        mine = sorted((ti for ti, o in owner.items() if o == k),
                      key=lambda ti: (texts[ti]["xyxy"][1], texts[ti]["xyxy"][0]))
        bid = "b%d" % k
        for ti in mine:
            els[ti]["in_box"] = bid
        els.append({"id": bid, "kind": "box", "box": xywh(b),
                    "text": " ".join(texts[ti]["text"] for ti in mine) or None,
                    "caption": caps.get(k), "score": round(s, 4),
                    "text_in": [tid[ti] for ti in mine]})
    return els, {"detect": t1 - t0, "caption": t2 - t1, "raw_boxes": len(det)}


# --------------------------------------------------------------------------- #
# 확인 그림
# --------------------------------------------------------------------------- #
def overlay(image, els, path):
    """왼쪽: 캡처 위에 박스 (파랑 = 글이 든 박스, 빨강 = 글 없는 박스, 초록 = OCR 글).
    오른쪽: 같은 자리에 읽힌 것만 - 글은 검정, 글 없는 박스의 설명은 빨강 기울임 대신 [ ]."""
    from PIL import Image, ImageDraw, ImageFont
    w, h = image.size
    canvas = Image.new("RGB", (w * 2 + 8, h), "white")
    canvas.paste(image, (0, 0))
    d = ImageDraw.Draw(canvas)
    small = ImageFont.truetype(FONT, 15)
    for e in els:
        x, y, bw, bh = e["box"]
        if e["kind"] == "text":
            d.rectangle([x, y, x + bw, y + bh], outline=(0, 160, 60), width=2)
        else:
            col = (30, 90, 230) if e["text"] else (220, 30, 30)
            d.rectangle([x, y, x + bw, y + bh], outline=col, width=3)
            d.text((x + 2, y - 16 if y > 16 else y + 2), e["id"], fill=col, font=small)
    ox = w + 8
    d.rectangle([w, 0, w + 7, h], fill=(200, 200, 200))
    for e in els:
        x, y, bw, bh = e["box"]
        if e["kind"] == "box":
            col = (30, 90, 230) if e["text"] else (220, 30, 30)
            d.rectangle([ox + x, y, ox + x + bw, y + bh], outline=col, width=1)
            if not e["text"]:
                d.text((ox + x + 2, y + 2), "%s [%s]" % (e["id"], e["caption"] or ""),
                       fill=col, font=small)
    for e in els:
        if e["kind"] == "text":
            x, y, bw, bh = e["box"]
            size = max(12, min(40, int(bh * 0.8)))
            d.text((ox + x, y), e["text"], fill=(0, 0, 0), font=ImageFont.truetype(FONT, size))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    canvas.save(path)


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="캡처 이름 (01a …). 없으면 폴더의 PNG 전부")
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "detect", "20261012"))
    ap.add_argument("--imgsz", type=int, default=IMGSZ, help="검출 입력 크기 (기본 640)")
    ap.add_argument("--stage", choices=["all", "ocr"], default="all")
    ap.add_argument("--ocr-out")
    a = ap.parse_args(argv)
    if a.stage == "ocr":
        run_ocr(a.names, a.ocr_out)
        return
    names = a.names or sorted(f[:-4] for f in os.listdir(a.captures) if f.endswith(".png"))
    paths = [os.path.join(a.captures, n + ".png") for n in names]

    ocr = ocr_in_child(paths)
    import torch
    from PIL import Image
    device = "cuda" if torch.cuda.is_available() else "cpu"
    t = time.time()
    models = Models(device, a.imgsz)
    load_sec = time.time() - t
    models.detect(paths[0]); models.caption(Image.open(paths[0]).convert("RGB"), [[0, 0, 64, 64]])

    os.makedirs(a.out, exist_ok=True)
    per = {}
    for n, p in zip(names, paths):
        image = Image.open(p).convert("RGB")
        o = ocr["images"][os.path.basename(p)]
        els, times = elements_of(image, o["items"], models)
        times["ocr"] = o["seconds"]
        per[n] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in times.items()}
        per[n].update(boxes=sum(e["kind"] == "box" for e in els),
                      texts=sum(e["kind"] == "text" for e in els),
                      no_text_boxes=sum(e["kind"] == "box" and not e["text"] for e in els))
        with io.open(os.path.join(a.out, n + ".json"), "w", encoding="utf-8") as f:
            json.dump({"capture": os.path.relpath(p, ROOT).replace("\\", "/"),
                       "size": list(image.size), "elements": els},
                      f, ensure_ascii=False, indent=1)
        overlay(image, els, os.path.join(a.out, "overlay", n + ".png"))
        print(n, per[n], flush=True)

    import transformers
    tot = lambda k: sum(v[k] for v in per.values())
    run = {"captures": os.path.relpath(a.captures, ROOT).replace("\\", "/"),
           "settings": {"box_threshold": BOX_THRESHOLD, "nms_iou": NMS_IOU,
                        "overlap_iou": OVERLAP_IOU, "imgsz": a.imgsz,
                        "caption_prompt": CAPTION_PROMPT, "text_threshold": TEXT_THRESHOLD,
                        "inside": INSIDE},
           "detector": {"weights": "microsoft/OmniParser-v2.0 icon_detect_v3/model.pt",
                        "code": "microsoft/OmniParser util/yolov9.py @ %s" % omniparser_commit()},
           "caption": {"weights": "microsoft/OmniParser-v2.0 icon_caption",
                       "processor": "%s@%s" % (FLORENCE_REPO, FLORENCE_REV)},
           "ocr": {"models": ocr["models"], "device": ocr["device"], "versions": ocr["versions"]},
           "torch": {"version": torch.__version__, "device": device,
                     "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
                     "transformers": transformers.__version__},
           "cpu": cpu_name(), "model_load_seconds": round(load_sec, 1),
           "per_image_seconds_mean": dict(
               {k: round(tot(k) / len(per), 3) for k in ("ocr", "detect", "caption")},
               total=round(sum(tot(k) for k in ("ocr", "detect", "caption")) / len(per), 3)),
           "images": per}
    with io.open(os.path.join(a.out, "_run.json"), "w", encoding="utf-8") as f:
        json.dump(run, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
