r"""채점 - OmniParser (strict2) 대 UI-DETR-1 (uidetr.py), 검출 단계만 (2026-10-19). 사람 파일을 읽는 채점 쪽이다.

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/uidetr_report.py
        → results/detect/20261019-uidetr/summary.md, results/detect/20261019-uidetr/home_01a.png

견주는 셋 - 모두 같은 정답지 · 같은 compare (자리 옮기기 local, 10/19 채점 고침) 로 잰 compare.json:
  OmniParser strict2     results/detect/20261019-strict2/score/detect-strict2
  UI-DETR-1 (자동 묶음)  results/detect/20261019-uidetr/score-auto      - 이어 붙이기도 UI-DETR-1 상자로 자동 판정
  UI-DETR-1 (같은 묶음)  results/detect/20261019-uidetr/score-samegroups - 이어 붙이기 묶음만 strict2 것을 그대로
남은 놓침 여섯 곳은 캡처 위 실제 자리 (그림을 보고 적은 상자, 캡처 픽셀) 에 검출 상자 · 칸 안 그림 후보가 있는지로 본다 -
실제 자리와 IoU 0.3 이상인 글 없는 상자 · 칸 안 그림 후보가 있으면 잡힘 (칸 상자처럼 넓은 것은 안 걸린다).
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import compare as C  # noqa: E402
import detect as D  # noqa: E402

R = os.path.join(ROOT, "results", "detect")
U = os.path.join(R, "20261019-uidetr")
SIDES = [("OmniParser (strict2)", os.path.join(R, "20261019-strict2", "detect"),
          os.path.join(R, "20261019-strict2", "score", "detect-strict2")),
         ("UI-DETR-1 (자동 묶음)", os.path.join(U, "detect"), os.path.join(U, "score-auto")),
         ("UI-DETR-1 (같은 묶음)", os.path.join(U, "detect-samegroups"), os.path.join(U, "score-samegroups"))]
# 남은 놓침 - 그림 자리 놓침 진단 (20261019-miss) 의 점수 낮음 3 · 검출기가 못 봄 1, strict2 에서 잃은 은행 로고 2
SPOT_IOU = 0.3       # 남은 놓침 - 실제 자리와 IoU 이 이상인 글 없는 상자 · 칸 안 그림 후보가 있으면 잡힘 (칸 상자는 넓어서 안 걸린다)
SPOTS = [("유진투자증권 로고 (점수 낮음)", "06a", [98, 1705, 111, 102]),
         ("LS증권 로고 (점수 낮음)", "06a", [361, 1704, 99, 99]),
         ("신한 로고 - 확인 화면 (점수 낮음)", "08", [329, 204, 168, 168]),
         ("체크카드 아이콘", "01a", [72, 810, 92, 92]),
         ("수협 로고", "05a", [100, 1138, 104, 104]),
         ("저축은행 로고", "05b", [362, 1350, 104, 104])]


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def slot_hits(c):
    st = {}
    for unit, pc in c["per_capture"].items():
        for r in pc["rows"]:
            if r["kind"] == "slot":
                k = (c["proposed"][unit], r["label"])
                st[k] = st.get(k) or bool(r.get("named") or r.get("near"))
    return sum(st.values()), len(st)


def spot_hit(det_dir, cap, rect):
    els = load(os.path.join(det_dir, cap + ".json"))["elements"]
    got = [e for e in els if (e["kind"] == "img_candidate" or (e["kind"] == "box" and not e.get("text")))
           and D.iou(D.xyxy(e["box"]), D.xyxy(rect)) >= SPOT_IOU]
    return ("예 (%s)" % ", ".join("%s %s %s" % (e["id"], e["kind"], e["box"]) for e in got[:2])) if got else "아니오"


def main():
    rows, data = [], []
    for name, det, sc in SIDES:
        c = load(os.path.join(sc, "compare.json"))
        run = load(os.path.join(det, "_run.json"))
        groups = load(os.path.join(det, "_groups.json"))["groups"] if os.path.exists(os.path.join(det, "_groups.json")) else []
        data.append((name, det, c, run, groups))
    br = lambda c, k: "%d/%d" % tuple(c["row"]["box_recall"][k])
    table = [["상자 재현율 - 버튼", *[br(c, "button") for _, _, c, _, _ in data]],
             ["상자 재현율 - 입구", *[br(c, "entrance") for _, _, c, _, _ in data]],
             ["상자 재현율 - 선택지", *[br(c, "choice") for _, _, c, _, _ in data]],
             ["상자 재현율 - 입력칸", *[br(c, "field") for _, _, c, _, _ in data]],
             ["그림 자리에 닿은 후보 (/90)", *["%d/%d" % slot_hits(c) for _, _, c, _, _ in data]],
             ["정답에 없는 상자 (그 밖 / 전체)", *["%d / %d" % (c["row"]["leftover"]["other"], c["row"]["leftover"]["total"])
                                           for _, _, c, _, _ in data]],
             ["검출 상자 (단위 합)", *[str(c["row"]["boxes"]) for _, _, c, _, _ in data]],
             ["칸 안 그림 후보 (단위 합)", *[str(sum(p.get("img_candidates", 0) for p in c["per_capture"].values()))
                                       for _, _, c, _, _ in data]],
             ["이어 붙이기 묶음", *[" · ".join(n for n, _ in g) for _, _, _, _, g in data]],
             ["캡처 한 장당 검출 시간 (초)", *["%.3f" % r["per_image_seconds_mean"]["detect"] for _, _, _, r, _ in data]]]
    for label, cap, rect in SPOTS:
        table.append([label, *[spot_hit(det, cap, rect) for _, det, _, _, _ in data]])
    md = ["# OmniParser 대 UI-DETR-1 - 검출 단계만 (2026-10-19)\n",
          "UI-DETR-1 = racineai/UI-DETR-1 (sha 0f0dda5, MIT, RF-DETR-M, 종류 구분 없음), rfdetr 1.5.0 (Apache-2.0). 설정은 "
          "모델 카드 Quick Start 그대로 - resolution 1600, threshold 0.3, NMS 없음, 대비 사본 검출 없음. OCR · 아이콘 글 규칙 · 겹친 "
          "박스 정리 · 칸 안 그림 후보 (로고 규칙 꺼짐) · 상태바 표시는 strict2 와 같다. 정답지 · compare (local, 10/19 채점 고침) "
          "도 같다. OmniParser 의 검출 시간은 원본 + 대비 사본 두 번 검출한 것이다.\n",
          C.table(["", *[n for n, _, _, _, _ in data]], table),
          "\n자동 묶음: 이어 붙이기 자동 판정은 \"잘린 칸\" 근거에 검출 상자를 쓴다 - UI-DETR-1 상자로는 01a → 01b · 06a → 06b 의 잘린 "
          "칸이 맞지 않아 01a · 06a 가 따로 남았다. 같은 묶음 = 검출기만 견주려고 strict2 의 묶음을 그대로 쓴 것 (이은 자리는 UI-DETR-1 "
          "상자로 다시 셈 - 01b 는 화소로, 06b 는 겹침 없음 가정으로 이어졌다).\n",
          "남은 놓침 칸: 캡처 위 실제 자리와 IoU 0.3 이상인 글 없는 검출 상자 또는 칸 안 그림 후보가 있으면 예.\n",
          "그림: `home_01a.png` - 홈 01a 의 OmniParser (왼쪽) · UI-DETR-1 (오른쪽) 최종 요소 (detect.overlay 와 같은 색 - 파랑 글 든 "
          "박스 · 빨강 글 없는 박스 · 주황 칸 안 그림 후보 · 초록 OCR 글).\n"]
    with io.open(os.path.join(U, "summary.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    # 홈 01a 나란히
    from PIL import Image
    a = Image.open(os.path.join(data[0][1], "overlay", "01a.png"))
    b = Image.open(os.path.join(data[1][1], "overlay", "01a.png"))
    w, h = a.width // 2, a.height        # overlay 는 [캡처 | 다시 그림] - 왼쪽 반만
    out = Image.new("RGB", (w * 2 + 16, h), "white")
    out.paste(a.crop((0, 0, w, h)), (0, 0))
    out.paste(b.crop((0, 0, w, h)), (w + 16, 0))
    out.save(os.path.join(U, "home_01a.png"))
    print(md[2])


if __name__ == "__main__":
    main()
