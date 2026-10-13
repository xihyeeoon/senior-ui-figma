r"""원본 닮음 - 재구성 실행의 화면이 원본 화면과 얼마나 같은 모양인가 (2026-10-13). 기록만 한다.

판정 · 검사기에는 쓰지 않는다 - tools/compare_runs.py 의 칸이다. 배치 단계 (--mode layout) 의
실행 20261013-152332 를 Figma 로 본 연구자 판단이 "배치는 풀렸지만 원본 UI 와 비슷해졌다" 였고,
그것을 실행끼리 같은 자로 견주려고 만들었다.

읽는 것은 화면설계서 둘 (storyboard.json) 이다 - 원본을 빌드로 둔 것 (tools/reference_storyboard.py,
이체는 results/reference/original-transfer) 과 재구성 실행의 것. 같은 도구가 같은 방식으로 걸어
모은 항목 (누를 수 있는 요소, 상자는 장 왼쪽 위 기준) 이라 두 쪽을 같은 자로 잰다. 견주는 장은
정답 경로 화면의 본 장 (main) 이고, 생성 화면은 계획의 screens[].from 으로 원본 이름에 맞춘다
(err- 는 빼고 남은 원본 화면이 하나일 때만 - 검사 M 의 flow_fixed.origin_of 와 같은 규칙).

  요소 순서 같음   두 장의 항목을 짝짓는다 - 먼저 같은 action 끼리 (같은 action 이 여럿이면
                   위→아래 k 번째끼리), 남은 것은 같은 글 (text, 없으면 aria) 끼리. 짝지은 항목의
                   읽는 순서 (위→아래, 같은 줄 - 위 끝이 ROW_TOLERANCE 안 - 이면 왼쪽부터) 가
                   얼마나 같은가 = 최장 공통 부분열 길이 / 짝지은 수. 1 이면 순서가 같다. 짝이
                   없으면 값이 없다.
  무리 순서 같음   두 장을 같은 규칙으로 무리로 나눈다 - 위에서 아래로 보며 세로 틈이 GAP 보다
                   벌어지면 새 무리 (화면설계서의 --mock 영역 묶기와 같은 규칙. 생성 쪽의 모델 영역은
                   원본 쪽에 없으므로 쓰지 않는다 - 두 쪽을 같은 자로 나누려는 것). 선택지 무리는
                   항목 하나라 그 무리 안에 든다. 생성 무리마다 짝지은 요소가 가장 많이 속한 원본
                   무리를 붙이고 (같으면 앞 무리), 처음 나온 차례로 줄인 목록에서 위와 같이 잰다.
  격자 · 탭        아래 "격자 · 탭 판정" 의 단위를 두 장에서 각각 모으고, 생성 단위마다 같은 종류의
                   원본 단위와 짝지은 항목을 둘 이상 (단위가 항목 하나면 하나) 나눠 가지면 "원본에도
                   있음", 아니면 "새로 생김". 짝을 볼 때는 종류를 가리지 않는다 - 원본의 아래 띠 (격자)
                   가 생성에서 탭처럼 바뀐 것은 같은 줄이므로 "원본에도 있음" (생성 쪽 종류로 센다).
                   그렇게 맞춰지지 않은 원본 단위는 "원본에 있었는데 없어짐"
                   - 다만 그 단위의 선택지 무리가 생성 쪽에서 안쪽 배치를 잴 수 없으면 (그림 자리가
                   없다) 모르는 것이라 세지 않는다.

격자 · 탭 판정 (누를 수 있는 항목의 상자로):
  줄       위 끝 차이가 ROW_TOLERANCE 이하이고 높이 차이가 SIZE_TOLERANCE 이하인 항목들. 그 안에서
           왼쪽부터 보아 이웃끼리 가로 틈이 NEIGHBOUR_GAP 이하이고 폭의 비가 WIDTH_RATIO 이하로
           이어지는 둘 이상 = 나란한 줄. 머리 띠의 [이전] · [취소] 처럼 멀리 떨어진 둘, 크기가 다른
           둘은 줄이 아니다.
  탭       나란한 줄 가운데 모든 항목이 눌러도 같은 화면에 남고 (결과 same · none), 하나 이상은
           제자리에 새 내용을 보이고 (same 이고 그 설명이 "새로 보임" 으로 시작 - 순서만 바뀌는 비밀번호
           [재배열] 은 아니다) 하나 이상은 그대로인 (none - 지금 고른 탭) 것. 화면설계서의
           항목에는 role 이 없어 role="tab" 은 볼 수 없다. none 뿐인 줄 (과제 밖 입구의 아래 띠) 과
           same 뿐인 줄 (메뉴마다 제자리에 안내를 띄우는 버튼 줄 - 실행 20261013-152332 의 홈) 은
           탭이 아니라 격자다.
  격자     탭이 아닌 나란한 줄. 바로 아래로 이어지는 줄 (세로 틈 NEIGHBOUR_GAP 이하) 이 같은 칸 수에
           왼쪽 끝이 같으면 (SIZE_TOLERANCE 안) 한 격자로 합친다. 선택지 무리 (항목 하나로
           묶인 것) 는 그 안의 그림 자리 (images 의 in 이 그 항목) 가 둘 이상의 열에 서 있으면 격자다
           (은행 로고). 그림 자리가 없는 무리 (숫자판 · 빠른 금액) 는 안쪽 배치를 잴 수 없어 세지
           않고 unmeasured 에 남긴다.
"""

