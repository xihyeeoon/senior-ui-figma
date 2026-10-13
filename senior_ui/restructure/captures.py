r"""캡처 입력 (--captures, 2026-10-12) - 진단·계획에 보여 줄 원본 그림을 연구자의 캡처로.

--see (기본 켬)는 원본 HTML 을 흐름대로 걸으며 찍은 그림을 진단·계획 프롬프트에 넣는다. 그
그림은 사람이 만든 재현본이라 아이콘이 회색 네모다 - 실행 20261008-131136 의 진단 D2 ("이름
오른쪽에 같은 모양의 네모 그림 네 개, 기능명이 없다") · D4 가 그 탓으로 보인다. 연구자 결정
(2026-10-12): 그림은 더미앱 A1 캡처를 쓴다. 원본 HTML 은 그대로 동작 코드 · 선택지 데이터 ·
검사 기준이다 - 원본 걷기와 렌더 그림 저장은 전과 같고, 모델에게 보내는 그림만 바뀐다.

대응표는 연구자가 쓴다 (docs/input-contract.md "캡처 입력"). 캡처가 어느 화면 · 상태인지 도구는
그림에서 짐작하지 않는다 - label 을 그대로 이름표로 쓴다.

    inputs/captures/<과제>/captures.json
    {"task": "transfer", "source": "<자유 글>",
     "images": [{"file": "01a.png", "label": "원본 화면 home — 스크롤 1/3 (맨 위)",
                 "taps": [{"text": "<누른 요소의 글>", "to": "<다음 캡처 file>"}]}, …]}

taps 는 스크린샷 입력 시험(feat/screen-detect)이 쓰는 칸이다. 여기서는 모양만 보고 읽지 않는다.

그림 크기: 렌더 그림(폭 390 · 창 높이 844)과 조건을 맞춘다. 가로 WIDTH 로 줄이고(비율 유지,
Pillow 의 LANCZOS - RESAMPLE). 줄인 높이가 HEIGHT 를 5% 이내(ONE_PIECE_MAX = 886 이하)로
넘으면 자르지 않고 한 장으로 보낸다 - 더미앱 캡처 824×1830 은 390×866 한 장이다 (연구자 결정
2026-10-13: 자르면 22px 만 다른 조각이 하나 더 생겨 그림이 두 배가 된다). 그보다 길면 렌더
그림과 같은 규칙(drive.see_parts - 창 높이씩, 장끼리 100px 겹치게, 마지막 장은 맨 아래에 맞춰,
최대 4장)으로 잘라 이름표 끝에 " · 조각 {i}/{n}" 을 붙인다. 렌더 그림 쪽 규칙은 그대로다. 줄인 그림은 실행 폴더가 아니라 산출물 폴더
(outputs/ 등 - git 이 무시한다)에 둔다. 실행 폴더에는 파일 이름 · sha256 · 크기만 남는다.
"""
import hashlib
import io
import json
import os

from senior_ui.audit.drive import see_parts
from senior_ui.config import ROOT

WIDTH = 390
HEIGHT = 844
# 이 높이까지는 자르지 않고 한 장으로 (HEIGHT 의 5% 이내 - 캡처 쪽에서만)
ONE_PIECE_MAX = int(HEIGHT * 1.05)
# 줄이는 필터 - 고정한다 (같은 캡처는 늘 같은 그림이 된다)
RESAMPLE = "LANCZOS"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
NAME = "captures.json"
PART_SUFFIX = " · 조각 %d/%d"


class CapturesError(ValueError):
    """대응표를 쓸 수 없다 - 실행은 시작하지 못한다 (cannot_start)."""


