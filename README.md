# S360 control — MSI MEG CoreLiquid S360 on Linux

Fan/pump control and CPU temperature feed for the S360, using a patched
fork of liquidctl. The S360 is not supported by upstream liquidctl; this
builds on PR liquidctl/liquidctl#784 (closed unmerged) plus local fixes
(`patches/s360-fixes.patch`).

The S360 has **no temperature sensor of its own**: fan curves only work
because `s360_feed.py` sends the CPU temperature to the cooler every 2
seconds. That feed runs as the systemd user service `s360-fancontrol`.

## Restore on a fresh machine

1. Copy this directory to `$HOME/s360-control`
2. Run `./setup.sh`

That installs pip deps to `~/.local`, clones liquidctl + applies the PR
and local fixes, installs the udev rule, and starts the service.

## Layout

- `setup.sh` — idempotent installer (re-run any time)
- `s360_feed.py` — feeder daemon; **fan/pump curves are at the top of this file**
- `s360-fancontrol.service` — systemd user unit
- `patches/s360-fixes.patch` — local fixes on top of PR #784
- `udev/72-liquidctl-s360.rules` — unprivileged access to 0db0:6a05
- `liquidctl/` — created by setup.sh (upstream + PR + patch)

## Daily use

```bash
~/.local/bin/liquidctl status                    # rpm/duty readout
~/.local/bin/liquidctl set fans speed 100        # fixed speed override
systemctl --user restart s360-fancontrol         # re-apply curves
journalctl --user -u s360-fancontrol -f          # logs
```

## License

GPL-3.0-or-later, same as liquidctl. The patch in `patches/` is a
derivative work of [liquidctl](https://github.com/liquidctl/liquidctl)
(GPL-3.0-or-later) and builds on PR liquidctl/liquidctl#784 by marrufa.

Notes:

- Only "Fan 1" reports RPM: the three radiator fans daisy-chain into one
  header on the pump block.
- The IPS screen is not controllable (its commands time out; each command
  to the device carries a ~5s probe delay as a result — harmless).
- Fixed speeds set via `liquidctl set` persist until the cooler loses
  power or the service re-applies the curves on next start.
- Display/screen commands (`set lcd ...`) are untested on the S360.
