r""""스크린샷만" 입력 (--inputs strict, 2026-10-19 연구자 결정).

갈래 B 의 만드는 줄 (검출 → 이어 붙이기 → 의미 → 흐름 → 구역 → 시안 · 조립) 의 입력은 과제 순서대로 찍은
스크린샷(파일 이름 순)뿐이다. 사람이 만든 것은 채점 쪽에서만 쓴다 (truth.json · truth_regions.json · 옛 원본 HTML ·
captures.json 의 label 로 짝짓기 · 견주기 페이지). 옛 판(옵션 없음)은 그대로 다시 돌릴 수 있다.

이 모듈이 하는 일
  enable()      strict 를 켠다. 그 프로세스에서 사람 파일을 열거나(open) git show 로 읽으면(subprocess) 오류가
                나게 감사 훅(sys.addaudithook)을 건다 - captures.json · truth.json · truth_regions.json · flows/ ·
                tasks/ · 옛 원본 HTML(original_*.html). 채점 스크립트(truth · compare · compare_flow · compare_page)는
                strict 를 켜지 않으므로 그대로 읽는다
  human(what)   사람이 정한 상수(stitch.GROUPS · semantic/flow 의 TASK · detect.LOGO_HEAD)를 쓰는 자리에서 부른다 -
                strict 이면 오류
  auto_groups() 이어 붙이기 묶음을 그림만 보고 가린다 (stitch.GROUPS 대신)
  prepare       D2.5 final 을 strict 폴더로 옮긴다 - 검출은 다시 돌리지 않고, LOGO_HEAD 규칙이 붙인 로고 이름
                (name · label)만 지운다

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/strict.py prepare
        [--from results/detect/20261013-d25/final] [--out results/detect/20261019-strict/detect]

이어 붙이기 자동 판정 (auto_groups) - 파일 이름 순으로 이웃한 캡처 A · B 마다 stitch.py 의 세로 어긋남 찾기를
그대로 쓴다: 위 · 아래 고정 띠(stitch.bands), 띠 밖 같은 글 · 같은 x · 같은 너비의 닻 글(shift_by_text), 없으면
앞 조각 아래 · 뒤 조각 위에서 잘린 같은 x · 너비의 칸(shift_by_boxes), 설정에 따라 화소(shift_by_pixels).
어긋남 d 가 MIN_SHIFT 이상(내용이 위로 밀렸다 = 스크롤)이고 그 방법의 근거 수가 기준 이상이면 같은 화면이다.
같은 화면인 이웃끼리 이은 것이 한 묶음 (조각이 하나면 낱장). 시험한 설정 셋 (README 에 결과):
  A  닻 글 1개 이상 · 잘린 칸 1개 이상 · 화소, 어긋남 1px 이상 (stitch.py 가 잇는 순서 그대로)
  B  닻 글 2개 이상 · 잘린 칸 1개 이상, 화소는 쓰지 않음, 어긋남 100px 이상 (기본)
  C  A 와 같되 어긋남 100px 이상
"""
import argparse
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

STRICT = False
# 사람이 만든 파일 - strict 인 프로세스에서 열면 오류
FORBIDDEN = ("captures.json", "truth.json", "truth_regions.json", "original_transfer.html", "original_bill.html")
FORBIDDEN_DIRS = ("flows", "tasks")
GROUP_CONFIGS = {
    "A": {"text_min": 1, "boxes_min": 1, "pixels": True, "min_shift": 1},
    "B": {"text_min": 2, "boxes_min": 1, "pixels": False, "min_shift": 100},
    "C": {"text_min": 1, "boxes_min": 1, "pixels": True, "min_shift": 100},
}
GROUP_CONFIG = "B"
STRIPPED = ("name", "label")     # LOGO_HEAD 규칙이 붙인 칸 (detect.img_candidates · stitch.name_across)


class StrictInputError(RuntimeError):
    """strict 인데 만드는 줄이 사람 파일 · 상수를 읽으려 했다."""


def _forbidden(path):
    p = os.path.normpath(str(path)).replace("\\", "/")
    parts = p.split("/")
    if os.path.basename(p) in FORBIDDEN:
        return True
    try:
        rel = os.path.relpath(os.path.abspath(str(path)), ROOT).replace("\\", "/").split("/")
    except ValueError:          # 다른 드라이브
        return False
    return len(rel) > 1 and rel[0] in FORBIDDEN_DIRS and len(parts) > 1


