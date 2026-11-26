import math
import threading
from typing import Optional

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QRect
)
from PyQt5.QtGui import (
    QColor, QPainter, QBrush, QPen, QFont, QPainterPath, QLinearGradient
)

from core.config import Config


class OverlaySignals(QObject):
    """Signals for thread-safe UI updates."""
    show_signal = pyqtSignal(str, str, int)
    hide_signal = pyqtSignal()
    update_signal = pyqtSignal(str, str)


class DynamicIsland(QWidget):
    """Floating capsule overlay with smooth interpolation and soundwave animation."""

    def __init__(self):
        super().__init__()
        self.signals = OverlaySignals()
        self.signals.show_signal.connect(self._show_island)
        self.signals.hide_signal.connect(self._hide_island)
        self.signals.update_signal.connect(self._update_island)

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self._hide_island)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._time = 0.0

        # Target and current dimensions for lerp animation
        self._curr_w = 280.0
        self._curr_h = 48.0
        self._target_w = 280.0
        self._target_h = 48.0

        self._wave_amp = 0.65
        self._target_wave_amp = 0.65

        self._status = "listening"
        self._display_text = "Listening..."

        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.resize(int(self._curr_w), int(self._curr_h))
        self._position_island()
        self.hide()

    def _position_island(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + 18
            self.move(int(x), int(y))

    def _anim_tick(self):
        """Asymptotic ease-out animation tick."""
        self._time += 0.08

        # Exponential lerp factor: smooth deceleration without overshoot
        lerp_factor = 0.16
        diff_w = self._target_w - self._curr_w
        diff_h = self._target_h - self._curr_h

        if abs(diff_w) > 0.3:
            self._curr_w += diff_w * lerp_factor
        else:
            self._curr_w = self._target_w

        if abs(diff_h) > 0.3:
            self._curr_h += diff_h * lerp_factor
        else:
            self._curr_h = self._target_h

        # Wave amplitude based on state
        if self._status == "speaking":
            self._target_wave_amp = 1.2
        elif self._status == "listening":
            self._target_wave_amp = 0.65
        elif self._status == "thinking":
            self._target_wave_amp = 0.85
        else:
            self._target_wave_amp = 0.25

        self._wave_amp += (self._target_wave_amp - self._wave_amp) * 0.15

        new_w = max(260, int(round(self._curr_w)))
        new_h = max(46, int(round(self._curr_h)))

        if self.width() != new_w or self.height() != new_h:
            self.resize(new_w, new_h)
            self._position_island()

        self.update()

    def _draw_siri_ribbon(self, painter: QPainter, cx: float, cy: float, width: float, height: float):
        """Render multi-layered organic sine wave ribbon."""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        layers = [
            (QColor(0, 230, 255, 190), 1.25, 0.08, 0.0, 9.0 * self._wave_amp),
            (QColor(140, 90, 255, 175), 0.95, 0.07, 2.1, 12.0 * self._wave_amp),
            (QColor(240, 60, 200, 150), 1.35, 0.09, 4.2, 10.0 * self._wave_amp),
        ]

        left_x = cx - width / 2
        right_x = cx + width / 2
        step = 2.0

        for col, speed, freq, phase, amp in layers:
            top_path = QPainterPath()
            bot_path = QPainterPath()

            top_path.moveTo(left_x, cy)
            bot_path.moveTo(left_x, cy)

            x = left_x
            while x <= right_x:
                rel_x = (x - left_x) / width
                envelope = math.sin(rel_x * math.pi)

                t = self._time * speed + phase
                displacement = math.sin(x * freq + t) * math.cos(x * 0.04 - t * 0.4) * amp * envelope

                top_path.lineTo(x, cy - displacement)
                bot_path.lineTo(x, cy + displacement)
                x += step

            top_path.lineTo(right_x, cy)
            bot_path.lineTo(right_x, cy)

            ribbon = QPainterPath(top_path)
            ribbon.connectPath(bot_path.toReversed())

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(col))
            painter.drawPath(ribbon)

        # Subtle center spine
        painter.setPen(QPen(QColor(255, 255, 255, 230), 1.3))
        painter.drawLine(int(left_x + 8), int(cy), int(right_x - 8), int(cy))

        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, radius, radius)

        # Dark capsule fill
        painter.fillPath(path, QBrush(QColor(8, 9, 14, 250)))

        # 1px subtle top highlight
        rim_grad = QLinearGradient(0, 0, 0, h)
        rim_grad.setColorAt(0.0, QColor(255, 255, 255, 55))
        rim_grad.setColorAt(0.4, QColor(90, 110, 150, 25))
        rim_grad.setColorAt(1.0, QColor(255, 255, 255, 12))
        painter.setPen(QPen(QBrush(rim_grad), 1.0))
        painter.drawPath(path)

        # Mask text strictly inside capsule boundary
        painter.setClipPath(path)

        # Waveform visualizer
        ribbon_w = 76.0
        ribbon_h = 24.0
        ribbon_cx = 50.0
        ribbon_cy = h / 2.0
        self._draw_siri_ribbon(painter, ribbon_cx, ribbon_cy, ribbon_w, ribbon_h)

        # Label typography
        painter.setPen(QPen(QColor(245, 246, 250), 1))
        font = QFont("Segoe UI", 10, QFont.DemiBold)
        painter.setFont(font)

        text_x = 94
        text_w = w - text_x - 18
        text_rect = QRect(text_x, 0, text_w, h)

        painter.drawText(
            text_rect,
            Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap,
            self._display_text
        )

    def show_status(self, status: str, text: str = "", auto_hide_ms: int = 0):
        self.signals.show_signal.emit(status, text, auto_hide_ms)

    def update_status(self, status: str, text: str = ""):
        self.signals.update_signal.emit(status, text)

    def hide_bar(self):
        self.signals.hide_signal.emit()

    def _recalculate_target_geometry(self):
        """Adjust capsule size based on text length."""
        length = len(self._display_text)
        if length <= 20:
            self._target_w = 280
            self._target_h = 48
        elif length <= 50:
            self._target_w = 400
            self._target_h = 52
        else:
            self._target_w = 520
            self._target_h = 60

    def _show_island(self, status: str, text: str, auto_hide_ms: int):
        self._status = status
        clean = " ".join((text or status.capitalize()).split())
        if len(clean) > 80:
            clean = clean[:77] + "..."
        self._display_text = clean

        self._recalculate_target_geometry()
        self._curr_w = self._target_w * 0.94
        self._curr_h = self._target_h
        self._position_island()
        self.show()

        if not self._anim_timer.isActive():
            self._anim_timer.start(20)

        if auto_hide_ms > 0:
            self._auto_hide_timer.start(auto_hide_ms)
        else:
            self._auto_hide_timer.stop()
        self.update()

    def _hide_island(self):
        self._anim_timer.stop()
        self.hide()

    def _update_island(self, status: str, text: str):
        self._status = status
        if text:
            clean = " ".join(text.split())
            if len(clean) > 80:
                clean = clean[:77] + "..."
            if clean != self._display_text:
                self._display_text = clean
                self._recalculate_target_geometry()
        self.update()


