"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import math

import pyray as rl

from openpilot.common.constants import CV
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

# Erik's request (Nov 27, 2026): lead-car chip at bottom-centre, above the
# torque bar — "<distance> m · <relative speed> mph", no "LEAD" label. It is
# drawn here rather than in the model renderer so it stays crisp after the
# onroad fade, like the speed readout. Units follow the approved mockup
# (metres / mph) regardless of the metric setting. The chip is centred but
# clamped so it can never reach the steering wheel icon (left) or the speed
# readout (right, wide enough for a 3-digit speed).
CHIP_FONT_SIZE = 30
CHIP_PADDING_X = 16
CHIP_PADDING_Y = 7
CHIP_MARGIN_BOTTOM = 62  # torque bar top edge reaches at most ~54px above the bottom
CHIP_SIDE_RESERVE_LEFT = 80
CHIP_SIDE_RESERVE_RIGHT = 150
CHIP_BG_COLOR = rl.Color(0, 0, 0, 170)


class HudRendererSP(HudRenderer):
  def __init__(self):
    super().__init__()
    self.blind_spot_indicators = BlindSpotIndicators()
    self._lead_present: bool = False
    self._lead_d_rel: float = 0.0
    self._lead_v_rel: float = 0.0

  def _update_state(self) -> None:
    super()._update_state()
    self.blind_spot_indicators.update()

    sm = ui_state.sm
    lead = sm['radarState'].leadOne if sm.valid['radarState'] else None
    self._lead_present = bool(lead and lead.status and math.isfinite(lead.dRel) and math.isfinite(lead.vRel))
    if self._lead_present:
      self._lead_d_rel = lead.dRel
      self._lead_v_rel = lead.vRel

  def _render(self, rect: rl.Rectangle) -> None:
    super()._render(rect)
    self.blind_spot_indicators.render(rect)
    self._draw_current_speed(rect)
    self._draw_lead_chip(rect)

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

  def _draw_lead_chip(self, rect: rl.Rectangle) -> None:
    """Draw the lead distance / relative speed chip, bottom-centre above the torque bar."""
    if not self._lead_present:
      return

    rel_speed_mph = round(self._lead_v_rel * CV.MS_TO_MPH)
    chip_text = f"{max(0.0, self._lead_d_rel):.0f} m · {rel_speed_mph:+d} mph"
    text_size = measure_text_cached(self._font_semi_bold, chip_text, CHIP_FONT_SIZE)

    chip_width = text_size.x + 2 * CHIP_PADDING_X
    chip_height = text_size.y + 2 * CHIP_PADDING_Y
    chip_x = rect.x + (rect.width - chip_width) / 2
    chip_x = min(max(chip_x, rect.x + CHIP_SIDE_RESERVE_LEFT),
                 max(rect.x + CHIP_SIDE_RESERVE_LEFT, rect.x + rect.width - CHIP_SIDE_RESERVE_RIGHT - chip_width))
    chip_y = rect.y + rect.height - CHIP_MARGIN_BOTTOM - chip_height

    rl.draw_rectangle_rounded(rl.Rectangle(chip_x, chip_y, chip_width, chip_height), 0.5, 10, CHIP_BG_COLOR)
    rl.draw_text_ex(self._font_semi_bold, chip_text, rl.Vector2(chip_x + CHIP_PADDING_X, chip_y + CHIP_PADDING_Y),
                    CHIP_FONT_SIZE, 0, COLORS.WHITE)

  def _has_blind_spot_detected(self) -> bool:

    return self.blind_spot_indicators.detected