def _hook(event, args):
    if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = args[0].decode() if isinstance(args[0], bytes) else args[0]
        if _forbidden(path):
            raise StrictInputError("strict: 사람 파일을 열려 했다 - %s" % path)
    elif event == "subprocess.Popen":
        raw = args[1] if len(args) > 1 else ""
        # Windows 에서는 명령이 한 줄 글로 온다 (list2cmdline)
        cmd = raw if isinstance(raw, str) else " ".join(str(x) for x in (raw or []))
        if any(f in cmd for f in FORBIDDEN):
            raise StrictInputError("strict: 사람 파일을 읽으려 했다 - %s" % cmd)


def enable():
    global STRICT
    if not STRICT:
        STRICT = True
        sys.addaudithook(_hook)


def human(what):
    """사람이 정한 상수를 쓰는 자리 - strict 이면 오류."""
    if STRICT:
        raise StrictInputError("strict: 사람이 정한 것을 쓰려 했다 - %s" % what)


def add_arg(ap):
    ap.add_argument("--inputs", choices=["legacy", "strict"], default="legacy",
                    help="strict = 스크린샷만 (사람 파일 · 상수를 읽지 않는다, 2026-10-19)")


def from_args(a):
    if getattr(a, "inputs", "legacy") == "strict":
        enable()
    return STRICT


def unit_name(caps):
    return "+".join(caps)


# --------------------------------------------------------------------------- #
# 이어 붙이기 자동 판정
# --------------------------------------------------------------------------- #
def pair_shift(ea, eb, ga, gb, cfg):
    """이웃한 두 캡처의 (같은 화면인가, 어긋남, 방법, 근거 수)."""
    import stitch as S
    h = ga.shape[0]
    top, bottom = S.bands(ga, gb)
    d, n = S.shift_by_text(ea, eb, top, bottom, h)
    if d is not None and n >= cfg["text_min"] and d >= cfg["min_shift"]:
        return True, d, "text", n
    d, n = S.shift_by_boxes(ea, eb, top, bottom, h)
    if d is not None and n >= cfg["boxes_min"] and d >= cfg["min_shift"]:
        return True, d, "boxes", n
    if cfg["pixels"]:
        d = S.shift_by_pixels(ga, gb, top, bottom)
        if d is not None and d >= cfg["min_shift"]:
            return True, d, "pixels", 0
    return False, None, None, 0


def auto_groups(folder, captures, config=None):
    """[(묶음 이름, [캡처 …]) …] 와 이웃 짝마다의 판정 기록. 조각이 둘 이상인 묶음만 돌려준다."""
    import numpy as np
    from PIL import Image
    cfg = GROUP_CONFIGS[config or GROUP_CONFIG]
    names = sorted(f[:-5] for f in os.listdir(folder)
                   if f.endswith(".json") and not f.startswith("_") and f not in ("compare.json",))
    names = [n for n in names if os.path.exists(os.path.join(captures, n + ".png"))]
    det = {n: json.load(io.open(os.path.join(folder, n + ".json"), encoding="utf-8"))["elements"] for n in names}
    gray = {n: np.asarray(Image.open(os.path.join(captures, n + ".png")).convert("L")) for n in names}
    runs, log = [[names[0]]], []
    for a, b in zip(names, names[1:]):
        ok, d, how, n = pair_shift(det[a], det[b], gray[a], gray[b], cfg)
        log.append({"a": a, "b": b, "same": ok, "shift": d, "method": how, "evidence": n})
        if ok:
            runs[-1].append(b)
        else:
            runs.append([b])
    return [(unit_name(r), r) for r in runs if len(r) > 1], log


