# 스크린샷 → 요소 검출 시험 D2 (2026-10-12)

더미앱 A1 이체 캡처(`inputs/captures/transfer`)를 검출해, 원본 재현 HTML(`inputs/original_transfer.html`)을 원본 흐름(`flows/original.json`)대로 걸어 얻은 정답지(`truth.json`)와 글 · 이름으로 견준 것이다. 만든 스크립트: `tools/screen_detect/` (README.md). 단위 13개 - 스크롤 조각은 이은 화면 하나로 센다 (stitched/).

- 검출: OmniParser v2 `icon_detect_v3` (YOLOv9-E), 설명: `icon_caption` (Florence-2, `<CAPTION>`), OCR: PaddleOCR 3.7.0 (PP-OCRv5_server_det + korean_PP-OCRv5_mobile_rec)
- 장치: NVIDIA GeForce RTX 4070 SUPER (torch 2.11.0+cu128, CUDA) · OCR gpu:0 · CPU Intel(R) Core(TM) i7-14700
- 설정: 박스 점수 0.10, NMS IoU 0.3, 겹친 박스 정리 0.7, 검출 입력 640, OCR 점수 0.5 미만 버림
- 한 장당 평균 (모델을 올린 뒤): OCR 0.17초 · 검출 0.13초 · 설명 0.73초


## 1. 캡처 ↔ 상태 짝 제안 (연구자 확인용)

글이 가장 많이 겹치는 상태. 점수 = F1(재현 R, 정밀 P). `덮개` 는 그 상태만의 글이 70% 이상 찾아져 F1 1위 대신 앞세운 것이다 (compare.pairing). `동점` 은 1 · 2위의 F1 이 같다 - 글로는 가를 수 없다. captures.json 은 만들거나 고치지 않았다. 상태 이름의 `~n` 은 그 걸음의 n 번째 동작 뒤, `bank+tab-sec` 은 흐름 밖의 [증권사] 탭, `error:` 는 오류 경로의 오류 상태다.

| 캡처 | 제안 상태 | 화면 | 점수 (R / P) | 그 상태만의 글 |  | 2위 |
|---|---|---|---|---|---|---|
| home(01a+01b+01c) | home | home | 0.95 (0.98 / 0.93) | 0.98 |  | amount 0.09 |
| 02 | recipient | recipient | 0.88 (0.90 / 0.87) | 1.00 |  | account 0.38 |
| 03 | account | account | 0.93 (1.00 / 0.88) | - |  | account#2 0.56 |
| 04 | account#2 | account | 0.97 (1.00 / 0.94) | - |  | amount~1 0.91 |
| bank(05a+05b+05c) | bank | bank | 0.90 (1.00 / 0.81) | 1.00 |  | account 0.19 |
| bank-tab-sec(06a+06b+06c) | bank+tab-sec | bank | 0.89 (1.00 / 0.80) | 1.00 |  | account 0.22 |
| 07 | amount | amount | 1.00 (1.00 / 1.00) | - |  | confirm~1 0.94 |
| 07a | amount | amount | 0.98 (0.96 / 1.00) | - | 동점 | confirm~1 0.98 |
| 08 | confirm | confirm | 0.93 (1.00 / 0.88) | 1.00 |  | amount 0.26 |
| 09a | password | password | 0.96 (0.93 / 1.00) | 1.00 |  | account#2 0.80 |
| 09b | password | password | 0.96 (0.93 / 1.00) | 1.00 |  | account#2 0.80 |
| 10 | done | done | 0.93 (0.88 / 1.00) | 1.00 |  | error:wrong-bank 0.35 |
| 11 | error:wrong-account | err-account | 0.51 (0.86 / 0.36) | 0.75 | 덮개 | amount~2 0.87 |

짝지어진 캡처가 없는 정답 상태: `amount~1`, `amount~2`, `confirm~1`, `error:wrong-bank`


