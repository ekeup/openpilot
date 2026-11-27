"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import pyray as rl

from openpilot.selfdrive.ui.onroad.augmented_road_view import BORDER_COLORS
from openpilot.selfdrive.ui.sunnypilot.mici.onroad.speed_strip import BALL_RADIUS, BALL_RING_RADIUS, SPEED_ZONE_H
from openpilot.selfdrive.ui.ui_state import ui_state, UIStatus


class ConfidenceBallSP:
  @staticmethod
  def get_dot_center_y(f: float, rect: rl.Rectangle) -> float:
    """Centre y of the confidence dot for filtered confidence f in [-0.5, 1].

    Stock maps f linearly over the full panel height, which puts the dot's
    painted footprint (disc plus its 35px black ring) at the very bottom of
    the side panel when f reaches 0 — exactly where Erik's speed number now
    lives. This remap reserves the bottom SPEED_ZONE_H px for the number:
    engaged travel (f in [0, 1]) runs from the stock top down to a stop
    whose ring bottom just touches the zone top, and the disengaged range
    (f in [-0.5, 0]) continues from that stop to the stock off-screen park
    position, so the dot still parks below the screen and the map stays
    continuous at f = 0.
    """
    f = min(max(f, -0.5), 1.0)
    top = rect.y + BALL_RADIUS
    stop = rect.y + rect.height - SPEED_ZONE_H - BALL_RING_RADIUS
    if f >= 0:
      return top + (1 - f) * (stop - top)
    park = rect.y + rect.height + 72  # stock park position at f = -0.5 (240px panel)
    return stop + (-f / 0.5) * (park - stop)

  @staticmethod
  def get_animate_status_probs():
    if ui_state.status == UIStatus.LAT_ONLY:
      return ui_state.sm['modelV2'].meta.disengagePredictions.steerOverrideProbs

    # UIStatus.LONG_ONLY
    return ui_state.sm['modelV2'].meta.disengagePredictions.brakeDisengageProbs

  @staticmethod
  def get_lat_long_dot_color():
    if ui_state.status == UIStatus.LAT_ONLY:
      return BORDER_COLORS[UIStatus.LAT_ONLY]

    # UIStatus.LONG_ONLY
    return BORDER_COLORS[UIStatus.LONG_ONLY]
