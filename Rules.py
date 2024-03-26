import typing
from typing import Callable, Dict, List, Tuple

from BaseClasses import MultiWorld, CollectionState, Entrance
from .Options import NO100FOptions
from .names import ConnectionNames, ItemNames, LocationNames, RegionNames
from worlds.generic.Rules import set_rule, add_rule, CollectionRule

upgrade_rules = [
    # connections
    {
        # Hub
        ConnectionNames.hub1_e001: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1),
        ConnectionNames.hub1_f001: lambda player: lambda state: state.has(ItemNames.ShovelPower, player, 1),

        # Manor
        ConnectionNames.i020_i021: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),
        ConnectionNames.i003_b004: lambda player: lambda state: state.has(ItemNames.SoapPower, player, 1),
        ConnectionNames.i003_i004: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),
        ConnectionNames.i004_o001: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1),
        ConnectionNames.i006_r001: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1),

        # Rooftops

        # Balcony
        ConnectionNames.o001_o008: lambda player: lambda state: state.has(ItemNames.BootsPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

        # Hedge
        ConnectionNames.e009_c001: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),

        # Fishing Village
        ConnectionNames.f003_f004: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.BootsPower, player, 1),
        ConnectionNames.f003_p001: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),
        ConnectionNames.f009_f008: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.BootsPower, player, 1),

        # Coast
        ConnectionNames.c001_c002: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),
        ConnectionNames.c007_g001: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),
        ConnectionNames.c005_c006: lambda player: lambda state: state.has(ItemNames.PlungerPower, player, 1),

        # Passage
        ConnectionNames.p001_p002: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),
        ConnectionNames.p004_p005: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PlungerPower, player, 1),
        ConnectionNames.p005_b001: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1),
        ConnectionNames.p002_s001: lambda player: lambda state: state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
        ConnectionNames.p003_p004: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1),

        # Secret Lab
        ConnectionNames.s001_s002: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.PoundPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1),

        # Basement
        ConnectionNames.b001_b002: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1) or state.has(ItemNames.SoapPower, player, 1),

        # Lighthouse
        ConnectionNames.l017_l018: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),
        ConnectionNames.l015_w020: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1),

        # Wrecked Ships
        ConnectionNames.w020_w021: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
    },
    # locations
    {
        ItemNames.Upgrades:
        {
            # Hub

            # Manor

            # Rooftops

            # Balcony

            # Hedge
            LocationNames.soapammo_e007: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

            # Fishing Village
            LocationNames.gumammo_f003: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1) and state.has(ItemNames.BootsPower, player, 1) and state.has(ItemNames.PoundPower, player, 1),
            LocationNames.soapammo_f001: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1) or (state.has(ItemNames.SpringPower, player, 1) and (state.has(ItemNames.GumPower, player, 1) or state.has(ItemNames.SoapPower, player, 1))),
            # Coast
            LocationNames.gumammo_c003: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1) or (state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.UmbrellaPower, player, 1)),

            # Passage

            # Secret Lab

            # Basement

            # Graveyard
            LocationNames.soapammo_g003: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),

            # Lighthouse
            LocationNames.soapammo_l019: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1) and (state.has(ItemNames.SoapPower, player, 1) or state.has(ItemNames.GumPower, player, 1)),
            LocationNames.gumammo_l011: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1) and (state.has(ItemNames.PlungerPower, player, 1) or state.has(ItemNames.SoapPower, player, 1) or state.has(ItemNames.GumPower, player, 1)),
            # Wrecked Ships
        },

        ItemNames.MonsterTokens:
        {
            # Hub

            # Manor
            LocationNames.headless_token_i001: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1),

            # Rooftops
            LocationNames.witchdoctor_token_r020: lambda player: lambda state: state.has(ItemNames.PlungerPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

            # Balcony
            LocationNames.creeper_token_o002: lambda player: lambda state: state.has(ItemNames.PlungerPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1),

            # Hedge
            LocationNames.wolfman_token_e001: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),
            LocationNames.witch_token_e003: lambda player: lambda state: state.has(ItemNames.BootsPower, player, 1),

            # Fishing Village
            LocationNames.tarmonster_token_f004: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1),
            LocationNames.ghostdiver_token_f007: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1),

            # Coast
            LocationNames.greenghost_token_c005: lambda player: lambda state: state.has(ItemNames.SoapPower, player, 1),

            # Passage

            # Secret Lab

            # Basement
            LocationNames.spacekook_token_b001: lambda player: lambda state: state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1),

            # Lighthouse
            LocationNames.seacreature_token_l014: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1) or state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
            LocationNames.caveman_token_l013: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

            # Wrecked Ships
            LocationNames.moody_token_w022: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1) or state.has(ItemNames.SoapPower, player, 1),
            LocationNames.redbeard_token_w025: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1) or state.has(ItemNames.SoapPower, player, 1),
        },

        ItemNames.victory:
        {
            LocationNames.Credits: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1),
        }
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
    allowed_loc_types = [ItemNames.Upgrades,ItemNames.victory]
    if options.include_monster_tokens.value:
        allowed_loc_types += [ItemNames.MonsterTokens]

    _add_rules(world, player, upgrade_rules, allowed_loc_types)
    if options.include_monster_tokens.value:
        _add_rules(world, player, monster_token_rules, allowed_loc_types)

    world.completion_condition[player] = lambda state: state.has("Victory", player)