## 2. 전체 합계 (짝지어진 상태 11개, 상태마다 그 캡처들을 합쳐서)

| 항목 | 값 | 메모 |
|---|---|---|
| 글 재현율 | 221/226 (98%) | 기호만인 줄 20개(‹ ✕ ⌄ ⌫ 등)는 분모에서 뺐다 |
| 과제 버튼 (글 있는 것) | 7/7 (100%) | 그중 검출 박스 안의 글로 찾은 것 5 · 아이콘만 0 |
| 과제 밖 입구 - 글 있는 것 | 24/24 (100%) | 그중 박스 안 17 |
| 과제 밖 입구 - 아이콘만 | 7개 | 판정 없음 - 곁 설명은 5절 |
| 선택지 값 (글 있는 것) | 102/102 (100%) | 그중 박스 안 102 · 글 없는 값 0 |
| 그림 자리 | 정답 90 대 후보 164 | 후보 = 글 없는 박스(아이콘) + 칸 안의 그림 후보(img_candidate). 짝지은 단위들의 합 |
| 로고 이름 맞음 | 64/67 | 은행 · 증권사 로고 - 정답 "<이름> 로고" 와 후보 이름이 같은 것 (5절) |
| 남는 박스 | 38 / 검출 박스 252 | 단위 13개의 합. 갈래: 덮개 뒤 14 · 고정 띠 12 · 그 밖 12 (flags.py 의 표시) |
| 박스 재현율 | 버튼 5/7 (71%) · 입구 17/24 (71%) · 선택지 102/102 (100%) · 입력칸 2/3 (67%) | 글 있는 정답 항목 가운데 그 글을 감싸는 검출 박스가 있는 비율 (글은 OCR 로 찾았어도) |

### 상태별

| 상태 | 캡처 | 글 | 과제 버튼 | 입구 (글 · 아이콘만) | 선택지 값 | 그림 자리 대 후보 | 남는 박스 |
|---|---|---|---|---|---|---|---|
| home | home(01a+01b+01c) | 49/50 (98%) | 1/1 (100%) | 16/16 (100%) · 아이콘 5 | - | 19 대 30 | 7 |
| recipient | 02 | 9/10 (90%) | 1/1 (100%) | 4/4 (100%) · 아이콘 2 | - | 3 대 3 | 0 |
| account | 03 | 7/7 (100%) | 1/1 (100%) | - · 아이콘 0 | - | 0 대 4 | 3 |
| account#2 | 04 | 17/17 (100%) | 1/1 (100%) | - · 아이콘 0 | 10/10 (100%) | 0 대 4 | 2 |
| bank | bank(05a+05b+05c) | 43/43 (100%) | 1/1 (100%) | - · 아이콘 0 | 38/38 (100%) | 38 대 44 | 5 |
| bank+tab-sec | bank-tab-sec(06a+06b+06c) | 34/34 (100%) | - | - · 아이콘 0 | 29/29 (100%) | 29 대 38 | 7 |
| amount | 07, 07a | 23/23 (100%) | - | 1/1 (100%) · 아이콘 0 | 15/15 (100%) | 0 대 13 | 3 |
| confirm | 08 | 13/13 (100%) | 1/1 (100%) | - · 아이콘 0 | - | 1 대 4 | 1 |
| password | 09a, 09b | 13/14 (93%) | - | - · 아이콘 0 | 10/10 (100%) | 0 대 16 | 2 |
| done | 10 | 7/8 (88%) | - | 3/3 (100%) · 아이콘 0 | - | 0 대 2 | 1 |
| error:wrong-account | 11 | 6/7 (86%) | 1/1 (100%) | - · 아이콘 0 | - | 0 대 6 | 7 |

## 3. 캡처별

