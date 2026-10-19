# screen_detect — 스크린샷에서 UI 요소 검출 (시험 D1 · D2)

도구의 입력을 "사람이 만든 원본 HTML" 에서 "이미 찍어 둔 스크린샷" 쪽으로 옮길 수 있는지 보는
첫 시험의 **요소 층**이다 (계획: 1 요소 층 → 2 의미 층(LLM 이 역할) → 3 흐름 층(연구자가 전환을
적음) → 4 조립(재현 HTML)). 더미앱 A1 이체 캡처(`inputs/captures/transfer/*.png`, 19장)에서
박스 · 글 · 아이콘 설명을 뽑고, 원본 재현 HTML(`inputs/original_transfer.html`)을 걸어 얻은
정답지와 **글 · 이름으로** 견준다. 재설계 · 검사기 · 프롬프트는 건드리지 않는다.

| 파일 | 하는 일 |
|---|---|
| `detect.py` | PNG 마다 요소 목록 JSON + 확인 그림 (검출 · 설명 · OCR) |
| `truth.py` | 원본 재현 HTML 을 원본 흐름대로 걸어 상태마다 보이는 것을 모은다 (정답지) |
| `flags.py` | (D2.5) 요소에 표시를 단다 - 고정 띠(`system_band`) · 덮개 뒤(`behind_overlay`). 지우지 않는다 |
| `stitch.py` | (D2) 스크롤 조각을 한 장 좌표계로 잇는다 |
| `compare.py` | 캡처 ↔ 상태 짝 **제안**, 글 재현율 · 버튼 · 입구 · 선택지 · 그림 자리 · 박스 재현율 · 남는 박스 |
| `sweep.py` | (D2.5) 검출 설정마다 detect → flags → stitch → compare 를 돌려 한 표로 |
| `semantic.py` · `SEMANTIC_PROMPT.md` | (D3) 의미 층 - 요소마다 누를 수 있나 · 종류 · 무리 · 그림 이름을 LLM 이 붙인다 |
| `flow.py` · `FLOW_PROMPT.md` · `compare_flow.py` | (D4) 흐름 층 - 캡처 짝마다 누른 것을 LLM 이 추정하고 원본의 실제 연결과 견준다 |

결과: D1 `results/detect/20261012/`, D2 `results/detect/20261012-d2/`, D2.5
`results/detect/20261013-d25/<설정>/` (**D3 의 입력은 `final/`**) — `<캡처>.json`, `overlay/<캡처>.png`,
`_run.json`(장치 · 판 · 시간 · 설정), `truth.json`, `summary.md`, `compare.json`, (D2~) `stitched/<화면>.json`
· `overlay/stitched/<화면>.png`, (D2.5) `_flags.json` · `_sweep.json`. 앞 시험의 결과는 고치지 않는다.

**설정 시험(sweep)의 확인 그림은 `final/` 것만 커밋한다.** 다른 설정 폴더는 json · summary 만 남긴다 (2026-10-13 연구자 결정 - D2.5 의 다른 설정 폴더에서 `overlay/` 를 지웠다. 다시 보려면 `sweep.py <설정>` 으로 다시 만든다).

## 설치 (전부 레포 밖)

