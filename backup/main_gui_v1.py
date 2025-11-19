import sys
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QTextEdit, QPushButton, QTableView, QSplitter,
    QDialog, QListWidget, QListWidgetItem,
    QDialogButtonBox, QTabWidget, QHBoxLayout
)
from PyQt6.QtCore import QAbstractTableModel, Qt
import pandas as pd

# Import the new refactored modules
import core_logic
from column_mappings import (
    ALL_COLUMN_MAPPINGS, REVERSE_COLUMN_MAPPING, 
    PRICE_COLUMN_MAPPING, BALANCE_COLUMN_MAPPING
)

# --- GUI Classes ---

class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.append(msg)

class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role == Qt.ItemDataRole.DisplayRole:
            return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            col_name = self._data.columns[section]
            return ALL_COLUMN_MAPPINGS.get(col_name, col_name)
        return None

class ColumnSelectionDialog(QDialog):
    def __init__(self, all_columns, selected_columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("컬럼 선택")
        
        self.list_widget = QListWidget()
        for col in all_columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if col in selected_columns else Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
            
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def get_selected_columns(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KIS Trading Program")
        self.setGeometry(100, 100, 1024, 768)
        
        # --- Data State ---
        # Get all possible column names by combining the keys of all mapping dictionaries
        all_price_cols = list(PRICE_COLUMN_MAPPING.values()) + [v for v in ALL_COLUMN_MAPPINGS.values() if v not in PRICE_COLUMN_MAPPING.values()]

        self.data_views = {
            "시세": {"data": None, 
                     "all_cols": list(dict.fromkeys(all_price_cols)), # Remove duplicates
                     "selected_cols": ['상품명', '주식 단축 종목코드', '주식 현재가', '전일 대비', '전일 대비율', '누적 거래량', '누적 거래 대금']},
            "보유 주식": {"data": None, "all_cols": list(BALANCE_COLUMN_MAPPING.values()), "selected_cols": ['상품번호', '상품명', '보유수량', '매입평균가격', '매입금액', '현재가', '평가금액', '평가손익금액', '평가손익율']},
            "계좌 평가": {"data": None, "all_cols": list(BALANCE_COLUMN_MAPPING.values()), "selected_cols": ['예수금총금액', '유가평가금액', '총평가금액', '순자산금액', '총대출금액', '매입금액합계금액', '평가금액합계금액', '평가손익합계금액']}
        }
        self.tabs = {}

        # --- Widgets & Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()
        self.log_widget = QTextEditLogger(self)
        self.log_widget.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.log_widget)
        logging.getLogger().setLevel(logging.INFO)

        button_layout = QHBoxLayout()
        self.inquire_price_button = QPushButton("현재가 조회 (005930)")
        self.inquire_balance_button = QPushButton("계좌 잔고 조회")
        self.select_columns_button = QPushButton("현재 탭 컬럼 선택")
        button_layout.addWidget(self.inquire_price_button)
        button_layout.addWidget(self.inquire_balance_button)
        button_layout.addWidget(self.select_columns_button)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.tab_widget)
        splitter.addWidget(self.log_widget.widget)
        splitter.setSizes([550, 200])

        main_layout.addLayout(button_layout)
        main_layout.addWidget(splitter)

        self.add_tab("시세")
        
        # --- Connections & Actions ---
        self.inquire_price_button.clicked.connect(self.ui_fetch_price)
        self.inquire_balance_button.clicked.connect(self.ui_fetch_balance)
        self.select_columns_button.clicked.connect(self.ui_open_column_selection)
        
        core_logic.authenticate()

    def add_tab(self, name):
        if name not in self.tabs:
            view = QTableView()
            self.tabs[name] = view
            self.tab_widget.addTab(view, name)
        return self.tabs[name]

    def ui_fetch_price(self):
        df = core_logic.get_price("005930")
        if df is not None:
            self.data_views["시세"]["data"] = df
            # Update all_cols with columns from the new dataframe
            self.data_views["시세"]["all_cols"] = [ALL_COLUMN_MAPPINGS.get(col, col) for col in df.columns]
            self.update_table_view("시세")
            self.tab_widget.setCurrentWidget(self.tabs["시세"])

    def ui_fetch_balance(self):
        df1, df2 = core_logic.get_balance()
        if df1 is not None and df2 is not None:
            self.data_views["보유 주식"]["data"] = df1
            self.data_views["보유 주식"]["all_cols"] = [ALL_COLUMN_MAPPINGS.get(col, col) for col in df1.columns]
            self.add_tab("보유 주식")
            self.update_table_view("보유 주식")
            
            self.data_views["계좌 평가"]["data"] = df2
            self.data_views["계좌 평가"]["all_cols"] = [ALL_COLUMN_MAPPINGS.get(col, col) for col in df2.columns]
            self.add_tab("계좌 평가")
            self.update_table_view("계좌 평가")
            
            self.tab_widget.setCurrentWidget(self.tabs["보유 주식"])

    def ui_open_column_selection(self):
        current_tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
        
        if current_tab_name not in self.data_views:
            logging.warning("No data view associated with this tab.")
            return

        view_state = self.data_views[current_tab_name]
        if view_state["data"] is None:
            logging.warning("Please fetch data for this tab first.")
            return
            
        dialog = ColumnSelectionDialog(view_state["all_cols"], view_state["selected_cols"], self)
        if dialog.exec():
            view_state["selected_cols"] = dialog.get_selected_columns()
            self.update_table_view(current_tab_name)

    def update_table_view(self, name):
        view_state = self.data_views.get(name)
        if view_state is None or view_state["data"] is None:
            return

        selected_cols_english = [REVERSE_COLUMN_MAPPING[k_name] for k_name in view_state["selected_cols"] if k_name in REVERSE_COLUMN_MAPPING]
        display_cols = [col for col in selected_cols_english if col in view_state["data"].columns]
        
        filtered_data = view_state["data"][display_cols]
        
        model = PandasModel(filtered_data)
        table_view = self.tabs[name]
        table_view.setModel(model)
        table_view.resizeColumnsToContents()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())