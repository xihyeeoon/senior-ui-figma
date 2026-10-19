r"""탐색용 시안 — 조립 설계 전. (나) LLM 시안: 같은 입력을 모델에게 주고 묶음을 살린 HTML 로 짜게 한다 (유료).

    $py = "C:\Users\xihye\venvs\detect\Scripts\python.exe"
    & $py tools/screen_detect/sketch/llm_assemble.py --dry-run          # 어림 토큰 · 비용만 (키를 읽지 않는다)
    & $py tools/screen_detect/sketch/llm_assemble.py --max-usd 2.0      # 실제 호출 → results/detect/20261019-sketch/llm.html
    & $py tools/screen_detect/sketch/llm_assemble.py --units "home(01a+01b+01c)" --max-usd 1.73   # 고른 단위만

단위마다 모델 한 번 (gpt-6.1-sol, 의미 층과 같은 모델 · 같은 키 읽는 방식 - senior_ui.restructure.model). 보내는 것:
  그림   단위 그림 (이은 화면은 이은 그림) 을 폭 600 으로 줄이고 요소마다 mark 번호를 적은 것 한 장 (의미 층 semantic.py 의
         draw_marks 와 같은 크기 규칙 · 같은 그리기)
  글     LLM_PROMPT.md 의 `---` 아래 + 공통 입력 (common.py - 요소 · 구역 · 띠, 좌표는 CSS px). 화면은 캡처 파일
         이름으로만 부른다 - 이름표(label) · 단위 이름은 넣지 않는다 (10/19 "스크린샷만")
출력 검사 (코드): data-src 가 요소 id 와 하나씩 맞나 (빠짐 · 없는 id · 겹침), data-src 를 단 요소 밖의 보이는 글이
있나 (새로 만든 글), <script> · <style> 이 있나. 틀리면 문제를 적어 한 번 다시 묻고, 그래도 틀리면 그대로 저장하고
"검사 실패" 로 적는다 (짐작해 고치지 않는다). 화면 이동은 코드가 흐름 짝(kind tap)으로 data-go 를 붙인다.
허락한 돈: --max-usd (기본 2.0) - 다음 호출의 어림(생각 = 답)을 더해 넘을 것 같으면 부르지 않고 멈춘다.
쓰는 것 (results/detect/20261019-sketch/): llm.html, llm/<단위>.json (시도마다 토큰 · 비용 · 문제 · 상태),
llm/raw/<단위>.<n>.request.txt · .response.txt (요청 · 응답 원문 - 키 · 헤더 없음), llm/_sent/<단위>/marks.png,
llm/_llm.json (합계).
"""
import argparse
import hashlib
import html
import io
import json
import os
import re
import sys
import tempfile
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common as K  # noqa: E402
import rule_assemble as RA  # noqa: E402

sys.path.insert(0, K.TOOLS)
sys.path.insert(0, K.ROOT)
import semantic as S  # noqa: E402  (draw_marks · estimate - 같은 크기 규칙)

PROMPT_FILE = os.path.join(HERE, "LLM_PROMPT.md")
# 스크린샷만 (--inputs strict, 2026-10-19) - 의미 층 v2 의 칸 셋과 그것을 쓰는 지시 셋
PROMPT_V2 = os.path.join(HERE, "LLM_PROMPT_V2.md")
# v3 (10/19) - 줄 · 카드 끝 꺾쇠는 그림 자리가 아니라 글자로 (규칙 11)
PROMPTS = {"v2": PROMPT_V2, "v3": os.path.join(HERE, "LLM_PROMPT_V3.md"),
           "v4": os.path.join(HERE, "LLM_PROMPT_V4.md")}  # v4 (10/19 조립 마무리) - 뒤로가기 꺾쇠 · 무리는 한 부모 아래
ANSWER_TOKENS = 60     # 어림 - 요소 하나의 HTML (태그 · data-src · style)
ANSWER_BASE = 300
MAX_TOKENS = 25000
OUT = os.path.join(K.OUT, "llm")
PAGE_DIR = K.OUT


def rows_of(u):
    return [dict(e, mark=k + 1) for k, e in enumerate(u["elements"])]


