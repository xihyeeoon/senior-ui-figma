r"""조립 2단계 B - LLM 생김새 (만드는 줄, --inputs strict, 유료). 동작 · 이름 · 처리기 · 흐름 파일 · 추적표는 build.py 의
plan() 그대로 (규칙 판과 같다), 화면마다 마크업 · CSS 만 LLM 이 짠다.

    $py = "C:\Users\xihye\venvs\detect\Scripts\python.exe"
    & $py tools/screen_detect/assemble/llm_build.py --inputs strict --dry-run       # 13화면 어림만 (키를 읽지 않는다)
    & $py tools/screen_detect/assemble/llm_build.py --inputs strict --max-usd 2.5   # 실제 호출
        → results/detect/20261019-assembly2/llm/{original.html, flow.json, trace.json, limits.md, check.json}
          llm/<화면>.json (시도마다 토큰 · 비용 · 문제), llm/raw/<화면>.<n>.request.txt · .response.txt, llm/_llm.json,
          llm/_dry.json (어림), llm/_sent/<화면>/marks.png

보내는 것은 LLM 시안과 같다 (sketch/llm_assemble.build - strict3 의미 층 · 구역 나무 · 띠 · mark 그림, 화면은 캡처 파일
이름으로만, 프롬프트 LLM_PROMPT_V3.md 규칙 1~11). 이은 긴 화면 (s01 · s05 · s06) 도 한 번에 보낸다.
  검사    check_markup ①~⑤ (규칙 판과 같은 기대값) + <script> · <style> 없음. 동작을 붙인 뒤의 section 을 검사한다
  다시    걸리면 문제를 적어 한 번 더 묻는다. 또 걸리면 (또는 답이 잘리면) 그 화면은 규칙 마크업으로 대신하고 limits 에 적는다
  동작    LLM 이 지은 data-action (규칙 5) · data-v · data-go 는 모두 지우고, data-src 로 찾은 요소의 태그 이름 바로 뒤에 규칙
          부분의 data-action · data-v 를 넣는다 (data-v 가 data-src 보다 앞 - 첫 data-*). 글 · 태그 · 구조 · style 은 그대로
  감싸기  LLM 의 <section> 은 그대로 section.screen[data-screen][data-captures] > div.canvas 안에 둔다
돈: --max-usd (기본 2.5) - 다음 호출의 어림 (생각 = 답) 을 더해 넘을 것 같으면 부르지 않고 멈춘다. 13화면 어림 합이
--stop-over (기본 1.8) 를 넘으면 실제 호출 없이 멈춘다.
"""
import argparse
import hashlib
import html
import io
import json
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build as B  # noqa: E402  (sketch · tools 경로도 여기서 잡힌다)
import check_markup as CM  # noqa: E402
import common as K  # noqa: E402
import llm_assemble as LA  # noqa: E402

OUT = os.path.join(B.R, "20261019-assembly2", "llm")
PROMPT = "v3"
HINT = {"①": "data-src 는 목록의 id 마다 꼭 한 번 쓴다",
        "②": "data-src 를 단 요소 밖에 글 · button · 그림 자리를 두지 마라 (감싸는 그릇은 button 이 아닌 div 로)",
        "③": "그 요소 바로 안의 글은 목록의 text (text_fixed 가 있으면 text_fixed) 그대로 - 고치거나 늘리지 마라",
        "④": '그림 자리는 <div class="pic" role="img" aria-label="이름"> 꼴',
        "⑤": "꺾쇠 요소는 그림 자리 없이 글자 하나만"}
# 쪽 공통 css 의 button{all:unset} 이 브라우저 기본 버튼의 가운데 맞춤까지 지운다 - LLM 은 기본 버튼을 생각하고 짰으므로
# LLM 마크업 안의 버튼에만 가운데 맞춤을 돌려준다 (LLM 출력은 건드리지 않는다, 인라인 style 이 이것보다 앞선다)
CSS = '  .canvas[data-markup="llm"] button{text-align:center;}\n'
TAG = re.compile(r"<([a-zA-Z][\w-]*)(\s[^<>]*?)?(/?)>")
OURS = re.compile(r"""\s+data-(?:action|v|go)\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""")
SRC = re.compile(r"""\sdata-src\s*=\s*(?:"([^"]*)"|'([^']*)')""")