| 캡처 | 상태 | 글 | 과제 버튼 | 입구 (글 · 아이콘만) | 선택지 값 | 그림 자리 대 글 없는 박스 + 칸 안 후보 | 남는 박스 / 박스 | 정답에 없는 OCR 글 | 닻 (움직임/위/아래) |
|---|---|---|---|---|---|---|---|---|---|
| home(01a+01b+01c) | home | 49/50 (98%) | 1/1 (100%) | 16/16 (100%) · 아이콘 5 | - | 19 대 15 + 15 | 7 / 42 | 4 | 36/3/4 |
| 02 | recipient | 9/10 (90%) | 1/1 (100%) | 4/4 (100%) · 아이콘 2 | - | 3 대 3 + 0 | 0 / 8 | 2 | 0/7/0 |
| 03 | account | 7/7 (100%) | 1/1 (100%) | - · 아이콘 0 | - | 0 대 4 + 0 | 3 / 8 | 1 | 0/5/1 |
| 04 | account#2 | 17/17 (100%) | 1/1 (100%) | - · 아이콘 0 | 10/10 (100%) | 0 대 4 + 0 | 2 / 12 | 1 | 0/5/1 |
| bank(05a+05b+05c) | bank | 43/43 (100%) | 1/1 (100%) | - · 아이콘 0 | 38/38 (100%) | 38 대 7 + 37 | 5 / 49 | 10 | 38/5/0 |
| bank-tab-sec(06a+06b+06c) | bank+tab-sec | 34/34 (100%) | - | - · 아이콘 0 | 29/29 (100%) | 29 대 9 + 29 | 7 / 44 | 9 | 28/5/0 |
| 07 | amount | 23/23 (100%) | - | 1/1 (100%) · 아이콘 0 | 15/15 (100%) | 0 대 7 + 0 | 2 / 21 | 0 | 0/4/6 |
| 07a | amount | 22/23 (96%) | - | 1/1 (100%) · 아이콘 0 | 15/15 (100%) | 0 대 6 + 0 | 1 / 21 | 0 | 0/4/6 |
| 08 | confirm | 13/13 (100%) | 1/1 (100%) | - · 아이콘 0 | - | 1 대 3 + 1 | 1 / 6 | 2 | 0/6/5 |
| 09a | password | 13/14 (93%) | - | - · 아이콘 0 | 10/10 (100%) | 0 대 8 + 0 | 1 / 12 | 0 | 0/2/1 |
| 09b | password | 13/14 (93%) | - | - · 아이콘 0 | 10/10 (100%) | 0 대 8 + 0 | 1 / 12 | 0 | 0/2/1 |
| 10 | done | 7/8 (88%) | - | 3/3 (100%) · 아이콘 0 | - | 0 대 2 + 0 | 1 / 6 | 0 | 0/4/2 |
| 11 | error:wrong-account | 6/7 (86%) | 1/1 (100%) | - · 아이콘 0 | - | 0 대 5 + 1 | 7 / 11 | 14 | 0/5/2 |

캡처별 분모는 그 상태의 전부다 - 스크롤한 캡처 한 장에는 일부만 보이므로 낮게 나온다. 닻은 자리를 맞추는 데 쓴 글 수(스크롤과 함께 움직이는 것 / 창 위에 고정 / 창 아래에 고정)다.


## 4. 놓친 것

글 있는 항목 가운데 (가) 짝지어진 캡처 어디에서도 못 찾은 것, (나) 다른 캡처에서는 찾았지만 자리상 이 캡처 안이었는데 못 찾은 것. (가) 가 먼저, 그다음 못 찾은 캡처 수 순. `자리상 안` 은 정답 자리를 캡처 위로 옮긴 대강의 판단이다 (Frame). `가장 비슷한 OCR` 은 못 찾은 캡처에서 가장 가까웠던 OCR 글과 그 비슷함이다 (두 글자 이하는 같아야 찾은 것이라 0.79 로 자른다).

