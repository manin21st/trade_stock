# -*- coding: utf-8 -*-
"""
main_gui.py - 전략 설정 및 로그 뷰어 GUI

이 스크립트는 자동매매 엔진(`main_cmd.py`)의 전략을 설정하고 실행 로그를
모니터링하기 위한 데스크톱 GUI 애플리케이션입니다.

주요 기능:
1.  **전략 설정**: `config.json` 파일에 저장되는 자동매매 전략의 파라미터(대상 종목, 매수/매도 조건, 루프 주기 등)를 직관적인 UI를 통해 수정하고 저장합니다.
2.  **실시간 로그 뷰어**: `main_cmd.py`가 생성하는 `main_cmd.log` 파일을 실시간으로 읽어와 화면에 표시합니다.
3.  **로그 필터링**: `cycle_id`를 기반으로 특정 실행 사이클의 로그만 필터링하여 볼 수 있어, 디버깅 및 매매 분석이 용이합니다.
"""

import sys
import json
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QCheckBox, QSpinBox, QDoubleSpinBox,
    QFormLayout, QGroupBox, QComboBox, QScrollArea, QTabWidget, QGridLayout
)
from PyQt6.QtCore import Qt

# --- Constants ---
CONFIG_FILE = 'json/config.json'
LOG_FILE = 'logs/main_cmd.log'