def attach(section, sid, actions):
    """LLM 의 data-action · data-v · data-go 를 지우고, data-src 로 찾은 요소에 규칙 부분의 동작을 태그 이름 바로 뒤에."""
    def one(m):
        tag, attrs, close = m.group(1), OURS.sub("", m.group(2) or ""), m.group(3)
        s = SRC.search(attrs)
        act = actions.get((sid, s.group(1) if s.group(1) is not None else s.group(2))) if s else None
        lead = ""
        if act:
            lead = ' data-action="%s"' % act[0] + (' data-v="%s"' % html.escape(act[1]) if act[1] is not None else "")
        return "<%s%s%s%s>" % (tag, lead, attrs, close)
    return TAG.sub(one, section)


def wrap(section, s):
    return ('<section class="screen" data-screen="%s" data-captures="%s"><div class="canvas" data-markup="llm">'
            '<!-- LLM 마크업 (LLM_PROMPT_V3) - 동작 (data-action · data-v) 은 규칙 부분이 붙임 -->%s</div></section>' % (
                s["screen"], "+".join(c[:-4] for c in s["captures"]), section))


def problems(section, wrapped, expected):
    """LLM 에게 돌려줄 문제 글 (검사 ①~⑤ + 쓰지 말라고 한 태그)."""
    if not section:
        return ["답에 <section> … </section> 이 없다 (잘렸거나 빠졌다)"], []
    r = CM.check("<body>%s</body>" % wrapped, expected)
    out = []
    for p in r["problems"]:
        extra = ""
        if p["rule"] == "⑤" and p["id"] in expected:
            extra = " (써야 할 글자: %s)" % expected[p["id"]]["chevron"]
        out.append("[%s] %s%s - %s%s" % (p["rule"], "data-src=%s: " % p["id"] if p["id"] else "", p["why"],
                                         HINT[p["rule"]], extra))
    _, info = LA.check(section, list(expected))
    if info.get("bad"):
        out.append("쓰지 말라고 한 태그: %s (꾸밈은 style 속성으로만)" % ", ".join(sorted(set(info["bad"]))))
    return out, r["problems"]


