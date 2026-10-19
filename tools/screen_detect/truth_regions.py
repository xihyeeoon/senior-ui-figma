r"""구역 정답지 - 원본 재현 HTML 에서 보이는 바탕 상자(카드 · 배너 · 시트 …)를 뽑는다 (2026-10-19).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/truth_regions.py
        [--dir results/detect/20261013-d25/final] [--truth results/detect/20261013-d3b/truth.json]
        [--out results/detect/20261019-regions]

truth.py 와 같은 원본 · 같은 흐름 · 같은 걷기(390x844 창, Playwright chromium)로 걷고, 상태를 긁을 때마다
(truth.snapshot) 구역을 더 긁는다 - truth.py 는 고치지 않고 이 프로세스에서만 snapshot 을 감싼다.

구역 = 켜진 화면(.screen.on) 안의 보이는 요소 가운데
  - 바탕이 뒤와 다르다 (자기 배경색 · 배경 그림이 있고, 뒤에 보이는 것 가운데 처음 배경이 있는 것과 다르다.
    뒤 = 창 안에 보이는 부분이 있으면 그 점에서 아래에 겹친 요소 - 덮개 위 팝업처럼 형제가 뒤에 있는 것까지,
    창 밖이면 조상), 또는
    네 변 모두 테두리가 있다 (한 변만 있는 밑줄 · 구분선은 상자가 아니다), 또는 그림자(box-shadow)가 있다
  - CSS 기준 가로 40px · 세로 24px 이상
  - 안에 보이는 요소나 글이 하나 이상 있다
  - 뺀다: 상태바(.statusbar) 와 그 안, 그림 자리(role="img" - 회색 X 상자는 그림 자리로 따로 센다),
    화면 전체 바탕(창의 가로 95% · 세로 90% 이상)
  - control = 그 요소가 누를 수 있는 것 자체(data-action · button · input)인가 - 버튼 · 은행 칸도 정의에
    맞으면 구역이지만 "바탕 상자" 와 따로 센다
같은 자리(네 변 2 CSS px 안)에 겹친 구역은 바깥 것 하나만 남긴다.

구역마다 안에 든 정답 항목 - compare.items_of 의 항목(글 · 버튼 · 입구 · 선택지 · 그림 자리 · 입력칸) 가운데
자리의 중심이 구역 안인 것의 key (compare.key, "<kind>|<action>|<label>"). 글은 닻(글 조각)의 자리로 본다.

캡처 좌표로 옮기기 - compare.Frame 의 꺾은선(--frame local, 2026-10-19)으로 위 · 아래 변을 따로 옮긴다.
가로는 창 비율. 고정(pinned)된 구역의 변은 변마다 창 위쪽 절반이면 위 고정, 아니면 아래 고정 무리로 옮기고,
그 무리의 닻이 없으면 다른 고정 무리, 그것도 없으면 움직이는 무리로. 창 아래 끝까지 닿는 고정 구역(바텀시트)의
아래 변은 단위 그림의 아래 끝. 옮긴 구역이 단위 그림과 반 넘게 겹치지
않으면 그 단위에서는 뺀다 (in_unit: false).

쓰는 것: <out>/truth_regions.json, <out>/truth_figures/<단위>.png (정답 구역을 캡처 위에 - 초록 = 바탕 상자,
보라 = 조작 상자).
"""
import argparse
import asyncio
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import compare as C  # noqa: E402
import detect as D  # noqa: E402
import truth as TR  # noqa: E402

MIN_W, MIN_H = 40, 24
SAME_PX = 2

