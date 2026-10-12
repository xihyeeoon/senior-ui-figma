# screen_detect — 스크린샷에서 UI 요소 검출 (시험 D1)

도구의 입력을 "사람이 만든 원본 HTML" 에서 "이미 찍어 둔 스크린샷" 쪽으로 옮길 수 있는지 보는
첫 시험의 **요소 층**이다 (계획: 1 요소 층 → 2 의미 층(LLM 이 역할) → 3 흐름 층(연구자가 전환을
적음) → 4 조립(재현 HTML)). 더미앱 A1 이체 캡처(`inputs/captures/transfer/*.png`, 19장)에서
박스 · 글 · 아이콘 설명을 뽑고, 원본 재현 HTML(`inputs/original_transfer.html`)을 걸어 얻은
정답지와 **글 · 이름으로** 견준다. 재설계 · 검사기 · 프롬프트는 건드리지 않는다.

| 파일 | 하는 일 |
|---|---|
| `detect.py` | PNG 마다 요소 목록 JSON + 확인 그림 (검출 · 설명 · OCR) |
| `truth.py` | 원본 재현 HTML 을 원본 흐름대로 걸어 상태마다 보이는 것을 모은다 (정답지) |
| `compare.py` | 캡처 ↔ 상태 짝 **제안**, 글 재현율 · 버튼 · 입구 · 선택지 · 그림 자리 · 남는 박스 |

결과: `results/detect/20261012/` — `<캡처>.json`, `overlay/<캡처>.png`, `_run.json`(장치 · 판 ·
시간), `truth.json`, `summary.md`, `compare.json`.

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
& $py tools/screen_detect/detect.py      # 19장 → results/detect/20261012/*.json, overlay/, _run.json
& $py tools/screen_detect/truth.py       # → results/detect/20261012/truth.json
& $py tools/screen_detect/compare.py     # → results/detect/20261012/summary.md, compare.json
```

`detect.py 01a 05a` 처럼 캡처 이름을 주면 그것만, `--out` 으로 다른 폴더에, `--imgsz` 로 검출 입력
크기를 바꾼다 (기본 640 = OmniParser 기본값. 1280 · 원본 크기도 해 봤는데 박스 수가 거의 같았다).

### 설정 (OmniParser 기본값을 따른다)

| | 값 | 어디서 |
|---|---|---|
| 검출 점수 · NMS IoU · 입력 | 0.05 · 0.1 · 640 | `gradio_demo.py` · `util/utils.py` |
| 겹친 박스 정리 | IoU 0.7 넘게 겹치면 큰 것을 버림, OCR 글 박스 안에 든 박스는 버림 | `remove_overlap_new` |
| 글을 박스에 붙임 | 글 박스 넓이의 80% 가 검출 박스 안 (`text_in`, 여럿이면 가장 작은 박스) | `is_inside` |
| 설명 | 글 없는 박스만, 64x64 로 줄여 `<CAPTION>`, 20 토큰 | `get_parsed_content_icon` |
| OCR | 점수 0.5 미만 버림 (우리 값) | — |

OCR 글은 박스에 붙었든 아니든 `kind: "text"` 요소로 모두 남는다 — 글 재현율은 OCR 만 본다.

## 라이선스 (저장소 · 모델 카드에서 확인, 2026-10-12)

| 무엇 | 라이선스 | 근거 |
|---|---|---|
| `icon_detect_v3` (YOLOv9-E) | MIT | `icon_detect_v3/LICENSE`, 가중치 README "New: MIT licensed detector weights" |
| `icon_caption` (Florence-2 미세조정) | MIT | `icon_caption/LICENSE` |
| `microsoft/Florence-2-base` (처리기 · 모델 코드) | MIT | HF 모델 카드 |
| OmniParser 코드 (`util/yolov9.py` 를 레포 밖에서 import 만 한다) | 저장소 `LICENSE` 파일은 CC BY 4.0, README 배지는 MIT | 저장소 |
| PaddleOCR 3.7.0 · PaddleX 3.7.2 · PaddlePaddle 3.2.0 | Apache-2.0 | 패키지 METADATA · LICENSE |
| `PP-OCRv5_server_det` · `korean_PP-OCRv5_mobile_rec` | Apache-2.0 | HF 모델 카드 (PaddlePaddle/…) |
| `icon_detect` (v1, YOLOv8) | AGPL-3.0 — **쓰지 않았다, 받지도 않았다** | 가중치 README |

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
- **표본 하나.** 더미앱 이체 한 과제, 19장. 실제 은행 앱 캡처는 쓰지 않았다.
