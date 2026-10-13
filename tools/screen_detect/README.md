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
