r"""의미 층 - 검출된 요소마다 누를 수 있나 · 무슨 종류인가 · 그림이면 이름이 무엇인가를 LLM 이 붙인다
(스크린샷 입력 시험 D3).

    $py = "C:\Users\xihye\venvs\detect\Scripts\python.exe"
    & $py tools/screen_detect/semantic.py --dry-run          # 그림 수 · 어림 토큰 · 어림 비용만
    & $py tools/screen_detect/semantic.py --mock             # 가짜 모델로 끝까지 (API 없음)
    & $py tools/screen_detect/semantic.py                    # 실제 호출 - 연구자가 돌린다
        [--in results/detect/20261013-d25/final] [--out results/detect/<날짜>-d3]
        [--model gpt-6.1-sol] [--reasoning-effort medium] [--max-tokens 25000] [단위 …]
        [--units "home(01a+01b+01c),02,08" --reuse results/detect/20261013-d3]

--units 로 고른 단위만 부른다. --reuse 를 주면 고르지 않은 단위는 앞 실행 폴더의 답 · 원문 · 보낸 그림 ·
truth.json 을 그대로 가져와 합친다 (결과 폴더 기본 <날짜>-d3b) - 비교는 13단위 전체로. 단위마다
prompt_sha(그때의 SEMANTIC_PROMPT.md)와 reused_from 이 남는다.

단위(--in 의 이은 화면 3 + 낱장 10 = 13)마다 모델을 한 번 부른다. 보내는 것:

  (가) 요소 JSON - 검출 박스 · img_candidate · OCR 글 줄(kind text) 모두. 칸은 detect.py 그대로
       (id · kind · box · text · ocr_guess · caption · name · in_box · flags) 에 그림 위 번호 mark 와
       곁의 글 near 를 더한다. 표시(flags)가 달린 요소도 넣는다 - 모델이 그대로 판단한다.
  (나) 화면 전체를 폭 MARK_WIDTH 로 줄이고 요소마다 mark 번호를 적은 그림 한 장.
  (다) 글 없는 박스 · img_candidate 의 잘라낸 그림 - 변마다 CROP_PAD 넓혀 CROP_SCALE 배 (긴 변
       CROP_MAX 까지). 글만 있는 요소는 보내지 않는다.
  과제 이름 한 줄(TASK)만 알려 준다 - 어느 버튼이 과제 경로인지는 알려 주지 않는다. 과제 버튼 대
  과제 밖 입구는 이 층이 정하지 않는다 (흐름 층에서 captures.json 의 taps 로).

프롬프트 문장은 SEMANTIC_PROMPT.md 에 있고 이 파일은 그것을 읽어 자리만 채운다.

답은 요소 id 마다 하나, 빠짐없이 {id, pressable, kind, group, image_name, image_shape, note}
(image_shape 는 kind 가 image 일 때 보이는 모양 - image_name 은 이름표 글로 지은 뜻 이름). 없는 id · 빠진 id ·
틀린 값이 있으면 한 번 다시 묻고(문제를 적어), 그래도 틀리면 그 단위를 실패로 적는다 - 짐작해 메우지
않는다. 규칙으로 이름이 붙은 로고(name)는 고정값으로 넘기고, 모델이 다른 image_name 을 내면 고정값으로
되돌리고 그 수를 적는다.

모델 호출 · 키 읽기 · 그림 토큰 어림 · 가격은 파이프라인의 것(senior_ui.restructure.model ·
senior_ui.config)을 그대로 쓴다. 키는 실제 호출 때만 읽는다 (환경 변수 OPENAI_API_KEY, 없으면 이
레포 뿌리의 .envs). --mock · --dry-run 은 키를 읽지 않는다.

쓰는 것 (--out):
  <단위>.semantic.json   답 (검증한 것) · 시도마다 토큰 · 비용 · 문제
  raw/<단위>.<n>.request.txt · .request.json · .response.txt   요청 · 응답 원문 (키 · 헤더 없음)
  _sent/<단위>/           보낸 그림 (mark 그림 · 잘라낸 그림)
  _semantic.json         단위마다 상태 · 토큰 · 비용과 합계. compare.py --semantic 이 summary 에 넣는다
"""
import argparse
import datetime
import io
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import compare as C  # noqa: E402  (단위 읽기 - 이은 화면이 조각을 대신한다)

