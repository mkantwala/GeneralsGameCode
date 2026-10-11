"""Check the buildable Tu-160's INI references, model attachments and packaging.

This checks data integration only; it does not simulate aircraft or combat.
"""

from pathlib import Path
import re
import tempfile

from bigfile import extract, pack


ROOT = Path(__file__).resolve().parents[1]
INI = ROOT / "archives/Rotr_INI/Data/INI"


def read(path):
    return path.read_bytes().decode("cp1252")


def block(text, kind, name):
    matches = list(re.finditer(
        rf"^{kind}\s+{re.escape(name)}\s*(?:;[^\r\n]*)?\r?\n(.*?)^End\s*$",
        text, re.MULTILINE | re.DOTALL,
    ))
    if len(matches) != 1:
        raise ValueError(f"Expected one {kind} {name}, found {len(matches)}")
    return matches[0].group(1)


def field(text, name):
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*([^;\r\n]+)", text, re.MULTILINE)
    if match is None:
        raise ValueError(f"Missing field: {name}")
    return match[1].strip()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    objects = "\n".join(read(path) for path in (INI / "Object").rglob("*.ini"))
    definitions = set(re.findall(r"^(?:Object|ChildObject)\s+(\S+)", objects, re.MULTILINE))
    unit_path = INI / "Object/Russia/Aircraft/Tu160Bomber.ini"
    unit = block(read(unit_path), "Object", "RussiaJetTu160Bomber")
    # Validate nesting in the new object, including Draw and Behavior sub-blocks.
    depth = 1
    for line in unit.splitlines():
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        if line.casefold() == "end":
            depth -= 1
        elif "=" not in line or line.split("=", 1)[0].strip() in {
            "Draw", "ConditionState", "Body", "Behavior",
        }:
            depth += 1
        require(depth >= 1, "Object sub-block closes too early")
    require(depth == 1, "Unclosed object sub-block")

    buttons = read(INI / "CommandButton.ini")
    sets = read(INI / "CommandSet.ini")
    button_name = "Command_ConstructRussiaJetTu160Bomber"
    button = block(buttons, "CommandButton", button_name)
    require(field(button, "Command") == "UNIT_BUILD", "Build button is not UNIT_BUILD")
    require(field(button, "Object") == "RussiaJetTu160Bomber", "Build button targets wrong object")
    for name in ("RussiaAirfieldCommandSet", "RussiaAirfieldCommandSetSnow"):
        menu = block(sets, "CommandSet", name)
        slots = re.findall(r"^\s*(\d+)\s*=\s*(\S+)", menu, re.MULTILINE)
        require(len(slots) == len({slot for slot, _ in slots}), f"Duplicate slot in {name}")
        require(button_name in dict(slots).values(), f"Bomber missing from {name}")
    controls = block(sets, "CommandSet", field(unit, "CommandSet"))
    for command in re.findall(r"^\s*\d+\s*=\s*(\S+)", controls, re.MULTILINE):
        block(buttons, "CommandButton", command)
    for prerequisite in re.findall(r"^\s*Object\s*=\s*(\S+)", unit, re.MULTILINE):
        require(prerequisite in definitions, f"Missing prerequisite: {prerequisite}")

    weapon_name = field(unit, "Weapon").split()[1]
    weapon = block(read(INI / "Weapon.ini"), "Weapon", weapon_name)
    require(field(weapon, "ProjectileObject") in definitions, "Missing bomb projectile")
    require(field(weapon, "AutoReloadsClip") == "RETURN_TO_BASE", "Bombs reload in flight")
    require(int(field(weapon, "ClipSize")) > 0, "Bomber has unlimited ammunition")
    require(field(weapon, "AntiAirborneVehicle") == "No", "Bomber can attack aircraft")
    require(field(weapon, "AntiAirborneInfantry") == "No", "Bomber can attack airborne infantry")
    block(read(INI / "Armor.ini"), "Armor", field(unit, "Armor"))
    locomotors = dict(re.findall(r"^\s*Locomotor\s*=\s*(\S+)\s+(\S+)", unit, re.MULTILINE))
    for name in locomotors.values():
        block(read(INI / "Locomotor.ini"), "Locomotor", name)
    for name in ("AttackLocomotorType", "ReturnForAmmoLocomotorType"):
        require(field(unit, name) in locomotors, f"Missing locomotor set for {name}")
    require(float(field(unit, "AttackersMissPersistTime")) == 0, "Aurora targeting protection enabled")
    require(float(field(unit, "SneakyOffsetWhenAttacking")) == 0, "Aurora targeting offset enabled")
    require("SELECTABLE" in field(unit, "KindOf").split(), "Bomber is not selectable")
    for support_flag in ("IGNORED_IN_GUI", "EMP_HARDENED", "FORCEATTACKABLE"):
        require(support_flag not in field(unit, "KindOf").split(), f"Support-only flag: {support_flag}")

    particles = read(INI / "ParticleSystem.ini")
    for name in set(re.findall(r"^\s*ParticleSysBone\s*=\s*\S+\s+(\S+)", unit, re.MULTILINE)):
        block(particles, "ParticleSystem", name)
    effects = read(INI / "FXList.ini")
    for name in set(re.findall(r"^\s*(?:FX\w+|FireFX|ProjectileDetonationFX)\s*=\s*(\S+)",
                               unit + weapon, re.MULTILINE)):
        block(effects, "FXList", name)
    audio = read(INI / "Voice.ini") + read(INI / "SoundEffects.ini")
    for name in set(re.findall(r"^\s*(?:Voice\w+|SoundAmbient|FireSound)\s*=\s*(\S+)",
                               unit + weapon, re.MULTILINE)):
        block(audio, "AudioEvent", name)

    strings = read(ROOT / "archives/Rotr_English/Data/Generals.str")
    images = "\n".join(read(path) for path in (INI / "MappedImages").rglob("*.[iI][nN][iI]"))
    for label in (field(unit, "DisplayName"), field(button, "TextLabel"), field(button, "DescriptLabel")):
        require(len(re.findall(rf"^{re.escape(label)}\s*$", strings, re.MULTILINE)) == 1,
                f"Missing or duplicate string: {label}")
    for image in (field(unit, "ButtonImage"), field(unit, "SelectPortrait"), field(button, "ButtonImage")):
        block(images, "MappedImage", image)
    draw_states = re.findall(r"^    (?:DefaultConditionState|ConditionState\s*=[^\r\n]*)\r?\n(.*?)^    End",
                             unit, re.MULTILINE | re.DOTALL)
    for state in draw_states:
        model = field(state, "Model")
        path = ROOT / f"archives/Rotr_W3D/Art/W3D/{model}.W3D"
        require(path.is_file(), f"Missing W3D model: {model}")
        data = path.read_bytes().upper()
        bones = re.findall(r"^\s*ParticleSysBone\s*=\s*(\S+)", state, re.MULTILINE)
        for bone in bones:
            require(bone.upper().encode("ascii") + b"\0" in data,
                    f"Missing particle attachment {bone} in {model}")
        if "WeaponLaunchBone" in state:
            bone = field(state, "WeaponLaunchBone").split()[1].upper().encode("ascii")
            require(bone + b"\0" in data or bone + b"01\0" in data,
                    f"Missing bomb-release bone in {model}")

    # Exercise the actual archive writer and reader with every changed game file.
    changed = [unit_path, INI / "CommandButton.ini", INI / "CommandSet.ini",
               INI / "Weapon.ini", INI / "Locomotor.ini",
               ROOT / "archives/Rotr_English/Data/Generals.str"]
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        source = temp / "source"
        for path in changed:
            # All archive paths begin with Data/, regardless of archive folder.
            relative = Path(*path.parts[path.parts.index("Data"):])
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
        count = pack(source, temp / "tu160-check.big")
        require(count == len(changed), "Missing file in test archive")
        extract(temp / "tu160-check.big", temp / "extracted")
        for path in source.rglob("*"):
            if path.is_file():
                require(path.read_bytes() == (temp / "extracted" / path.relative_to(source)).read_bytes(),
                        f"Archive round-trip changed bytes: {path.name}")
    print("Tu-160 data integration, model attachments and BIG round-trip checks passed.")


if __name__ == "__main__":
    main()
