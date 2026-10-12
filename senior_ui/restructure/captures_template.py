r"""캡처 대응표의 빈 틀 - 연구자 손을 덜어 준다 (2026-10-12).

    python -m senior_ui.restructure.captures_template inputs/captures/transfer --task transfer

폴더의 PNG 를 이름순으로 나열하고 label 이 빈 (taps 는 빈 배열인) captures.json 을 만든다.
같은 출력에 지금 렌더 그림의 이름표(실행 하나의 attempt_1.plan_prompt.txt 의 "[그림 n/N]" 줄)를
참고용으로 보인다. **label 과 taps 를 짐작해 채우지 않는다** - 캡처가 어느 화면 · 상태인지는
연구자가 적는다 (docs/input-contract.md "캡처 입력"). 이미 파일이 있으면 덮어쓰지 않는다.
--dry-run 이면 쓰지 않고 보이기만 한다.
"""
import argparse
import io
import json
import os
import re
import sys

from senior_ui import tasks as T
from senior_ui._cli import setup_stdout
from senior_ui.config import ROOT

from .captures import NAME, rel

# 참고 이름표를 읽을 실행 - --see 로 원본 그림 15장을 보낸 이체 실행 (2026-10-08)
REFERENCE_RUN = os.path.join(ROOT, "results", "runs", "20261008-131136")
LABEL_LINE = re.compile(r"^\[그림 (\d+)/(\d+)\] (.*?)  <그림: ")


def reference_labels(plan_prompt):
    """그 기록의 그림 이름표들 `[(n, N, 이름표)]`. 없으면 빈 목록."""
    if not plan_prompt or not os.path.isfile(plan_prompt):
        return []
    out = []
    for line in io.open(plan_prompt, encoding="utf-8"):
        m = LABEL_LINE.match(line)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), m.group(3)))
    return out


def template(folder, task):
    pngs = sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))
    return {"task": task, "source": "",
            "images": [{"file": f, "label": "", "taps": []} for f in pngs]}


def main(argv=None):
    setup_stdout()
    ap = argparse.ArgumentParser(description="캡처 대응표(captures.json)의 빈 틀을 만든다")
    ap.add_argument("folder", help="캡처 PNG 가 있는 폴더 (inputs/captures/<과제>)")
    ap.add_argument("--task", choices=T.task_names(), required=True)
    ap.add_argument("--labels-from", default=os.path.join(REFERENCE_RUN,
                                                          "attempt_1.plan_prompt.txt"),
                    help="참고 이름표를 읽을 진단·계획 프롬프트 기록 (기본: %s)"
                         % rel(os.path.join(REFERENCE_RUN, "attempt_1.plan_prompt.txt")))
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 보이기만 한다")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.folder):
        print("폴더가 없다: %s" % args.folder, file=sys.stderr)
        return 2
    data = template(args.folder, args.task)
    out = os.path.join(args.folder, NAME)
    print("캡처 %d장 (%s, 이름순 - 이 순서가 모델에게 보이는 순서다. 바꾸려면 images 의 "
          "순서를 바꾼다):" % (len(data["images"]), rel(args.folder)))
    for i, im in enumerate(data["images"], 1):
        print("  %2d. %s" % (i, im["file"]))
    refs = reference_labels(args.labels_from)
    print()
    print("참고 - 지금 렌더 그림의 이름표 %d개 (%s). label 은 이것을 본떠 연구자가 쓴다 - "
          "이 도구는 짐작해 채우지 않는다:" % (len(refs), rel(args.labels_from)))
    for n, total, label in refs:
        print("  [그림 %d/%d] %s" % (n, total, label))
    print()
    if args.dry_run:
        print("--dry-run: 쓰지 않았다. 쓸 내용:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if os.path.exists(out):
        print("이미 있다 - 덮어쓰지 않았다: %s" % rel(out))
        return 1
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("썼다: %s - label 을 채운 뒤 --captures %s 로 돌린다" % (rel(out), rel(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
