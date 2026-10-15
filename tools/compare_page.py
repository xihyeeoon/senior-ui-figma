r"""원본과 재구성 실행 여럿을 한 페이지에 나란히 - 그림 · 숫자 · 원칙 적용 · 바꾼 것 (2026-10-15).

    .\.venv\Scripts\python.exe tools\compare_page.py --runs <실행 id> [<실행 id> …] --name <이름>

결과는 outputs/compare/<이름>/index.html 하나와 같은 폴더의 그림들이다 (브라우저로 바로 연다).
원본은 언제나 첫 열이다 - 과제의 원본 HTML 을 그 과제의 원본 흐름대로 걸은 것 (원본 재현본),
원본 닮음의 원본 쪽은 results/reference/<과제의 원본 화면설계서>, 원본 칸에는 연구자가 더미앱에서
찍은 캡처 (inputs/captures/<과제>) 도 작게 둔다.

실행 id 는 results/runs/<id> · outputs/restructure_auto/<id> · .mock-outputs/restructure_auto/<id> 순서로
찾는다 (폴더 경로를 줘도 된다). 실행 폴더가 없거나 그 빌드를 걷지 못하면 그 열에 이유를 적고 계속한다.

파이프라인을 바꾸지 않는다. 결과 폴더와 원본은 읽기만 하고 outputs/compare/ 에만 쓴다. 가져오는 것은
읽기용 함수뿐이다 - 걷기 (storyboard/walk.py 의 new_page · states_of · replay · EXPAND, 검사기와 같은
걸음), 흐름 읽기 (audit.inputs.judged_flow · read_flow, audit.flow.load_flow), 원본 닮음 (storyboard/
likeness.py 를 부르는 tools/compare_runs.py 의 칸 - 같은 표의 같은 숫자다). 모델도 부르지 않는다.

재는 규칙은 10/13 점검 페이지 (outputs/review-1013/index.html 맨 위) 와 같다 - RULES. 그 페이지를
만든 측정 스크립트는 저장소 밖에 있었다. 여기 MEASURE · FULL 은 그 스크립트의 것을 그대로 옮겼다.
다른 점은 둘 - 걸음을 검사기 · 화면설계서와 같은 함수 (walk.replay) 로 밟고, 그 페이지처럼 시각 ·
난수를 고정한다 (walk.new_page - 비밀번호 숫자판의 차례가 늘 같다). 그림은 배율 1 이다.
"""
import argparse
import asyncio
import html as H
import io
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
for p in (ROOT, TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)

from senior_ui import tasks as T                                  # noqa: E402
from senior_ui.audit.flow import load_flow                        # noqa: E402
from senior_ui.audit.inputs import judged_flow, read_flow         # noqa: E402
from senior_ui.restructure import flow_fixed as FF                # noqa: E402
from senior_ui.storyboard import likeness as LK                   # noqa: E402
from senior_ui.storyboard import walk as W                        # noqa: E402
import compare_runs as CR                                         # noqa: E402

OUT_DIR = os.path.join(ROOT, "outputs", "compare")
RUN_HOMES = [os.path.join(ROOT, "results", "runs"),
             os.path.join(ROOT, "outputs", "restructure_auto"),
             os.path.join(ROOT, ".mock-outputs", "restructure_auto")]
CAPTURES = os.path.join(ROOT, "inputs", "captures")
# 화면을 연 뒤 (정답 걸음 · settle 뒤) 그림을 찍기 전에 기다리는 시간 - 10/13 스크립트와 같다
SETTLE_MS = 500
VH = W.VIEWPORT["height"]

RULES = [
    ("찍는 법", "Chromium 헤드리스, 창 390×844, 배율 1. 각 빌드를 자기 흐름 명세(steps)대로 매번 새 "
     "페이지에서 그 화면에 처음 닿을 때까지 몰고 간다 (검사기 · 화면설계서와 같은 걸음 함수 "
     "storyboard/walk.replay, 시각 · 난수 고정). 정답 값은 과제의 원본 흐름의 것 (이체: 계좌 "
     "110234567890 · 은행 신한 · 금액 32000)."),
    ("첫 화면 안 누를 것", "스크롤 0 상태에서 잰다. [data-action] 요소 가운데 보이는 것(display · "
     "visibility · 조상 opacity, 크기 > 0), 그리고 가운데 점이 창(0~844) 과 넘침(overflow) 조상의 잘림 "
     "안에 드는 것."),
    ("화면 높이", "그 다음 켜진 화면 안의 스크롤 요소가 넘치는 만큼 #phone 을 늘린다 (storyboard/"
     "walk.py 의 EXPAND). 늘린 #phone 의 높이 = 화면 높이. 그림도 이 상태에서 찍는다 — 아래 고정 버튼은 "
     "맨 아래에 온다."),
    ("누를 것", "펼친 상태에서 보이는 [data-action] 요소 수 (안에 든 것도 따로 센다)."),
    ("가장 작은 글자", "자기 글(텍스트 노드)을 가진 보이는 요소의 computed font-size 최소. "
     ".statusbar(가짜 시계 · 배터리) 는 뺀다."),
    ("가장 작은 누를 것 높이", "보이는 [data-action] 요소의 getBoundingClientRect 높이 최소."),
    ("가장 낮은 글 대비", "위 글 요소마다 글자색과 그 뒤 배경색(조상의 background-color 를 알파 합성, "
     "없으면 흰색) 의 WCAG 대비. 그라디언트 · 그림 배경 위의 글과 투명 글자(그림 자리) 는 뺀다. 꺼진 "
     "버튼 글도 센다."),
    ("글 덩어리 수", "자기 글을 가진 보이는 요소 수 (참고용 — 글이 얼마나 늘었나)."),
    ("원본 닮음 · 격자 · 탭", "tools/compare_runs.py 의 두 칸 그대로 (storyboard/likeness.py - 원본 "
     "화면설계서와 실행의 화면설계서 storyboard.json 을 견준다). 실행에 화면설계서가 없으면 잴 수 "
     "없다 — python -m senior_ui.storyboard <실행 폴더> --mock 으로 만든다 (모델을 부르지 않는다)."),
]

