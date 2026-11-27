"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import math

import numpy as np
import pyray as rl

from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached

# Erik's request (Nov 27, 2026): a large following-gap readout in seconds
# under the lead car on the mici onroad view, drawn together with the stock
# lead chevron (ModelRenderer._draw_lead_indicator). The matching distance /
# relative-speed chip lives in HudRendererSP so it is drawn after the onroad
# fade, next to the other HUD elements. Sized for the mici surface (536x240,
# content rect 476x240): the block goes below the chevron when it fits above
# the reserved bottom zone (torque bar + chip), otherwise above the chevron,
# the same strategy as tici's ChevronMetrics.
GAP_FONT_SIZE = 44
GAP_LABEL_FONT_SIZE = 20
GAP_TOP_MARGIN = 10
GAP_LINE_SPACING = 3
GAP_BOTTOM_RESERVE = 114  # px reserved at bottom-centre for the chip and torque bar
MIN_GAP_EGO_SPEED = 1.0   # m/s; below this a gap in seconds is meaningless
MAX_GAP_SECONDS = 30.0    # beyond this it is not a following gap worth showing

SCREEN_MARGIN = 16


class LeadDisplay:
  def __init__(self):
    self._font_bold = gui_app.font(FontWeight.BOLD)
    self._font_medium = gui_app.font(FontWeight.MEDIUM)

  def draw(self, sm, radar_state, rect: rl.Rectangle, lead_vehicles) -> None:
    """Draw the following gap in seconds under the lead chevron, if a lead is present."""
    lead = radar_state.leadOne
    if not lead or not lead.status:
      return

    lead_vehicle = lead_vehicles[0]
    if not lead_vehicle.chevron or len(lead_vehicle.chevron) < 3:
      return

    v_ego = sm['carState'].vEgo
    if not math.isfinite(lead.dRel) or not math.isfinite(v_ego):
      return
    if v_ego < MIN_GAP_EGO_SPEED:
      return
    gap = lead.dRel / v_ego
    if not 0.0 < gap <= MAX_GAP_SECONDS:
      return

    gap_text = f"{gap:.1f} s"
    gap_size = measure_text_cached(self._font_bold, gap_text, GAP_FONT_SIZE)
    label_text = tr("GAP")
    label_size = measure_text_cached(self._font_medium, label_text, GAP_LABEL_FONT_SIZE)
    block_height = gap_size.y + GAP_LINE_SPACING + label_size.y

    chevron_x = lead_vehicle.chevron[1][0]
    text_y = lead_vehicle.chevron[0][1] + GAP_TOP_MARGIN
    if text_y + block_height > rect.height - GAP_BOTTOM_RESERVE:
      # No room below the chevron: draw the block above it instead
      text_y = lead_vehicle.chevron[1][1] - GAP_TOP_MARGIN - block_height
    # Hard cap: the block must never enter the reserved bottom zone (chip +
    # torque bar), even when a close lead pushes the chevron itself into it
    text_y = min(text_y, rect.height - GAP_BOTTOM_RESERVE - block_height)
    text_y = float(np.clip(text_y, SCREEN_MARGIN, max(SCREEN_MARGIN, rect.height - SCREEN_MARGIN - block_height)))

    gap_x = float(np.clip(chevron_x - gap_size.x / 2, SCREEN_MARGIN, max(SCREEN_MARGIN, rect.width - gap_size.x - SCREEN_MARGIN)))
    label_x = float(np.clip(chevron_x - label_size.x / 2, SCREEN_MARGIN, max(SCREEN_MARGIN, rect.width - label_size.x - SCREEN_MARGIN)))

    shadow_color = rl.Color(0, 0, 0, 200)
    rl.draw_text_ex(self._font_bold, gap_text, rl.Vector2(gap_x + 2, text_y + 2), GAP_FONT_SIZE, 0, shadow_color)
    rl.draw_text_ex(self._font_bold, gap_text, rl.Vector2(gap_x, text_y), GAP_FONT_SIZE, 0, rl.WHITE)
    label_y = text_y + gap_size.y + GAP_LINE_SPACING
    rl.draw_text_ex(self._font_medium, label_text, rl.Vector2(label_x + 1, label_y + 1), GAP_LABEL_FONT_SIZE, 0, shadow_color)
    rl.draw_text_ex(self._font_medium, label_text, rl.Vector2(label_x, label_y), GAP_LABEL_FONT_SIZE, 0, rl.Color(255, 255, 255, 200))