class Parents(HTMLParser):
    """data-action 요소마다 부모 (몇 번째 열린 태그) - 검사 I 는 같은 부모 아래 형제만 무리로 본다."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.n, self.of = [], 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.n += 1
        if "data-action" in a:
            self.of.append((a["data-action"], a.get("data-v"), self.stack[-1] if self.stack else None))
        if tag not in CM.VOID:
            self.stack.append(self.n)

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()


def split_groups(sections, S):
    """무리 data-action (a-sNN-gK) 마다 부모 수. 2 이상이면 검사 I 에서 무리가 갈린다."""
    rows = []
    for sec, s in zip(sections, S["screens"]):
        p = Parents()
        p.feed(sec)
        by = {}
        for act, v, par in p.of:
            if re.search(r"-g\d+$", act):
                by.setdefault(act, {}).setdefault(par, []).append(v)
        for act, ps in by.items():
            if len(ps) > 1:
                rows.append([s["screen"], act, len(ps), sum(len(x) for x in ps.values()),
                             " / ".join("%d" % len(x) for x in ps.values())])
    return rows


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main(argv=None):
    ap = argparse.ArgumentParser()
    K.ST.add_arg(ap)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-usd", type=float, default=2.5)
    ap.add_argument("--stop-over", type=float, default=1.8, help="13화면 어림 합 (생각 = 답) 이 이것을 넘으면 부르지 않는다")
    ap.add_argument("--model", default=None)
    ap.add_argument("--reuse", action="store_true", help="부르지 않고 llm/raw 의 앞 답 (llm/<화면>.json 의 시도) 으로 다시 짓는다")
    a = ap.parse_args(argv)
    if not K.ST.from_args(a):
        raise SystemExit("조립은 --inputs strict 로만 돈다 (스크린샷만)")
    from senior_ui import config
    from senior_ui.restructure import model as M
    LA.PROMPT_FILE = LA.PROMPTS[PROMPT]
    model = a.model or config.DEFAULT_MODEL
    effort = config.DEFAULT_REASONING_EFFORT
    S = B.plan(a.out)
    LOG = os.path.join(a.out, "llm")
    jobs = []
    for u, s in zip(S["units"], S["screens"]):
        prompt, images, rows = LA.build(u, os.path.join(LOG, "_sent", s["screen"]))
        est = LA.estimate(prompt, images, rows, model)
        exp = {i: v for (s_, i), v in S["expected"].items() if s_ == s["screen"]}
        jobs.append((s, u, prompt, images, rows, est, exp))
    dry = {"model": model, "price": M.price_for(model), "prompt_file": os.path.relpath(LA.PROMPT_FILE, K.ROOT).replace(os.sep, "/"),
           "screens": {s["screen"]: dict(est, elements=len(rows), captures=s["captures"]) for s, _, _, _, rows, est, _ in jobs}}
    for k in ("input_tokens", "answer_tokens", "cost_usd", "cost_usd_with_reasoning", "cost_usd_cap"):
        dry[k] = sum(x[k] for x in dry["screens"].values())
    write(os.path.join(LOG, "_dry.json"), json.dumps(dry, ensure_ascii=False, indent=1))
    print("모델 %s · 가격 %s (100만 토큰당 USD)" % (model, dry["price"]))
    for s, u, _, _, rows, e, _ in jobs:
        print("%s %-12s 요소 %3d · 입력 %6d (그림 %5d) · 답 %5d · $%.4f (생각 = 답 $%.4f, 상한 $%.3f)" % (
            s["screen"], "+".join(c[:-4] for c in s["captures"]), len(rows), e["input_tokens"], e["image_tokens"],
            e["answer_tokens"], e["cost_usd"], e["cost_usd_with_reasoning"], e["cost_usd_cap"]))
    print("합계 입력 %d · 답 %d · $%.4f (생각 = 답 $%.4f, 상한 $%.3f)" % (
        dry["input_tokens"], dry["answer_tokens"], dry["cost_usd"], dry["cost_usd_with_reasoning"], dry["cost_usd_cap"]))
    if dry["cost_usd_with_reasoning"] > a.stop_over and not a.reuse:
        print("어림 $%.4f > $%.2f - 부르지 않고 멈춘다" % (dry["cost_usd_with_reasoning"], a.stop_over))
        return
    if a.dry_run:
        return
    if a.reuse:
        prev = {s["screen"]: json.load(io.open(os.path.join(LOG, "%s.json" % s["screen"]), encoding="utf-8"))
                for s, *_ in jobs}

        def call(sid, n, ask, images):
            at = prev[sid]["attempts"][n - 1]
            return dict(at, text=io.open(os.path.join(LOG, "raw", "%s.%d.response.txt" % (sid, n)), encoding="utf-8").read())
    else:
        M.load_env()                     # 실제 호출일 때만 - 환경 변수 또는 이 레포 뿌리의 .envs (의미 층과 같다)

        def call(sid, n, ask, images):
            write(os.path.join(LOG, "raw", "%s.%d.request.txt" % (sid, n)), M.prompt_record(ask, images, model, base=LOG))
            reply = M.call_model(model, ask, LA.MAX_TOKENS, log=log, reasoning_effort=effort, images=images,
                                 detail=config.IMAGE_DETAIL)
            write(os.path.join(LOG, "raw", "%s.%d.response.txt" % (sid, n)), reply.get("text") or "")
            return reply
    log = lambda m: print("  " + m, flush=True)
    sha = hashlib.sha256(io.open(LA.PROMPT_FILE, "rb").read()).hexdigest()[:12]
    spent, results, sections, markup, stopped = 0.0, {}, [], {}, None
    for (s, u, prompt, images, rows, est, exp), rule_sec in zip(jobs, S["sections"]):
        sid = s["screen"]
        res = {"screen": sid, "captures": s["captures"], "model": model, "reasoning_effort": effort, "prompt_sha": sha,
               "estimate": est, "attempts": [], "status": None}
        ask, good = prompt, None
        for n in (1, 2):
            if stopped:
                break
            need = est["cost_usd_with_reasoning"] or 0
            if a.reuse and n > len(prev[sid]["attempts"]):
                break
            if spent + need > a.max_usd and not a.reuse:
                stopped = "쓴 돈 $%.4f + %s 어림 $%.4f > 상한 $%.2f" % (spent, sid, need, a.max_usd)
                break
            reply = call(sid, n, ask, images)
            usage = reply.get("usage") or {}
            cost = M.cost_usd(usage, M.price_for(model))
            spent += cost if cost is not None else need
            section = LA.extract(reply.get("text"))
            wrapped = wrap(attach(section, sid, S["actions"]), s) if section else None
            probs, raw = problems(section, wrapped, exp)
            res["attempts"].append({"n": n, "usage": usage, "cost_usd": cost, "seconds": reply.get("seconds"),
                                    "finish_reason": reply.get("finish_reason"), "model": reply.get("model"),
                                    "truncated": reply.get("finish_reason") == "length", "problems": probs})
            print(sid, "시도", n, "$%.4f" % (cost or 0), "문제 %d" % len(probs), reply.get("finish_reason"),
                  "누적 $%.4f" % spent, flush=True)
            if not probs:
                good = wrapped
                break
            ask = LA.reask(prompt, probs)
        if good:
            res["status"] = "ok" if len(res["attempts"]) == 1 else "ok (다시 물음)"
            sections.append(good)
            markup[sid] = "LLM 마크업 (LLM_PROMPT_V3, %s) + 규칙 동작" % res["status"]
        else:
            truncated = any(x["truncated"] for x in res["attempts"])
            res["status"] = ("호출 안 함 (%s)" % stopped if not res["attempts"] else
                             "규칙 마크업으로 대신 (%s)" % ("답 잘림" if truncated else "두 번 검사 실패"))
            sections.append(rule_sec)
            markup[sid] = "규칙 시안 마크업 - LLM %s" % res["status"]
        results[sid] = res
        write(os.path.join(LOG, "%s.json" % sid), json.dumps(res, ensure_ascii=False, indent=1))
    summ = {"model": model, "reasoning_effort": effort, "inputs": "strict", "prompt_file": dry["prompt_file"],
            "prompt_sha": sha, "max_usd": a.max_usd, "spent_usd": round(spent, 4), "stopped": stopped,
            "estimate_usd": round(dry["cost_usd_with_reasoning"], 4), "reused": a.reuse,
            "screens": {k: {"status": r["status"], "attempts": len(r["attempts"]),
                            "prompt_tokens": sum((x["usage"] or {}).get("prompt") or 0 for x in r["attempts"]),
                            "completion_tokens": sum((x["usage"] or {}).get("completion") or 0 for x in r["attempts"]),
                            "reasoning_tokens": sum((x["usage"] or {}).get("reasoning") or 0 for x in r["attempts"]),
                            "cost_usd": round(sum(x["cost_usd"] or 0 for x in r["attempts"]), 6),
                            "estimate_usd": round(r["estimate"]["cost_usd_with_reasoning"], 6),
                            "truncated": [x["n"] for x in r["attempts"] if x["truncated"]],
                            "problems_first": len(r["attempts"][0]["problems"]) if r["attempts"] else None}
                        for k, r in results.items()}}
    write(os.path.join(LOG, "_llm.json"), json.dumps(summ, ensure_ascii=False, indent=1))
    split = split_groups(sections, S)
    more = ["\n## LLM 마크업 (이 판)\n",
            "모델 %s · 프롬프트 %s (%s) · 쓴 돈 $%.4f / 상한 $%.2f%s\n" % (
                model, summ["prompt_file"], sha, spent, a.max_usd, " · 멈춤: " + stopped if stopped else ""),
            K.C.table(["화면", "캡처", "상태", "시도", "첫 답 문제", "잘림", "비용 (어림)"],
                      [[k, "+".join(c[:-4] for c in results[k]["captures"]), r["status"], r["attempts"],
                        "-" if r["problems_first"] is None else r["problems_first"], ",".join(map(str, r["truncated"])) or "-",
                        "$%.4f ($%.4f)" % (r["cost_usd"], r["estimate_usd"])] for k, r in summ["screens"].items()]),
            "\n## 무리가 여러 부모로 갈린 것 (LLM 이 줄 · 행으로 나눠 짬 - 검사 I 는 같은 부모 형제만 무리로 본다)\n",
            K.C.table(["화면", "data-action", "부모 수", "요소 수", "부모마다"], split or [["-"] * 5]),
            "\n- LLM 이 지은 data-action (규칙 5) 은 지우고 규칙 부분의 이름으로 바꿨다 - 처리기 · flow.json · trace.json 은 규칙 "
            "판과 같다.\n"]
    chk = B.write(S, a.out, sections, markup,
                  page_vars={"which": "LLM 판", "markup": "LLM 마크업 (LLM_PROMPT_V3) - 대신한 화면은 규칙 시안 마크업",
                             "maker": "llm_build.py", "css": CSS}, more_limits=more)
    print("쓴 돈 $%.4f %s · 검사 %s (%d) · 무리 갈림 %d" % (spent, stopped or "", chk["ok"], len(chk["problems"]), len(split)))


if __name__ == "__main__":
    main()
