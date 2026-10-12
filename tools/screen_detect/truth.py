r"""정답지 - 원본 재현 HTML 을 걸어 화면 · 상태마다 보이는 것을 모은다 (스크린샷 입력 시험 D1).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/truth.py
        [--task transfer] [--out results/detect/20261012/truth.json]

과제 파일의 원본(`inputs/original_transfer.html`)을 그 과제의 원본 흐름(`flows/original.json`)
대로 걷는다. 걷기는 검사기의 것을 그대로 쓴다 - 걸음 실행 `drive.run_actions`, 화면이 켜지기를
기다리는 `drive.settle`, 방문 이름 `flow.visit_keys`, 화면을 긁는 probe `probes.INVENTORY` ·
`CHOICE_SHOWN` · `ENTRANCES` (검사 K 의 입구 · 검사 I 의 보이는 선택지와 같은 것). 판정은 하지 않는다.

검사기의 걷기와 다른 점 - 캡처는 걸음의 끝만이 아니라 그 사이의 모습도 찍혀 있다 (은행을
고른 계좌 화면, 금액을 넣은 금액 화면, 비밀번호 몇 자리). 그래서

  - 걸음 안의 동작(`do`) 하나가 끝날 때마다도 긁는다. 이름은 `<방문>~<n>` 이다 (n 번째 동작 뒤).
    `repeat` 는 한 번씩 풀어 누른다. 앞 상태와 보이는 것이 같으면 새 상태로 세지 않는다
  - 은행 시트에서 [증권사] 탭을 누른 상태를 하나 더 긁는다 (`bank+tab-sec`) - 흐름에 없는
    걸음이다. 캡처가 두 탭을 다 찍었고 증권사 29 개는 그 탭에서만 보인다
  - 오류 경로(`error_paths`)마다 오류 상태(`expect_screen`)를 긁는다 - 검사 J 의 걷기와 같은 순서

상태마다 모으는 것:

  texts         보이는 글 - 켜진 화면의 innerText 와 화면 밖에 떠 있는 것(INVENTORY), 줄마다.
                빈 입력칸의 안내 글(data-empty, CSS 로 그린다)을 더한다
  task_buttons  그 상태에서 정답 경로가 누르는 것 (+ 오류 경로에서 누르는 것, path="error").
                data-v 가 붙은 숫자 키는 선택지 값으로 세고 여기에 넣지 않는다
  entrances     과제 밖 입구 (data-action oos-*) 가운데 누를 수 있게 보이는 것 (ENTRANCES)
  image_slots   그림 자리 - 켜진 화면 안의 보이는 role="img" 와 그 aria-label
  choices       선택지 값 (CHOICE_SHOWN - 누를 수 있게 보이는 값, 무리 규칙은 검사 I 와 같다)
  fields        입력칸 - FIELDS 의 선택자 가운데 보이는 것
"""
import argparse
import asyncio
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from senior_ui import tasks as T                       # noqa: E402
from senior_ui.audit import probes as P                # noqa: E402
from senior_ui.audit.drive import run_actions, settle  # noqa: E402
from senior_ui.audit.flow import fill, load_flow, truth_of, visit_keys  # noqa: E402

# 입력칸. 원본에는 <input> 이 없다 - 숫자판으로 채우는 칸을 div 로 그렸다 (계좌번호 칸, 금액
# 표시, 비밀번호 점). 그 셋은 흐름의 required_ids 에 있는 이름이다. 다른 원본에 <input> 이
# 있으면 앞의 셋이 잡는다.
FIELDS = ["input", "textarea", "[contenteditable]", "#acc-field", "#amt-display", "#pw-dots"]

# 자리 - 모든 스크롤을 0 으로 되돌린 자리의 [x, y, w, h] (CSS 픽셀, 390x844 창) 와 스크롤과 함께
# 움직이지 않는지(pinned). 셈은 probes.ENTRANCES 의 scroll_px 와 같다 (조상들의 scrollTop 을 더한다).
# compare.py 가 캡처 위의 대강의 자리로 옮겨, 글 없는 것(그림 자리 · 아이콘 입구) 곁에 둘
# OmniParser 설명을 고르는 데만 쓴다 - 맞았는지의 판정에는 쓰지 않는다.
PLACE = r"""
  const doc = document.scrollingElement || document.documentElement;
  const scrollers = el => {
    const got = [];
    for (let n = el.parentElement; n && n !== document.body && n !== document.documentElement;
         n = n.parentElement)
      if (/(auto|scroll|overlay)/.test(getComputedStyle(n).overflowY)
          && n.scrollHeight > n.clientHeight + 1) got.push(n);
    return got;
  };
  /* 스크롤과 함께 움직이지 않는 것 - fixed · sticky 이거나, 스크롤하는 조상이 없고 문서도
     스크롤하지 않는다 (화면 아래에 붙은 탭바 · 버튼) */
  const pinned = el => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement)
      if (/^(fixed|sticky)$/.test(getComputedStyle(n).position)) return true;
    return !scrollers(el).length && doc.scrollHeight <= window.innerHeight + 1;
  };
  const box = (r, el) => { const d = pinned(el) ? 0
      : scrollers(el).reduce((s, n) => s + n.scrollTop, 0) + doc.scrollTop;
    return [Math.round(r.x), Math.round(r.y + d), Math.round(r.width), Math.round(r.height)]; };
  const place = e => ({rect: box(e.getBoundingClientRect(), e), pinned: pinned(e)});
"""


