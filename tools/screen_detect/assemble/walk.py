r"""조립 1 · 2단계 - 걷기 시험 (유료 호출 없음). 헤드리스 chromium (Playwright 1.62, venvs\detect 에 이미 있음).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/assemble/walk.py
        [--dir results/detect/20261019-assembly2/rule] → <dir>/walk.json, walk.md

original.html 을 열고 (창 390x844, truth.py 와 같다)
  1. steps   flow.json 의 steps 대로 s01 부터 누르고 화면이 맞는지
  2. 닿기    s01 에서 시작해 실제로 눌러서 닿는 화면 (넓이 우선) - 화면에 닿으면 그 화면에서 나가는 이동 (transitions) 을
             하나씩 눌러 본다 (누르기 전에 그 화면으로 되돌린다)
  3. 이동마다 그 화면을 띄우고 (show) 그 요소를 눌러 다음 화면이 되나 - 눌렀는데 안 바뀐 것을 센다 (s01 에서 닿지 않는
             화면의 이동도 이렇게 시험한다)
  4. 오류 경로 expect_screen 에서 recover 를 눌러 back_to 로 가나
"""
import argparse
import asyncio
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


async def run(folder):
    from playwright.async_api import async_playwright
    flow = json.load(io.open(os.path.join(folder, "flow.json"), encoding="utf-8"))
    url = "file:///" + os.path.join(folder, "original.html").replace("\\", "/")
    out = {"steps": [], "edges": [], "errors": []}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844})
        await page.goto(url)
        screen = lambda: page.evaluate("() => window.__screen()")

        async def press(sel):
            loc = page.locator(".screen.on " + sel).first
            if not await loc.count():
                return "요소 없음"
            try:
                await loc.click(timeout=3000)
            except Exception as e:                       # 가려짐 등 - 힘으로 한 번 더
                try:
                    await loc.click(timeout=3000, force=True)
                except Exception:
                    return "누르지 못함: %s" % str(e).split("\n")[0][:80]
            await asyncio.sleep(0.05)
            return None
        # 1. steps
        start = await screen()
        out["start"] = start
        for st in flow["steps"][1:]:
            err = await press(st["click"])
            now = await screen()
            out["steps"].append({"want": st["screen"], "got": now, "error": err, "ok": now == st["screen"],
                                 "via": st.get("via")})
            if now != st["screen"]:
                break
        # 3. 이동마다
        for m in flow["transitions"]:
            await page.evaluate("(s) => show(s)", m["from"])
            err = await press(m["click"])
            now = await screen()
            out["edges"].append({"from": m["from"], "to": m["to"], "click": m["click"], "got": now, "error": err,
                                 "ok": now == m["to"], "pair": m["pair"], "via": m.get("via")})
            if m.get("keys"):                            # keypad-advance - 무리의 키마다 눌러 본다 (어느 키든 넘어가야)
                good = []
                for k in m["keys"]:
                    await page.evaluate("(s) => show(s)", m["from"])
                    await press("[data-src='%s']" % k)
                    good.append(await screen() == m["to"])
                out["edges"][-1]["keys"] = "%d/%d" % (sum(good), len(good))
                stay = []                                # 숫자 아닌 키 (지우기 · 재배열) 는 넘어가지 않아야
                for k in m.get("other_keys") or []:
                    await page.evaluate("(s) => show(s)", m["from"])
                    await press("[data-src='%s']" % k)
                    stay.append(await screen() == m["from"])
                out["edges"][-1]["other_keys"] = "%d/%d" % (sum(stay), len(stay))
        # 2. s01 에서 눌러서 닿는 화면 (된 이동만 따라)
        ok = [e for e in out["edges"] if e["ok"]]
        reach, todo = {start}, [start]
        while todo:
            s = todo.pop(0)
            for e in ok:
                if e["from"] == s and e["to"] not in reach:
                    reach.add(e["to"])
                    todo.append(e["to"])
        out["reached"] = sorted(reach)
        out["screens"] = [s["screen"] for s in flow["screens"]]
        out["unreached"] = [s for s in out["screens"] if s not in reach]
        # 4. 오류 경로
        for ep in flow["error_paths"]:
            await page.evaluate("(s) => show(s)", ep["expect_screen"])
            res = {"id": ep["id"], "expect_screen": ep["expect_screen"], "back_to": ep.get("back_to")}
            if ep.get("recover"):
                res["error"] = await press(ep["recover"][0]["click"])
                res["got"] = await screen()
                res["ok"] = res["got"] == ep.get("back_to")
            out["errors"].append(res)
        await browser.close()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "detect", "20261019-assembly2", "rule"))
    a = ap.parse_args(argv)
    out = asyncio.run(run(a.dir))
    with io.open(os.path.join(a.dir, "walk.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = ["# 걷기 시험 (헤드리스 chromium, 창 390x844)\n",
          "- 시작 화면: %s" % out["start"],
          "- steps: %s" % (" → ".join([out["start"]] + ["(%s) %s" % (s.get("via") or "-", s["got"]) for s in out["steps"]])
                           + ("" if all(s["ok"] for s in out["steps"]) else " - 여기서 끊김 (바라던 %s)" % out["steps"][-1]["want"])
                           if out["steps"] else "%s 하나뿐 (s01 에서 나가는 이동이 없다)" % out["start"]),
          "- s01 에서 눌러서 닿는 화면: %s" % ", ".join(out["reached"]),
          "- 닿지 않는 화면: %s" % (", ".join(out["unreached"]) or "없음"),
          "\n## 이동마다 (그 화면을 띄우고 눌러 봄)\n",
          "| 이동 | via | 누른 것 | 결과 | 짝 |\n|---|---|---|---|---|"]
    md += ["| %s → %s | %s | `%s` | %s | %s |" % (e["from"], e["to"], e.get("via") or "-", e["click"],
                                           "됨" if e["ok"] else "안 바뀜 (%s%s)" % (e["got"], ", " + e["error"] if e["error"] else ""),
                                           e["pair"]) for e in out["edges"]]
    md += ["\n- keypad-advance 숫자 키마다 눌러 넘어간 수: %s" % (", ".join(
        "%s → %s %s" % (e["from"], e["to"], e["keys"]) for e in out["edges"] if e.get("keys")) or "없음"),
           "- keypad-advance 숫자 아닌 키를 눌러 그 화면에 머문 수: %s" % (", ".join(
               "%s %s" % (e["from"], e["other_keys"]) for e in out["edges"] if e.get("other_keys")) or "없음")]
    md += ["\n## 오류 경로\n"] + ["- %s: %s 에서 recover → %s (%s)" % (
        e["id"], e["expect_screen"], e.get("got"), "됨" if e.get("ok") else "안 됨") for e in out["errors"]]
    with io.open(os.path.join(a.dir, "walk.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
