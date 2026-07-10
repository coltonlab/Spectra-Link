from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor


class KAnalysisInteractionController:
    """Handles region selection, hover feedback, and plot interaction state."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def connect_plot_mouse_events(self, connect: bool) -> None:
        plot = self.dashboard.plot
        scene = plot.scene()
        if connect:
            try:
                scene.sigMouseClicked.disconnect(self.dashboard._handle_plot_click)
            except TypeError:
                pass
            try:
                scene.sigMouseMoved.disconnect(self.dashboard._handle_plot_mouse_move)
            except TypeError:
                pass
            scene.sigMouseClicked.connect(self.dashboard._handle_plot_click)
            scene.sigMouseMoved.connect(self.dashboard._handle_plot_mouse_move)
        else:
            try:
                scene.sigMouseClicked.disconnect(self.dashboard._handle_plot_click)
            except TypeError:
                pass
            try:
                scene.sigMouseMoved.disconnect(self.dashboard._handle_plot_mouse_move)
            except TypeError:
                pass

    def set_region_pen(self, region, pen) -> None:
        if hasattr(region, "lines"):
            for line in region.lines:
                line.setPen(pen)

    def set_region_style(self, region, color, *, line_width=4, brush_alpha=25, hover_alpha=30) -> None:
        brush_color = QColor(color)
        brush_color.setAlpha(brush_alpha)
        region.setBrush(pg.mkBrush(brush_color))

        hover_color = QColor(color)
        hover_color.setAlpha(hover_alpha)
        region.setHoverBrush(pg.mkBrush(hover_color))

        self.set_region_pen(region, pg.mkPen(color, width=line_width))

    def handle_plot_click(self, event) -> None:
        dashboard = self.dashboard
        if not dashboard._selection_mode_active or event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.scenePos()
        x_coord = dashboard.plot.plotItem.vb.mapSceneToView(pos).x()

        if dashboard._first_click_x is None:
            dashboard._first_click_x = x_coord
            dashboard.results_log.setText("Click again to define the width of your peak range.")

            if dashboard.x_data is not None and len(dashboard.x_data) > 1:
                x_range = dashboard.x_data.max() - dashboard.x_data.min()
                default_width = x_range * 0.05
            else:
                default_width = 0.1

            dashboard._temp_region = pg.LinearRegionItem(
                values=(x_coord - default_width / 2, x_coord + default_width / 2),
                movable=False,
            )
            dashboard._temp_region.setZValue(100)
            self.set_region_style(
                dashboard._temp_region,
                QColor(255, 255, 0, 255),
                line_width=1,
                brush_alpha=25,
                hover_alpha=40,
            )
            dashboard.plot.addItem(dashboard._temp_region)
        else:
            center_x = dashboard._first_click_x
            width = abs(x_coord - center_x) * 2

            min_allowed_width = (
                (dashboard.x_data.max() - dashboard.x_data.min()) * 0.005
                if dashboard.x_data is not None and len(dashboard.x_data) > 1
                else 0.01
            )
            if width < min_allowed_width:
                width = min_allowed_width
            x_start, x_end = center_x - width / 2, center_x + width / 2

            if dashboard._temp_region:
                dashboard.plot.removeItem(dashboard._temp_region)
                dashboard._temp_region = None

            self.create_and_add_region(x_start, x_end)
            self.cancel_selection_mode()

    def handle_plot_mouse_move(self, pos) -> None:
        dashboard = self.dashboard
        if dashboard._selection_mode_active and dashboard._first_click_x is not None and dashboard._temp_region:
            view_pos = dashboard.plot.plotItem.vb.mapSceneToView(pos)
            if view_pos is None:
                return

            current_x = view_pos.x()
            center_x = dashboard._first_click_x

            min_allowed_width = (
                (dashboard.x_data.max() - dashboard.x_data.min()) * 0.005
                if dashboard.x_data is not None and len(dashboard.x_data) > 1
                else 0.01
            )

            width = abs(current_x - center_x) * 2
            if width < min_allowed_width:
                width = min_allowed_width

            dashboard._temp_region.setRegion((center_x - width / 2, center_x + width / 2))

    def finalize_temp_region(self) -> None:
        dashboard = self.dashboard
        if dashboard._temp_region and dashboard._selection_mode_active and dashboard._first_click_x is not None:
            x_start, x_end = dashboard._temp_region.getRegion()
            dashboard.plot.removeItem(dashboard._temp_region)
            dashboard._temp_region = None
            self.create_and_add_region(x_start, x_end)
            self.cancel_selection_mode()

    def create_and_add_region(self, x_start, x_end) -> None:
        dashboard = self.dashboard
        new_region = pg.LinearRegionItem(values=(x_start, x_end))
        new_region.setZValue(10)

        color_idx = len(dashboard.regions) % 10
        region_color = pg.intColor(color_idx, 10)
        self.set_region_style(new_region, region_color, line_width=4, brush_alpha=25, hover_alpha=30)

        dashboard.plot.addItem(new_region)
        dashboard.regions.append(new_region)

        new_region.sigRegionChangeFinished.connect(dashboard.perform_k_analysis)
        new_region.sigRegionChanged.connect(self.update_region_label)

    def cancel_selection_mode(self) -> None:
        dashboard = self.dashboard
        dashboard._selection_mode_active = False
        dashboard._first_click_x = None
        if dashboard._temp_region:
            dashboard.plot.removeItem(dashboard._temp_region)
            dashboard._temp_region = None
        dashboard.results_log.clear()
        self.set_ui_selection_mode(False)
        self.connect_plot_mouse_events(False)

    def set_ui_selection_mode(self, active: bool) -> None:
        dashboard = self.dashboard
        dashboard.btn_add_range.setEnabled(not active)
        dashboard.btn_remove_range.setEnabled(not active and bool(dashboard.regions))
        dashboard.btn_toggle_view.setEnabled(not active)
        dashboard.range_list_widget.setEnabled(not active)
        dashboard.chk_show_fits.setEnabled(not active)
        if active:
            dashboard.plot.setCursor(Qt.CursorShape.CrossCursor)
        else:
            dashboard.plot.unsetCursor()

    def update_region_label(self, region_item) -> None:
        dashboard = self.dashboard
        try:
            idx = dashboard.regions.index(region_item)
            min_x, max_x = region_item.getRegion()
            item = dashboard.range_list_widget.item(idx)
            if item:
                QTimer.singleShot(0, lambda: item.setText(f"Range {idx + 1}: {min_x:.2f} - {max_x:.2f} eV"))
        except ValueError:
            pass

    def on_range_selected_from_list(self, row) -> None:
        dashboard = self.dashboard
        for i, region in enumerate(dashboard.regions):
            if i == row:
                region.setZValue(11)
                self.set_region_pen(region, pg.mkPen("y", width=5))
            else:
                region.setZValue(10)
                color_idx = i % 10
                region_color = pg.intColor(color_idx, 10)
                self.set_region_pen(region, pg.mkPen(region_color, width=4))
        dashboard.btn_remove_range.setEnabled(row >= 0)