# 같은 줄로 보는 위 끝 차이 - 화면설계서가 항목 번호를 매기는 규칙과 같다 (build.ROW_TOLERANCE)
ROW_TOLERANCE = 6
# 높이 · 왼쪽 끝이 같다고 보는 차이 (px)
SIZE_TOLERANCE = 4
# 나란한 이웃 사이의 가로 틈, 이어지는 줄 사이의 세로 틈 (px)
NEIGHBOUR_GAP = 24
# 나란한 이웃의 폭 비 (큰 것 / 작은 것)
WIDTH_RATIO = 1.34
# 무리를 나누는 세로 틈 - 화면설계서 --mock 영역 묶기 (regions.MOCK_GAP) 와 같다
GAP = 24
# 그림 자리의 열을 가르는 가로 차이 (px)
COLUMN_TOLERANCE = 8


def reading_order(items):
    """항목 번호 (items 의 자리) 를 읽는 순서로 - 위→아래, 같은 줄이면 왼쪽부터."""
    idx = sorted(range(len(items)), key=lambda i: (items[i]["box"][1], items[i]["box"][0]))
    rows, cur = [], []
    for i in idx:
        if cur and items[i]["box"][1] - items[cur[0]]["box"][1] > ROW_TOLERANCE:
            rows.append(cur)
            cur = []
        cur.append(i)
    if cur:
        rows.append(cur)
    return [i for r in rows for i in sorted(r, key=lambda i: items[i]["box"][0])]


def _label(it):
    return " ".join(str(it.get("text") or it.get("aria") or "").split())


def pair(orig, built):
    """`[(원본 자리, 생성 자리)]` - 같은 action 끼리 k 번째끼리, 남은 것은 같은 글끼리."""
    o_order, b_order = reading_order(orig), reading_order(built)
    pairs, used_o, used_b = [], set(), set()
    for key in (lambda it: it.get("action"), _label):
        groups = {}
        for i in o_order:
            k = key(orig[i])
            if i not in used_o and k:
                groups.setdefault(k, ([], []))[0].append(i)
        for j in b_order:
            k = key(built[j])
            if j not in used_b and k in groups:
                groups[k][1].append(j)
        for os_, bs in groups.values():
            for i, j in zip(os_, bs):
                pairs.append((i, j))
                used_o.add(i)
                used_b.add(j)
    return pairs


def lis(seq):
    """가장 긴 증가 부분열의 길이 (= 0..n-1 과의 최장 공통 부분열)."""
    import bisect
    tails = []
    for x in seq:
        k = bisect.bisect_left(tails, x)
        tails[k:k + 1] = [x]
    return len(tails)


def element_order(orig, built, pairs):
    """짝지은 요소의 순서가 같은 정도 (0~1). 짝이 없으면 None."""
    if not pairs:
        return None
    o_rank = {i: r for r, i in enumerate(reading_order(orig))}
    b_rank = {j: r for r, j in enumerate(reading_order(built))}
    seq = [o_rank[i] for i, j in sorted(pairs, key=lambda p: b_rank[p[1]])]
    return round(lis(seq) / len(pairs), 4)