REGIONS = r"""() => {
  __PRESSABLE__
  __PLACE__
  const on = document.querySelector('.screen.on') || document.body;
  const W = window.innerWidth, H = window.innerHeight;
  const solid = c => !!c && c !== 'transparent' && !/rgba\([^)]*,\s*0\)$/.test(c);
  const own = cs => cs.backgroundImage !== 'none' ? 'img:' + cs.backgroundImage
                    : (solid(cs.backgroundColor) ? cs.backgroundColor : null);
  const behind = el => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const b = own(getComputedStyle(n));
      if (b) return b;
    }
    return 'rgb(255, 255, 255)';
  };
  /* 눈에 뒤에 보이는 바탕 - 창 안에 보이는 부분이 있으면 그 점에서 겹친 요소들(위에서부터) 가운데 이 요소
     다음의, 이 요소 안이 아닌 것 중 처음 배경이 있는 것 (덮개 위에 뜬 팝업처럼 부모가 아닌 형제가 뒤에 있는
     것). 창 밖(스크롤해야 보이는 곳)이면 부모 쪽 */
  const backdrop = el => {
    const r = el.getBoundingClientRect();
    const x0 = Math.max(r.left, 0), x1 = Math.min(r.right, W);
    const y0 = Math.max(r.top, 0), y1 = Math.min(r.bottom, H);
    if (x1 - x0 >= 2 && y1 - y0 >= 2) {
      const stack = document.elementsFromPoint(x0 + 1, y0 + (y1 - y0) / 2);
      const i = stack.indexOf(el);
      if (i >= 0) {
        for (const n of stack.slice(i + 1)) {
          if (el.contains(n)) continue;
          const b = own(getComputedStyle(n));
          if (b) return b;
        }
        return 'rgb(255, 255, 255)';
      }
    }
    return behind(el.parentElement);
  };
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const out = [];
  on.querySelectorAll('*').forEach(el => {
    if (!pressable(el) || el.closest('.statusbar') || el.getAttribute('role') === 'img') return;
    const r = el.getBoundingClientRect();
    if (r.width < __MINW__ || r.height < __MINH__) return;
    if (r.width >= 0.95 * W && r.height >= 0.9 * H) return;
    const cs = getComputedStyle(el);
    const why = [];
    const bg = own(cs);
    if (bg && bg !== backdrop(el)) why.push('background');
    const sides = ['Top', 'Right', 'Bottom', 'Left'].filter(s =>
      parseFloat(cs['border' + s + 'Width']) > 0 && cs['border' + s + 'Style'] !== 'none'
      && solid(cs['border' + s + 'Color']));
    if (sides.length === 4) why.push('border');
    if (cs.boxShadow && cs.boxShadow !== 'none') why.push('shadow');
    if (!why.length) return;
    const content = clean(el.innerText) || Array.from(el.querySelectorAll('*')).some(pressable);
    if (!content) return;
    out.push(Object.assign({tag: el.tagName.toLowerCase(), cls: el.className || '',
      text: clean(el.innerText).slice(0, 40), why: why,
      control: el.hasAttribute('data-action') || /^(BUTTON|INPUT|TEXTAREA|SELECT)$/.test(el.tagName),
      action: el.getAttribute('data-action')}, place(el)));
  });
  return out;
}""".replace("__PRESSABLE__", TR.P.PRESSABLE.strip()).replace("__PLACE__", TR.PLACE.strip()) \
    .replace("__MINW__", str(MIN_W)).replace("__MINH__", str(MIN_H))


def walk_regions():
    """truth.py 의 걷기 그대로 - snapshot 만 감싸 상태마다 구역을 더 긁는다."""
    orig = TR.snapshot

    async def snapshot(page):
        s = await orig(page)
        s["regions"] = await page.evaluate(REGIONS)
        return s
    TR.snapshot = snapshot
    task = TR.T.load_task("transfer")
    flow = TR.load_flow(None, task="transfer")
    html = TR.T.abs_path(task["original"])
    states, _ = asyncio.run(TR.walk("file:///" + html.replace("\\", "/"), flow))
    return task, html, states


def dedupe(regs):
    """같은 자리의 구역은 바깥(문서 순서에서 앞) 것 하나만."""
    out = []
    for r in regs:
        if any(all(abs(a - b) <= SAME_PX for a, b in zip(r["rect"], o["rect"])) for o in out):
            continue
        out.append(r)
    return out


def contains(rect, pt):
    x, y, w, h = rect
    return x <= pt[0] <= x + w and y <= pt[1] <= y + h


def edge_group(frame, y, pinned):
    if not pinned:
        order = ["move", "top", "bottom"]
    elif y < C.VIEW[1] / 2:
        order = ["top", "bottom", "move"]
    else:
        order = ["bottom", "top", "move"]
    return next((g for g in order if frame.fit[g] is not None), None)


def map_region(frame, reg):
    """정답 구역 → 단위 좌표 [x, y, w, h] (위 · 아래 변을 따로 꺾은선으로). 옮길 수 없으면 None.
    창 아래 끝까지 닿는 고정 구역(바텀시트)의 아래 변은 단위 그림의 아래 끝 - 이은 화면에서는 시트 안의
    목록이 스크롤되어 시트가 이은 그림 끝까지 이어진다."""
    x, y, w, h = reg["rect"]
    g0, g1 = edge_group(frame, y, reg["pinned"]), edge_group(frame, y + h, reg["pinned"])
    if g0 is None or g1 is None:
        return None
    top = frame._local(g0, y)
    bot = frame.size[1] if reg["pinned"] and y + h >= C.VIEW[1] - 1 else frame._local(g1, y + h)
    if bot <= top:
        return None
    return [round(x * frame.sx), round(top), round(w * frame.sx), round(bot - top)]


def overlap_frac(r, size):
    x, y, w, h = r
    ix = max(0, min(x + w, size[0]) - max(x, 0))
    iy = max(0, min(y + h, size[1]) - max(y, 0))
    return ix * iy / (w * h) if w * h else 0


def unit_image(det, captures):
    from PIL import Image
    if "fragments" in det:
        import stitch
        imgs = [Image.open(os.path.join(captures, f["capture"] + ".png")).convert("RGB")
                for f in det["fragments"]]
        return stitch.compose(det["fragments"], imgs)
    return Image.open(os.path.join(ROOT, det["capture"])).convert("RGB")


