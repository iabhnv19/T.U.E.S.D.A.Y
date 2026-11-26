import math
import threading
from typing import Optional

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QRect
)
from PyQt5.QtGui import (
    QColor, QPainter, QBrush, QPen, QFont, QPainterPath, QLinearGradient, QRadialGradient
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
    start_signal = pyqtSignal(str, int, int, int)
    update_signal = pyqtSignal(str, int, int, int, float, float, float)
    stop_signal = pyqtSignal()


_active_scan_overlay: Optional["ScreenScanOverlay"] = None
_scan_depth_lock = threading.Lock()
_scan_depth = 0


def start_screen_scan(label: str = "Scanning screen...", accent_rgb: tuple = (59, 130, 246)):
    """Trigger the full-screen living content-reactive edge glow (thread-safe)."""
    global _scan_depth
    r, g, b = accent_rgb if accent_rgb and len(accent_rgb) == 3 else (59, 130, 246)
    with _scan_depth_lock:
        _scan_depth += 1
        if _active_scan_overlay is not None:
            try:
                _active_scan_overlay.signals.start_signal.emit(label, int(r), int(g), int(b))
            except Exception:
                pass


def update_screen_scan(
    label: str = "",
    accent_rgb: Optional[tuple] = None,
    intensity: float = 1.25,
    hotspot_x: float = 0.5,
    hotspot_y: float = 0.5,
):
    """Reactively steer the edge glow color, energy, and spatial hotspot to live screen content."""
    if _active_scan_overlay is not None:
        r, g, b = accent_rgb if accent_rgb and len(accent_rgb) == 3 else (-1, -1, -1)
        try:
            _active_scan_overlay.signals.update_signal.emit(
                label, int(r), int(g), int(b), float(intensity), float(hotspot_x), float(hotspot_y)
            )
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
    Renders a living, content-reactive 4-edge aura with smooth exponential grow/vanish,
    traveling organic wave blooms, and a sleek bottom status capsule.
    """

    def __init__(self):
        super().__init__()
        global _active_scan_overlay
        _active_scan_overlay = self

        self.signals = ScanSignals()
        self.signals.start_signal.connect(self._start_scan)
        self.signals.update_signal.connect(self._update_scan)
        self.signals.stop_signal.connect(self._stop_scan)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._on_hold_expired)
        self._min_hold_ms = 2200
        self._pending_stop = False
        self._time = 0.0
        self._opacity_factor = 0.0
        self._fading_out = False
        self._label = "T.U.E.S.D.A.Y Vision Scan"

        # Living color & spatial reactivity (smoothly lerped)
        self._curr_rgb = [59.0, 130.0, 246.0]
        self._target_rgb = [59.0, 130.0, 246.0]
        self._curr_intensity = 1.0
        self._target_intensity = 1.0
        self._curr_hotspot = [0.5, 0.5]
        self._target_hotspot = [0.5, 0.5]

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

    def _start_scan(self, label: str, r: int, g: int, b: int):
        self._label = label or "Scanning screen..."
        self._fading_out = False
        self._pending_stop = False
        self._opacity_factor = max(self._opacity_factor, 0.02)
        self._target_rgb = [float(r), float(g), float(b)]
        self._target_intensity = 1.0
        self._hold_timer.start(self._min_hold_ms)
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        self.show()
        if not self._anim_timer.isActive():
            self._anim_timer.start(16)  # ~60 FPS organic motion
        self.update()

    def _update_scan(self, label: str, r: int, g: int, b: int, intensity: float, hx: float, hy: float):
        if label:
            self._label = label
        if r >= 0 and g >= 0 and b >= 0:
            self._target_rgb = [float(r), float(g), float(b)]
        self._target_intensity = max(0.6, min(1.8, intensity))
        self._target_hotspot = [max(0.05, min(0.95, hx)), max(0.05, min(0.95, hy))]

    def _stop_scan(self):
        if self._hold_timer.isActive():
            self._pending_stop = True
        else:
            self._fading_out = True

    def _on_hold_expired(self):
        if self._pending_stop:
            self._pending_stop = False
            self._fading_out = True

    def _tick(self):
        self._time += 0.038

        # Smoothly lerp color, energy intensity, and content hotspot
        for i in range(3):
            self._curr_rgb[i] += (self._target_rgb[i] - self._curr_rgb[i]) * 0.08
        self._curr_intensity += (self._target_intensity - self._curr_intensity) * 0.08
        self._curr_hotspot[0] += (self._target_hotspot[0] - self._curr_hotspot[0]) * 0.07
        self._curr_hotspot[1] += (self._target_hotspot[1] - self._curr_hotspot[1]) * 0.07
        # Gently relax intensity back toward baseline 1.05
        self._target_intensity += (1.05 - self._target_intensity) * 0.02

        if self._fading_out:
            # Silky ~0.9s dissolve out
            self._opacity_factor *= 0.92
            if self._opacity_factor <= 0.01:
                self._opacity_factor = 0.0
                self._anim_timer.stop()
                self.hide()
                return
        else:
            # Silky ~0.7s bloom in
            self._opacity_factor += (1.0 - self._opacity_factor) * 0.055
            if self._opacity_factor > 0.995:
                self._opacity_factor = 1.0

        self.update()

    def paintEvent(self, event):
        if self._opacity_factor <= 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()

        r, g, b = int(self._curr_rgb[0]), int(self._curr_rgb[1]), int(self._curr_rgb[2])
        # Secondary harmonic color (shifted toward cyan/indigo)
        r2 = max(0, min(255, int(r * 0.6 + 40)))
        g2 = max(0, min(255, int(g * 0.8 + 45)))
        b2 = max(0, min(255, int(b * 0.7 + 75)))

        # Multi-wave organic breathing
        wave = 0.78 + 0.14 * math.sin(self._time * 2.1) + 0.08 * math.cos(self._time * 3.7)
        alpha_scale = min(1.35, self._opacity_factor * wave * self._curr_intensity)

        # ── 1. Living 4-Edge Content-Reactive Vignette ──────────────────────
        edge_depth = max(28, int((130 * self._opacity_factor * self._curr_intensity) + 16 * math.sin(self._time * 1.9)))
        c_outer = QColor(r, g, b, min(210, int(120 * alpha_scale)))
        c_mid = QColor(r2, g2, b2, min(140, int(48 * alpha_scale)))
        c_clear = QColor(r, g, b, 0)

        for grad, rect in (
            (QLinearGradient(0, 0, 0, edge_depth), (0, 0, w, edge_depth)),
            (QLinearGradient(0, h, 0, h - edge_depth), (0, h - edge_depth, w, edge_depth)),
            (QLinearGradient(0, 0, edge_depth, 0), (0, 0, edge_depth, h)),
            (QLinearGradient(w, 0, w - edge_depth, 0), (w - edge_depth, 0, edge_depth, h)),
        ):
            grad.setColorAt(0.0, c_outer)
            grad.setColorAt(0.45, c_mid)
            grad.setColorAt(1.0, c_clear)
            painter.fillRect(*rect, grad)

        # ── 2. Orbiting & Content-Attracted Radial Energy Blooms ────────────
        hx = self._curr_hotspot[0] * w
        hy = self._curr_hotspot[1] * h
        # Project hotspot onto nearest perimeter + add organic drift
        bloom_centers = [
            (hx + 70 * math.sin(self._time * 1.4), 12 if hy < h * 0.5 else h - 12, 340),
            (12 if hx < w * 0.5 else w - 12, hy + 70 * math.cos(self._time * 1.6), 300),
            (w * (0.5 + 0.35 * math.sin(self._time * 0.9)), h - 10, 280),
        ]
        for bx, by, radius in bloom_centers:
            rad = int(radius * (0.5 + 0.5 * self._opacity_factor))
            rg = QRadialGradient(bx, by, max(40, rad))
            rg.setColorAt(0.0, QColor(min(255, r + 45), min(255, g + 45), min(255, b + 45), min(190, int(110 * alpha_scale))))
            rg.setColorAt(0.5, QColor(r2, g2, b2, min(110, int(40 * alpha_scale))))
            rg.setColorAt(1.0, QColor(r, g, b, 0))
            painter.fillRect(int(bx - rad), int(by - rad), rad * 2, rad * 2, rg)

        # Crisp neon perimeter border
        border_pen = QPen(QColor(min(255, r + 40), min(255, g + 40), min(255, b + 40), min(220, int(180 * alpha_scale))), 2)
        painter.setPen(border_pen)
        painter.drawRect(1, 1, w - 2, h - 2)

        # ── 3. Reactive Perimeter Dot-Matrix ────────────────────────────────
        painter.setPen(Qt.NoPen)
        step = 28
        margin = max(24, int(edge_depth * 0.75))
        base_dot_alpha = int(48 * alpha_scale)
        dot_color = QColor(min(255, r + 80), min(255, g + 80), min(255, b + 80), min(150, base_dot_alpha))
        painter.setBrush(QBrush(dot_color))
        for x in range(14, w, step):
            for y in range(14, h, step):
                if x < margin or x > w - margin or y < margin or y > h - margin:
                    painter.drawEllipse(x, y, 2, 2)

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
