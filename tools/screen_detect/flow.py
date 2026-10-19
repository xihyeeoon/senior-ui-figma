r"""흐름 층 - 캡처 순서 · 화면 글 · 요소 역할로 "어느 캡처에서 무엇을 누르면 어느 캡처로 가나" 를
LLM 이 추정한다 (스크린샷 입력 시험 D4). 연구자는 추정 목록을 검토만 한다.

    $py = "C:\Users\xihye\venvs\detect\Scripts\python.exe"
    & $py tools/screen_detect/flow.py --dry-run         # 어림 토큰 · 비용만 (키를 읽지 않는다)
    & $py tools/screen_detect/flow.py --mock            # 가짜 답으로 끝까지 (키를 읽지 않는다)
    & $py tools/screen_detect/flow.py --max-usd 0.60    # 실제 호출 한 번 (형식이 틀리면 한 번 더)
        [--captures-ref origin/feat/see-captures] [--elements results/detect/20261013-d25/final]
        [--roles results/detect/20261013-d3b] [--out results/detect/<날짜>-d4] [--model gpt-6.1-sol]

입력:
  캡처 순서와 이름표 - 캡처 대응표 captures.json 을 다른 브랜치에서 `git show <ref>:<경로>` 로 읽는다
  (이 브랜치에 가져오거나 고치지 않는다). 순서 = images 의 순서 = 파일 이름순 = 찍은 순서.
  단위마다 누를 수 있는 요소 - 요소(--elements, 스크롤 조각은 이은 화면 하나)와 의미 층의 역할
  (--roles 의 <단위>.semantic.json) 에서 pressable=true 이고 표시(flags)가 없는 것만. 글은 요소의 글,
  글이 없으면 그림 이름(image_name), 그것도 없으면 ocr_guess.
  글만 보낸다 - 그림은 보내지 않는다 (비용).

모델은 이웃한 캡처 짝마다 {from, to, tap, tap_text, kind, confidence, reason} 를 낸다. 짝이 빠지거나 더
있거나, tap 이 앞 캡처의 단위 요소가 아니거나, tap_text 가 그 요소의 글과 다르거나, 값이 틀리면 문제를 적어
한 번 다시 묻고, 그래도 틀리면 실패로 적는다 - 짐작해 메우지 않는다. --max-usd 를 주면 호출마다 "쓴 돈 +
이 호출의 최악(출력 상한을 다 쓴 값)" 이 상한을 넘을 것 같으면 부르지 않고 멈춘다.

쓰는 것 (--out): flow.proposed.json (짝마다 추정 · 시도마다 토큰 · 비용 · 문제), taps.proposed.json
(captures.json 의 taps 꼴 - captures.json 자체는 쓰지 않는다), raw/flow.<n>.request.txt · .request.json ·
.response.txt (요청 · 응답 원문, 키 · 헤더 없음). 정답과의 견주기는 compare_flow.py.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import compare as C  # noqa: E402
import strict as ST  # noqa: E402

PROMPT_FILE = os.path.join(HERE, "FLOW_PROMPT.md")
# 스크린샷만 (--inputs strict, 2026-10-19) - 과제 이름 줄 없음, 캡처 목록은 파일 이름 순 · 파일 이름 · 단위만
PROMPT_STRICT = os.path.join(HERE, "FLOW_PROMPT_STRICT.md")
TASK = "이체 — 받는 사람 계좌로 돈 보내기"
CAPTURES_REF = "origin/feat/see-captures"
CAPTURES_PATH = "inputs/captures/transfer/captures.json"
KINDS = ["tap", "scroll", "skipped", "error_path", "unknown"]
ANSWER_TOKENS = 80    # 어림 - 짝 하나의 답 토큰
MAX_TOKENS = 25000


def captures_from_files(folder):
    """스크린샷만 - 캡처 폴더의 PNG 를 파일 이름 순으로 (이름표 · taps 없음). captures.json 대신."""
    return {"task": None, "source": os.path.relpath(folder, ROOT).replace(os.sep, "/"),
            "images": [{"file": f, "taps": []} for f in sorted(os.listdir(folder)) if f.endswith(".png")]}


def roles_file(roles_dir, name, units):
    """의미 층 답 파일 - 같은 이름, 없으면 같은 캡처 묶음의 옛 이름 (home(01a+01b+01c) ↔ 01a+01b+01c)."""
    p = os.path.join(roles_dir, name + ".semantic.json")
    if os.path.exists(p):
        return p
    caps = "+".join(units[name].get("captures") or [name])
    for f in os.listdir(roles_dir):
        if f.endswith(".semantic.json") and f[:-len(".semantic.json")].endswith("(%s)" % caps):
            return os.path.join(roles_dir, f)
    return p


def read_captures(ref, path):
    """다른 브랜치의 captures.json 을 git show 로 읽는다 (작업 트리에 꺼내지 않는다)."""
    out = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (ref, path)], capture_output=True,
                         check=True)
    return json.loads(out.stdout.decode("utf-8"))


def unit_of(units):
    """캡처 파일(01a.png) → 단위 이름."""
    out = {}
    for name, d in units.items():
        for c in d.get("captures") or [os.path.splitext(os.path.basename(d["capture"]))[0]]:
            out[c + ".png"] = name
    return out


def pressable(units, roles_dir):
    """단위마다 누를 수 있는 요소 [{id, text, kind, group}] - 위에서 아래 순."""
    out = {}
    for name, d in units.items():
        r = json.load(io.open(roles_file(roles_dir, name, units), encoding="utf-8"))
        ans = {e["id"]: e for e in r["elements"] or []}
        rows = []
        for e in sorted(d["elements"], key=lambda e: (e["box"][1], e["box"][0])):
            g = ans.get(e["id"])
            if not g or not g["pressable"] or e.get("flags"):
                continue
            text = e.get("text") or g.get("image_name") or e.get("ocr_guess")
            rows.append({"id": e["id"], "text": " ".join((text or "").split()) or None,
                         "kind": g["kind"], "group": g.get("group")})
        out[name] = rows
    return out


def build(caps, umap, plist):
    images = caps["images"]
    pairs = [(a["file"], b["file"]) for a, b in zip(images, images[1:])]
    lines = [json.dumps({"file": im["file"], "unit": umap[im["file"]]} if ST.STRICT else
                        {"file": im["file"], "label": im["label"], "unit": umap[im["file"]]},
                        ensure_ascii=False) for im in images]
    used = list(dict.fromkeys(umap[im["file"]] for im in images))
    units_txt = "\n\n".join("[%s]\n%s" % (u, "\n".join(json.dumps(r, ensure_ascii=False,
                                                                   separators=(",", ":"))
                                                        for r in plist[u])) for u in used)
    body = io.open(PROMPT_STRICT if ST.STRICT else PROMPT_FILE, encoding="utf-8").read().split("\n---\n", 1)[1]
    if "{{TASK}}" in body:
        ST.human("flow.TASK")
        body = body.replace("{{TASK}}", TASK)
    prompt = (body.replace("{{CAPTURES}}","\n".join(lines))
              .replace("{{UNITS}}", units_txt)
              .replace("{{PAIRS}}", "\n".join("%s -> %s" % p for p in pairs)))
    return prompt, pairs


def parse(text):
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except ValueError:
        a, b = t.find("{"), t.rfind("}")
        try:
            return json.loads(t[a:b + 1]) if a >= 0 and b > a else None
        except ValueError:
            return None


def check(obj, pairs, umap, plist):
    """`(짝 목록, 문제 목록)`."""
    if not isinstance(obj, dict) or not isinstance(obj.get("pairs"), list):
        return None, ['답이 {"pairs": [...]} 모양의 JSON 이 아니다']
    probs, got = [], {}
    want = set(pairs)
    for p in obj["pairs"]:
        if not isinstance(p, dict):
            probs.append("짝이 객체가 아니다")
            continue
        k = (p.get("from"), p.get("to"))
        if k not in want:
            probs.append("답할 짝이 아니다: %s -> %s" % k)
            continue
        if k in got:
            probs.append("같은 짝에 답이 둘: %s -> %s" % k)
            continue
        where = "%s -> %s" % k
        els = {r["id"]: r for r in plist[umap[k[0]]]}
        tap, text, kind = p.get("tap"), p.get("tap_text"), p.get("kind")
        if kind not in KINDS:
            probs.append("%s: kind 가 정해진 값이 아니다 (%r)" % (where, kind))
        if tap is not None and tap not in els:
            probs.append("%s: tap %r 는 앞 캡처의 단위(%s) 요소 목록에 없다" % (where, tap, umap[k[0]]))
        elif tap is not None and (text or "").strip() != (els[tap]["text"] or "").strip():
            probs.append("%s: tap_text %r 가 요소 %s 의 글 %r 와 다르다" % (where, text, tap, els[tap]["text"]))
        if tap is None and text is not None:
            probs.append("%s: tap 이 null 인데 tap_text 가 있다" % where)
        if kind == "scroll" and tap is not None:
            probs.append("%s: scroll 인데 tap 이 있다" % where)
        if kind == "tap" and tap is None:
            probs.append("%s: kind 가 tap 인데 tap 이 null 이다" % where)
        c = p.get("confidence")
        if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0 <= c <= 1:
            probs.append("%s: confidence 가 0~1 의 수가 아니다" % where)
        got[k] = {"from": k[0], "to": k[1], "tap": tap, "tap_text": text, "kind": kind,
                  "confidence": c, "reason": p.get("reason")}
    missing = [p for p in pairs if p not in got]
    if missing:
        probs.append("답이 없는 짝 %d개: %s" % (len(missing), ", ".join("%s -> %s" % p for p in missing)))
    return [got[p] for p in pairs if p in got], probs


def mock_reply(pairs, umap, plist, caps, mode, n):
    """가짜 답 - 같은 단위면 scroll, 이름표가 오류 상태면 error_path, 아니면 앞 단위의 첫 button 을
    tap (코드가 끝까지 도는지 보려는 것, 품질 측정이 아니다)."""
    label = {im["file"]: im.get("label") or "" for im in caps["images"]}
    out = []
    for a, b in pairs:
        if umap[a] == umap[b] and "스크롤" in label[a] and "스크롤" in label[b]:
            out.append(dict(tap=None, tap_text=None, kind="scroll", confidence=0.9))
        elif "오류" in label[b]:
            out.append(dict(tap=None, tap_text=None, kind="error_path", confidence=0.6))
        else:
            first = next((r for r in plist[umap[a]] if r["kind"] in ("button", "link")), None)
            out.append(dict(tap=first and first["id"], tap_text=first and first["text"],
                            kind="tap" if first else "unknown", confidence=0.5))
        out[-1].update({"from": a, "to": b, "reason": "mock"})
    if mode == "bad-once" and n == 1 or mode == "bad-twice":
        out = out[1:]
    return {"text": json.dumps({"pairs": out}, ensure_ascii=False), "usage": {}, "model": "mock",
            "sent": {"model": "mock"}, "finish_reason": "stop", "seconds": 0.0}


def estimate(prompt, pairs, model, max_tokens):
    from senior_ui.restructure import model as M
    tokens, how = M.estimate_tokens(prompt, model)
    price = M.price_for(model)
    cost = (lambda o: (tokens * price["input"] + o * price["output"]) / 1e6) if price else (lambda o: None)
    answer = ANSWER_TOKENS * len(pairs)
    return {"input_tokens": tokens, "answer_tokens": answer, "how": how,
            "cost_usd": cost(answer), "cost_usd_with_reasoning": cost(2 * answer),
            "cost_usd_cap": cost(max_tokens)}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--captures-ref", default=CAPTURES_REF)
    ap.add_argument("--captures-path", default=CAPTURES_PATH)
    ap.add_argument("--elements", default=os.path.join(ROOT, "results", "detect", "20261013-d25", "final"))
    ap.add_argument("--roles", default=os.path.join(ROOT, "results", "detect", "20261013-d3b"))
    ap.add_argument("--out")
    ap.add_argument("--model")
    ap.add_argument("--reasoning-effort")
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--max-usd", type=float, help="이번 실행의 상한 (USD) - 호출마다 쓴 돈 + 그 호출의 "
                                                "최악(출력 상한을 다 씀)이 넘을 것 같으면 부르지 않는다")
    ap.add_argument("--mock", nargs="?", const="ok", choices=["ok", "bad-once", "bad-twice"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"),
                    help="strict 에서 캡처 목록을 읽는 폴더 (파일 이름 순)")
    ST.add_arg(ap)
    a = ap.parse_args(argv)
    ST.from_args(a)
    from senior_ui import config
    from senior_ui.restructure import model as M
    model = a.model or config.DEFAULT_MODEL
    effort = a.reasoning_effort or config.DEFAULT_REASONING_EFFORT
    caps = captures_from_files(a.captures) if ST.STRICT else read_captures(a.captures_ref, a.captures_path)
    units = C.load_units(a.elements)
    umap = unit_of(units)
    missing = [im["file"] for im in caps["images"] if im["file"] not in umap]
    if missing:
        raise SystemExit("요소 단위가 없는 캡처: %s" % ", ".join(missing))
    plist = pressable(units, a.roles)
    prompt, pairs = build(caps, umap, plist)
    est = estimate(prompt, pairs, model, a.max_tokens)
    pfile = PROMPT_STRICT if ST.STRICT else PROMPT_FILE
    sha = hashlib.sha256(io.open(pfile, "rb").read()).hexdigest()[:12]
    if a.dry_run:
        print("모델 %s · 가격 %s · 캡처 %d · 짝 %d · 단위 %d · 누를 수 있는 요소 %d · 그림 0 (글만)"
              % (model, config.MODEL_PRICES.get(model), len(caps["images"]), len(pairs),
                 len(set(umap.values())), sum(len(v) for v in plist.values())))
        print(json.dumps(est, ensure_ascii=False, indent=1))
        return
    today = datetime.date.today().strftime("%Y%m%d")
    out = a.out or os.path.join(ROOT, "results", "detect", today + "-d4" + ("-mock" if a.mock else ""))
    os.makedirs(out, exist_ok=True)
    if a.mock:
        call = lambda ask, n: mock_reply(pairs, umap, plist, caps, a.mock, n)
    else:
        M.load_env()                 # 실제 호출일 때만 - 환경 변수 또는 이 레포 뿌리의 .envs
        call = lambda ask, n: M.call_model(model, ask, a.max_tokens, log=lambda m: print("  " + m),
                                           reasoning_effort=effort)
    res = {"model": "mock:%s" % a.mock if a.mock else model, "reasoning_effort": None if a.mock else effort,
           "inputs": "strict" if ST.STRICT else "legacy",
           "prompt_file": os.path.relpath(pfile, ROOT).replace("\\", "/"), "prompt_sha": sha,
           "captures": None if ST.STRICT else "%s:%s" % (a.captures_ref, a.captures_path),
           "elements": os.path.relpath(a.elements, ROOT).replace("\\", "/"),
           "roles": os.path.relpath(a.roles, ROOT).replace("\\", "/"),
           "sent": "글만 (그림 0) - 캡처 목록 · 단위마다 누를 수 있는 요소 · 짝 목록",
           "pressable_elements": sum(len(v) for v in plist.values()),
           "estimate": est, "status": None, "attempts": [], "pairs": None}
    ask, spent = prompt, 0.0
    for n in (1, 2):
        worst = est["cost_usd_cap"] or 0
        if a.max_usd is not None and not a.mock and spent + worst > a.max_usd:
            res["status"] = "stopped"
            res["stopped"] = "쓴 돈 $%.4f + 이 호출의 최악 $%.4f > 상한 $%.2f" % (spent, worst, a.max_usd)
            break
        write(os.path.join(out, "raw", "flow.%d.request.txt" % n), ask)
        reply = call(ask, n)
        write(os.path.join(out, "raw", "flow.%d.request.json" % n),
              json.dumps({k: v for k, v in reply.items() if k in ("sent", "api", "max_tokens",
                                                                  "temperature", "seed")},
                         ensure_ascii=False, indent=1))
        write(os.path.join(out, "raw", "flow.%d.response.txt" % n), reply.get("text") or "")
        usage = reply.get("usage") or {}
        cost = None if a.mock else M.cost_usd(usage, M.price_for(model))
        spent += cost or 0
        got, probs = check(parse(reply.get("text")), pairs, umap, plist)
        res["attempts"].append({"n": n, "usage": usage, "cost_usd": cost, "seconds": reply.get("seconds"),
                                "finish_reason": reply.get("finish_reason"), "model": reply.get("model"),
                                "problems": probs})
        if not probs:
            res["status"], res["pairs"] = "ok", got
            break
        ask = (prompt + "\n\n앞 답에 문제가 있었다. 고친 답 전체를 JSON 하나로 다시 내라.\n"
               + "\n".join("- " + p for p in probs))
    else:
        res["status"] = "failed"
    res["cost_usd"] = spent
    write(os.path.join(out, "flow.proposed.json"), json.dumps(res, ensure_ascii=False, indent=1))
    if res["pairs"]:
        taps = {im["file"]: [] for im in caps["images"]}
        for p in res["pairs"]:
            if p["tap"] is not None:
                taps[p["from"]].append({"text": p["tap_text"], "to": p["to"], "kind": p["kind"],
                                        "confidence": p["confidence"]})
        prop = dict(caps, images=[dict(im, taps=taps[im["file"]]) for im in caps["images"]],
                    note="흐름 추정 (flow.py) 의 제안 - 연구자 검토용. captures.json 이 아니다")
        write(os.path.join(out, "taps.proposed.json"), json.dumps(prop, ensure_ascii=False, indent=1))
    print(res["status"], "시도 %d" % len(res["attempts"]), "$%.4f" % spent, "→", out)


if __name__ == "__main__":
    main()
