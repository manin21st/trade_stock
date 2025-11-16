# KIS 자동매매 프로그램

## 1. 프로젝트 개요

이 프로그램은 한국투자증권(KIS) Open Trading API를 활용하여 주식 자동매매를 수행하는 **클라우드 기반의 헤드리스(Headless) 엔진**과, 이 엔진의 **전략을 설정하고 실행 로그를 모니터링하는 데스크톱 GUI 애플리케이션**으로 구성됩니다.
이 프로젝트는 **핵심 자동매매 로직**과 **사용자 인터페이스**를 명확히 분리하여, 안정적이고 확장 가능한 시스템 구축을 목표로 합니다. 주식 매매 기능은 `open-trading-api` 라이브러리를 참조하여 모든 기능을 구현합니다. 

## 2. 프로젝트 아키텍처

이 프로젝트는 클라우드 서버 환경에서의 자동매매(Headless) 운영을 고려하여, **자동매매 엔진**, **핵심 로직**, **전략 정의**, **거래 실행**, **설정 관리**, **사용자 인터페이스**를 명확하게 분리하는 모듈식 구조로 설계되었습니다.

- **`main_cmd.py` (자동매매 엔진)**: 클라우드 서버 환경에서 독립적으로 실행되며, `config.json`에 정의된 전략에 따라 실제 거래 (`trade.py`)를 수행합니다. 모든 실행 과정은 상세한 로그를 남깁니다.
- **`main_gui.py` (전략 설정 및 로그 뷰어)**: `main_cmd.py`가 참조하는 전략 파라미터 (`config.json`)를 사용자가 쉽게 설정하고 저장할 수 있는 GUI입니다. 또한 `main_cmd.py`가 기록한 로그 (`main_cmd.log`)를 실시간으로 조회하고 필터링하는 기능을 제공합니다.
- **`core_logic.py` (핵심 API 로직)**: KIS API 인증 및 주식 정보 조회, 계좌 잔고 조회 등 모든 API 통신 및 비즈니스 데이터를 처리하는 핵심 모듈입니다. `main_cmd.py`, `condition.py`, `trade.py`에서 공통으로 참조됩니다.
- **`condition.py` (거래 조건 정의)**: 매수/매도/보유 여부를 결정하는 다양한 조건 함수들을 정의합니다. `core_logic.py`를 통해 데이터를 조회하고, `config.json`의 설정값을 활용합니다.
- **`trade.py` (거래 실행 로직)**: 실제 매수/매도 주문을 KIS API를 통해 실행하는 함수들을 정의합니다. (현재는 플레이스홀더)
- **`config.json` (전략 설정 파일)**: `main_gui.py`에서 설정하고 `main_cmd.py`에서 읽어 사용하는 JSON 형식의 중앙 설정 파일입니다. 대상 종목, 매수/매도 조건, 루프 주기 등을 포함합니다.
- **`column_mappings.py` (컬럼명 한글 매핑)**: API가 반환하는 복잡한 영문 컬럼명을 이해하기 쉬운 한글로 변환하기 위한 매핑 정보를 관리합니다.
- `open-trading-api/` (참조 라이브러리): 한국투자증권에서 제공하는 공식 API 샘플 코드입니다. 우리 프로젝트는 이 라이브러리의 함수를 호출하여 실제 기능을 수행합니다. 이 폴더는 **Git 서브모듈로 관리됩니다.** 프로젝트 클론 시 `git clone --recurse-submodules` 명령을 사용하거나, 클론 후 `git submodule update --init --recursive` 명령을 실행하여 라이브러리 코드를 가져와야 합니다.

## 3. 주요 기능

- **자동매매 엔진 (`main_cmd.py`)**:
    - `config.json`에 설정된 전략 파라미터(대상 종목, 매수/매도 조건 등)에 따라 주식 자동매매 로직을 실행합니다.
    - 각 자동매매 사이클마다 고유 ID를 부여하고, 모든 실행 과정을 상세한 로그 파일 (`main_cmd.log`)로 기록합니다.
    - 리눅스 서버 환경에서 백그라운드 실행 및 터미널을 통한 로그 모니터링을 지원합니다.
- **전략 설정 및 로그 뷰어 GUI (`main_gui.py`)**:
    - 직관적인 GUI를 통해 `config.json` 파일의 전략 파라미터(대상 종목, 매수/매도 조건, 루프 주기 등)를 쉽게 설정하고 저장합니다.
    - `main_cmd.log` 파일을 실시간으로 조회하고, 생성된 `cycle_id`를 기반으로 특정 사이클의 로그만 필터링하여 볼 수 있습니다.
    - 설정 기능과 로그 뷰어가 단일 화면에 통합되어 사용자 편의성을 높입니다.