# --------------------------------------------------------------------------- #
# prepare - D2.5 final 을 strict 폴더로 (로고 규칙 이름만 지운다)
# --------------------------------------------------------------------------- #
def prepare(src, out):
    os.makedirs(out, exist_ok=True)
    stripped = []
    for f in sorted(os.listdir(src)):
        p = os.path.join(src, f)
        if f.endswith(".json") and f not in ("truth.json", "compare.json", "_sweep.json"):
            d = json.load(io.open(p, encoding="utf-8"))
            for e in d.get("elements") or []:
                for k in STRIPPED:
                    if e.get(k) is not None:
                        stripped.append({"file": f, "id": e["id"], "field": k, "value": e[k]})
                        e[k] = None
            with io.open(os.path.join(out, f), "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False, indent=1)
    with io.open(os.path.join(out, "_strict.json"), "w", encoding="utf-8") as fh:
        json.dump({"from": os.path.relpath(src, ROOT).replace("\\", "/"),
                   "note": "검출(OmniParser · OCR · 설명 · 칸 안 그림 후보)은 D2.5 final 그대로. LOGO_HEAD 규칙이 "
                           "붙인 로고 이름(name)과 그 칸 글(label)만 지웠다 - 그림 후보를 찾을 때 은행 칸에서 칸 글만 "
                           "지운 차이는 남아 있다 (후보 자체를 다시 찾으려면 설명 모델을 다시 돌려야 한다)",
                   "stripped": stripped}, fh, ensure_ascii=False, indent=1)
    return stripped


def check():
    """strict 막기가 걸리는지 - 사람 파일 열기 · git show · 사람 상수 쓰기를 하나씩 해 보고 오류가 나는지."""
    import subprocess
    sys.path.insert(0, os.path.join(HERE, "sketch"))
    tries = [
        ("truth.json 열기", lambda: open(os.path.join(ROOT, "results", "detect", "20261013-d3b", "truth.json"))),
        ("truth_regions.json 열기", lambda: open(os.path.join(ROOT, "results", "detect", "20261019-regions",
                                                            "truth_regions.json"))),
        ("flows/original.json 열기", lambda: open(os.path.join(ROOT, "flows", "original.json"))),
        ("tasks/transfer.json 열기", lambda: open(os.path.join(ROOT, "tasks", "transfer.json"))),
        ("옛 원본 HTML 열기", lambda: open(os.path.join(ROOT, "inputs", "original_transfer.html"))),
        ("git show captures.json", lambda: subprocess.run(["git", "-C", ROOT, "show",
                                                           "origin/feat/db-principles:inputs/captures/transfer/captures.json"],
                                                          capture_output=True)),
        ("stitch.GROUPS", lambda: __import__("stitch").human_groups()),
        ("semantic.TASK", lambda: __import__("semantic").task_line()),
        ("flow.read_captures (이름표)", lambda: __import__("flow").read_captures(
            "origin/feat/see-captures", "inputs/captures/transfer/captures.json")),
        ("sketch/common.read_captures (이름표)", lambda: __import__("common").read_captures()),
    ]
    out = []
    for name, fn in tries:
        try:
            fn()
            out.append((name, "막히지 않음"))
        except StrictInputError as e:
            out.append((name, "막힘 - %s" % e))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "groups", "check"])
    ap.add_argument("--from", dest="src", default=os.path.join(ROOT, "results", "detect", "20261013-d25", "final"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "detect", "20261019-strict", "detect"))
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    a = ap.parse_args(argv)
    if a.cmd != "check":
        enable()
    if a.cmd == "check":
        # 다른 스크립트처럼 import 한 strict 모듈로 켜고 막는다 (__main__ 으로 돈 이 파일과는 다른 모듈이다)
        mod = __import__("strict")
        mod.enable()
        res = mod.check()
        lines = ["%-34s %s" % r for r in res]
        print("\n".join(lines))
        path = os.path.join(os.path.dirname(a.out), "strict_check.txt")
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("strict.py check - strict 를 켠 프로세스에서 사람 파일 · 상수를 하나씩 읽어 본 결과\n\n"
                     + "\n".join(lines) + "\n")
        if any(r[1] == "막히지 않음" for r in res):
            raise SystemExit("막히지 않은 것이 있다")
        return
    if a.cmd == "prepare":
        s = prepare(a.src, a.out)
        print("지운 칸 %d (name %d · label %d) → %s" % (len(s), sum(x["field"] == "name" for x in s),
                                                     sum(x["field"] == "label" for x in s), a.out))
    else:
        res = {}
        for c in GROUP_CONFIGS:
            groups, log = auto_groups(a.src, a.captures, c)
            res[c] = {"config": GROUP_CONFIGS[c], "groups": groups, "pairs": log}
            print(c, GROUP_CONFIGS[c], [g for g, _ in groups])
        path = os.path.join(os.path.dirname(a.out), "groups.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
