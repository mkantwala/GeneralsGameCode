"""Check buildable Rafale data integration; does not simulate the game."""

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
    objects = '\n'.join(read(p) for p in (INI / 'Object').rglob('*.ini'))
    definitions = set(re.findall(r'^(?:Object|ChildObject)\s+(\S+)', objects, re.M))
    unit_path = INI / 'Object/Europe/Aircraft/RafaleF4.ini'
    unit = block(read(unit_path), 'Object', 'EuropeJetRafaleF4')
    depth = 1
    for line in unit.splitlines():
        line = line.split(';', 1)[0].strip()
        if not line:
            continue
        if line.lower() == 'end':
            depth -= 1
        elif '=' not in line or line.split('=', 1)[0].strip() in {
                'Draw', 'ConditionState', 'Body', 'Behavior'}:
            depth += 1
        require(depth >= 1, 'Early block closure')
    require(depth == 1, 'Unclosed unit block')
    require(field(unit, 'Side') == 'Europe', 'Wrong faction')
    require('PRODUCED_AT_HELIPAD' in field(unit, 'KindOf'), 'Missing helipad production')
    require('SELECTABLE' in field(unit, 'KindOf'), 'Not selectable')
    for forbidden in ('JetAIUpdate', 'DeliverPayloadAIUpdate', 'TransportContain',
                      'GenPowerAirplaneArmor', 'StealthUpdate', 'MaxHealthUpgrade'):
        require(forbidden not in unit, 'Unexpected support/landing behavior: ' + forbidden)
    require('Behavior = AIUpdateInterface' in unit, 'Missing continuous-flight AI')
    for prerequisite in re.findall(r'^\s*Object\s*=\s*(\S+)', unit, re.M):
        require(prerequisite in definitions, 'Missing prerequisite: ' + prerequisite)
    buttons, sets = read(INI / 'CommandButton.ini'), read(INI / 'CommandSet.ini')
    button_name = 'Command_ConstructEuropeJetRafaleF4'
    button = block(buttons, 'CommandButton', button_name)
    require(field(button, 'Object') == 'EuropeJetRafaleF4', 'Wrong build target')
    for menu_name in ('EuropeanDeploymentZone', field(unit, 'CommandSet')):
        menu = block(sets, 'CommandSet', menu_name)
        slots = re.findall(r'^\s*(\d+)\s*=\s*(\S+)', menu, re.M)
        require(len(slots) == len(dict(slots)), 'Duplicate menu slots')
        if menu_name == 'EuropeanDeploymentZone':
            require(dict(slots).get('4') == button_name, 'Missing Deployment Zone button')
        for _, command in slots:
            block(buttons, 'CommandButton', command)
    weapon = block(read(INI / 'Weapon.ini'), 'Weapon', field(unit, 'Weapon').split()[1])
    require(field(weapon, 'ProjectileObject') in definitions, 'Missing projectile')
    require(field(weapon, 'AutoReloadsClip') == 'Yes', 'Must reload without a runway')
    require(int(field(weapon, 'ClipSize')) > 0, 'Missing finite payload')
    for flag in ('AntiAirborneVehicle', 'AntiAirborneInfantry'):
        require(field(weapon, flag) == 'No', 'Bombs must not target aircraft')
    block(read(INI / 'Armor.ini'), 'Armor', field(unit, 'Armor'))
    for name in re.findall(r'^\s*Locomotor\s*=\s*\S+\s+(\S+)', unit, re.M):
        block(read(INI / 'Locomotor.ini'), 'Locomotor', name)
    strings = read(ROOT / 'archives/Rotr_English/Data/Generals.str')
    for key in (field(unit, 'DisplayName'), field(button, 'TextLabel'), field(button, 'DescriptLabel')):
        require(len(re.findall(r'^' + re.escape(key) + r'\s*$', strings, re.M)) == 1,
                'Missing/duplicate string: ' + key)
    models = ROOT / 'archives/Rotr_W3D/Art/W3D'
    for name in set(re.findall(r'^\s*Model\s*=\s*(\S+)', unit, re.M)) - {'NONE'}:
        require((models / (name + '.W3D')).is_file(), 'Missing model: ' + name)
    for name in ('EVBomber', 'EVBomber_D'):
        require(b'WEAPONA01\0' in (models / (name + '.W3D')).read_bytes().upper(),
                'Missing bomb-release bone: ' + name)
    mapped = '\n'.join(read(p) for p in (INI / 'MappedImages').rglob('*') if p.is_file())
    for key in ('SelectPortrait', 'ButtonImage'):
        require(re.search(r'^MappedImage\s+' + field(unit, key) + r'\s*$', mapped, re.M),
                'Missing UI image')
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for archive in ('Rotr_INI', 'Rotr_English'):
            source = ROOT / 'archives' / archive
            pack(source, tmp / (archive + '.big'))
            extract(tmp / (archive + '.big'), tmp / archive)
            for path in source.rglob('*'):
                if path.is_file():
                    require(path.read_bytes() == (tmp / archive / path.relative_to(source)).read_bytes(),
                            'Archive round-trip changed bytes')
    print('Rafale build integration, airborne reload, model attachments and BIG round trips passed.')
    print('Spawning, circling and bombing passes still require in-game validation.')


if __name__ == '__main__':
    main()