def build(u, folder):
    from senior_ui.restructure.model import IMAGE_MARK
    os.makedirs(folder, exist_ok=True)
    rows = rows_of(u)
    marks = [{"box": e["box"], "kind": e["det"], "text": e["text"], "mark": e["mark"]} for e in rows]
    img = S.draw_marks(K.unit_image(u), marks, os.path.join(folder, "marks.png"))
    images = [{"path": img, "label": "화면 전체 - 요소마다 mark 번호"}]
    v2 = ("icon", "text_is_icon", "text_fixed") if u.get("strict") else ()
    el = lambda e: json.dumps(dict({"id": e["id"], "mark": e["mark"], "kind": e["kind"], "pressable": e["pressable"],
                                    "text": e["text"], "image_name": e["image_name"], "group": e["group"],
                                    "in_box": e["in_box"], "region": e["region"], "box": e["box_css"]},
                                   **{k: e.get(k) for k in v2}),
                              ensure_ascii=False, separators=(",", ":"))
    body = io.open(PROMPT_FILE, encoding="utf-8").read().split("\n---\n", 1)[1]
    # 캡처 파일 이름만 - 이름표(label) · 단위 이름(GROUPS 의 화면 이름)은 사람이 쓴 것이라 넣지 않는다 (10/19)
    prompt = (body.replace("{{CAPTURES}}", " + ".join(c + ".png" for c in u["captures"]))
              .replace("{{HEIGHT}}", str(u["size_css"][1]))
              .replace("{{ELEMENTS}}", "\n".join(el(e) for e in rows))
              .replace("{{REGIONS}}", "\n".join(json.dumps({"id": r["id"], "parent": r["parent"], "box": r["box_css"]},
                                                           separators=(",", ":")) for r in u["regions"]) or "(없음)")
              .replace("{{BANDS}}", "\n".join(json.dumps({"id": r["id"], "box": [0, K.css(r["box"][1]), K.WIDTH,
                                                                               K.css(r["box"][3])]},
                                                         separators=(",", ":")) for r in u["bands"]) or "(없음)")
              .replace("{{IMAGES}}", IMAGE_MARK))
    return prompt, images, rows


def estimate(prompt, images, rows, model):
    from senior_ui.restructure import model as M
    text_tokens, how = M.estimate_tokens(M.model_text(prompt, images), model)
    im = M.describe_images(images, model)
    answer = ANSWER_BASE + ANSWER_TOKENS * len(rows)
    price = M.price_for(model)
    cost = lambda inp, out: (inp * price["input"] + out * price["output"]) / 1e6 if price else None
    inp = text_tokens + im["estimated"]
    return {"images": im["count"], "image_tokens": im["estimated"], "text_tokens": text_tokens,
            "input_tokens": inp, "answer_tokens": answer, "cost_usd": cost(inp, answer),
            "cost_usd_with_reasoning": cost(inp, 2 * answer), "cost_usd_cap": cost(inp, MAX_TOKENS)}