레포에는 우리 스크립트 · 결과 · 이 설명만 둔다. 환경 · 검출기 코드 · 가중치 · 모델 캐시는
`C:\Users\xihye\` 아래 따로 둔다.

| 무엇 | 자리 |
|---|---|
| 파이썬 환경 (3.12) | `C:\Users\xihye\venvs\detect` |
| OmniParser 코드 (`util/yolov9.py` 만 쓴다) | `C:\Users\xihye\tools\OmniParser` (commit `3540212`) |
| OmniParser v2 가중치 | `C:\Users\xihye\tools\OmniParser-v2.0-weights\{icon_detect_v3, icon_caption}` |
| Florence-2 처리기 · 모델 코드 (HF 캐시) | `C:\Users\xihye\tools\hf` (`microsoft/Florence-2-base@5ca5edf`) |
| PaddleOCR 모델 | `C:\Users\xihye\tools\paddlex\official_models\{PP-OCRv5_server_det, korean_PP-OCRv5_mobile_rec}` |

```powershell
uv venv C:\Users\xihye\venvs\detect --python 3.12
$py = "C:\Users\xihye\venvs\detect\Scripts\python.exe"
uv pip install --python $py torch torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install --python $py "transformers==4.45.2" timm einops huggingface_hub opencv-python-headless pillow playwright==1.62.0
uv pip install --python $py "paddlepaddle-gpu==3.2.0" --index-url https://www.paddlepaddle.org.cn/packages/stable/cu126/ --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match
uv pip install --python $py "paddleocr>=3.2,<4"
git clone --depth 1 https://github.com/microsoft/OmniParser.git C:\Users\xihye\tools\OmniParser
# 가중치: huggingface.co/microsoft/OmniParser-v2.0 의 icon_detect_v3/{model.pt,LICENSE},
#         icon_caption/{model.safetensors,config.json,generation_config.json,LICENSE}
#         를 C:\Users\xihye\tools\OmniParser-v2.0-weights\ 아래 같은 이름으로 받는다.
#         icon_detect/ (v1, AGPL) 는 받지 않는다.
```

Florence-2 처리기와 PaddleOCR 모델은 처음 돌릴 때 위 캐시 자리로 저절로 받아진다 (`detect.py` 가
`HF_HOME` · `PADDLE_PDX_CACHE_HOME` 을 그 자리로 둔다). Playwright 의 chromium 은 사용자 캐시
(`%LOCALAPPDATA%\ms-playwright`)에 이미 있는 것을 쓴다.

**paddle 과 torch 는 한 프로세스에 올리지 못한다.** 둘이 싣는 cuDNN DLL 이 달라 나중에 올리는 쪽이
`WinError 127` 로 죽는다 (paddlex → modelscope 가 torch 를 부른다). 그래서 `detect.py` 는 OCR 을
torch 를 막은 자식 프로세스(`--stage ocr`)에서 돌린다. paddle 은 "cuDNN 9.9 로 빌드했는데 9.5 가
있다" 고 경고하지만 결과는 나온다.

## 돌리기

```powershell
$py = "C:\Users\xihye\venvs\detect\Scripts\python.exe"
$out = "results/detect/20261013-d25/final"
& $py tools/screen_detect/detect.py --out $out            # 19장 → *.json, overlay/, _run.json
& $py tools/screen_detect/flags.py --dir $out             # → 요소의 flags, _flags.json
& $py tools/screen_detect/stitch.py --dir $out            # → stitched/, overlay/stitched/
& $py tools/screen_detect/truth.py --out $out/truth.json
& $py tools/screen_detect/compare.py --dir $out           # → summary.md, compare.json
# 설정 시험 전체 (D2.5): 설정마다 위 순서 → results/detect/20261013-d25/<설정>/, 맨 위 summary.md
& $py tools/screen_detect/sweep.py                        # 한 번에 하나씩 바꾼 설정 + 묶음
& $py tools/screen_detect/sweep.py final                  # detect.py 기본값으로
```

D1 은 `results/detect/20261012` 로 flags · stitch 없이(커밋 `4c1e576` 의 detect.py), D2 는
`results/detect/20261012-d2` 로 flags 없이(D2 의 detect.py 기본값 = 지금의 `--conf 0.05 --nms 0.1
--no-clahe --overlap omniparser`) 돌렸다.

`detect.py 01a 05a` 처럼 캡처 이름을 주면 그것만, `--out` 으로 다른 폴더에. 검출 설정 인자는
`--imgsz` · `--conf` · `--nms` · `--tiles` · `--clahe/--no-clahe` · `--classic/--no-classic` ·
`--overlap {omniparser,iou}` (D2.5 절). `--ocr-cache` 를 주면 OCR 결과를 그 파일에서 읽는다 (없으면 써 둔다).

### 설정 (D1 · D2 는 OmniParser 기본값, D2.5 부터 기본값이 바뀌었다)

| | D1 · D2 값 | D2.5 기본값 | 어디서 |
|---|---|---|---|
| 검출 점수 · NMS IoU · 입력 | 0.05 · 0.1 · 640 | **0.1 · 0.3** · 640 | `gradio_demo.py` · `util/utils.py` |
| 대비 올린 사본으로 한 번 더 | 안 함 | **함** (CLAHE) | (D2.5) |
| 겹친 박스 정리 | 한 박스가 다른 박스를 70% 넘게 덮으면(포함 포함) 큰 것을 버림, OCR 글 박스 안에 든 박스는 버림 | **IoU 0.7 을 넘을 때만** 큰 것을 버림 (칸 안에 아이콘이 있어도 칸을 남긴다), 글 안 박스는 같다 | `remove_overlap_new` |
| 글을 박스에 붙임 | 글 박스 넓이의 80% 가 검출 박스 안 (`text_in`, 여럿이면 가장 작은 박스) | `is_inside` |
| 설명 | 글 없는 박스만, 64x64 로 줄여 `<CAPTION>`, 20 토큰 | `get_parsed_content_icon` |
| OCR | 점수 0.5 미만 버림 (우리 값) | — |

OCR 글은 박스에 붙었든 아니든 `kind: "text"` 요소로 모두 남는다 — 글 재현율은 OCR 만 본다
(D2 부터는 아이콘으로 바꾼 것만 빠진다).

## D2 에서 바꾼 것 (2026-10-12)

**1. 아이콘을 글자로 읽은 OCR → 아이콘 박스** (`detect.icon_texts`). 짧은 글이 작은 정사각 자리에
혼자 있으면 글 요소에서 빼고 박스의 `ocr_guess` 로 옮긴다. 그 박스는 `text: null` 이고 설명이 붙는다 -
그 글이 든 검출 박스에 다른 글이 없으면 그 박스, 아니면 글 자리를 변마다 30% 넓힌 새 박스
(`source: "ocr_icon"`). 바꾼 목록은 JSON 의 `icon_from_ocr`.

| 조건 | 문턱값 | 왜 |
|---|---|---|
| 글 길이 | 두 글자 이하, 한글이 들었으면 한 글자 | 요청 |
| 글 박스 긴 변 | 64px 이하 | 요청의 예 |
| 가로 / 세로 | 0.85 ~ 1.18 | 요청의 예(0.75~1.33)로는 세로가 긴 숫자판 숫자(0.69~0.84)가 걸린다. 처음 규칙(0.85 하한, 숫자판 줄 규칙 없음)에서도 04 의 "7"(0.88)이 바뀌어 글 재현율 221 → 220, 선택지 102 → 101 로 떨어졌다. 아래 숫자판 줄 규칙을 더해 맞췄다 |
| 앞뒤에 붙은 글 | 같은 줄에서 모양이 맞지 않은 글과의 틈이 글 높이의 1.0 배 안이면 글 | "C 홍길동님" 의 C, "7월 소비 ↻" 의 ↻ 를 읽은 C |
| 탭 이름 줄 | 한 글자 한글이 같은 줄에 높이 비 0.8~1.25 의 한글을 두면 글 | "홈 금융 상품 혜택 주식" 의 홈 |
| 숫자판 줄 | 숫자가 같은 줄에 높이 비 0.8~1.25 의 숫자를 두면 글 | "7 8 9" 의 7 |

정답지로 맞춘 결과 글 재현율 221/226 · 선택지 102/102 로 D1 과 같고, 바꾼 38개 가운데 정답의 보이는
글과 같은 것은 없다 (summary.md 6절). 아직 글로 남은 아이콘: "P"(포인트 로고, 0.83), "푸"(고정 핀,
0.72~0.83), "8+"(받는 사람 관리, 1.28), 줄 끝 "<" · "L" · ✎ 를 읽은 "0"(앞 글에 붙음), 상태바 "57" · "767".

**2. 칸 안의 그림 자리 → `img_candidate`** (`detect.img_candidates`). 글이 든 검출 박스 안에서 글이
덮지 않은 그림 덩어리를 후보로 낸다. 정해진 규칙이고 LLM 을 쓰지 않는다.

| | 값 |
|---|---|
| 살펴보는 자리 | 박스를 짧은 변의 6% 안쪽으로 (둥근 모서리 · 테두리 빼기) |
| 그림 화소 | 가장자리 화소의 중앙값(칸 바탕색)과 채널 차 40 이상 |
| 덩어리 | 7px 팽창으로 이은 연결 요소, 가로 · 세로 모두 16px 이상, 살펴보는 자리의 가장자리에 닿지 않는 것 |
| 지우는 것 | 칸 안의 글 박스(4px 넓혀서)와 칸 안의 글 없는 박스(이미 아이콘) |
| 이름 | 같은 크기(±15%)의 글 든 칸이 6개 이상이고 캡처에 "은행" 또는 "증권" 글이 있으면 은행 · 증권사 칸으로 본다. 칸 아래쪽 45% 의 맨 아래 글이 칸 글, 가장 큰 덩어리가 `"<칸 글> 로고"` (그 칸에서는 칸 글만 지운다 - "NH" "Kbank" 같은 로고 안 글자는 로고의 일부). 로고가 이미 글 없는 박스로 잡혔으면 그 박스에 이름을 붙인다. 그 밖의 칸은 이름 없이 후보만 |

**3. 스크롤 조각 잇기** (`stitch.py`, `GROUPS` = 홈 01a~c · 은행 05a~c · 증권사 06a~c, 연구자가
정하는 묶음). 이웃한 두 조각의 고정 띠(같은 높이의 화소 줄이 같은 것 - 상태바 · 시트 머리 · 탭바)를
세고, 띠 밖의 같은 글 · 같은 x(±8px) · 같은 너비의 OCR 글을 닻으로 세로 어긋남을 정한다 (최빈값
±6px 안의 중앙값). 닻이 없으면 잘린 칸으로(앞 조각에서 아래가, 뒤 조각에서 위가 잘린 같은 x · 너비의
칸을 온전한 칸 높이로 맞춘다), 그것도 없으면 겹친 줄마다의 화소 평균 차가 모두 3 이하인 자리로(겹친
줄 20 이상), 그것도 없으면 겹치지 않았다고 본다. 어느 방법이었는지 `fragments[].method` 에 남긴다.
고정 띠 안의 겹친 요소는 빼고, 겹친 부분의 같은 요소(글: 같은 글 · 중심 20px 안, 그 밖: IoU 0.5
이상)는 이름 붙은 것 · 넓은 것을 남겨 하나로 합친다. 조각 경계에서 잘려 이름이 없는 로고는 이은
좌표에서 "로고 → 칸 글" 세로 거리의 중앙값(±20px) · 같은 열(±30px)의 글로 이름을 붙인다.

**4. compare.py** — 이은 화면은 한 단위(한 상태)로 센다. 그림 자리는 (a) 상태별 정답 수 대 후보 수
(글 없는 박스 + `img_candidate`), (b) 은행 · 증권사 로고 67개는 정답 `"<이름> 로고"` 와 후보 이름이
같은지 자동으로 센다 (둘 다 같은 규칙으로 만든 이름), (c) 그 밖의 아이콘은 이름 대 설명을 나란히만.
자리 맞추기는 위 · 아래 고정을 따로 맞춘다 (이은 화면에서는 둘이 멀리 떨어진다). `--baseline` 으로
D1 과 합계를 나란히 놓는다.

## D2.5 에서 바꾼 것 (2026-10-13) — 표시 · 설정 시험

**이 앱 캡처로 고른 설정이다.** 같은 19장을 보며 맞췄으므로 다른 앱에서는 다시 봐야 한다. 문턱은 몇 개
후보 값만 시험했다. 지키는 선(D2 의 값) - 글 재현율 221/226 · 로고 이름 63/67 · 선택지 102/102 - 에서
떨어진 설정은 버린다 (이번에는 모두 지켰다). 결과 표: `results/detect/20261013-d25/summary.md`.

**재는 것 (compare.py)**
- 박스 재현율: 정답의 과제 버튼 · 입구(글 있는 것) · 선택지 · 입력칸마다 그 글을 감싸는 검출 박스가
  있는 비율 (박스 하나의 글 안에서 비슷함 0.8 이상). 입력칸은 보이는 글(라벨 · 값) 또는 빈 칸의 안내 글.
- 남는 박스의 갈래: 요소의 표시로 고정 띠 · 덮개 뒤 · 그 밖. 둘 다 달렸으면 고정 띠로 센다.
- `compare.json` 의 `row` 한 줄, `compare.py --table <폴더> …` 로 설정 대 지표 표.

**표시 (flags.py) - 지우지 않고 `flags` 만 단다. 무엇을 버릴지는 D3 와 연구자가 정한다**

| 표시 | 규칙 | 이번 결과 |
|---|---|---|
| `system_band` | 줄마다 바탕(그 줄의 중앙값)을 빼고 남은 잉크를 캡처끼리 견준다 - 빈 줄(잉크 표준편차 < 3)은 빈 줄끼리, 아니면 상관 ≥ 0.9 면 같다. 서로 같은 캡처가 75% 이상인 줄이 위(아래)에서부터 이어지는 마지막 줄까지가 띠 (4줄까지의 틈은 넘는다 - 글자 가장자리 줄이 어두운 캡처에서 빈 줄로 읽힌다. 빈 줄만이면 띠가 아니다). 캡처는 띠 줄의 90% 이상에서 다수와 같아야 그 띠를 가진다. 바탕을 빼므로 회색 바탕(홈)과 덮개로 어두워진 캡처도 같은 띠로 본다 | 위 87px (상태바), 아래 없음. 17장이 가진다 (스크롤해 상태바 없이 찍힌 01b · 01c 는 안 가진다) |
| `behind_overlay` | 16px 칸마다 중앙값 색이 무채색(채널 차 ≤ 10)이고 밝기 90~150 인 칸이 화면의 10% 이상이면 덮개가 뜬 캡처 (반투명 검은 막이 흰 바탕을 117 회색으로 만든다 - 파란 숫자판처럼 짙은 유채색은 걸리지 않는다). 밝기 200 이상 칸의 가장 큰 덩어리를 판(시트 · 팝업)으로 보고 판 밖에 중심이 있는 요소에 단다 | 7장 - 은행 · 증권사 시트 05a~06c (판 [0, 256, 816, 1568]), 오류 팝업 11 (판 [64, 672, 704, 480]) |

**검출 설정 시험 (detect.py 인자, sweep.py)** - D2 바탕에서 하나씩 바꾼 뒤 좋아진 것을 묶었다.

| 설정 | 무엇 | 결과 (표 참고) |
|---|---|---|
| `--imgsz 1024` · `1280` | 검출 입력 크기 | 박스 재현율이 거의 그대로, 그 밖 남는 박스 +6 · +10 |
| `--tiles 2` | 위아래 두 조각(20% 겹침)으로 한 번 더 검출해 합침. 조각을 자른 가장자리에 닿는 박스는 버린다 | 입구 박스 9 → 7 |
| `--clahe` | LAB 밝기에 CLAHE(clip 2.0, 8x8) 한 사본으로 한 번 더 검출해 합침 | 버튼 +1 · 입구 +1, 남는 박스 그대로 |
| `--nms 0.3` · `0.5` | 검출 NMS IoU | 입구 +1 · 선택지 +1 (0.3) |
| `--classic` | 고전 영상 처리 - UIED 의 요소 검출(기울기 이진화 → 선 지우기 → 연결 요소 → 거르기 · 합치기 · 블록 알아보기)을 레포 밖에서 import, run_single.py 의 mobile 권장 값(min-grad 4, min-ele-area 50) · 높이 800 으로 줄여서, 16px 미만 · 화면 60% 이상 버림, 점수 0.04 로 검출기 뒤에 | 입구 9 → 6 - 작은 고전 박스가 포함 규칙으로 바깥 칸을 지운다 |
| `--conf 0.1` | 검출 점수 문턱 | 버튼 +1 · 입구 +3 · 선택지 +8 · 입력칸 +2, 그 밖 남는 박스 11 → 8 - 점수 낮은 작은 박스가 포함 규칙으로 바깥 칸을 지우던 것이 줄었다 |
| `--overlap iou` (요청 밖, 더한 것) | 겹친 박스 정리를 IoU 로만 | 입구 +7 · 선택지 73 → 102, 그 밖 남는 박스 +5 |

여러 번 찾은 박스(조각 · 사본 · 고전)는 IoU 0.5 이상이면 하나로 합친다 (전체 · 원본 검출 쪽을 남긴다).
박스마다 출처가 `source` 에 남는다 (`detector` · `detector:tile` · `detector:clahe` · `classic` · `ocr_icon`).

**고른 기본값 = combo** (`--conf 0.1 --nms 0.3 --clahe --overlap iou`): 박스 재현율이 가장 높고(버튼 5/7 ·
입구 17/24 · 선택지 102/102 · 입력칸 2/3) 지키는 선을 지킨다. 표시 없는 남는 박스는 12 로 D2(11)와
비슷하다 (conf 0.1 하나만이 8 로 가장 적지만 입구 12/24 · 선택지 81/102 에 그친다).

**설정을 바꾸며 드러나 고친 것** - IoU 겹침 규칙에서는 칸 안에 칸이 남아 칸 안 그림 후보에 숫자판 ·
표의 글자가 덩어리로 나왔다 → 은행 칸이 아닌 칸은 안에 든 글 · 안쪽 박스를 모두 지운 뒤 찾는다. 홈의
줄 목록이 은행 칸으로 읽혀 "나에게 맞는 카드 찾기 로고" 가 붙었다 → 칸 글이 이름처럼(띄어쓰기 없는
10자 이하) 생겼을 때만 이름을 붙인다.

## D3 — 의미 층 (2026-10-13)

검출된 요소마다 "누를 수 있나 · 무슨 종류인가 · 무리 · 그림이면 이름" 을 LLM 이 붙이고 정답과 견준다.
입력은 `results/detect/20261013-d25/final/` (13단위 - 이은 화면 3 + 낱장 10).

**이 층이 정하지 않는 것 - 과제 경로.** 과제 버튼 대 과제 밖 입구는 흐름 층에서 연구자가 적는
`captures.json` 의 taps 로 정한다 (누른 것 = 과제 버튼, 누를 수 있지만 안 누른 것 = 과제 밖 입구). 모델에게는
과제 이름 한 줄("이체 — 받는 사람 계좌로 돈 보내기")만 주고 어느 버튼이 과제 경로인지는 알려 주지 않는다.
compare 도 둘을 함께 "누를 수 있는 것" 으로 센다.

**보내는 것 (단위마다 한 번):**
- 요소 JSON - 검출 박스 · img_candidate · OCR 글 줄 모두. 칸은 id · mark(그림 위 번호) · kind · box · text ·
  ocr_guess · caption · name · in_box · near(곁의 글 - inside · row · parent) · flags. 표시 달린 요소도 넣는다.
- 화면 전체를 폭 600 으로 줄이고 mark 번호를 적은 그림 한 장 (이은 화면은 `stitch.compose` 로 다시 이어서).
- 글 없는 박스 · img_candidate 의 잘라낸 그림 (변마다 20% 넓혀 2배, 긴 변 512 까지). 글만 있는 요소는 안 보낸다.
- 규칙으로 이름이 붙은 로고는 고정값으로 넘긴다 - 모델이 다른 이름을 내면 고정값으로 되돌리고 그 수를 적는다.

**받는 것:** 요소 id 마다 하나 `{id, pressable, kind, group, image_name, image_shape, note}` - kind 는 button · link ·
back_close · tab · choice · input · keypad_key · image · text · system. 없는 id · 빠진 id · 틀린 값(kind 밖,
image 인데 이름 모양이 아님 …)이면 문제를 적어 한 번 다시 묻고, 그래도 틀리면 그 단위를 실패로 적는다 -
짐작해 메우지 않는다.

**프롬프트**는 `SEMANTIC_PROMPT.md` 의 `---` 아래 글 그대로다 (지키는 규칙만 - 빠짐없이, 새 요소 금지, 힌트는
힌트일 뿐, 이름은 보이는 것만 · 잘린 글을 채우지 않음). 모델 호출 · 키 읽기 · 그림 토큰 어림 · 가격은
파이프라인의 `senior_ui.restructure.model` · `senior_ui.config` 를 그대로 쓴다 (기본 모델 `gpt-6.1-sol`,
reasoning medium, 출력 상한 25,000, 그림 detail high).

**돌리기:**
```powershell
$py = "C:\Users\xihye\venvs\detect\Scripts\python.exe"
uv pip install --python $py "openai==3.8.0" "tiktoken==0.14.0"      # 한 번 (레포 requirements.txt 와 같은 판)
& $py tools/screen_detect/semantic.py --dry-run          # 그림 수 · 어림 토큰 · 어림 비용만 (키를 읽지 않는다)
& $py tools/screen_detect/semantic.py --mock             # 가짜 답으로 끝까지 (키를 읽지 않는다) → results/detect/<오늘>-d3-mock
& $py tools/screen_detect/semantic.py                    # 실제 호출 → results/detect/<오늘>-d3  (--model 로 바꾼다)
$d = "results/detect/<오늘>-d3"
& $py tools/screen_detect/truth.py --out $d/truth.json   # 정답지 (누를 수 있는 data-action 전부를 담은 판)
& $py tools/screen_detect/compare.py --dir results/detect/20261013-d25/final --semantic $d   # → $d/summary.md
```
`--mock bad-once` · `--mock bad-twice` 는 다시 묻기 · 실패 기록 길을 시험한다.

**아이콘 이름 고침 (D3b, 2026-10-13):** 첫 실제 실행(`results/detect/20261013-d3`, 실패 0, $0.49)에서 모델이 지은 아이콘 이름이 정답과 1/13 만 같았다 - 모양으로 지었다(혜택 → 선물상자, 주식 → 상승 그래프). 디자이너가 표준 아이콘으로 바꿀 때는 뜻 이름이 필요하다. 그래서 프롬프트 규칙 5 를 더했다 - 이름표 글(near 의 같은 박스 · 같은 줄 · 바로 아래 글 `below`)이 있으면 그 글로(이름표 '혜택' → '혜택 아이콘'), 없으면 모양으로 짓고, 모양은 `image_shape` 에 따로 적는다. 규칙 4(보이는 것만 · 잘린 글 채우지 않기)는 그대로다. 고친 단위만 다시 부를 수 있다:
```powershell
& $py tools/screen_detect/semantic.py --units "home(01a+01b+01c),02,08" --reuse results/detect/20261013-d3
#   → results/detect/<오늘>-d3b  (고르지 않은 10단위는 앞 실행의 답 · 원문 · 보낸 그림 · truth.json 을 그대로)
& $py tools/screen_detect/compare.py --dir results/detect/20261013-d25/final --semantic results/detect/<오늘>-d3b
```
가져온 단위는 `<단위>.semantic.json` 의 `reused_from` 에, 단위마다 그때의 프롬프트는 `prompt_sha` 에 남는다 (앞 실행의 답에는 없다 - 그 판에는 image_shape 도 없다).

**키:** 실제 호출 때만 읽는다 - 환경 변수 `OPENAI_API_KEY`, 없으면 이 레포 뿌리의 `.envs` (파이프라인과 같은
방식, `load_env`). `.envs` 는 `.gitignore` 에 있어 커밋되지 않는다.

**비용 어림 (`--dry-run`, gpt-6.1-sol, 2026-10-13):** 13단위 · 요소 666 · 그림 177장(그림 토큰 약 25,650) ·
입력 약 90,000 토큰. 답만 세면 약 $0.48, 생각 토큰이 답과 같다고 보면 약 $0.78, 출력 상한(단위마다 25,000)을
다 쓰는 최악은 $3.43. 다시 묻기가 생긴 단위는 그만큼 한 번 더 든다.

**쓰는 것:** `<단위>.semantic.json` (답 · 시도마다 토큰 · 비용 · 문제 · 고정값 되돌림), `raw/<단위>.<n>.request.txt`
· `.request.json` · `.response.txt` (요청 · 응답 원문 - 키 · 헤더 없음), `_sent/<단위>/` (보낸 그림),
`_semantic.json` (단위마다 상태 · 토큰 · 비용, 합계).

**견주기 (`compare.py --semantic`):** 정답 항목마다 닿는 요소(그 글을 읽은 글 줄 · 박스, 한 요소에 다 들지 않으면
조각 글 줄들, 글 없는 것은 옮긴 자리의 요소) 가운데 하나라도 그 역할이면 맞음. 누를 수 있는 것(글 있는 것 ·
아이콘만 · 박스 없이 글 줄로만 있는 것 - D2.5 의 10개) · 정답에 없는데 누를 수 있다고 한 것(표시 달린 것 따로,
정답 = truth 의 누를 수 있는 data-action 전부) · 선택지(kind=choice)와 무리(group) · 숫자판 키 · 입력칸 ·
그림 자리(kind=image) · 그림 이름(같은 글일 때만 맞음, 규칙 이름 · 모델 이름 · 잘린 이름 따로, 다르면 나란히) ·
그림 자리가 없는 상태의 image 수 · 표시 달린 요소의 system 비율 · 토큰과 비용.

**자리 옮기기 기준:** 10/19 부터 local 기준 (이전 line 기준: 그림 자리 78/90 · 그림 이름 72). local 기준 D3.1 은
그림 자리 79/90 · 그림 이름 75 · 버튼 5/7 · 입구 17/24 · 선택지 102/102 · 입력칸 2/3. 이전 결과 폴더의 summary 는
line 기준 그대로다 (다시 쓰지 않았다). line 으로 다시 세려면 `compare.py … --frame line`.

**잘린 이름** (연구자 결정 2026-10-13): 화면이 이름을 잘라 보인 것("아이엠뱅크(대. 로고")은 앞부분이 정답과
같으면 맞음으로 세되 "잘린 이름" 으로 따로 센다. 뒷부분을 짐작해 채우지 않는다. 남은 OCR 오독("P" · "푸" ·
"8+")은 규칙을 그대로 두고 의미 층이 ocr_guess 를 힌트로 판단한다.

`results/detect/20261013-d3-mock/` 는 가짜 답으로 끝까지 돌린 것이다 (코드가 도는지 보려는 것 - 품질 측정이
아니다. 보낸 그림 `_sent/` 는 커밋하지 않았다).

## D4 — 흐름 층 (2026-10-13)

연구자가 누른 것을 손으로 적지 않는다 - 원본 재현 HTML 의 연결도 캡처 순서와 화면 글로 AI 가 추정해 만들었다.
같은 방식으로 LLM 이 "어느 캡처에서 무엇을 누르면 어느 캡처로 가나" 를 추정하고, 연구자는 그 목록을 검토만 한다.

**입력:** 캡처 순서와 연구자의 이름표 - `origin/feat/see-captures` 의 `inputs/captures/transfer/captures.json` 을
`git show` 로 읽기만 한다 (이 브랜치에 가져오거나 고치지 않는다, taps 는 비어 있다). 단위마다 누를 수 있는 요소 -
`results/detect/20261013-d25/final` (요소, 스크롤 조각은 이은 화면 하나) + `results/detect/20261013-d3b` (역할 ·
이름)에서 pressable 이고 표시(flags)가 없는 것 [id · 글 · kind · group]. **글만 보낸다 - 그림 0장** (입력 약 7,400 토큰).

**출력:** 이웃한 캡처 짝(18)마다 `{from, to, tap, tap_text, kind, confidence, reason}` - kind 는 tap · scroll ·
skipped(사이 상태가 캡처에 없음) · error_path · unknown. 짝 빠짐 · 목록에 없는 요소 · 글을 바꾼 tap_text · 틀린 값은
한 번 다시 묻고 그래도 틀리면 실패. `flow.proposed.json` 과 그것을 captures.json 의 taps 꼴(`{text, to}` + kind ·
confidence)로 바꾼 `taps.proposed.json` - **captures.json 자체는 쓰지 않는다**. 규칙은 `FLOW_PROMPT.md`.

**정답 (compare_flow.py):** `truth.py` 가 걸으며 남긴 timeline(도착한 상태와 누른 것의 차례, 오류 경로 따로)에서
캡처 짝 사이에 실제로 누른 것과 kind 를 얻는다. 이름표 → 상태는 "원본 화면 <방문>" · "원본 오류 상태 <id>" ·
"[증권사] 탭" · "… 입력(중)" 으로 옮긴다. 누름이 하나(숫자 키 하나 포함)이고 사이 상태가 없으면 tap, 아니면 skipped.
누른 것은 글로 맞추고(정답의 첫 누름이 숫자 키면 숫자판 키면 맞음 - 정답 값 32000 과 더미앱 값 10000 이 다르다),
kind 는 같으면 맞음.

```powershell
$py = "C:\Users\xihye\venvs\detect\Scripts\python.exe"
& $py tools/screen_detect/flow.py --dry-run              # 어림 (키를 읽지 않는다)
& $py tools/screen_detect/flow.py --mock                 # 가짜 답으로 끝까지 (키를 읽지 않는다)
& $py tools/screen_detect/flow.py --max-usd 0.60         # 실제 호출 → results/detect/<오늘>-d4
& $py tools/screen_detect/truth.py --out results/detect/<오늘>-d4/truth.json
& $py tools/screen_detect/compare_flow.py --dir results/detect/<오늘>-d4     # → summary.md
```

**첫 실제 실행 (`results/detect/20261013-d4`, gpt-6.1-sol, $0.026, 시도 1):** 누른 것 14/18 · kind 14/18 · 둘 다
13/18. confidence 가 모두 0.85 이상이라 confidence 로 틀린 것을 가려내지 못했다 (틀린 5짝도 0.85~0.98).

## 그림 자리 놓침 진단 (2026-10-19)

`miss_diag.py` - D3.1(`20261013-d3b`) 이 놓친 그림 자리(90 중 12)를 단계별로 따라간다. 읽기만 하고 기본
실행 경로는 바꾸지 않는다 (유료 호출 없음, 의미 층 다시 안 돌림, OCR 은 캐시). 검출기만 다시 돌려 NMS 전 원
출력 → NMS → 사본 합치기 → 겹친 박스 정리 → OCR 글 박스 안 박스 버림 의 어디서 무엇에 지워졌는지, 점수 문턱
0.1 · 0.01 두 번. `--virtual` 은 detect.py 의 함수를 이 프로세스에서만 바꿔 끼워 Soft-NMS · "종류가 다르면
안 지우기" · (참고) 짧은 글 안 박스 남기기를 `results/detect/20261019-miss/<이름>/` 에 돌리고 박스 수준으로 견준다.

```powershell
& $py tools/screen_detect/miss_diag.py --text "08:보내기" --virtual    # → results/detect/20261019-miss/
```

결과 (`results/detect/20261019-miss/summary.md`): A 분류 6 (모두 누를 수 있는 아이콘 - kind 하나라 button) ·
B 정리 단계 1 (OCR "8+" 글 박스 안이라 버림) · C 민감도 3 (0.015~0.066) · D 1 · E 1 (견주기 자리 어긋남 - 실제로는
맞음). 겹침 정리 · NMS 에서 지워진 것은 없었다.

## 구역 검출 시험 (2026-10-19)

정답지에는 글 · 버튼 · 입구 · 선택지 · 입력칸 · 그림 자리만 있고 카드 · 배너 · 시트 같은 **바탕 상자(구역)** 는
없었다. 구역 = "어떤 요소들이 한 묶음인가" - 조립(검출 → 원본 HTML)에서 묶음 구조를 살리는 데 쓴다. 기본 검출
경로 · 설정(D2.5 combo)은 그대로이고, 모두 따로 부르는 스크립트다. 결과 `results/detect/20261019-regions/`.
새로 설치한 패키지 없음 - M2 의 UIED 는 `--classic` 에 쓰던 레포 밖 코드다 (아래 라이선스 표).

| 파일 | 하는 일 |
|---|---|
| `kind_figure.py` | 비교 그림 - detect.overlay 와 같은 꼴(왼쪽 캡처 위 요소, 오른쪽 다시 그린 화면)에 의미 층 kind 를 색으로 → `figures/kind_<캡처>.png` |
| `compare.py --frame local` | 정답 자리 옮기기를 꺾은선 + 글 없는 것 하나씩 짝짓기로 (10/19 부터 기본값, `--frame line` 이 이전 방식) |
| `truth_regions.py` | 구역 정답지 → `truth_regions.json`, `truth_figures/<단위>.png` |
| `regions.py` | 구역 찾기 M1 · M2 와 재기 → `regions.json`, `summary.md`, `found/<방법>/<단위>.png` |

```powershell
& $py tools/screen_detect/kind_figure.py                          # 01a 01b 01c
& $py tools/screen_detect/compare.py --dir results/detect/20261013-d25/final --semantic results/detect/20261013-d3b --frame local --out results/detect/20261019-regions/frame-local
& $py tools/screen_detect/truth_regions.py                        # 원본을 다시 걷는다 (Playwright)
& $py tools/screen_detect/regions.py
```

**자리 옮기기 (`--frame local`).** 직선 하나(무리마다 y' = a·y + b)는 홈처럼 구역마다 줄 높이가 다른 화면에서 한
줄씩 밀렸고(SOL패밀리 자리 → "추천서비스" 머리), 가로는 창 비율이라 아이콘 간격이 다른 홈 머리에서 옆 아이콘을
가리켰다. local 은 (1) 세로를 이웃한 닻 둘 사이의 꺾은선으로 (닻은 정답 y 순으로 캡처 y 도 늘어나는 가장 긴 줄만,
닻 밖은 끝 닻에서 직선 기울기), (2) 글 없는 것(그림 자리끼리, 아이콘만인 버튼 · 입구끼리)을 후보와 헝가리안
짝짓기로 하나씩 (비용 = 중심 거리, NEAR 안이거나 FAR 안만, 짝 없음 = FAR + 1, 상태바 표시 후보는 뺀다).
D3.1 에 대해 그림 자리 78 → 79 (SOL패밀리), 그림 이름 72 → 75, 정답에 없는데 누를 수 있다고 한 것 36 → 35, 박스
재현율 · 선택지 · 숫자판 · 입력칸 그대로 (`frame-line/` 대 `frame-local/`).

**구역 정답 뽑는 규칙 (`truth_regions.py`).** truth.py 와 같은 원본 · 같은 흐름 · 같은 걷기(snapshot 만 감싼다).
켜진 화면 안의 보이는 요소 가운데 (1) 바탕이 뒤와 다르거나(자기 배경색 · 배경 그림이 뒤에 보이는 것 - 창 안이면
그 점에서 아래에 겹친 요소, 창 밖이면 조상 - 의 처음 배경과 다르다), 네 변 모두 테두리가 있거나, 그림자가 있고
(2) CSS 40x24 이상이며 (3) 안에 보이는 요소 · 글이 있는 것. 상태바 · 그림 자리(role="img") · 화면 전체 바탕(창의
95% x 90% 이상)은 뺀다. 같은 자리(2px)는 바깥 하나. `control` = 그 요소가 누를 수 있는 것 자체(버튼 · 은행 칸) -
정의에는 맞지만 "바탕 상자" 와 따로 센다. 구역마다 안에 든 정답 항목(compare.key) 과 부모 구역. 캡처로는 위 ·
아래 변을 꺾은선으로 따로 옮기고, 창 아래 끝까지 닿는 고정 구역(시트 · 비밀번호 판)은 단위 그림 끝까지.
상태 15개에 구역 121개 (바탕 17 · 조작 104 - 홈 14 = 바탕 7 · 조작 7, 은행 39 · 증권사 30 은 거의 칸). 캡처 단위 13개로 옮기면 114개.

**구역 찾기 (`regions.py`).** M1 색 영역 나누기 - 이웃 화소와 채널 차가 DIFF 보다 큰 화소를 경계로, 경계 아닌
화소의 이어진 영역마다 바깥 윤곽을 채운 넓이가 둘레 상자의 0.85 이상이고 CSS 40x24 이상이면 구역 (구멍은 채움).
시험한 값: DIFF 2 · 6 · 12, 최소 크기 1배 · 2배(DIFF 6). M2 UIED - 블록 알아보기까지 돌린 요소 전부(all) · 블록만
(block), 캡처마다 돌려 이은 화면으로 합친다. 맞음 = IoU 0.7 이상 또는 네 변 모두 12px 안.

| 방법 | 구역 재현율 | 바탕 상자 | 정답에 없는 구역 | 묶음 정확도 | IRP 배너 · 땡겨요 카드 |
|---|---|---|---|---|---|
| M1 DIFF 2 | 108/114 | 16/17 | 31 | 412/447 (92%) | 예 · 예 |
| M1 DIFF 6 | 33/114 | 9/17 | 20 | 26% | 아니오 · 아니오 |
| M2 UIED all | 96/114 | 10/17 | 117 | 174/447 (39%) | 예 · 예 |

DIFF 6 · 12 가 크게 떨어진 까닭: 둥근 모서리의 앤티에일리어싱이 채널 차 10 안팎(흰 바탕 위 #F4F6FA 칸)을 두 화소에
나눠 그려 한 걸음 차가 5 안팎이다 - 경계가 끊겨 칸이 바탕과 이어진다. **이 앱 캡처(PNG, 압축 손실 없음)로 고른
값이다.** JPEG · 실기기 캡처에서는 DIFF 2 가 잡음을 경계로 볼 수 있다. 놓친 정답 구역의 상당수(홈 "이체" ·
"시작하기", 완료 화면 버튼)는 찾은 구역이 실제 상자에 맞는데 정답을 옮긴 자리가 더미앱 배치와 달라 어긋난 것이다
(`found/M1-diff2/`).

## 구역 검출 다지기 (2026-10-19)

연구자 결정 (10/19): compare 의 자리 옮기기 기본값 = local. 구역은 **바탕 상자와 조작 상자를 늘 따로** 센다 - 주
숫자는 바탕 상자 재현율과 묶음 (가) (조작 상자는 버튼 · 선택지 숫자로 이미 잰다). 결과 `results/detect/20261019-robust/`.
새 패키지 없음 (OpenCV · Pillow).

**묶음 정확도 두 가지 (`regions.py`).** (가) 바탕 묶음 - D2.5 final 의 요소(박스 · 글 줄 · 그림 후보)마다 중심을
감싸는 가장 작은 정답 바탕 상자 B 를 정한다. 그 요소를 감싸는 찾은 구역들 가운데 B 와 맞는 것(IoU 0.7 이상 또는 네
변 12px 안)이 있으면 맞음. B 가 없는 요소("바탕 없음")는 감싸는 찾은 구역 가운데 정답 바탕 상자와 맞는 것이 하나도
없으면 맞음. M1 은 바탕 · 조작을 가리지 못하므로 "가장 작은 찾은 구역" 대신 "감싸는 구역들 안에 있나" 로 본다.
요약에는 B 가 있는 요소만의 비율("B 안")도 붙인다. (나) 전부 - 담은 가장 작은 정답 구역(바탕 · 조작)과 가장 작은
찾은 구역이 맞나 (앞 시험의 묶음 정확도).

| 방법 | 바탕 | 조작 | 정답에 없는 구역 | 묶음 (가) | (나) | 합친 재현율 |
|---|---|---|---|---|---|---|
| M1 색 차이 2 | 16/17 | 92/97 | 31 | 653/666 (B 안 374/387) | 412/447 | 108/114 |
| M2 UIED all | 10/17 | 86/97 | 117 | 370/666 (B 안 91/387) | 174/447 | 96/114 |

**`regions_robust.py`** (`miss` · `shake` · `tree`, 아래 셋 모두 M1).

```powershell
& $py tools/screen_detect/regions.py --configs M1-diff2 M2-uied-all --out results/detect/20261019-robust/recount --no-figures
& $py tools/screen_detect/regions_robust.py miss     # miss/marks.json (눈으로 가른 표시) 대로 세고 그린다
& $py tools/screen_detect/regions_robust.py shake    # 사본은 _copies/ (.gitignore)
& $py tools/screen_detect/regions_robust.py tree
```

- miss - 놓친 정답 구역 6 = a 정답 자리 어긋남 4 ("이체" · "시작하기" · 완료 화면 두 버튼, 모두 조작) · b 진짜 놓침 1
  (완료 화면 파란 원 - 원은 사각형 채움 0.79 < 0.85) · c 더미앱에 상자 없음 1 (이벤트 카드). 넘침 31 = 그림 칸 6 ·
  숫자판 판 3 · 덮개 5 · 정답 규칙이 빠뜨린 상자 1 (받는 사람 "편집" 꼬리표 - HTML 에서는 CSS 40x24 아래) · 기타 16
  (화면 바탕 조각 10 · 정답 자리 어긋남의 짝 4 · 구분선으로 나뉜 시트 머리 2). 정답지는 고치지 않았다.
- shake - 사본 다섯 (원본 · JPEG 90 · JPEG 75 · 0.75배 LANCZOS · 0.75배 + JPEG 75, JPEG 은 Pillow 기본) × 색 차이 2 · 3 · 4.
  원본 · 0.75배는 세 값 모두 바탕 16/17. JPEG 90 은 색 차이 2 만 16/17 (3 에서 12/17). JPEG 75 는 색 차이 2 에서 11/17 ·
  넘침 31 이라 정한 조건대로 중앙값 흐림 3x3 을 한 번 더 했지만 11/17 그대로 (원본은 흐림 뒤에도 16/17 · 31).
- tree - 단위마다 구역 나무 (`tree/<단위>.regions.json`): 부모 = 감싼 가장 작은 구역 (2px 넘침 허용), 깊이 맨 바깥 1,
  요소는 중심을 감싼 가장 작은 구역에만. 의미 층 group 과 견주기 · 홈 01a 나무 글 (`tree/home_01a.txt`).

## 라이선스 (저장소 · 모델 카드에서 확인, 2026-10-12)

| 무엇 | 라이선스 | 근거 |
|---|---|---|
| `icon_detect_v3` (YOLOv9-E) | MIT | `icon_detect_v3/LICENSE`, 가중치 README "New: MIT licensed detector weights" |
| `icon_caption` (Florence-2 미세조정) | MIT | `icon_caption/LICENSE` |
| `microsoft/Florence-2-base` (처리기 · 모델 코드) | MIT | HF 모델 카드 |
| OmniParser 코드 (`util/yolov9.py` 를 레포 밖에서 import 만 한다 - 레포로 옮겨 오지 않는다) | 두 표기가 다르다: 저장소 `LICENSE` 파일은 CC BY 4.0, README 배지는 MIT | 저장소 |
| PaddleOCR 3.7.0 · PaddleX 3.7.2 · PaddlePaddle 3.2.0 | Apache-2.0 | 패키지 METADATA · LICENSE |
| `PP-OCRv5_server_det` · `korean_PP-OCRv5_mobile_rec` | Apache-2.0 | HF 모델 카드 (PaddlePaddle/…) |
| `icon_detect` (v1, YOLOv8) | AGPL-3.0 — **쓰지 않았다, 받지도 않았다** | 가중치 README |
| UIED (MulongXie/UIED @ `0a9862a`, `detect_compo/` 만 레포 밖 `C:\Users\xihye\tools\UIED` 에서 import - `--classic`) | Apache-2.0 | 저장소 `LICENSE` · GitHub API (2026-10-13). 기본값에서는 쓰지 않는다 |

## 정답지 (`truth.py`)

과제 파일이 가리키는 원본(`inputs/original_transfer.html`)을 원본 흐름(`flows/original.json`)대로
걷는다. 걸음 실행 · 화면 기다리기 · 방문 이름 · 화면 긁기는 검사기의 것
(`senior_ui.audit.drive.run_actions` · `settle`, `flow.visit_keys`, `probes.INVENTORY` ·
`CHOICE_SHOWN` · `ENTRANCES` — 검사 I · K 가 쓰는 것과 같은 probe)을 그대로 쓴다. 이 브랜치에는
검사 L 이 없다 (`senior_ui/audit/checks/` 는 A~K).

검사기의 걷기와 다른 점: 캡처에는 걸음 사이의 모습도 있어서 (은행을 고른 계좌 화면, 금액을 넣은
화면) 걸음 안의 동작마다 긁고(`<방문>~<n>`), 흐름에 없는 [증권사] 탭 상태(`bank+tab-sec`)와
오류 경로의 오류 상태(`error:<id>`)를 더 긁는다. 상태마다: 보이는 글(innerText 줄 + 빈 칸의
안내 글), 과제 버튼(정답 경로가 그 상태에서 누르는 것, 숫자 키 제외), 과제 밖 입구(oos-*),
그림 자리(role="img" + aria-label), 선택지 값, 입력칸, 그리고 자리 맞추기용 글 조각의 자리.
비밀번호 숫자판은 원본이 열 때마다 섞으므로(N10) `truth.json` 의 그 글 순서는 돌릴 때마다 다르다.

## 맞추는 규칙 (`compare.py`)

- **짝 제안**: 캡처마다 글 F1 이 가장 큰 상태. 다만 그 상태만의 글이 둘 이상이고 70% 이상 찾아진
  상태가 있으면 그것을 앞세운다(덮개 규칙 — 팝업이 밑 화면 위에 뜬 캡처). **제안일 뿐이다.**
  `captures.json` 은 만들거나 읽거나 고치지 않는다.
- **글 찾기**: 공백 · 기호를 뺀 뒤 비슷함 0.8 이상 (OCR 글 하나와의 비율, 또는 OCR 글을 읽는
  순서로 이은 줄 안의 부분 비율). 두 글자 이하는 OCR 글 또는 그 안 낱말과 같아야 한다.
- **글 없는 것**(그림 자리 · 아이콘 입구): 판정하지 않는다. 정답 자리를 캡처 위로 대강 옮겨
  (글 조각을 닻으로 세로 직선 맞춤) 곁의 글 없는 박스 설명을 나란히 적기만 한다.
- **남는 박스**: 글이 든 박스는 그 안의 글이 정답 어디에도 없으면, 글 없는 박스는 옮긴 정답
  자리 어디에도 들지 않으면.

## 이 시험의 한계

- **더미앱(Flutter)과 재현 HTML 은 같은 앱이 아니다.** 문구 · 값 · 배치가 조금씩 다르다 — 금액
  (캡처 10,000원 · 정답 32,000원), 오류 팝업의 계좌번호(100 · 110234567891), 은행 칸 높이, 홈
  머리(더미앱은 스크롤로 사라지고 재현 HTML 은 고정), 시트 · 팝업 뒤에 비친 밑 화면(재현 HTML 의
  은행 시트 · 오류 화면에는 밑 화면 글이 없다). 그래서 박스 겹침이 아니라 글 · 이름으로 맞췄고,
  남는 글 · 남는 박스에는 이 차이가 섞인다.
- **짝은 제안일 뿐이다.** 07a 처럼 글로는 가를 수 없는 짝(금액을 넣기 전 · 뒤)이 있고, 덮개
  규칙도 짐작이다. 연구자가 확인해 `captures.json` 에 적어야 한다.
- **자리 옮기기는 대강이다.** 글 없는 것의 곁 설명과 "자리상 캡처 안" 판단은 닻 글로 맞춘 직선
  하나에 기대므로, 줄 높이가 다른 곳 · 스크롤 끝 근처에서 틀릴 수 있다. 판정에는 쓰지 않았다.
- **캡처가 스크롤 조각이다.** 홈 · 은행 · 증권사는 세 장으로 나뉘어, 캡처 한 장의 재현율은 낮고
  합계는 상태마다 합쳐 센다. 상태 이름이 같은 캡처끼리 겹친 부분은 두 번 센다(글 없는 박스 수).
- **찍지 않은 상태는 볼 수 없다.** 은행을 고른 계좌 화면, 계좌번호를 넣은 계좌 화면, ETA00325(은행이
  틀렸다) 팝업은 캡처가 없어 정답지에만 있다. 새로 찍지 않는다 - 스크린샷 입력의 한계로 둔다
  (연구자 결정, 2026-10-12). 스크린샷으로 들어오는 것은 찍힌 상태뿐이다.
- **스크롤 잇기는 겹침에 기댄다.** 홈 01a → 01b 는 겹치는 글이 없어 화소(겹친 26줄, 거의 빈 줄)로
  이었다 - 어긋남이 수십 px 틀릴 수 있다. 증권사 06a → 06b 는 겹친 내용이 거의 없어 잘린 칸의 높이로
  짐작했다.
- **표본 하나.** 더미앱 이체 한 과제, 19장. 실제 은행 앱 캡처는 쓰지 않았다.