| # | 종류 | 항목 | 상태 | 어디서도 못 찾음 | 자리상 안인데 못 찾은 캡처 | 찾은 캡처 | 가장 비슷한 OCR |
|---|---|---|---|---|---|---|---|
| 1 | 글 | 67 | password | 예 | 09a, 09b | - | 767 (0.79) |
| 2 | 글 | 67 | done | 예 | 10 | - | 567 (0.79) |
| 3 | 글 | 계좌번호[110234567891] | error:wrong-account | 예 | 11 | - | (이은 줄) (0.56) |
| 4 | 글 | 땡겨요 | home | 예 | home(01a+01b+01c) | - | 팽겨요 (0.67) |
| 5 | 글 | 67 | recipient | 예 | - | - | 767 (0.79) |

## 5. 그림 자리

### (a) 상태별 정답 수 대 후보 수

후보 = 글 없는 박스(검출기 박스 · 아이콘으로 바꾼 OCR 자리) + 칸 안의 그림 후보.

| 상태 | 정답 그림 자리 | 글 없는 박스 | 칸 안 후보 | 그중 이름 붙은 것 |
|---|---|---|---|---|
| home | 19 | 15 | 15 | 0 |
| recipient | 3 | 3 | 0 | 0 |
| account | 0 | 4 | 0 | 0 |
| account#2 | 0 | 4 | 0 | 0 |
| bank | 38 | 7 | 37 | 38 |
| bank+tab-sec | 29 | 9 | 29 | 27 |
| amount | 0 | 13 | 0 | 0 |
| confirm | 1 | 3 | 1 | 0 |
| password | 0 | 16 | 0 | 0 |
| done | 0 | 2 | 0 | 0 |
| error:wrong-account | 0 | 5 | 1 | 0 |

### (b) 로고 이름 - 정답 "<이름> 로고" 대 후보 이름 (자동 판정)

둘 다 같은 규칙("<칸 글> 로고")으로 만든 이름이므로 같으면 맞음으로 센다. 맞음 64/67.

| 못 맞은 정답 이름 | 상태 |
|---|---|
| 아이엠뱅크(대구) 로고 | bank |
| 유진투자증권 로고 | bank+tab-sec |
| LS증권 로고 | bank+tab-sec |

