# LLM 시안 프롬프트 (탐색용 시안 — 조립 설계 전)

`llm_assemble.py` 가 `---` 아래 글을 그대로 보내고 `{{…}}` 자리만 채운다. 단위(화면)마다 한 번.

입력은 스크린샷 쪽 정보만이다 (10/19 연구자 결정 "스크린샷만") - 연구자가 쓴 이름표(captures.json 의 label)와 단위 이름
(stitch.py GROUPS 의 화면 이름)은 넣지 않고 캡처 파일 이름만 쓴다. 20261019-sketch 의 홈 실행은 이 고침 전 판이다
(prompt_sha 1b89fd0f58ff - 이름표가 들어 있었다).

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

## 그림
{{IMAGES}}
위 그림은 화면 전체를 폭 600 으로 줄이고 요소마다 테두리와 mark 번호를 적은 것이다 (요소 목록의 mark 와 같다).

## 요소 (한 줄에 하나, JSON)
id · mark · kind (의미 층: button · link · back_close · tab · choice · input · keypad_key · image · text) · pressable · text ·
image_name · group (같은 무리) · in_box (이 글 줄을 담은 박스 요소 id) · region (든 구역 id) · box
{{ELEMENTS}}

## 구역 (바탕 상자, 한 줄에 하나)
{{REGIONS}}

## 띠 (화면 너비 바탕 조각)
{{BANDS}}

## 답
`<section>` 하나만 ```html 블록 하나에 담아 답하라. 설명 글은 쓰지 마라.
