# Rise of the Reds 1.85 development base

Imported from `ROTRBeta_185.zip`, supplied by the project owner via ModDB.
This is the 1.85 release, without later patches. The game engine above this
directory is unchanged. Engine compatibility and gameplay have not been tested.
The development changes below extend the imported release.

## Editable content

Each original `.gib` archive has its own directory under `archives/`.
Keeping those directories separate preserves overlapping archive paths and
the original archive priority when rebuilding. Development edits retain the
existing encodings, filenames, and attribution.

Start with `archives/Rotr_INI/Data/INI/`:

- `PlayerTemplate.ini`: playable faction definitions and starting buildings.
- `Object/`: unit and building definitions, organized by faction.
- `CommandButton.ini` and `CommandSet.ini`: build buttons and command menus.
- `Weapon.ini`, `Armor.ini`, `Upgrade.ini`, and `Science.ini`: gameplay definitions.

In this release, Russia uses `FactionAmericaLaserGeneral` and the side
`AmericaLaserGeneral`; ECA uses `FactionAmericaSuperWeaponGeneral` and the side
`AmericaSuperWeaponGeneral`. Their `BaseSide` values are `Russia` and `ECA`.
Preserve those identifiers until all references have been accounted for.

Other archive directories contain W3D models, textures, sounds, music,
localization, maps, GUI windows, and AI scripts. The `.scb` scripts are binary,
not editable text. `runtime/` preserves the installer's loose files, including
the launcher, World Builder, optional installers, and original executables;
none were executed during import. `upstream/` contains the original readme,
changelog, and installer license notice.

`manifest.json` records the package and archive SHA-256 hashes, and the path,
size, and SHA-256 hash of every imported archive and loose runtime file.
It describes the original release: `verify_import.py` detects differences from
that baseline, including intentional development edits. Do not regenerate the
release manifest to make edited files appear to be original release content.

## Buildable Russia Tu-160 White Swan

The Russian Airfield offers the Tu-160 after construction of the Industrial
Site, in both normal and snow variants. It costs $2,800, takes 35 seconds to
build, and has 220 health with standard `AirplaneArmor`. Each sortie carries
three conventional bombs, each dealing 180 base damage in a radius of 25,
released 200 milliseconds apart. It returns to the airfield for an eight-second
reload. Cruise, attack, and return speeds are 170, 220, and 150 respectively;
turn rate is 90 degrees per second and flight height is 100. It has no stealth,
countermeasure upgrade, or Aurora attack-run targeting protection.

The aircraft reuses `RVTU160`, `RVTU160_D`, and `RVTU160_D1` at 50% scale, the
stock FOAB icon, and existing Russian aircraft voices. It uses Aurora's bomb
projectile and `AURORA_BOMB` damage type, so target armor affects actual damage.
The existing FOAB support aircraft is separate and unchanged.

Run the data integration and archive round-trip checks from the repository root:

```sh
python mods/rotr/tools/check_tu160.py
```

These checks validate references, production menus, model attachment points,
and lossless BIG packing. They do not replace in-game testing. Before release,
check parking, takeoff, landing, all three bomb releases, rearming, damaged
models, and AA vulnerability on normal and snow maps.

## Rebuild mod archives

From the repository root, with Python 3.10 or newer:

```sh
python mods/rotr/tools/build_archives.py build/rotr
```

This produces the original archive names with `.big` extensions, including
their leading exclamation marks. Use a dedicated development game installation
with the required original Zero Hour files. Avoid mixing rebuilt archives with
another installed ROTR version. The tools do not install or launch the game,
modify the registry, or replace its executable. Runtime integration with the
engine fork remains a separate step.

## Ownership and publication

ROTR material remains attributed to SWR Productions, EA Games, and the
contributors named by the upstream files. Importing it does not relicense it
under the engine's GPL. The project owner identified themselves as a ROTR
developer and authorized this import, then explicitly confirmed publication
to the public `mkantwala/GeneralsGameCode` repository on the `rotr-base` branch.
The importer verifies the release SHA-256 before extracting any content and
does not execute the installer.
