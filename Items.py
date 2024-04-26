import typing
from BaseClasses import Item, ItemClassification
from .names import ItemNames


class ItemData(typing.NamedTuple):
    id: typing.Optional[int]
    classification: ItemClassification

    def is_progression(self):
        return self.classification & ItemClassification.progression == ItemClassification.progression

    def is_trap(self):
        return self.classification & ItemClassification.trap == ItemClassification.trap

    def is_filler(self):
        return self.classification & ItemClassification.filler == ItemClassification.filler


class NO100FItem(Item):
    game: str = "Night of 100 Frights"


base_id = 1495000

item_table = {
    #Upgrades
    ItemNames.GumPower         : ItemData(base_id + 0, ItemClassification.progression),
    ItemNames.SoapPower        : ItemData(base_id + 1, ItemClassification.progression),
    ItemNames.BootsPower       : ItemData(base_id + 2, ItemClassification.progression),
    ItemNames.PlungerPower     : ItemData(base_id + 3, ItemClassification.progression),
    ItemNames.SlipperPower     : ItemData(base_id + 4, ItemClassification.useful),
    ItemNames.LampshadePower   : ItemData(base_id + 5, ItemClassification.useful),
    ItemNames.BlackknightPower : ItemData(base_id + 6, ItemClassification.useful),
    ItemNames.SpringPower      : ItemData(base_id + 7, ItemClassification.progression),
    ItemNames.PoundPower       : ItemData(base_id + 8, ItemClassification.progression),
    ItemNames.HelmetPower      : ItemData(base_id + 9, ItemClassification.progression),
    ItemNames.UmbrellaPower    : ItemData(base_id + 10, ItemClassification.progression),
    ItemNames.ShovelPower      : ItemData(base_id + 11, ItemClassification.progression),
    ItemNames.ShockwavePower   : ItemData(base_id + 12, ItemClassification.useful),

    #Ammo Upgrades
    ItemNames.GumAmmoUpgrade   : ItemData(base_id + 13, ItemClassification.useful),
    ItemNames.SoapAmmoUpgrade  : ItemData(base_id + 14, ItemClassification.useful),

    #Monster Tokens
    ItemNames.MT_BLACKKNIGHT   : ItemData(base_id + 15, ItemClassification.filler),
    ItemNames.MT_MOODY         : ItemData(base_id + 16, ItemClassification.filler),
    ItemNames.MT_CAVEMAN       : ItemData(base_id + 17, ItemClassification.filler),
    ItemNames.MT_CREEPER       : ItemData(base_id + 18, ItemClassification.filler),
    ItemNames.MT_GARGOYLE      : ItemData(base_id + 19, ItemClassification.filler),
    ItemNames.MT_GERONIMO      : ItemData(base_id + 20, ItemClassification.filler),
    ItemNames.MT_GHOST         : ItemData(base_id + 21, ItemClassification.filler),
    ItemNames.MT_GHOSTDIVER    : ItemData(base_id + 22, ItemClassification.filler),
    ItemNames.MT_GREENGHOST    : ItemData(base_id + 23, ItemClassification.filler),
    ItemNames.MT_HEADLESS      : ItemData(base_id + 24, ItemClassification.filler),
    ItemNames.MT_MASTERMIND    : ItemData(base_id + 25, ItemClassification.filler),
    ItemNames.MT_ROBOT         : ItemData(base_id + 26, ItemClassification.filler),
    ItemNames.MT_REDBEARD      : ItemData(base_id + 27, ItemClassification.filler),
    ItemNames.MT_SCARECROW     : ItemData(base_id + 28, ItemClassification.filler),
    ItemNames.MT_SEACREATURE   : ItemData(base_id + 29, ItemClassification.filler),
    ItemNames.MT_SPACEKOOK     : ItemData(base_id + 30, ItemClassification.filler),
    ItemNames.MT_TARMONSTER    : ItemData(base_id + 31, ItemClassification.filler),
    ItemNames.MT_WITCH         : ItemData(base_id + 32, ItemClassification.filler),
    ItemNames.MT_WITCHDOC      : ItemData(base_id + 33, ItemClassification.filler),
    ItemNames.MT_WOLFMAN       : ItemData(base_id + 34, ItemClassification.filler),
    ItemNames.MT_ZOMBIE        : ItemData(base_id + 35, ItemClassification.filler),

    #Keys
    ItemNames.Clamor1_Key      : ItemData(base_id + 36, ItemClassification.progression),
    ItemNames.Hedge_Key        : ItemData(base_id + 37, ItemClassification.progression),
    ItemNames.Fishing_Key      : ItemData(base_id + 38, ItemClassification.progression),
    ItemNames.Cellar2_Key      : ItemData(base_id + 39, ItemClassification.progression),
    ItemNames.Cellar3_Key      : ItemData(base_id + 40, ItemClassification.progression),
    ItemNames.Cavein_Key       : ItemData(base_id + 41, ItemClassification.progression),
    ItemNames.FishyClues_Key   : ItemData(base_id + 42, ItemClassification.progression),
    ItemNames.Graveplot_Key    : ItemData(base_id + 43, ItemClassification.progression),
    ItemNames.Tomb1_Key        : ItemData(base_id + 44, ItemClassification.progression),
    ItemNames.Tomb3_Key        : ItemData(base_id + 45, ItemClassification.progression),
    ItemNames.Clamor4_Key      : ItemData(base_id + 46, ItemClassification.progression),
    ItemNames.MYM_Key          : ItemData(base_id + 47, ItemClassification.progression),
    ItemNames.Coast_Key        : ItemData(base_id + 48, ItemClassification.progression),
    ItemNames.Attic_Key        : ItemData(base_id + 49, ItemClassification.progression),
    ItemNames.Knight_Key       : ItemData(base_id + 50, ItemClassification.progression),
    ItemNames.Creepy2_Key      : ItemData(base_id + 51, ItemClassification.progression),
    ItemNames.Creepy3_Key      : ItemData(base_id + 52, ItemClassification.progression),
    ItemNames.Gusts1_Key       : ItemData(base_id + 53, ItemClassification.progression),
    ItemNames.Gusts2_Key       : ItemData(base_id + 54, ItemClassification.progression),
    ItemNames.DLD_Key          : ItemData(base_id + 55, ItemClassification.progression),
    ItemNames.Shiver_Key       : ItemData(base_id + 56, ItemClassification.progression),


    # events
    ItemNames.victory: ItemData(None, ItemClassification.progression)
}

lookup_id_to_name: typing.Dict[int, str] = {data.id: name for name, data in item_table.items() if data.id}
