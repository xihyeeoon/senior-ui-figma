r"""탐색용 시안 — 조립 설계 전. LLM 시안 v3 (꺾쇠 규칙 11) 이 icon 이 붙은 요소를 어떻게 그렸나 (유료 호출 없음).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/sketch/chevron_check.py
        [--html results/detect/20261019-strict3/sketch/llm.html] [--root results/detect/20261019-strict2]
        [--unit 01a+01b+01c] → <html 폴더>/chevron.md

의미 층에서 icon 이 붙었거나 text_is_icon 이거나 kind 가 image 인 요소마다, 시안에서 그 data-src 요소 안에 그림 자리
(role="img") 가 있는지, 꺾쇠 글자 (› ⌄ ⌃ 와 비슷한 > ^ 등) 로 그렸는지를 센다. icon.shape 에 "꺾쇠" 가 없는데 글자로
바뀐 것 (새로고침 · 핀 · 로고 등) 은 따로 적는다.
"""
import argparse
import io
import json
import os
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common as K  # noqa: E402

GLYPHS = set("›‹⌄⌃>^ˇ∨∧")


class Walk(HTMLParser):
    """data-src 요소마다 (그 안의 role=img 수, 그 안의 글) - 안쪽 data-src 요소의 것은 빼지 않고 함께 센다."""
    VOID = {"br", "img", "input", "meta", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.info = [], {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        src = a.get("data-src")
        if src:
            self.info.setdefault(src, {"img": 0, "text": ""})
        if a.get("role") == "img":
            # 그 요소 자신이 그림 자리인 것 (kind image) 도 센다
            for s in self.stack + [src]:
                if s:
                    self.info[s]["img"] += 1
        if tag not in self.VOID:
            self.stack.append(src)

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        for s in self.stack:
            if s:
                self.info[s]["text"] += data


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=os.path.join(K.ROOT, "results", "detect", "20261019-strict3", "sketch", "llm.html"))
    ap.add_argument("--root", default=os.path.join(K.ROOT, "results", "detect", "20261019-strict2"))
    ap.add_argument("--unit", default="01a+01b+01c")
    a = ap.parse_args(argv)
    K.set_strict_root(a.root)
    u = K.load_units(strict=True, only=[a.unit])[a.unit]
    w = Walk()
    w.feed(io.open(a.html, encoding="utf-8").read())
    rows, glyph, wrong = [], [], []
    for e in u["elements"]:
        if not (e.get("icon") or e.get("text_is_icon") or e["kind"] == "image"):
            continue
        got = w.info.get(e["id"], {"img": 0, "text": ""})
        text = "".join(got["text"].split())
        shape = (e.get("icon") or {}).get("shape") or e.get("image_shape") or ""
        as_glyph = got["img"] == 0 and bool(text) and set(text) <= GLYPHS
        rows.append([e["id"], e["kind"], (e.get("text") or "-")[:16],
                     (e.get("icon") or {}).get("name") or e.get("image_name") or "-", shape,
                     got["img"], text[:16] or "-", "글자" if as_glyph else ("그림 자리" if got["img"] else "-")])
        if as_glyph:
            glyph.append(e["id"])
            if "꺾쇠" not in shape and "화살표" not in shape:
                wrong.append(e["id"])
    md = ["# 꺾쇠 규칙 점검 - %s (%s)\n" % (os.path.relpath(a.html, K.ROOT).replace(os.sep, "/"), a.unit),
          "의미 층에서 icon 이 붙었거나 text_is_icon 이거나 kind 가 image 인 요소마다 시안에서 어떻게 그렸나.\n",
          K.C.table(["id", "kind", "OCR 글", "icon.name (image_name)", "모양", "안의 그림 자리", "안의 글", "그린 꼴"], rows),
          "\n꺾쇠로 판단해 글자로 그린 요소 (%d): %s\n" % (len(glyph), ", ".join(glyph) or "없음"),
          "모양이 꺾쇠 · 화살표가 아닌데 글자로 바뀐 것: %s\n" % (", ".join(wrong) or "없음")]
    path = os.path.join(os.path.dirname(a.html), "chevron.md")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md[2:]))


if __name__ == "__main__":
    main()