class ScanSignals(QObject):
    """Thread-safe signals for the full-screen cyber OCR scan overlay."""
    start_signal = pyqtSignal(str)
    stop_signal = pyqtSignal()


_active_scan_overlay: Optional["ScreenScanOverlay"] = None
_scan_depth_lock = threading.Lock()
_scan_depth = 0


def start_screen_scan(label: str = "Scanning screen..."):
    """Trigger the full-screen glowing cyber border & laser scanline (thread-safe)."""
    global _scan_depth
    with _scan_depth_lock:
        _scan_depth += 1
        if _active_scan_overlay is not None:
            try:
                _active_scan_overlay.signals.start_signal.emit(label)
            except Exception:
                pass


def stop_screen_scan():
    """Stop the full-screen cyber scan animation when all nested scans finish."""
    global _scan_depth
    with _scan_depth_lock:
        _scan_depth = max(0, _scan_depth - 1)
        if _scan_depth == 0 and _active_scan_overlay is not None:
            try:
                _active_scan_overlay.signals.stop_signal.emit()
            except Exception:
                pass


class ScreenScanOverlay(QWidget):
    """
    Full-screen transparent click-through overlay shown during OCR & screen analysis.
    Renders a glowing blue/indigo 4-edge vignette, subtle cyber dot-matrix,
    a sweeping horizontal laser scanline, and a sleek bottom status capsule.
    """

    def __init__(self):
        super().__init__()
        global _active_scan_overlay
        _active_scan_overlay = self

        self.signals = ScanSignals()
        self.signals.start_signal.connect(self._start_scan)
        self.signals.stop_signal.connect(self._stop_scan)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._time = 0.0
        self._scan_y_ratio = 0.0
        self._opacity_factor = 0.0
        self._fading_out = False
        self._label = "T.U.E.S.D.A.Y Vision Scan"

        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        self.hide()

    def _start_scan(self, label: str):
        self._label = label or "Scanning screen..."
        self._fading_out = False
        self._opacity_factor = max(self._opacity_factor, 0.2)
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        self.show()
        if not self._anim_timer.isActive():
            self._anim_timer.start(16)  # ~60 FPS smooth sweep
        self.update()

    def _stop_scan(self):
        self._fading_out = True

    def _tick(self):
        self._time += 0.07
        self._scan_y_ratio = (self._scan_y_ratio + 0.018) % 1.0

        if self._fading_out:
            self._opacity_factor = max(0.0, self._opacity_factor - 0.12)
            if self._opacity_factor <= 0.01:
                self._anim_timer.stop()
                self.hide()
                return
        else:
            self._opacity_factor = min(1.0, self._opacity_factor + 0.15)

        self.update()

    def paintEvent(self, event):
        if self._opacity_factor <= 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        pulse = 0.78 + 0.22 * math.sin(self._time * 2.2)
        alpha_scale = self._opacity_factor * pulse

        # ── 1. 4-Edge Glowing Cyber Vignette ────────────────────────────────
        edge_depth = 120
        c_outer = QColor(59, 130, 246, int(115 * alpha_scale))   # Electric Blue
        c_mid = QColor(99, 102, 241, int(45 * alpha_scale))      # Indigo glow
        c_clear = QColor(59, 130, 246, 0)

        # Top edge
        g_top = QLinearGradient(0, 0, 0, edge_depth)
        g_top.setColorAt(0.0, c_outer)
        g_top.setColorAt(0.45, c_mid)
        g_top.setColorAt(1.0, c_clear)
        painter.fillRect(0, 0, w, edge_depth, g_top)

        # Bottom edge
        g_bot = QLinearGradient(0, h, 0, h - edge_depth)
        g_bot.setColorAt(0.0, c_outer)
        g_bot.setColorAt(0.45, c_mid)
        g_bot.setColorAt(1.0, c_clear)
        painter.fillRect(0, h - edge_depth, w, edge_depth, g_bot)

        # Left edge
        g_left = QLinearGradient(0, 0, edge_depth, 0)
        g_left.setColorAt(0.0, c_outer)
        g_left.setColorAt(0.45, c_mid)
        g_left.setColorAt(1.0, c_clear)
        painter.fillRect(0, 0, edge_depth, h, g_left)

        # Right edge
        g_right = QLinearGradient(w, 0, w - edge_depth, 0)
        g_right.setColorAt(0.0, c_outer)
        g_right.setColorAt(0.45, c_mid)
        g_right.setColorAt(1.0, c_clear)
        painter.fillRect(w - edge_depth, 0, edge_depth, h, g_right)

        # Crisp neon perimeter border
        border_pen = QPen(QColor(96, 165, 250, int(180 * alpha_scale)), 2)
        painter.setPen(border_pen)
        painter.drawRect(1, 1, w - 2, h - 2)

        # ── 2. Subtle Cyber Dot-Matrix Texture Near Perimeter ───────────────
        dot_color = QColor(147, 197, 253, int(55 * alpha_scale))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(dot_color))
        step = 28
        margin = 96
        for x in range(14, w, step):
            for y in range(14, h, step):
                if x < margin or x > w - margin or y < margin or y > h - margin:
                    painter.drawEllipse(x, y, 2, 2)

        # ── 3. Sweeping Horizontal Laser Scanline ───────────────────────────
        scan_y = int(self._scan_y_ratio * h)
        trail_h = 44
        g_laser = QLinearGradient(0, scan_y - trail_h, 0, scan_y)
        g_laser.setColorAt(0.0, QColor(56, 189, 248, 0))
        g_laser.setColorAt(1.0, QColor(56, 189, 248, int(65 * alpha_scale)))
        painter.fillRect(0, scan_y - trail_h, w, trail_h, g_laser)

        laser_pen = QPen(QColor(56, 189, 248, int(190 * alpha_scale)), 2)
        painter.setPen(laser_pen)
        painter.drawLine(0, scan_y, w, scan_y)

        # ── 4. Bottom Floating Status Capsule ───────────────────────────────
        pill_w, pill_h = 310, 44
        pill_x = (w - pill_w) // 2
        pill_y = h - 78
        path = QPainterPath()
        path.addRoundedRect(pill_x, pill_y, pill_w, pill_h, 22, 22)
        painter.fillPath(path, QColor(12, 14, 22, int(220 * self._opacity_factor)))
        painter.setPen(QPen(QColor(96, 165, 250, int(160 * alpha_scale)), 1.5))
        painter.drawPath(path)

        # Spinning cyan arc loader inside pill
        arc_rect = QRect(pill_x + 14, pill_y + 12, 20, 20)
        painter.setPen(QPen(QColor(56, 189, 248, int(240 * self._opacity_factor)), 2.5))
        start_angle = int((self._time * 240) % 360) * 16
        painter.drawArc(arc_rect, start_angle, 220 * 16)

        # Status text
        painter.setPen(QColor(235, 245, 255, int(245 * self._opacity_factor)))
        painter.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        text_rect = QRect(pill_x + 44, pill_y, pill_w - 56, pill_h)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._label)


class TrayIcon:
    """System tray icon and menu."""

    def __init__(self, on_quit=None, on_toggle=None):
        self.on_quit = on_quit
        self.on_toggle = on_toggle
        self._icon = None
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([8, 8, 56, 56], fill=(15, 15, 20, 255), outline=(0, 230, 255, 255), width=3)
            draw.text((24, 18), "T", fill=(0, 230, 255, 255))

            menu = pystray.Menu(
                pystray.MenuItem(f"{Config.NAME} — AI Assistant", lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Toggle Active Mode", lambda icon, item: self.on_toggle() if self.on_toggle else None),
                pystray.MenuItem("Quit", lambda icon, item: self._quit(icon)),
            )

            self._icon = pystray.Icon(Config.NAME, img, Config.NAME, menu)
            self._icon.run()
        except ImportError:
            pass

    def _quit(self, icon):
        icon.stop()
        if self.on_quit:
            self.on_quit()

    def stop(self):
        if self._icon:
            self._icon.stop()
