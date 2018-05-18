import re
import json
import BigWorld
import nations
import ResMgr
from functools import wraps, partial
from items import vehicles, _xml
from constants import ITEM_DEFS_PATH
from helpers.EffectsList import _PixieEffectDesc
from helpers.bound_effects import ModelBoundEffects, StaticSceneBoundEffects
from gui.mods.goldvisibility_prereqs import files as prerequisites


# load and parse json file
def load_json_from_file(file_path):
    try:
        with open(file_path, 'r') as json_file:
            # credits to https://regex101.com/r/fJ1aC6/1
            # not perfect though, "//" in strings will be matched as comments!
            without_comments = re.sub('(\/\*[\S\s]*?\*\/)|(\/\/[^\n]*)', '', json_file.read(), flags=re.M)
            return json.loads(without_comments)
    except (IOError, ValueError):
        return None


config = load_json_from_file('res_mods/configs/goldvisibility.json') \
         or load_json_from_file('mods/configs/goldvisibility.json') \
         or {}


class PrerequisitesLoader:
    def __init__(self, prerequisites):
        self._prerequisites = None
        BigWorld.loadResourceListBG(prerequisites, self.__on_prerequisites_loaded)

    def has(self, file):
        return self._prerequisites is not None and self._prerequisites.has_key(file)

    def __on_prerequisites_loaded(self, refs):
        self._prerequisites = refs


class ModifiedValueManager:
    def __init__(self):
        self._values = []

    def modify(self, container, key, value):
        self._values.append((container, key, container[key]))
        container[key] = value

    def restore(self):
        for (container, key, restore_value) in self._values:
            container[key] = restore_value
        self._values = []


# decorator for running callback before the specified function is called
def run_before(module, func_name):
    def decorator(callback):
        func = getattr(module, func_name)

        @wraps(func)
        def run_before_wrapper(*args, **kwargs):
            callback(*args, **kwargs)
            return func(*args, **kwargs)

        setattr(module, func_name, run_before_wrapper)
        return callback

    return decorator


def load_shell_prices(nation):
    xml_path = ITEM_DEFS_PATH + 'vehicles/' + nation + '/components/shells.xml'
    section = ResMgr.openSection(xml_path)

    prices = {}
    for name, subsection in section.items():
        if name in ('icons', 'xmlns:xmlref'):
            continue

        xml_ctx = (None, xml_path + '/' + name)
        shell_id = _xml.readInt(xml_ctx, subsection, 'id', 0, 65535)
        prices[shell_id] = _xml.readPrice(xml_ctx, subsection, 'price')

    ResMgr.purge(xml_path, True)
    return prices


def get_pixie_files(effects_list):
    effects_desc = getattr(effects_list, '_EffectsList__effectDescList')
    for effect_desc in effects_desc:
        if isinstance(effect_desc, _PixieEffectDesc):
            file_container = getattr(effect_desc, '_files')
            for (index, file_path) in enumerate(file_container):
                yield file_container, index, file_path


def get_shell_eff_files(effects_list):
    for container, key, file_path in get_pixie_files(effects_list):
        match = re.search('^particles/Shells_Eff/([a-zA-Z0-9_-]+)\.xml$', file_path)
        if match is not None:
            effect_name = match.group(1)
            yield container, key, file_path, effect_name


def get_gun(attacker_id, players):
    attacker = players.get(attacker_id, None)
    if attacker is None:
        return None
    gun, _ = attacker['vehicleType'].getComponentsByType('vehicleGun')
    return gun


# return gold ammo shell types for gun
def get_gold_ammo_types_from_prices(shell_prices, default_gold_ammo_types, gun):
    if gun is None:
        return default_gold_ammo_types

    # no shell buyable with gold
    # shell is considered 'gold' if credits price is higher then the avg shell price for the gun
    # WG removed gold price in patch 1.0.1 for gold shells
    credits_prices = []
    for shot in gun.shots:
        nation_id, shell_id = shot.shell.id
        credits_price = shell_prices[nation_id][shell_id].get('credits', 0)
        credits_prices.append(credits_price)

    avg_price = reduce(lambda total, price: total + price, credits_prices, 0) / len(credits_prices)
    premium_shells = [index for (index, price) in enumerate(credits_prices) if price > avg_price]

    return map(lambda index: gun.shots[index].shell.kind, premium_shells)


