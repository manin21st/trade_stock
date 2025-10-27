# 변경 이력 (Changelog)

## 2025-10-27

### 추가 (Added)

- **프로젝트 초기 설정**
  - `koreainvestment/open-trading-api` Git 저장소 복제
  - Python 종속성(`requirements.txt`) 설치
- **GUI 애플리케이션 (`main_gui.py`) 개발**
  - PyQt6 기반의 기본 GUI 윈도우 생성
  - 시세 조회 기능 추가 및 표(그리드) 뷰에 결과 표시
  - 계좌 잔고 조회 기능 추가 (보유 주식, 계좌 평가)
  - 탭(Tab) 인터페이스를 도입하여 각 기능 분리
  - 컬럼 선택 기능을 추가하여 사용자가 원하는 데이터만 볼 수 있도록 개선
- **프로젝트 아키텍처 리팩토링**
  - 핵심 로직(`core_logic.py`)과 GUI(`main_gui.py`) 코드 분리
  - API 컬럼명 매핑 정보(`column_mappings.py`)를 별도 파일로 분리
- **버전 관리 및 문서화**
  - Git 저장소 초기화 및 GitHub 연동
  - `.gitignore` 파일 추가
  - 프로젝트 지침서 (`GEMINI.md`) 작성
  - 프로젝트 관리 파일 (`MANAGEMENT.md`) 및 변경 이력 파일 (`CHANGELOG.md`) 생성

### 수정 (Changed)

- API 호출 파라미터 오류 수정 (`inquire_balance`)
- API 인증 정보(`kis_devlp.yaml`) 참조 경로 문제 해결
- GUI의 데이터 표시 방식을 단순 텍스트 로그에서 그리드 뷰로 변경
- API 응답의 영문 컬럼명을 한글로 변환하여 표시

### 수정 (Fixed)

- 다수의 API 인증 및 설정 오류 디버깅
- Python 경로 문제로 인한 `ModuleNotFoundError` 해결