# --------------------------------------------------------------------------- #
# 재는 것 - 10/13 점검 스크립트의 것 그대로 (outputs/review-1013 의 metrics.json 을 만든 것)
# --------------------------------------------------------------------------- #
MEASURE = r"""() => {
  const phone = document.getElementById('phone');
  const VH = 844;
  const vis = el => {
    if (!el.getClientRects().length) return false;
    for (let p = el; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.display === 'none' || +cs.opacity === 0) return false;
      if (p === el && cs.visibility === 'hidden') return false;
    }
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const clipRect = el => {
    let r = el.getBoundingClientRect();
    let t = r.top, b = r.bottom, l = r.left, rr = r.right;
    for (let p = el.parentElement; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.overflowY !== 'visible' || cs.overflowX !== 'visible') {
        const q = p.getBoundingClientRect();
        t = Math.max(t, q.top); b = Math.min(b, q.bottom); l = Math.max(l, q.left); rr = Math.min(rr, q.right);
      }
    }
    t = Math.max(t, 0); b = Math.min(b, VH);
    return {t, b, l, r: rr};
  };
  const acts = [...phone.querySelectorAll('[data-action]')].filter(vis);
  const first = acts.filter(el => {
    const c = clipRect(el); if (c.b <= c.t || c.r <= c.l) return false;
    const r = el.getBoundingClientRect(); const cy = (r.top + r.bottom) / 2, cx = (r.left + r.right) / 2;
    return cy >= c.t && cy <= c.b && cx >= c.l && cx <= c.r;
  });
  return {first_viewport_pressables: first.length, first_list: first.map(e => e.dataset.action)};
}"""

FULL = r"""() => {
  const phone = document.getElementById('phone');
  const vis = el => {
    if (!el.getClientRects().length) return false;
    for (let p = el; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.display === 'none' || +cs.opacity === 0) return false;
      if (p === el && cs.visibility === 'hidden') return false;
    }
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const parse = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const v = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r:v[0],g:v[1],b:v[2],a: v.length>3? v[3]:1}; };
  const lum = c => { const f = x => { x/=255; return x<=0.03928? x/12.92 : Math.pow((x+0.055)/1.055,2.4); };
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
  const blend = (top, bot) => ({r: top.r*top.a + bot.r*(1-top.a), g: top.g*top.a + bot.g*(1-top.a), b: top.b*top.a + bot.b*(1-top.a), a: 1});
  const bgOf = el => {
    const layers = [];
    for (let p = el; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 1) break; }
    }
    let acc = {r:255,g:255,b:255,a:1};
    for (let i = layers.length - 1; i >= 0; i--) acc = blend(layers[i], acc);
    return acc;
  };
  const sw = s => s.replace(/\s+/g, ' ').trim();
  const acts = [...phone.querySelectorAll('[data-action]')].filter(vis);
  let minTarget = null;
  acts.forEach(el => { const r = el.getBoundingClientRect();
    if (!minTarget || r.height < minTarget.h) minTarget = {h: Math.round(r.height*10)/10, w: Math.round(r.width), text: sw(el.innerText||el.getAttribute('aria-label')||'').slice(0,30), action: el.dataset.action}; });
  const under44 = acts.filter(el => el.getBoundingClientRect().height < 44).length;
  const texts = [];
  phone.querySelectorAll('*').forEach(el => {
    if (el.closest('.statusbar')) return;
    if (!vis(el)) return;
    const own = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('');
    if (!sw(own)) return;
    texts.push(el);
  });
  let minFont = null, minC = null, nUnder16 = 0;
  texts.forEach(el => {
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    const t = sw([...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('')).slice(0, 30);
    if (fs < 16) nUnder16++;
    if (!minFont || fs < minFont.px) minFont = {px: fs, text: t};
    const fg = parse(cs.color); if (!fg || fg.a === 0) return;
    const bg = bgOf(el); if (!bg) return;
    const f2 = fg.a < 1 ? blend(fg, bg) : fg;
    const L1 = lum(f2), L2 = lum(bg);
    const ratio = (Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    if (!minC || ratio < minC.ratio) minC = {ratio: Math.round(ratio*100)/100, text: t, px: fs};
  });
  return {pressables: acts.length, min_target: minTarget, under44, min_font: minFont,
          text_elems: texts.length, under16: nUnder16, min_contrast: minC};
}"""


