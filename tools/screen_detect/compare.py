r"""검출 결과를 정답지와 견준다 - 글 · 이름으로 (스크린샷 입력 시험 D1 · D2).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/compare.py
        [--dir results/detect/20261012-d2] [--baseline results/detect/20261012]

읽는 것: <dir>/<캡처>.json (detect.py), <dir>/truth.json (truth.py), <dir>/_run.json.
쓰는 것: <dir>/summary.md (표), <dir>/compare.json (같은 내용의 자세한 것).

1. 짝 제안. 캡처마다 정답의 상태 가운데 글이 가장 많이 겹치는 것을 고른다. 점수는 F1 -
   재현(그 상태의 글 중 이 캡처의 OCR 이 찾은 비율)과 정밀(이 캡처의 OCR 글 중 그 상태의 글에
   닿는 비율)의 조화평균. **제안일 뿐이다** - captures.json 은 연구자가 채운다. 이 스크립트는
   그 파일을 만들거나 읽지 않는다.
2. 맞추기. 글은 공백 · 기호를 뺀 뒤(`norm`) 비슷함 0.8 이상이면 찾은 것이다. 비슷함은 OCR 글
   하나와의 비율, 또는 OCR 글을 읽는 순서로 이은 줄 안에서 가장 비슷한 같은 길이 조각과의
   비율(부분 비율) 가운데 큰 것이다 - 한 줄이 두 줄로 읽혔거나 두 줄이 한 줄로 읽혀도 맞게.
   두 글자 이하는 OCR 글 하나 또는 그 안의 낱말 하나와 같아야 한다 (숫자 키 "1" 이 "1,000,000"
   안에서 찾아지지 않게). 박스 겹침은 쓰지 않는다 - 더미앱과 재현 HTML 은 자리가 다르다.
3. 글 없는 것(그림 자리 · 아이콘만인 입구)은 글로 맞출 수 없다. 정답의 자리를 캡처 위로 대강
   옮겨(아래 `Frame`) 그 근처의 글 없는 박스 설명을 곁에 적기만 한다. 맞았다고 판정하지 않는다.
4. 남는 박스 - 정답 어디에도 닿지 않는 검출 박스. 글이 든 박스는 그 글이 정답의 글 · 버튼 ·
   입구 · 선택지 어디에도 없으면, 글 없는 박스는 옮긴 정답 자리 어디에도 들지 않고 어느 상태 하나에 캡처가 여럿이면 합계는 상태마다 그 캡처들을 합쳐 센다 - 한 장에는 화면의 일부만
보이기 때문이다. <dir>/stitched/ 에 이은 화면(stitch.py)이 있으면 그 조각들 대신 이은 화면 하나를
한 단위로 센다 (D2).

D2 에서 더한 것:
5. 그림 자리 후보 = 글 없는 박스(검출기 박스 · 아이콘으로 바꾼 OCR 자리) + 칸 안의 그림
   후보(img_candidate). (a) 상태별 정답 수 대 후보 수. (b) 은행 · 증권사 로고는 정답 이름
   "<이름> 로고" 와 후보 이름이 같으면 맞음으로 센다 - 둘 다 같은 규칙으로 만든 이름이다.
   (c) 그 밖의 그림 자리 · 아이콘 입구는 3 처럼 곁의 후보 설명을 나란히 놓기만 한다.
6. 아이콘으로 바꾼 OCR 글 목록 - 그 글이 짝지은 상태의 보이는 글과 같으면 잘못 바꾼 것.
7. --baseline 을 주면 앞 시험(D1) 결과와 합계를 나란히 놓는다.
 센다 -
한 장에는 화면의 일부만 보이기 때문이다. 캡처별 표는 한 장씩이다.
"""
import argparse
import difflib
import io
import json
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

FOUND = 0.8
OWN = 0.7
SHORT = 2
# 재현 HTML 의 창(390x844 CSS 픽셀) → 캡처 픽셀. 가로 · 세로 비를 따로 쓴다.
VIEW = (390, 844)
NEAR = 40        # 옮긴 정답 자리를 이만큼 넓혀 그 안의 글 없는 박스를 곁 설명 후보로
FAR = 120        # 그 안에 없으면 중심이 이만큼 안인 가장 가까운 것
SPAN_PAD = 80    # 맞은 닻의 세로 범위를 이만큼 넓혀 "자리상 캡처 안" 으로 본다


def norm(s):
    return re.sub(r"[\W_]+", "", (s or "").lower())