class MainWindow(QMainWindow):
    def __init__(self):
        """
        MainWindow 클래스의 생성자입니다.
        UI 초기화, 레이아웃 설정, 위젯 생성 및 시그널-슬롯 연결을 담당합니다.
        """
        super().__init__()
        self.setWindowTitle("Strategy Config & Log Viewer") # 윈도우 제목 설정
        self.setGeometry(150, 150, 1000, 700) # 윈도우 위치와 크기 설정

        # --- 메인 레이아웃 설정 ---
        central_widget = QWidget() # 중앙 위젯 생성
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget) # 중앙 위젯에 수직 레이아웃 적용

        self.tab_widget = QTabWidget() # 탭 위젯 생성 (설정 탭과 로그 뷰어 탭 포함)
        main_layout.addWidget(self.tab_widget)

        # --- 설정 탭 ---
        config_tab = QWidget() # 설정 탭 위젯 생성
        self.tab_widget.addTab(config_tab, "Configuration") # 탭 위젯에 설정 탭 추가
        config_tab_layout = QVBoxLayout(config_tab) # 설정 탭에 수직 레이아웃 적용

        config_scroll_area = QScrollArea() # 설정 내용을 스크롤할 수 있도록 스크롤 영역 생성
        config_scroll_area.setWidgetResizable(True) # 스크롤 영역 내 위젯 크기 조절 가능
        self.config_container_widget = QWidget() # 설정 그룹들을 담을 컨테이너 위젯
        config_scroll_area.setWidget(self.config_container_widget)
        self.config_main_layout = QVBoxLayout(self.config_container_widget) # 3단 레이아웃을 포함할 메인 레이아웃

        config_tab_layout.addWidget(config_scroll_area)

        # --- 설정 탭 레이아웃 (3단) ---
        config_grid_layout = QGridLayout() # 3단 구성을 위한 그리드 레이아웃
        config_grid_layout.setColumnStretch(0, 1) # 0번째 컬럼 너비 비율
        config_grid_layout.setColumnStretch(1, 1) # 1번째 컬럼 너비 비율
        config_grid_layout.setColumnStretch(2, 1) # 2번째 컬럼 너비 비율
        self.config_main_layout.addLayout(config_grid_layout)

        # 1열: 일반 설정 (간단한 매수/매도 조건 포함)
        general_group = QGroupBox("General Settings") # 일반 설정 그룹 박스
        general_form = QFormLayout() # 폼 레이아웃
        self.trading_mode_combo = QComboBox() # 거래 모드 콤보 박스
        self.trading_mode_combo.addItems(["실전투자 (real)", "모의투자 (paper)"])
        self.stock_input = QLineEdit() # 대상 종목 입력 필드
        self.interval_input = QSpinBox(maximum=86400, minimum=1, singleStep=1, suffix=" sec") # 반복 주기 스핀 박스
        general_form.addRow("실행 모드:", self.trading_mode_combo)
        general_form.addRow("대상 종목:", self.stock_input)
        general_form.addRow("반복 주기:", self.interval_input)
        
        # 통합된 간단 매수/매도 조건
        self.price_input = QSpinBox(maximum=10000000, singleStep=100) # 매수 목표 가격 스핀 박스
        self.trading_hours_check = QCheckBox("거래 시간 확인") # 거래 시간 확인 체크 박스
        self.cash_input = QSpinBox(maximum=100000000, singleStep=10000) # 최소 현금 보유액 스핀 박스
        self.profit_input = QDoubleSpinBox(maximum=100.0, minimum=-100.0, singleStep=0.5, suffix=" %") # 매도 목표 수익률 스핀 박스
        self.loss_input = QDoubleSpinBox(maximum=100.0, minimum=-100.0, singleStep=0.5, suffix=" %") # 매도 손절률 스핀 박스
        general_form.addRow("매수 목표 가격:", self.price_input)
        general_form.addRow("최소 현금 보유액:", self.cash_input)
        general_form.addRow(self.trading_hours_check)
        general_form.addRow("매도 목표 수익률:", self.profit_input)
        general_form.addRow("매도 손절률:", self.loss_input)

        # Forced Trade Settings
        self.forced_trade_enabled_check = QCheckBox("강제 매매 사용")
        self.forced_trade_type_combo = QComboBox()
        self.forced_trade_type_combo.addItems(["BUY", "SELL", "AUTO"])
        self.forced_stock_input = QLineEdit()
        self.forced_amount_input = QSpinBox(maximum=1000000000, singleStep=10000, suffix=" KRW")
        self.forced_amount_input.setMinimum(0)
        self.forced_quantity_input = QSpinBox(maximum=1000000, singleStep=1)
        self.forced_quantity_input.setMinimum(0)
        self.forced_price_input = QSpinBox(maximum=10000000, singleStep=100)
        self.forced_price_input.setMinimum(0) # 0 for market order
        self.forced_division_count_input = QSpinBox(maximum=100, minimum=0, singleStep=1) # 0 for no division
        self.forced_sell_profit_target_percent_input = QDoubleSpinBox(maximum=100.0, minimum=0.0, singleStep=0.1, suffix=" %")

        general_form.addRow(self.forced_trade_enabled_check)
        general_form.addRow("강제 매매 유형:", self.forced_trade_type_combo)
        general_form.addRow("강제 매매 종목:", self.forced_stock_input)
        general_form.addRow("강제 매매 수량:", self.forced_quantity_input)
        general_form.addRow("강제 매매 가격:", self.forced_price_input)
        general_form.addRow("매매 금액:", self.forced_amount_input)
        general_form.addRow("분할 횟수:", self.forced_division_count_input)
        general_form.addRow("매도 목표 수익률 (AUTO):", self.forced_sell_profit_target_percent_input)

        general_group.setLayout(general_form)
        config_grid_layout.addWidget(general_group, 0, 0)

        # 2열: 매수 조건 (기술적 분석 제외)
        buy_conditions_group = QGroupBox("매수 조건") # 매수 조건 그룹 박스
        buy_conditions_layout = QVBoxLayout(buy_conditions_group)
        buy_conditions_layout.addWidget(QLabel("기술적 분석 조건은 제거되었습니다.")) # 제거 안내 문구
        buy_conditions_layout.addWidget(QLabel("향후 추가 매수 조건 구현 예정")) # 향후 구현 예정 문구
        config_grid_layout.addWidget(buy_conditions_group, 0, 1)

        # 3열: 매도 조건 (기술적 분석 제외)
        sell_conditions_group = QGroupBox("매도 조건") # 매도 조건 그룹 박스
        sell_conditions_layout = QVBoxLayout(sell_conditions_group)
        sell_conditions_layout.addWidget(QLabel("기술적 분석 조건은 제거되었습니다.")) # 제거 안내 문구
        sell_conditions_layout.addWidget(QLabel("향후 추가 매도 조건 구현 예정")) # 향후 구현 예정 문구
        config_grid_layout.addWidget(sell_conditions_group, 0, 2)

        # --- 설정 저장 버튼 (설정 탭의 오른쪽 상단) ---
        save_button_container = QWidget() # 저장 버튼 컨테이너
        save_button_layout = QHBoxLayout(save_button_container)
        save_button_layout.addStretch() # 버튼을 오른쪽으로 밀기
        self.save_button = QPushButton("설정 저장") # 설정 저장 버튼
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; /* Blue */
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2; /* Darker Blue on hover */
            }
            QPushButton:pressed {
                background-color: #0D47A1; /* Even Darker Blue when pressed */
            }
        """)
        save_button_layout.addWidget(self.save_button)
        config_tab_layout.addWidget(save_button_container) # 설정 탭 레이아웃에 저장 버튼 컨테이너 추가
        config_tab_layout.addStretch() # 내용을 상단으로 밀어 올림

        # --- 로그 뷰어 탭 ---
        log_tab = QWidget() # 로그 뷰어 탭 위젯 생성
        self.tab_widget.addTab(log_tab, "Log Viewer") # 탭 위젯에 로그 뷰어 탭 추가
        log_tab_layout = QVBoxLayout(log_tab) # 로그 뷰어 탭에 수직 레이아웃 적용

        log_group = QGroupBox("Log Viewer") # 로그 뷰어 그룹 박스
        log_group_layout = QVBoxLayout(log_group)
        self.log_display = QTextEdit() # 로그를 표시할 텍스트 에디트
        self.log_display.setReadOnly(True) # 읽기 전용으로 설정
        self.full_log_content = "" # 전체 로그 내용을 저장할 변수

        filter_layout = QHBoxLayout() # 필터 레이아웃
        filter_label = QLabel("사이클 ID 필터:") # 사이클 ID 필터 라벨
        self.cycle_filter_combo = QComboBox() # 사이클 ID 필터 콤보 박스
        self.refresh_log_button = QPushButton("로그 새로고침") # 로그 새로고침 버튼
        self.refresh_log_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; /* Blue */
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2; /* Darker Blue on hover */
            }
            QPushButton:pressed {
                background-color: #0D47A1; /* Even Darker Blue when pressed */
            }
        """)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.cycle_filter_combo)
        filter_layout.addStretch() # 새로고침 버튼을 오른쪽으로 밀기
        filter_layout.addWidget(self.refresh_log_button)
        
        log_group_layout.addLayout(filter_layout)
        log_group_layout.addWidget(self.log_display)
        log_tab_layout.addWidget(log_group) # 로그 탭 레이아웃에 로그 그룹 추가

        # --- 시그널-슬롯 연결 ---
        self.save_button.clicked.connect(self.save_config) # 저장 버튼 클릭 시 save_config 호출
        self.refresh_log_button.clicked.connect(self.load_log) # 새로고침 버튼 클릭 시 load_log 호출
        self.cycle_filter_combo.currentIndexChanged.connect(self.filter_log_by_cycle) # 콤보 박스 선택 변경 시 filter_log_by_cycle 호출

        # --- 초기 로드 ---
        self.load_config() # 설정 파일 로드
        self.load_log() # 로그 파일 로드



    def load_config(self):
        """
        1. 전략 설정: `config.json` 파일에서 설정 값을 로드하여 GUI 요소에 반영합니다.
        파일이 없거나 로드 중 오류가 발생하면 기본값을 사용하거나 오류를 로깅합니다.
        """
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 일반 설정 로드
            mode = config.get('trading_mode', 'real')
            # 'paper' 모드면 콤보박스 인덱스 1 (모의투자), 아니면 0 (실전투자) 설정
            self.trading_mode_combo.setCurrentIndex(1 if mode == 'paper' else 0)

            strategy_config = config.get('strategy_A', {})
            self.stock_input.setText(strategy_config.get('target_stock', '')) # 대상 종목 설정
            self.interval_input.setValue(strategy_config.get('loop_interval_seconds', 300)) # 반복 주기 설정

            # 간단한 매수 조건 로드 (이제 일반 설정에 포함됨)
            buy_conditions = strategy_config.get('buy_conditions', {})
            self.price_input.setValue(buy_conditions.get('target_price', 0)) # 매수 목표 가격 설정
            self.trading_hours_check.setChecked(buy_conditions.get('check_trading_hours', False)) # 거래 시간 확인 체크박스 설정
            self.cash_input.setValue(buy_conditions.get('min_cash_amount', 0)) # 최소 현금 보유액 설정
            
            # 간단한 매도 조건 로드 (이제 일반 설정에 포함됨)
            sell_conditions = strategy_config.get('sell_conditions', {})
            self.profit_input.setValue(sell_conditions.get('target_profit_percent', 0.0)) # 매도 목표 수익률 설정
            self.loss_input.setValue(sell_conditions.get('stop_loss_percent', 0.0)) # 매도 손절률 설정

            # 기술적 분석 조건은 GUI에서 제거되었지만, config.json에 존재하면 그 값을 유지합니다.
            # 이는 main_cmd.py가 여전히 이 값을 사용할 수 있도록 보존하기 위함입니다.
            # GUI 위젯으로는 로드하지 않습니다.

            # Forced Trade
            forced_trade_config = config.get('forced_trade', {})
            self.forced_trade_enabled_check.setChecked(forced_trade_config.get('enabled', False))
            self.forced_trade_type_combo.setCurrentText(forced_trade_config.get('trade_type', 'BUY'))
            self.forced_stock_input.setText(forced_trade_config.get('stock_code', ''))
            self.forced_amount_input.setValue(forced_trade_config.get('amount', 0))
            self.forced_quantity_input.setValue(forced_trade_config.get('quantity', 0))
            self.forced_price_input.setValue(forced_trade_config.get('price', 0))
            self.forced_division_count_input.setValue(forced_trade_config.get('division_count', 0))
            self.forced_sell_profit_target_percent_input.setValue(forced_trade_config.get('sell_profit_target_percent', 0.0))

        except FileNotFoundError:
            logging.warning(f"{CONFIG_FILE} 파일을 찾을 수 없습니다. 기본값을 사용합니다.")
        except Exception as e:
            logging.error(f"설정 로드 중 오류 발생: {e}")

    def save_config(self):
        """
        1. 전략 설정: GUI 요소의 현재 값을 `config.json` 파일에 저장합니다.
        기술적 분석 조건은 GUI에서 제거되었지만, 기본값으로 설정하여 config.json 구조를 유지합니다.
        """
        # 현재 선택된 거래 모드 가져오기
        mode = "paper" if self.trading_mode_combo.currentIndex() == 1 else "real"
        
        # GUI에서 설정된 값을 바탕으로 config 사전 생성
        config = {
            "trading_mode": mode,
            "strategy_A": {
                "target_stock": self.stock_input.text(),
                "loop_interval_seconds": self.interval_input.value(),
                "buy_conditions": {
                    "target_price": self.price_input.value(),
                    "check_trading_hours": self.trading_hours_check.isChecked(),
                    "min_cash_amount": self.cash_input.value(),
                    # 기술적 분석 조건은 GUI에서 제거되었지만, config.json 구조 유지를 위해 기본값으로 저장
                    "technical_analysis": {
                        "moving_average_cross": {
                            "enabled": False, # GUI에서 제거됨
                            "short_term_days": 20,
                            "long_term_days": 60
                        },
                        "bollinger_bands": {
                            "enabled": False, # GUI에서 제거됨
                            "days": 20,
                            "std_dev": 2.0
                        },
                        "rsi": {
                            "enabled": False, # GUI에서 제거됨
                            "days": 14,
                            "buy_threshold": 30
                        }
                    }
                },
                "sell_conditions": {
                    "target_profit_percent": self.profit_input.value(),
                    "stop_loss_percent": self.loss_input.value(),
                    # 기술적 분석 조건은 GUI에서 제거되었지만, config.json 구조 유지를 위해 기본값으로 저장
                    "technical_analysis": {
                        "moving_average_cross": {
                            "enabled": False # GUI에서 제거됨
                        },
                        "bollinger_bands": {
                            "enabled": False # GUI에서 제거됨
                        },
                        "rsi": {
                            "enabled": False, # GUI에서 제거됨
                            "days": 14,
                            "sell_threshold": 70
                        }
                    }
                }
            },
            "forced_trade": {
                "enabled": self.forced_trade_enabled_check.isChecked(),
                "trade_type": self.forced_trade_type_combo.currentText(),
                "stock_code": self.forced_stock_input.text(),
                "amount": self.forced_amount_input.value(),
                "quantity": self.forced_quantity_input.value(),
                "price": self.forced_price_input.value(),
                "division_count": self.forced_division_count_input.value(),
                "sell_profit_target_percent": self.forced_sell_profit_target_percent_input.value()
            }
        }

        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False) # 가독성을 위해 들여쓰기 및 비 ASCII 문자 처리
            logging.info(f"설정 파일이 {CONFIG_FILE}에 저장되었습니다.")
            self.statusBar().showMessage("설정이 저장되었습니다!", 3000) # 3초간 상태바 메시지 표시
        except Exception as e:
            logging.error(f"설정 저장 중 오류 발생: {e}")
            self.statusBar().showMessage(f"설정 저장 오류: {e}", 5000) # 5초간 오류 메시지 표시

    def load_log(self):
        """
        2. 실시간 로그 뷰어: `main_cmd.log` 파일의 내용을 로드하여 텍스트 디스플레이에 표시합니다.
        3. 로그 필터링: 로그 파일에서 `cycle_id`를 추출하여 필터 콤보 박스를 채웁니다.
        """
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                self.full_log_content = f.read() # 전체 로그 내용을 변수에 저장
            
            self.log_display.setText(self.full_log_content) # 텍스트 디스플레이에 전체 로그 표시
            self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum()) # 스크롤을 최하단으로 이동
            
            cycle_ids = set() # 중복 없는 cycle_id를 저장하기 위한 set
            for line in self.full_log_content.splitlines():
                if line.startswith("[#"): # cycle_id가 포함된 라인 필터링
                    try:
                        end_idx = line.find("]")
                        if end_idx != -1:
                            cycle_id = line[2:end_idx] # "[#" 다음부터 "]" 전까지 추출
                            cycle_ids.add(cycle_id)
                    except Exception:
                        pass # 파싱 오류는 무시

            # 콤보 박스 시그널 블록 (항목 변경 시 불필요한 필터링 방지)
            self.cycle_filter_combo.blockSignals(True)
            self.cycle_filter_combo.clear() # 기존 항목 초기화
            self.cycle_filter_combo.addItem("--- 전체 보기 ---") # 전체 보기 옵션 추가
            sorted_cycle_ids = sorted(list(cycle_ids), reverse=True) # cycle_id를 내림차순 정렬
            self.cycle_filter_combo.addItems(sorted_cycle_ids) # 정렬된 cycle_id 추가
            self.cycle_filter_combo.blockSignals(False) # 시그널 블록 해제

        except FileNotFoundError:
            self.log_display.setText(f"--- 로그 파일 '{LOG_FILE}'을 찾을 수 없습니다. ---")
        except Exception as e:
            self.log_display.setText(f"--- 로그 파일 로드 중 오류 발생: {e} ---")

    def filter_log_by_cycle(self, index):
        """
        3. 로그 필터링: 선택된 `cycle_id`를 기반으로 로그 디스플레이를 필터링합니다.
        '--- 전체 보기 ---'가 선택되면 전체 로그를 표시합니다.
        """
        selected_cycle_id = self.cycle_filter_combo.currentText() # 현재 선택된 cycle_id 가져오기
        
        if selected_cycle_id == "--- 전체 보기 ---":
            self.log_display.setText(self.full_log_content) # 전체 로그 표시
        else:
            # 선택된 cycle_id를 포함하는 라인만 필터링
            filtered_log = [line for line in self.full_log_content.splitlines() if f"[{selected_cycle_id}]" in line or f"[#{selected_cycle_id}]" in line]
            self.log_display.setText("\n".join(filtered_log)) # 필터링된 로그 표시
        
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum()) # 스크롤을 최하단으로 이동


if __name__ == "__main__":
    # GUI 애플리케이션의 로깅 설정을 구성합니다.
    # main_cmd.py와 독립적으로 작동하며, GUI 내부에서 발생하는 오류 등을 기록합니다.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = QApplication(sys.argv) # QApplication 인스턴스 생성
    main_win = MainWindow() # MainWindow 인스턴스 생성
    main_win.show() # 메인 윈도우 표시
    sys.exit(app.exec()) # 애플리케이션 실행 시작 (이벤트 루프 진입)