# --------------------------------------------------------------------------- #
# 열 (원본 · 실행) 읽기
# --------------------------------------------------------------------------- #
def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def find_run(rid):
    """실행 폴더. 없으면 None."""
    if os.path.isdir(rid):
        return os.path.abspath(rid)
    for home in RUN_HOMES:
        d = os.path.join(home, rid)
        if os.path.isdir(d):
            return d
    return None


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def original_column(task):
    t = T.load_task(task)
    ref = CR.REFERENCE.get(task)
    return {"key": "orig", "label": "원본 재현본", "kind": "original", "task": task,
            "html": T.abs_path(t["original"]), "flow": load_flow(None, task=task),
            "storyboard": ref if ref and os.path.exists(ref) else None,
            "came": {}, "plan": None, "summary": None, "error": None,
            "source": "%s · %s" % (t["original"], t["flow"])}


def run_column(rid, i):
    """실행 하나의 열. 걸을 수 없는 실행이면 error 에 이유."""
    col = {"key": "r%d" % i, "label": rid, "kind": "run", "id": rid, "error": None,
           "summary": None, "plan": None, "came": {}, "storyboard": None, "task": None}
    d = find_run(rid)
    if d is None:
        col["error"] = "실행 폴더가 없다 (%s 아래에서 찾았다)" % " · ".join(rel(h) for h in RUN_HOMES)
        return col
    col["dir"] = d
    try:
        s = load(os.path.join(d, "summary.json"))
    except (OSError, ValueError) as e:
        col["error"] = "summary.json 을 읽지 못했다: %s" % e
        return col
    col["summary"] = s
    col["task"] = s.get("task") or T.DEFAULT_TASK
    if not s.get("passed") or not s.get("final"):
        col["error"] = "통과한 빌드가 없는 실행이다 (stopped_reason: %s)" % s.get("stopped_reason")
        return col
    n = CR.final_attempt(s)
    col["attempt"] = n
    col["label"] = "%s (시도 %d)" % (os.path.basename(d), n)
    html = os.path.join(d, os.path.basename(s["final"].get("html") or "attempt_%d.html" % n))
    flow = os.path.join(d, os.path.basename(s["final"].get("flow") or "attempt_%d.flow.json" % n))
    if not (os.path.exists(html) and os.path.exists(flow)):
        col["error"] = "최종 빌드 파일이 없다 (%s · %s)" % (os.path.basename(html),
                                                       os.path.basename(flow))
        return col
    col["html"] = html
    col["source"] = "%s · %s" % (rel(html), os.path.basename(flow))
    try:
        col["flow"] = judged_flow(read_flow(flow), task=col["task"], stage=s.get("stage"))
    except (OSError, ValueError) as e:
        col["error"] = "흐름 명세를 읽지 못했다: %s" % e
        return col
    col["plan"] = CR.plan_of(d, n)
    col["came"] = {sc["name"]: list(sc.get("from") or [])
                   for sc in col["plan"].get("screens") or [] if isinstance(sc, dict)}
    sb = os.path.join(d, "storyboard", "storyboard.json")
    col["storyboard"] = sb if os.path.exists(sb) else None
    try:
        col["audit"] = load(os.path.join(d, "attempt_%d.audit.json" % n))
    except (OSError, ValueError):
        col["audit"] = None
    return col


def built_screen(col, screen):
    """원본 화면 하나에 맞는 이 열의 화면 이름 - 흐름에 같은 이름이 있으면 그것, 아니면 계획의
    from 이 그 화면 하나인 생성 화면 (likeness · 검사 M 과 같은 규칙). 없으면 None."""
    visits = []
    for st in col["flow"].get("steps") or []:
        v = st.get("screen") if isinstance(st, dict) else None
        if v and v not in visits:
            visits.append(v)
    if screen in visits:
        return screen
    for v in visits:
        if LK.origin(v, col["came"]) == screen:
            return v
    return None


def first_visit_state(flow, name):
    for st in W.states_of(flow):
        if st["kind"] == "visit" and st["visit"] == name:
            return st
    return None


