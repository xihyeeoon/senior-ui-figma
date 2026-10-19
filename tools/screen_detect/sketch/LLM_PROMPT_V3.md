# LLM 시안 프롬프트 v3 (탐색용 시안 — 조립 설계 전, 2026-10-19 "스크린샷만")

`llm_assemble.py --inputs strict --prompt v3` 가 `---` 아래 글을 그대로 보내고 `{{…}}` 자리만 채운다. LLM_PROMPT_V2.md 와
다른 점: 규칙 11 (줄 · 카드 끝 꺾쇠는 그림 자리가 아니라 글자로) 하나를 더했다 - 의미 층 v2 가 꺾쇠에도 icon 을 붙여 규칙 8 로
X 그림 자리가 늘어난 것을 조립 규칙으로 다룬다 (10/19 연구자 결정, 어느 앱에나 같은 뜻인 일반 규칙).

---
너는 모바일 앱 화면 한 장을 HTML 로 다시 짜는 사람이다. 아래는 스크린샷 한 장에서 검출 · 분류한 요소 목록과 묶음(구역)
정보다. 이 화면을 HTML `<section>` 하나로 다시 짜라.

화면: {{CAPTURES}} (캡처 파일 이름. 여럿이면 한 화면을 스크롤하며 찍어 이어 붙인 것이다)
화면 크기: 가로 390px, 세로 {{HEIGHT}}px (CSS px). 아래 좌표는 모두 이 크기 기준 [x, y, 가로, 세로] 다.

## 지킬 것
1. 목록에 있는 요소만 쓴다. 목록에 없는 글 · 버튼 · 그림을 새로 만들지 마라. 목록의 요소는 하나도 빠뜨리지 말고, 각 요소를
   나타내는 HTML 요소에 `data-src="<요소 id>"` 를 그대로 달아라. 한 id 는 한 번만 쓴다.
2. 글이 든 박스 요소와 그 안의 글 줄 요소(글 줄의 in_box 가 그 박스 id)는 둘 다 쓴다 - 박스는 감싸는 요소로, 글 줄은 그 안의
   글로 (예: `<button data-src="b18" data-action="transfer"><span data-src="t6">이체</span></button>`). 글은 목록의 text 를
   그대로 쓰고 고치거나 늘리지 마라 (잘린 글을 채우지 마라).
3. 배치는 절대 위치가 아니라 묶음을 살린 흐름 배치(flex · grid)로 하라. 구역 목록(regions - 바탕 상자, parent 로 나무)을 묶음의
   근거로 쓰되, 그림과 다르면 그림을 따르고 그 차이를 HTML 주석(`<!-- … -->`)으로 적어라. 띠 목록(bands - 화면 너비의 바탕
   조각)은 화면을 위아래로 나누는 경계로만 참고하라.
4. kind 가 image 인 요소는 `<div class="pic" role="img" aria-label="<image_name>" data-src="…">` 로 쓴다 (class pic 은 회색 X
   상자로 그려진다 - 그림을 그리지 마라). image_name 이 없으면 aria-label 을 비워 둔다.
5. 누를 수 있는 것(pressable 이 true 이거나 kind 가 button · link · back_close · tab · choice · keypad_key)은 `<button>` 에
   `data-action="<짧은 영어 이름>"` 을 지어 단다. 버튼 안에 또 누를 수 있는 것이 있으면 안쪽은 `<div role="button">` 으로 쓴다
   (버튼 안에 버튼을 넣지 마라). kind 가 input 이면 테두리 있는 `<div>` 로 쓴다. 누른 뒤 어느 화면으로 가는지는 쓰지 마라 -
   주어지지 않았다 (화면 이동은 따로 붙인다).
6. 색 · 글자 크기 · 둥근 모서리는 그림에서 대략 맞춰라. 꾸밈은 `style` 속성으로만 쓴다 - `<style>` · `<script>` · 외부 파일 ·
   그림 파일을 쓰지 마라.
7. kind 가 system (상태바) 인 것은 목록에 없다 - 상태바를 새로 그리지 마라.
8. icon 이 있는 요소는 그 요소 안에 `<div class="pic" role="img" aria-label="<icon.name>">` 을 넣는다 (누를 수 있는 요소면
   그 button 안에). kind 가 image 인 요소는 규칙 4 대로 쓰고 icon 을 따로 넣지 않는다.
9. text_is_icon 이 true 인 요소는 OCR 글을 쓰지 않는다 - 그 자리에 규칙 8 의 그림 자리만 둔다 (data-src 는 그대로).
10. text_fixed 가 있는 요소는 text 대신 text_fixed 를 글로 쓰고, 원래 text 를 `data-ocr="<text>"` 로 단다.
11. 줄 · 카드 끝에서 다음으로 넘어감을 알리는 방향 표시 (›, ⌄, ⌃ 같은 꺾쇠) 는 icon 이 있어도 그림 자리를 만들지 않고
    글자 › (또는 ⌄ · ⌃) 로 둔다 (규칙 8 · 9 보다 앞선다. data-src 는 그대로 그 요소에 단다). 새로고침 · 고정 핀처럼 뜻이 있는
    아이콘은 그대로 그림 자리다. 꺾쇠인지는 mark 그림과 icon.shape 를 보고 정한다.

## 그림
{{IMAGES}}
위 그림은 화면 전체를 폭 600 으로 줄이고 요소마다 테두리와 mark 번호를 적은 것이다 (요소 목록의 mark 와 같다).

## 요소 (한 줄에 하나, JSON)
id · mark · kind (의미 층: button · link · back_close · tab · choice · input · keypad_key · image · text) · pressable · text ·
image_name · group (같은 무리) · in_box (이 글 줄을 담은 박스 요소 id) · region (든 구역 id) · box ·
icon (담은 아이콘 · 로고 {name, shape} 또는 null) · text_is_icon (OCR 글이 아이콘을 글자로 잘못 읽은 것인가) ·
text_fixed (그림에 보이는 대로 고친 글 또는 null)
{{ELEMENTS}}

## 구역 (바탕 상자, 한 줄에 하나)
{{REGIONS}}

## 띠 (화면 너비 바탕 조각)
{{BANDS}}

## 답
`<section>` 하나만 ```html 블록 하나에 담아 답하라. 설명 글은 쓰지 마라.
