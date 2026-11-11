# flacmn deck pro: housing brief

2026-11-11 · Alec (owner). Living copy: [flacmn deck pro: housing brief](https://claude.ai/artifact/3FGeBVRBxumSJjKfTsXjaT)

## Overview

The housing holds a Raspberry Pi 4 with a DAC board stacked on it, a small screen, two knobs and its connectors.
flacmn deck pro is a music player for the hi-fi shelf: line out to an amplifier, a live oscilloscope on the screen,
and streaming to the owner's phone.

- **Screen and knobs:** the owner has their own arrangement for these and will supply it. This brief lists the parts
  and their sizes only.
- **Inputs and outputs:** placement is the designer's call. The owner would like them housed primarily at the rear,
  with as few add-on parts as possible: use the boards' own sockets where you can, and add panel-mount extensions
  only where a socket can't reach the rear otherwise.
- **Fixed by the Pi:** the microSD card stays in the Pi's own slot; the housing needs a way to reach it.
- **Still open:** the screen (2″ or 3.5″) and the knob caps. Both screen sizes are given below.

Dimensions are in mm, from the makers' pages unless marked "estimate". Measure the real parts before the final
drawing.

## Components inside

The core is a two-board stack (Pi 4 with the DAC Pro on top) about 85 × 56 × 35 mm (height an estimate), mounted on
four M2.5 posts.

| Part | Size (mm) | Mounting | Notes |
| --- | --- | --- | --- |
| Raspberry Pi 4 Model B | 85 × 56 board; ~17 tall with the USB/Ethernet stack (estimate) | 4 × M2.5 holes on a 58 × 49 pattern | Use Raspberry Pi's mechanical drawing for exact port positions |
| [Raspberry Pi DAC Pro](https://www.raspberrypi.com/products/dac-pro/) (SC2077) | 65 × 56.5 (HAT size) | Same 4 holes, on 9 mm standoffs above the Pi | 40-pin pass-through header on top; its own RCA and headphone sockets, plus line-out, headphone and balanced-out headers |
| Screen, option A: [Waveshare 2″ LCD Module](https://www.waveshare.com/2inch-LCD-Module.htm) (17344) | 58 × 35 outline; lit area 40.8 × 30.6; ~4–5 thick (estimate) | Screw holes on the module | Wired to the pins with ~7 jumpers |
| Screen, option B: [Waveshare 3.5″ HDMI LCD](https://www.waveshare.com/wiki/3.5inch_HDMI_LCD) (12824) | 85 × 56.5 board; glass 84 × 55; lit area 74.16 × 49.44 | Pi-pattern holes | HDMI cable to the Pi (internal), 5 V from 2 jumpers |
| 2 × Bourns PEC11R-4220F-S0024 encoders | ~12.5 body (estimate); M7 × 0.75 bushing; 20 shaft, flatted | Nut on the panel from behind; hole 7.2–7.5 plus an anti-turn tab hole | Knob caps still to be chosen (allow up to ~25 across) |
| Heatsink or thermal pad | ~14 × 14 on the processor | Stuck on | See Heat below |
| *Only if needed:* USB-C panel-mount extension, 90° | Depends on the part | 2 screws | Only if the Pi's side USB-C socket can't reach the rear |
| *Only if needed:* 2 × RCA panel sockets, 3.5 mm panel jack | ~6–8 hole each | Nut from inside | Only if the DAC Pro's own sockets can't face the rear; wired to its headers |

Not inside: the power supply (external, official 15 W USB-C) and the music drive (the owner's USB drive, plugged in
at the back).

Models already in this repo: `projects/rpi_dac_pro`, `projects/encoder_pec11r`, `projects/lcd_35_hdmi`,
`projects/standoff_m25`, `projects/header_2x20_female`, `projects/usbc_power_cable`, `projects/rca_cable`. There is no
Raspberry Pi 4 model yet.

## Screen and knobs

The owner supplies the arrangement of the screen and knobs separately; only their cut-outs are given here.

| Part | Cut-out (mm) | Notes |
| --- | --- | --- |
| Screen window, option A (2″) | ~42 × 32 | Lit area 40.8 × 30.6 plus a ~0.5–1 margin |
| Screen window, option B (3.5″) | ~76 × 51 | Lit area 74.16 × 49.44; view area 75.96 × 51.24 |
| Knob × 2 | 7.2–7.5 hole each, plus the anti-turn tab hole | Panel thin enough for the M7 nut to catch (check the datasheet) |

## Inputs and outputs

The designer chooses where each one goes. The owner would like them housed primarily at the rear, with minimal add-on
components: the boards' own sockets are preferred over extensions. The DAC Pro's RCA and headphone sockets face the
Pi's long side, the same side as its USB-C power socket; USB and Ethernet are on the Pi's short edge (per
`projects/rpi_dac_pro`, modelled from a photo). So no single face takes every socket without an add-on: either long
side or short edge as the rear needs one. Sizes marked ~ are estimates.

| Connector | Kind | Opening (mm) | On which board |
| --- | --- | --- | --- |
| Ethernet | RJ45 | ~16 × 14 | Pi, USB/Ethernet edge |
| USB 3 × 2 (blue) | Stacked USB-A | ~15 × 16 | Pi, USB/Ethernet edge; the music drive plugs in here |
| USB 2 × 2 (black) | Stacked USB-A | ~15 × 16 | Pi, USB/Ethernet edge; spare (a CD drive later) |
| Power in | USB-C, 5 V 3 A | ~10 × 4 | Pi, long side (an extension only if it can't reach the rear) |
| Line out, left and right | 2 × RCA | ~6–8 each, ~15 apart | DAC Pro's own sockets |
| Headphones (optional) | 3.5 mm stereo jack | ~6 | DAC Pro's own socket |
| Balanced out (optional, later) | 2 × XLR or 6.35 mm TRS | ~22–24 per XLR | DAC Pro headers, above the Pi's USB/Ethernet ports |
| Status light (optional) | 3 mm LED | 3.1 | Wired to a spare pin |

No opening is needed for HDMI (it runs inside to the screen) or for a power button (the deck shuts down with a long
knob press and starts when plugged in).

## Heat, Wi-Fi and access

The housing must shed up to ~8–10 W with no fan, let Wi-Fi out, and give access to the microSD card.

- **Heat:** about 3–4 W playing and 6–8 W while converting music, plus 0.3 W (2″) to 2.5 W (3.5″) for the screen and
  ~0.5 W for the DAC. The Pi slows down at 80 °C. Best: a thermal pad from the processor to an aluminium wall or
  plate, no vents. Otherwise: a heatsink and ~10–15 cm² of slots low on the housing and ~10–15 cm² high, over the
  processor. No fan.
- **Material:** if printed, PETG or ASA near the Pi; PLA softens at ~55–60 °C.
- **Wi-Fi:** a metal housing blocks it. Leave a plastic window over the Pi's antenna (locate it on the board in hand),
  or the owner uses Ethernet.
- **microSD:** stays in the Pi's slot on the short edge opposite the USB/Ethernet ports. A slot in that wall or an
  easy-to-remove lid is enough.
- **Audio:** keep the RCA and headphone wires short and away from the USB-C power lead.
- **Feet:** rubber feet, so the housing sits still on a shelf and air can pass underneath.

**Test:** with the prototype in the housing, convert an album for 30 minutes; it should stay under ~70 °C with no
slow-down.

## Open questions

- [ ] Screen: 2″ SPI or 3.5″ HDMI? Decided after the 2″ is tested with the scope.
- [ ] Knob caps: style and diameter.
- [ ] Stack height with the DAC Pro and its sockets: measure with the parts in hand.
- [ ] Confirm with the board in hand that the DAC Pro's RCA and headphone sockets face the Pi's USB-C long side, as
  the photo-based model shows.
- [ ] Panel-mount USB-C extension: pick the part, then its cut-out.
- [ ] Where the Pi's Wi-Fi antenna sits, for the window in a metal housing.
- [ ] Balanced out: include the XLR/TRS openings now, or leave room for later?

## Sources

- [Raspberry Pi DAC Pro](https://www.raspberrypi.com/products/dac-pro/) and
  [Raspberry Pi audio boards documentation](https://www.raspberrypi.com/documentation/accessories/audio.html)
  (headers, standoffs, pass-through)
- [Waveshare 2″ LCD Module](https://www.waveshare.com/2inch-LCD-Module.htm)
- [Waveshare 3.5″ HDMI LCD wiki](https://www.waveshare.com/wiki/3.5inch_HDMI_LCD) and its drawing
- flacmn-pi `docs/hardware.md` (pins, knobs, power)
