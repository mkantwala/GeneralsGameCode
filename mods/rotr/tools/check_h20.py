"""Check H-20 faction/build integration and lossless archive packaging."""
from pathlib import Path
import re
import tempfile

from bigfile import pack, extract

ROOT = Path(__file__).resolve().parents[1]
INI = ROOT / 'archives/Rotr_INI/Data/INI'


def read(path):
    return path.read_bytes().decode('cp1252').replace('\r\n', '\n')


def block(text, kind, name):
    matches = re.findall(rf'^{kind} {re.escape(name)}\s*\n(.*?)^End\s*$', text,
                         flags=re.M | re.S)
    assert len(matches) == 1, f'Missing or duplicate {kind}: {name}'
    return matches[0]


def main():
    unit_path = INI / 'Object/China/Aircraft/H20Bomber.ini'
    unit = read(unit_path)
    objects = '\n'.join(read(p) for p in (INI / 'Object').rglob('*.ini'))
    assert len(re.findall(r'^Object AmericaJetAurora\s*$', objects, re.M)) == 1
    assert re.search(r'^\s*Side\s*= China\s*$', unit, re.M)
    for prerequisite in ('ChinaAirfield', 'ChinaPropagandaCenter'):
        assert re.search(rf'^\s*Object\s*= {prerequisite}\s*$', unit, re.M)
        assert re.search(rf'^Object {prerequisite}\s*$', objects, re.M)
    assert 'Upgrade_America' not in unit
    assert 'CountermeasuresAirplaneArmor' not in unit
    assert 'CountermeasuresBehavior' not in unit
    assert 'StealthUpdate' not in unit
    buttons = read(INI / 'CommandButton.ini')
    button = block(buttons, 'CommandButton', 'Command_ConstructChinaJetH20')
    assert re.search(r'^\s*Object\s*= AmericaJetAurora\s*$', button, re.M)
    sets = read(INI / 'CommandSet.ini')
    china = block(sets, 'CommandSet', 'ChinaAirfieldCommandSet')
    usa = block(sets, 'CommandSet', 'AmericaAirfieldCommandSet')
    assert '5 = Command_ConstructChinaJetH20' in china
    assert 'Aurora' not in usa and 'H20' not in usa
    for menu in (china, usa):
        slots = re.findall(r'^\s*(\d+)\s*=', menu, re.M)
        assert len(slots) == len(set(slots)), 'Duplicate airfield slot'
        for command in re.findall(r'^\s*\d+\s*= (\w+)', menu, re.M):
            block(buttons, 'CommandButton', command)
    commandset = re.search(r'^\s*CommandSet\s*= (\w+)', unit, re.M)[1]
    block(sets, 'CommandSet', commandset)
    strings = read(ROOT / 'archives/Rotr_English/Data/Generals.str')
    labels = re.findall(r'^\s*(?:DisplayName|TextLabel|DescriptLabel)\s*= (\S+)',
                        unit + '\n' + button, re.M)
    for label in labels:
        assert len(re.findall(rf'^{re.escape(label)}$', strings, re.M)) == 1, label
    # Full gameplay archive round trip catches path collisions and byte corruption.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for archive in ('Rotr_INI', 'Rotr_English'):
            source = ROOT / 'archives' / archive
            target = tmp / archive
            pack(source, tmp / (archive + '.big'))
            extract(tmp / (archive + '.big'), target)
            for path in source.rglob('*'):
                if path.is_file():
                    assert path.read_bytes() == (target / path.relative_to(source)).read_bytes()
    print('H-20 faction, build-menu, string and BIG round-trip checks passed.')


if __name__ == '__main__':
    main()
