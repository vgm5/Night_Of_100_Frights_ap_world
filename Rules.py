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
        # ConnectionNames.hub1_e001: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1), Moved outside Rule Factory
        # ConnectionNames.hub1_f001: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),

        # Manor
        ConnectionNames.i020_i021: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),
        ConnectionNames.i003_b004: lambda player: lambda state: state.has(ItemNames.SoapPower, player, 1),
        # ConnectionNames.i003_i004: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),
        ConnectionNames.i004_o001: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
        ConnectionNames.i006_r001: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1),

        # Rooftops

        # Balcony
        ConnectionNames.o001_o008: lambda player: lambda state: state.has(ItemNames.BootsPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

        # Hedge
        ConnectionNames.e009_c001: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),

        # Fishing Village
        ConnectionNames.f003_f004: lambda player: lambda state: state.has(ItemNames.BootsPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
        ConnectionNames.f003_p001: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),
        ConnectionNames.f009_f008: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1) and state.has(ItemNames.BootsPower, player, 1) and state.has(ItemNames.PoundPower, player, 1),

        # Coast
        ConnectionNames.c001_c002: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),
        ConnectionNames.c007_g001: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),
        # ConnectionNames.c005_c006: lambda player: lambda state: state.has(ItemNames.PlungerPower, player, 1),

        # Passage
        ConnectionNames.p001_p002: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),
        # ConnectionNames.p002_p003: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PoundPower, player, 1),
        # ConnectionNames.p004_p005: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PlungerPower, player, 1),
        # ConnectionNames.p005_b001: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
        # ConnectionNames.p002_s001: lambda player: lambda state: state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.SpringPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PoundPower, player, 1),
        # ConnectionNames.p003_p004: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

        # Secret Lab
        ConnectionNames.s001_s002: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.PoundPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

        # Basement
        ConnectionNames.b001_b002: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1) or state.has(ItemNames.SoapPower, player, 1),

        # Lighthouse
        ConnectionNames.l017_l018: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1),
        ConnectionNames.l015_l017: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1),
        ConnectionNames.l015_w020: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
        ConnectionNames.l015_l014: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1),

        # Wrecked Ships
        ConnectionNames.w020_w021: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
        ConnectionNames.w025_w026: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1)
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
            LocationNames.soapammo_f001: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1) and state.has(ItemNames.UmbrellaPower, player, 1) or (state.has(ItemNames.SpringPower, player, 1) and (state.has(ItemNames.GumPower, player, 1) or state.has(ItemNames.SoapPower, player, 1))),
            # Coast
            LocationNames.gumammo_c003: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1) or (state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1)),

            # Passage

            # Secret Lab

            # Basement

            # Graveyard
            LocationNames.soapammo_g003: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1),

            # Lighthouse
            LocationNames.soapammo_l019: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1) and state.has(ItemNames.UmbrellaPower, player, 1) and (state.has(ItemNames.SoapPower, player, 1) or state.has(ItemNames.GumPower, player, 1)),
            LocationNames.gumammo_l011: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1) and (state.has(ItemNames.PlungerPower, player, 1) or state.has(ItemNames.SoapPower, player, 1) or state.has(ItemNames.GumPower, player, 1)),
            LocationNames.pound_l017: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1)
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
            LocationNames.witch_token_e003: lambda player: lambda state: state.has(ItemNames.BootsPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

            # Fishing Village
            LocationNames.tarmonster_token_f004: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1),
            LocationNames.ghostdiver_token_f007: lambda player: lambda state: state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

            # Coast
            LocationNames.greenghost_token_c005: lambda player: lambda state: state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

            # Passage

            # Secret Lab

            # Basement
            # LocationNames.spacekook_token_b001: lambda player: lambda state: state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1),

            # Lighthouse
            LocationNames.seacreature_token_l014: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1) or state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
            LocationNames.caveman_token_l013: lambda player: lambda state: state.has(ItemNames.PoundPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

            # Wrecked Ships
            LocationNames.moody_token_w022: lambda player: lambda state: state.has(ItemNames.GumPower, player, 1) or state.has(ItemNames.SoapPower, player, 1),
            LocationNames.redbeard_token_w025: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) and (state.has(ItemNames.GumPower, player, 1) or state.has(ItemNames.SoapPower, player, 1)),
        },

        ItemNames.Keys:
            {
                # Hub
                LocationNames.hedgekey_h001: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1),
                LocationNames.fishingkey_h001: lambda player: lambda state: state.has(ItemNames.ShovelPower, player, 1),

                # Lighthouse
                LocationNames.key1_l011: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) or state.has(ItemNames.PoundPower, player, 1),
                LocationNames.key2_l011: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) or state.has(ItemNames.PoundPower, player, 1),
                LocationNames.key3_l011: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) or state.has(ItemNames.PoundPower, player, 1),
                LocationNames.key4_l011: lambda player: lambda state: state.has(ItemNames.HelmetPower, player, 1) or state.has(ItemNames.PoundPower, player, 1),

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