def blocks(items):
    """세로 틈 GAP 으로 나눈 무리들 - 항목 자리의 목록, 위에서부터."""
    out, cur, bottom = [], [], None
    for i in sorted(range(len(items)), key=lambda i: (items[i]["box"][1], items[i]["box"][0])):
        top, h = items[i]["box"][1], items[i]["box"][3]
        if cur and top - bottom > GAP:
            out.append(cur)
            cur = []
        bottom = top + h if not cur else max(bottom, top + h)
        cur.append(i)
    if cur:
        out.append(cur)
    return out


def block_order(orig, built, pairs):
    """무리 순서가 같은 정도 (0~1). 짝지은 요소가 든 생성 무리가 없으면 None."""
    o_block = {i: n for n, b in enumerate(blocks(orig)) for i in b}
    to_orig = dict((j, i) for i, j in pairs)
    seq = []
    for b in blocks(built):
        votes = {}
        for j in b:
            if j in to_orig:
                n = o_block[to_orig[j]]
                votes[n] = votes.get(n, 0) + 1
        if votes:
            n = min(votes, key=lambda k: (-votes[k], k))
            if n not in seq:
                seq.append(n)
    return round(lis(seq) / len(seq), 4) if seq else None


# --------------------------------------------------------------------------- #
# 격자 · 탭
# --------------------------------------------------------------------------- #
def _rows(items):
    """나란한 줄들 - 항목 자리의 목록 (왼쪽부터). 선택지 무리는 빼고 본다."""
    els = [i for i, it in enumerate(items) if it.get("kind") != "group"]
    els.sort(key=lambda i: (items[i]["box"][1], items[i]["box"][0]))
    lines, seen = [], set()
    for i in els:
        if i in seen:
            continue
        x, y, w, h = items[i]["box"]
        line = [j for j in els if j not in seen
                and abs(items[j]["box"][1] - y) <= ROW_TOLERANCE
                and abs(items[j]["box"][3] - h) <= SIZE_TOLERANCE]
        seen.update(line)
        line.sort(key=lambda j: items[j]["box"][0])
        run = [line[0]]
        for a, b in zip(line, line[1:]):
            ax, _, aw, _ = items[a]["box"]
            bx, _, bw, _ = items[b]["box"]
            gap = bx - (ax + aw)
            ratio = max(aw, bw) / max(min(aw, bw), 1)
            if 0 <= gap <= NEIGHBOUR_GAP and ratio <= WIDTH_RATIO:
                run.append(b)
            else:
                if len(run) >= 2:
                    lines.append(run)
                run = [b]
        if len(run) >= 2:
            lines.append(run)
    return lines


def _is_tab(items, line):
    res = [items[i].get("result") or {} for i in line]
    kinds = [r.get("kind") for r in res]
    shows = any(r.get("kind") == "same" and str(r.get("detail") or "").startswith("새로 보임")
                for r in res)
    return all(k in ("same", "none") for k in kinds) and shows and "none" in kinds


def _columns(images, no):
    xs = sorted(g["box"][0] for g in images if g.get("in") == no)
    cols = []
    for x in xs:
        if not cols or x - cols[-1] > COLUMN_TOLERANCE:
            cols.append(x)
    return len(cols), len(xs)


def units(sh):
    """한 장의 격자 · 탭 단위 `[{"kind": "grid" | "tab", "members": [항목 자리], "top"}]`, 위에서부터."""
    items, out = sh.get("items") or [], []
    grids = []
    for line in _rows(items):
        if _is_tab(items, line):
            out.append({"kind": "tab", "members": line, "top": items[line[0]]["box"][1]})
        else:
            grids.append(line)
    merged = []
    for line in grids:
        last = merged[-1] if merged else None
        if last is not None and len(line) == last["cols"]:
            prev_bottom = max(items[i]["box"][1] + items[i]["box"][3] for i in last["row"])
            lefts_same = all(abs(items[a]["box"][0] - items[b]["box"][0]) <= SIZE_TOLERANCE
                             for a, b in zip(last["row"], line))
            if lefts_same and 0 <= items[line[0]]["box"][1] - prev_bottom <= NEIGHBOUR_GAP:
                last["members"] += line
                last["row"] = line
                continue
        merged.append({"kind": "grid", "members": list(line), "row": line, "cols": len(line),
                       "top": items[line[0]]["box"][1]})
    for g in merged:
        out.append({"kind": "grid", "members": g["members"], "top": g["top"]})
    for i, it in enumerate(items):
        if it.get("kind") == "group":
            cols, n = _columns(sh.get("images") or [], it.get("no"))
            if n and cols >= 2:
                out.append({"kind": "grid", "members": [i], "top": it["box"][1]})
    out.sort(key=lambda u: u["top"])
    return [{"kind": u["kind"], "members": u["members"]} for u in out]


