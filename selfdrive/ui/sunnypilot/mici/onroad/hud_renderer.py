"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import pyray as rl

from openpilot.selfdrive.ui.mici.onroad.hud_renderer import HudRenderer, COLORS
from openpilot.selfdrive.ui.sunnypilot.onroad.blind_spot_indicators import BlindSpotIndicators
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached

# Erik's request (Nov 27, 2026): current-speed readout in the bottom-right
# corner of the camera view. The number is right-aligned to the content
# rect's right edge (the side panel strip to its right belongs to the
# confidence ball, whose disc never reaches this far left), and the block
# sits on the bottom edge, clear of the torque bar's arc at bottom-center.
SPEED_FONT_SIZE = 72
SPEED_UNIT_FONT_SIZE = 28
SPEED_MARGIN_RIGHT = 18
SPEED_MARGIN_BOTTOM = 16


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
    """Draw the current vehicle speed and unit, bottom-right of the camera view."""
    # self.speed is already unit-converted in HudRenderer._update_state
    speed_text = str(round(self.speed))
    speed_text_size = measure_text_cached(self._font_bold, speed_text, SPEED_FONT_SIZE)

    unit_text = tr("km/h") if ui_state.is_metric else tr("mph")
    unit_text_size = measure_text_cached(self._font_medium, unit_text, SPEED_UNIT_FONT_SIZE)

    right_edge = rect.x + rect.width - SPEED_MARGIN_RIGHT
    unit_pos = rl.Vector2(right_edge - unit_text_size.x,
                          rect.y + rect.height - SPEED_MARGIN_BOTTOM - unit_text_size.y)
    speed_pos = rl.Vector2(right_edge - speed_text_size.x,
                           unit_pos.y - speed_text_size.y - 2)

    rl.draw_text_ex(self._font_bold, speed_text, speed_pos, SPEED_FONT_SIZE, 0, COLORS.WHITE)
    rl.draw_text_ex(self._font_medium, unit_text, unit_pos, SPEED_UNIT_FONT_SIZE, 0, COLORS.WHITE_TRANSLUCENT)

  def _has_blind_spot_detected(self) -> bool:

    return self.blind_spot_indicators.detected