def ratio(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def partial(n, s):
    """s 안에서 n 과 가장 비슷한 같은 길이 조각과의 비율 (fuzzywuzzy partial_ratio 와 같은 길)."""
    if len(s) <= len(n):
        return ratio(n, s)
    best = 0.0
    for a, b, size in difflib.SequenceMatcher(None, n, s, autojunk=False).get_matching_blocks():
        if not size:
            continue
        start = max(0, min(b - a, len(s) - len(n)))
        best = max(best, ratio(n, s[start:start + len(n)]))
        if best == 1.0:
            break
    return best


class Pool:
    """찾을 곳 - 글 목록(정규화 전)과 그 글들을 읽는 순서로 이은 줄."""

    def __init__(self, texts, join=True):
        self.raw = [t for t in texts if t]
        self.items = [norm(t) for t in self.raw]
        self.tokens = {norm(w) for t in self.raw for w in t.split()} | set(self.items)
        self.joined = "".join(self.items) if join else ""

    def best(self, n):
        """(비슷함, 가장 비슷한 원래 글)."""
        if not n:
            return 0.0, None
        if len(n) <= SHORT:
            if n in self.tokens:
                return 1.0, next((r for r, i in zip(self.raw, self.items)
                                  if i == n or n in {norm(w) for w in r.split()}), n)
            near = max(((ratio(n, i), r) for r, i in zip(self.raw, self.items) if i),
                       default=(0.0, None))
            return min(near[0], FOUND - 0.01), near[1]
        got = max(((max(ratio(n, i), partial(n, i)), r) for r, i in zip(self.raw, self.items)
                   if i), default=(0.0, None))
        if self.joined and got[0] < 1.0:
            j = partial(n, self.joined)
            if j > got[0]:
                got = (j, "(이은 줄)")
        return got

    def has(self, n):
        return self.best(n)[0] >= FOUND


def reading(els):
    """OCR 글을 읽는 순서로 - 위에서 아래로, 같은 줄이면 왼쪽부터."""
    return sorted(els, key=lambda e: (round((e["box"][1] + e["box"][3] / 2) / 24), e["box"][0]))


# --------------------------------------------------------------------------- #
# 자리 - 정답의 자리를 캡처 위로 대강 옮긴다
# --------------------------------------------------------------------------- #
def group(thing):
    """자리 맞추기의 무리 - 스크롤과 함께 움직이는 것, 창 위에 고정된 것(상태바 · 머리), 창 아래에
    고정된 것(탭바 · 아래 버튼). 이은 화면에서는 위 · 아래 고정이 서로 멀리 떨어진다."""
    if not thing.get("pinned"):
        return "move"
    r = thing["rect"]
    return "top" if r[1] + r[3] / 2 < VIEW[1] / 2 else "bottom"


class Frame:
    """정답의 글 조각(닻)을 캡처의 OCR 글과 맞춰, 세로 자리를 직선 y' = a·y + b 로 옮긴다.
    무리(group - 움직이는 것 · 위 고정 · 아래 고정)마다 따로 맞춘다. 기울기 a 는 닻 둘씩의
    기울기의 중앙값(Theil-Sen) - 더미앱과 재현 HTML 은 줄 높이가 달라(은행 칸 88 CSS px 대
    약 280 캡처 px) 창 비율만으로는 아래로 갈수록 어긋난다. 닻이 하나면 창 비율, 없으면 그
    무리의 자리를 모른다. 가로는 창 비율 그대로다."""

    def __init__(self, state, det):
        w, h = det["size"]
        self.size = (w, h)
        # 기본 비율은 가로 비율 하나 - 이은 화면은 세로가 창 몇 개 길이라 h / 844 가 비율이 아니다
        self.sx = self.sy = w / VIEW[0]
        texts = [e for e in det["elements"] if e["kind"] == "text"]
        counts = {}
        for a in state["anchors"]:
            counts[norm(a["text"])] = counts.get(norm(a["text"]), 0) + 1
        pts = {"move": [], "top": [], "bottom": []}
        for a in state["anchors"]:
            n = norm(a["text"])
            if len(n) < 2 or counts[n] > 1:
                continue
            hits = [e for e in texts if ratio(n, norm(e["text"])) >= 0.9]
            if len(hits) != 1:
                continue
            e = hits[0]
            pts[group(a)].append((a["rect"][1] + a["rect"][3] / 2, e["box"][1] + e["box"][3] / 2))
        self.fit = {k: self._fit(v) for k, v in pts.items()}
        self.anchors = {k: len(v) for k, v in pts.items()}
        # 맞은 닻이 걸친 세로 범위 - 그 밖으로 늘여 옮긴 자리는 믿지 않는다 (아래 inside)
        self.span = {k: (min(y for _, y in v), max(y for _, y in v)) if v else None
                     for k, v in pts.items()}

    def _fit(self, pts):
        if not pts:
            return None
        slopes = [(y2 - v1) / (x2 - u1) for i, (u1, v1) in enumerate(pts)
                  for x2, y2 in pts[i + 1:] if abs(x2 - u1) > 10]
        a = statistics.median(slopes) if slopes else self.sy
        if not 0.5 * self.sy <= a <= 2.5 * self.sy:
            a = self.sy
        return a, statistics.median(v - a * u for u, v in pts)

    def map(self, thing):
        """정답 자리 → 캡처 픽셀 [x, y, w, h]. 자리를 모르면 None."""
        if not thing.get("rect"):
            return None
        f = self.fit[group(thing)]
        if f is None:
            return None
        x, y, w, h = thing["rect"]
        return [x * self.sx, y * f[0] + f[1], w * self.sx, h * f[0]]

    def inside(self, thing):
        """옮긴 자리의 중심이 이 캡처에 보이는 범위 안인가 - 같은 무리(움직임/고정)의 맞은 닻이
        걸친 세로 범위 ± SPAN_PAD 안이면 그렇다. 늘여 짐작하지 않는다: 시트 머리 밑으로 스크롤해
        들어간 줄, 더미앱에서는 스크롤로 사라지는 머리(재현 HTML 에서는 고정)가 '안' 으로
        잘못 세지 않게. 자리를 모르면 None."""
        r = self.map(thing)
        span = self.span[group(thing)]
        if r is None or span is None:
            return None
        cy = r[1] + r[3] / 2
        return span[0] - SPAN_PAD <= cy <= span[1] + SPAN_PAD and 0 <= cy <= self.size[1]


def centre(b):
    return (b[0] + b[2] / 2, b[1] + b[3] / 2)


def within(p, r, pad=0):
    return r[0] - pad <= p[0] <= r[0] + r[2] + pad and r[1] - pad <= p[1] <= r[1] + r[3] + pad


def near_box(r, boxes):
    """옮긴 자리 r 곁의 글 없는 박스 하나 (없으면 None)."""
    if r is None:
        return None
    c = centre(r)
    dist = lambda b: ((centre(b["box"])[0] - c[0]) ** 2 + (centre(b["box"])[1] - c[1]) ** 2) ** 0.5
    inner = [b for b in boxes if within(centre(b["box"]), r, NEAR)]
    if inner:
        return min(inner, key=dist)
    close = [b for b in boxes if dist(b) <= FAR]
    return min(close, key=dist) if close else None


# --------------------------------------------------------------------------- #
# 정답의 항목
# --------------------------------------------------------------------------- #
def items_of(state):
    """그 상태에서 찾을 것 - kind 마다 {key, label, n(정규화 글), thing(자리)}."""
    anchors, raw = {}, {}
    for a in state["anchors"]:
        anchors.setdefault(norm(a["text"]), a)
        raw.setdefault(a["text"].strip(), a)

    def anchor_of(line):
        n = norm(line)
        if not n:
            # 기호만인 줄(‹ ✕ ⌫) - 글자 그대로 찾는다 (자리만 쓴다: 남는 박스 판단)
            return raw.get(line.strip())
        if n in anchors:
            return anchors[n]
        return next((a for k, a in anchors.items() if k and (k in n or n in k)), None)

    out = []
    for t in state["texts"]:
        out.append({"kind": "text", "label": t, "n": norm(t), "thing": anchor_of(t) or {}})
    for b in state["task_buttons"]:
        label = b["text"] if norm(b["text"]) else (b["aria"] or b["img"] or b["text"])
        out.append({"kind": "button", "label": label, "n": norm(b["text"]), "thing": b,
                    "action": b["action"], "path": b["path"]})
    for e in state["entrances"]:
        out.append({"kind": "entrance", "label": e["text"] if norm(e["text"]) else e["aria"],
                    "n": norm(e["text"]), "thing": e, "action": e["action"], "aria": e["aria"]})
    for action, els in sorted(state["choice_items"].items()):
        for c in els:
            out.append({"kind": "choice", "label": c["text"] or c["value"], "n": norm(c["text"]),
                        "thing": c, "action": action, "value": c["value"]})
    for s in state["image_slots"]:
        out.append({"kind": "slot", "label": s["label"], "n": "", "thing": s,
                    "action": s["action"]})
    for f in state.get("fields") or []:
        # 입력칸 - 보이는 글(라벨 · 값) 또는 빈 칸의 안내 글. 둘 다 없으면(비밀번호 점) 글 없는 것
        label = f["text"] or f["placeholder"] or f["id"]
        out.append({"kind": "field", "label": label, "n": norm(f["text"] or f["placeholder"]),
                    "thing": f, "action": f["id"]})
    return out


def key(it):
    return "%s|%s|%s" % (it["kind"], it.get("action") or "", it["label"])


# --------------------------------------------------------------------------- #
def pairing(truth, dets):
    """캡처마다 상태별 (F1, 재현, 정밀, 그 상태만의 글 재현) - 제안할 것이 맨 앞.

    덮개 규칙: 팝업 · 시트가 밑 화면 위에 뜬 캡처는 밑 화면의 글이 더 많아 F1 로는 밑 화면이
    뽑힌다 (더미앱의 오류 팝업은 계좌 화면 위에 뜨고, 재현 HTML 의 오류 화면에는 팝업만 있다).
    그래서 그 상태만의 글(다른 상태에 없는 글)이 둘 이상이고 그 OWN 이상이 이 캡처에서 찾아진
    상태가 있으면 그것들 가운데에서 F1 이 큰 것을 앞세운다."""
    df = {}
    for st in truth["states"]:
        for n in {norm(t) for t in st["texts"]} - {""}:
            df[n] = df.get(n, 0) + 1
    out = {}
    for name, det in dets.items():
        ocr = reading([e for e in det["elements"] if e["kind"] == "text"])
        pool = Pool([e["text"] for e in ocr])
        rows = []
        for st in truth["states"]:
            ns = [n for n in (norm(t) for t in st["texts"]) if n]
            tpool = Pool(st["texts"])
            r = sum(pool.has(n) for n in ns) / len(ns) if ns else 0
            on = [norm(e["text"]) for e in ocr if norm(e["text"])]
            p = sum(tpool.has(n) for n in on) / len(on) if on else 0
            f = 2 * r * p / (r + p) if r + p else 0
            own = [n for n in set(ns) if df[n] == 1]
            rows.append({"state": st["state"], "screen": st["screen"], "f1": round(f, 3),
                         "recall": round(r, 3), "precision": round(p, 3),
                         "own": round(sum(pool.has(n) for n in own) / len(own), 3)
                         if len(own) >= 2 else None})
        # 같은 점수면 흐름에서 앞선 상태 (정답 걸음 · 오류 경로의 순서)
        rows.sort(key=lambda x: -x["f1"])
        cover = [r for r in rows if r["own"] is not None and r["own"] >= OWN]
        if cover and cover[0] is not rows[0]:
            rows.remove(cover[0])
            rows.insert(0, dict(cover[0], rule="덮개"))
        out[name] = rows
    return out


CUT_MARKS = ".…"


def truncated_match(label, names):
    """잘린 이름의 후보 - 후보 이름("<앞부분>. 로고" · "<앞부분>… 로고")의 앞부분으로 정답 이름이
    시작하면 그 후보. 앞부분은 두 글자 이상이어야 한다."""
    want = label.strip()
    if not want.endswith(" 로고"):
        return None
    for name, c in names.items():
        base = name[:-len(" 로고")] if name.endswith(" 로고") else None
        if not base or base[-1] not in CUT_MARKS:
            continue
        head = base.rstrip(CUT_MARKS)
        if len(head) >= 2 and want[:-len(" 로고")].startswith(head) and want != name:
            return c
    return None


def judge_capture(det, st):
    """캡처 한 장 대 상태 하나."""
    frame = Frame(st, det)
    texts = [e for e in det["elements"] if e["kind"] == "text"]
    boxes = [e for e in det["elements"] if e["kind"] == "box"]
    plain = [b for b in boxes if not b["text"]]
    cands = [e for e in det["elements"] if e["kind"] == "img_candidate"]
    names = {}
    for c in cands + plain:
        if c.get("name"):
            names.setdefault(c["name"].strip(), c)
    ocr = Pool([e["text"] for e in reading(texts)])
    inbox = Pool([b["text"] for b in boxes if b["text"]], join=False)
    rows = []
    picked = set()
    pools = {e["id"]: Pool([e["text"]], join=False) for e in det["elements"]
             if e["kind"] in ("text", "box") and e.get("text")}
    parent = {e["id"]: e.get("in_box") for e in texts}

    def els_of(n):
        """글 n 이 닿는 요소 - 그 글을 읽은 글 줄 · 박스, 그리고 그 글 줄을 담은 박스."""
        hit = [i for i, pl in pools.items() if pl.has(n)]
        if not hit and n:
            # 한 요소에 다 들지 않는 항목(줄 전체가 입구인 "자주쓰는 계좌 편집 0개 ⌄", 두 줄로 읽힌
            # "얼마를 보낼까요?") - 그 항목의 조각인 글 줄들 (두 글자 이상)
            hit = [i for i, pl in pools.items() if pl.items[0] and len(pl.items[0]) >= 2
                   and pl.items[0] in n]
        return sorted(set(hit) | {parent[i] for i in hit if parent.get(i)})

    def els_at(thing):
        """글 없는 정답 것(‹ ✕ · 아이콘만)이 닿는 요소 - 옮긴 자리 안에 중심이 있는 요소."""
        r = frame.map(thing)
        if r is None or frame.inside(thing) is False:
            return []
        return [e["id"] for e in det["elements"] if within(centre(e["box"]), r, NEAR / 2)]
    for it in items_of(st):
        r = frame.map(it["thing"])
        row = {"kind": it["kind"], "label": it["label"], "action": it.get("action"),
               "key": key(it), "in_frame": frame.inside(it["thing"])}
        cut = truncated_match(it["label"], names) if it["kind"] == "slot" else None
        if it["kind"] == "slot" and (it["label"].strip() in names or cut):
            # 로고 - 후보 이름이 정답 이름과 같다 (둘 다 "<이름> 로고" 규칙이라 판정한다).
            # 화면이 이름을 잘라 보인 것("아이엠뱅크(대." 로고)은 앞부분이 같으면 맞음이되
            # 잘린 이름으로 따로 센다 - 뒷부분을 짐작해 채우지 않는다 (연구자 결정 2026-10-13)
            c = names.get(it["label"].strip()) or cut
            row.update(icon=True, named=c["id"], near=c["id"], caption=c["caption"],
                       truncated=c["name"] if cut and it["label"].strip() not in names else None)
        elif it["kind"] == "slot" or not it["n"]:
            pool = [c for c in plain + cands if not c.get("name")]
            nb = near_box(r, pool) if row["in_frame"] is not False else None
            row.update(icon=True, named=None, near=nb and nb["id"], caption=nb and nb["caption"],
                       ocr_guess=nb and nb.get("ocr_guess"))
            if nb:
                picked.add(nb["id"])
        else:
            sim, hit = ocr.best(it["n"])
            row.update(icon=False, found=sim >= FOUND, in_box=inbox.has(it["n"]),
                       sim=round(sim, 2), closest=hit)
        row["els"] = els_of(it["n"]) if not row["icon"] else \
            [x for x in (row.get("named") or row.get("near"),) if x]
        rows.append(row)
    # 누를 수 있는 정답 것 전부 (truth.py 의 actions - 뒤로 · 닫기 · 탭 · 지우기 포함)에 닿는 요소.
    # 의미 층이 누를 수 있다고 한 요소가 정답에 있는지 가르는 데 쓴다
    action_ids = set()
    for act in st.get("actions") or []:
        n = norm(act.get("text") or "")
        action_ids.update(els_of(n) if n else els_at(act))
    for row in rows:
        if row["kind"] in ("button", "entrance", "choice", "field"):
            action_ids.update(row["els"])

    # 남는 박스
    truth_pool = Pool([it["label"] for it in items_of(st) if it["n"]])
    places = [frame.map(it["thing"]) for it in items_of(st)]
    places = [p for p in places if p]
    left = []
    for b in boxes:
        inner = [norm(e["text"]) for e in texts if e["in_box"] == b["id"]]
        inner = [n for n in inner if n]
        if inner:
            if not any(truth_pool.has(n) for n in inner):
                left.append(b)
        elif b["id"] not in picked and not any(within(centre(b["box"]), p, NEAR)
                                               for p in places):
            left.append(b)
    extra_text = [e for e in texts if norm(e["text"]) and not truth_pool.has(norm(e["text"]))
                  and not Pool(st["texts"]).has(norm(e["text"]))]
    def kind_of(b):
        fl = b.get("flags") or []
        return "system_band" if "system_band" in fl else \
            "behind_overlay" if "behind_overlay" in fl else "other"
    return {"rows": rows, "boxes": len(boxes), "plain_boxes": len(plain),
            "img_candidates": len(cands), "named": len(names),
            "names": sorted(names), "action_ids": sorted(action_ids),
            "has_actions": "actions" in st,
            "leftover": [{"id": b["id"], "text": b["text"], "caption": b["caption"],
                          "why": kind_of(b)} for b in left],
            "extra_text": [e["text"] for e in extra_text],
            "frame": {"fit": {str(k): v for k, v in frame.fit.items()}, "anchors": frame.anchors}}


def tally(rows, kind):
    rs = [r for r in rows if r["kind"] == kind]
    words = [r for r in rs if not r["icon"]]
    return {"total": len(rs), "with_text": len(words),
            "found": sum(r["found"] for r in words),
            "in_box": sum(r["in_box"] for r in words),
            "icon": len(rs) - len(words)}


def merge_rows(per):
    """같은 상태의 여러 캡처를 합친다 - 한 장에서라도 찾았으면 찾은 것."""
    out = {}
    for name, res in per:
        for r in res["rows"]:
            m = out.setdefault(r["key"], dict(
                {k: v for k, v in r.items()
                 if k not in ("found", "in_box", "sim", "closest", "near", "caption", "named")},
                captures=[], missed_in_frame=[], seen_in=[]))
            m["captures"].append(name)
            if not r["icon"]:
                m["found"] = m.get("found", False) or r["found"]
                m["in_box"] = m.get("in_box", False) or r["in_box"]
                if r["found"]:
                    m["seen_in"].append(name)
                elif r["in_frame"]:
                    m["missed_in_frame"].append(name)
                if r["sim"] > m.get("sim", -1) and not r["found"]:
                    m.update(sim=r["sim"], closest=r["closest"])
            else:
                m["named"] = m.get("named") or r.get("named")
                if r.get("near") and not m.get("near_from"):
                    m.update(near=r["near"], caption=r["caption"], near_from=name,
                             ocr_guess=r.get("ocr_guess"))
            m["in_frame_any"] = m.get("in_frame_any") or bool(r["in_frame"])
    return list(out.values())


# --------------------------------------------------------------------------- #
def pct(a, b):
    return "%d/%d (%.0f%%)" % (a, b, 100.0 * a / b) if b else "-"


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ")
                                     for c in r) + " |")
    return "\n".join(out)