def unmeasured(sh):
    """안쪽 배치를 잴 수 없는 선택지 무리의 action (그림 자리가 없다 - 숫자판 · 빠른 금액)."""
    imgs = sh.get("images") or []
    return [it.get("action") for it in sh.get("items") or []
            if it.get("kind") == "group" and not any(g.get("in") == it.get("no") for g in imgs)]


def compare_units(orig_sh, built_sh, pairs):
    """`{"grid": {"kept", "new", "gone"}, "tab": {...}}` - 원본에도 있음 · 새로 생김 · 없어짐."""
    o_units, b_units = units(orig_sh), units(built_sh)
    to_orig = dict((j, i) for i, j in pairs)
    b_items = built_sh.get("items") or []
    blind = set(unmeasured(built_sh))
    unknown = {i for i, j in pairs if b_items[j].get("kind") == "group"
               and b_items[j].get("action") in blind}
    os_ = [u for u in o_units if not set(u["members"]) & unknown]
    out = {k: {"kept": 0, "new": 0, "gone": 0} for k in ("grid", "tab")}
    matched = set()
    for u in b_units:
        mapped = {to_orig[j] for j in u["members"] if j in to_orig}
        need = min(2, len(u["members"]))
        hit = [n for n, v in enumerate(os_) if len(mapped & set(v["members"])) >= need]
        out[u["kind"]]["kept" if hit else "new"] += 1
        matched.update(hit)
    for n, v in enumerate(os_):
        if n not in matched:
            out[v["kind"]]["gone"] += 1
    return out


# --------------------------------------------------------------------------- #
# 실행 하나
# --------------------------------------------------------------------------- #
def origin(name, came):
    """생성 화면 이름 → 원본 화면 이름 (from 에서 err- 를 빼고 하나만 남을 때). 아니면 None."""
    froms = [s for s in came.get(name) or [] if isinstance(s, str) and not s.startswith("err-")]
    return froms[0] if len(froms) == 1 else None


def _mains(board):
    out = {}
    for sh in board.get("sheets") or []:
        if sh.get("main") and sh.get("screen") not in out:
            out[sh["screen"]] = sh
    return out


def _summary(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return {"mean": None, "min": None, "screens": 0}
    return {"mean": round(sum(vals) / len(vals), 4), "min": min(vals), "screens": len(vals)}


def run_report(orig_board, built_board, came, path):
    """정답 경로 화면마다 견준 것과 그 요약.

    `came` 은 생성 화면 → 계획의 from, `path` 는 원본의 정답 경로 화면 (flow_fixed.first_visits).
    돌려주는 것 {"screens": [{"screen", "built", "paired", "elements", "blocks", "units",
    "unmeasured"}], "summary": {"elements", "blocks", "units"}, "missing": [원본 화면]}."""
    o_main, b_main = _mains(orig_board), _mains(built_board)
    by_origin = {}
    for name, sh in b_main.items():
        o = origin(name, came)
        if o and o not in by_origin:
            by_origin[o] = sh
    rows, missing = [], []
    for screen in path:
        o_sh, b_sh = o_main.get(screen), by_origin.get(screen)
        if o_sh is None or b_sh is None:
            missing.append(screen)
            continue
        o_items, b_items = o_sh.get("items") or [], b_sh.get("items") or []
        pairs = pair(o_items, b_items)
        rows.append({"screen": screen, "built": b_sh["screen"], "paired": len(pairs),
                     "elements": element_order(o_items, b_items, pairs),
                     "blocks": block_order(o_items, b_items, pairs),
                     "units": compare_units(o_sh, b_sh, pairs),
                     "unmeasured": sorted(set(unmeasured(o_sh)) | set(unmeasured(b_sh)))})
    total = {k: {s: sum(r["units"][k][s] for r in rows) for s in ("kept", "new", "gone")}
             for k in ("grid", "tab")}
    return {"screens": rows, "missing": missing,
            "summary": {"elements": _summary(r["elements"] for r in rows),
                        "blocks": _summary(r["blocks"] for r in rows), "units": total}}
