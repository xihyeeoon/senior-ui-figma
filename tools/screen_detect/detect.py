r"""캡처 PNG 에서 UI 요소를 검출한다 - 요소 층 (스크린샷 입력 시험 D1).

검출은 OmniParser v2 의 icon_detect_v3 (YOLOv9-E TorchScript, MIT), 글 없는 박스의 설명은
icon_caption (Florence-2, MIT), 글은 PaddleOCR (PP-OCRv5 검출 + korean_PP-OCRv5_mobile_rec).
검출기 코드 · 가중치 · 파이썬 환경은 레포 밖에 있다 (README.md).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/detect.py
        [--captures inputs/captures/transfer] [--out results/detect/20261012] [이름 …]

PNG 마다 <out>/<이름>.json 과 확인 그림 <out>/overlay/<이름>.png 를 쓴다. 요소 하나는

    {id, kind: "box" | "text", box: [x, y, w, h] (원본 PNG 픽셀), text, caption, score}

이고, box 에는 그 안에 든 OCR 글의 id 목록 text_in 이 더 붙는다 (text 는 그 글을 이은 것).
D2: 아이콘을 OCR 이 글자로 읽은 것(icon_texts)은 글 요소에서 빼서 box 의 ocr_guess 로 옮기고
그 box 는 글 없는 아이콘으로 설명을 붙인다. box 의 source 는 "detector" 또는 그 글 자리로 새로
만든 "ocr_icon". 바꾼 목록은 JSON 의 icon_from_ocr 에 남는다.
D2: 글이 든 박스 안에서 글이 덮지 않은 그림 덩어리를 kind "img_candidate" 로 낸다 (in_box =
그 박스, name = 은행 · 증권사 칸이면 "<칸 글> 로고", 아니면 null). 그 칸의 로고가 이미 글 없는
박스로 잡혔으면 그 박스에 name 을 붙인다. img_candidates() 참고.
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
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import strict as ST  # noqa: E402

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
# D2.5 검출 설정 - 한 번에 하나씩 바꿔 견준다 (README "D2.5"). main() 이 인자로 고친다.
#   tiles    캡처를 위아래 조각(TILE_OVERLAP 만큼 겹치게)으로 나눠 한 번 더 검출해 합친다 (0 = 안 함)
#   clahe    대비를 올린 사본(CLAHE)으로 한 번 더 검출해 합친다
#   classic  고전 영상 처리(UIED 의 요소 검출)로 찾은 박스를 합친다
#   overlap  겹친 박스 정리 규칙 - "omniparser" 는 한 박스가 다른 박스를 70% 넘게 덮어도(포함도)
#            큰 것을 버린다 (OmniParser 그대로). "iou" 는 IoU 가 0.7 을 넘을 때만 - 칸 안에 아이콘
#            박스가 있어도 칸을 남긴다
# 기본값은 D2.5 시험(results/detect/20261013-d25/summary.md)에서 고른 묶음이다 - **이 앱 캡처로 고른
# 설정**: 박스 점수 0.1 · NMS 0.3 · 대비 사본 · IoU 겹침 규칙. 박스 재현율(버튼 · 입구 · 선택지 ·
# 입력칸)이 4/7 · 9/24 · 73/102 · 0/3 → 5/7 · 17/24 · 102/102 · 2/3 이고 지키는 선(글 · 로고 · 선택지)은
# 그대로다. OmniParser 기본값(D1 · D2)으로 돌리려면 --conf 0.05 --nms 0.1 --no-clahe --overlap omniparser.
CFG = {"conf": 0.1, "nms": 0.3, "tiles": 0, "clahe": True, "classic": False, "overlap": "iou"}
TILE_OVERLAP = 0.2
PASS_IOU = 0.5       # 여러 번 찾은 박스끼리 IoU 가 이 이상이면 같은 것 (원본 · 전체 검출 쪽을 남긴다)
CLAHE_CLIP, CLAHE_GRID = 2.0, 8
UIED = os.path.join(TOOLS, "UIED")
UIED_PARAMS = {"min-grad": 4, "min-ele-area": 50, "resize": 800}   # UIED run_single.py 의 mobile 권장 값
CLASSIC_SCORE = 0.04  # 고전 박스의 점수 - 검출기 박스(0.05 이상)보다 뒤에 둔다
CLASSIC_MIN = 16      # 고전 박스의 가로 · 세로 최소 (캡처 픽셀)

# OCR 글은 이 점수 아래면 버린다 - 아이콘을 글로 읽은 것("Q'", "ㅁ")이 대개 여기 걸린다.
TEXT_THRESHOLD = 0.5
OCR_DET = "PP-OCRv5_server_det"
OCR_REC = "korean_PP-OCRv5_mobile_rec"
# 박스 안에 들었다고 보는 겹침 - 글 박스 넓이의 80% 가 검출 박스 안 (OmniParser 의 is_inside)
INSIDE = 0.8

# D2 아이콘 규칙 - 아이콘을 OCR 이 글자로 읽은 것 ("Q", "요", "×", ">" 를 "7" 로). 문턱값은
# D1 정답지로 맞췄다 (README "D2"). 짧은 글(두 글자 이하, 한글이면 한 글자)이 작은 정사각
# 자리에 혼자 있으면 아이콘 후보다.
ICON_SIDE = 64              # OCR 글 박스의 긴 변 (캡처 픽셀)
ICON_ASPECT = (0.85, 1.18)  # 가로 / 세로. 숫자판 숫자는 0.69~0.84 로 세로가 길어 걸리지 않는다
ICON_GAP = 1.0              # 같은 줄에서 글 높이의 이만큼 안에 다른 글이 붙어 있으면 낱말의 일부
ICON_PEER_H = (0.8, 1.25)   # 한 글자 한글은 같은 줄에 이 높이 비의 한글이 있으면 글 (탭 이름 줄)
ICON_PAD = 0.3              # 새 아이콘 박스는 OCR 글 박스를 변마다 이만큼 넓힌다
HANGUL = re.compile("[가-힣ㄱ-ㆎ]")

# D2 칸 안의 그림 자리 (규칙 2). 글이 든 검출 박스에서 글이 덮지 않은 곳의 덩어리를 그림 자리
# 후보(img_candidate)로 낸다. 정해진 규칙이다 - LLM 을 쓰지 않는다.
BLOB_MIN = 16        # 덩어리의 가로 · 세로가 모두 이 이상 (캡처 픽셀)
BLOB_INSET = 0.06    # 칸 가장자리(둥근 모서리 · 테두리)는 짧은 변의 이만큼 안쪽부터 본다
BLOB_DIFF = 40       # 칸 바탕색(가장자리 화소의 중앙값)과 채널 차가 이 이상이면 그림 화소
BLOB_JOIN = 7        # 이만큼 떨어진 조각까지 한 덩어리로 (팽창 커널, 픽셀)
TEXT_PAD = 4         # 글 박스를 이만큼 넓혀 지운다
# 이름 - 같은 크기(±GRID_TOL)의 글 든 칸이 GRID_MIN 개 이상 늘어선 목록이고 캡처에 LOGO_HEAD 의
# 글(시트 제목 "은행 또는 증권사 선택" · 탭 "은행" "증권사")이 있으면 그 칸 글은 은행 · 증권사
# 이름이다. 칸 아래쪽(LABEL_LOW 아래)의 맨 아래 글이 칸 글이고, 가장 큰 덩어리가 "<칸 글> 로고".
# 그 칸에서는 칸 글만 지운다 - 로고 안의 글자("NH" "Kbank")는 로고의 일부다.
GRID_MIN = 6
GRID_TOL = 0.15
LOGO_HEAD = re.compile("은행|증권")
LABEL_LOW = 0.55
# 칸 글은 이름처럼 생겨야 한다 - 띄어쓰기 없는 10자 이하 (홈의 "나에게 맞는 카드 찾기" 줄 목록이 걸렸다)
NAME_LIKE = re.compile(r"^\S{1,10}$")

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


def iou(a, b):
    i = inter(a, b)
    u = area(a) + area(b) - i
    return i / u if u else 0


def inside(a, b):
    """a 의 넓이 INSIDE 이상이 b 안에 있다."""
    return area(a) > 0 and inter(a, b) / area(a) > INSIDE


def _h(t):
    return t["xyxy"][3] - t["xyxy"][1]


def same_line(t, u):
    cy = lambda v: (v["xyxy"][1] + v["xyxy"][3]) / 2
    return abs(cy(t) - cy(u)) < 0.5 * _h(t)


def gap(t, u):
    """두 글 박스 사이의 가로 틈 (겹치면 0)."""
    return max(0, max(t["xyxy"][0], u["xyxy"][0]) - min(t["xyxy"][2], u["xyxy"][2]))


def icon_texts(texts):
    """아이콘을 글자로 읽은 것으로 보이는 OCR 글의 번호 (D2 규칙 1).

    모양 - 글이 두 글자 이하다(한글이 들었으면 한 글자). 글 박스가 작고 정사각에 가깝다 (긴
    변 ICON_SIDE 이하, 가로/세로 ICON_ASPECT 안). 모양이 맞은 것 가운데
    - 같은 줄에서 모양이 맞지 않은 글(보통 글)과의 틈이 글 높이의 ICON_GAP 배 안이면 글이다
      (앞뒤에 붙은 글 - "C 홍길동님" 의 C, "7월 소비 ↻" 의 ↻ 를 읽은 C)
    - 한 글자 한글이 같은 줄에 높이가 비슷한(ICON_PEER_H) 한글을 두면 글이다 (탭 이름 "홈 금융 상품")
    - 숫자가 같은 줄에 높이가 비슷한 숫자를 두면 글이다 (숫자판 "7 8 9")
    나머지가 아이콘 후보다 ("Q" "요" "×" "←", 오른쪽 끝 ">" 를 읽은 "7")."""
    def shaped(t):
        s = t["text"].strip()
        w, h = t["xyxy"][2] - t["xyxy"][0], _h(t)
        han = HANGUL.findall(s)
        if not s or len(s) > 2 or (han and len(s) != 1) or w <= 0 or h <= 0:
            return False
        return max(w, h) <= ICON_SIDE and ICON_ASPECT[0] <= w / h <= ICON_ASPECT[1]

    def peer(t, u, kind):
        return kind(u["text"].strip()) and ICON_PEER_H[0] <= _h(u) / _h(t) <= ICON_PEER_H[1]

    shape = [shaped(t) for t in texts]
    out = set()
    for i, t in enumerate(texts):
        if not shape[i]:
            continue
        s, h = t["text"].strip(), _h(t)
        line = [(j, u) for j, u in enumerate(texts) if j != i and same_line(t, u)]
        if any(not shape[j] and gap(t, u) < ICON_GAP * h for j, u in line):
            continue
        if HANGUL.search(s) and any(peer(t, u, HANGUL.search) for _, u in line):
            continue
        if s.isdigit() and any(peer(t, u, str.isdigit) for _, u in line):
            continue
        out.add(i)
    return out


def pad(b, k, size):
    w, h = b[2] - b[0], b[3] - b[1]
    return [max(0, b[0] - k * w), max(0, b[1] - k * h),
            min(size[0], b[2] + k * w), min(size[1], b[3] + k * h)]


def merge(det, texts):
    """검출 박스와 OCR 글을 합친다 - OmniParser remove_overlap_new 와 같은 규칙.

    - 크게 겹친 박스 둘 중 큰 것을 버린다 (OVERLAP_IOU, 겹침 셈은 CFG["overlap"])
    - 박스가 OCR 글 박스 안에 들면 그 박스는 글 자체이므로 버린다
    - OCR 글이 박스 안에 들면 그 박스에 붙인다 (text_in). 둘 이상의 박스 안이면 가장 작은 것
    OCR 글은 붙었든 아니든 text 요소로 모두 남긴다 - 글 재현율은 OCR 만 본다.
    """
    keep = []
    ov = overlap if CFG["overlap"] == "omniparser" else iou
    for i, (b1, s1) in enumerate(det):
        if any(i != j and ov(b1, b2) > OVERLAP_IOU and area(b1) > area(b2)
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
        r = self.det.predict(path, conf=CFG["conf"], iou=CFG["nms"], imgsz=self.imgsz)[0].boxes
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


def clahe(image):
    """대비를 올린 사본 - LAB 의 밝기에 CLAHE."""
    import cv2
    import numpy as np
    from PIL import Image
    lab = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2LAB)
    lab[..., 0] = cv2.createCLAHE(CLAHE_CLIP, (CLAHE_GRID, CLAHE_GRID)).apply(lab[..., 0])
    return Image.fromarray(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB))


def classic_boxes(image):
    """UIED(MulongXie/UIED, Apache-2.0)의 요소 검출 - 기울기 이진화 → 선 지우기 → 연결 요소 →
    거르기 · 합치기 · 블록 알아보기 · 블록 밖 포함 요소 지우기. 레포 밖의 UIED 코드를 import 한다."""
    import cv2
    import numpy as np
    if UIED not in sys.path:
        sys.path.insert(0, UIED)
    import detect_compo.lib_ip.ip_preprocessing as pre
    import detect_compo.lib_ip.ip_detection as det
    import detect_compo.lib_ip.Component as Compo
    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    k = UIED_PARAMS["resize"] / h
    org = cv2.resize(bgr, (int(w * k), UIED_PARAMS["resize"]))
    binary = pre.binarization(org, grad_min=UIED_PARAMS["min-grad"])
    det.rm_line(binary, show=False)
    compos = det.component_detection(binary, min_obj_area=UIED_PARAMS["min-ele-area"])
    compos = det.compo_filter(compos, min_area=UIED_PARAMS["min-ele-area"], img_shape=binary.shape)
    compos = det.merge_intersected_compos(compos)
    det.compo_block_recognition(binary, compos)
    compos = det.rm_contained_compos_not_in_block(compos)
    out = []
    for c in compos:
        x0, y0, x1, y1 = (v / k for v in c.put_bbox())
        if x1 - x0 >= CLASSIC_MIN and y1 - y0 >= CLASSIC_MIN and \
                (x1 - x0) * (y1 - y0) < 0.6 * w * h:
            out.append([x0, y0, x1, y1])
    return out


def detect_all(image, models):
    """검출 박스 [(xyxy, 점수, 출처)] - 전체 검출에 CFG 의 조각 · 대비 사본 · 고전 박스를 더해 합친다.
    조각 검출은 조각을 자른 가장자리(이미지 끝이 아닌 곳)에 닿는 박스를 버린다 - 잘린 요소다.
    여러 번 찾은 같은 박스(IoU PASS_IOU 이상)는 하나만 남긴다 - 전체 · 원본 · 점수 높은 쪽."""
    w, h = image.size
    found = [(b, s, "detector") for b, s in models.detect(image)]
    if CFG["tiles"]:
        n = CFG["tiles"]
        th = h / (n - (n - 1) * TILE_OVERLAP)
        for i in range(n):
            y0 = int(round(i * th * (1 - TILE_OVERLAP)))
            y1 = min(h, int(round(y0 + th)))
            for b, s in models.detect(image.crop((0, y0, w, y1))):
                b = [b[0], b[1] + y0, b[2], b[3] + y0]
                if (y0 > 0 and b[1] <= y0 + 3) or (y1 < h and b[3] >= y1 - 3):
                    continue
                found.append((b, s, "detector:tile"))
    if CFG["clahe"]:
        found += [(b, s, "detector:clahe") for b, s in models.detect(clahe(image))]
    if CFG["classic"]:
        found += [(b, CLASSIC_SCORE, "classic") for b in classic_boxes(image)]
    if len(found) == 0:
        return []
    rank = {"detector": 3, "detector:tile": 2, "detector:clahe": 1, "classic": 0}
    keep = []
    for b, s, src in sorted(found, key=lambda f: (rank[f[2]], f[1]), reverse=True):
        if all(iou(b, k[0]) < PASS_IOU for k in keep):
            keep.append((b, s, src))
    return keep


def elements_of(image, ocr_items, models):
    """한 장의 요소 목록, 아이콘으로 바꾼 OCR 글 목록, 단계별 시간.

    아이콘으로 본 OCR 글(icon_texts)은 글 요소에서 빼고 박스의 ocr_guess 로 옮긴다. 그 글이
    든 검출 박스에 다른 글이 없으면 그 박스가, 없으면 그 글 박스를 넓힌 새 박스(source
    "ocr_icon")가 아이콘이 된다. 아이콘 박스는 글이 없으므로(text null) 설명을 붙인다."""
    texts = [t for t in ocr_items if t["score"] >= TEXT_THRESHOLD and t["text"].strip()]
    icons = icon_texts(texts)
    real = [t for i, t in enumerate(texts) if i not in icons]
    guessed = [t for i, t in enumerate(texts) if i in icons]
    t0 = time.time()
    found = detect_all(image, models)
    det = [(b, s) for b, s, _ in found]
    src = {id(b): x for b, _, x in found}
    t1 = time.time()
    keep, owner = merge(det, real)
    boxes = [{"xyxy": b, "score": s, "source": src.get(id(b), "detector"), "guess": []}
             for b, s in keep]
    owned = set(owner.values())
    moved = []
    for t in guessed:
        free = [k for k, b in enumerate(boxes) if k not in owned]
        hits = [k for k in free if inside(t["xyxy"], boxes[k]["xyxy"])]
        if not hits:
            wide = pad(t["xyxy"], ICON_PAD, image.size)
            hits = [k for k in free if overlap(wide, boxes[k]["xyxy"]) > 0.5]
        if hits:
            k = min(hits, key=lambda k: area(boxes[k]["xyxy"]))
        else:
            boxes.append({"xyxy": pad(t["xyxy"], ICON_PAD, image.size), "score": t["score"],
                          "source": "ocr_icon", "guess": []})
            k = len(boxes) - 1
        boxes[k]["guess"].append(t)
        moved.append({"text": t["text"], "score": round(t["score"], 4), "box": xywh(t["xyxy"]),
                      "into": "b%d" % k})
    plain = [k for k in range(len(boxes)) if k not in owned]
    caps = dict(zip(plain, models.caption(image, [boxes[k]["xyxy"] for k in plain])))
    t2 = time.time()
    els = []
    tid = {}
    for ti, t in enumerate(real):
        tid[ti] = "t%d" % ti
        els.append({"id": tid[ti], "kind": "text", "box": xywh(t["xyxy"]),
                    "text": t["text"], "caption": None, "score": round(t["score"], 4),
                    "in_box": None})
    for k, bx in enumerate(boxes):
        mine = sorted((ti for ti, o in owner.items() if o == k),
                      key=lambda ti: (real[ti]["xyxy"][1], real[ti]["xyxy"][0]))
        bid = "b%d" % k
        for ti in mine:
            els[ti]["in_box"] = bid
        els.append({"id": bid, "kind": "box", "box": xywh(bx["xyxy"]),
                    "text": " ".join(real[ti]["text"] for ti in mine) or None,
                    "caption": caps.get(k), "score": round(bx["score"], 4),
                    "text_in": [tid[ti] for ti in mine],
                    "ocr_guess": " ".join(g["text"] for g in bx["guess"]) or None,
                    "source": bx["source"]})
    t3 = time.time()
    cands = img_candidates(image, els)
    caps = models.caption(image, [c.pop("xyxy") for c in cands])
    for k, (c, cap) in enumerate(zip(cands, caps)):
        els.append(dict({"id": "i%d" % k, "kind": "img_candidate", "text": None, "caption": cap,
                         "score": None}, **c))
    t4 = time.time()
    return els, moved, {"detect": t1 - t0, "caption": (t2 - t1) + (t4 - t3),
                        "raw_boxes": len(det)}


def img_candidates(image, els):
    """글이 든 검출 박스 안에서 글이 덮지 않은 그림 덩어리 (D2 규칙 2). 칸 안의 글 없는 박스
    (아이콘)가 덮은 곳은 이미 요소이므로 뺀다."""
    import cv2
    import numpy as np
    arr = np.asarray(image).astype(np.int16)
    texts = {e["id"]: e for e in els if e["kind"] == "text"}
    boxes = [e for e in els if e["kind"] == "box"]
    filled = [b for b in boxes if b["text_in"]]
    # 은행 · 증권사 칸 이름 규칙 - 과제 분야 낱말(LOGO_HEAD)이다. 스크린샷만(--inputs strict)에서는 끈다
    heading = False if ST.STRICT else any(LOGO_HEAD.search(t["text"]) for t in texts.values())

    def like(a, b):
        return all(abs(a["box"][i] - b["box"][i]) <= GRID_TOL * b["box"][i] for i in (2, 3))
    grid = {b["id"] for b in filled
            if heading and sum(like(o, b) for o in filled) >= GRID_MIN}

    out = []
    for b in filled:
        x, y, w, h = b["box"]
        ins = [texts[t] for t in b["text_in"]]
        label, listed = None, b["id"] in grid
        if listed:
            low = [t for t in ins if t["box"][1] + t["box"][3] / 2 > y + LABEL_LOW * h]
            label = max(low, key=lambda t: t["box"][1]) if low else None
            if label and not NAME_LIKE.match(label["text"].strip()):
                # 이름처럼 생기지 않은 글 (띄어쓴 문장 · 긴 글) - 은행 · 증권사 칸이 아니다
                label, listed = None, False
        if listed:
            wipe = [label] if label else []
        else:
            # 박스 안의 글은 누구 것이든 지운다 - 안쪽 박스에 붙은 글도 (겹침 규칙이 "iou" 면 칸 안에
            # 칸이 남아, 바깥 칸의 text_in 에는 안쪽 칸의 글이 들지 않는다)
            wipe = [t for t in texts.values() if inside(xyxy(t["box"]), xyxy(b["box"]))]
        i = int(BLOB_INSET * min(w, h))
        x0, y0 = max(0, x + i), max(0, y + i)
        x1, y1 = min(arr.shape[1], x + w - i), min(arr.shape[0], y + h - i)
        if x1 - x0 < BLOB_MIN or y1 - y0 < BLOB_MIN:
            continue
        sub = arr[y0:y1, x0:x1]
        ring = np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]])
        fg = (np.abs(sub - np.median(ring, axis=0)).max(axis=2) >= BLOB_DIFF).astype(np.uint8)
        # 안쪽 박스는 이미 요소다 - 은행 칸에서는 글 없는 박스(아이콘)만, 그 밖의 칸에서는 모두 지운다
        icons = [o for o in boxes if o is not b and (not o["text"] or not listed)
                 and inside(xyxy(o["box"]), xyxy(b["box"]))]
        for t in wipe + icons:
            tx, ty, tw, th = t["box"]
            pad_ = TEXT_PAD if t["kind"] == "text" else 0
            fg[max(0, ty - pad_ - y0):max(0, ty + th + pad_ - y0),
               max(0, tx - pad_ - x0):max(0, tx + tw + pad_ - x0)] = 0
        fg = cv2.dilate(fg, np.ones((BLOB_JOIN, BLOB_JOIN), np.uint8))
        n, _, stats, _ = cv2.connectedComponentsWithStats(fg)
        r = BLOB_JOIN // 2
        # 살펴보는 자리의 가장자리에 닿는 덩어리는 칸의 모양(둥근 알약의 모서리 · 테두리)이다
        H, W = fg.shape
        blobs = [[int(x0 + bx + r), int(y0 + by + r), int(bw - 2 * r), int(bh - 2 * r)]
                 for bx, by, bw, bh, _ in stats[1:]
                 if bx > 0 and by > 0 and bx + bw < W and by + bh < H]
        blobs = [bl for bl in blobs if bl[2] >= BLOB_MIN and bl[3] >= BLOB_MIN]
        big = max(blobs, key=lambda bl: bl[2] * bl[3]) if blobs and label else None
        if label and not blobs and icons:
            # 로고가 이미 글 없는 박스(아이콘)로 잡혔다 - 그 박스에 이름을 붙인다
            ic = max(icons, key=lambda o: o["box"][2] * o["box"][3])
            ic.update(name="%s 로고" % label["text"].strip(), label=label["id"])
        for bl in blobs:
            out.append({"box": bl, "xyxy": xyxy(bl), "in_box": b["id"],
                        "name": "%s 로고" % label["text"].strip() if bl is big else None,
                        "label": label["id"] if bl is big else None})
    return out


def xyxy(b):
    return [b[0], b[1], b[0] + b[2], b[1] + b[3]]


# --------------------------------------------------------------------------- #
# 확인 그림
# --------------------------------------------------------------------------- #
def overlay(image, els, path):
    """왼쪽: 캡처 위에 박스 (파랑 = 글이 든 박스, 빨강 = 글 없는 박스, 초록 = OCR 글,
    주황 = 칸 안의 그림 자리 후보).
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
        elif e["kind"] == "img_candidate":
            d.rectangle([x, y, x + bw, y + bh], outline=(240, 140, 0), width=2)
        else:
            col = (30, 90, 230) if e["text"] else (220, 30, 30)
            d.rectangle([x, y, x + bw, y + bh], outline=col, width=3)
            d.text((x + 2, y - 16 if y > 16 else y + 2), e["id"], fill=col, font=small)
    ox = w + 8
    d.rectangle([w, 0, w + 7, h], fill=(200, 200, 200))
    for e in els:
        x, y, bw, bh = e["box"]
        if e["kind"] == "img_candidate":
            d.rectangle([ox + x, y, ox + x + bw, y + bh], outline=(240, 140, 0), width=2)
            d.text((ox + x + 2, y + 2), "%s %s" % (e["id"], e["name"] or "[%s]" % (e["caption"] or "")),
                   fill=(200, 100, 0), font=small)
        if e["kind"] == "box":
            col = (30, 90, 230) if e["text"] else (220, 30, 30)
            d.rectangle([ox + x, y, ox + x + bw, y + bh], outline=col, width=1)
            if not e["text"]:
                d.text((ox + x + 2, y + 2), "%s %s%s" % (
                    e["id"], e.get("name") or "[%s]" % (e["caption"] or ""),
                    " ocr:%s" % e["ocr_guess"] if e.get("ocr_guess") else ""),
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
    ap.add_argument("--conf", type=float, default=CFG["conf"], help="검출 점수 문턱")
    ap.add_argument("--nms", type=float, default=CFG["nms"], help="검출 NMS IoU")
    ap.add_argument("--tiles", type=int, default=CFG["tiles"], help="위아래 조각 수 (0 = 안 함)")
    ap.add_argument("--clahe", action=argparse.BooleanOptionalAction, default=CFG["clahe"])
    ap.add_argument("--classic", action=argparse.BooleanOptionalAction, default=CFG["classic"])
    ap.add_argument("--overlap", choices=["omniparser", "iou"], default=CFG["overlap"])
    ap.add_argument("--ocr-cache", help="OCR 결과 JSON - 있으면 읽고(OCR 을 건너뛴다), 없으면 써 둔다")
    ap.add_argument("--stage", choices=["all", "ocr"], default="all")
    ap.add_argument("--ocr-out")
    ST.add_arg(ap)
    a = ap.parse_args(argv)
    ST.from_args(a)
    if a.stage == "ocr":
        run_ocr(a.names, a.ocr_out)
        return
    names = a.names or sorted(f[:-4] for f in os.listdir(a.captures) if f.endswith(".png"))
    paths = [os.path.join(a.captures, n + ".png") for n in names]

    CFG.update(conf=a.conf, nms=a.nms, tiles=a.tiles, clahe=a.clahe, classic=a.classic,
               overlap=a.overlap)
    cached = bool(a.ocr_cache) and os.path.exists(a.ocr_cache)
    if cached:
        with io.open(a.ocr_cache, encoding="utf-8") as f:
            ocr = json.load(f)
    else:
        ocr = ocr_in_child(paths)
        if a.ocr_cache:
            with io.open(a.ocr_cache, "w", encoding="utf-8") as f:
                json.dump(ocr, f, ensure_ascii=False)
    import torch
    from PIL import Image
    device = "cuda" if torch.cuda.is_available() else "cpu"
    t = time.time()
    models = Models(device, a.imgsz)
    load_sec = time.time() - t
    models.detect(Image.open(paths[0]).convert("RGB")); models.caption(Image.open(paths[0]).convert("RGB"), [[0, 0, 64, 64]])

    os.makedirs(a.out, exist_ok=True)
    per = {}
    for n, p in zip(names, paths):
        image = Image.open(p).convert("RGB")
        o = ocr["images"][os.path.basename(p)]
        els, moved, times = elements_of(image, o["items"], models)
        times["ocr"] = o["seconds"]
        per[n] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in times.items()}
        per[n].update(boxes=sum(e["kind"] == "box" for e in els),
                      texts=sum(e["kind"] == "text" for e in els),
                      no_text_boxes=sum(e["kind"] == "box" and not e["text"] for e in els),
                      icons_from_ocr=len(moved),
                      img_candidates=sum(e["kind"] == "img_candidate" for e in els),
                      named=sum(bool(e.get("name")) for e in els))
        with io.open(os.path.join(a.out, n + ".json"), "w", encoding="utf-8") as f:
            json.dump({"capture": os.path.relpath(p, ROOT).replace("\\", "/"),
                       "size": list(image.size), "elements": els, "icon_from_ocr": moved},
                      f, ensure_ascii=False, indent=1)
        overlay(image, els, os.path.join(a.out, "overlay", n + ".png"))
        print(n, per[n], flush=True)

    import transformers
    tot = lambda k: sum(v[k] for v in per.values())
    run = {"captures": os.path.relpath(a.captures, ROOT).replace("\\", "/"),
           "settings": {"box_threshold": CFG["conf"], "nms_iou": CFG["nms"],
                        "overlap_iou": OVERLAP_IOU, "imgsz": a.imgsz,
                        "tiles": CFG["tiles"], "tile_overlap": TILE_OVERLAP, "clahe": CFG["clahe"],
                        "classic": CFG["classic"], "overlap_rule": CFG["overlap"],
                        "pass_iou": PASS_IOU, "ocr_from_cache": cached,
                        "caption_prompt": CAPTION_PROMPT, "text_threshold": TEXT_THRESHOLD,
                        "inside": INSIDE,
                        "icon_rule": {"side": ICON_SIDE, "aspect": ICON_ASPECT, "gap": ICON_GAP,
                                      "peer_height": ICON_PEER_H, "pad": ICON_PAD},
                        "img_rule": {"min": BLOB_MIN, "inset": BLOB_INSET, "diff": BLOB_DIFF,
                                     "join": BLOB_JOIN, "text_pad": TEXT_PAD,
                                     "grid_min": GRID_MIN, "grid_tol": GRID_TOL,
                                     "head": LOGO_HEAD.pattern, "label_low": LABEL_LOW}},
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
