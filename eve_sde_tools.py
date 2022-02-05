import os
import typing
import yaml
import json
from yaml import SafeLoader


def get_yaml(f_name: str):
    with open(f_name, 'r', encoding='utf8') as f:
        s = f.read()
        yaml_data = yaml.load(s, Loader=SafeLoader)
        f.close()
        return yaml_data


def get_yaml_fragment(f_name: str, item: str):
    item_to_search = "\n{}".format(item)
    with open(f_name, 'r', encoding='utf8') as f:
        contents = f.read()
        beg = contents.find(item_to_search)
        if beg == -1:
            return {}
        beg = beg + len(item_to_search)
        # debug:print("{} = {}".format(item, beg))
        end = beg + 1
        length = len(contents)
        while True:
            end = contents.find("\n", end)
            if (end == -1) or (end == (length-1)):
                yaml_contents = contents[beg:length].encode('utf-8')
                break
            if contents[end+1] == ' ':
                end = end + 1
            else:
                yaml_contents = contents[beg:beg+end-beg].encode('utf-8')
                break
        yaml_data = yaml.load(yaml_contents, Loader=SafeLoader)
        return yaml_data


def get_converted_name(ws_dir, name):
    return '{dir}/sde_cache/.converted_{nm}.json'.format(dir=ws_dir, nm=name)


def read_converted(ws_dir, name):
    f_name_json = get_converted_name(ws_dir, name)
    with open(f_name_json, 'r', encoding='utf8') as f:
        s = f.read()
        json_data = (json.loads(s))
        return json_data


def write_converted(ws_dir: str, name: str, data):
    f_name_json = get_converted_name(ws_dir, name)
    with open(f_name_json, 'wt+', encoding='utf8') as f:
        s: str = json.dumps(data, indent=1, sort_keys=False)
        f.write(s)
        f.close()


def main():
    cwd: str = os.path.dirname(os.path.realpath(__file__))
    sde_universe_path = '{cwd}/sde_cache/fsd/universe/eve'.format(cwd=cwd)
    positions_filename: str = get_converted_name(cwd, "invPositions")
    universe_systems: typing.Dict[int, typing.Any] = {}

    # если заранее проиндексированного файла из Q.Industrialist нет, то медленно читаем все файлы в fst/universe
    if not os.path.isfile(positions_filename):
        for path, dirs, files in os.walk(sde_universe_path):
            for f in files:
                if f != 'solarsystem.staticdata':
                    continue
                solar_system = get_yaml('{}/{}'.format(path, f))
                if 'solarSystemID' in solar_system:
                    solar_system_id: int = int(solar_system['solarSystemID'])
                    data = solar_system['center']
                    data.append(solar_system['luminosity'])
                    universe_systems[solar_system_id] = data
                    del data
                del solar_system
    else:
        sde_inv_positions = read_converted(cwd, "invPositions")
        for path, dirs, files in os.walk(sde_universe_path):
            for f in files:
                if f != 'solarsystem.staticdata':
                    continue
                solar_system_id = int(get_yaml_fragment('{}/{}'.format(path, f), 'solarSystemID:'))
                luminosity = float(get_yaml_fragment('{}/{}'.format(path, f), 'luminosity:'))
                position = sde_inv_positions[str(solar_system_id)]
                universe_systems[solar_system_id] = [position['x'], position['y'], position['z'], luminosity]
        del sde_inv_positions

    write_converted(cwd, 'fsdUniversePositions', universe_systems)


if __name__ == "__main__":
    main()
