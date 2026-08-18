# 로컬 PDF BM25 검색기 실행 가이드

이 프로젝트는 PDF를 로컬에서 읽어 JSON 데이터베이스를 만들고, BM25로 검색합니다. 외부 LLM, 임베딩 API, 클라우드 DB는 사용하지 않습니다.

## 구성

```text
PDF 폴더
  └─ PDF 파일들
       ↓ build_paper_db.py
  └─ paper_database.json
       ↓ search_server.py --db ...
  └─ http://127.0.0.1:8000 검색 화면
```

DB에는 PDF에서 추출한 전체 텍스트가 들어가므로, PDF 원본과 같은 수준의 기밀 데이터로 취급해야 합니다.

## 필요한 환경

- Python 3.10 이상
- `pypdf` 라이브러리
- 한→영 검색기를 쓸 경우 `torch`, `transformers` 라이브러리와 한→영 모델
- 웹 브라우저 (검색 화면 확인용)

검색 서버와 화면은 Python 표준 라이브러리로 동작합니다. 별도의 Flask, Node.js, 데이터베이스 서버는 필요하지 않습니다.

## 설치

프로젝트 폴더에서 가상환경을 만드는 방법입니다.

```bash
cd /Users/pkp020831gmail.com/AI_project/Day1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

폐쇄망 환경에서는 미리 확보한 wheel 파일만 사용합니다.

```bash
python -m pip install --no-index --find-links /secure/wheels -r requirements.txt
```

설치 여부는 다음으로 확인할 수 있습니다.

```bash
python -c "from pypdf import PdfReader; print('pypdf ready')"
```

## 로컬 한→영 번역 + BM25 검색기

`search_server_ko_en.py`는 고정 용어 사전을 쓰지 않습니다. 한국어로 입력한 질의 전체를 로컬 Transformer 한→영 모델로 기계번역한 뒤, 번역 결과를 기존 BM25 인덱스에 검색합니다. 원본 `search_server.py`는 변경되지 않았습니다.

번역 모델은 한 번만 설치하면 됩니다. 기본 저장 위치는 프로젝트의 `models/opus-mt-ko-en/`이며, PDF 폴더나 JSON DB에는 저장되지 않습니다.

```bash
cd /Users/pkp020831gmail.com/AI_project/Day1
python3 install_ko_en_model.py
python3 search_server_ko_en.py --db "/secure/confidential-pdfs/paper_database.json"
```

검색 화면은 다음 주소입니다.

```text
http://127.0.0.1:8001
```

첫 모델 설치 때만 공개 번역 모델을 내려받기 위한 네트워크가 필요합니다. 폐쇄망에서는 다른 보안 환경에서 미리 내려받은 모델 폴더를 설치합니다.

```bash
python3 install_ko_en_model.py --from-dir "/secure/models/opus-mt-ko-en"
```

서버 실행 중에는 PDF와 질의가 외부로 전송되지 않으며, 영어 질의는 번역 없이 그대로 BM25로 검색합니다.

## 필요한 파일 구조

`search_server.py`는 같은 프로젝트의 `web/` 폴더를 사용하므로 아래 파일은 함께 유지해야 합니다.

```text
Day1/
  build_paper_db.py
  search_server.py
  web/
    index.html
    styles.css
    app.js
```

PDF는 프로젝트 내부 또는 별도 기밀 폴더 어디에 있어도 됩니다.

```text
/secure/confidential-pdfs/
  report-a.pdf
  report-b.pdf
  nested/
    report-c.pdf
```

## PDF 폴더 전체를 DB로 만들기

아래 명령은 지정 폴더와 모든 하위 폴더의 `.pdf` 파일을 읽습니다.

```bash
python3 build_paper_db.py --pdf-dir "/secure/confidential-pdfs"
```

생성 결과는 입력 PDF 폴더 안에 저장됩니다.

```text
/secure/confidential-pdfs/paper_database.json
```

다른 파일명이나 위치를 사용하려면 `--output`을 지정합니다.

```bash
python3 build_paper_db.py \
  --pdf-dir "/secure/confidential-pdfs" \
  --output "/secure/databases/project-a.json"