key_rules = [
# connections
    {
        # Hub
        ConnectionNames.hub1_e001: lambda player: lambda state: state.has(ItemNames.Hedge_Key, player, 1),
        ConnectionNames.hub1_f001: lambda player: lambda state: state.has(ItemNames.Fishing_Key, player, 1),

        # Manor
        ConnectionNames.i001_i020: lambda player: lambda state: state.has(ItemNames.Clamor1_Key, player, 1),
        ConnectionNames.i003_i004: lambda player: lambda state: state.has(ItemNames.Clamor4_Key, player, 1) and state.has(ItemNames.HelmetPower, player, 1),
        ConnectionNames.i005_i006: lambda player: lambda state: state.has(ItemNames.MYM_Key, player, 4),

        # Hedge
        ConnectionNames.e002_e003: lambda player: lambda state: state.has(ItemNames.SpringPower, player, 1),

        # Rooftop
        ConnectionNames.r005_o001: lambda player: lambda state: state.has(ItemNames.DLD_Key, player, 3),

        # Balcony
        ConnectionNames.o003_o004: lambda player: lambda state: state.has(ItemNames.Attic_Key, player, 3),
        ConnectionNames.o006_o008: lambda player: lambda state: state.has(ItemNames.Knight_Key, player, 4),
        ConnectionNames.o008_o006: lambda player: lambda state: state.has(ItemNames.Knight_Key, player, 4),

        # Fishing Village
        ConnectionNames.f005_f006: lambda player: lambda state: state.has(ItemNames.FishyClues_Key, player, 4),

        # Coast
        ConnectionNames.c005_c006: lambda player: lambda state: state.has(ItemNames.Cavein_Key, player, 4) and state.has(ItemNames.PlungerPower, player, 1),

        # Passage
        ConnectionNames.p002_s001: lambda player: lambda state: state.has(ItemNames.Creepy2_Key, player, 5) and state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.SpringPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PoundPower, player, 1),
        ConnectionNames.p002_p003: lambda player: lambda state: state.has(ItemNames.Creepy2_Key, player, 5) and state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PoundPower, player, 1),
        ConnectionNames.p003_p004: lambda player: lambda state: state.has(ItemNames.Creepy3_Key, player, 3) and state.has(ItemNames.GumPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),
        ConnectionNames.p004_p005: lambda player: lambda state: state.has(ItemNames.Gusts1_Key, player, 1) and state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PlungerPower, player, 1),
        ConnectionNames.p005_b001: lambda player: lambda state: state.has(ItemNames.Gusts2_Key, player, 4) and state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1),

        # Graveyard
        ConnectionNames.g001_g002: lambda player: lambda state: state.has(ItemNames.Graveplot_Key, player, 3),
        ConnectionNames.g007_g008: lambda player: lambda state: state.has(ItemNames.Tomb1_Key, player, 1),

        # Basement
        ConnectionNames.b002_b003: lambda player: lambda state: state.has(ItemNames.Cellar2_Key, player, 3),
        ConnectionNames.b003_b004: lambda player: lambda state: state.has(ItemNames.Cellar3_Key, player, 4),

        # Lighthouse
        ConnectionNames.l011_l013: lambda player: lambda state: state.has(ItemNames.Coast_Key, player, 4),

        # Wrecked Ships
        ConnectionNames.w027_w028: lambda player: lambda state: state.has(ItemNames.Shiver_Key, player, 4),
    },
    # locations
    {
        ItemNames.Upgrades:
            {
                # Graveyard
                LocationNames.umbrella_g009: lambda player: lambda state: state.has(ItemNames.Tomb3_Key, player, 2),

                # Balcony
                LocationNames.gumammo_o001: lambda player: lambda state: state.has(ItemNames.BootsPower, player, 1) or (state.has(ItemNames.Attic_Key, player, 3) and state.has(ItemNames.Knight_Key, player, 4)),
            },
        ItemNames.MonsterTokens:
            {
                # Manor
                LocationNames.geronimo_token_i005: lambda player: lambda state: state.has(ItemNames.MYM_Key, player, 4) or (state.has(ItemNames.SpringPower, player, 1) and state.has(ItemNames.UmbrellaPower, player, 1)),

                # Balcony
                LocationNames.blackknight_token_o001: lambda player: lambda state: state.has(ItemNames.BootsPower, player, 1) or (state.has(ItemNames.Attic_Key, player, 3) and state.has(ItemNames.Knight_Key, player, 4)),

                # Basement
                LocationNames.spacekook_token_b001: lambda player: lambda state: state.has(ItemNames.Cellar2_Key, player, 3) and state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1),
            },
        ItemNames.Keys:
            {
                # Passage
                LocationNames.key5_p002: lambda player: lambda state: state.has(ItemNames.Creepy2_Key, player, 4) and state.has(ItemNames.HelmetPower, player, 1),
            },
     }
]

