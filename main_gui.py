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
    QFormLayout, QGroupBox, QComboBox, QScrollArea
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
        main_layout = QHBoxLayout(central_widget)

        # --- Left Side: Config ---
        config_scroll_area = QScrollArea()
        config_scroll_area.setWidgetResizable(True)
        config_group = QGroupBox("Strategy Configuration")
        config_layout = QVBoxLayout(config_group)

        # --- General Settings ---
        general_group = QGroupBox("General Settings")
        general_form = QFormLayout()
        self.trading_mode_combo = QComboBox()
        self.trading_mode_combo.addItems(["실전투자 (real)", "모의투자 (paper)"])
        self.stock_input = QLineEdit()
        self.interval_input = QSpinBox(maximum=86400, minimum=1, singleStep=1, suffix=" sec")
        general_form.addRow("실행 모드:", self.trading_mode_combo)
        general_form.addRow("Target Stock:", self.stock_input)
        general_form.addRow("Loop Interval:", self.interval_input)
        general_group.setLayout(general_form)

        # --- Simple Buy/Sell Conditions ---
        simple_conditions_group = QGroupBox("Simple Buy/Sell Conditions")
        simple_form = QFormLayout()
        self.price_input = QSpinBox(maximum=10000000, singleStep=100)
        self.trading_hours_check = QCheckBox("Check Trading Hours")
        self.cash_input = QSpinBox(maximum=100000000, singleStep=10000)
        self.profit_input = QDoubleSpinBox(maximum=100.0, minimum=-100.0, singleStep=0.5, suffix=" %")
        self.loss_input = QDoubleSpinBox(maximum=100.0, minimum=-100.0, singleStep=0.5, suffix=" %")
        simple_form.addRow("Buy Target Price:", self.price_input)
        simple_form.addRow("Buy Min Cash:", self.cash_input)
        simple_form.addRow(self.trading_hours_check)
        simple_form.addRow("Sell Target Profit:", self.profit_input)
        simple_form.addRow("Sell Stop Loss:", self.loss_input)
        simple_conditions_group.setLayout(simple_form)

        # --- Technical Analysis Buy Conditions ---
        buy_ta_group = self._create_buy_ta_group()

        # --- Technical Analysis Sell Conditions ---
        sell_ta_group = self._create_sell_ta_group()

        # --- Save Button ---
        self.save_button = QPushButton("Save Configuration")

        # --- Assemble Config Layout ---
        config_layout.addWidget(general_group)
        config_layout.addWidget(simple_conditions_group)
        config_layout.addWidget(buy_ta_group)
        config_layout.addWidget(sell_ta_group)
        config_layout.addWidget(self.save_button)
        config_layout.addStretch()
        
        config_scroll_area.setWidget(config_group)

        # --- Right Side: Log Viewer ---
        log_group = QGroupBox("Log Viewer")
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.full_log_content = ""

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
        main_layout.addWidget(config_scroll_area, 1)
        main_layout.addWidget(log_group, 2)

        # --- Connections ---
        self.save_button.clicked.connect(self.save_config)
        self.refresh_log_button.clicked.connect(self.load_log)
        self.cycle_filter_combo.currentIndexChanged.connect(self.filter_log_by_cycle)

        # --- Initial Load ---
        self.load_config()
        self.load_log()

    def _create_buy_ta_group(self):
        group = QGroupBox("매수 조건 (기술적 분석)")
        layout = QVBoxLayout(group)

        # MA Cross
        ma_group = QGroupBox("이동평균선 교차")
        self.buy_ma_check = QCheckBox("활성화", ma_group) # Use QCheckBox for enabled state
        ma_form = QFormLayout(ma_group)
        ma_form.addRow(self.buy_ma_check)
        self.buy_ma_short = QSpinBox(minimum=1, maximum=200)
        self.buy_ma_long = QSpinBox(minimum=1, maximum=200)
        ma_form.addRow("단기 기간(일):", self.buy_ma_short)
        ma_form.addRow("장기 기간(일):", self.buy_ma_long)
        
        # Bollinger Bands
        bb_group = QGroupBox("볼린저 밴드")
        self.buy_bb_check = QCheckBox("활성화", bb_group) # Use QCheckBox for enabled state
        bb_form = QFormLayout(bb_group)
        bb_form.addRow(self.buy_bb_check)
        self.buy_bb_days = QSpinBox(minimum=1, maximum=200)
        self.buy_bb_std = QDoubleSpinBox(minimum=0.1, maximum=5.0, singleStep=0.1)
        bb_form.addRow("기간(일):", self.buy_bb_days)
        bb_form.addRow("표준편차:", self.buy_bb_std)

        # RSI
        rsi_group = QGroupBox("RSI (상대강도지수)")
        self.buy_rsi_check = QCheckBox("활성화", rsi_group) # Use QCheckBox for enabled state
        rsi_form = QFormLayout(rsi_group)
        rsi_form.addRow(self.buy_rsi_check)
        self.buy_rsi_days = QSpinBox(minimum=1, maximum=200)
        self.buy_rsi_threshold = QSpinBox(minimum=1, maximum=100)
        rsi_form.addRow("기간(일):", self.buy_rsi_days)
        rsi_form.addRow("매수 기준값 (이하):", self.buy_rsi_threshold)

        layout.addWidget(ma_group)
        layout.addWidget(bb_group)
        layout.addWidget(rsi_group)
        return group

    def _create_sell_ta_group(self):
        group = QGroupBox("매도 조건 (기술적 분석)")
        layout = QVBoxLayout(group)

        # MA Cross
        ma_group = QGroupBox("이동평균선 교차")
        self.sell_ma_check = QCheckBox("활성화", ma_group) # Use QCheckBox for enabled state
        ma_form = QFormLayout(ma_group)
        ma_form.addRow(self.sell_ma_check)
        
        # Bollinger Bands
        bb_group = QGroupBox("볼린저 밴드")
        self.sell_bb_check = QCheckBox("활성화", bb_group) # Use QCheckBox for enabled state
        bb_form = QFormLayout(bb_group)
        bb_form.addRow(self.sell_bb_check)

        # RSI
        rsi_group = QGroupBox("RSI (상대강도지수)")
        self.sell_rsi_check = QCheckBox("활성화", rsi_group) # Use QCheckBox for enabled state
        rsi_form = QFormLayout(rsi_group)
        rsi_form.addRow(self.sell_rsi_check)
        self.sell_rsi_days = QSpinBox(minimum=1, maximum=200)
        self.sell_rsi_threshold = QSpinBox(minimum=1, maximum=100)
        rsi_form.addRow("기간(일):", self.sell_rsi_days)
        rsi_form.addRow("매도 기준값 (이상):", self.sell_rsi_threshold)

        layout.addWidget(ma_group)
        layout.addWidget(bb_group)
        layout.addWidget(rsi_group)
        return group

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

            # Simple Conditions
            buy_conditions = strategy_config.get('buy_conditions', {})
            self.price_input.setValue(buy_conditions.get('target_price', 0))
            self.trading_hours_check.setChecked(buy_conditions.get('check_trading_hours', False))
            self.cash_input.setValue(buy_conditions.get('min_cash_amount', 0))
            
            sell_conditions = strategy_config.get('sell_conditions', {})
            self.profit_input.setValue(sell_conditions.get('target_profit_percent', 0.0))
            self.loss_input.setValue(sell_conditions.get('stop_loss_percent', 0.0))

            # TA Buy Conditions
            buy_ta = buy_conditions.get('technical_analysis', {})
            buy_ma = buy_ta.get('moving_average_cross', {})
            self.buy_ma_check.setChecked(buy_ma.get('enabled', False))
            self.buy_ma_short.setValue(buy_ma.get('short_term_days', 20))
            self.buy_ma_long.setValue(buy_ma.get('long_term_days', 60))
            
            buy_bb = buy_ta.get('bollinger_bands', {})
            self.buy_bb_check.setChecked(buy_bb.get('enabled', False))
            self.buy_bb_days.setValue(buy_bb.get('days', 20))
            self.buy_bb_std.setValue(buy_bb.get('std_dev', 2.0))

            buy_rsi = buy_ta.get('rsi', {})
            self.buy_rsi_check.setChecked(buy_rsi.get('enabled', False))
            self.buy_rsi_days.setValue(buy_rsi.get('days', 14))
            self.buy_rsi_threshold.setValue(buy_rsi.get('buy_threshold', 30))

            # TA Sell Conditions
            sell_ta = sell_conditions.get('technical_analysis', {})
            self.sell_ma_check.setChecked(sell_ta.get('moving_average_cross', {}).get('enabled', False))
            self.sell_bb_check.setChecked(sell_ta.get('bollinger_bands', {}).get('enabled', False))
            
            sell_rsi = sell_ta.get('rsi', {})
            self.sell_rsi_check.setChecked(sell_rsi.get('enabled', False))
            self.sell_rsi_days.setValue(sell_rsi.get('days', 14))
            self.sell_rsi_threshold.setValue(sell_rsi.get('sell_threshold', 70))

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
                    "technical_analysis": {
                        "moving_average_cross": {
                            "enabled": self.buy_ma_check.isChecked(),
                            "short_term_days": self.buy_ma_short.value(),
                            "long_term_days": self.buy_ma_long.value()
                        },
                        "bollinger_bands": {
                            "enabled": self.buy_bb_check.isChecked(),
                            "days": self.buy_bb_days.value(),
                            "std_dev": self.buy_bb_std.value()
                        },
                        "rsi": {
                            "enabled": self.buy_rsi_check.isChecked(),
                            "days": self.buy_rsi_days.value(),
                            "buy_threshold": self.buy_rsi_threshold.value()
                        }
                    }
                },
                "sell_conditions": {
                    "target_profit_percent": self.profit_input.value(),
                    "stop_loss_percent": self.loss_input.value(),
                    "technical_analysis": {
                        "moving_average_cross": {
                            "enabled": self.sell_ma_check.isChecked()
                        },
                        "bollinger_bands": {
                            "enabled": self.sell_bb_check.isChecked()
                        },
                        "rsi": {
                            "enabled": self.sell_rsi_check.isChecked(),
                            "days": self.sell_rsi_days.value(),
                            "sell_threshold": self.sell_rsi_threshold.value()
                        }
                    }
                }
            }
        }

        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logging.info(f"Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            logging.error(f"Error saving config: {e}")

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