정답에 없는 후보 이름 (OCR 이 칸 글을 다르게 읽은 것 등): 아이엠뱅크(대. 로고


### (c) 아이콘 - 정답 이름 대 OmniParser 설명 (판정하지 않는다)

로고가 아닌 그림 자리 · 아이콘 입구마다 정답 자리를 캡처 위로 옮겨(Frame) 곁의 후보를 고른 것이다. `ocr` 은 아이콘으로 바꾼 OCR 글. 자리가 맞지 않을 수 있으니 id 를 확인 그림(overlay/)에서 본다.

| 상태 | 종류 | 정답 이름 | 후보 | OmniParser 설명 | ocr |
|---|---|---|---|---|---|
| home | 아이콘 입구 | 알림 | home(01a+01b+01c) 01a:b0 | Notifications | 요 |
| home | 아이콘 입구 | 전체메뉴 | home(01a+01b+01c) 01a:b3 | Find and Replace | Q |
| home | 아이콘 입구 | 메시지 | home(01a+01b+01c) 01a:b1 | Open Document |  |
| home | 아이콘 입구 | 소비 상세 | home(01a+01b+01c) 01a:b22 | Forward | 7 |
| home | 아이콘 입구 | 지갑 | home(01a+01b+01c) 01a:b0 | Notifications | 요 |
| home | 그림 자리 | 메시지 아이콘 | home(01a+01b+01c) 01a:b1 | Open Document |  |
| home | 그림 자리 | 지갑 아이콘 | home(01a+01b+01c) 01a:b0 | Notifications | 요 |
| home | 그림 자리 | 알림 아이콘 | home(01a+01b+01c) 01a:b0 | Notifications | 요 |
| home | 그림 자리 | 전체메뉴 아이콘 | home(01a+01b+01c) 01a:b3 | Find and Replace | Q |
| home | 그림 자리 | 신한은행 로고 | home(01a+01b+01c) 01a:i1 | Sending a message or message. |  |
| home | 그림 자리 | 체크카드 아이콘 |  - | - |  |
| home | 그림 자리 | 땡겨요 쿠폰 아이콘 | home(01a+01b+01c) 01a:i3 | a hamburger or sandwich. |  |
| home | 그림 자리 | 오늘 쓴 돈 아이콘 | home(01a+01b+01c) 01b:i9 | a calendar or scheduling function. |  |
| home | 그림 자리 | SOL패밀리 아이콘 |  - | - |  |
| home | 그림 자리 | 급여클럽+ 아이콘 | home(01a+01b+01c) 01c:i1 | a stop or close button. |  |
| home | 그림 자리 | 내 카드 승인내역 아이콘 | home(01a+01b+01c) 01c:i0 | a trash bin or trash bin. |  |
| home | 그림 자리 | 신한카드 아이콘 | home(01a+01b+01c) 01c:i4 | a credit card or payment application. |  |
| home | 그림 자리 | 신한투자증권 아이콘 | home(01a+01b+01c) 01c:i2 | a graph or chart. |  |
| home | 그림 자리 | 신한라이프 아이콘 | home(01a+01b+01c) 01c:i5 | Adding a new item or creating a new document. |  |
| home | 그림 자리 | 홈 아이콘 | home(01a+01b+01c) 01c:b16 | Home |  |
| home | 그림 자리 | 금융 아이콘 | home(01a+01b+01c) 01c:i7 | a video file. |  |
| home | 그림 자리 | 상품 아이콘 | home(01a+01b+01c) 01c:i6 | a shopping or shopping cart function. |  |
| home | 그림 자리 | 혜택 아이콘 | home(01a+01b+01c) 01c:i8 | a tool or function related to a tool or toolbox. |  |
| home | 그림 자리 | 주식 아이콘 | home(01a+01b+01c) 01c:i9 | a graph or chart. |  |
| recipient | 아이콘 입구 | 받는 사람 관리 | 02 b5 | Right triangle |  |
| recipient | 아이콘 입구 | 검색 | 02 b0 | Search function. | Q |
| recipient | 그림 자리 | 받는 사람 관리 아이콘 | 02 b5 | Right triangle |  |
| recipient | 그림 자리 | 검색 아이콘 | 02 b0 | Search function. | Q |
| recipient | 그림 자리 | 카메라 아이콘 | 02 b6 | Camera functionality. |  |
| confirm | 그림 자리 | 신한 로고 |  - | - |  |
| password | 글 없는 입력칸 | pw-dots |  - | - |  |

## 6. 아이콘으로 바꾼 OCR 글 (D2 규칙 1)

`잘못` 은 그 글이 짝지은 상태의 보이는 글과 같은 것 (진짜 글을 아이콘으로 바꿨다).

| 단위 | 캡처 | OCR 글 | 점수 | 박스 | 설명 | 잘못 |
|---|---|---|---|---|---|---|
| home(01a+01b+01c) | 01a | 요 | 0.6834 | 01a:b0 | Notifications |  |
| home(01a+01b+01c) | 01a | Q | 0.9917 | 01a:b3 | Find and Replace |  |
| home(01a+01b+01c) | 01a | 7 | 0.9721 | 01a:b21 | Forward |  |
| home(01a+01b+01c) | 01a | 7 | 0.9804 | 01a:b22 | Forward |  |
| home(01a+01b+01c) | 01b | L | 0.9894 | 01b:b18 | - |  |
| home(01a+01b+01c) | 01c | 7 | 0.9915 | 01c:b18 | Forward |  |
| home(01a+01b+01c) | 01c | L | 0.9107 | 01c:b19 | Forward |  |
| home(01a+01b+01c) | 01c | 7 | 0.9915 | 01c:b20 | Forward |  |
| 02 | 02 | Q | 0.9978 | b0 | Search function. |  |
| 03 | 03 | × | 0.9652 | b7 | Strikethrough |  |
| 04 | 04 | × | 0.9652 | b10 | Strikethrough |  |
| 04 | 04 | ← | 0.9998 | b9 | Back |  |
| bank(05a+05b+05c) | 05a | × | 0.9878 | 05a:b23 | Close |  |
| bank(05a+05b+05c) | 05a | × | 0.8645 | 05a:b17 | closing or cancel action. |  |
| bank(05a+05b+05c) | 05b | × | 0.9878 | 05b:b23 | - |  |
| bank(05a+05b+05c) | 05b | × | 0.8472 | 05b:b17 | - |  |
| bank(05a+05b+05c) | 05c | × | 0.9878 | 05c:b20 | - |  |
| bank(05a+05b+05c) | 05c | × | 0.9488 | 05c:b14 | - |  |
| bank(05a+05b+05c) | 05c | E3 | 0.6698 | 05c:b21 | A Chinese translation or translation function. |  |
| bank-tab-sec(06a+06b+06c) | 06a | × | 0.9963 | 06a:b24 | Close |  |
| bank-tab-sec(06a+06b+06c) | 06a | × | 0.8645 | 06a:b17 | closing or cancel action. |  |
| bank-tab-sec(06a+06b+06c) | 06b | × | 0.9878 | 06b:b23 | - |  |
| bank-tab-sec(06a+06b+06c) | 06b | × | 0.8372 | 06b:b15 | - |  |
| bank-tab-sec(06a+06b+06c) | 06c | × | 0.9878 | 06c:b20 | - |  |
| bank-tab-sec(06a+06b+06c) | 06c | × | 0.9488 | 06c:b14 | - |  |
| 07 | 07 | × | 0.8946 | b7 | closing or cancel action. |  |
| 07 | 07 | L | 0.9061 | b18 | expand or dropdown menu. |  |
| 07 | 07 | ← | 0.9999 | b16 | Back |  |
| 07a | 07a | × | 0.8946 | b8 | closing or cancel action. |  |
| 07a | 07a | L | 0.9061 | b17 | expand or dropdown menu. |  |
| 07a | 07a | ← | 0.9999 | b16 | Back |  |
| 08 | 08 | < | 0.9547 | b3 | Back |  |
| 08 | 08 | × | 0.9652 | b1 | closing or cancel action. |  |
| 09a | 09a | × | 0.9111 | b4 | closing or cancel action. |  |
| 09b | 09b | × | 0.9111 | b5 | closing or cancel action. |  |
| 11 | 11 | × | 0.9963 | b7 | Close |  |
| 11 | 11 | × | 0.8426 | b6 | closing or cancel an action. |  |
| 11 | 11 | ← | 0.9989 | b10 | Back |  |

## 7. 스크롤 잇기 (stitched/)

조각마다 이은 좌표의 세로 자리(offset), 앞 조각과의 어긋남과 그것을 정한 방법(닻 수), 겹친 줄, 위 · 아래 고정 띠. 확인 그림은 `overlay/stitched/<화면>.png`.

| 화면 | 조각 | offset | 어긋남 | 방법 (닻) | 겹친 줄 | 위 띠 | 아래 띠 |
|---|---|---|---|---|---|---|---|
| home | 01a | 0 | - | - | 0 | 0 | 152 |
| home | 01b | 1759 | 1759 | boxes (1) | -81 | 0 | 152 |
| home | 01c | 2232 | 473 | text (13) | 1205 | 0 | 0 |
| bank | 05a | 0 | - | - | 0 | 0 | 25 |
| bank | 05b | 1195 | 1195 | text (1) | 113 | 497 | 0 |
| bank | 05c | 2390 | 1195 | text (3) | 138 | 497 | 0 |
| bank-tab-sec | 06a | 0 | - | - | 0 | 0 | 0 |
| bank-tab-sec | 06b | 1319 | 1319 | boxes (3) | 14 | 497 | 0 |
| bank-tab-sec | 06c | 1543 | 224 | text (12) | 1109 | 497 | 0 |

| 화면 | 크기 | 합친 요소 | 고정 띠라 뺀 요소 | 이은 뒤 이름 붙인 로고 |
|---|---|---|---|---|
| home | 824x4062 | 29 | 31 | 0 |
| bank | 824x4220 | 10 | 31 | 2 |
| bank-tab-sec | 824x3373 | 33 | 29 | 1 |

## 8. 남는 박스 (단위별)

| 단위 | 정답 어디에도 닿지 않은 박스 (글 또는 [설명]) (표시) |
|---|---|
| home(01a+01b+01c) | 01a:b2 [WhatsApp], 01a:b5 [a triangle or "Play" function.] (고정 띠), 01a:b20 팽겨요, 01c:b18 [Forward], 01c:b5 [a stopwatch function.], 01c:b19 [Forward], 01c:b20 [Forward] |
| 02 | - |
| 03 | b3 [Play or Start.] (고정 띠), b5 [M0,0L9,0 4.5,5z], b7 [Strikethrough] |
| 04 | b3 [Play or Start.] (고정 띠), b10 [Strikethrough] |
| bank(05a+05b+05c) | 05a:b18 [Play or Start.] (고정 띠), 05a:b20 [closing or cancel a window or dialog.] (덮개 뒤), 05a:b22 [Decrease] (덮개 뒤), 05a:b23 [Close] (덮개 뒤), 05a:b24 누구에게 보낼까요? (덮개 뒤) |
| bank-tab-sec(06a+06b+06c) | 06a:b12 pay, 06a:b13 LS, 06a:b18 [Play or Start.] (고정 띠), 06a:b19 [closing or cancel a window or dialog.] (덮개 뒤), 06a:b22 [Decrease] (덮개 뒤), 06a:b23 누구에게 보낼까요? (덮개 뒤), 06a:b24 [Close] (덮개 뒤) |
| 07 | b4 [Play or Start.] (고정 띠), b19 [Strikethrough] |
| 07a | b4 [Play or Start.] (고정 띠) |
| 08 | b0 [Play or Start.] (고정 띠) |
| 09a | b0 [Right triangle] (고정 띠) |
| 09b | b4 [Right triangle] (고정 띠) |
| 10 | b4 [Play or Start.] (고정 띠) |
| 11 | b0 신한 (덮개 뒤), b3 다음 (덮개 뒤), b4 [closing or cancel a window or dialog.] (덮개 뒤), b5 [Play or Start.] (고정 띠), b6 [closing or cancel an action.] (덮개 뒤), b7 [Close] (덮개 뒤), b10 [Back] (덮개 뒤) |

## 9. 정답에 없는 OCR 글 (단위별)

더미앱에만 있는 글, 시트 뒤에 비친 화면의 글, 잘못 읽은 글이 섞여 있다.

| 캡처 | 글 |
|---|---|
| home(01a+01b+01c) | 팽겨요 · P · 푸 · 푸 |
| 02 | 8+ · L |
| 03 | 57 |
| 04 | 57 |
| bank(05a+05b+05c) | 누구에게 보낼까요? · NH · Sh · D · citi · Kbank · BNV · BiNV · BNV · SB |
| bank-tab-sec(06a+06b+06c) | 누구에게 보낼까요? · DAOL · meritz · MIRAEASSET · SK증권 · LS · pay · BiNV · NH |
| 07 | - |
| 07a | - |
| 08 | 517 · 0 |
| 09a | - |
| 09b | - |
| 10 | - |
| 11 | 누구에게 보낼까요? · \|100 · 신한 · 1 · 2 · 3 · 4 · 5 · 6 · 7 · 8 · 9 · 0 · 다음 |