def draw_regions(image, regs, path, colors, label):
    """구역을 그림 위에 - regs [{box, …}], colors(reg) → RGB, label(reg) → 글."""
    from PIL import ImageDraw, ImageFont
    im = image.copy()
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(D.FONT, 16)
    for r in sorted(regs, key=lambda r: -r["box"][2] * r["box"][3]):
        x, y, w, h = r["box"]
        col = colors(r)
        d.rectangle([x, y, x + w, y + h], outline=col, width=4)
        t = label(r)
        if t:
            tw = d.textlength(t, font=font)
            d.rectangle([x + 4, y + 4, x + 8 + tw, y + 24], fill=(255, 255, 255))
            d.text((x + 6, y + 4), t, fill=col, font=font)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261013-d25", "final"))
    ap.add_argument("--truth", default=os.path.join(ROOT, "results", "detect", "20261013-d3b",
                                                    "truth.json"))
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "detect", "20261019-regions"))
    a = ap.parse_args(argv)
    C.FRAME = "local"
    truth = json.load(io.open(a.truth, encoding="utf-8"))
    task, html, walked = walk_regions()
    by_state = {s["state"]: s for s in walked}
    # 같은 걷기인지 - 상태 이름과 보이는 글이 정답지와 같아야 한다
    names = [s["state"] for s in truth["states"]]
    if [s["state"] for s in walked] != names:
        raise SystemExit("상태가 정답지와 다르다: %s" % [s["state"] for s in walked])
    same_texts = all(by_state[s["state"]]["texts"] == s["texts"] for s in truth["states"]
                     if not s["state"].startswith("password"))

    states = []
    for s in truth["states"]:
        regs = dedupe(by_state[s["state"]]["regions"])
        items = C.items_of(s)
        for k, r in enumerate(regs):
            r["id"] = "r%d" % k
            r["items"] = [C.key(it) for it in items if it["thing"].get("rect")
                          and contains(r["rect"], C.centre(it["thing"]["rect"]))]
        # 부모 구역 - 이 구역을 담은 가장 작은 다른 구역
        for r in regs:
            outer = [o for o in regs if o is not r and o["rect"][2] * o["rect"][3] > r["rect"][2] * r["rect"][3]
                     and contains(o["rect"], (r["rect"][0] + 1, r["rect"][1] + 1))
                     and contains(o["rect"], (r["rect"][0] + r["rect"][2] - 1, r["rect"][1] + r["rect"][3] - 1))]
            r["parent"] = min(outer, key=lambda o: o["rect"][2] * o["rect"][3])["id"] if outer else None
        states.append({"state": s["state"], "screen": s["screen"], "regions": regs})

    dets = C.load_units(a.dir)
    pairs = C.pairing(truth, dets)
    st_of = {s["state"]: s for s in truth["states"]}
    reg_of = {s["state"]: s["regions"] for s in states}
    units = {}
    for n, det in dets.items():
        pick = pairs[n][0]["state"]
        frame = C.Frame(st_of[pick], det)
        size = det["size"]
        rows = []
        for r in reg_of[pick]:
            box = map_region(frame, r)
            rows.append({"id": r["id"], "box": box, "control": r["control"],
                         "in_unit": bool(box) and overlap_frac(box, size) > 0.5})
        units[n] = {"state": pick, "size": size, "regions": rows,
                    "frame": {"anchors": frame.anchors,
                              "knots": {k: len(v) for k, v in frame.knots.items()}}}
        img = unit_image(det, a.captures)
        desc = {r["id"]: r for r in reg_of[pick]}
        draw_regions(img, [x for x in rows if x["in_unit"]],
                     os.path.join(a.out, "truth_figures", "%s.png" % n),
                     lambda x: (150, 60, 200) if x["control"] else (0, 160, 60),
                     lambda x: "%s %s" % (x["id"], (desc[x["id"]]["text"] or desc[x["id"]]["cls"])[:14]))

    out = {"original": task["original"], "original_sha256": TR.T.file_sha256(html),
           "truth": os.path.relpath(a.truth, ROOT).replace("\\", "/"),
           "dir": os.path.relpath(a.dir, ROOT).replace("\\", "/"),
           "rule": {"min_css": [MIN_W, MIN_H], "same_px": SAME_PX, "frame": "local",
                    "why": "background (부모와 다른 배경) | border (네 변) | shadow",
                    "excluded": ".statusbar, role=img, 창의 95% x 90% 이상"},
           "same_texts_as_truth": same_texts,
           "states": states, "units": units}
    os.makedirs(a.out, exist_ok=True)
    with io.open(os.path.join(a.out, "truth_regions.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for s in states:
        print("%-22s 구역 %2d (바탕 %2d · 조작 %2d)" % (
            s["state"], len(s["regions"]), sum(not r["control"] for r in s["regions"]),
            sum(r["control"] for r in s["regions"])))
    for n, u in units.items():
        print("%-28s %-14s 단위 안 %d / %d" % (n, u["state"], sum(r["in_unit"] for r in u["regions"]),
                                             len(u["regions"])))
    print("same_texts", same_texts)


if __name__ == "__main__":
    main()