def _add_rules(multiworld: MultiWorld, player: int, rules: List, allowed_loc_types: List[str]):
    for name, rule_factory in rules[0].items():
        if type(rule_factory) == tuple and len(rule_factory) > 1 and rule_factory[1]:  # force override
            rule_factory = rule_factory[0]
            set_rule(multiworld.get_entrance(name, player), rule_factory(player))
        else:
            add_rule(multiworld.get_entrance(name, player), rule_factory(player))
    for loc_type, type_rules in rules[1].items():
        if loc_type not in allowed_loc_types:
            continue
        for name, rule_factory in type_rules.items():
            if type(rule_factory) == tuple and len(rule_factory) > 1 and rule_factory[1]:  # force override
                rule_factory = rule_factory[0]
                set_rule(multiworld.get_location(name, player), rule_factory(player))
            else:
                add_rule(multiworld.get_location(name, player), rule_factory(player))


def _set_rules(multiworld: MultiWorld, player: int, rules: List, allowed_loc_types: List[str]):
    for name, rule_factory in rules[0].items():
        set_rule(multiworld.get_entrance(name, player), rule_factory(player))
    for loc_type, type_rules in rules[1].items():
        if loc_type not in allowed_loc_types:
            continue
        for name, rule_factory in type_rules.items():
            set_rule(multiworld.get_location(name, player), rule_factory(player))


def set_rules(multiworld: MultiWorld, options: NO100FOptions, player: int):
    allowed_loc_types = [ItemNames.Upgrades,ItemNames.victory]
    if options.include_monster_tokens.value:
        allowed_loc_types += [ItemNames.MonsterTokens]
    if options.include_keys.value:
        allowed_loc_types += [ItemNames.Keys]

    _add_rules(multiworld, player, upgrade_rules, allowed_loc_types)
    if options.include_monster_tokens.value:
        _add_rules(multiworld, player, monster_token_rules, allowed_loc_types)
    if options.include_keys.value:
        _add_rules(multiworld, player, key_rules, allowed_loc_types)
    if ItemNames.Keys not in allowed_loc_types:
        if ItemNames.MonsterTokens in allowed_loc_types:
            add_rule(multiworld.get_location(LocationNames.spacekook_token_b001, player), lambda state: state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1))
        add_rule(multiworld.get_entrance(ConnectionNames.hub1_e001, player), lambda state: state.has(ItemNames.SpringPower, player, 1))
        add_rule(multiworld.get_entrance(ConnectionNames.hub1_f001, player), lambda state: state.has(ItemNames.ShovelPower, player, 1))
        add_rule(multiworld.get_entrance(ConnectionNames.i003_i004, player), lambda state: state.has(ItemNames.HelmetPower, player, 1))
        add_rule(multiworld.get_entrance(ConnectionNames.c005_c006, player), lambda state: state.has(ItemNames.PlungerPower, player, 1))
        add_rule(multiworld.get_entrance(ConnectionNames.p002_p003, player), lambda state: state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PoundPower, player, 1))
        add_rule(multiworld.get_entrance(ConnectionNames.p003_p004, player), lambda state: state.has(ItemNames.GumPower, player, 1) and state.has(ItemNames.SpringPower, player, 1))
        add_rule(multiworld.get_entrance(ConnectionNames.p004_p005, player), lambda state: state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PlungerPower, player, 1))
        add_rule(multiworld.get_entrance(ConnectionNames.p005_b001, player), lambda state: state.has(ItemNames.UmbrellaPower, player, 1) and state.has(ItemNames.SpringPower, player, 1))
        add_rule(multiworld.get_entrance(ConnectionNames.p002_s001, player), lambda state: state.has(ItemNames.SoapPower, player, 1) and state.has(ItemNames.SpringPower, player, 1) and state.has(ItemNames.HelmetPower, player, 1) and state.has(ItemNames.PoundPower, player, 1)),

    multiworld.completion_condition[player] = lambda state: state.has("Victory", player)
