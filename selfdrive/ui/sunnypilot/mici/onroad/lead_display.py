"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import math

import numpy as np
import pyray as rl

from openpilot.common.constants import CV
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

# Erik's request (Nov 27, 2026, revised the same evening): the only lead-car
# readout he wants is the lead vehicle's own speed — a bare number, no unit
# label, overlaid at the lead car's position on the camera view. This
# replaces the earlier same-day display (chevron + gap-in-seconds hero +
# distance/relative-speed chip), which he found too much; the chevron, the
# gap readout and the chip are all gone. The number is centred on the spot
# the stock lead chevron occupied (its position still comes from
# ModelRenderer._update_leads) and is drawn in the model renderer like the
# chevron was, so it follows the chevron's visibility: shown whenever the
# lead indicator renders (openpilot longitudinal control + valid
# radarState), including while disengaged.
LEAD_SPEED_FONT_SIZE = 39
MAX_LEAD_SPEED = 100.0  # m/s; beyond this the radar value is not sane

SCREEN_MARGIN = 16


class LeadDisplay:
  def __init__(self):
    self._font_bold = gui_app.font(FontWeight.BOLD)

  def draw(self, sm, radar_state, rect: rl.Rectangle, lead_vehicles) -> None:
    """Draw the lead vehicle's speed (bare number) at the lead car's position."""
    lead = radar_state.leadOne
    if not lead or not lead.status:
      return

    lead_vehicle = lead_vehicles[0]
    if not lead_vehicle.chevron or len(lead_vehicle.chevron) < 3:
      return

    # Absolute lead speed: radard's vLead when it is populated, otherwise
    # reconstruct it from ego speed + relative speed.
    v_lead = None
    if math.isfinite(lead.vLead) and lead.vLead > 0.0:
      v_lead = lead.vLead
    else:
      v_ego = sm['carState'].vEgo
      if math.isfinite(lead.vRel) and math.isfinite(v_ego):
        v_lead = v_ego + lead.vRel
    if v_lead is not None and -0.5 <= v_lead < 0.0:
      v_lead = 0.0  # filter noise around a stopped lead, not a real negative speed
    if v_lead is None or not math.isfinite(v_lead) or not 0.0 <= v_lead <= MAX_LEAD_SPEED:
      return

    conversion = CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH
    speed_text = str(round(v_lead * conversion))
    text_size = measure_text_cached(self._font_bold, speed_text, LEAD_SPEED_FONT_SIZE)

    # Centre the number on the chevron's position: apex x, midway between
    # the apex and the base.
    chevron = lead_vehicle.chevron
    center_x = chevron[1][0]
    center_y = (chevron[1][1] + chevron[0][1]) / 2
    text_x = float(np.clip(center_x - text_size.x / 2, SCREEN_MARGIN,
                           max(SCREEN_MARGIN, rect.width - text_size.x - SCREEN_MARGIN)))
    text_y = float(np.clip(center_y - text_size.y / 2, SCREEN_MARGIN,
                           max(SCREEN_MARGIN, rect.height - text_size.y - SCREEN_MARGIN)))

    shadow_color = rl.Color(0, 0, 0, 200)
    rl.draw_text_ex(self._font_bold, speed_text, rl.Vector2(text_x + 2, text_y + 2), LEAD_SPEED_FONT_SIZE, 0, shadow_color)
    rl.draw_text_ex(self._font_bold, speed_text, rl.Vector2(text_x, text_y), LEAD_SPEED_FONT_SIZE, 0, rl.WHITE)
