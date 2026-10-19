r"""탐색용 시안 — 조립 설계 전. 정식 조립 코드가 아니다 (연구자가 눈으로 보고 조립 방식을 고르기 위한 것).

시안 둘(rule_assemble.py · llm_assemble.py)이 같이 쓰는 입력 - 단위(이은 화면 3 + 낱장 10)마다

  그림      캡처 (이은 화면은 stitch.compose 로 이은 그림)
  요소      results/detect/20261013-d25/final 의 요소 (박스 · 글 줄 · 그림 후보) + 의미 층 답
            (results/detect/20261013-d3b/<단위>.semantic.json). 의미 층 kind 가 system (상태바 · 덮개 뒤) 인
            요소는 넣지 않는다
  구역      results/detect/20261019-robust/tree/<단위>.regions.json - 가로가 단위의 95% 이상인 구역은
            구역이 아니라 띠(band)로만 쓴다 (10/19 연구자 결정)
  흐름      results/detect/20261013-d4/flow.proposed.json 의 짝 - kind 가 tap 이고 누른 요소가 있는 것만
            (unknown · skipped · scroll · error_path 는 넘어가지 않는다)
  이름표    captures.json 의 label (origin/feat/db-principles 에서 git show 로 읽는다)

옛 원본 HTML · flows/original.json · tasks/transfer.json 은 쓰지 않는다 (견주기 페이지에서만 옛 원본을 그린다).
좌표는 CSS px (화면 가로 390) 로 바꿔 쓴다 - 캡처 가로 824 → 390.
"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(TOOLS))
sys.path.insert(0, TOOLS)

import compare as C  # noqa: E402
import truth_regions as TRG  # noqa: E402

FINAL = os.path.join(ROOT, "results", "detect", "20261013-d25", "final")
SEMANTIC = os.path.join(ROOT, "results", "detect", "20261013-d3b")
TREES = os.path.join(ROOT, "results", "detect", "20261019-robust", "tree")
FLOW = os.path.join(ROOT, "results", "detect", "20261013-d4", "flow.proposed.json")
CAPTURES = os.path.join(ROOT, "inputs", "captures", "transfer")
CAPTURES_JSON = ("origin/feat/db-principles", "inputs/captures/transfer/captures.json")
OUT = os.path.join(ROOT, "results", "detect", "20261019-sketch")
WIDTH = 390
SCALE = WIDTH / 824
WIDE = 0.95
BUTTONS = ("button", "link", "back_close", "tab", "choice", "keypad_key")


def css(v):
    return int(round(v * SCALE))


def section_id(unit):
    return "u-" + unit.split("(")[0]


def read_captures():
    ref, path = CAPTURES_JSON
    out = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (ref, path)], capture_output=True, check=True)
    return json.loads(out.stdout.decode("utf-8"))


def load_units():
    """단위 이름 → 공통 입력 dict. 단위 순서는 캡처 순서."""
    dets = C.load_units(FINAL)
    sem, _ = C.load_semantic(SEMANTIC)
    labels = {i["file"]: i["label"] for i in read_captures()["images"]}
    flow = json.load(io.open(FLOW, encoding="utf-8"))
    cap_unit = {}
    for n, d in dets.items():
        for c in d.get("captures") or [os.path.splitext(os.path.basename(d["capture"]))[0]]:
            cap_unit[c + ".png"] = n
    units = {}
    for n, d in dets.items():
        ans = sem.get(n) or {}
        caps = d.get("captures") or [os.path.splitext(os.path.basename(d["capture"]))[0]]
        tree = json.load(io.open(os.path.join(TREES, "%s.regions.json" % n), encoding="utf-8"))
        w = d["size"][0]
        regions = [r for r in tree["regions"] if r["box"][2] < WIDE * w]
        bands = [r for r in tree["regions"] if r["box"][2] >= WIDE * w]
        els = []
        for e in d["elements"]:
            if e["kind"] not in ("box", "text", "img_candidate"):
                continue
            g = ans.get(e["id"]) or {}
            if g.get("kind") == "system" or not g:
                continue
            els.append({"id": e["id"], "det": e["kind"], "kind": g["kind"], "pressable": g["pressable"],
                        "group": g.get("group"), "image_name": g.get("image_name"),
                        "text": e.get("text"), "in_box": e.get("in_box"), "box": e["box"],
                        "box_css": [css(v) for v in e["box"]]})
        keep = {e["id"] for e in els}
        # 구역 나무의 부모 · 요소를 띠를 뺀 구역으로 다시 - 띠에 든 구역 · 요소는 단위 바로 아래
        rid = {r["id"] for r in regions}
        home = {}
        for r in tree["regions"]:
            for i in r["elements"]:
                home[i] = r["id"]
        parent = {r["id"]: r.get("parent") for r in tree["regions"]}

        def up(x):
            while x and x not in rid:
                x = parent.get(x)
            return x
        for r in regions:
            r["parent"] = up(r.get("parent"))
            r["box_css"] = [css(v) for v in r["box"]]
        for e in els:
            e["region"] = up(home.get(e["id"]))
        taps = []
        for p in flow["pairs"]:
            if p["kind"] == "tap" and p.get("tap") and cap_unit.get(p["from"]) == n and p["tap"] in keep:
                taps.append({"tap": p["tap"], "to": section_id(cap_unit[p["to"]]), "to_unit": cap_unit[p["to"]],
                             "tap_text": p.get("tap_text"), "from": p["from"], "to_capture": p["to"]})
        units[n] = {"unit": n, "section": section_id(n), "captures": caps,
                    "label": labels.get(caps[0] + ".png"), "labels": [labels.get(c + ".png") for c in caps],
                    "size": d["size"], "size_css": [WIDTH, css(d["size"][1])], "det": d,
                    "elements": els, "regions": regions, "bands": bands, "taps": taps}
    return units


def unit_image(u):
    return TRG.unit_image(u["det"], CAPTURES)