class Scan(HTMLParser):
    """data-src · data-src 밖 보이는 글 · script/style 을 센다."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.src, self.stray, self.bad = [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.bad.append(tag)
        if "data-src" in a:
            self.src.append(a["data-src"])
        if tag not in self.VOID:
            self.stack.append((tag, "data-src" in a))

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break

    def handle_data(self, data):
        t = " ".join(data.split())
        if t and not any(s for _, s in self.stack) and not any(tg in ("script", "style") for tg, _ in self.stack):
            self.stray.append(t)


def extract(text):
    m = re.search(r"<section\b.*</section>", text or "", re.S | re.I)
    return m.group(0) if m else None


def check(section, ids):
    if not section:
        return ["답에 <section> … </section> 이 없다"], {}
    sc = Scan()
    sc.feed(section)
    want = set(ids)
    seen = {}
    for s in sc.src:
        seen[s] = seen.get(s, 0) + 1
    probs = []
    miss = [i for i in ids if i not in seen]
    unknown = [s for s in seen if s not in want]
    dup = [s for s, n in seen.items() if n > 1]
    if miss:
        probs.append("빠진 id (data-src 가 없다): %s" % ", ".join(miss))
    if unknown:
        probs.append("목록에 없는 data-src: %s" % ", ".join(unknown))
    if dup:
        probs.append("한 번보다 많이 쓴 data-src: %s" % ", ".join(dup))
    if sc.stray:
        probs.append("data-src 를 단 요소 밖의 글 (새로 만든 글): %s" % " | ".join(sc.stray[:20]))
    if sc.bad:
        probs.append("쓰지 말라고 한 태그: %s" % ", ".join(sorted(set(sc.bad))))
    return probs, {"missing": miss, "unknown": unknown, "dup": dup, "stray": sc.stray, "bad": sc.bad}


def reask(prompt, probs):
    return (prompt + "\n\n## 앞 답의 문제 (고쳐서 section 전체를 다시 답하라)\n" + "\n".join("- " + p for p in probs))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def add_go(section, taps):
    """흐름 짝의 누른 요소에 data-go (코드가 붙인다 - 모델은 쓰지 않는다)."""
    for t in taps:
        section = re.sub(r'data-src="%s"' % re.escape(t["tap"]),
                         'data-src="%s" data-go="%s"' % (t["tap"], t["to"]), section, count=1)
    return section


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-usd", type=float, default=2.0)
    ap.add_argument("--model", default=None)
    ap.add_argument("--units", help='고른 단위만 - 쉼표로 ("home(01a+01b+01c),02"). 없으면 13단위 전부')
    K.ST.add_arg(ap)
    ap.add_argument("--root", default=K.STRICT_ROOT, help="strict 결과 폴더 (detect/ · semantic/ · flow/, 시안도 여기에)")
    ap.add_argument("--prompt", choices=sorted(PROMPTS), default="v2", help="(strict) 프롬프트 판 - v3 는 꺾쇠 규칙 11, v4 는 뒤로가기 꺾쇠 · 무리 한 부모 (규칙 12)")
    ap.add_argument("--out", help="(strict) 시안 · 기록을 쓸 폴더 (기본: --root)")
    a = ap.parse_args(argv)
    strict = K.ST.from_args(a)
    K.set_strict_root(a.root)
    global PROMPT_FILE, OUT, PAGE_DIR
    if strict:
        PROMPT_FILE, PAGE_DIR = PROMPTS[a.prompt], a.out or K.STRICT_PATHS["out"]
        OUT = os.path.join(PAGE_DIR, "llm")
    from senior_ui import config
    from senior_ui.restructure import model as M
    model = a.model or config.DEFAULT_MODEL
    effort = config.DEFAULT_REASONING_EFFORT
    units = K.load_units(strict=strict)
    if a.units:
        pick = [x.strip() for x in a.units.split(",") if x.strip()]
        bad = [x for x in pick if x not in units]
        if bad:
            raise SystemExit("모르는 단위: %s (있는 단위: %s)" % (", ".join(bad), ", ".join(units)))
        units = {k: v for k, v in units.items() if k in pick}
    if a.dry_run:
        tmp = tempfile.mkdtemp(prefix="sketch_dry_")
        tot = {"input_tokens": 0, "answer_tokens": 0, "cost_usd": 0, "cost_usd_with_reasoning": 0, "cost_usd_cap": 0}
        print("모델 %s · 가격 %s (100만 토큰당 USD)" % (model, M.price_for(model)))
        for u in units.values():
            prompt, images, rows = build(u, os.path.join(tmp, u["unit"]))
            e = estimate(prompt, images, rows, model)
            print("%-28s 요소 %3d · 입력 %6d (그림 %5d) · 답 %5d · $%.4f (생각 = 답 $%.4f, 상한 $%.3f)" % (
                u["unit"], len(rows), e["input_tokens"], e["image_tokens"], e["answer_tokens"], e["cost_usd"],
                e["cost_usd_with_reasoning"], e["cost_usd_cap"]))
            for k in tot:
                tot[k] += e[k]
        print("합계 입력 %d · 답 %d · $%.4f (생각 = 답 $%.4f, 상한 $%.3f)" % (
            tot["input_tokens"], tot["answer_tokens"], tot["cost_usd"], tot["cost_usd_with_reasoning"],
            tot["cost_usd_cap"]))
        return
    M.load_env()                         # 실제 호출일 때만 - 환경 변수 또는 이 레포 뿌리의 .envs (의미 층과 같다)
    log = lambda m: print("  " + m, flush=True)
    sha = hashlib.sha256(io.open(PROMPT_FILE, "rb").read()).hexdigest()[:12]
    spent, results, sections, stopped = 0.0, {}, [], None
    for u in units.values():
        prompt, images, rows = build(u, os.path.join(OUT, "_sent", u["unit"]))
        ids = [e["id"] for e in rows]
        est = estimate(prompt, images, rows, model)
        res = {"unit": u["unit"], "model": model, "reasoning_effort": effort, "prompt_sha": sha, "estimate": est,
               "attempts": [], "status": None}
        ask, section, info = prompt, None, {}
        for n in (1, 2):
            need = est["cost_usd_with_reasoning"] or 0
            if spent + need > a.max_usd:
                stopped = "쓴 돈 $%.4f + %s 어림 $%.4f > 상한 $%.2f" % (spent, u["unit"], need, a.max_usd)
                break
            write(os.path.join(OUT, "raw", "%s.%d.request.txt" % (u["unit"], n)),
                  M.prompt_record(ask, images, model, base=OUT))
            reply = M.call_model(model, ask, MAX_TOKENS, log=log, reasoning_effort=effort, images=images,
                                 detail=config.IMAGE_DETAIL)
            usage = reply.get("usage") or {}
            cost = M.cost_usd(usage, M.price_for(model))
            spent += cost if cost is not None else need
            write(os.path.join(OUT, "raw", "%s.%d.response.txt" % (u["unit"], n)), reply.get("text") or "")
            section = extract(reply.get("text"))
            probs, info = check(section, ids)
            res["attempts"].append({"n": n, "usage": usage, "cost_usd": cost, "seconds": reply.get("seconds"),
                                    "finish_reason": reply.get("finish_reason"), "model": reply.get("model"),
                                    "problems": probs})
            print(u["unit"], "시도", n, "$%.4f" % (cost or 0), "문제 %d" % len(probs), "누적 $%.4f" % spent, flush=True)
            if not probs:
                res["status"] = "ok"
                break
            ask = reask(prompt, probs)
        if res["attempts"] and res["status"] is None:
            res["status"] = "검사 실패"
        res["check"] = info
        results[u["unit"]] = res
        write(os.path.join(OUT, "%s.json" % u["unit"]), json.dumps(res, ensure_ascii=False, indent=1))
        if section:
            # 스크린샷만(strict) 에서는 이름표(data-label)를 넣지 않는다
            label = "" if strict else ' data-label="%s"' % html.escape(u["label"] or "")
            sections.append('<section class="screen" id="%s" data-unit="%s"%s data-check="%s">'
                            '<!-- 모델 답 (%s) -->%s</section>' % (
                                u["section"], html.escape(u["unit"]), label, res["status"],
                                res["status"], add_go(section, u["taps"])))
        if stopped:
            break
    write(os.path.join(PAGE_DIR, "llm.html"),
          RA.page("LLM 시안", "llm_assemble.py", [u for u in units.values() if u["unit"] in results], sections))
    summ = {"model": model, "reasoning_effort": effort, "inputs": "strict" if strict else "legacy",
            "prompt_file": os.path.relpath(PROMPT_FILE, K.ROOT).replace(os.sep, "/"),
            "prompt_sha": sha, "max_usd": a.max_usd, "spent_usd": round(spent, 4), "stopped": stopped,
            "units": {k: {"status": r["status"], "attempts": len(r["attempts"]),
                          "prompt_tokens": sum((x["usage"] or {}).get("prompt") or 0 for x in r["attempts"]),
                          "completion_tokens": sum((x["usage"] or {}).get("completion") or 0 for x in r["attempts"]),
                          "reasoning_tokens": sum((x["usage"] or {}).get("reasoning") or 0 for x in r["attempts"]),
                          "cost_usd": sum(x["cost_usd"] or 0 for x in r["attempts"]),
                          "estimate_usd": r["estimate"]["cost_usd_with_reasoning"]} for k, r in results.items()}}
    write(os.path.join(OUT, "_llm.json"), json.dumps(summ, ensure_ascii=False, indent=1))
    print("쓴 돈 $%.4f" % spent, stopped or "")


if __name__ == "__main__":
    main()