# 그 상태의 그림 자리 · 입력칸 · 선택지 요소 · 입구의 자리 · 글 조각의 자리. 켜진 화면 안에서,
# 보이는 것만 (검사 K 와 같은 PRESSABLE). 입구는 문서 전체에서 (probes.ENTRANCES 와 같다).
STATE = r"""(args) => {
  const [fields, groups] = args;
  __PRESSABLE__
  __PLACE__
  const on = document.querySelector('.screen.on') || document.body;
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const slots = Array.from(on.querySelectorAll('[role="img"]')).filter(pressable).map(e => {
    const pick = e.closest('[data-action]');
    return Object.assign({label: e.getAttribute('aria-label'),
                          action: pick ? pick.getAttribute('data-action') : null}, place(e));
  });
  const out = [];
  for (const sel of fields) {
    on.querySelectorAll(sel).forEach(e => {
      if (!pressable(e) || out.some(o => o.el === e)) return;
      const empty = Array.from(e.querySelectorAll('[data-empty]'))
                         .filter(x => !clean(x.textContent)).map(x => x.getAttribute('data-empty'));
      out.push(Object.assign({el: e, selector: sel, id: e.id || null,
                              text: clean(e.innerText || e.value),
                              placeholder: e.getAttribute('placeholder') || empty[0] || null},
                             place(e)));
    });
  }
  /* 선택지 요소 - 값(첫 data-*, 없으면 글)과 보이는 글. 무리는 CHOICE_SHOWN 이 정한 것 */
  const items = {};
  for (const a of groups) {
    items[a] = Array.from(document.querySelectorAll('[data-action="' + a + '"]'))
      .filter(pressable).map(e => {
        let v = null;
        for (const k in e.dataset) { if (k !== 'action' && clean(e.dataset[k])) { v = clean(e.dataset[k]); break; } }
        return Object.assign({value: v || clean(e.textContent), text: clean(e.innerText)}, place(e));
      });
  }
  const ent = {};
  document.querySelectorAll('[data-action^="oos-"]').forEach(e => {
    if (pressable(e) && !ent[e.getAttribute('data-action')])
      ent[e.getAttribute('data-action')] = place(e);
  });
  /* 글 조각 - 보이는 글 노드마다 한 줄. 캡처와 자리를 맞추는 닻으로만 쓴다 */
  const anchors = [];
  const walk = root => {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      const t = clean(n.nodeValue);
      if (!t || !n.parentElement || !pressable(n.parentElement)) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      const r = rg.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) continue;
      anchors.push({text: t, rect: box(r, n.parentElement), pinned: pinned(n.parentElement)});
    }
  };
  walk(on);
  return {slots: slots, fields: out.map(({el, ...rest}) => rest), choice_items: items,
          entrance_places: ent, anchors: anchors,
          placeholders: out.map(o => o.placeholder).filter(Boolean)};
}""".replace("__PRESSABLE__", P.PRESSABLE.strip()).replace("__PLACE__", PLACE.strip())

# 누를 요소 하나 - 누르기 전에 읽는다.
TARGET = r"""(sel) => {
  let e = null;
  try { e = document.querySelector(sel); } catch (err) { return null; }
  if (!e) return null;
  __PLACE__
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const img = e.querySelector('[role="img"]');
  return Object.assign({action: e.getAttribute('data-action'), id: e.id || null,
          text: clean(e.innerText), aria: e.getAttribute('aria-label'),
          img: img ? img.getAttribute('aria-label') : null, key: e.hasAttribute('data-v')},
          place(e));
}""".replace("__PLACE__", PLACE.strip())


def lines(*blocks):
    out = []
    for b in blocks:
        for ln in (b or "").split("\n"):
            ln = " ".join(ln.split())
            if ln and ln not in out:
                out.append(ln)
    return out


async def snapshot(page):
    inv = await page.evaluate(P.INVENTORY)
    ent = await page.evaluate(P.ENTRANCES)
    choices = await page.evaluate(P.CHOICE_SHOWN, [])
    st = await page.evaluate(STATE, [FIELDS, sorted(choices)])
    return {"screen": await page.evaluate(P.DOM_SCREEN),
            "texts": lines(inv.get("text"), inv.get("outside_text"), *st["placeholders"]),
            "entrances": [dict({"action": a, "text": r.get("text") or None,
                                "aria": r.get("aria") or None},
                               **st["entrance_places"].get(a, {}))
                          for a, r in sorted(ent.items()) if r.get("visible")],
            "image_slots": st["slots"],
            "choices": choices,
            "choice_items": st["choice_items"],
            "fields": st["fields"],
            "anchors": st["anchors"]}


