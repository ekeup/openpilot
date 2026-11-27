"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
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


class HudRendererSP(HudRenderer):
  def __init__(self):
    super().__init__()
    self.blind_spot_indicators = BlindSpotIndicators()

  def _update_state(self) -> None:
    super()._update_state()
    self.blind_spot_indicators.update()

  def _render(self, rect: rl.Rectangle) -> None:
    super()._render(rect)
    self.blind_spot_indicators.render(rect)
    self._draw_current_speed(rect)

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