def load_units(folder):
    """캡처 이름 → 검출 결과. stitched/ 의 이은 화면이 있으면 그 조각들 대신 한 단위로 센다
    (이름 "<화면>(<조각>+…)")."""
    load = lambda p: json.load(io.open(os.path.join(folder, p), encoding="utf-8"))
    units = {f[:-5]: load(f) for f in os.listdir(folder)
             if f.endswith(".json") and not f.startswith("_")
             and f not in ("truth.json", "compare.json")}
    sd = os.path.join(folder, "stitched")
    if os.path.isdir(sd):
        for f in sorted(os.listdir(sd)):
            if f.endswith(".json"):
                st = load(os.path.join("stitched", f))
                for c in st["captures"]:
                    units.pop(c, None)
                units["%s(%s)" % (st["screen"], "+".join(st["captures"]))] = st
    first = lambda n: units[n].get("captures", [n])[0]
    return {n: units[n] for n in sorted(units, key=first)}


def baseline(folder):
    """앞 시험(D1)의 compare.json 에서 합계를 다시 센다 (D1 대 D2 표)."""
    c = json.load(io.open(os.path.join(folder, "compare.json"), encoding="utf-8"))
    per = c["per_capture"].values()
    return {"totals": c["totals"], "candidates": sum(p["plain_boxes"] + p.get("img_candidates", 0)
                                                     for p in per),
            "leftover": sum(len(p["leftover"]) for p in per),
            "boxes": sum(p["boxes"] for p in per), "units": len(c["per_capture"]),
            "logos": sum(1 for rs in c["per_state"].values() for r in rs
                         if r["kind"] == "slot" and r.get("action") == "pick-bank"
                         and r.get("named"))}


