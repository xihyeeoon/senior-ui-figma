r"""검출 설정 시험 - 설정마다 detect → flags → stitch → compare 를 돌리고 한 표로 (시험 D2.5).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/sweep.py
        [설정 이름 …] [--root results/detect/20261013-d25] [--config 이름="detect 인자" …]

설정마다 <root>/<이름>/ 에 detect.py 의 결과(확인 그림 포함) · _flags.json · stitched/ ·
summary.md · compare.json 을 쓰고, <root>/summary.md 에 설정 대 지표 표를 쓴다. OCR 은 한 번만
돌려 <root>/_ocr.json 을 함께 쓴다 (검출 설정은 OCR 을 바꾸지 않는다). 정답지는 <root>/truth.json
을 한 번 만들어 설정마다 복사한다.

지키는 선 (D2 의 값, 연구자 결정): 글 재현율 221/226 · 로고 이름 63/67 · 선택지 102/102. 하나라도
떨어진 설정은 표에 "버림" 으로 적는다.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable

# 한 번에 하나씩 바꾼 설정. D2 의 설정(BASE)에서 하나씩만 바꾼다 - detect.py 의 기본값은 D2.5 에서
# 고른 묶음으로 바뀌었으므로(final) 바탕을 인자로 다 적는다.
BASE = "--conf 0.05 --nms 0.1 --no-clahe --no-classic --tiles 0 --overlap omniparser --imgsz 640"
CONFIGS = {
    "d2": BASE,
    "imgsz1024": BASE + " --imgsz 1024",
    "imgsz1280": BASE + " --imgsz 1280",
    "tiles2": BASE + " --tiles 2",
    "clahe": BASE + " --clahe",
    "nms03": BASE + " --nms 0.3",
    "nms05": BASE + " --nms 0.5",
    "classic": BASE + " --classic",
    "conf01": BASE + " --conf 0.1",
    "overlap_iou": BASE + " --overlap iou",
    # 좋은 것끼리 묶은 것 (combo2 는 크게 오른 둘만 - 나머지 둘이 보태는지 보려고)
    "combo": BASE + " --conf 0.1 --overlap iou --clahe --nms 0.3",
    "combo2": BASE + " --conf 0.1 --overlap iou",
    # detect.py 의 기본값 (= combo 로 바꾼 뒤)
    "final": "",
}
GUARD = {"text": 221, "logos": 63, "choices": 102}


def run(args):
    r = subprocess.run([PY] + args, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    if r.returncode:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit("실패: %s" % " ".join(args))
    return r.stdout


def one(root, name, args):
    out = os.path.join(root, name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    tool = lambda t: os.path.join(HERE, t)
    run([tool("detect.py"), "--out", out, "--ocr-cache", os.path.join(root, "_ocr.json")]
        + args.split())
    run([tool("flags.py"), "--dir", out])
    run([tool("stitch.py"), "--dir", out])
    shutil.copy(os.path.join(root, "truth.json"), os.path.join(out, "truth.json"))
    run([tool("compare.py"), "--dir", out])
    with io.open(os.path.join(out, "_sweep.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name, "detect_args": args}, f, ensure_ascii=False)


def guard(d):
    r = json.load(io.open(os.path.join(d, "compare.json"), encoding="utf-8"))["row"]
    bad = [k for k, v in GUARD.items() if r[k][0] < v]
    return bad


def shown(args):
    """표에 적는 인자 - D2 바탕(BASE)에서 바꾼 것만."""
    if args is None:
        return "?"
    if not args:
        return "detect.py 기본값"
    if args == BASE:
        return "D2 그대로 (`%s`)" % BASE
    if args.startswith(BASE):
        return "D2 + `%s`" % args[len(BASE):].strip()
    return "`%s`" % args


def write_summary(root, order):
    sys.path.insert(0, HERE)
    import compare as C
    dirs = [os.path.join(root, n) for n in order if os.path.isfile(os.path.join(root, n, "compare.json"))]
    names = [os.path.basename(d) for d in dirs]
    args_of = {}
    for n, d in zip(names, dirs):
        try:
            args_of[n] = json.load(io.open(os.path.join(d, "_sweep.json"), encoding="utf-8"))["detect_args"]
        except OSError:
            args_of[n] = None
    md = ["# 검출 설정 시험 D2.5 (2026-10-13)\n",
          "더미앱 A1 이체 캡처 19장 · 같은 OCR(`_ocr.json`) · 같은 정답지(`truth.json`). 설정마다 "
          "`detect.py → flags.py → stitch.py → compare.py` (tools/screen_detect/sweep.py). "
          "**이 앱 캡처로 고른 설정이다** - 같은 19장을 보며 맞췄으므로 다른 앱에서는 다시 봐야 한다.\n",
          "지키는 선: 글 %d/226 · 로고 %d/67 · 선택지 %d/102 - 떨어지면 버린다.\n"
          % (GUARD["text"], GUARD["logos"], GUARD["choices"]),
          C.row_table(dirs, names), "",
          C.table(["설정", "detect 인자 (D2 에서 바꾼 것)", "지키는 선"],
                  [[n, shown(args_of.get(n)),
                    "지킴" if not guard(d) else "버림 (%s)" % ", ".join(guard(d))]
                   for n, d in zip(names, dirs)]),
          "\n박스 재현율 = 글 있는 정답 항목 가운데 그 글을 감싸는 검출 박스가 있는 것. 남는 박스 = 정답 "
          "어디에도 닿지 않는 검출 박스, 괄호는 표시(flags)별 - 덮개 뒤 · 고정 띠 · 그 밖. 초/장 = OCR "
          "(캐시에 남은 첫 측정) + 검출 + 설명.\n"]
    with io.open(os.path.join(root, "summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--root", default=os.path.join(ROOT, "results", "detect", "20261013-d25"))
    ap.add_argument("--config", action="append", default=[], help='이름="detect 인자"')
    ap.add_argument("--order", nargs="*", help="표의 줄 순서 (없으면 CONFIGS 순 + 더한 것)")
    a = ap.parse_args(argv)
    configs = dict(CONFIGS)
    for c in a.config:
        k, v = c.split("=", 1)
        configs[k] = v
    os.makedirs(a.root, exist_ok=True)
    if not os.path.exists(os.path.join(a.root, "truth.json")):
        run([os.path.join(HERE, "truth.py"), "--out", os.path.join(a.root, "truth.json")])
    for n in a.names or [k for k in CONFIGS if k != "final"]:
        one(a.root, n, configs[n])
        print(n, "지킴" if not guard(os.path.join(a.root, n)) else "버림", flush=True)
    order = a.order or list(dict.fromkeys(list(CONFIGS) + [k for k in configs if k not in CONFIGS]
                                          + sorted(os.listdir(a.root))))
    write_summary(a.root, order)


if __name__ == "__main__":
    main()
