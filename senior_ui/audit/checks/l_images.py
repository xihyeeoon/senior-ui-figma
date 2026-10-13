r"""검사 L - 그림 자리 보존. fatal.

원본 HTML 은 실제 앱에서 로고 · 아이콘 · 사진이 보이는 자리를 이름 붙은 그림 자리로 갖고
있다 - `role="img"` + aria-label "<무엇> 로고/아이콘" 의 회색 상자 (CSS 클래스 pic,
tests/test_image_slots.py). 그 자리는 "이 위치에 이 크기로 이런 그림이 들어간다" 는 설계
정보다. 그런데 생성 프롬프트에 그것을 지키라는 말이 없었고 검사기도 보지 않아서, 실행
20261008-131136 (시도 2) · 20261012-132226 (시도 1) 둘 다 role="img" 가 0개였다 - 계획이
"그림 대신 읽을 수 있는 이름" 으로 바꿨고 (20261012-132226 계획 C2) 은행 목록의 로고 67개도
사라졌다. 연구자 결정 (2026-10-12): 지우면 안 된다. 위치 · 크기 · 묶음은 바꿔도 되고 새
그림을 더해도 된다. 실제 그림 파일은 넣지 않는다 (외부 자원 없음) - 이름 붙은 상자면 된다.

판정 (검사 K 를 본뜬다):

    O   원본을 걷는 동안 - 정답 경로의 어느 걸음에서든, 흐름 명세의 reveal 로 펼친 뒤에든 -
        그려져 보인 그림 자리 (role="img" + aria-label, 크기 0 이 아니고 자신이나 조상이
        숨기지 않았다 - probes.PRESSABLE 과 같은 보임 규칙) 의 이름 집합. 누를 수 있든
        없든 센다. 은행 목록처럼 스크립트가 그리는 것도 같다
    B   생성물을 같은 방식으로 걸으며 보인 이름 집합
    O - B   지운 그림 자리 → fatal. 같은 화면이 아니어도 된다
    B - O   새 그림 자리 → 기록만 (images_new)

원본 문서에는 있지만 원본을 걷는 동안 한 번도 보이지 않은 이름 (은행 시트의 [증권사] 탭처럼)은
세지 않고 기록만 한다 (images_not_in_original). 크기 · 위치는 판정에 쓰지 않는다 - 생성 쪽에서
처음 보인 상자를 기록만 한다 (images_box).
"""

# 실패 안내문에 그대로 담는 기술 계약의 문장 (docs/restructure-prompt.md 의 CONTRACT).
RULE = ("원본의 그림 자리 (role=\"img\" 와 aria-label 을 가진 요소 — 로고 · 아이콘 · 사진이 들어갈 "
        "자리) 는 지우지 마라. aria-label 은 원본 그대로 둔다. 위치 · 크기 · 묶음은 바꿔도 된다. "
        "그림 자리는 CSS 로 크기를 준 상자로 그린다 (그림 파일 · 외부 자원 · 이모지 · 글자로 흉내 "
        "내지 않는다). 이름 글을 곁에 더하는 것은 자유다. 새 그림이 필요하면 같은 형식 "
        "(role=\"img\" + aria-label \"<무엇> 아이콘/로고/그림\") 으로 더해도 된다. 선택지마다 붙은 "
        "그림 자리 (은행 로고 등) 는 그 선택지마다 둔다.")


def seen(snapshot):
    """그 스냅샷의 그림 자리 `{이름: {visible, box, visit, reveal}}` - 정답 경로 + 펼치기,
    처음 본 순서대로. 한 번이라도 보였으면 보인 것이고, 상자 · 방문은 처음 보인 때의 것이다
    (drive.merge_entrances 와 같은 규칙). 정답 경로의 것이 먼저다."""
    out = {}
    rows = [snapshot.get("images_seen") or {}] + [
        (res or {}).get("images_seen") or {}
        for _, res in sorted((snapshot.get("revealed") or {}).items())]
    for got in rows:
        for name, row in got.items():
            old = out.get(name)
            if old is None or (row.get("visible") and not old.get("visible")):
                out[name] = row
    return out


def shown(state):
    return [n for n, row in state.items() if row.get("visible")]


def original_names(snapshot):
    """원본을 걷는 동안 그려져 보인 그림 자리 이름 (O) - 처음 본 순서. 판정은 이것으로 한다."""
    return shown(seen(snapshot))


def document_names(snapshot):
    """원본 문서에 있는 그림 자리 이름 - 걷는 동안 보인 것 (O) 먼저, 그다음 한 번도 보이지 않은
    것 (images_not_in_original - 은행 시트의 [증권사] 탭 뒤 증권사 로고 29개 등). 화면설계서가
    "원본의 그림 자리" (images[].original) 를 이것으로 가른다 (storyboard.build, 2026-10-13) -
    원본에 있던 그림이 원본에서 숨어 있었다고 새 그림으로 적히지 않게."""
    state = seen(snapshot)
    visible = shown(state)
    return visible + [n for n in state if n not in set(visible)]


def run(ctx):
    if "images_seen" not in ctx.orig or "images_seen" not in ctx.rep:
        ctx.skipped.append(
            "L/그림 자리 - 스냅샷에 그림 자리 수집(images_seen)이 없다 (수집이 생기기 전의 "
            "스냅샷이거나 손으로 만든 것). 판정하지 않았다.")
        return
    orig, rep = seen(ctx.orig), seen(ctx.rep)
    in_orig = original_names(ctx.orig)
    in_rep = shown(rep)
    kept = set(in_rep)
    missing = [n for n in in_orig if n not in kept]

    m = ctx.metrics
    m["images_original"] = len(in_orig)
    m["images_kept"] = len(in_orig) - len(missing)
    m["images_missing"] = missing
    # 기록만 한다 - 원본에 없던 그림 자리 (모델이 더한 것)
    m["images_new"] = [n for n in in_rep if n not in set(in_orig)]
    # 기록만 한다 - 원본 문서에는 있지만 원본을 걷는 동안 보이지 않은 것 ([증권사] 탭 등)
    m["images_not_in_original"] = [n for n in orig if n not in set(in_orig)]
    # 기록만 한다 - 생성 쪽에서 처음 보인 상자 [x, y, w, h] 와 그 화면
    m["images_box"] = {n: {"box": rep[n].get("box"), "screen": ctx.screen(rep[n].get("visit"))}
                       for n in in_rep}
    if missing:
        ctx.fatal_(
            "L", None,
            "원본에서 보인 그림 자리 %d개 중 %d개가 생성물에서 보이지 않는다: %s. %s 검사기는 "
            "원본의 aria-label 이름을 그대로 가진 role=\"img\" 요소가 걷는 동안 (정답 경로 · "
            "reveal) 그려져 보이는지 본다."
            % (len(in_orig), len(missing), ", ".join(missing), RULE),
            missing=missing)
