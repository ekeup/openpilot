"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""

# Shared geometry for Erik's current-speed readout in the mici side panel
# (Nov 27, 2026). The 60px strip right of the camera view is shared by the
# confidence ball (above) and the speed number (bottom). The ball's painted
# footprint is bigger than its 24px disc: draw_circle_gradient adds a black
# ring out to a 35px radius, and the ball is rendered with the FULL view
# rect, its centre 24px left of the screen's right edge, so the footprint
# reaches to within ~1px of the camera view's right edge. The bottom
# SPEED_ZONE_H px of the strip are reserved for the speed number, and the
# ball's travel is remapped (ConfidenceBallSP.get_dot_center_y) so its ring
# never enters that zone while engaged.
BALL_RADIUS = 24
BALL_RING_RADIUS = 35
SPEED_ZONE_H = 48
SPEED_FONT_SIZE = 36
SPEED_USABLE_WIDTH = 54  # SIDE_PANEL_WIDTH (60) minus 3px padding per side
SPEED_MARGIN_BOTTOM = 4
