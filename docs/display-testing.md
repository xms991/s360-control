# S360 display experiments (untested, low risk)

The S360's IPS screen ignores the K360's display firmware-version query,
but the other display commands have never been tried. Run one at a time,
in this order, watching the physical screen. Each command takes ~5s
(display probe timeout at connect — normal).

```bash
liquidctl set lcd screen settings '50;0'   # brightness 50%: dims? -> panel understands K360 cmds
liquidctl set lcd screen settings '80;0'   # restore brightness
liquidctl set lcd screen hardware 'cpu_temp;cpu_freq;fan_radiator'  # live values from the temp feed
liquidctl set lcd screen clock 0
liquidctl set lcd screen banner '0;1;Hello from Linux'
liquidctl set lcd screen disable
liquidctl set lcd screen image '0;0'       # preset image; try uploads last
```

Recovery if wedged: shutdown + PSU switch off ~30s (reboot alone does
not reset the cooler; fan control is unaffected either way).

If nothing responds at all: the IPS uses a different command set; next
step is capturing MSI Center traffic (Windows VM + USB passthrough +
Wireshark/usbmon). See https://github.com/liquidctl/liquidctl/blob/main/docs/developer/capturing-usb-traffic.md
