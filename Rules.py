import typing
from typing import Callable, Dict, List, Tuple

from BaseClasses import MultiWorld, CollectionState, Entrance
from .Options import NO100FOptions
from .names import ConnectionNames, ItemNames, LocationNames, RegionNames
from worlds.generic.Rules import set_rule, add_rule, CollectionRule

upgrade_rules = [
    # connections
    {
        ConnectionNames.hub1_e001: lambda player: lambda state: state.has(ItemNames.SpringPower, player),
        ConnectionNames.hub1_f001: lambda player: lambda state: state.has(ItemNames.ShovelPower, player),
        ConnectionNames.i020_i021: lambda player: lambda state: state.has(ItemNames.HelmetPower, player),
        ConnectionNames.i004_o001: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player),
        ConnectionNames.e009_c001: lambda player: lambda state: state.has(ItemNames.PoundPower, player),
        ConnectionNames.f003_f004: lambda player: lambda state: state.has(ItemNames.HelmetPower, player) and \
                                                                state.has(ItemNames.BootsPower, player),
        ConnectionNames.f003_p001: lambda player: lambda state: state.has(ItemNames.PoundPower, player),
        ConnectionNames.f009_f008: lambda player: lambda state: state.has(ItemNames.HelmetPower, player) and \
                                                                state.has(ItemNames.BootsPower, player),
        ConnectionNames.c007_g001: lambda player: lambda state: state.has(ItemNames.PlungerPower, player),
        #determine logic for f003 to f009 access
    },
    # locations
    {
        LocationNames.headless_token_i001: lambda player: lambda state: state.has(ItemNames.SpringPower, player),
        LocationNames.wolfman_token_e001: lambda player: lambda state: state.has(ItemNames.HelmetPower, player),
        LocationNames.soapammo_e007: lambda player: lambda state: state.has(ItemNames.GumPower, player),
        LocationNames.gumammo_f003: lambda player: lambda state: state.has(ItemNames.SpringPower, player) and \
                                                                 state.has(ItemNames.BootsPower, player),
        LocationNames.spacekook_token_b001: lambda player: lambda state: state.has(ItemNames.SoapPower, player),
        LocationNames.moody_token_w022: lambda player: lambda state: state.has(ItemNames.GumPower, player),
        LocationNames.seacreature_token_l014: lambda player: lambda state: state.has(ItemNames.PoundPower, player) or \
                                                                           state.has(ItemNames.UmbrellaPower, player),
    }
]
monster_token_rules = [
    # connections
    {},
    # locations
    {}
]


def _add_rules(world: MultiWorld, player: int, rules: List, allowed_loc_types: List[str]):
    for name, rule_factory in rules[0].items():
        if type(rule_factory) == tuple and len(rule_factory) > 1 and rule_factory[1]:  # force override
            rule_factory = rule_factory[0]
            set_rule(world.get_entrance(name, player), rule_factory(player))
        else:
            add_rule(world.get_entrance(name, player), rule_factory(player))
    for loc_type, type_rules in rules[1].items():
        if loc_type not in allowed_loc_types:
            continue
        for name, rule_factory in type_rules.items():
            if type(rule_factory) == tuple and len(rule_factory) > 1 and rule_factory[1]:  # force override
                rule_factory = rule_factory[0]
                set_rule(world.get_location(name, player), rule_factory(player))
            else:
                add_rule(world.get_location(name, player), rule_factory(player))


def _set_rules(world: MultiWorld, player: int, rules: List, allowed_loc_types: List[str]):
    for name, rule_factory in rules[0].items():
        set_rule(world.get_entrance(name, player), rule_factory(player))
    for loc_type, type_rules in rules[1].items():
        if loc_type not in allowed_loc_types:
            continue
        for name, rule_factory in type_rules.items():
            set_rule(world.get_location(name, player), rule_factory(player))


def set_rules(world: MultiWorld, options: NO100FOptions, player: int):
    allowed_loc_types = [ItemNames.GumPower, ItemNames.SoapPower, ItemNames.SpringPower, ItemNames.PoundPower,
                         ItemNames.HelmetPower, ItemNames.UmbrellaPower, ItemNames.ShockwavePower,
                         ItemNames.BootsPower, ItemNames.PlungerPower, ItemNames.SlipperPower, ItemNames.LampshadePower,
                         ItemNames.BlackknightPower, ItemNames.ShovelPower,
                         ItemNames.GumAmmoUpgrade, ItemNames.SoapAmmoUpgrade]
    if options.include_monster_tokens.value:
        allowed_loc_types += [ItemNames.MT_BLACKKNIGHT, ItemNames.MT_MOODY, ItemNames.MT_CAVEMAN, ItemNames.MT_CREEPER,
                              ItemNames.MT_GARGOYLE, ItemNames.MT_GERONIMO, ItemNames.MT_GHOST,
                              ItemNames.MT_GHOSTDIVER, ItemNames.MT_GREENGHOST, ItemNames.MT_HEADLESS,
                              ItemNames.MT_MASTERMIND, ItemNames.MT_ROBOT, ItemNames.MT_REDBEARD,
                              ItemNames.MT_SCARECROW,
                              ItemNames.MT_SEACREATURE, ItemNames.MT_SPACEKOOK, ItemNames.MT_TARMONSTER,
                              ItemNames.MT_WITCH, ItemNames.MT_WITCHDOC, ItemNames.MT_WOLFMAN, ItemNames.MT_ZOMBIE]

    _add_rules(world, player, upgrade_rules, allowed_loc_types)
    if options.include_monster_tokens.value:
        _add_rules(world, player, monster_token_rules, allowed_loc_types)

    world.completion_condition[player] = lambda state: state.has("Victory", player)