PROMPT_FILE = os.path.join(HERE, "SEMANTIC_PROMPT.md")
TASK = "이체 — 받는 사람 계좌로 돈 보내기"
KINDS = ["button", "link", "back_close", "tab", "choice", "input", "keypad_key", "image",
         "text", "system"]
FIELDS = ["id", "mark", "kind", "box", "text", "ocr_guess", "caption", "name", "in_box",
          "near", "flags"]
MARK_WIDTH = 600      # 화면 전체 그림의 폭 (캡처 824 → 600)
CROP_PAD = 0.2        # 잘라낼 때 변마다 넓히는 비율
CROP_SCALE = 2        # 잘라낸 그림을 키우는 배수
CROP_MAX = 512        # 잘라낸 그림의 긴 변 상한 (큰 빈 박스가 그림 토큰을 다 먹지 않게)
BELOW_GAP = 1.0       # 바로 아래 글로 보는 틈 - 요소 높이(40px 이상)의 이만큼
ANSWER_TOKENS = 45    # 어림 - 요소 하나의 답 토큰 (id · 칸 · 짧은 note)
MAX_TOKENS = 25000    # 출력 상한 (생각 토큰 포함) - 파이프라인의 진단 · 계획 호출과 같은 값
FONT = r"C:\Windows\Fonts\malgun.ttf"


# --------------------------------------------------------------------------- #
# 보낼 것 만들기
# --------------------------------------------------------------------------- #
def unit_image(det, captures):
    """단위의 화면 그림 - 이은 화면이면 조각들을 stitch.compose 로 다시 잇는다."""
    from PIL import Image
    if "fragments" in det:
        import stitch
        imgs = [Image.open(os.path.join(captures, f["capture"] + ".png")).convert("RGB")
                for f in det["fragments"]]
        return stitch.compose(det["fragments"], imgs)
    return Image.open(os.path.join(ROOT, det["capture"])).convert("RGB")


def short(s, n=30):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def near_of(e, els):
    """곁의 글 - inside(이 요소 안에 든 OCR 글), row(같은 줄 양옆에서 가장 가까운 글 둘),
    below(바로 아래 글 - 가로 중심이 이 요소 폭 안이고 위 끝이 아래 끝에서 BELOW_GAP 안인 가장 가까운
    글, 탭바 아이콘 밑의 이름표 같은 것), parent(담은 박스의 글)."""
    x, y, w, h = e["box"]
    cy = y + h / 2
    texts = [t for t in els if t["kind"] == "text" and t is not e]
    inside = [t["text"] for t in texts
              if x <= t["box"][0] + t["box"][2] / 2 <= x + w and y <= t["box"][1] + t["box"][3] / 2 <= y + h]
    row = sorted((t for t in texts if abs(t["box"][1] + t["box"][3] / 2 - cy) < max(h, 20) / 2
                  and not (x <= t["box"][0] + t["box"][2] / 2 <= x + w)),
                 key=lambda t: abs(t["box"][0] + t["box"][2] / 2 - (x + w / 2)))[:2]
    gap = max(h, 40) * BELOW_GAP
    under = sorted((t for t in texts if x <= t["box"][0] + t["box"][2] / 2 <= x + w
                    and 0 <= t["box"][1] - (y + h) <= gap), key=lambda t: t["box"][1])
    parent = next((p for p in els if p["id"] == e.get("in_box")), None)
    out = {}
    if inside and e["kind"] != "text":
        out["inside"] = [short(t) for t in inside[:4]]
    if row:
        out["row"] = [short(t["text"]) for t in row]
    if under and not e.get("text"):      # 글 없는 박스 · 칸 안 그림만 - 이름표 찾기
        out["below"] = short(under[0]["text"])
    if parent and parent.get("text"):
        out["parent"] = short(parent["text"])
    return out or None