def sha256_of(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def rel(path):
    """저장소 안이면 저장소 기준 경로 (/), 밖이면 절대 경로."""
    p = os.path.abspath(path)
    try:
        r = os.path.relpath(p, ROOT)
    except ValueError:
        return p.replace(os.sep, "/")
    return p.replace(os.sep, "/") if r.startswith("..") else r.replace(os.sep, "/")


def _text(v):
    return isinstance(v, str) and v.strip() != ""


def problems(data, folder, task_id):
    """대응표의 문제들 - 비면 쓸 수 있다. task · 파일 · PNG · label · taps 의 모양."""
    out = []
    if not isinstance(data, dict):
        return ["대응표가 JSON 객체가 아니다"]
    if data.get("task") != task_id:
        out.append("task 가 %r 인데 이번 과제는 %r 이다" % (data.get("task"), task_id))
    images = data.get("images")
    if not isinstance(images, list) or not images:
        return out + ["images 가 비었거나 목록이 아니다"]
    files = [im.get("file") for im in images if isinstance(im, dict)]
    for i, im in enumerate(images, 1):
        where = "images[%d]" % i
        if not isinstance(im, dict):
            out.append("%s 가 객체가 아니다" % where)
            continue
        f = im.get("file")
        if not _text(f):
            out.append("%s 의 file 이 비었다" % where)
        else:
            where = "%s (%s)" % (where, f)
            path = os.path.join(folder, f)
            if not os.path.isfile(path):
                out.append("%s 파일이 없다: %s" % (where, rel(path)))
            else:
                with open(path, "rb") as fh:
                    if fh.read(8) != PNG_MAGIC:
                        out.append("%s 가 PNG 가 아니다" % where)
        if not _text(im.get("label")):
            out.append("%s 의 label 이 비었다" % where)
        taps = im.get("taps")
        if taps is None:
            continue
        if not isinstance(taps, list):
            out.append("%s 의 taps 가 목록이 아니다" % where)
            continue
        for j, t in enumerate(taps, 1):
            if not isinstance(t, dict) or not _text(t.get("text")) or not _text(t.get("to")):
                out.append("%s 의 taps[%d] 는 text · to 가 비지 않은 글이어야 한다" % (where, j))
            elif t["to"] not in files:
                out.append("%s 의 taps[%d].to %r 는 images 의 file 이 아니다" % (where, j, t["to"]))
    return out


def load(path, task_id):
    """대응표를 읽고 확인한다. 문제가 있으면 CapturesError (모두 적는다)."""
    if not os.path.isfile(path):
        raise CapturesError("캡처 대응표가 없다: %s" % rel(path))
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except ValueError as e:
        raise CapturesError("캡처 대응표를 읽지 못했다 (%s): %s" % (rel(path), e))
    folder = os.path.dirname(os.path.abspath(path))
    bad = problems(data, folder, task_id)
    if bad:
        raise CapturesError("캡처 대응표 %s 를 쓸 수 없다 - %s" % (rel(path), " · ".join(bad)))
    return {"path": os.path.abspath(path), "rel": rel(path), "sha256": sha256_of(path),
            "folder": folder, "source": data.get("source"),
            "images": [{"file": im["file"], "label": im["label"].strip(),
                        "path": os.path.join(folder, im["file"])} for im in data["images"]]}


def prepare(cap, out_dir):
    """캡처마다 가로 WIDTH 로 줄이고 필요하면 조각낸 그림을 out_dir 에 쓴다.

    돌려주는 것: `(images, records)` - images 는 모델에게 보내는 `[{"label", "path",
    "source"}]` (source = 캡처 파일, 기록 줄에 남는다), records 는 summary 의 see.images."""
    from PIL import Image
    resample = getattr(Image.Resampling, RESAMPLE)
    os.makedirs(out_dir, exist_ok=True)
    images, records = [], []
    for k, im in enumerate(cap["images"], 1):
        with Image.open(im["path"]) as src:
            src.load()
            w, h = src.size
            pic = src.convert("RGBA" if "A" in src.getbands() else "RGB")
        nh = max(1, int(round(h * WIDTH / float(w))))
        small = pic if (w, nh) == (WIDTH, h) else pic.resize((WIDTH, nh), resample)
        one = nh <= ONE_PIECE_MAX
        parts, step, more = (1, 0, 0) if one else see_parts(nh - HEIGHT, HEIGHT)
        tall = nh if one else HEIGHT
        stem = "%02d_%s" % (k, os.path.splitext(os.path.basename(im["file"]))[0])
        for i in range(parts):
            y = min(i * step, max(0, nh - tall))
            piece = small.crop((0, y, WIDTH, min(nh, y + tall)))
            name = "%s.%d.png" % (stem, i + 1)
            piece.save(os.path.join(out_dir, name), format="PNG")
            label = im["label"] + (PART_SUFFIX % (i + 1, parts) if parts > 1 else "")
            images.append({"label": label, "path": os.path.join(out_dir, name),
                           "source": rel(im["path"])})
        records.append({"file": im["file"], "sha256": sha256_of(im["path"]),
                        "size": [w, h], "sent": [WIDTH, min(nh, tall)], "scaled": [WIDTH, nh],
                        "parts": parts, "more_px": more, "label": im["label"]})
    return images, records