# --------------------------------------------------------------------------- #
# 걷고 찍고 재기
# --------------------------------------------------------------------------- #
async def shoot_state(browser, url, flow, state, png):
    ctx, page = await W.new_page(browser, 1)
    try:
        await W.replay(page, flow, state, url)
        await page.wait_for_timeout(SETTLE_MS)
        cur = await page.evaluate("() => window.__screen ? window.__screen() : null")
        first = await page.evaluate(MEASURE)
        ex = await page.evaluate(W.EXPAND, W.MAX_PHONE_HEIGHT)
        # 늘린 것이 없고 창 안에 다 들면 창을 키우지 않는다 - 원본의 #phone 은 좁은 창에서
        # height: 100vh 라 창을 키우면 따라 커진다 (10/13 스크립트는 창을 높이 + 2 로 키워 846 이 됐다)
        fits = not ex.get("grown") and ex["y"] + ex["h"] <= VH
        for _ in range(0 if fits else 3):
            need = int(ex["y"] + ex["h"] + 1)
            await page.set_viewport_size({"width": max(W.VIEWPORT["width"],
                                                       int(ex["x"] + ex["w"] + 0.5)),
                                          "height": max(VH, need)})
            again = await page.evaluate(W.PHONE_RECT)
            if abs(again["y"] + again["h"] - (ex["y"] + ex["h"])) < 1:
                break
            ex.update(again)
        ex.update(await page.evaluate(W.PHONE_RECT))
        await page.wait_for_timeout(200)
        full = await page.evaluate(FULL)
        await page.screenshot(path=png, clip={"x": ex["x"], "y": ex["y"], "width": ex["w"],
                                              "height": ex["h"]})
        return dict(screen=cur, height=round(ex["h"]), clipped=ex.get("clipped") or 0,
                    file=os.path.basename(png), **first, **full)
    finally:
        await ctx.close()


async def walk_columns(cols, screens, out):
    """열마다 원본 화면 차례로 첫 방문 상태를 찍고 잰다. `{열 key: {원본 화면: 잰 것}}`."""
    from playwright.async_api import async_playwright
    res = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            for col in cols:
                res[col["key"]] = got = {}
                if col.get("error"):
                    continue
                url = "file:///" + col["html"].replace(os.sep, "/").lstrip("/")
                for screen in screens:
                    name = built_screen(col, screen)
                    state = first_visit_state(col["flow"], name) if name else None
                    if state is None:
                        got[screen] = {"error": "이 화면에 맞는 화면이 흐름에 없다"}
                        continue
                    png = os.path.join(out, "%s_%s.png" % (col["key"], screen))
                    try:
                        got[screen] = await shoot_state(browser, url, col["flow"], state, png)
                        got[screen]["built"] = name
                    except Exception as e:      # 걷지 못한 화면 - 그 칸에 이유를 적고 계속
                        got[screen] = {"error": "%s: %s" % (type(e).__name__,
                                                            " ".join(str(e).split())[:200])}
                    print("  %s %s %s" % (col["key"], screen,
                                          got[screen].get("error") or got[screen]["height"]),
                          flush=True)
        finally:
            await browser.close()
    return res


def walk(cols, screens, out):
    return asyncio.run(walk_columns(cols, screens, out))


# --------------------------------------------------------------------------- #
# 숫자
# --------------------------------------------------------------------------- #
def likeness_of(col, task, path):
    """compare_runs 의 원본 닮음 보고. 원본 열은 원본 대 원본 (격자 · 탭의 '원본에도' = 원본의 수)."""
    ref = CR.REFERENCE.get(task)
    if not ref or not os.path.exists(ref) or not col.get("storyboard"):
        return None
    ref_board = load(ref)
    if col["kind"] == "original":
        came = {sh["screen"]: [sh["screen"]] for sh in ref_board.get("sheets") or []
                if sh.get("screen")}
        return LK.run_report(ref_board, ref_board, came, path)
    return LK.run_report(ref_board, load(col["storyboard"]), col["came"], path)


def _num(v, fmt="%.2f"):
    return "-" if v is None else fmt % v


def _g(v):
    return "%g" % v


def screen_values(m):
    return [x for x in m.values() if isinstance(x, dict) and not x.get("error")]