def element_rows(det):
    """요소 목록 - 위에서 아래, 왼쪽에서 오른쪽 순으로 mark 1.. 를 붙인다."""
    els = sorted(det["elements"], key=lambda e: (e["box"][1], e["box"][0]))
    rows = []
    for i, e in enumerate(els, 1):
        r = {k: e.get(k) for k in FIELDS if k not in ("mark", "near")}
        r["mark"] = i
        r["near"] = near_of(e, els)
        r["flags"] = e.get("flags") or None
        rows.append({k: r.get(k) for k in FIELDS})
    return rows


def needs_crop(r):
    return r["kind"] == "img_candidate" or (r["kind"] == "box" and not r["text"])


def draw_marks(image, rows, path):
    """화면 전체를 폭 MARK_WIDTH 로 줄이고 요소마다 테두리와 mark 번호를 적는다."""
    from PIL import ImageDraw, ImageFont
    k = MARK_WIDTH / image.size[0]
    im = image.resize((MARK_WIDTH, int(round(image.size[1] * k))))
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, 11)
    col = {"text": (0, 150, 60), "box": (30, 90, 230), "img_candidate": (240, 120, 0)}
    for r in rows:
        x, y, w, h = (v * k for v in r["box"])
        c = col.get(r["kind"], (220, 30, 30)) if (r["kind"] != "box" or r["text"]) else (220, 30, 30)
        d.rectangle([x, y, x + w, y + h], outline=c, width=1)
        label = str(r["mark"])
        tw = d.textlength(label, font=font)
        d.rectangle([x, y, x + tw + 3, y + 12], fill=(255, 255, 255))
        d.text((x + 1, y - 1), label, fill=c, font=font)
    im.save(path)
    return path


def crop(image, r, path):
    """변마다 CROP_PAD 넓혀 잘라 CROP_SCALE 배 (긴 변 CROP_MAX 까지)."""
    x, y, w, h = r["box"]
    px, py = w * CROP_PAD, h * CROP_PAD
    box = (max(0, int(x - px)), max(0, int(y - py)),
           min(image.size[0], int(x + w + px)), min(image.size[1], int(y + h + py)))
    c = image.crop(box)
    s = min(CROP_SCALE, CROP_MAX / max(c.size))
    c = c.resize((max(1, int(c.size[0] * s)), max(1, int(c.size[1] * s))))
    c.save(path)
    return path


def build(unit, det, captures, folder):
    """그 단위의 (프롬프트, 그림 목록, 요소 목록, 고정값)."""
    from senior_ui.restructure.model import IMAGE_MARK
    os.makedirs(folder, exist_ok=True)
    rows = element_rows(det)
    image = unit_image(det, captures)
    images = [{"path": draw_marks(image, rows, os.path.join(folder, "marks.png")),
               "label": "화면 전체 - 요소마다 mark 번호"}]
    for r in rows:
        if needs_crop(r):
            p = crop(image, r, os.path.join(folder, "crop_%03d.png" % r["mark"]))
            images.append({"path": p, "label": "잘라낸 그림 - mark %d · id %s" % (r["mark"], r["id"])})
    fixed = {r["id"]: r["name"] for r in rows if r.get("name")}
    text = io.open(PROMPT_FILE, encoding="utf-8").read()
    body = text.split("\n---\n", 1)[1]
    prompt = (body.replace("{{TASK}}", TASK).replace("{{UNIT}}", unit)
              .replace("{{FIXED}}", "\n".join("%s: %s" % kv for kv in fixed.items()) or "(없음)")
              .replace("{{ELEMENTS}}", "\n".join(json.dumps(r, ensure_ascii=False,
                                                            separators=(",", ":")) for r in rows))
              .replace("{{IMAGES}}", IMAGE_MARK))
    return prompt, images, rows, fixed


# --------------------------------------------------------------------------- #
# 답 읽기 · 검증
# --------------------------------------------------------------------------- #
def parse(text):
    """답 글에서 JSON 하나. 코드 울타리(```)가 있으면 벗긴다. 못 읽으면 None."""
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except ValueError:
        a, b = t.find("{"), t.rfind("}")
        if a >= 0 and b > a:
            try:
                return json.loads(t[a:b + 1])
            except ValueError:
                return None
    return None


IMAGE_NAME = re.compile(r".+ (아이콘|로고)$")


