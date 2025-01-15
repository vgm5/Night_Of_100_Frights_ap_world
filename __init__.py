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
    print('running Scooby-Doo! NO100F client')
    from worlds.no100f.NO100FClient import main  # lazy import
    file_types = (('NO100F Patch File', ('.apno100f',)), ('NGC iso', ('.gcm',)),)
    kwargs = {'patch_file': Utils.open_filename("Select .apno100f", file_types)}
    p = Process(target=main, kwargs=kwargs)
    p.start()


components.append(Component("Scooby-Doo! NO100F Client", func=run_client, component_type=Type.CLIENT,
                            file_identifier=SuffixIdentifier('.apno100f')))


class NO100FWeb(WebWorld):
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up the integration for Archipelago multiworld games.",
        "English",
        "setup_en.md",
        "setup/en",
        ["vgm5"]
    )]



class NightOf100FrightsWorld(World):
    """
    Scooby-Doo! Night of 100 Frights
    """
    game = "Scooby-Doo! Night of 100 Frights"
    options_dataclass = NO100FOptions
    options: NO100FOptions
    topology_present = False

    item_name_to_id = {name: data.id for name, data in item_table.items()}
    location_name_to_id = location_table
    web = NO100FWeb()

    def __init__(self, multiworld: "MultiWorld", player: int):
        super().__init__(multiworld, player)
        self.snack_counter: int = 0

    def get_items(self):
        # Generate item pool
        itempool = [ItemNames.GumPower, ItemNames.SoapPower, ItemNames.PoundPower, ItemNames.HelmetPower,
                    ItemNames.ShockwavePower, ItemNames.BootsPower, ItemNames.PlungerPower, ItemNames.ShovelPower]
        itempool += [ItemNames.ProgressiveJump] * 2
        itempool += [ItemNames.ProgressiveSneak] * 3
        itempool += [ItemNames.SoapAmmoUpgrade] * 8
        itempool += [ItemNames.GumAmmoUpgrade] * 7
        if self.options.include_snacks:
            itempool += [ItemNames.Snack] * 4993
            itempool += [ItemNames.SnackBox] * 350
        if self.options.include_monster_tokens:
            itempool += [ItemNames.MT_PROGRESSIVE] * 21
        if self.options.include_keys == 1:
            itempool += [ItemNames.Hedge_Key, ItemNames.Fishing_Key, ItemNames.Clamor1_Key, ItemNames.Clamor4_Key,
                         ItemNames.Gusts1_Key, ItemNames.Tomb1_Key]  # Single Keys
            itempool += [ItemNames.Tomb3_Key] * 2  # Double Keys
            itempool += [ItemNames.Cellar2_Key, ItemNames.Graveplot_Key, ItemNames.Attic_Key, ItemNames.Creepy3_Key,
                         ItemNames.DLD_Key] * 3  # Triple Keys
            itempool += [ItemNames.Cellar3_Key, ItemNames.Cavein_Key, ItemNames.FishyClues_Key, ItemNames.MYM_Key,
                         ItemNames.Coast_Key, ItemNames.Knight_Key, ItemNames.Gusts2_Key, ItemNames.Shiver_Key] * 4  # Quad Keys
            itempool += [ItemNames.Creepy2_Key] * 5  # Penta Keys
        if self.options.include_keys == 2:
            itempool+=[ItemNames.Hedge_Key, ItemNames.Fishing_Key, ItemNames.Clamor1_Key, ItemNames.Clamor4_Key,
                         ItemNames.Gusts1_KeyRing, ItemNames.Tomb1_KeyRing, ItemNames.Tomb3_KeyRing, ItemNames.Cellar2_KeyRing,
                         ItemNames.Graveplot_KeyRing, ItemNames.Attic_KeyRing, ItemNames.Creepy3_KeyRing,
                         ItemNames.DLD_KeyRing, ItemNames.Cellar3_KeyRing, ItemNames.Cavein_KeyRing, ItemNames.FishyClues_KeyRing, ItemNames.MYM_KeyRing,
                         ItemNames.Coast_KeyRing, ItemNames.Knight_KeyRing, ItemNames.Gusts2_KeyRing, ItemNames.Shiver_KeyRing, ItemNames.Creepy2_KeyRing]
            itempool += [ItemNames.FillerSnack] * 39
        if self.options.include_warpgates:
            itempool += [ItemNames.Cellar4_Warp, ItemNames.Cliff4_Warp, ItemNames.Hedge4_Warp, ItemNames.Hedge6_Warp,
                         ItemNames.Hedge9_Warp, ItemNames.Fish3_Warp, ItemNames.Fish7_Warp, ItemNames.Balc1_Warp,
                         ItemNames.Balc4_Warp, ItemNames.Balc6_Warp, ItemNames.Grave1_Warp, ItemNames.Grave5_Warp,
                         ItemNames.Grave8_Warp, ItemNames.Manor3_Warp, ItemNames.Manor6_Warp, ItemNames.LH14_Warp,
                         ItemNames.LH15_Warp, ItemNames.LH18_Warp, ItemNames.SP3_Warp, ItemNames.SP5_Warp,
                         ItemNames.Roof3_Warp, ItemNames.SL2_Warp, ItemNames.Wreck22_Warp, ItemNames.Wreck26_Warp,
                         ItemNames.MG_Warp]

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
            "include_warpgates": self.options.include_warpgates.value,
            "include_snacks": self.options.include_snacks.value,
            "completion_goal": self.options.completion_goal.value,
            "boss_count": self.options.boss_count.value,
            "token_count": self.options.token_count.value,
            "advanced_logic": self.options.advanced_logic.value,
            "expert_logic": self.options.expert_logic.value,
            "creepy_early": self.options.creepy_early.value,
            "no_logic": self.options.no_logic.value,
            "speedster": self.options.speedster.value,
        }

    def create_item(self, name: str,) -> Item:
        item_data = item_table[name]
        classification = item_data.classification

        if name == ItemNames.Snack:
            self.snack_counter += 1
            if self.snack_counter > 850:
                classification = ItemClassification.filler

        if name == ItemNames.SnackBox:
            self.snack_counter += 5
            if self.snack_counter > 850:
                classification = ItemClassification.filler

        item = NO100FItem(name, classification, item_data.id, self.player)

        return item

    def write_spoiler(self, spoiler_handle: TextIO) -> None:
        return

    def generate_output(self, output_directory: str) -> None:
        patch = NO100FDeltaPatch(path=os.path.join(output_directory,
                                                 f"{self.multiworld.get_out_file_name_base(self.player)}{NO100FDeltaPatch.patch_file_ending}"),
                               player=self.player,
                               player_name=self.multiworld.get_player_name(self.player),
                               include_snacks=bool(self.options.include_snacks),
                               include_keys=bool(self.options.include_keys.value),
                               include_monster_tokens=bool(self.options.include_monster_tokens.value),
                               include_warpgates=bool(self.options.include_warpgates.value),
                               completion_goal=bool(self.options.completion_goal.value),
                               seed=self.multiworld.seed_name.encode('utf-8'),
                               )
        patch.write()
