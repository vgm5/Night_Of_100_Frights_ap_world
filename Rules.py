import typing
from typing import Callable, Dict, List, Tuple

from BaseClasses import MultiWorld, CollectionState, Entrance
from .Options import NO100FOptions
from .names import ConnectionNames, ItemNames, LocationNames, RegionNames
from worlds.generic.Rules import set_rule, add_rule, CollectionRule


upgrade_rules = [
    # connections
    {
        ConnectionNames.hub1_e001: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1),
        ConnectionNames.hub1_f001: lambda player: lambda state: state.has(ItemNames.ShovelPower, player, 1),
        ConnectionNames.i020_i021: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),
        # ConnectionNames.hub1_gl01: lambda player: lambda state: state.has(ItemNames.spat, player, 10),
        # ConnectionNames.hub1_b1: lambda player: lambda state: state.has(ItemNames.spat, player, 15),
        # ConnectionNames.hub2_rb01: lambda player: lambda state: state.has(ItemNames.spat, player, 25),
        # ConnectionNames.hub2_sm01: lambda player: lambda state: state.has(ItemNames.spat, player, 30),
        # ConnectionNames.hub2_b2: lambda player: lambda state: state.has(ItemNames.spat, player, 40),
        # ConnectionNames.hub3_kf01: lambda player: lambda state: state.has(ItemNames.spat, player, 50),
        # ConnectionNames.hub3_gy01: lambda player: lambda state: state.has(ItemNames.spat, player, 60),
        # ConnectionNames.cb_b3: lambda player: lambda state: state.has(ItemNames.spat, player, 75),
    },
    # locations
    {
        # ItemNames.spat: {
        #    LocationNames.spat_ks_01: lambda player: lambda state: state.has(ItemNames.spat, player, 5),
        #    LocationNames.spat_ks_02: lambda player: lambda state: state.has(ItemNames.spat, player, 10),
        #   LocationNames.spat_ks_03: lambda player: lambda state: state.has(ItemNames.spat, player, 15),
        #   LocationNames.spat_ks_04: lambda player: lambda state: state.has(ItemNames.spat, player, 20),
        #   LocationNames.spat_ks_05: lambda player: lambda state: state.has(ItemNames.spat, player, 25),
        #  LocationNames.spat_ks_06: lambda player: lambda state: state.has(ItemNames.spat, player, 30),
        #  LocationNames.spat_ks_07: lambda player: lambda state: state.has(ItemNames.spat, player, 35),
        #   LocationNames.spat_ks_08: lambda player: lambda state: state.has(ItemNames.spat, player, 40),
        # }
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