def check(obj, ids):
    """`(답 목록 {id: 답}, 문제 목록)`. 문제가 없어야 받는다."""
    probs = []
    if not isinstance(obj, dict) or not isinstance(obj.get("elements"), list):
        return None, ['답이 {"elements": [...]} 모양의 JSON 이 아니다']
    got = {}
    for a in obj["elements"]:
        if not isinstance(a, dict) or "id" not in a:
            probs.append("id 가 없는 답이 있다")
            continue
        i = a["id"]
        if i not in ids:
            probs.append("목록에 없는 id: %s" % i)
            continue
        if i in got:
            probs.append("같은 id 에 답이 둘: %s" % i)
            continue
        if not isinstance(a.get("pressable"), bool):
            probs.append("%s: pressable 이 true/false 가 아니다" % i)
        if a.get("kind") not in KINDS:
            probs.append("%s: kind 가 정해진 값이 아니다 (%r)" % (i, a.get("kind")))
        name = a.get("image_name")
        if a.get("kind") == "image":
            if not isinstance(name, str) or not IMAGE_NAME.match(name.strip()):
                probs.append("%s: kind 가 image 인데 image_name 이 '<무엇> 아이콘/로고' 가 아니다" % i)
        elif name is not None:
            probs.append("%s: kind 가 image 가 아닌데 image_name 이 있다" % i)
        shape = a.get("image_shape")
        if a.get("kind") == "image":
            if not isinstance(shape, str) or not shape.strip():
                probs.append("%s: kind 가 image 인데 image_shape 가 없다" % i)
        elif shape is not None:
            probs.append("%s: kind 가 image 가 아닌데 image_shape 가 있다" % i)
        if a.get("group") is not None and not isinstance(a.get("group"), str):
            probs.append("%s: group 이 글이나 null 이 아니다" % i)
        got[i] = {"id": i, "pressable": a.get("pressable"), "kind": a.get("kind"),
                  "group": a.get("group"), "image_name": name, "image_shape": shape,
                  "note": a.get("note")}
    missing = [i for i in ids if i not in got]
    if missing:
        probs.append("답이 없는 id %d개: %s" % (len(missing), ", ".join(missing[:20])
                                              + (" …" if len(missing) > 20 else "")))
    return got, probs


def reask(prompt, probs):
    return (prompt + "\n\n앞 답에 문제가 있었다. 고친 답 전체를 JSON 하나로 다시 내라.\n"
            + "\n".join("- " + p for p in probs))


# --------------------------------------------------------------------------- #
# 가짜 모델 - 정해진 규칙으로 만든 답 (코드가 끝까지 도는지 보려는 것, 품질 측정이 아니다)
# --------------------------------------------------------------------------- #
KEY = re.compile(r"^(\d{1,2}|[←⌫]|재배열)$")


def mock_answer(r):
    fl = r.get("flags") or []
    t = (r.get("text") or "").strip()
    if fl:
        return dict(pressable=False, kind="system", group=None, image_name=None,
                    note="mock: 표시 %s" % ",".join(fl))
    if r.get("name"):
        return dict(pressable=False, kind="image", group=None, image_name=r["name"],
                    image_shape="로고", note="mock: 규칙 이름")
    if r["kind"] == "img_candidate" or (r["kind"] == "box" and not t):
        near = r.get("near") or {}
        label = near.get("below") or near.get("parent") or (near.get("row") or [None])[0]
        shape = (r.get("caption") or "알 수 없는 모양").split(".")[0][:20]
        return dict(pressable=r["kind"] == "box", kind="image", group=None,
                    image_name="%s 아이콘" % label if label else "알 수 없는 아이콘",
                    image_shape=shape, note="mock: 이름표 %s" % (label or "없음"))
    if KEY.match(t):
        return dict(pressable=True, kind="keypad_key", group="keypad", image_name=None,
                    note="mock: 숫자")
    if r["kind"] == "box":
        return dict(pressable=True, kind="button", group=None, image_name=None, note="mock: 글 든 박스")
    if not r.get("in_box") and len(t) <= 8:
        return dict(pressable=True, kind="link", group=None, image_name=None, note="mock: 짧은 글 줄")
    return dict(pressable=False, kind="text", group=None, image_name=None, note="mock: 글")