- **모듈화된 조건 및 거래 로직**:
    - `condition.py`에서 다양한 시장 상황(거래 시간, 가격, 계좌 잔고 등)에 대한 판단 기준을 정의합니다.
    - `trade.py`에서 실제 KIS API를 통한 매수/매도 주문 실행 로직을 제공합니다. (현재는 플레이스홀더)

## 4. 설치 및 설정 방법

**1단계: 소스 코드 복제**

```bash
git clone https://github.com/koreainvestment/open-trading-api.git
```

**2단계: 필요 라이브러리 설치**

```bash
cd open-trading-api
py -m pip install -r requirements.txt
cd ..
```

**3단계: 설정 파일(`kis_devlp.yaml`) 생성 및 수정**

1.  **폴더 생성**: `C:\Users\<사용자이름>\KIS\config`
2.  **설정 파일 준비**: `open-trading-api/kis_devlp.yaml` 파일을 열어 본인 정보를 입력합니다.
3.  **설정 파일 복사**: 수정한 `kis_devlp.yaml` 파일을 위에서 생성한 `config` 폴더 안으로 복사합니다.

## 5. 프로그램 실행 방법

```bash
py main_gui.py
```

## 6. 파일 구조

```
C:\DigitalTwin\trade_stock
├── main_cmd.py             # 클라우드 서버용 자동매매 엔진 (Headless)
├── main_gui.py             # 전략 설정 및 로그 뷰어 GUI
├── core_logic.py           # 핵심 비즈니스 로직 (API 호출, 데이터 처리)
├── condition.py            # 거래 조건 정의 라이브러리
├── trade.py                # 거래 실행 로직 라이브러리
├── column_mappings.py      # 컬럼명 한글 매핑 정보
├── config.json             # 전략 설정 파일 (GUI와 main_cmd 공유)
├── open-trading-api/       # 한국투자증권 API 라이브러리 (Git 버전관리에서 제외됨)
├── backup/                 # 백업 파일 저장 폴더
│   └── main_gui_v1.py      # 초기 main_gui.py 백업
├── test/                   # 각종 기능 테스트용 스크립트 폴더
│   └── test_balance.py     # 잔고 조회 기능 테스트용 스크립트
└── GEMINI.md               # 본 프로젝트 지침서
```

## 7. 소스 버전 관리 (Git)

이 프로젝트의 소스 코드는 Git으로 버전 관리되며, 아래 GitHub 저장소에서 관리됩니다.

- **저장소 주소:** `https://github.com/manin21st/trade_stock.git`

## 8. 로드맵 (Roadmap)

- [x] 1. 초기 환경 설정 및 API 연동
- [x] 2. 기본 GUI 뷰어 구현 (시세, 잔고 조회)
- [x] 3. 핵심 로직 모듈화 리팩토링 (`core_logic`, `column_mappings`)
- [x] 4. Git 버전 관리 및 GitHub 연동
- [x] 5. 프로젝트 문서 체계화
- [x] 6. 클라우드 서버용 자동매매 엔진 (`main_cmd.py`) 구현 및 GUI 분리
- [x] 7. 전략 설정 GUI (`main_gui.py`) 및 로그 뷰어 구현
- [x] 8. 조건 (`condition.py`) 및 거래 (`trade.py`) 모듈 분리
- [x] 9. 로깅 시스템 개선 (사이클 ID, Custom Formatter, 외부 로그 억제)
- [ ] 10. 실시간 데이터 조회 및 자동 갱신 (Websocket 연동)
- [ ] 11. 매수/매도 주문 기능 구현
- [ ] 12. 거래 전략 수립 및 구현
- [ ] 13. 서버 배포 및 자동 실행

## 9. 변경 이력 (Changelog)

### 2025-11-14
- 클라우드 서버용 자동매매 엔진 (`main_cmd.py`) 구현 및 GUI 분리
- 전략 설정 및 로그 뷰어 GUI (`main_gui.py`) 구현
- 거래 조건 (`condition.py`) 및 거래 실행 (`trade.py`) 모듈 분리
- `config.json`을 통한 전략 설정 중앙 관리
- 로깅 시스템 전면 개선 (사이클 ID 부여, Custom Formatter, 외부 라이브러리 로그 억제)
- `test_balance.py`를 `test/` 폴더로 이동
- 기존 `main_gui.py`를 `backup/main_gui_v1.py`로 백업

### 2025-10-27
- 프로젝트 생성 및 초기 환경 설정 (Git, Python)
- PyQt6 기반 GUI 애플리케이션 골격 개발
- 주식 현재가 조회 기능 구현
- 계좌 잔고 조회 기능 구현 (보유 주식, 계좌 평가)
- 탭 인터페이스 및 데이터 그리드 뷰 적용
- 컬럼 선택 기능 및 한글 컬럼명 적용
- 핵심 로직과 GUI의 모듈화 리팩토링
- Git 연동 및 GitHub 저장소에 초기 버전 푸시
- 프로젝트 문서 구조화 및 작성