def row_table(dirs, names=None):
    """폴더마다 compare.json 의 row 를 한 줄로 - 설정 대 지표 표 (D2.5)."""
    def frac(v):
        return "%d/%d" % tuple(v)
    out = []
    for i, d in enumerate(dirs):
        r = json.load(io.open(os.path.join(d, "compare.json"), encoding="utf-8"))["row"]
        b, lo = r["box_recall"], r["leftover"]
        out.append([names[i] if names else os.path.basename(d.rstrip("/\\")), frac(r["text"]),
                    frac(r["logos"]), frac(r["choices"]), frac(b["button"]), frac(b["entrance"]),
                    frac(b["choice"]), frac(b["field"]), r["candidates"],
                    "%d (%d · %d · %d)" % (lo["total"], lo["behind_overlay"], lo["system_band"],
                                           lo["other"]),
                    r["boxes"], "%.2f" % r["sec_per_image"] if r.get("sec_per_image") else "-"])
    return table(["설정", "글", "로고", "선택지", "박스: 버튼", "박스: 입구", "박스: 선택지",
                  "박스: 입력칸", "그림 자리 후보", "남는 박스 (덮개 뒤 · 고정 띠 · 그 밖)",
                  "검출 박스", "초/장"], out)


# --------------------------------------------------------------------------- #
# 의미 층 (D3) - semantic.py 의 답을 정답과 견준다
# --------------------------------------------------------------------------- #
KEYPAD = {"acc-num", "num", "pw"}       # 정답의 숫자판 무리 (data-v 키) - 나머지 선택지는 choice


def load_semantic(folder):
    """단위 → {id: 답} (실패한 단위는 None), 그리고 _semantic.json."""
    out = {}
    for f in os.listdir(folder):
        if f.endswith(".semantic.json"):
            r = json.load(io.open(os.path.join(folder, f), encoding="utf-8"))
            out[r["unit"]] = ({e["id"]: e for e in r["elements"]} if r["status"] == "ok"
                              else None)
    summ = os.path.join(folder, "_semantic.json")
    return out, (json.load(io.open(summ, encoding="utf-8")) if os.path.exists(summ) else None)


def is_cut(name):
    base = (name or "").strip()
    for tail in (" 아이콘", " 로고"):
        if base.endswith(tail):
            base = base[:-len(tail)]
    return bool(base) and base[-1] in CUT_MARKS


def roles(names, per, dets, sem, states, pick):
    """역할 지표와 목록. 정답 항목마다 닿는 요소(els) 가운데 하나라도 그 역할이면 맞음 - 한 항목이
    글 줄 · 박스 둘에 닿기 때문이다. 같은 상태의 여러 단위는 합친다 (하나에서라도 맞으면 맞음)."""
    by = {}
    for n in names:
        ans = sem.get(n)
        for r in per[n]["rows"]:
            k = (pick[n], r["key"])
            m = by.setdefault(k, dict(state=pick[n], kind=r["kind"], label=r["label"],
                                      action=r.get("action"), icon=r["icon"],
                                      text_only=False, pressable=False, kinds=set(),
                                      groups=[], image_names=[], image_shapes=[], units=[], els=[],
                                      failed=False, rule_named=False))
            m["units"].append(n)
            m["rule_named"] = m["rule_named"] or bool(r.get("named"))
            if ans is None:
                m["failed"] = True
                continue
            got = [ans[i] for i in r["els"] if i in ans]
            m["els"] += r["els"]
            m["pressable"] = m["pressable"] or any(g["pressable"] for g in got)
            m["kinds"].update(g["kind"] for g in got)
            pick_g = [g for g in got if g["kind"] in ("choice", "keypad_key")] or got
            m["groups"] += [g["group"] for g in pick_g if g.get("group")]
            m["image_names"] += [g["image_name"] for g in got if g.get("image_name")]
            # 보이는 모양 (D3b - image_name 은 뜻 이름, image_shape 는 모양). 앞 판의 답에는 없다
            m["image_shapes"] += [g.get("image_shape") for g in got if g.get("image_name")]
            if not r["icon"] and r.get("found") and not r.get("in_box"):
                m["text_only"] = True
    rows = list(by.values())

    def frac(rs, ok):
        return [sum(1 for r in rs if ok(r)), len(rs)]
    press = [r for r in rows if r["kind"] in ("button", "entrance")]
    out = {"pressable_text": frac([r for r in press if not r["icon"]], lambda r: r["pressable"]),
           "pressable_icon": frac([r for r in press if r["icon"]], lambda r: r["pressable"]),
           "text_only": [dict(state=r["state"], kind=r["kind"], label=r["label"],
                              pressable=r["pressable"], kinds=sorted(r["kinds"]))
                         for r in rows if r["text_only"] and r["kind"] in
                         ("button", "entrance", "choice", "field")]}
    ch = [r for r in rows if r["kind"] == "choice" and r["action"] not in KEYPAD]
    keys = [r for r in rows if r["kind"] == "choice" and r["action"] in KEYPAD]
    out["choice"] = frac(ch, lambda r: "choice" in r["kinds"])
    out["keypad"] = frac(keys, lambda r: "keypad_key" in r["kinds"])
    out["field"] = frac([r for r in rows if r["kind"] == "field" and not r["icon"]],
                        lambda r: "input" in r["kinds"])
    groups = []
    for (st, act) in sorted({(r["state"], r["action"]) for r in ch + keys}):
        rs = [r for r in ch + keys if r["state"] == st and r["action"] == act]
        names_ = [g for r in rs for g in r["groups"][:1]]
        top = max(set(names_), key=names_.count) if names_ else None
        groups.append({"state": st, "action": act, "values": len(rs),
                       "top_group": top, "in_top": sum(1 for r in rs if top in r["groups"])})
    out["groups"] = groups
    slots = [r for r in rows if r["kind"] == "slot"]
    out["image"] = frac(slots, lambda r: "image" in r["kinds"])
    same, cut, diff = [], [], []
    for r in slots:
        names_ = r["image_names"]
        if not names_:
            continue
        if r["label"].strip() in [x.strip() for x in names_]:
            same.append(r)
        elif any(is_cut(x) and r["label"].startswith(x.strip().rstrip(" 아이콘로고").rstrip(CUT_MARKS))
                 for x in names_):
            cut.append(r)
        else:
            diff.append({"state": r["state"], "label": r["label"], "image_name": names_[0],
                         "image_shape": r["image_shapes"][0] if r["image_shapes"] else None})
    out["image_name_same"], out["image_name_cut"], out["image_name_diff"] = len(same), len(cut), diff
    out["image_name_checked"] = sum(1 for r in slots if r["image_names"])
    # 규칙이 이름을 붙인 로고(고정값)와 모델이 이름을 지은 것을 따로
    out["image_name_rule"] = [sum(1 for r in same + cut if r["rule_named"]),
                              sum(1 for r in slots if r["rule_named"] and r["image_names"])]
    out["image_name_model"] = [sum(1 for r in same if not r["rule_named"]),
                               sum(1 for r in slots if not r["rule_named"] and r["image_names"])]
    # 정답에 그림 자리가 없는 상태에서 image 로 잡힌 것, 정답에 없는데 누를 수 있다고 한 것, 표시
    zero, fp, fp_flag, flagged, flagged_sys, fp_list = 0, 0, 0, 0, 0, []
    for n in names:
        ans = sem.get(n)
        if ans is None:
            continue
        no_slots = not states[pick[n]]["image_slots"]
        truth_ids = set(per[n]["action_ids"])
        for e in dets[n]["elements"]:
            g = ans.get(e["id"])
            if not g:
                continue
            if no_slots and g["kind"] == "image":
                zero += 1
            fl = e.get("flags") or []
            if fl:
                flagged += 1
                flagged_sys += g["kind"] == "system"
            if g["pressable"] and e["id"] not in truth_ids:
                if fl:
                    fp_flag += 1
                else:
                    fp += 1
                    fp_list.append({"unit": n, "id": e["id"], "kind": g["kind"],
                                    "text": e.get("text") or e.get("ocr_guess"),
                                    "caption": e.get("caption")})
    out.update(image_in_zero=zero, pressable_not_in_truth=fp, pressable_not_in_truth_flagged=fp_flag,
               not_in_truth_list=fp_list, flagged=[flagged_sys, flagged],
               failed_units=[n for n in names if sem.get(n) is None],
               truth_has_actions=all(per[n]["has_actions"] for n in names))
    return out


