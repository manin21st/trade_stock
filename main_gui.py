# -*- coding: utf-8 -*-

"""
A simplified GUI to configure strategy conditions and view logs.
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
CONFIG_FILE = 'config.json'
LOG_FILE = 'main_cmd.log'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Strategy Config & Log Viewer")
        self.setGeometry(150, 150, 1000, 700)

        # --- Main Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget) # Use QVBoxLayout for the main layout

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- Configuration Tab ---
        config_tab = QWidget()
        self.tab_widget.addTab(config_tab, "Configuration")
        config_tab_layout = QVBoxLayout(config_tab) # Layout for the config tab

        config_scroll_area = QScrollArea()
        config_scroll_area.setWidgetResizable(True)
        self.config_container_widget = QWidget() # A container widget for the config groups
        config_scroll_area.setWidget(self.config_container_widget)
        self.config_main_layout = QVBoxLayout(self.config_container_widget) # This will hold the 3-column layout

        config_tab_layout.addWidget(config_scroll_area)

        # --- Configuration Tab Layout (3 columns) ---
        config_grid_layout = QGridLayout()
        config_grid_layout.setColumnStretch(0, 1) # Equal width for column 0
        config_grid_layout.setColumnStretch(1, 1) # Equal width for column 1
        config_grid_layout.setColumnStretch(2, 1) # Equal width for column 2
        self.config_main_layout.addLayout(config_grid_layout)

        # Column 1: General Settings (now includes simple buy/sell conditions)
        general_group = QGroupBox("General Settings")
        general_form = QFormLayout()
        self.trading_mode_combo = QComboBox()
        self.trading_mode_combo.addItems(["실전투자 (real)", "모의투자 (paper)"])
        self.stock_input = QLineEdit()
        self.interval_input = QSpinBox(maximum=86400, minimum=1, singleStep=1, suffix=" sec")
        general_form.addRow("실행 모드:", self.trading_mode_combo)
        general_form.addRow("대상 종목:", self.stock_input)
        general_form.addRow("반복 주기:", self.interval_input)
        
        # Merged Simple Buy/Sell Conditions
        self.price_input = QSpinBox(maximum=10000000, singleStep=100)
        self.trading_hours_check = QCheckBox("거래 시간 확인")
        self.cash_input = QSpinBox(maximum=100000000, singleStep=10000)
        self.profit_input = QDoubleSpinBox(maximum=100.0, minimum=-100.0, singleStep=0.5, suffix=" %")
        self.loss_input = QDoubleSpinBox(maximum=100.0, minimum=-100.0, singleStep=0.5, suffix=" %")
        general_form.addRow("매수 목표 가격:", self.price_input)
        general_form.addRow("최소 현금 보유액:", self.cash_input)
        general_form.addRow(self.trading_hours_check)
        general_form.addRow("매도 목표 수익률:", self.profit_input)
        general_form.addRow("매도 손절률:", self.loss_input)
        general_group.setLayout(general_form)
        config_grid_layout.addWidget(general_group, 0, 0)

        # Column 2: Buy Conditions (without TA)
        buy_conditions_group = QGroupBox("매수 조건")
        buy_conditions_layout = QVBoxLayout(buy_conditions_group)
        buy_conditions_layout.addWidget(QLabel("기술적 분석 조건은 제거되었습니다."))
        buy_conditions_layout.addWidget(QLabel("향후 추가 매수 조건 구현 예정"))
        config_grid_layout.addWidget(buy_conditions_group, 0, 1)

        # Column 3: Sell Conditions (without TA)
        sell_conditions_group = QGroupBox("매도 조건")
        sell_conditions_layout = QVBoxLayout(sell_conditions_group)
        sell_conditions_layout.addWidget(QLabel("기술적 분석 조건은 제거되었습니다."))
        sell_conditions_layout.addWidget(QLabel("향후 추가 매도 조건 구현 예정"))
        config_grid_layout.addWidget(sell_conditions_group, 0, 2)

        # --- Save Button (Top Right of Config Tab) ---
        save_button_container = QWidget()
        save_button_layout = QHBoxLayout(save_button_container)
        save_button_layout.addStretch()
        self.save_button = QPushButton("설정 저장")
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
        config_tab_layout.addWidget(save_button_container) # Add to config_tab_layout, not config_main_layout
        config_tab_layout.addStretch() # Push content to top

        # --- Log Viewer Tab ---
        log_tab = QWidget()
        self.tab_widget.addTab(log_tab, "Log Viewer")
        log_tab_layout = QVBoxLayout(log_tab) # Layout for the log tab

        log_group = QGroupBox("Log Viewer") # Keep the group box for visual consistency
        log_group_layout = QVBoxLayout(log_group)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.full_log_content = ""

        filter_layout = QHBoxLayout()
        filter_label = QLabel("사이클 ID 필터:")
        self.cycle_filter_combo = QComboBox()
        self.refresh_log_button = QPushButton("로그 새로고침")
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
        filter_layout.addStretch() # Push refresh button to the right
        filter_layout.addWidget(self.refresh_log_button)
        
        log_group_layout.addLayout(filter_layout)
        log_group_layout.addWidget(self.log_display)
        log_tab_layout.addWidget(log_group) # Add the log_group to the log_tab_layout

        # --- Connections ---
        self.save_button.clicked.connect(self.save_config)
        self.refresh_log_button.clicked.connect(self.load_log)
        self.cycle_filter_combo.currentIndexChanged.connect(self.filter_log_by_cycle)

        # --- Initial Load ---
        self.load_config()
        self.load_log()



    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # General
            mode = config.get('trading_mode', 'real')
            self.trading_mode_combo.setCurrentIndex(1 if mode == 'paper' else 0)

            strategy_config = config.get('strategy_A', {})
            self.stock_input.setText(strategy_config.get('target_stock', ''))
            self.interval_input.setValue(strategy_config.get('loop_interval_seconds', 300))

            # Simple Conditions (now part of General Settings)
            buy_conditions = strategy_config.get('buy_conditions', {})
            self.price_input.setValue(buy_conditions.get('target_price', 0))
            self.trading_hours_check.setChecked(buy_conditions.get('check_trading_hours', False))
            self.cash_input.setValue(buy_conditions.get('min_cash_amount', 0))
            
            sell_conditions = strategy_config.get('sell_conditions', {})
            self.profit_input.setValue(sell_conditions.get('target_profit_percent', 0.0))
            self.loss_input.setValue(sell_conditions.get('stop_loss_percent', 0.0))

            # Technical Analysis conditions are removed from GUI, but keep their values if they exist in config.json
            # This ensures that if main_cmd.py still uses them, they are preserved.
            # We will not load them into GUI widgets as those widgets no longer exist.

        except FileNotFoundError:
            logging.warning(f"{CONFIG_FILE} not found. Using default values.")
        except Exception as e:
            logging.error(f"Error loading config: {e}")

    def save_config(self):
        mode = "paper" if self.trading_mode_combo.currentIndex() == 1 else "real"
        
        config = {
            "trading_mode": mode,
            "strategy_A": {
                "target_stock": self.stock_input.text(),
                "loop_interval_seconds": self.interval_input.value(),
                "buy_conditions": {
                    "target_price": self.price_input.value(),
                    "check_trading_hours": self.trading_hours_check.isChecked(),
                    "min_cash_amount": self.cash_input.value(),
                    # Technical Analysis conditions are removed from GUI, but keep their values if they exist in config.json
                    # This ensures that if main_cmd.py still uses them, they are preserved.
                    "technical_analysis": {
                        "moving_average_cross": {
                            "enabled": False, # Removed from GUI
                            "short_term_days": 20,
                            "long_term_days": 60
                        },
                        "bollinger_bands": {
                            "enabled": False, # Removed from GUI
                            "days": 20,
                            "std_dev": 2.0
                        },
                        "rsi": {
                            "enabled": False, # Removed from GUI
                            "days": 14,
                            "buy_threshold": 30
                        }
                    }
                },
                "sell_conditions": {
                    "target_profit_percent": self.profit_input.value(),
                    "stop_loss_percent": self.loss_input.value(),
                    # Technical Analysis conditions are removed from GUI, but keep their values if they exist in config.json
                    # This ensures that if main_cmd.py still uses them, they are preserved.
                    "technical_analysis": {
                        "moving_average_cross": {
                            "enabled": False # Removed from GUI
                        },
                        "bollinger_bands": {
                            "enabled": False # Removed from GUI
                        },
                        "rsi": {
                            "enabled": False, # Removed from GUI
                            "days": 14,
                            "sell_threshold": 70
                        }
                    }
                }
            }
        }

        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logging.info(f"Configuration saved to {CONFIG_FILE}")
            self.statusBar().showMessage("설정이 저장되었습니다!", 3000) # Show message for 3 seconds
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            self.statusBar().showMessage(f"설정 저장 오류: {e}", 5000) # Show error message for 5 seconds

    def load_log(self):
        """Loads the content of the log file into the text display and populates cycle filter."""
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                self.full_log_content = f.read()
            
            self.log_display.setText(self.full_log_content)
            self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())
            
            cycle_ids = set()
            for line in self.full_log_content.splitlines():
                if line.startswith("[#"):
                    try:
                        end_idx = line.find("]")
                        if end_idx != -1:
                            cycle_id = line[2:end_idx]
                            cycle_ids.add(cycle_id)
                    except Exception:
                        pass
            
            self.cycle_filter_combo.blockSignals(True)
            self.cycle_filter_combo.clear()
            self.cycle_filter_combo.addItem("--- 전체 보기 ---")
            sorted_cycle_ids = sorted(list(cycle_ids), reverse=True)
            self.cycle_filter_combo.addItems(sorted_cycle_ids)
            self.cycle_filter_combo.blockSignals(False)

        except FileNotFoundError:
            self.log_display.setText(f"--- Log file '{LOG_FILE}' not found. ---")
        except Exception as e:
            self.log_display.setText(f"--- Error loading log file: {e} ---")

    def filter_log_by_cycle(self, index):
        """Filters the log display based on the selected cycle ID."""
        selected_cycle_id = self.cycle_filter_combo.currentText()
        
        if selected_cycle_id == "--- 전체 보기 ---":
            self.log_display.setText(self.full_log_content)
        else:
            filtered_log = [line for line in self.full_log_content.splitlines() if f"[{selected_cycle_id}]" in line or f"[#{selected_cycle_id}]" in line]
            self.log_display.setText("\n".join(filtered_log))
        
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
