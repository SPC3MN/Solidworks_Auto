# airmn: feasibility of an upward-blowing fan

Estimate, 2026-11-08. Question: replace the plug fan (radial discharge, turned up by the lid) with angled blades
that send the air straight up, so the filtered air leaves at right angles to the air coming in through the
pleats, and keep the pressure loss as low as possible.

Numbers come from [upflow_estimate.py](upflow_estimate.py) (rerun it after changing any input). They are first-order
estimates (velocity heads, textbook loss factors, typical efficiencies), good to about ±30 %. Duty: 500 m³/h, filter
2.4 Pa (brief), lid grid as now (7.2 holes, 62 % open, R200).

## Short answer

**Feasible, and a better match than the plug fan.** At 500 m³/h and about 5 Pa, the specific speed is about 3.5 to 4,
which is axial-fan territory. A plug fan is a radial machine and works far from its best point at this duty. A
400 mm axial fan with outlet guide vanes, at about 265 rpm, needs about 12 % less pressure, about 40 % less shaft
power, and has the same tip speed (so a similar noise level). Two further changes lower the pressure more (below).

## Options compared

| | A: plug fan + lid turn (now) | B: axial 400, outlet guide vanes |
| --- | --- | --- |
| Flow path | radial out, 90° turn in the lid, up through the grid | straight up from the core, through rotor and vanes, out through the grid |
| System pressure | 5.7 Pa | 5.0 Pa |
| Speed / tip speed | 335 rpm / 5.3 m/s | 265 rpm / 5.5 m/s |
| Specific speed Ωs (best: radial < 1.5, axial > 3) | 4.1 (mismatch) | 3.5 (match) |
| Efficiency (shaft) | about 0.30 | about 0.45 |
| Shaft power / torque | 2.6 W / 0.77 kg·cm | 1.5 W / 0.57 kg·cm |

Where the pressure goes (Pa):

| Loss | A | B |
| --- | --- | --- |
| Filter (brief) | 2.40 | 2.40 |
| Core and bellmouth (core speed 2.0 m/s) | 0.36 | 0.36 |
| Spider and motor in the inflow | 0.71 | 0.71 |
| 90° turn in the lid | 1.04 | none |
| Core to fan annulus | none | 0.23 |
| Swirl left after the vanes | (swirl lost in the lid) | 0.12 |
| Perforated top (K 1.73 at 1.07 m/s) | 1.18 | 1.18 |
| **Total** | **5.69** | **5.00** |

A mixed-flow (diagonal) fan would also turn the flow upward. It falls between the two on these numbers, but needs
conical hub and shroud surfaces (printing supports, and no revolve in `swlib` yet), so it is not the first choice.

## Lowering the pressure further

1. **Motor inside the fan's hub, carried by the guide vanes.** A 0.45 hub ratio on 400 mm gives a 180 mm hub, room
   for the 25 mm gearmotor, the coupling and both 608 bearings. The guide vanes become the motor mount, so the spider
   and motor leave the core: **−0.7 Pa (to about 4.3 Pa)**, and the brief's "nothing in front of the eye" rule holds
   again. The vanes also take the motor off any large flat panel (the brief's noise rule 1).
2. **More open top.** At 75 % open instead of 62 %, the grid factor drops from 1.73 to about 0.8: **−0.6 Pa (to about
   3.7 Pa)**. Bigger holes or a thinner web do it. Keep finger safety by putting the grid above the vanes, so the
   rotor sits behind both.

With both, the system needs about 3.7 Pa instead of 5.7, and about 1.1 W at the shaft instead of 2.6 (estimates).

## Axial fan, first sizing (option B)

| Item | Value |
| --- | --- |
| Rotor | 400 mm tip (fills the 425 lid), hub 180 mm, axial speed 1.4 m/s through the annulus |
| Duty coefficients | flow φ 0.25, pressure ψ 0.14: a lightly loaded fan, so flat or slightly cambered printed blades will do |
| Blade angles | flow meets the tip about 76° from the axis and the hub about 61°: steep, high-stagger blades with little turning |
| Blade count | 7 rotor blades against 11 vanes (no common factor; also none with the 5 tie rods) |
| Spacing | at least one blade chord between rotor and vanes (the brief's tone rule) |
| Motor | 0.57 kg·cm at 265 rpm, about half of the 12 V 300 rpm motor's 1.2 kg·cm rating: the in-spec 12 V motor now fits. Blade pitch sets the final speed. |

## Risks and unknowns

- **Steep pressure curve and stall.** An axial fan loses flow faster than a plug fan as the filter loads. A dirty
  filter at twice the loss (about 7.4 Pa total) pushes ψ to about 0.2, still workable, but check it on the flow box
  (test step 3) with a part-blocked filter.
- **Rotor–vane tone.** The main new noise source. Counts with no common factor, the chord spacing and swept or leaned
  vanes deal with it. Measure it at test step 7.
- **Loss factors are textbook values.** The lid turn (1.0 velocity head) and the spider (0.3) are the least certain.
  The flow box can measure A and B directly.
- **Modelling.** Angled blades need sketches on tilted planes, which `swlib` does not do yet (Z, Y and X-normal planes
  only). It is a small extension: a reference plane at an angle about an axis.

## Recommendation

Go to option B, with the motor in the hub on the guide vanes and a more open top. Keep the plug-fan parts as the
fallback until test step 3 compares the two on the flow box.