def roles_md(ro, summ, table_):
    pc = lambda v: "%d/%d (%.0f%%)" % (v[0], v[1], 100.0 * v[0] / v[1]) if v[1] else "-"
    md = ["\n## 10. 의미 층 (D3)\n"]
    if summ:
        md.append("모델 `%s` · 프롬프트 `%s` · 입력 `%s`. 실패한 단위: %s\n"
                  % (summ["model"], summ["prompt_file"], summ["in"],
                     ", ".join(summ["totals"]["failed"]) or "없음"))
    md.append("정답 항목마다 닿는 요소(그 글을 읽은 글 줄 · 박스, 글 없는 것은 옮긴 자리의 요소) 가운데 하나라도 "
              "그 역할이면 맞음으로 센다. 과제 버튼 대 과제 밖 입구는 이 층이 정하지 않는다 - 둘을 함께 "
              "\"누를 수 있는 것\" 으로 본다.\n")
    md.append(table_(["항목", "값", "메모"], [
        ["누를 수 있는 것 - 글 있는 것 (과제 버튼 + 입구)", pc(ro["pressable_text"]), "pressable=true"],
        ["누를 수 있는 것 - 아이콘만", pc(ro["pressable_icon"]), "옮긴 자리의 요소"],
        ["박스 없이 글 줄로만 있는 것", "%d/%d" % (sum(1 for r in ro["text_only"] if r["pressable"]
                                                     or "input" in r["kinds"]),
                                                 len(ro["text_only"])),
         "누를 수 있음(입력칸은 input) - 아래 목록"],
        ["정답에 없는데 누를 수 있다고 한 것", "%d (표시 달린 것 %d 따로)"
         % (ro["pressable_not_in_truth"], ro["pressable_not_in_truth_flagged"]),
         "정답 = truth 의 누를 수 있는 data-action 전부%s" % (
             "" if ro["truth_has_actions"] else " (이 truth.json 에 actions 가 없어 과제 항목만으로 셈)")],
        ["선택지 (숫자판 밖)", pc(ro["choice"]), "kind=choice"],
        ["숫자판 키", pc(ro["keypad"]), "kind=keypad_key"],
        ["입력칸", pc(ro["field"]), "kind=input (글 있는 칸)"],
        ["그림 자리", pc(ro["image"]), "kind=image"],
        ["그림 이름 = 정답 aria-label", "%d / 이름 있는 %d (잘린 이름 %d 따로)"
         % (ro["image_name_same"], ro["image_name_checked"], ro["image_name_cut"]),
         "같은 글일 때만 맞음. 그중 규칙 이름(로고 고정값) %d/%d · 모델이 지은 이름 %d/%d"
         % tuple(ro["image_name_rule"] + ro["image_name_model"])],
        ["그림 자리가 없는 상태에서 image", "%d" % ro["image_in_zero"], ""],
        ["표시 달린 요소 중 kind=system", pc(ro["flagged"]), "system_band · behind_overlay"],
    ]))
    md.append("\n### 무리 - 같은 정답 무리가 같은 group 으로 묶였나\n")
    md.append(table_(["상태", "정답 무리", "값", "가장 많은 group", "그 group 에 든 값"],
                     [[g["state"], g["action"], g["values"], g["top_group"] or "-", g["in_top"]]
                      for g in ro["groups"]]))
    md.append("\n### 박스 없이 글 줄로만 있는 것\n")
    md.append(table_(["상태", "종류", "항목", "누를 수 있음", "답한 kind"],
                     [[r["state"], r["kind"], r["label"], "예" if r["pressable"] else "",
                       ", ".join(r["kinds"]) or "-"] for r in ro["text_only"]] or [["-"] * 5]))
    md.append("\n### 그림 이름이 정답과 다른 것 (판정하지 않고 나란히)\n")
    md.append(table_(["상태", "정답 aria-label", "답한 image_name", "답한 image_shape"],
                     [[d["state"], d["label"], d["image_name"], d.get("image_shape") or "-"]
                      for d in ro["image_name_diff"]] or [["-"] * 4]))
    md.append("\n### 정답에 없는데 누를 수 있다고 한 것 (표시 없는 것)\n")
    md.append(table_(["단위", "id", "답한 kind", "글", "설명"],
                     [[d["unit"], d["id"], d["kind"], d["text"] or "-", d["caption"] or "-"]
                      for d in ro["not_in_truth_list"]] or [["-"] * 5]))
    if summ:
        md.append("\n### 토큰 · 비용\n")
        md.append(table_(["단위", "상태", "시도", "그림", "입력 토큰", "출력 토큰 (생각)", "비용 USD",
                          "어림 입력 토큰"],
                         [[u, x["status"], x["attempts"], x["images"], x["prompt_tokens"],
                           "%d (%d)" % (x["completion_tokens"], x["reasoning_tokens"]),
                           "%.4f" % x["cost_usd"], x["estimate"]["input_tokens"]]
                          for u, x in summ["units"].items()]
                         + [["합계", "", "", summ["totals"]["images"], summ["totals"]["prompt_tokens"],
                             "%d (%d)" % (summ["totals"]["completion_tokens"],
                                          summ["totals"]["reasoning_tokens"]),
                             "%.4f" % summ["totals"]["cost_usd"], ""]]))
    return md


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261012-d2"))
    ap.add_argument("--baseline", help="앞 시험의 결과 폴더 (D1 대 D2 표)")
    ap.add_argument("--table", nargs="+", help="폴더들의 compare.json 한 줄씩을 표로 내고 끝낸다")
    ap.add_argument("--semantic", help="semantic.py 의 결과 폴더 (D3). 주면 역할 지표를 더하고 "
                                       "summary.md · compare.json 을 그 폴더에 쓴다. 정답지는 그 "
                                       "폴더의 truth.json 이 있으면 그것")
    a = ap.parse_args(argv)
    if a.table:
        print(row_table(a.table))
        return
    load = lambda p: json.load(io.open(os.path.join(a.dir, p), encoding="utf-8"))
    out_dir = a.semantic or a.dir
    tp = os.path.join(a.semantic, "truth.json") if a.semantic else None
    truth = (json.load(io.open(tp, encoding="utf-8")) if tp and os.path.exists(tp)
             else load("truth.json"))
    run = load("_run.json")
    dets = load_units(a.dir)
    names = list(dets)
    states = {s["state"]: s for s in truth["states"]}
    order = [s["state"] for s in truth["states"]]
    d2 = "icon_rule" in run["settings"]

    pairs = pairing(truth, dets)
    pick = {n: pairs[n][0]["state"] for n in names}
    per = {n: judge_capture(dets[n], states[pick[n]]) for n in names}
    by_state = {}
    for n in names:
        by_state.setdefault(pick[n], []).append((n, per[n]))
    merged = {s: merge_rows(by_state[s]) for s in order if s in by_state}

    # ------------------------------------------------------------------ 합계
    def sums(rowsets, kind):
        t = [tally(rs, kind) for rs in rowsets]
        return {k: sum(x[k] for x in t) for k in ("total", "with_text", "found", "in_box", "icon")}

    allrows = list(merged.values())
    tot = {k: sums(allrows, k) for k in ("text", "button", "entrance", "choice", "slot", "field")}
    glyphs = sum(1 for rs in allrows for r in rs if r["kind"] == "text" and r["icon"])
    cand_by_state = {s: sum(res["plain_boxes"] + res["img_candidates"] for _, res in by_state[s])
                     for s in merged}
    logo_rows = [r for rs in allrows for r in rs
                 if r["kind"] == "slot" and r["action"] == "pick-bank"]
    logos = {"total": len(logo_rows), "named": sum(bool(r.get("named")) for r in logo_rows),
             "truncated": sum(bool(r.get("truncated")) for r in logo_rows)}
    left_total = sum(len(per[n]["leftover"]) for n in names)
    left_by = {w: sum(1 for n in names for b in per[n]["leftover"] if b["why"] == w)
               for w in ("behind_overlay", "system_band", "other")}
    box_total = sum(per[n]["boxes"] for n in names)

    # 아이콘으로 바꾼 OCR 글 (D2 규칙 1) - 짝지은 상태의 글과 같으면 잘못 바꾼 것 (진짜 글)
    moved = []
    for n in names:
        tpool = Pool(states[pick[n]]["texts"], join=False)
        els = {e["id"]: e for e in dets[n]["elements"]}
        for m in dets[n].get("icon_from_ocr") or []:
            into = "%s:%s" % (m["capture"], m["into"]) if "capture" in m else m["into"]
            moved.append({"unit": n, "capture": m.get("capture", n), "text": m["text"],
                          "score": m["score"], "into": into,
                          "caption": (els.get(into) or {}).get("caption"),
                          "wrong": bool(norm(m["text"])) and tpool.has(norm(m["text"]))})

    md = []
    md.append("# 스크린샷 → 요소 검출 시험 %s (2026-10-12)\n" % ("D2" if d2 else "D1"))
    md.append("더미앱 A1 이체 캡처(`%s`)를 검출해, 원본 재현 HTML(`%s`)을 원본 흐름(`%s`)대로 "
              "걸어 얻은 정답지(`truth.json`)와 글 · 이름으로 견준 것이다. 만든 스크립트: "
              "`tools/screen_detect/` (README.md). 단위 %d개%s.\n"
              % (run["captures"], truth["original"], truth["flow"], len(names),
                 " - 스크롤 조각은 이은 화면 하나로 센다 (stitched/)"
                 if any("captures" in d for d in dets.values()) else ""))
    md.append("- 검출: OmniParser v2 `icon_detect_v3` (YOLOv9-E), 설명: `icon_caption` (Florence-2, "
              "`<CAPTION>`), OCR: PaddleOCR %s (%s)\n- 장치: %s (torch %s, CUDA) · OCR %s · CPU %s\n"
              "- 설정: 박스 점수 %.2f, NMS IoU %.1f, 겹친 박스 정리 %.1f, 검출 입력 %d, OCR 점수 %.1f 미만 버림\n"
              "- 한 장당 평균 (모델을 올린 뒤): OCR %.2f초 · 검출 %.2f초 · 설명 %.2f초\n"
              % (run["ocr"]["versions"]["paddleocr"], " + ".join(run["ocr"]["models"]),
                 run["torch"]["gpu"] or "CPU", run["torch"]["version"], run["ocr"]["device"],
                 run["cpu"], run["settings"]["box_threshold"], run["settings"]["nms_iou"],
                 run["settings"]["overlap_iou"], run["settings"]["imgsz"],
                 run["settings"]["text_threshold"], run["per_image_seconds_mean"]["ocr"],
                 run["per_image_seconds_mean"]["detect"], run["per_image_seconds_mean"]["caption"]))

    md.append("\n## 1. 캡처 ↔ 상태 짝 제안 (연구자 확인용)\n")
    md.append("글이 가장 많이 겹치는 상태. 점수 = F1(재현 R, 정밀 P). `덮개` 는 그 상태만의 글이 %d%% "
              "이상 찾아져 F1 1위 대신 앞세운 것이다 (compare.pairing). `동점` 은 1 · 2위의 F1 이 같다 - "
              "글로는 가를 수 없다. captures.json 은 만들거나 고치지 않았다. 상태 이름의 `~n` 은 그 "
              "걸음의 n 번째 동작 뒤, `bank+tab-sec` 은 흐름 밖의 [증권사] 탭, `error:` 는 오류 경로의 "
              "오류 상태다.\n" % (OWN * 100))

    def mark(n):
        top, nxt = pairs[n][0], pairs[n][1]
        return ", ".join(x for x in (top.get("rule"), "동점" if top["f1"] == nxt["f1"] else None) if x)
    md.append(table(["캡처", "제안 상태", "화면", "점수 (R / P)", "그 상태만의 글", "", "2위"], [
        [n, pairs[n][0]["state"], pairs[n][0]["screen"],
         "%.2f (%.2f / %.2f)" % (pairs[n][0]["f1"], pairs[n][0]["recall"], pairs[n][0]["precision"]),
         "-" if pairs[n][0]["own"] is None else "%.2f" % pairs[n][0]["own"], mark(n) or "",
         "%s %.2f" % (pairs[n][1]["state"], pairs[n][1]["f1"])] for n in names]))
    lonely = [s for s in order if s not in by_state]
    md.append("\n짝지어진 캡처가 없는 정답 상태: %s\n" % (", ".join("`%s`" % s for s in lonely) or "없음"))

    md.append("\n## 2. 전체 합계 (짝지어진 상태 %d개, 상태마다 그 캡처들을 합쳐서)\n" % len(merged))
    t = tot
    md.append(table(["항목", "값", "메모"], [
        ["글 재현율", pct(t["text"]["found"], t["text"]["with_text"]),
         "기호만인 줄 %d개(‹ ✕ ⌄ ⌫ 등)는 분모에서 뺐다" % glyphs],
        ["과제 버튼 (글 있는 것)", pct(t["button"]["found"], t["button"]["with_text"]),
         "그중 검출 박스 안의 글로 찾은 것 %d · 아이콘만 %d" % (t["button"]["in_box"], t["button"]["icon"])],
        ["과제 밖 입구 - 글 있는 것", pct(t["entrance"]["found"], t["entrance"]["with_text"]),
         "그중 박스 안 %d" % t["entrance"]["in_box"]],
        ["과제 밖 입구 - 아이콘만", "%d개" % t["entrance"]["icon"], "판정 없음 - 곁 설명은 5절"],
        ["선택지 값 (글 있는 것)", pct(t["choice"]["found"], t["choice"]["with_text"]),
         "그중 박스 안 %d · 글 없는 값 %d" % (t["choice"]["in_box"], t["choice"]["icon"])],
        ["그림 자리", "정답 %d 대 후보 %d" % (t["slot"]["total"], sum(cand_by_state.values())),
         "후보 = 글 없는 박스(아이콘) + 칸 안의 그림 후보(img_candidate). 짝지은 단위들의 합"],
        ["로고 이름 맞음", "%d/%d (잘린 이름 %d 포함)" % (logos["named"], logos["total"],
                                                    logos["truncated"]),
         "은행 · 증권사 로고 - 정답 \"<이름> 로고\" 와 후보 이름이 같은 것 (5절)"],
        ["남는 박스", "%d / 검출 박스 %d" % (left_total, box_total),
         "단위 %d개의 합. 갈래: 덮개 뒤 %d · 고정 띠 %d · 그 밖 %d (flags.py 의 표시)"
         % (len(names), left_by["behind_overlay"], left_by["system_band"], left_by["other"])],
        ["박스 재현율", " · ".join("%s %s" % (k, pct(t[key]["in_box"], t[key]["with_text"]))
                                   for k, key in (("버튼", "button"), ("입구", "entrance"),
                                                  ("선택지", "choice"), ("입력칸", "field"))),
         "글 있는 정답 항목 가운데 그 글을 감싸는 검출 박스가 있는 비율 (글은 OCR 로 찾았어도)"],
    ]))
    if a.baseline:
        b0 = baseline(a.baseline)
        bt = b0["totals"]
        md.append("\n### 앞 시험 대 이번 (`%s` 대 이 폴더)\n" % os.path.basename(a.baseline.rstrip("/\\")))
        md.append(table(["항목", "앞", "이번"], [
            ["글 재현율", pct(bt["text"]["found"], bt["text"]["with_text"]),
             pct(t["text"]["found"], t["text"]["with_text"])],
            ["과제 버튼", pct(bt["button"]["found"], bt["button"]["with_text"]),
             pct(t["button"]["found"], t["button"]["with_text"])],
            ["입구 글 있는 것 / 아이콘만",
             "%s / %d" % (pct(bt["entrance"]["found"], bt["entrance"]["with_text"]), bt["entrance"]["icon"]),
             "%s / %d" % (pct(t["entrance"]["found"], t["entrance"]["with_text"]), t["entrance"]["icon"])],
            ["선택지 값", pct(bt["choice"]["found"], bt["choice"]["with_text"]),
             pct(t["choice"]["found"], t["choice"]["with_text"])],
            ["그림 자리 정답 대 후보", "%d 대 %d" % (bt["slot"]["total"], b0["candidates"]),
             "%d 대 %d" % (t["slot"]["total"], sum(cand_by_state.values()))],
            ["로고 이름 맞음", "%d/%d" % (b0["logos"], logos["total"]),
             "%d/%d" % (logos["named"], logos["total"])],
            ["남는 박스 / 검출 박스", "%d / %d (단위 %d)" % (b0["leftover"], b0["boxes"], b0["units"]),
             "%d / %d (단위 %d)" % (left_total, box_total, len(names))],
        ]))
        md.append("\n앞 시험의 후보는 글 없는 박스 수이고(이름이 없어 로고 이름 맞음은 0), 스크롤 조각을 "
                  "장마다 따로 셌다 (겹친 부분을 두 번).\n")

    md.append("\n### 상태별\n")
    rows = []
    for s in merged:
        rs = merged[s]
        tt = {k: tally(rs, k) for k in ("text", "button", "entrance", "choice", "slot")}
        rows.append([s, ", ".join(n for n, _ in by_state[s]),
                     pct(tt["text"]["found"], tt["text"]["with_text"]),
                     pct(tt["button"]["found"], tt["button"]["with_text"]),
                     "%s · 아이콘 %d" % (pct(tt["entrance"]["found"], tt["entrance"]["with_text"]),
                                       tt["entrance"]["icon"]),
                     pct(tt["choice"]["found"], tt["choice"]["with_text"]),
                     "%d 대 %d" % (tt["slot"]["total"], cand_by_state[s]),
                     sum(len(res["leftover"]) for _, res in by_state[s])])
    md.append(table(["상태", "캡처", "글", "과제 버튼", "입구 (글 · 아이콘만)", "선택지 값",
                     "그림 자리 대 후보", "남는 박스"], rows))

    md.append("\n## 3. 캡처별\n")
    rows = []
    for n in names:
        rs = per[n]["rows"]
        tt = {k: tally(rs, k) for k in ("text", "button", "entrance", "choice", "slot")}
        fr = per[n]["frame"]
        rows.append([n, pick[n], pct(tt["text"]["found"], tt["text"]["with_text"]),
                     pct(tt["button"]["found"], tt["button"]["with_text"]),
                     "%s · 아이콘 %d" % (pct(tt["entrance"]["found"], tt["entrance"]["with_text"]),
                                       tt["entrance"]["icon"]),
                     pct(tt["choice"]["found"], tt["choice"]["with_text"]),
                     "%d 대 %d + %d" % (tt["slot"]["total"], per[n]["plain_boxes"],
                                       per[n]["img_candidates"]),
                     "%d / %d" % (len(per[n]["leftover"]), per[n]["boxes"]),
                     len(per[n]["extra_text"]),
                     "%s/%s/%s" % (fr["anchors"]["move"], fr["anchors"]["top"], fr["anchors"]["bottom"])])
    md.append(table(["캡처", "상태", "글", "과제 버튼", "입구 (글 · 아이콘만)", "선택지 값",
                     "그림 자리 대 글 없는 박스 + 칸 안 후보", "남는 박스 / 박스",
                     "정답에 없는 OCR 글", "닻 (움직임/위/아래)"], rows))
    md.append("\n캡처별 분모는 그 상태의 전부다 - 스크롤한 캡처 한 장에는 일부만 보이므로 낮게 나온다. "
              "닻은 자리를 맞추는 데 쓴 글 수(스크롤과 함께 움직이는 것 / 창 위에 고정 / 창 아래에 고정)다.\n")

    # ------------------------------------------------------------------ 놓친 것
    # 캡처 한 장 단위로도 센다 - 자리상 그 캡처 안이었는데 못 찾은 것은 같은 상태의 다른
    # 캡처에서 찾았어도 놓친 것이다 (스크롤해 다시 보인 자리에서 놓쳤다).
    missed = []
    for s, rs in merged.items():
        for r in rs:
            if r["icon"] or (r["found"] and not r["missed_in_frame"]):
                continue
            missed.append(dict(r, state=s))
    prio = {"button": 0, "entrance": 1, "choice": 2, "text": 3}
    missed.sort(key=lambda r: (r["found"], -len(r["missed_in_frame"]), prio[r["kind"]], r["state"]))
    kname = {"text": "글", "button": "과제 버튼", "entrance": "입구", "choice": "선택지 값"}
    md.append("\n## 4. 놓친 것\n")
    md.append("글 있는 항목 가운데 (가) 짝지어진 캡처 어디에서도 못 찾은 것, (나) 다른 캡처에서는 "
              "찾았지만 자리상 이 캡처 안이었는데 못 찾은 것. (가) 가 먼저, 그다음 못 찾은 캡처 수 순. "
              "`자리상 안` 은 정답 자리를 캡처 위로 옮긴 대강의 판단이다 (Frame). `가장 비슷한 OCR` 은 "
              "못 찾은 캡처에서 가장 가까웠던 OCR 글과 그 비슷함이다 (두 글자 이하는 같아야 찾은 것이라 "
              "0.79 로 자른다).\n")
    md.append(table(["#", "종류", "항목", "상태", "어디서도 못 찾음", "자리상 안인데 못 찾은 캡처",
                     "찾은 캡처", "가장 비슷한 OCR"], [
        [i + 1, kname[r["kind"]], r["label"], r["state"], "" if r["found"] else "예",
         ", ".join(r["missed_in_frame"]) or "-", ", ".join(r["seen_in"]) or "-",
         "%s (%.2f)" % (r.get("closest"), r.get("sim", 0)) if r.get("closest") else "-"]
        for i, r in enumerate(missed)]))

    # ------------------------------------------------------------------ 그림 자리
    md.append("\n## 5. 그림 자리\n")
    md.append("### (a) 상태별 정답 수 대 후보 수\n")
    md.append("후보 = 글 없는 박스(검출기 박스 · 아이콘으로 바꾼 OCR 자리) + 칸 안의 그림 후보.\n")
    rows = []
    for s in merged:
        res = [r for _, r in by_state[s]]
        rows.append([s, tally(merged[s], "slot")["total"], sum(r["plain_boxes"] for r in res),
                     sum(r["img_candidates"] for r in res), sum(r["named"] for r in res)])
    md.append(table(["상태", "정답 그림 자리", "글 없는 박스", "칸 안 후보", "그중 이름 붙은 것"], rows))

    md.append("\n### (b) 로고 이름 - 정답 \"<이름> 로고\" 대 후보 이름 (자동 판정)\n")
    md.append("둘 다 같은 규칙(\"<칸 글> 로고\")으로 만든 이름이므로 같으면 맞음으로 센다. 화면이 이름을 잘라 "
              "보인 것(\"…(대. 로고\")은 앞부분이 같으면 맞음이되 잘린 이름으로 따로 센다. 맞음 %d/%d.\n"
              % (logos["named"], logos["total"]))
    unnamed = [r for r in logo_rows if not r.get("named")]
    cut_rows = [r for r in logo_rows if r.get("truncated")]
    if cut_rows:
        md.append("잘린 이름으로 맞음 %d: %s\n" % (len(cut_rows), ", ".join(
            "%s ← 후보 \"%s\"" % (r["label"], r["truncated"]) for r in cut_rows)))
    states_of = {r["key"]: s for s, rs in merged.items() for r in rs}
    extra = sorted({c for s in ("bank", "bank+tab-sec") for _, res in by_state.get(s, [])
                    for c in res["names"]} - {r["label"].strip() for r in logo_rows}
                   - {r["truncated"] for r in logo_rows if r.get("truncated")})
    md.append(table(["못 맞은 정답 이름", "상태"], [[r["label"], states_of[r["key"]]]
                                                   for r in unnamed] or [["-", "-"]]))
    md.append("\n정답에 없는 후보 이름 (OCR 이 칸 글을 다르게 읽은 것 등): %s\n"
              % (", ".join(extra) or "없음"))

    md.append("\n### (c) 아이콘 - 정답 이름 대 OmniParser 설명 (판정하지 않는다)\n")
    md.append("로고가 아닌 그림 자리 · 아이콘 입구마다 정답 자리를 캡처 위로 옮겨(Frame) 곁의 후보를 "
              "고른 것이다. `ocr` 은 아이콘으로 바꾼 OCR 글. 자리가 맞지 않을 수 있으니 id 를 확인 "
              "그림(overlay/)에서 본다.\n")
    kinds = {"slot": "그림 자리", "entrance": "아이콘 입구", "button": "아이콘 버튼",
             "choice": "글 없는 선택지", "field": "글 없는 입력칸"}
    rows = []
    for s, rs in merged.items():
        for r in rs:
            if r["icon"] and r["kind"] != "text" and not r.get("named") and \
                    not (r["kind"] == "slot" and r["action"] == "pick-bank"):
                rows.append([s, kinds[r["kind"]], r["label"],
                             "%s %s" % (r.get("near_from") or "", r.get("near") or "-"),
                             r.get("caption") or "-", r.get("ocr_guess") or ""])
    md.append(table(["상태", "종류", "정답 이름", "후보", "OmniParser 설명", "ocr"], rows))

    # ------------------------------------------------------------------ 아이콘으로 바꾼 글
    md.append("\n## 6. 아이콘으로 바꾼 OCR 글 (D2 규칙 1)\n")
    md.append("`잘못` 은 그 글이 짝지은 상태의 보이는 글과 같은 것 (진짜 글을 아이콘으로 바꿨다).\n")
    md.append(table(["단위", "캡처", "OCR 글", "점수", "박스", "설명", "잘못"], [
        [m["unit"], m["capture"], m["text"], m["score"], m["into"], m["caption"] or "-",
         "예" if m["wrong"] else ""] for m in moved] or [["-"] * 7]))

    # ------------------------------------------------------------------ 이은 화면
    sts = [(n, d) for n, d in dets.items() if "fragments" in d]
    if sts:
        md.append("\n## 7. 스크롤 잇기 (stitched/)\n")
        md.append("조각마다 이은 좌표의 세로 자리(offset), 앞 조각과의 어긋남과 그것을 정한 방법(닻 수), "
                  "겹친 줄, 위 · 아래 고정 띠. 확인 그림은 `overlay/stitched/<화면>.png`.\n")
        rows = []
        for n, d in sts:
            for f in d["fragments"]:
                rows.append([d["screen"], f["capture"], f["offset"], f["shift"] or "-",
                             "%s (%d)" % (f["method"], f["anchors"]) if f["method"] else "-",
                             f.get("overlap_rows", 0), f["top_band"], f["bottom_band"]])
        md.append(table(["화면", "조각", "offset", "어긋남", "방법 (닻)", "겹친 줄", "위 띠", "아래 띠"],
                        rows))
        md.append("\n" + table(["화면", "크기", "합친 요소", "고정 띠라 뺀 요소", "이은 뒤 이름 붙인 로고"],
                               [[d["screen"], "%dx%d" % tuple(d["size"]), d["merged"],
                                 d["dropped_fixed"], d.get("named_across", 0)] for _, d in sts]))

    md.append("\n## 8. 남는 박스 (단위별)\n")
    tag = {"behind_overlay": " (덮개 뒤)", "system_band": " (고정 띠)", "other": ""}
    rows = [[n, ", ".join("%s %s%s" % (b["id"], b["text"] or "[%s]" % (b["caption"] or ""),
                                       tag[b["why"]])
                          for b in per[n]["leftover"]) or "-"] for n in names]
    md.append(table(["단위", "정답 어디에도 닿지 않은 박스 (글 또는 [설명]) (표시)"], rows))

    md.append("\n## 9. 정답에 없는 OCR 글 (단위별)\n")
    md.append("더미앱에만 있는 글, 시트 뒤에 비친 화면의 글, 잘못 읽은 글이 섞여 있다.\n")
    md.append(table(["캡처", "글"], [[n, " · ".join(per[n]["extra_text"]) or "-"] for n in names]))

    row = {"text": [t["text"]["found"], t["text"]["with_text"]],
           "logos": [logos["named"], logos["total"]], "logos_truncated": logos["truncated"],
           "choices": [t["choice"]["found"], t["choice"]["with_text"]],
           "box_recall": {k: [t[k]["in_box"], t[k]["with_text"]]
                          for k in ("button", "entrance", "choice", "field")},
           "candidates": sum(cand_by_state.values()), "boxes": box_total,
           "leftover": dict(left_by, total=left_total),
           "sec_per_image": run["per_image_seconds_mean"].get("total")}
    ro = None
    if a.semantic:
        sem, summ = load_semantic(a.semantic)
        ro = roles(names, per, dets, sem, states, pick)
        md += roles_md(ro, summ, table)
        md[0] = md[0].replace("요소 검출 시험", "요소 검출 · 의미 층 시험")
    with io.open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    with io.open(os.path.join(out_dir, "compare.json"), "w", encoding="utf-8") as f:
        json.dump({"pairs": {n: pairs[n][:3] for n in names}, "proposed": pick,
                   "per_capture": per, "per_state": merged, "totals": tot, "logos": logos,
                   "row": row, "roles": ro,
                   "icon_from_ocr": moved,
                   "settings": {"found": FOUND, "short": SHORT, "near": NEAR, "far": FAR}},
                  f, ensure_ascii=False, indent=1)
    print("\n".join(md[:12]))


if __name__ == "__main__":
    main()