def summary_cells(col, metrics, rep, task):
    """요약표의 한 열 - 칸마다 (글, 설명)."""
    m = metrics.get(col["key"]) or {}
    vals = screen_values(m)
    s = col.get("summary") or {}
    orig = col["kind"] == "original"
    t = T.load_task(task)
    cells = {}
    if orig:
        sha = T.original_sha256(task)
        cells["조건"] = "원본 HTML (기준) · %s · 원본 sha256 %s" % (t["original"], sha[:8])
    elif col.get("error") and not s:
        cells["조건"] = "읽지 못함 — %s" % col["error"]
    else:
        cells["조건"] = "%s · 커밋 %s · 모드 %s · %s" % (
            (s.get("principles") or {}).get("condition") or "none",
            ((s.get("git") or {}).get("commit") or "?")[:7], s.get("mode") or "full",
            "캡처" if (s.get("see") or {}).get("source") == "captures" else "렌더")
    likeness = CR.likeness_cells(rep)
    cells["원본 닮음 (요소 · 무리, 화면 평균 · 최저)"] = likeness[0] if rep else (
        "잴 수 없음 — 화면설계서 없음 (python -m senior_ui.storyboard <실행> --mock)")
    cells["격자 · 탭 (원본에도 · 새로 · 없어짐)"] = likeness[1] if rep else "잴 수 없음 — 화면설계서 없음"
    if vals:
        home = m.get("home") or {}
        cells["home 높이 · 화면 높이 합 (px)"] = "%s · %d" % (
            home.get("height", "-"), sum(v["height"] for v in vals))
        firsts = [v["first_viewport_pressables"] for v in vals]
        cells["첫 화면 (390×844) 안 누를 것 (화면 평균 · home)"] = "%.1f · %s" % (
            sum(firsts) / len(firsts), home.get("first_viewport_pressables", "-"))
        fonts = [v["min_font"]["px"] for v in vals if v.get("min_font")]
        targets = [v["min_target"]["h"] for v in vals if v.get("min_target")]
        contrast = [v["min_contrast"]["ratio"] for v in vals if v.get("min_contrast")]
        cells["가장 작은 글자 px · 가장 작은 누를 것 높이 px · 가장 낮은 글 대비"] = "%s · %s · %s" % (
            _g(min(fonts)) if fonts else "-", _g(min(targets)) if targets else "-",
            "%.2f" % min(contrast) if contrast else "-")
        missed = [k for k, v in m.items() if v.get("error")]
        if missed:
            cells["home 높이 · 화면 높이 합 (px)"] += " (못 잰 화면: %s)" % ", ".join(missed)
    else:
        why = col.get("error") or "잰 화면이 없다"
        for k in ("home 높이 · 화면 높이 합 (px)", "첫 화면 (390×844) 안 누를 것 (화면 평균 · home)",
                  "가장 작은 글자 px · 가장 작은 누를 것 높이 px · 가장 낮은 글 대비"):
            cells[k] = "잴 수 없음 — %s" % why
    if orig:
        cells["시도 수 · 금액"] = "해당 없음 (원본)"
        cells["검사 결과"] = "해당 없음 (원본 — 검사의 기준)"
    else:
        cost = (s.get("cost") or {}).get("total_usd")
        cells["시도 수 · 금액"] = "%d · %s" % (
            len(s.get("attempts") or []),
            ("$%.2f" % cost) if cost is not None else ("mock (요금 없음)" if s.get("mock")
                                                      else "금액 기록 없음")) if s else "-"
        cells["검사 결과"] = audit_cell(col)
    return cells


def audit_cell(col):
    a = col.get("audit")
    if not a:
        return "검사 기록 없음" + (" — %s" % col["error"] if col.get("error") else "")
    m = a.get("metrics") or {}
    shown = m.get("choice_groups_original") or {}
    sel = m.get("choice_values_selectable") or {}
    ep = m.get("error_paths") or {}
    ff = m.get("flow_fixed")
    bits = ["fatal %d" % len(a.get("fatal") or []) + (" ✓" if not a.get("fatal") else ""),
            "K %s/%s" % (m.get("entrances_kept"), m.get("entrances_original")),
            "L %s/%s" % (m.get("images_kept"), m.get("images_original")),
            "I %d/%d" % (sum(sel.get(k, 0) for k in shown), sum(shown.values())),
            "J %d/%d" % (sum(1 for e in ep.values() if isinstance(e, dict) and e.get("appeared")
                             and e.get("recovered")), len(ep))]
    if ff is not None:
        bits.append("M %s" % ("같다" if ff.get("same") else "다르다"))
    return " · ".join(bits)


SUMMARY_ROWS = ["조건", "원본 닮음 (요소 · 무리, 화면 평균 · 최저)", "격자 · 탭 (원본에도 · 새로 · 없어짐)",
                "home 높이 · 화면 높이 합 (px)", "첫 화면 (390×844) 안 누를 것 (화면 평균 · home)",
                "가장 작은 글자 px · 가장 작은 누를 것 높이 px · 가장 낮은 글 대비", "시도 수 · 금액",
                "검사 결과"]


# --------------------------------------------------------------------------- #
# 캡처 (원본 칸)
# --------------------------------------------------------------------------- #
def capture_files(task, screen):
    """원본 화면 하나의 첫 방문에 해당하는 캡처 - 이름표가 "원본 화면 <화면>" 그대로이거나 그
    뒤가 스크롤 조각뿐인 것. 없으면 그 화면의 첫 캡처 (예: password — 비밀번호 입력 전)."""
    path = os.path.join(CAPTURES, task, "captures.json")
    if not os.path.exists(path):
        return []
    imgs = load(path).get("images") or []
    head = "원본 화면 %s" % screen
    plain = [im["file"] for im in imgs
             if im.get("label") == head or (im.get("label") or "").startswith(head + " — 스크롤 ")]
    if plain:
        return plain
    return [im["file"] for im in imgs if (im.get("label") or "").startswith(head + " — ")][:1]


# --------------------------------------------------------------------------- #
# 페이지
# --------------------------------------------------------------------------- #
e = H.escape

