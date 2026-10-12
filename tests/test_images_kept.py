r"""그림 자리 보존 - 연구자 결정 2026-10-12.

원본의 로고 · 아이콘 자리(role="img" + aria-label "<무엇> 로고/아이콘", 회색 상자 pic -
test_image_slots.py)는 "이 위치에 이 크기로 이런 그림이 들어간다" 는 설계 정보다. 실행
20261008-131136 (시도 2) · 20261012-132226 (시도 1) 은 그것을 모두 지웠다 (role="img" 0개,
은행 로고 67개도). 생성 프롬프트에 그것을 지키라는 말이 없었다.

  .\.venv\Scripts\python.exe -m pytest tests/test_images_kept.py
"""
import pytest

import _api


# ===================================================================== #
# 프롬프트 - 기술 계약 한 줄과 세 프롬프트의 한 줄
# ===================================================================== #
CONTRACT_LINE = ("원본의 그림 자리 (role=\"img\" 와 aria-label 을 가진 요소 — 로고 · 아이콘 · "
                 "사진이 들어갈 자리) 는 지우지 마라. aria-label 은 원본 그대로 둔다. 위치 · 크기 · "
                 "묶음은 바꿔도 된다. 그림 자리는 CSS 로 크기를 준 상자로 그린다 (그림 파일 · 외부 "
                 "자원 · 이모지 · 글자로 흉내 내지 않는다). 이름 글을 곁에 더하는 것은 자유다. 새 "
                 "그림이 필요하면 같은 형식 (role=\"img\" + aria-label \"<무엇> 아이콘/로고/그림\") "
                 "으로 더해도 된다. 선택지마다 붙은 그림 자리 (은행 로고 등) 는 그 선택지마다 둔다.")
PIC_LINE = ("원본의 그림 자리 (로고 · 아이콘) 는 그림이 들어갈 자리를 뜻하는 설계 정보다. "
            "장식으로 보고 지우지 마라 — 위치 · 크기는 바꿔도 된다.")
MENU = "다만 없애지 마라."


@pytest.mark.parametrize("task", ["transfer", "bill"])
def test_the_prompts_carry_the_contract_line_and_the_menu_line(task):
    p = _api.prompt_module
    for t in (p.load_plan_template(task), p.load_template(task),
              p.load_refine_template(task)):
        flat = " ".join(t.split())
        assert flat.count(PIC_LINE) == 1
        # 메뉴 문장 바로 뒤의 줄이다
        assert flat.index(PIC_LINE) == flat.index(MENU) + len(MENU) + len(" - ")
    # 기술 계약(생성 · 재시도 · 다듬기가 함께 쓴다) - 과제 밖 입구 줄 바로 뒤
    for t in (p.load_template(task), p.load_refine_template(task)):
        flat = " ".join(t.split())
        assert flat.count(CONTRACT_LINE) == 1
        assert flat.index("흐름 명세의 걸음이나 `reveal` 로 닿을 수 있어야 한다. - "
                          + CONTRACT_LINE) >= 0
    assert CONTRACT_LINE not in " ".join(p.load_plan_template(task).split())
