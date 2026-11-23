# AGNOS dependency fallback

SConstruct imports 12 comma dependency packages from the AGNOS system Python
environment. Newer AGNOS images — comma's current line and StarPilot's alike —
build that environment from upstream openpilot master's dependency set, which
no longer includes `bzip2`, `catch2`, `libjpeg` or `libyuv`. Upstream dropped
them; this fork's build still imports all 12 (libjpeg has a real on-device
consumer: loggerd's `encoderd` links `jpeg` unconditionally).

In November 2026 this fork was installed on StarPilot AGNOS 19.8.1 without a
fallback and the on-device build died with `ModuleNotFoundError` (first
failure: `bzip2`), forcing a rollback to stock AGNOS. This directory is the
fix.

Contents: the four packages extracted verbatim from comma's official PyPI
wheels, aarch64 builds with static libraries:

- `bzip2` — comma-deps-bzip2 1.0.8.post97
- `catch2` — comma-deps-catch2 2.13.10.post96
- `libjpeg` — comma-deps-libjpeg 3.1.0.post92
- `libyuv` — comma-deps-libyuv 1922.0.post95

SConstruct appends this directory to `sys.path` only when the plain imports
fail, so on stock AGNOS (which ships all 12 packages) nothing changes.

## Preflight rule

Before flashing any non-stock AGNOS, diff SConstruct's `pkg_names` against
the target image's dependency set — the image builder's `uv.lock`, mapping
module names through the `comma-deps-*` distributions — and vendor whatever
is missing BEFORE the flash. The November failure was avoidable with exactly
this check; the pre-flash review at the time diffed only the kernel config,
not the userspace dependency set.
