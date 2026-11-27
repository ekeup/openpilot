"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import fcntl
import socket
import struct
import time

import pyray as rl

from openpilot.selfdrive.ui.mici.onroad import SIDE_PANEL_WIDTH
from openpilot.selfdrive.ui.mici.onroad.hud_renderer import HudRenderer, COLORS
from openpilot.selfdrive.ui.sunnypilot.mici.onroad.speed_strip import SPEED_FONT_SIZE, SPEED_MARGIN_BOTTOM, SPEED_USABLE_WIDTH
from openpilot.selfdrive.ui.sunnypilot.onroad.blind_spot_indicators import BlindSpotIndicators
from openpilot.system.ui.lib.text_measure import measure_text_cached

# Erik's request (Nov 27, 2026): current-speed readout, number only (no unit
# label), at the bottom of the 60px side panel strip right of the camera
# view — see speed_strip.py for the geometry shared with the confidence
# ball. The strip is outside the content rect this renderer is clipped to,
# so _draw_current_speed drops the caller's scissor mode to draw there and
# restores it before returning. The font auto-fits: full size for 1-2
# digits, shrunk only when a 3-digit speed would overflow the strip.

# Erik's request (Nov 27, 2026): the device's current Wi-Fi IP address as
# small plain text in the top right corner, so he can read it off the
# screen instead of digging through settings whenever Sunny needs it to
# SSH in. The address changes with every network, so it is re-read every
# few seconds (never cached from boot) and the text disappears entirely
# when there is no Wi-Fi address, rather than showing a stale one. It is
# right-aligned to the content rect, just left of the side panel strip:
# the strip's top is where the confidence ball sits at high confidence,
# and the ball is drawn after the HUD, so text there would be painted
# over exactly while driving.
IP_FONT_SIZE = 14
IP_MARGIN_RIGHT = 12  # clear of the fake rounded border's corner arc (drawn over the HUD)
IP_MARGIN_TOP = 6
IP_REFRESH_S = 5.0
WIFI_INTERFACE = b"wlan0"
SIOCGIFADDR = 0x8915


def _get_wifi_ip() -> str:
  """Current IPv4 address of the Wi-Fi interface, or "" if it has none."""
  try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
      packed = fcntl.ioctl(sock.fileno(), SIOCGIFADDR, struct.pack("256s", WIFI_INTERFACE))
    return socket.inet_ntoa(packed[20:24])
  except Exception:
    return ""


class HudRendererSP(HudRenderer):
  def __init__(self):
    super().__init__()
    self.blind_spot_indicators = BlindSpotIndicators()
    self._wifi_ip: str = ""
    self._wifi_ip_checked_at: float = 0.0

  def _update_state(self) -> None:
    super()._update_state()
    self.blind_spot_indicators.update()
    now = time.monotonic()
    if now - self._wifi_ip_checked_at >= IP_REFRESH_S:
      self._wifi_ip_checked_at = now
      self._wifi_ip = _get_wifi_ip()

  def _render(self, rect: rl.Rectangle) -> None:
    super()._render(rect)
    self.blind_spot_indicators.render(rect)
    self._draw_current_speed(rect)
    self._draw_wifi_ip(rect)

  def _draw_wifi_ip(self, rect: rl.Rectangle) -> None:
    """Draw the current Wi-Fi IP address, small, in the top right corner."""
    if not self._wifi_ip:
      return
    try:
      ip_size = measure_text_cached(self._font_medium, self._wifi_ip, IP_FONT_SIZE)
      ip_pos = rl.Vector2(rect.x + rect.width - ip_size.x - IP_MARGIN_RIGHT, rect.y + IP_MARGIN_TOP)
      rl.draw_text_ex(self._font_medium, self._wifi_ip, ip_pos, IP_FONT_SIZE, 0, COLORS.WHITE_TRANSLUCENT)
    except Exception:
      pass

  def _draw_current_speed(self, rect: rl.Rectangle) -> None:
    """Draw the current vehicle speed (number only) at the bottom of the side panel strip."""
    # self.speed is already unit-converted in HudRenderer._update_state
    speed_text = str(round(self.speed))

    font_size = SPEED_FONT_SIZE
    speed_text_size = measure_text_cached(self._font_bold, speed_text, font_size)
    if speed_text_size.x > SPEED_USABLE_WIDTH:
      font_size = int(font_size * SPEED_USABLE_WIDTH / speed_text_size.x)
      speed_text_size = measure_text_cached(self._font_bold, speed_text, font_size)

    strip_x = rect.x + rect.width
    speed_pos = rl.Vector2(strip_x + (SIDE_PANEL_WIDTH - speed_text_size.x) / 2,
                           rect.y + rect.height - SPEED_MARGIN_BOTTOM - speed_text_size.y)

    # The strip is outside the content rect the caller clipped to (see
    # AugmentedRoadView._render), so drop the scissor mode to draw there,
    # then restore it exactly as the caller set it for the remaining draws.
    rl.end_scissor_mode()
    rl.draw_text_ex(self._font_bold, speed_text, speed_pos, font_size, 0, COLORS.WHITE)
    rl.begin_scissor_mode(int(rect.x), int(rect.y), int(rect.width), int(rect.height))

  def _has_blind_spot_detected(self) -> bool:

    return self.blind_spot_indicators.detected