CSS = """
:root{--bg:#f6f7f9;--fg:#1a1d21;--sub:#5b6370;--line:#d9dde3;--card:#fff;--hl:#fff6d6;--bad:#b42318}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#15171a;--fg:#e8eaed;--sub:#9aa3ae;--line:#33383f;--card:#1e2125;--hl:#3a3420;--bad:#ff8a80}}
:root[data-theme="dark"]{--bg:#15171a;--fg:#e8eaed;--sub:#9aa3ae;--line:#33383f;--card:#1e2125;--hl:#3a3420;--bad:#ff8a80}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,"Malgun Gothic","Apple SD Gothic Neo",sans-serif;padding:24px 16px 80px}
main{max-width:1600px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px} h2{font-size:20px;margin:40px 0 12px;padding-top:12px;border-top:2px solid var(--line)}
h3{font-size:16px;margin:20px 0 8px}
p.sub{color:var(--sub);margin:0 0 16px}
nav{position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:2;display:flex;gap:10px;flex-wrap:wrap;border-bottom:1px solid var(--line)}
nav a{color:var(--fg)}
.scroll{overflow-x:auto;max-width:100%}
table{border-collapse:collapse;background:var(--card);margin:8px 0;font-size:14px}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
thead th{background:var(--hl)}
small{color:var(--sub)}
.grid{display:grid;grid-template-columns:repeat(var(--cols),minmax(220px,1fr));gap:12px;align-items:start;overflow-x:auto}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px}
figcaption{font-size:13px;margin-bottom:6px}
figcaption span{display:block;color:var(--sub);font-size:12px;word-break:break-all}
figure img{width:100%;height:auto;display:block;border:1px solid var(--line)}
.caps{display:flex;gap:4px;margin-top:8px}
.caps img{width:72px;border:1px solid var(--line)}
.err{color:var(--bad)}
dl{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px}
dt{font-weight:600;margin-top:8px} dd{margin:2px 0 0 0}
"""


def _metric_rows(cols, metrics, likeness_by_col, screen):
    trs = []
    for col in cols:
        x = (metrics.get(col["key"]) or {}).get(screen) or {}
        if col.get("error"):
            trs.append('<tr><th>%s</th><td colspan="8" class="err">%s</td></tr>'
                       % (e(col["label"]), e(col["error"])))
            continue
        if x.get("error"):
            trs.append('<tr><th>%s</th><td colspan="8" class="err">%s</td></tr>'
                       % (e(col["label"]), e(x["error"])))
            continue
        rep = likeness_by_col.get(col["key"])
        row = next((r for r in (rep or {}).get("screens") or [] if r["screen"] == screen), None)
        order = _num(row["elements"]) if row else "-"
        mf, mt, mc = x.get("min_font") or {}, x.get("min_target") or {}, x.get("min_contrast") or {}
        trs.append("<tr><th>%s</th><td>%d</td><td>%d</td><td>%d</td><td>%s <small>%s</small></td>"
                   "<td>%s <small>%s</small></td><td>%s <small>%s</small></td><td>%d</td><td>%s</td>"
                   "</tr>" % (
                       e(col["label"]), x["height"], x["pressables"],
                       x["first_viewport_pressables"],
                       _g(mf["px"]) if mf else "-", e(mf.get("text") or ""),
                       _g(mt["h"]) if mt else "-", e(mt.get("text") or mt.get("action") or ""),
                       "%.2f" % mc["ratio"] if mc else "-", e(mc.get("text") or ""),
                       x["text_elems"], order))
    return ("<div class=\"scroll\"><table><thead><tr><th></th><th>화면 높이 px</th><th>누를 것</th>"
            "<th>첫 화면 안 누를 것</th><th>가장 작은 글자 px</th><th>가장 작은 누를 것 높이 px</th>"
            "<th>가장 낮은 글 대비</th><th>글 덩어리 수</th><th>요소 순서 같음</th></tr></thead>"
            "<tbody>%s</tbody></table></div>" % "".join(trs))


def _figure(col, x, task, screen, caps_copied):
    if col.get("error"):
        return ('<figure><figcaption><b>%s</b></figcaption><p class="err">%s</p></figure>'
                % (e(col["label"]), e(col["error"])))
    head = '<figcaption><b>%s</b><span>%s</span></figcaption>' % (
        e(col["label"]), e(col.get("source") or ""))
    if x.get("error"):
        body = '<p class="err">%s</p>' % e(x["error"])
    else:
        built = x.get("built")
        body = '<img src="%s" alt="%s %s" loading="lazy">' % (e(x["file"]), e(col["label"]), e(screen))
        if built and built != screen:
            head = head.replace("</span>", " · 화면 %s</span>" % e(built), 1)
    caps = ""
    if col["kind"] == "original" and caps_copied.get(screen):
        files = caps_copied[screen]
        caps = ('<div class="caps" title="더미앱 캡처">%s</div><small>더미앱 캡처 inputs/captures/%s/%s'
                '</small>' % ("".join('<img src="%s" alt="캡처 %s">' % (e(f), e(f)) for f in files),
                              e(task), e(" · ".join(f.split("cap_", 1)[1] for f in files))))
    return "<figure>%s%s%s</figure>" % (head, body, caps)


