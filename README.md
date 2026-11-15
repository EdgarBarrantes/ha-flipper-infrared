# Flipper Zero Infrared

Use a Flipper Zero connected by USB as an **infrared emitter** in Home Assistant. It shows up as an
`infrared` entity, so any integration built on Home Assistant's infrared platform can send through
it: Gree Infrared, [Gree I Feel](https://github.com/EdgarBarrantes/ha-gree-ifeel), and others.

It sends raw timings with the Flipper's own command line (`ir tx RAW`), so it works with the stock
firmware and its forks (tested on Momentum), with no app to install on the Flipper.

## Requirements

- Home Assistant 2026.10 or newer, on Linux (Home Assistant OS, Container with the device passed
  through, or Core).
- A Flipper Zero on a USB data cable to the Home Assistant machine, unlocked and on its main screen.
  The top edge (the infrared LED) must face the devices to control.

## Install

Settings > Marketplace (HACS on older versions) > add this repository as a custom repository
(type Integration), install **Flipper Zero Infrared**, restart, then Settings > Devices & services
> Add integration > Flipper Zero Infrared and pick the port (`/dev/serial/by-id/usb-Flipper_...`).

## Notes

- One command at a time: the port is opened for each command and closed after, so qFlipper or a
  script can use it in between (not at the same moment).
- While a Flipper app that takes over USB is open (for example its Bluetooth or USB remotes), the
  command line doesn't answer and sends fail.
- Range is a few metres: the LED is small. Aim it.

MIT licensed.