get_gold_ammo_types = partial(
    get_gold_ammo_types_from_prices,
    map(lambda nation: load_shell_prices(nation), nations.NAMES),
    config.get('gold_ammo_types_for_unspotted_vehicles', [])
)


# return True if the gun uses the gold shell type as standard shell type as well
def is_gold_shell_type_ambiguous(shell_type, gun):
    if gun is None:
        return False

    gold_shell_types = get_gold_ammo_types(gun)

    if shell_type not in gold_shell_types:
        return False

    shell_types = map(lambda s: s.shell.kind, gun.shots)

    occ_in_shell_types = reduce(lambda total, st: int(st == shell_type) + total, shell_types, 0)
    occ_in_gold_shell_types = reduce(lambda total, st: int(st == shell_type) + total, gold_shell_types, 0)

    return occ_in_shell_types > occ_in_gold_shell_types


# in game id is different form the player().id
def get_ingame_player_id(player, players):
    player_name = player.name
    return [player_id for (player_id, player) in players.items() if player['name'] == player_name][0]


def is_own_player(attacker_id, player, players):
    return get_ingame_player_id(player, players) == attacker_id


def get_team_id(player_id, players):
    return players.get(player_id, {}).get('team', None)


def is_allied_player(attacker_id, player, players):
    own_team_id = get_team_id(get_ingame_player_id(player, players), players)
    attacker_team_id = get_team_id(attacker_id, players)
    return attacker_team_id == own_team_id and own_team_id is not None


def is_team_member(attacker_id, player, players):
    return is_allied_player(attacker_id, player, players) and not is_own_player(attacker_id, player, players)


def settings_effect_must_show(display_settings, player, players, shell_type, gun, attacker_id):
    return (not is_gold_shell_type_ambiguous(shell_type, gun) or display_settings['display_if_ambiguous']) \
           and (not is_own_player(attacker_id, player, players) or display_settings['display_for_own']) \
           and (not is_team_member(attacker_id, player, players) or display_settings['display_for_allies']) \
           and (is_allied_player(attacker_id, player, players) or display_settings['display_for_enemy'])


effect_must_show = partial(settings_effect_must_show, {
    'display_if_ambiguous': config.get('display_effect_if_ammo_type_ambiguous', False),
    'display_for_own': config.get('display_effect_for_own_shots', False),
    'display_for_allies': config.get('display_effect_for_allied_shots', False),
    'display_for_enemy': config.get('display_effect_for_enemy_shots', True)
})


def shell_type_from_effect_name(effect_name):
    shell_type = 'ARMOR_PIERCING'
    if '_AP_CR' in effect_name.upper():
        shell_type = 'ARMOR_PIERCING_CR'
    elif '_HC' in effect_name.upper():
        shell_type = 'HOLLOW_CHARGE'
    elif '_HE' in effect_name.upper():
        shell_type = 'HIGH_EXPLOSIVE'
    return shell_type


# Restore effects and modify PixieEffectDescription file names to point to modified effects for gold shells
def restore_effects_and_modify_effect(modified_file_name_mgr, prereq_loader, effects_list, attacker_id):
    # restore modified effects to their default
    modified_file_name_mgr.restore()

    player = BigWorld.player()
    players = player.arena.vehicles
    gun = get_gun(attacker_id, players)
    gold_ammo_types = get_gold_ammo_types(gun)

    for container, key, file_path, effect_name in get_shell_eff_files(effects_list):
        shell_type = shell_type_from_effect_name(effect_name)

        new_file_path = 'particles/Shells_Eff/' + effect_name + '_prem.xml'
        if shell_type in gold_ammo_types and prereq_loader.has(new_file_path) \
                and effect_must_show(player, players, shell_type, gun, attacker_id):
            modified_file_name_mgr.modify(container, key, new_file_path)


modify_effect = partial(
    restore_effects_and_modify_effect,
    ModifiedValueManager(),
    PrerequisitesLoader(prerequisites)
)


@run_before(StaticSceneBoundEffects, 'addNew')
def modify_static_bound_effect(*args, **kwargs):
    return modify_effect(args[2], kwargs.get('attackerID', 0))


@run_before(ModelBoundEffects, 'addNewToNode')
def modify_model_bound_effect(*args, **kwargs):
    return modify_effect(args[3], kwargs.get('attackerID', 0))