def applied_table(col):
    if col["kind"] == "original":
        return ""
    s = col.get("summary") or {}
    cond = (s.get("principles") or {}).get("condition")
    head = "<h3>%s</h3>" % e(col["label"])
    if col.get("error") and not col.get("plan"):
        return head + '<p class="err">%s</p>' % e(col["error"])
    if not cond:
        return head + "<p>원칙 없음</p>"
    rows = []
    for sc in (col.get("plan") or {}).get("screens") or []:
        items = sc.get("applied")
        if not items:
            rows.append("<tr><td>%s</td><td>(적지 않음)</td><td></td><td></td></tr>" % e(sc.get("name")))
            continue
        for a in items if isinstance(items, list) else [items]:
            a = a if isinstance(a, dict) else {"id": "?", "how": str(a)}
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                e(sc.get("name")), e(str(a.get("id"))), e(str(a.get("why") or "-")),
                e(str(a.get("how") or ""))))
    return (head + "<p>조건 <b>%s</b> · %s</p><div class=\"scroll\"><table><thead><tr><th>화면</th>"
            "<th>원칙</th><th>왜</th><th>어떻게</th></tr></thead><tbody>%s</tbody></table></div>"
            % (e(cond), e((s.get("principles") or {}).get("file") or ""), "".join(rows)))


def changes_table(col):
    if col["kind"] == "original":
        return ""
    head = "<h3>%s</h3>" % e(col["label"])
    plan = col.get("plan")
    if not plan:
        return head + '<p class="err">%s</p>' % e(col.get("error") or "계획이 없다")
    by = {}
    for c in plan.get("changes") or []:
        for sc in c.get("to_screens") or ["(화면 없음)"]:
            by.setdefault(sc, []).append(c)
    rows = []
    for sc in [x.get("name") for x in plan.get("screens") or []] + sorted(
            set(by) - set(x.get("name") for x in plan.get("screens") or [])):
        for c in by.get(sc) or []:
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                        % (e(sc), e(c.get("id")), e(" ".join(str(c.get("what") or "").split()))))
    return (head + "<p>시도 %s 의 계획 (attempt_N.plan.json) 의 changes</p><div class=\"scroll\"><table>"
            "<thead><tr><th>화면</th><th>변경</th><th>무엇을</th></tr></thead><tbody>%s</tbody>"
            "</table></div>" % (col.get("attempt"), "".join(rows)))


def provenance(cols, task):
    items = []
    for col in cols:
        if col["kind"] == "original":
            items.append("<dt>%s</dt><dd>%s · 원본 sha256 %s · 원본 화면설계서 %s</dd>" % (
                e(col["label"]), e(col["source"]), e(T.original_sha256(task)),
                e(rel(col["storyboard"])) if col.get("storyboard") else "없음"))
            continue
        s = col.get("summary") or {}
        if not s:
            items.append("<dt>%s</dt><dd class=\"err\">%s</dd>" % (e(col["label"]), e(col["error"])))
            continue
        pr = s.get("principles") or {}
        bits = ["폴더 %s" % rel(col["dir"]),
                "모델 %s" % s.get("model"), "커밋 %s%s" % ((s.get("git") or {}).get("commit"),
                                                          " (작업 트리 깨끗하지 않음)"
                                                          if (s.get("git") or {}).get("dirty") else ""),
                "모드 %s" % (s.get("mode") or "full"),
                "원칙 %s%s" % (pr.get("condition") or "none",
                               " (%s · sha256 %s)" % (pr.get("file"), pr.get("sha256"))
                               if pr else ""),
                "진단 그림 %s" % ((s.get("see") or {}).get("source") or "-"),
                "다듬기 %s" % ((s.get("refine") or {}).get("budget")),
                "원본 sha256 %s" % s.get("original_sha256"),
                "생성 템플릿 sha256 %s" % (s.get("repro") or {}).get("prompt_template_sha256"),
                "화면설계서 %s" % (rel(col["storyboard"]) if col.get("storyboard") else "없음")]
        if col.get("error"):
            bits.append("걷지 못함: %s" % col["error"])
        items.append("<dt>%s</dt><dd>%s</dd>" % (e(col["label"]), e(" · ".join(bits))))
    return "<dl>%s</dl>" % "".join(items)