def mock_reply(rows, mode, attempt):
    ans = [dict(dict(image_shape=None), id=r["id"], **mock_answer(r)) for r in rows]
    if mode == "bad-once" and attempt == 1 or mode == "bad-twice":
        ans = ans[1:] + [dict(ans[0], id="없는-id")]     # 하나 빠지고 없는 id 하나
    text = json.dumps({"elements": ans}, ensure_ascii=False)
    return {"text": text, "finish_reason": "stop", "seconds": 0.0,
            "usage": {"prompt": None, "completion": None, "reasoning": None},
            "model": "mock", "sent": {"model": "mock"}, "images": None}


# --------------------------------------------------------------------------- #
def estimate(prompt, images, rows, model, max_tokens):
    from senior_ui.restructure import model as M
    text_tokens, how = M.estimate_tokens(M.model_text(prompt, images), model)
    im = M.describe_images(images, model)
    answer = ANSWER_TOKENS * len(rows)
    price = M.price_for(model)
    cost = lambda inp, out: (inp * price["input"] + out * price["output"]) / 1e6 if price else None
    inp = text_tokens + im["estimated"]
    return {"images": im["count"], "image_tokens": im["estimated"], "text_tokens": text_tokens,
            "input_tokens": inp, "answer_tokens": answer,
            "cost_usd": cost(inp, answer),
            "cost_usd_with_reasoning": cost(inp, 2 * answer),
            "cost_usd_cap": cost(inp, max_tokens),
            "how": "글 %s · 그림 %s · 답 = 요소 %d x %d" % (how, im["method"], len(rows), ANSWER_TOKENS)}


