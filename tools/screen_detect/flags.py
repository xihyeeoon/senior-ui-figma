r"""요소에 표시(flags)를 단다 - 지우지 않고 남긴다 (시험 D2.5).

    C:\Users\xihye\venvs\detect\Scripts\python.exe tools/screen_detect/flags.py
        [--dir results/detect/20261013-d25/<설정>] [--captures inputs/captures/transfer]

detect.py 의 <dir>/<캡처>.json 을 읽어 요소마다 `flags` 목록을 더해 다시 쓰고, 무엇을 어떻게
찾았는지 <dir>/_flags.json 에 남긴다. stitch.py 보다 먼저 돌린다 (이은 요소는 표시를 그대로 가진다).
무엇을 버릴지는 의미 층(D3)과 연구자가 정한다 - 여기서는 표시만 한다.

  system_band   캡처들 사이에서 같은 자리 · 거의 같은 화소인 위 · 아래 띠(상태바 등) 안의 요소.
                band() 참고.
"""
import argparse
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# 고정 띠 - 줄마다 바탕(줄의 중앙값)을 빼고 남은 "잉크" 를 견준다. 바탕색이 다르거나(홈의 회색
# 바탕) 덮개로 어두워진 캡처(시트 · 팝업 뒤)도 같은 상태바로 보기 위해서다.
BLANK_STD = 3.0      # 잉크의 표준편차가 이 아래면 빈 줄 (빈 줄끼리만 같다)
ROW_CORR = 0.9       # 빈 줄이 아닌 두 줄은 잉크의 상관이 이 이상이면 같다
BAND_SHARE = 0.75    # 한 줄에서 서로 같은 캡처가 이 비율 이상이어야 띠의 줄이다
BAND_FIT = 0.9       # 한 캡처는 띠의 줄 가운데 이 비율 이상이 다수와 같아야 그 띠를 가진다
BAND_GAP = 4         # 띠의 줄이 아닌 줄이 이만큼까지 이어져도 띠를 끊지 않는다 (글자 윗 · 아랫 가장자리
                     # 줄은 어두워진 캡처에서 빈 줄로 읽혀 어긋난다)


def rows_ink(img):
    """[캡처 수, 높이, 너비] 회색조 → 줄마다 정규화한 잉크와 빈 줄 여부."""
    import numpy as np
    g = img.astype(np.float32)
    ink = g - np.median(g, axis=2, keepdims=True)
    std = ink.std(axis=2)
    blank = std < BLANK_STD
    z = ink / np.maximum(std, 1e-6)[..., None]
    return z, blank


def same_rows(z, blank, y):
    """줄 y 에서 캡처끼리 같은가 [n, n]."""
    import numpy as np
    zy, by = z[:, y, :], blank[:, y]
    corr = zy @ zy.T / zy.shape[1]
    same = (corr >= ROW_CORR) & ~by[:, None] & ~by[None, :]
    return same | (by[:, None] & by[None, :])


def band(gray):
    """위 · 아래 고정 띠의 높이와 그 띠를 가진 캡처.

    줄마다 "서로 같은 캡처" 의 가장 큰 무리(어느 캡처와 같은 캡처 수 + 1 의 최댓값)가 전체의
    BAND_SHARE 이상인 줄을 띠의 줄로 본다. 위에서부터(아래에서부터) 그런 줄이 이어지는(BAND_GAP 줄까지의
    틈은 넘는다) 마지막 줄까지가 띠의 높이다. 빈 줄만 같은 띠는 띠가 아니다. 캡처마다는 띠의 줄 가운데 BAND_FIT 이상에서 그 무리에 들어야 띠를 가진다
    (스크롤해 상태바 없이 찍힌 홈 01b · 01c 는 갖지 않는다)."""
    import numpy as np
    z, blank = rows_ink(gray)
    n, h = gray.shape[0], gray.shape[1]
    need = int(np.ceil(BAND_SHARE * n))

    def scan(ys):
        rows, member, ink, miss = [], [], False, 0
        for i, y in enumerate(ys):
            s = same_rows(z, blank, y)
            deg = s.sum(axis=1)
            k = int(deg.argmax())
            if deg[k] < need:
                miss += 1
                if miss > BAND_GAP:
                    break
                continue
            miss = 0
            rows.append(i)
            member.append(s[k])
            ink = ink or not blank[k, y]
        if not rows or not ink:
            # 빈 줄만 같은 띠는 띠가 아니다 (화면 끝의 흰 여백)
            return 0, [False] * n
        fit = np.mean(member, axis=0) >= BAND_FIT
        return rows[-1] + 1, [bool(f) for f in fit]

    top, top_has = scan(range(h))
    bottom, bottom_has = scan(range(h - 1, -1, -1))
    return {"top": top, "bottom": bottom, "top_has": top_has, "bottom_has": bottom_has}


def centre_y(e):
    return e["box"][1] + e["box"][3] / 2


def add(e, flag):
    e.setdefault("flags", [])
    if flag not in e["flags"]:
        e["flags"].append(flag)


def main(argv=None):
    import numpy as np
    from PIL import Image
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--captures", default=os.path.join(ROOT, "inputs", "captures", "transfer"))
    a = ap.parse_args(argv)
    names = sorted(f[:-5] for f in os.listdir(a.dir) if f.endswith(".json")
                   and not f.startswith("_") and f not in ("truth.json", "compare.json"))
    dets = {n: json.load(io.open(os.path.join(a.dir, n + ".json"), encoding="utf-8"))
            for n in names}
    gray = np.stack([np.asarray(Image.open(os.path.join(a.captures, n + ".png")).convert("L"))
                     for n in names])
    b = band(gray)
    h = gray.shape[1]
    info = {"system_band": {
        "top": b["top"], "bottom": b["bottom"],
        "top_captures": [n for n, f in zip(names, b["top_has"]) if f],
        "bottom_captures": [n for n, f in zip(names, b["bottom_has"]) if f],
        "how": "줄마다 바탕(중앙값)을 뺀 잉크를 견줘(빈 줄은 빈 줄끼리, 아니면 상관 >= %.1f) 서로 "
               "같은 캡처가 %d%% 이상인 줄이 위(아래)에서부터 이어지는 마지막 줄까지 (%d줄까지의 틈은 "
               "넘는다, 빈 줄만이면 띠 없음). 캡처는 띠 줄의 %d%% 이상에서 다수와 같아야 그 띠를 "
               "가진다" % (ROW_CORR, BAND_SHARE * 100, BAND_GAP, BAND_FIT * 100)},
        "counts": {}}
    for i, n in enumerate(names):
        k = 0
        for e in dets[n]["elements"]:
            cy = centre_y(e)
            if (b["top_has"][i] and cy < b["top"]) or (b["bottom_has"][i] and cy > h - b["bottom"]):
                add(e, "system_band")
                k += 1
        info["counts"].setdefault("system_band", {})[n] = k
    for n in names:
        with io.open(os.path.join(a.dir, n + ".json"), "w", encoding="utf-8") as f:
            json.dump(dets[n], f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(a.dir, "_flags.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in info.items() if k != "counts"}, ensure_ascii=False))
    print({k: sum(v.values()) for k, v in info["counts"].items()})


if __name__ == "__main__":
    main()
