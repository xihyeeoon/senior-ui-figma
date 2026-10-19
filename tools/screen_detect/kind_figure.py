r"""비교 그림 - 검출 결과 위에 의미 층의 kind 를 색으로 (2026-10-19, 구역 검출 시험 2-1).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/kind_figure.py
        [01a 01b 01c] [--dir results/detect/20261013-d25/final] [--semantic results/detect/20261013-d3b]
        [--out results/detect/20261019-regions/figures]

detect.overlay (D1 부터의 확인 그림) 과 같은 꼴이다 - 왼쪽은 캡처 위에 최종 요소, 오른쪽은 검출 결과만으로
다시 그린 화면. 다른 점은 박스의 색이 검출 종류(글 든 박스 · 글 없는 박스) 대신 의미 층이 붙인 kind 라는
것 하나다. 글 줄(OCR)은 왼쪽에 얇은 초록 테두리로, 오른쪽에 글자로 그린다. 의미 층의 답이 없는 요소(이은
화면에서 겹쳐 빠진 조각의 요소)는 회색 점선이다. 읽기만 한다 - 의미 층은 다시 돌리지 않는다.
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

COLORS = {"button": (30, 90, 230), "link": (0, 150, 170), "back_close": (130, 60, 200),
          "tab": (20, 40, 120), "choice": (240, 120, 0), "input": (150, 90, 40),
          "keypad_key": (110, 110, 110), "image": (220, 30, 30), "text": (0, 160, 60),
          "system": (180, 180, 180)}
NONE = (150, 150, 150)


def answers(sem_dir, dir_):
    """캡처 → {요소 id: 답}. 이은 화면의 id 는 "<캡처>:<id>" 이다."""
    sem, _ = C.load_semantic(sem_dir)
    out = {}
    for unit, d in C.load_units(dir_).items():
        caps = d.get("captures") or [unit]
        for i, g in (sem.get(unit) or {}).items():
            cap, _, eid = i.rpartition(":")
            out.setdefault(cap or caps[0], {})[eid] = g
    return out


def dashed(d, box, col, width=2, dash=8):
    x0, y0, x1, y1 = box
    for a in range(int(x0), int(x1), dash * 2):
        d.line([a, y0, min(a + dash, x1), y0], fill=col, width=width)
        d.line([a, y1, min(a + dash, x1), y1], fill=col, width=width)
    for a in range(int(y0), int(y1), dash * 2):
        d.line([x0, a, x0, min(a + dash, y1)], fill=col, width=width)
        d.line([x1, a, x1, min(a + dash, y1)], fill=col, width=width)


def draw(image, els, ans, path):
    from PIL import Image, ImageDraw, ImageFont
    w, h = image.size
    legend_h = 70
    canvas = Image.new("RGB", (w * 2 + 8, h + legend_h), "white")
    canvas.paste(image, (0, 0))
    d = ImageDraw.Draw(canvas)
    small = ImageFont.truetype(D.FONT, 15)
    ox = w + 8
    d.rectangle([w, 0, w + 7, h], fill=(200, 200, 200))
    # 큰 것부터 그려 작은 것의 이름이 위에 오게
    for e in sorted(els, key=lambda e: -e["box"][2] * e["box"][3]):
        x, y, bw, bh = e["box"]
        g = ans.get(e["id"])
        if e["kind"] == "text":
            d.rectangle([x, y, x + bw, y + bh], outline=(0, 160, 60), width=1)
            if g and g["kind"] != "text":
                # 글 줄인데 다른 kind (박스 없이 글 줄로만 있는 버튼 · 입구)
                col = COLORS.get(g["kind"], NONE)
                d.rectangle([x - 3, y - 3, x + bw + 3, y + bh + 3], outline=col, width=3)
                d.text((x + 2, y - 17 if y > 17 else y + bh + 2), "%s %s" % (e["id"], g["kind"]),
                       fill=col, font=small)
            continue
        col = COLORS.get(g["kind"], NONE) if g else NONE
        if g:
            d.rectangle([x, y, x + bw, y + bh], outline=col, width=3)
        else:
            dashed(d, [x, y, x + bw, y + bh], col)
        label = "%s %s" % (e["id"], g["kind"] if g else "-")
        d.text((x + 2, y - 16 if y > 16 else y + 2), label, fill=col, font=small)
        # 오른쪽 - 다시 그린 화면
        d.rectangle([ox + x, y, ox + x + bw, y + bh], outline=col, width=1)
        if not e.get("text"):
            name = (g or {}).get("image_name") or e.get("name") or "[%s]" % (e.get("caption") or "")
            d.text((ox + x + 2, y + 2), "%s %s" % (g["kind"] if g else "-", name), fill=col, font=small)
    for e in els:
        if e["kind"] == "text":
            x, y, bw, bh = e["box"]
            size = max(12, min(40, int(bh * 0.8)))
            d.text((ox + x, y), e["text"], fill=(0, 0, 0), font=ImageFont.truetype(D.FONT, size))
    # 범례
    lx, ly = 10, h + 10
    for k, col in list(COLORS.items()) + [("답 없음", NONE)]:
        d.rectangle([lx, ly, lx + 22, ly + 16], outline=col, width=3)
        d.text((lx + 28, ly - 2), k, fill=col, font=small)
        lx += 40 + int(d.textlength(k, font=small))
        if lx > canvas.width - 160:
            lx, ly = 10, ly + 26
    d.text((lx, ly - 2), "얇은 초록 = OCR 글 줄", fill=(0, 160, 60), font=small)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    canvas.save(path)


def main(argv=None):
    from PIL import Image
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=["01a", "01b", "01c"])
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261013-d25", "final"))
    ap.add_argument("--semantic", default=os.path.join(ROOT, "results", "detect", "20261013-d3b"))
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "detect", "20261019-regions",
                                                  "figures"))
    a = ap.parse_args(argv)
    ans = answers(a.semantic, a.dir)
    for n in a.names:
        det = json.load(io.open(os.path.join(a.dir, n + ".json"), encoding="utf-8"))
        image = Image.open(os.path.join(a.captures, n + ".png")).convert("RGB")
        path = os.path.join(a.out, "kind_%s.png" % n)
        draw(image, det["elements"], ans.get(n, {}), path)
        print(path)


if __name__ == "__main__":
    main()
