# Buildable ECA Rafale F4

Adds a Rafale F4 to Deployment Zone slot 3 in Bomber mode, requiring the Research
and Development Compound. The unit intentionally reuses the existing Vulcan visual models at
50% scale; its silhouette is not that of a real Rafale. Existing support-power
Vulcans remain separate. This is a gameplay adaptation with automatic airborne
reloading, not a simulation of real aircraft rearming.

| Parameter | Value |
| --- | --- |
| Health | 200 |
| Cost / construction time | $3,000 / 40 seconds |
| Armor | AirplaneArmor |
| Speed / damaged speed | 140 / 100 |
| Turn rate / damaged turn rate | 70 / 50 degrees per second |
| Flight height / circling radius | 100 / 100 |
| Payload | Two 200-damage bombs, radius 25, 300 ms release interval |
| Attack range | 250 |
| Reload | 20 seconds automatically while airborne |
| Protection | No stealth, countermeasures or Aurora attack protection |
| Targeting | Ground only |

The unit uses the Harrier's helipad production flag and AIUpdateInterface pattern
because the Deployment Zone has no runway or parking slots. It uses its own
locomotor, weapon, build button and command set. Existing Vulcan models, ambient
sound, smart-bomb UI images, Harrier voice lines and the conventional Aurora bomb
projectile/effects are reused. Harrier voices may still identify their original
unit; no new voice assets are included. Damage type AURORA_BOMB controls armor
interactions and does not grant Aurora flight protection.

Run `python3 mods/rotr/tools/check_rafale.py` to validate menu and definition
references, airborne reload configuration, model release attachments and lossless
BIG archive round trips. GitHub Actions runs the same check. These checks do not
simulate flight: deployment spawning, circling, bombing passes, reload timing,
selection geometry, visuals, sound and balance need in-game testing. The original
import manifest remains the release baseline.

## Deployment Zone aircraft modes

Each Deployment Zone starts in Fighter mode, with the Harrier in slot 3. The
free, instant switch in slot 4 opens Bomber mode, which replaces the Harrier
button with the Rafale F4. The same slot switches back to Fighter mode. Tiger
and Marksman helicopters, battlegroups, Desperate Barrage and Sell are identical
in both menus. Already queued aircraft continue production after switching.

Dedicated object-scoped upgrades make the choice local to each building. The
repeatable CommandSetUpgrade pattern removes the opposite mode upgrade and
clears the return trigger when switching back, as existing ROTR menu switches do.
The Deployment Zone's MaxSimultaneousOfType = 1 restriction is removed, allowing
multiple buildings subject to the usual cost, power and placement requirements.
Repeat switching, independent modes across multiple zones, construction and
production queues still require in-game verification.
