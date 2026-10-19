# 의미 층 프롬프트 v2 (2026-10-19, "스크린샷만")

`semantic.py --prompt v2` 가 이 파일을 읽어 첫 `---` 줄 **아래** 글을 그대로 모델에게 보낸다. `{{…}}` 자리는
semantic.py 가 채운다 - `{{UNIT}}` 단위 이름(strict 에서는 묶인 캡처 파일 이름), `{{FIXED}}` 규칙으로 이름이 붙은
로고 목록(strict 에서는 없음), `{{ELEMENTS}}` 요소 목록, `{{IMAGES}}` 그림 자리. v1(SEMANTIC_PROMPT.md)과 다른 점:
과제 이름 줄을 뺐다 (스크린샷만). 요소마다 칸 셋을 더했다 - icon (아이콘 · 로고를 담았으면 뜻 이름과 모양),
text_is_icon (OCR 글이 아이콘을 글자로 잘못 읽은 것인가), text_fixed (OCR 글이 그림과 다르면 그림에 보이는 글).

---
앱 화면 캡처에서 검출된 요소마다 역할을 적어라.

화면: {{UNIT}}

받는 것
- 요소 목록 (JSON, 한 줄에 요소 하나). 칸의 뜻:
  - id: 요소의 이름. 답에 그대로 쓴다.
  - mark: 첫 그림 위에 적힌 번호.
  - kind: 검출 종류 - box(검출 박스), text(OCR 글 줄), img_candidate(박스 안 그림 덩어리).
  - box: [x, y, w, h], 캡처 픽셀.
  - text: 그 자리에서 OCR 이 읽은 글. 박스는 안에 든 글을 이은 것.
  - ocr_guess: 아이콘을 OCR 이 글자로 읽은 것.
  - caption: 아이콘 설명 모델이 붙인 영어 설명.
  - name: 규칙으로 붙인 로고 이름 (없으면 null).
  - in_box: 이 요소를 담은 박스의 id.
  - near: 곁의 글 (inside 안에 든 글, row 같은 줄의 글, below 바로 아래 글, parent 담은 박스의 글).
  - flags: system_band(여러 캡처에서 같은 자리 · 같은 모습인 띠 - 상태바 등), behind_overlay(시트 · 팝업 뒤의 어두워진 화면).
  - 값이 없는 칸은 null 이다.
- 그림: 첫 그림은 화면 전체를 줄이고 요소마다 mark 번호를 적은 것이다. 그다음 그림들은 글 없는 박스 · 박스 안 그림 덩어리 · 한두 글자 글 · ocr_guess 가 있는 요소를 잘라 키운 것이고, 이름표에 mark 와 id 가 있다.

지키는 규칙
1. 요소 목록의 id 마다 답을 정확히 하나씩, 빠짐없이 낸다.
2. 목록에 없는 id 를 만들지 않는다. 요소를 합치거나 나누지 않는다.
3. ocr_guess · caption · name · near · flags 는 힌트일 뿐이다. 그림에 보이는 것으로 정한다. 힌트와 그림이 다르면 그림을 따른다.
4. image_name 은 그림에 보이는 것으로만 짓는다. 글이 잘려 보이면 보이는 데까지만 쓰고 뒷부분을 채우지 않는다. 무엇인지 알아볼 수 없으면 "알 수 없는 아이콘" 이라고 쓴다.
5. 아이콘 이름(image_name)은 그 아이콘이 가리키는 것으로 짓는다. 곁에 이름표 글(near 의 같은 박스 · 같은 줄 · 바로 아래 글)이 있으면 그 글을 쓴다 (예: 이름표 '혜택' → '혜택 아이콘'). 이름표가 없으면 보이는 모양으로 짓는다. 모양은 image_shape 칸에 따로 적는다 (예: '선물상자').
6. 고정값 목록에 있는 id 는 image_name 을 그 값 그대로 쓴다.
7. 무엇을 눌러야 하는지는 정하지 않는다. 누를 수 있게 생겼는지만 본다.
8. icon: 이 요소가 아이콘 · 로고를 담고 있으면 {"name": "<무엇> 아이콘" 또는 "<무엇> 로고", "shape": "<보이는 모양>"}, 아니면 null. 이름은 규칙 5 와 같이 짓는다. 누를 수 있는 아이콘이면 kind(button 등)는 그대로 두고 icon 을 채운다. kind 가 image 이면 icon 의 name · shape 는 image_name · image_shape 와 같게 쓴다.
9. text_is_icon: 요소의 OCR 글(text)이 실제로는 아이콘 모양을 글자로 잘못 읽은 것이면 true (예: 고정 핀을 '푸', 새로고침 화살표를 'C' 로 읽음), 아니면 false. true 이면 icon 도 채운다. 글이 없는 요소는 false.
10. text_fixed: OCR 글이 그림에 보이는 글과 다르게 읽혔으면 그림에 보이는 글 그대로 (예: '팽겨요' → '땡겨요'), 같으면 null. 보이는 글만 쓴다 - 잘린 글의 뒷부분을 짐작해 채우지 않는다. 고쳤으면 그 까닭을 note 에 짧게 적는다. text_is_icon 이 true 인 요소는 null.
11. JSON 하나만 답한다. 그 앞뒤에 다른 글을 붙이지 않는다.

답의 모양
{"elements": [{"id": "<id>", "pressable": true 또는 false, "kind": "<kind>", "group": "<무리 이름>" 또는 null, "image_name": "<이름>" 또는 null, "image_shape": "<모양>" 또는 null, "icon": {"name": "<이름>", "shape": "<모양>"} 또는 null, "text_is_icon": true 또는 false, "text_fixed": "<글>" 또는 null, "note": "<짧은 근거>"}]}

- kind 는 다음 가운데 하나다.
  - button: 버튼
  - link: 테두리 없는 글 링크, 또는 줄 전체가 누르는 곳인 것
  - back_close: 뒤로 · 닫기
  - tab: 탭
  - choice: 여럿 가운데 고르는 것
  - input: 입력칸
  - keypad_key: 숫자판의 키
  - image: 그림 · 아이콘 · 로고
  - text: 누르지 않는 글
  - system: 상태바 · 덮개 뒤처럼 이 화면의 요소가 아닌 것
- group: 같은 무리(한 목록의 선택지, 한 숫자판의 키, 한 줄의 탭 등)는 같은 이름을 쓴다. 무리가 없으면 null.
- image_name: kind 가 image 일 때만 "<무엇> 아이콘" 또는 "<무엇> 로고". 그 밖에는 null.
- image_shape: kind 가 image 일 때만 보이는 모양 (예: "선물상자"). 그 밖에는 null.
- note: 그렇게 정한 근거 한 줄.

고정값 (규칙으로 이름이 붙은 로고 - image_name 을 바꾸지 않는다)
{{FIXED}}

요소 목록
{{ELEMENTS}}

그림
{{IMAGES}}