def usd(v, k):
    """금액 글 - 가격표에 없는 모델이면 "-" (모른다)."""
    return "-" if v is None else "%.*f" % (k, v)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def run_unit(unit, det, a, captures, out, call):
    """한 단위 - 묻고, 검증하고, 한 번 다시 묻는다. 결과 dict."""
    from senior_ui.restructure import model as M
    prompt, images, rows, fixed = build(unit, det, captures, os.path.join(out, "_sent", unit))
    ids = [r["id"] for r in rows]
    import hashlib
    res = {"unit": unit, "model": "mock" if a.mock else a.model, "status": None, "attempts": [],
           "prompt_sha": hashlib.sha256(io.open(PROMPT_FILE, "rb").read()).hexdigest()[:12],
           "elements": None, "fixed": fixed, "fixed_overrides": [], "images": len(images),
           "estimate": estimate(prompt, images, rows, a.model, a.max_tokens)}
    ask = prompt
    for n in (1, 2):
        write(os.path.join(out, "raw", "%s.%d.request.txt" % (unit, n)),
              M.prompt_record(ask, images, a.model, base=out))
        need = res["estimate"]["cost_usd_with_reasoning"] or 0
        if a.max_usd is not None and not a.mock and a.spent + need > a.max_usd:
            # 이 호출을 하면 허락한 금액을 넘을 것 같다 - 부르지 않고 멈춘다
            res["status"] = "stopped"
            res["stopped"] = "쓴 돈 $%.4f + 이 호출 어림 $%.4f > 상한 $%.2f" % (a.spent, need, a.max_usd)
            return res
        reply = call(ask, images, rows, n)
        if not a.mock:
            a.spent += M.cost_usd(reply.get("usage"), M.price_for(a.model)) or need
        write(os.path.join(out, "raw", "%s.%d.request.json" % (unit, n)),
              json.dumps({k: v for k, v in reply.items() if k in ("sent", "api", "max_tokens",
                                                                  "temperature", "seed")},
                         ensure_ascii=False, indent=1))
        write(os.path.join(out, "raw", "%s.%d.response.txt" % (unit, n)), reply.get("text") or "")
        got, probs = check(parse(reply.get("text")), ids)
        usage = reply.get("usage") or {}
        res["attempts"].append({"n": n, "usage": usage, "seconds": reply.get("seconds"),
                                "finish_reason": reply.get("finish_reason"),
                                "model": reply.get("model"),
                                "cost_usd": M.cost_usd(usage, M.price_for(a.model)) if not a.mock else None,
                                "problems": probs})
        if not probs:
            for i, name in fixed.items():
                if got[i].get("image_name") != name or got[i].get("kind") != "image":
                    res["fixed_overrides"].append({"id": i, "answer": got[i].get("image_name"),
                                                   "kind": got[i].get("kind")})
                    got[i].update(kind="image", image_name=name)
            res["elements"] = [got[i] for i in ids]
            res["status"] = "ok"
            return res
        if n == 1:
            ask = reask(prompt, probs)
    res["status"] = "failed"
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="단위 이름 (없으면 전부, --units 와 같다)")
    ap.add_argument("--in", dest="inp", default=os.path.join(ROOT, "results", "detect",
                                                            "20261013-d25", "final"))
    ap.add_argument("--out")
    ap.add_argument("--model", default=None, help="기본: senior_ui.config.DEFAULT_MODEL")
    ap.add_argument("--reasoning-effort", default=None)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--mock", nargs="?", const="ok", choices=["ok", "bad-once", "bad-twice"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-usd", type=float, help="이번 실행에 쓸 상한 (USD). 다음 호출의 어림(생각 = 답)을 "
                                                "더해 넘을 것 같으면 부르지 않고 멈춘다")
    ap.add_argument("--units", help='고른 단위만 - 쉼표로 ("home(01a+01b+01c),02,08")')
    ap.add_argument("--reuse", help="고르지 않은 단위의 답을 가져올 앞 실행 폴더 (예 results/detect/"
                                    "20261013-d3). 비교는 13단위 전체로 한다")
    a = ap.parse_args(argv)
    a.spent = 0.0
    from senior_ui import config
    a.model = a.model or config.DEFAULT_MODEL
    effort = a.reasoning_effort or config.DEFAULT_REASONING_EFFORT
    units = C.load_units(a.inp)
    names = (a.names + [u.strip() for u in (a.units or "").split(",") if u.strip()]) or list(units)
    bad = [u for u in names if u not in units]
    if bad:
        raise SystemExit("모르는 단위: %s (있는 단위: %s)" % (", ".join(bad), ", ".join(units)))
    run = json.load(io.open(os.path.join(a.inp, "_run.json"), encoding="utf-8"))
    captures = os.path.join(ROOT, run["captures"])
    today = datetime.date.today().strftime("%Y%m%d")

    if a.dry_run:
        tmp = tempfile.mkdtemp(prefix="semantic_dry_")
        try:
            rows_out, tot = [], {}
            for u in names:
                prompt, images, rows, _ = build(u, units[u], captures, os.path.join(tmp, u))
                e = estimate(prompt, images, rows, a.model, a.max_tokens)
                rows_out.append([u, len(rows), e["images"], e["image_tokens"], e["text_tokens"],
                                 e["input_tokens"], e["answer_tokens"], usd(e["cost_usd"], 4),
                                 usd(e["cost_usd_with_reasoning"], 4), usd(e["cost_usd_cap"], 3)])
                for k in ("images", "image_tokens", "text_tokens", "input_tokens", "answer_tokens",
                          "cost_usd", "cost_usd_with_reasoning", "cost_usd_cap"):
                    tot[k] = None if e[k] is None or tot.get(k, 0) is None else tot.get(k, 0) + e[k]
                tot["elements"] = tot.get("elements", 0) + len(rows)
            rows_out.append(["합계", tot["elements"], tot["images"], tot["image_tokens"],
                             tot["text_tokens"], tot["input_tokens"], tot["answer_tokens"],
                             usd(tot["cost_usd"], 4), usd(tot["cost_usd_with_reasoning"], 4),
                             usd(tot["cost_usd_cap"], 3)])
            print("모델 %s · 그림 detail %s · 가격 %s (100만 토큰당 USD) · 단위 %d개"
                  % (a.model, config.IMAGE_DETAIL, config.MODEL_PRICES.get(a.model), len(names)))
            print(C.table(["단위", "요소", "그림", "그림 토큰", "글 토큰", "입력 토큰", "답 토큰 어림",
                           "비용 (답만)", "비용 (생각 = 답)", "비용 상한 (출력 %d)" % a.max_tokens],
                          rows_out))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return

    tag = "-d3b" if a.reuse else "-d3"
    out = a.out or os.path.join(ROOT, "results", "detect", today + tag + ("-mock" if a.mock else ""))
    os.makedirs(out, exist_ok=True)
    reused = []
    if a.reuse:
        # 고르지 않은 단위 - 앞 실행의 답 · 원문 · 보낸 그림을 그대로 가져온다 (다시 부르지 않는다)
        for u in units:
            if u in names:
                continue
            src = os.path.join(a.reuse, u + ".semantic.json")
            if not os.path.exists(src):
                raise SystemExit("앞 실행에 %s 의 답이 없다: %s" % (u, src))
            r = json.load(io.open(src, encoding="utf-8"))
            r["reused_from"] = os.path.relpath(a.reuse, ROOT).replace("\\", "/")
            write(os.path.join(out, u + ".semantic.json"), json.dumps(r, ensure_ascii=False, indent=1))
            for f in os.listdir(os.path.join(a.reuse, "raw")) if os.path.isdir(os.path.join(a.reuse, "raw")) else []:
                if f.startswith(u + "."):
                    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
                    shutil.copy(os.path.join(a.reuse, "raw", f), os.path.join(out, "raw", f))
            sent = os.path.join(a.reuse, "_sent", u)
            if os.path.isdir(sent):
                shutil.copytree(sent, os.path.join(out, "_sent", u), dirs_exist_ok=True)
            reused.append(r)
        if os.path.exists(os.path.join(a.reuse, "truth.json")):
            shutil.copy(os.path.join(a.reuse, "truth.json"), os.path.join(out, "truth.json"))
    if a.mock:
        def call(prompt, images, rows, n):
            return mock_reply(rows, a.mock, n)
    else:
        from senior_ui.restructure import model as M
        M.load_env()                     # 실제 호출일 때만 - 환경 변수 또는 이 레포 뿌리의 .envs
        log = lambda m: print("  " + m, flush=True)

        def call(prompt, images, rows, n):
            return M.call_model(a.model, prompt, a.max_tokens, log=log, reasoning_effort=effort,
                                images=images, detail=config.IMAGE_DETAIL)
    done = []
    for u in names:
        r = run_unit(u, units[u], a, captures, out, call)
        write(os.path.join(out, u + ".semantic.json"), json.dumps(r, ensure_ascii=False, indent=1))
        done.append(r)
        print(u, r["status"], "시도 %d" % len(r["attempts"]), r.get("stopped") or "", flush=True)
        if r["status"] == "stopped":
            break
    summ = {"model": "mock:%s" % a.mock if a.mock else a.model, "reasoning_effort": None if a.mock else effort,
            "units_run": names, "reuse": (os.path.relpath(a.reuse, ROOT).replace("\\", "/")
                                          if a.reuse else None),
            "in": os.path.relpath(a.inp, ROOT).replace("\\", "/"), "task": TASK,
            "prompt_file": os.path.relpath(PROMPT_FILE, ROOT).replace("\\", "/"),
            "units": {}, "totals": {}}
    for r in done + reused:
        u = {"status": r["status"], "attempts": len(r["attempts"]), "images": r["images"],
             "reused_from": r.get("reused_from"), "prompt_sha": r.get("prompt_sha"),
             "elements": len(r["elements"] or []), "fixed_overrides": len(r["fixed_overrides"]),
             "prompt_tokens": sum((x["usage"] or {}).get("prompt") or 0 for x in r["attempts"]),
             "completion_tokens": sum((x["usage"] or {}).get("completion") or 0 for x in r["attempts"]),
             "reasoning_tokens": sum((x["usage"] or {}).get("reasoning") or 0 for x in r["attempts"]),
             "cost_usd": sum(x["cost_usd"] or 0 for x in r["attempts"]),
             "estimate": r["estimate"]}
        summ["units"][r["unit"]] = u
    for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "cost_usd", "images"):
        summ["totals"][k] = sum(u[k] for u in summ["units"].values())
    summ["totals"]["failed"] = [k for k, u in summ["units"].items() if u["status"] != "ok"]
    write(os.path.join(out, "_semantic.json"), json.dumps(summ, ensure_ascii=False, indent=1))
    print("→", out)


if __name__ == "__main__":
    main()