def same(a, b):
    keys = ("screen", "texts", "entrances", "image_slots", "choices", "fields")
    return all(a[k] == b[k] for k in keys)


def expand(spec):
    """걸음의 동작 목록. repeat 는 한 번씩 풀고, wait 은 앞 동작에 붙인다."""
    out = []
    for item in spec if isinstance(spec, list) else [spec]:
        if "repeat" in item:
            for _ in range(int(item["repeat"])):
                out.append({"click": item["click"], "wait": item.get("wait", 0.1)})
        elif "wait" in item and "click" not in item and out:
            out[-1] = dict(out[-1], wait=item["wait"])
        else:
            out.append(item)
    return out


class Walk:
    def __init__(self, page, flow):
        self.page, self.truth = page, truth_of(flow)
        self.states = []

    async def keep(self, name, via):
        snap = await snapshot(self.page)
        if self.states and same(self.states[-1], snap):
            self.states[-1]["also"].append(name)
            return self.states[-1]
        snap.update(state=name, via=via, also=[], task_buttons=[])
        self.states.append(snap)
        return snap

    async def press(self, item, path, where):
        """동작 하나. 누르는 것이면 누르기 전 상태(where)에 과제 버튼으로 적는다."""
        if "click" in item and where is not None:
            sel = fill(item["click"], self.truth)
            t = await self.page.evaluate(TARGET, sel)
            if t and not t["key"]:
                row = dict(t, selector=item["click"], path=path)
                row.pop("key")
                if row not in where["task_buttons"]:
                    where["task_buttons"].append(row)
        await run_actions(self.page, [item], None, self.truth)
        await asyncio.sleep(0.25)


async def walk(url, flow):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.goto(url, wait_until="networkidle")
            w = Walk(page, flow)
            here = None
            for n, (step, visit) in enumerate(zip(flow["steps"], visit_keys(flow["steps"])), 1):
                acts = expand(step.get("do") or ({"click": step["click"]} if "click" in step else []))
                for i, item in enumerate(acts):
                    await w.press(item, "main", here)
                    if i < len(acts) - 1:
                        here = await w.keep("%s~%d" % (visit, i + 1),
                                            "정답 걸음 %d 의 동작 %d 뒤" % (n, i + 1))
                await settle(page, step["screen"])
                here = await w.keep(visit, "정답 걸음 %d" % n + (" - %s" % step["state"]
                                                              if step.get("state") else ""))
                if visit == "bank":
                    # 흐름에 없는 걸음 - [증권사] 탭. 보고 나서 [은행] 탭으로 되돌린다
                    await page.click("#tab-sec")
                    await asyncio.sleep(0.25)
                    await w.keep("bank+tab-sec", "은행 시트에서 [증권사] 탭을 누른 뒤 (흐름 밖)")
                    await page.click("#tab-bank")
                    await asyncio.sleep(0.25)
            states = w.states
            for ep in flow.get("error_paths") or []:
                states.append(await walk_error(browser, url, flow, ep))
            return states
        finally:
            await browser.close()


async def walk_error(browser, url, flow, ep):
    """오류 경로 하나 - 검사 J 의 걷기(drive.walk_error_path)와 같은 순서로 오류 상태까지."""
    page = await browser.new_page(viewport={"width": 390, "height": 844})
    try:
        await page.goto(url, wait_until="networkidle")
        w = Walk(page, flow)
        for step, visit in zip(flow["steps"], visit_keys(flow["steps"])):
            await run_actions(page, step.get("do") or ({"click": step["click"]}
                                                       if "click" in step else []),
                              None, w.truth)
            await settle(page, step["screen"])
            if visit == ep["from_step"]:
                break
        for item in expand(ep.get("inputs") or []):
            await w.press(item, "error", None)
        await settle(page, ep["expect_screen"])
        st = await w.keep("error:%s" % ep["id"], "오류 경로 %s - %s" % (ep["id"], ep.get("about")))
        for item in expand(ep.get("recover") or []):
            await w.press(item, "error", st)
        return st
    finally:
        await page.close()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="transfer")
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "detect", "20261012",
                                                  "truth.json"))
    a = ap.parse_args(argv)
    task = T.load_task(a.task)
    flow = load_flow(None, task=a.task)
    html = T.abs_path(task["original"])
    states = asyncio.run(walk("file:///" + html.replace("\\", "/"), flow))
    out = {"task": a.task, "original": task["original"], "flow": task["flow"],
           "original_sha256": T.file_sha256(html),
           "walk": "senior_ui.audit.drive.run_actions · settle + probes.INVENTORY · "
                   "CHOICE_SHOWN · ENTRANCES (검사 I · K 와 같은 probe)",
           "states": states}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with io.open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for s in states:
        print("%-22s %-12s 글 %3d  버튼 %d  입구 %2d  그림 %2d  선택지 %s  칸 %d  %s" % (
            s["state"], s["screen"], len(s["texts"]), len(s["task_buttons"]),
            len(s["entrances"]), len(s["image_slots"]),
            {k: len(v) for k, v in s["choices"].items()}, len(s["fields"]),
            ",".join(s["also"])))


if __name__ == "__main__":
    main()
