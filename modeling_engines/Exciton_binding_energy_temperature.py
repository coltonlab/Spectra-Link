import sys
import csv
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QCheckBox, QFormLayout, QFrame, QTableWidget, 
                             QTableWidgetItem, QFileDialog, QMessageBox, QHeaderView)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class ScientificPlotter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exciton & Band Gap Plotter")
        self.resize(1100, 750)

        # Data storage
        self.temperatures = []
        self.e_gap = []
        self.e_gap_err = []
        self.e_ex = []
        self.e_ex_err = []

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- LEFT PANEL (Plot & Toolbar) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        main_layout.addWidget(left_panel, stretch=3)

        self.figure = Figure(figsize=(7, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        # Add Matplotlib Navigation Toolbar (Save, Zoom, Pan)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        left_layout.addWidget(self.toolbar)
        left_layout.addWidget(self.canvas)

        # --- RIGHT PANEL (Controls) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        main_layout.addWidget(right_panel, stretch=1)

        # 1. Data Entry Form
        form_layout = QFormLayout()
        
        self.input_t = QLineEdit()
        self.input_eg = QLineEdit()
        self.input_eg_err = QLineEdit()
        self.input_ex = QLineEdit()
        self.input_ex_err = QLineEdit()
        
        self.input_t.setPlaceholderText("e.g., 10")
        self.input_eg.setPlaceholderText("e.g., 1.52")
        self.input_eg_err.setPlaceholderText("e.g., 0.01")
        self.input_ex.setPlaceholderText("e.g., 1.48")
        self.input_ex_err.setPlaceholderText("e.g., 0.01")

        form_layout.addRow("Temperature (K):", self.input_t)
        form_layout.addRow("Band Gap (eV):", self.input_eg)
        form_layout.addRow("Band Gap Unc.:", self.input_eg_err)
        form_layout.addRow("Exciton Peak (eV):", self.input_ex)
        form_layout.addRow("Exciton Unc.:", self.input_ex_err)
        
        right_layout.addLayout(form_layout)

        # Add Data Button
        self.btn_add_data = QPushButton("Add Data Point")
        self.btn_add_data.clicked.connect(self.add_manual_data_point)
        right_layout.addWidget(self.btn_add_data)

        # Data Preview Table
        self.data_table = QTableWidget(0, 5)
        self.data_table.setHorizontalHeaderLabels(["T", "Eg", "dEg", "Eex", "dEex"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.data_table)

        # Delete Row Button
        self.btn_delete_row = QPushButton("Delete Selected Row")
        self.btn_delete_row.clicked.connect(self.delete_row)
        right_layout.addWidget(self.btn_delete_row)

        self.add_separator(right_layout)

        # CSV File Operations
        csv_layout = QHBoxLayout()
        self.btn_load_csv = QPushButton("Load CSV")
        self.btn_export_csv = QPushButton("Export CSV")
        
        self.btn_load_csv.clicked.connect(self.load_csv)
        self.btn_export_csv.clicked.connect(self.export_csv)
        
        csv_layout.addWidget(self.btn_load_csv)
        csv_layout.addWidget(self.btn_export_csv)
        right_layout.addLayout(csv_layout)

        self.add_separator(right_layout)

        # 2. Plot Controls
        self.cb_binding_energy = QCheckBox("Plot Exciton Binding Energy (Subplot)")
        self.cb_binding_energy.stateChanged.connect(self.update_plot)
        right_layout.addWidget(self.cb_binding_energy)
        
        self.cb_grid = QCheckBox("Show Grid")
        self.cb_grid.setChecked(True) # Default to having the grid on
        self.cb_grid.stateChanged.connect(self.update_plot)
        right_layout.addWidget(self.cb_grid)
        
        right_layout.addStretch()
        
        # Initial Plot update
        self.update_plot()

    def add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

    def append_data(self, t, eg, eg_err, ex, ex_err):
        self.temperatures.append(t)
        self.e_gap.append(eg)
        self.e_gap_err.append(eg_err)
        self.e_ex.append(ex)
        self.e_ex_err.append(ex_err)

        row = self.data_table.rowCount()
        self.data_table.insertRow(row)
        self.data_table.setItem(row, 0, QTableWidgetItem(f"{t:.2f}"))
        self.data_table.setItem(row, 1, QTableWidgetItem(f"{eg:.4f}"))
        self.data_table.setItem(row, 2, QTableWidgetItem(f"{eg_err:.4f}"))
        self.data_table.setItem(row, 3, QTableWidgetItem(f"{ex:.4f}"))
        self.data_table.setItem(row, 4, QTableWidgetItem(f"{ex_err:.4f}"))

    def add_manual_data_point(self):
        try:
            t = float(self.input_t.text())
            eg = float(self.input_eg.text())
            eg_err = float(self.input_eg_err.text())
            ex = float(self.input_ex.text())
            ex_err = float(self.input_ex_err.text())

            self.append_data(t, eg, eg_err, ex, ex_err)

            for widget in [self.input_t, self.input_eg, self.input_eg_err, self.input_ex, self.input_ex_err]:
                widget.clear()

            self.update_plot()
            
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric values for all fields.")

    def delete_row(self):
        current_row = self.data_table.currentRow()
        if current_row >= 0:
            self.data_table.removeRow(current_row)
            
            self.temperatures.pop(current_row)
            self.e_gap.pop(current_row)
            self.e_gap_err.pop(current_row)
            self.e_ex.pop(current_row)
            self.e_ex_err.pop(current_row)
            
            self.update_plot()
        else:
            QMessageBox.information(self, "Selection Error", "Please select a row in the table to delete.")

    def load_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open CSV Data", "", "CSV Files (*.csv);;All Files (*)")
        if not file_name:
            return

        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                success_count = 0
                for row in reader:
                    if len(row) < 5:
                        continue
                    try:
                        t, eg, deg, ex, dex = map(float, row[:5])
                        self.append_data(t, eg, deg, ex, dex)
                        success_count += 1
                    except ValueError:
                        continue 
                
                if success_count > 0:
                    self.update_plot()
                    QMessageBox.information(self, "Success", f"Successfully loaded {success_count} data points.")
                else:
                    QMessageBox.warning(self, "Format Error", "No valid data found. Ensure your CSV has 5 columns of numbers (T, Eg, dEg, Eex, dEex).")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error Loading File", f"An error occurred: {str(e)}")

    def export_csv(self):
        if not self.temperatures:
            QMessageBox.warning(self, "Export Error", "No data to export.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save CSV Data", "bandgap_data.csv", "CSV Files (*.csv)")
        if not file_name:
            return

        try:
            with open(file_name, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Temperature(K)", "Eg(eV)", "Eg_err", "Eex(eV)", "Eex_err"])
                for i in range(len(self.temperatures)):
                    writer.writerow([
                        self.temperatures[i], 
                        self.e_gap[i], self.e_gap_err[i], 
                        self.e_ex[i], self.e_ex_err[i]
                    ])
            QMessageBox.information(self, "Success", "Data exported successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", f"An error occurred: {str(e)}")

    def update_plot(self):
        self.figure.clear()
        
        show_subplot = self.cb_binding_energy.isChecked()
        show_grid = self.cb_grid.isChecked()
        
        if show_subplot:
            ax_main = self.figure.add_axes([0.15, 0.4, 0.8, 0.55])
            ax_sub = self.figure.add_axes([0.15, 0.15, 0.8, 0.25], sharex=ax_main)
            ax_main.tick_params(labelbottom=False)
        else:
            ax_main = self.figure.add_subplot(111)
            ax_sub = None

        if self.temperatures:
            sort_idx = np.argsort(self.temperatures)
            t = np.array(self.temperatures)[sort_idx]
            eg = np.array(self.e_gap)[sort_idx]
            deg = np.array(self.e_gap_err)[sort_idx]/1000
            ex = np.array(self.e_ex)[sort_idx]
            dex = np.array(self.e_ex_err)[sort_idx]/1000

            marker_style = dict(fmt='o', capsize=3, elinewidth=1.5, markersize=6)

            ax_main.errorbar(t, eg, yerr=deg, label='Band Gap', color='navy', **marker_style)
            ax_main.errorbar(t, ex, yerr=dex, label='Exciton Peak', color='crimson', marker='s', 
                             capsize=3, elinewidth=1.5, markersize=6, linestyle='')
            
            if show_subplot:
                eb = eg - ex
                deb = np.sqrt(deg**2 + dex**2)
                
                ax_sub.errorbar(t, eb * 1000, yerr=deb * 1000, color='forestgreen', 
                                fmt='^', capsize=3, elinewidth=1.5, markersize=6, label='Binding Energy')
                ax_sub.set_ylabel("Binding Energy (meV)", fontsize=12)
                
                if show_grid:
                    ax_sub.grid(True, linestyle='--', alpha=0.6)
                else:
                    ax_sub.grid(False)

        ax_main.set_ylabel("Energy (eV)", fontsize=12)
        
        if show_grid:
            ax_main.grid(True, linestyle='--', alpha=0.6)
        else:
            ax_main.grid(False)

        if self.temperatures:
            ax_main.legend(loc='best', frameon=True, edgecolor='black')
        
        if show_subplot:
            ax_sub.set_xlabel("Temperature (K)", fontsize=12)
        else:
            ax_main.set_xlabel("Temperature (K)", fontsize=12)
            
        ax_main.tick_params(direction='in', right=True, top=True)
        if show_subplot:
            ax_sub.tick_params(direction='in', right=True, top=True)

        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScientificPlotter()
    window.show()
    sys.exit(app.exec())