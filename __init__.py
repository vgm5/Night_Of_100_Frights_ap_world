import os
import typing
from multiprocessing import Process
from typing import TextIO

import Utils
from BaseClasses import Item, Tutorial, ItemClassification
from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import Component, components, Type, SuffixIdentifier
from .Events import create_events
from .Items import item_table, NO100FItem
from .Locations import location_table, NO100FLocation
from .Options import NO100FOptions
from .Regions import create_regions
from .Rom import NO100FDeltaPatch
from .Rules import set_rules
from .names import ItemNames, ConnectionNames


def run_client():
    print('running NO100F client')
    from worlds.no100f.NO100FClient import main  # lazy import
    file_types = (('NO100F Patch File', ('.apno100f',)), ('NGC iso', ('.gcm',)),)
    kwargs = {'patch_file': Utils.open_filename("Select .apno100f", file_types)}
    p = Process(target=main, kwargs=kwargs)
    p.start()


components.append(Component("NO100F Client", func=run_client, component_type=Type.CLIENT,
                            file_identifier=SuffixIdentifier('.apno100f')))


class NO100FWeb(WebWorld):
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up the The Binding Of Isaac Repentance integration for Archipelago multiworld games.",
        "English",
        "setup_en.md",
        "setup/en",
        ["vgm5"]
    )]



class NightOf100FrightsWorld(World):
    """
    Scooby Doo: Night of 100 Frights
    """
    game = "Night of 100 Frights"
    options_dataclass = NO100FOptions
    options: NO100FOptions
    topology_present = False

    item_name_to_id = {name: data.id for name, data in item_table.items()}
    location_name_to_id = location_table
    web = NO100FWeb()

    def __init__(self, multiworld: "MultiWorld", player: int):
        super().__init__(multiworld, player)
        #self.snack_counter: int = 0

    def get_items(self):
        # Generate item pool
        itempool = [ItemNames.GumPower, ItemNames.SoapPower, ItemNames.SpringPower, ItemNames.PoundPower, ItemNames.HelmetPower, ItemNames.UmbrellaPower, ItemNames.ShockwavePower,
                    ItemNames.BootsPower, ItemNames.PlungerPower,ItemNames.SlipperPower, ItemNames.LampshadePower, ItemNames.BlackknightPower, ItemNames.ShovelPower]
        itempool += [ItemNames.SoapAmmoUpgrade] * 8
        itempool += [ItemNames.GumAmmoUpgrade] * 7
       # if self.options.include_snacks:
       #     itempool += [ItemNames.Snack] * way too much
       #     itempool += [ItemNames.SnackBox] * also alot
        if self.options.include_monster_tokens:
            itempool += [ItemNames.MT_BLACKKNIGHT, ItemNames.MT_MOODY, ItemNames.MT_CAVEMAN, ItemNames.MT_CREEPER, ItemNames.MT_GARGOYLE, ItemNames.MT_GERONIMO, ItemNames.MT_GHOST,
                         ItemNames.MT_GHOSTDIVER, ItemNames.MT_GREENGHOST, ItemNames.MT_HEADLESS, ItemNames.MT_MASTERMIND, ItemNames.MT_ROBOT, ItemNames.MT_REDBEARD, ItemNames.MT_SCARECROW,
                         ItemNames.MT_SEACREATURE, ItemNames.MT_SPACEKOOK, ItemNames.MT_TARMONSTER, ItemNames.MT_WITCH, ItemNames.MT_WITCHDOC, ItemNames.MT_WOLFMAN, ItemNames.MT_ZOMBIE]
        if self.options.include_keys:
            itempool += [ItemNames.Hedge_Key, ItemNames.Fishing_Key, ItemNames.Clamor1_Key, ItemNames.Clamor4_Key,  ItemNames.Gusts1_Key, ItemNames.Tomb1_Key]  # Single Keys
            itempool += [ItemNames.Tomb3_Key] * 2  # Double Keys
            itempool += [ItemNames.Cellar2_Key, ItemNames.Graveplot_Key, ItemNames.Attic_Key, ItemNames.Creepy3_Key, ItemNames.DLD_Key] * 3  # Triple Keys
            itempool += [ItemNames.Cellar3_Key, ItemNames.Cavein_Key, ItemNames.FishyClues_Key, ItemNames.MYM_Key, ItemNames.Coast_Key, ItemNames.Knight_Key, ItemNames.Gusts2_Key, ItemNames.Shiver_Key] * 4  # Quad Keys
            itempool += [ItemNames.Creepy2_Key] * 5  # Penta Keys

        # adjust for starting inv prog. items
        k = 0
        for item in self.multiworld.precollected_items[self.player]:
            if item.name in itempool and item.advancement:
                itempool.remove(item.name)
                k = k + 1

        # Convert itempool into real items
        itempool = list(map(lambda name: self.create_item(name), itempool))
        return itempool

    def create_items(self):
        self.multiworld.itempool += self.get_items()

    def set_rules(self):
        create_events(self.multiworld, self.player)
        if(self.options.no_logic == 0):
            set_rules(self.multiworld, self.options, self.player)

    def create_regions(self):
        create_regions(self.multiworld, self.options, self.player)

    def fill_slot_data(self):
        return {
            "death_link": self.options.death_link.value,
            "include_monster_tokens": self.options.include_monster_tokens.value,
            "include_keys": self.options.include_keys.value,
            #"include_snacks": self.options.include_snacks.value,
            "no_logic": self.options.no_logic.value,
        }

    def create_item(self, name: str,) -> Item:
        item_data = item_table[name]
        classification = item_data.classification

        #if name == ItemNames.snack:
            #self.snack_counter += 1
            #if self.snack_counter > required number for all SnackGates:
            #    classification = ItemClassification.progression_skip_balancing

        item = NO100FItem(name, classification, item_data.id, self.player)

        return item

    def write_spoiler(self, spoiler_handle: TextIO) -> None:
        return

    def generate_output(self, output_directory: str) -> None:
        patch = NO100FDeltaPatch(path=os.path.join(output_directory,
                                                 f"{self.multiworld.get_out_file_name_base(self.player)}{NO100FDeltaPatch.patch_file_ending}"),
                               player=self.player,
                               player_name=self.multiworld.get_player_name(self.player),
                               #include_snacks=bool(self.options.include_snacks),
                               include_keys=bool(self.options.include_keys.value),
                               include_monster_tokens=bool(self.options.include_monster_tokens.value),
                               seed=self.multiworld.seed_name.encode('utf-8'),
                               )
        patch.write()