def render(name, cols, screens, metrics, likeness_by_col, cells_by_col, caps_copied, task):
    n = len(cols)
    head = "".join("<th>%s</th>" % e(c["label"]) for c in cols)
    srows = "".join("<tr><th>%s</th>%s</tr>" % (e(k), "".join(
        "<td>%s</td>" % e(cells_by_col[c["key"]][k]) for c in cols)) for k in SUMMARY_ROWS)
    sections = []
    for screen in screens:
        figs = "".join(_figure(c, (metrics.get(c["key"]) or {}).get(screen) or {}, task, screen,
                               caps_copied) for c in cols)
        sections.append('<section id="s-%s"><h2>%s</h2><div class="grid" style="--cols:%d">%s</div>%s'
                        '</section>' % (e(screen), e(screen), n, figs,
                                        _metric_rows(cols, metrics, likeness_by_col, screen)))
    rules = "".join("<dt>%s</dt><dd>%s</dd>" % (e(k), e(v)) for k, v in RULES)
    return """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title><style>%(css)s</style></head>
<body><main>
<h1>%(title)s</h1>
<p class="sub">원본 대 실행 %(runs)d개 — 정답 경로 %(nscreens)d화면 · tools/compare_page.py · %(at)s. 그림과 숫자는 모델을 부르지 않고 이 폴더에서 새로 찍고 잰 것이다.</p>
<nav>%(nav)s · <a href="#principles">원칙 적용표</a> · <a href="#changes">바꾼 것</a> · <a href="#rules">재는 규칙</a></nav>
<h2 id="summary">요약</h2>
<div class="scroll"><table><thead><tr><th></th>%(head)s</tr></thead><tbody>%(srows)s</tbody></table></div>
%(sections)s
<h2 id="principles">원칙 적용표</h2>
<p class="sub">실행마다 마지막 시도의 계획 (attempt_N.plan.json) 의 화면별 applied — 원칙 id · 왜 (na) · 어떻게.</p>
%(applied)s
<h2 id="changes">바꾼 것</h2>
%(changes)s
<h2 id="rules">재는 규칙</h2>
<dl>%(rules)s</dl>
<h3>그림 출처</h3>
<p>원본 칸: 원본 HTML 을 과제의 원본 흐름대로 새로 찍은 것 (원본 재현본) 과, 그 아래 작게 연구자가 더미앱에서 찍은 캡처 (진단·계획 호출에 들어간 그림 — 그대로 복사). 실행 칸: 각 실행의 최종 빌드 (summary.json 의 final) 를 그 흐름 명세대로 새로 찍은 것. 화면설계서의 그림 (storyboard/shots) 은 색 · 강조를 지운 와이어 사본이고 shots/attempt_N/audit_*.png 는 첫 화면 (844px) 만 있어 쓰지 않았다.</p>
<h3>각 열의 조건 · sha</h3>
%(prov)s
</main></body></html>
""" % {"title": e("비교 — %s" % name), "css": CSS, "runs": n - 1, "nscreens": len(screens),
       "at": time.strftime("%Y-%m-%d %H:%M"),
       "nav": " · ".join('<a href="#s-%s">%s</a>' % (e(s), e(s)) for s in screens),
       "head": head, "srows": srows, "sections": "".join(sections),
       "applied": "".join(applied_table(c) for c in cols),
       "changes": "".join(changes_table(c) for c in cols), "rules": rules,
       "prov": provenance(cols, task)}


# --------------------------------------------------------------------------- #
def build(run_ids, name, out_root=OUT_DIR, walker=None):
    """페이지를 만든다. 돌려주는 것은 index.html 경로. `walker` 는 시험이 걷기를 바꿔 끼울 자리."""
    out = os.path.join(out_root, name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    runs = [run_column(rid, i + 1) for i, rid in enumerate(run_ids)]
    tasks = sorted(set(c["task"] for c in runs if c.get("task")))
    task = tasks[0] if tasks else T.DEFAULT_TASK
    if len(tasks) > 1:
        raise SystemExit("과제가 다른 실행을 한 페이지에 둘 수 없다: %s" % ", ".join(tasks))
    for c in runs:
        if c.get("task") and c["task"] != task:
            c["error"] = "과제가 다르다 (%s)" % c["task"]
    cols = [original_column(task)] + runs
    screens = FF.first_visits(FF.original_steps(task))
    metrics = (walker or walk)(cols, screens, out)
    likeness_by_col = {c["key"]: likeness_of(c, task, screens) for c in cols}
    cells = {c["key"]: summary_cells(c, metrics, likeness_by_col[c["key"]], task) for c in cols}
    caps = {}
    for screen in screens:
        files = []
        for f in capture_files(task, screen):
            dst = "cap_%s" % f
            shutil.copy2(os.path.join(CAPTURES, task, f), os.path.join(out, dst))
            files.append(dst)
        caps[screen] = files
    page = render(name, cols, screens, metrics, likeness_by_col, cells, caps, task)
    path = os.path.join(out, "index.html")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    with io.open(os.path.join(out, "metrics.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"columns": [{k: c.get(k) for k in ("key", "label", "kind", "id", "error")}
                               for c in cols],
                   "screens": screens, "metrics": metrics, "summary": cells}, f,
                  ensure_ascii=False, indent=1)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", nargs="+", required=True, help="실행 id (또는 실행 폴더)")
    ap.add_argument("--name", required=True, help="outputs/compare/<이름>/index.html")
    args = ap.parse_args(argv)
    path = build(args.runs, args.name)
    print(path)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