```

같은 PDF 폴더를 다시 인덱싱하면 기존 `paper_database.json`은 새 데이터로 덮어써집니다. 이전 DB가 필요하면 이름을 바꾸거나 `--output`으로 별도 경로를 지정하세요.

## 특정 DB만 검색하기

검색 서버는 `--db`로 지정한 JSON 파일 하나만 읽습니다.

```bash
python3 search_server.py \
  --db "/secure/confidential-pdfs/paper_database.json"
```

## 청크 단위 DB 만들기

긴 문서의 검색 정밀도를 높이려면 기존 DB를 유지한 채 청크 DB를 만듭니다. 기본값은 청크당 1,000자, 인접 청크 간 200자 중복이며, 결과 파일명은 `paper_database_chunked.json`입니다.

```bash
python3 build_chunked_paper_db.py \
  --input "/secure/confidential-pdfs/paper_database.json"
```

청크 크기와 중복 길이를 바꾸거나 생성 파일명을 지정할 수 있습니다.

```bash
python3 build_chunked_paper_db.py \
  --input "/secure/confidential-pdfs/paper_database.json" \
  --output "/secure/confidential-pdfs/project-a_chunked.json" \
  --chunk-size 1200 \
  --chunk-overlap 200
```

생성된 DB는 기존 서버에 그대로 지정할 수 있습니다.

```bash
python3 search_server.py --db "/secure/confidential-pdfs/paper_database_chunked.json"
```

서버가 시작되면 브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:8000
```

서버는 `127.0.0.1`에만 바인딩되므로 같은 컴퓨터에서만 접근할 수 있습니다.

PDF 폴더로 이동해 실행한다면 `--db`는 생략할 수 있습니다.

```bash
cd "/secure/confidential-pdfs"
python3 "/Users/pkp020831gmail.com/AI_project/Day1/search_server.py"
```

이 경우 현재 폴더의 `paper_database.json`만 읽습니다.

## 현재 테스트 데이터 실행 예시

프로젝트 루트에서 아래를 실행하면 `output/pdf/`의 테스트 PDF를 인덱싱합니다.

```bash
python3 build_paper_db.py
python3 search_server.py --db ./output/pdf/paper_database.json
```

## 동작 확인

서버 실행 중 다른 터미널에서 다음 명령을 실행합니다.

```bash
curl http://127.0.0.1:8000/api/health
curl "http://127.0.0.1:8000/api/search?q=vector%20retrieval"
```

첫 요청은 인덱싱된 PDF 수를, 두 번째 요청은 BM25 검색 결과를 반환합니다.

## DB에 저장되는 정보

각 PDF 레코드에는 다음 정보가 들어갑니다.

- 파일명, 상대 경로, 파일 크기, SHA-256
- 페이지 수와 암호화 여부
- PDF 내장 메타데이터(제목, 저자, 키워드 등)
- 로컬에서 추출한 전체 텍스트와 화면용 미리보기
- 텍스트 추출 실패 또는 암호화 관련 오류

BM25는 제목(×4), 키워드(×3), PDF 메타데이터(×2), 본문 텍스트(×1)를 가중해 순위를 계산합니다.

## 제한 사항

- 스캔 이미지로만 된 PDF는 `pypdf`로 텍스트를 추출할 수 없습니다. 이런 문서는 `metadata only`로 기록됩니다. 필요하면 별도의 로컬 OCR 단계를 추가해야 합니다.
- 비밀번호가 걸린 PDF는 비밀번호를 제공하는 기능이 아직 없으므로 본문을 추출하지 않습니다.
- 입력 폴더에서 PDF를 추가, 삭제, 수정하면 DB 생성 명령을 다시 실행해야 합니다.

## 보안 권장 사항

- 기밀 PDF와 `paper_database.json`을 같은 접근 제어·암호화 정책으로 보호합니다.
- `127.0.0.1` 이외의 주소로 서버를 노출하지 않습니다.
- 폐쇄망이 필요하면 사내 패키지 저장소 또는 사전 내려받은 wheel로 `pypdf`를 설치합니다.
- JSON DB와 PDF를 외부 저장소, 메신저, 공개 Git 저장소에 업로드하지 않습니다.
