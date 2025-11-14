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
    QFormLayout, QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt

# --- Constants ---
CONFIG_FILE = 'config.json'
LOG_FILE = 'main_cmd.log'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Strategy Config & Log Viewer")
        self.setGeometry(150, 150, 800, 600)

        # --- Main Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Left Side: Config ---
        config_group = QGroupBox("Strategy A Configuration")
        form_layout = QFormLayout()

        self.stock_input = QLineEdit()
        self.price_input = QSpinBox(maximum=10000000, singleStep=100)
        self.trading_hours_check = QCheckBox("Check Trading Hours")
        self.cash_input = QSpinBox(maximum=100000000, singleStep=10000)
        self.profit_input = QDoubleSpinBox(maximum=100.0, minimum=-100.0, singleStep=0.5, suffix=" %")
        self.loss_input = QDoubleSpinBox(maximum=100.0, minimum=-100.0, singleStep=0.5, suffix=" %")
        self.interval_input = QSpinBox(maximum=86400, minimum=1, singleStep=1, suffix=" sec")

        form_layout.addRow("Target Stock:", self.stock_input)
        form_layout.addRow("Loop Interval:", self.interval_input)
        form_layout.addRow("Buy Target Price:", self.price_input)
        form_layout.addRow("Buy Min Cash:", self.cash_input)
        form_layout.addRow(self.trading_hours_check)
        form_layout.addRow("Sell Target Profit:", self.profit_input)
        form_layout.addRow("Sell Stop Loss:", self.loss_input)
        
        self.save_button = QPushButton("Save Configuration")
        
        config_layout = QVBoxLayout()
        config_layout.addLayout(form_layout)
        config_layout.addWidget(self.save_button)
        config_layout.addStretch()
        config_group.setLayout(config_layout)

        # --- Right Side: Log Viewer ---
        log_group = QGroupBox("Log Viewer")
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.full_log_content = "" # 전체 로그 내용을 저장할 변수

        # 필터링 UI
        filter_layout = QHBoxLayout()
        self.cycle_filter_combo = QComboBox()
        self.refresh_log_button = QPushButton("로그 새로고침")
        filter_layout.addWidget(QLabel("사이클 ID 필터:"))
        filter_layout.addWidget(self.cycle_filter_combo)
        filter_layout.addWidget(self.refresh_log_button)
        
        log_layout = QVBoxLayout()
        log_layout.addLayout(filter_layout)
        log_layout.addWidget(self.log_display)
        log_group.setLayout(log_layout)

        # --- Combine Layouts ---
        main_layout.addWidget(config_group, 1) # 1/3 of the space
        main_layout.addWidget(log_group, 2)    # 2/3 of the space

        # --- Connections ---
        self.save_button.clicked.connect(self.save_config)
        self.refresh_log_button.clicked.connect(self.load_log) # 새로고침 버튼 연결
        self.cycle_filter_combo.currentIndexChanged.connect(self.filter_log_by_cycle) # 콤보박스 변경 시 필터링

        # --- Initial Load ---
        self.load_config()
        self.load_log()

    def load_config(self):
        """Loads configuration from the JSON file and populates the UI."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            strategy_config = config.get('strategy_A', {})
            buy_conditions = strategy_config.get('buy_conditions', {})
            sell_conditions = strategy_config.get('sell_conditions', {})

            self.stock_input.setText(strategy_config.get('target_stock', ''))
            self.interval_input.setValue(strategy_config.get('loop_interval_seconds', 300))
            self.price_input.setValue(buy_conditions.get('target_price', 0))
            self.trading_hours_check.setChecked(buy_conditions.get('check_trading_hours', False))
            self.cash_input.setValue(buy_conditions.get('min_cash_amount', 0))
            self.profit_input.setValue(sell_conditions.get('target_profit_percent', 0.0))
            self.loss_input.setValue(sell_conditions.get('stop_loss_percent', 0.0))
            
            logging.info(f"Configuration loaded from {CONFIG_FILE}")

        except FileNotFoundError:
            logging.warning(f"{CONFIG_FILE} not found. Using default values.")
        except Exception as e:
            logging.error(f"Error loading config: {e}")

    def save_config(self):
        """Saves the current UI settings to the JSON file."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {} # Start with a new dict if file is bad or doesn't exist

        config['strategy_A'] = {
            'target_stock': self.stock_input.text(),
            'loop_interval_seconds': self.interval_input.value(),
            'buy_conditions': {
                'target_price': self.price_input.value(),
                'check_trading_hours': self.trading_hours_check.isChecked(),
                'min_cash_amount': self.cash_input.value()
            },
            'sell_conditions': {
                'target_profit_percent': self.profit_input.value(),
                'stop_loss_percent': self.loss_input.value()
            }
        }

        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            logging.info(f"Configuration saved to {CONFIG_FILE}")
            # You might want a status bar message here
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    def load_log(self):
        """Loads the content of the log file into the text display and populates cycle filter."""
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                self.full_log_content = f.read()
            
            self.log_display.setText(self.full_log_content)
            self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum()) # Scroll to bottom
            logging.info(f"Log file {LOG_FILE} loaded.")

            # Extract unique cycle IDs
            cycle_ids = set()
            for line in self.full_log_content.splitlines():
                # New format: [#YYYYMMDDHHMMSS]
                if line.startswith("[#"):
                    try:
                        start_idx = line.find("#")
                        end_idx = line.find("]", start_idx)
                        if start_idx != -1 and end_idx != -1:
                            cycle_id = line[start_idx + 1 : end_idx] # Remove '#' and ']'
                            cycle_ids.add(cycle_id)
                    except Exception as e:
                        logging.warning(f"Error parsing cycle_id from log line: {line[:100]}... Error: {e}")
            
            # Populate combo box
            self.cycle_filter_combo.clear()
            self.cycle_filter_combo.addItem("--- 전체 보기 ---")
            sorted_cycle_ids = sorted(list(cycle_ids), reverse=True) # 최신 사이클부터
            self.cycle_filter_combo.addItems(sorted_cycle_ids)

        except FileNotFoundError:
            self.log_display.setText(f"--- Log file '{LOG_FILE}' not found. ---")
            self.full_log_content = ""
            self.cycle_filter_combo.clear()
            self.cycle_filter_combo.addItem("--- 전체 보기 ---")
        except Exception as e:
            self.log_display.setText(f"--- Error loading log file: {e} ---")
            self.full_log_content = ""
            self.cycle_filter_combo.clear()
            self.cycle_filter_combo.addItem("--- 전체 보기 ---")

    def filter_log_by_cycle(self, index):
        """Filters the log display based on the selected cycle ID."""
        selected_cycle_id = self.cycle_filter_combo.currentText()
        
        if selected_cycle_id == "--- 전체 보기 ---":
            self.log_display.setText(self.full_log_content)
        else:
            filtered_log = []
            for line in self.full_log_content.splitlines():
                if selected_cycle_id in line:
                    filtered_log.append(line)
            self.log_display.setText("\n".join(filtered_log))
        
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum()) # Scroll to bottom


if __name__ == "__main__":
    # Set up basic logging for the GUI itself
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
