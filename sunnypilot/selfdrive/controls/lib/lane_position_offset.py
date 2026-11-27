"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import math

from cereal import log

from openpilot.common.params import Params

LaneChangeState = log.ModelDataV2.MetaData.LaneChangeState

# A true lane-position offset, added for Erik (Nov 27, 2026) after a Claude
# code review showed CameraOffset cannot do this job: it only warps the
# model's input image, over a designed range of -0.35..+0.35, with no
# guaranteed relationship to where the car ends up in the lane.
#
# This loop instead measures where the car actually sits in the lane (from
# modelV2's ego lane lines), runs a small PI controller on the error versus
# the LanePositionOffset param, and returns a curvature bias that controlsd
# adds to the model's desired curvature before clip_curvature. Gains are
# starting values from the design review and are unverified on the road;
# the safety envelope below (caps, slew, gates, divergence latch) is the
# part that must not be loosened without a re-review.
MAX_OFFSET = 0.30          # m, hard clamp on the setpoint, whatever the param says
KP = 0.08                  # 1/s^2, proportional gain on the lateral error
KI = 0.02                  # 1/s^3, integral gain (needed: the model re-centres itself)
INTEGRAL_LIMIT = 0.20      # m/s^2, clamp on the integral's contribution
A_BIAS_LIMIT = 0.30        # m/s^2, clamp on the total lateral-accel bias
SETPOINT_SLEW = 0.03       # m/s, the applied setpoint moves no faster than this
MIN_SPEED = 11.0           # m/s, no offset below this
MIN_CURVATURE_SPEED = 8.0  # m/s, floor in the accel -> curvature conversion
MIN_LINE_PROB = 0.6        # both ego lane lines must be at least this confident
MAX_LINE_STD = 0.3         # m, and at least this steady (design-review estimate)
MIN_LANE_WIDTH = 2.5       # m, sane-lane sanity bounds
MAX_LANE_WIDTH = 4.5       # m
MAX_CENTRE_OFFSET = 1.2    # m, sanity bound on the measured centre offset
CENTRE_FILTER_TAU = 0.5    # s, first-order filter on the measured centre offset
DIVERGENCE_MARGIN = 0.5    # m of error beyond |setpoint| before the latch trips
DIVERGENCE_TIME = 2.0      # s the divergence must persist before latching off


class LanePositionOffset:
  def __init__(self):
    self.params = Params()
    self.offset_param = 0.0  # metres, + = right of lane centre

    self.centre = 0.0          # filtered measured car offset, + = right of centre
    self.applied = 0.0         # slew-limited setpoint actually being chased
    self.integral = 0.0        # integral of the lateral error
    self.divergence_timer = 0.0
    self.latched_off = False   # divergence latch; clears on disengage

  def get_params(self) -> None:
    try:
      val = float(self.params.get("LanePositionOffset", return_default=True))
    except (TypeError, ValueError):
      val = 0.0
    if not math.isfinite(val):
      val = 0.0
    self.offset_param = max(-MAX_OFFSET, min(MAX_OFFSET, val))

  def reset(self) -> None:
    self.centre = 0.0
    self.applied = 0.0
    self.integral = 0.0
    self.divergence_timer = 0.0
    self.latched_off = False

  def update(self, model_v2, CS, lat_active: bool, freeze_integral: bool, dt: float) -> float:
    """Curvature bias (1/m, + = left) to add to the desired curvature."""
    if not lat_active:
      self.reset()
      return 0.0

    # Measure where the car sits in the lane. Model frame: y is + left.
    # laneLines[1] is the left ego line, laneLines[2] the right ego line,
    # and y[0] is at x ~= 0, i.e. at the car.
    y_left = model_v2.laneLines[1].y[0]
    y_right = model_v2.laneLines[2].y[0]
    lane_width = y_left - y_right
    # Lane centre in the car frame: + means the centre is to the car's
    # left, i.e. the car itself sits that far RIGHT of centre.
    c_raw = (y_left + y_right) / 2.0
    alpha = dt / (CENTRE_FILTER_TAU + dt)
    self.centre += alpha * (c_raw - self.centre)

    # Every gate must hold, or the offset fades out.
    gated = (
      model_v2.meta.laneChangeState == LaneChangeState.off and
      CS.vEgo >= MIN_SPEED and
      not CS.steeringPressed and
      not CS.standstill and
      model_v2.laneLineProbs[1] >= MIN_LINE_PROB and
      model_v2.laneLineProbs[2] >= MIN_LINE_PROB and
      model_v2.laneLineStds[1] < MAX_LINE_STD and
      model_v2.laneLineStds[2] < MAX_LINE_STD and
      MIN_LANE_WIDTH < lane_width < MAX_LANE_WIDTH and
      abs(c_raw) < MAX_CENTRE_OFFSET and
      not self.latched_off
    )

    target = self.offset_param if gated else 0.0

    # Slew the applied setpoint toward the target, so live changes from
    # the sunnylink button arrive gently (0.15 m takes about 5 s).
    step = SETPOINT_SLEW * dt
    if self.applied < target:
      self.applied = min(self.applied + step, target)
    elif self.applied > target:
      self.applied = max(self.applied - step, target)

    if self.applied == 0.0:
      # Nothing to chase: the model's own centring is the behaviour.
      # Bleed the integral away so a later re-engage starts clean.
      self.integral *= max(0.0, 1.0 - dt / 2.0)
      self.divergence_timer = 0.0
      return 0.0

    e = self.applied - self.centre  # + means: the car must move further right

    # Divergence latch: error far beyond the setpoint and not closing
    # means a sign error or oscillation — off until the next disengage.
    if abs(e) > abs(self.applied) + DIVERGENCE_MARGIN:
      self.divergence_timer += dt
      if self.divergence_timer > DIVERGENCE_TIME:
        self.latched_off = True
        self.integral = 0.0
        return 0.0
    else:
      self.divergence_timer = 0.0

    if not freeze_integral:
      self.integral += e * dt
    integral_term = max(-INTEGRAL_LIMIT, min(INTEGRAL_LIMIT, KI * self.integral))

    # Lateral-accel bias; rightward is negative (curvature is + left).
    a_bias = -(KP * e + integral_term)
    a_bias = max(-A_BIAS_LIMIT, min(A_BIAS_LIMIT, a_bias))

    kappa_bias = a_bias / max(CS.vEgo, MIN_CURVATURE_SPEED) ** 2
    return kappa_bias if math.isfinite(kappa_bias) else 0.0
