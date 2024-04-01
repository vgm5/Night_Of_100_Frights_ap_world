import typing
from BaseClasses import Location
from .names import LocationNames


class NO100FLocation(Location):
    game: str = "Night of 100 Frights"


base_id = 1495000

upgrade_location_table = {
    LocationNames.gumpower_w028: base_id + 0,
    LocationNames.soappower_b004: base_id + 1,
    LocationNames.boots_o008: base_id + 2,
    LocationNames.plunger_p003: base_id + 3,
    LocationNames.slippers_e002: base_id + 4,
    LocationNames.lampshade_e002: base_id + 5,
    LocationNames.blackknight_power_r004: base_id + 6,
    LocationNames.spring_f010: base_id + 7,
    LocationNames.pound_l017: base_id + 8,
    LocationNames.helmetpower_e009: base_id + 9,
    LocationNames.umbrella_g009: base_id + 10,
    LocationNames.shovel_h001: base_id + 11,
    LocationNames.shockwave_c007: base_id + 12,

    #Gum Ammo
    LocationNames.gumammo_c003: base_id + 13,
    LocationNames.gumammo_l011: base_id + 14,
    LocationNames.gumammo_f003: base_id + 15,
    LocationNames.gumammo_s005: base_id + 16,
    LocationNames.gumammo_o001: base_id + 17,
    LocationNames.gumammo_g006: base_id + 18,
    LocationNames.gumammo_r020: base_id + 19,

    #Soap Ammo
    LocationNames.soapammo_e007: base_id + 20,
    LocationNames.soapammo_g003: base_id + 21,
    LocationNames.soapammo_r005: base_id + 22,
    LocationNames.soapammo_r021: base_id + 23,
    LocationNames.soapammo_l019: base_id + 24,
    LocationNames.soapammo_s005: base_id + 25,
    LocationNames.soapammo_w023: base_id + 26,
    LocationNames.soapammo_f001: base_id + 27,
}

monstertoken_location_table = {
    LocationNames.blackknight_token_o001: base_id + 100 + 0,
    LocationNames.moody_token_w022: base_id + 100 + 1,
    LocationNames.caveman_token_l013: base_id + 100 + 2,
    LocationNames.creeper_token_o002: base_id + 100 + 3,
    LocationNames.gargoyle_token_h002: base_id + 100 + 4,
    LocationNames.geronimo_token_i005: base_id + 100 + 5,
    LocationNames.ghost_token_g005: base_id + 100 + 6,
    LocationNames.ghostdiver_token_f007: base_id + 100 + 7,
    LocationNames.greenghost_token_c005: base_id + 100 + 8,
    LocationNames.headless_token_i001: base_id + 100 + 9,
    LocationNames.mastermind_token_s003: base_id + 100 + 10,
    LocationNames.robot_token_s002: base_id + 100 + 11,
    LocationNames.redbeard_token_w025: base_id + 100 + 12,
    LocationNames.scarecrow_token_g008: base_id + 100 + 13,
    LocationNames.seacreature_token_l014: base_id + 100 + 14,
    LocationNames.spacekook_token_b001: base_id + 100 + 15,
    LocationNames.tarmonster_token_f004: base_id + 100 + 16,
    LocationNames.witch_token_e003: base_id + 100 + 17,
    LocationNames.witchdoctor_token_r020: base_id + 100 + 18,
    LocationNames.wolfman_token_e001: base_id + 100 + 19,
    LocationNames.zombie_token_g002: base_id + 100 + 20,
}

key_location_table = {
    LocationNames.key1_b002: base_id + 200 + 0,
    LocationNames.key2_b002: base_id + 200 + 1,
    LocationNames.key3_b002: base_id + 200 + 2,

    LocationNames.key1_b003: base_id + 200 + 3,
    LocationNames.key2_b003: base_id + 200 + 4,
    LocationNames.key3_b003: base_id + 200 + 5,
    LocationNames.key4_b003: base_id + 200 + 6,

    LocationNames.key1_c005: base_id + 200 + 7,
    LocationNames.key2_c005: base_id + 200 + 8,
    LocationNames.key3_c005: base_id + 200 + 9,
    LocationNames.key4_c005: base_id + 200 + 10,

    LocationNames.key1_f005: base_id + 200 + 11,
    LocationNames.key2_f005: base_id + 200 + 12,
    LocationNames.key3_f005: base_id + 200 + 13,
    LocationNames.key4_f005: base_id + 200 + 14,

    LocationNames.key1_g001: base_id + 200 + 15,
    LocationNames.key2_g001: base_id + 200 + 16,
    LocationNames.key3_g001: base_id + 200 + 17,

    LocationNames.key_g007: base_id + 200 + 18,

    LocationNames.key1_g009: base_id + 200 + 19,
    LocationNames.key2_g009: base_id + 200 + 20,

    LocationNames.hedgekey_h001: base_id + 200 + 21,
    LocationNames.fishingkey_h001: base_id + 200 + 22,

    LocationNames.key_i001: base_id + 200 + 23,

    LocationNames.key_i003: base_id + 200 + 24,

    LocationNames.key1_i005: base_id + 200 + 25,
    LocationNames.key2_i005: base_id + 200 + 26,
    LocationNames.key3_i005: base_id + 200 + 27,
    LocationNames.key4_i005: base_id + 200 + 28,

    LocationNames.key1_l011: base_id + 200 + 29,
    LocationNames.key2_l011: base_id + 200 + 30,
    LocationNames.key3_l011: base_id + 200 + 31,
    LocationNames.key4_l011: base_id + 200 + 32,

    LocationNames.key1_o003: base_id + 200 + 33,
    LocationNames.key2_o003: base_id + 200 + 34,
    LocationNames.key3_o003: base_id + 200 + 35,

    LocationNames.key1_o006: base_id + 200 + 36,
    LocationNames.key2_o006: base_id + 200 + 37,
    LocationNames.key3_o006: base_id + 200 + 38,
    LocationNames.key4_o006: base_id + 200 + 39,

    LocationNames.key1_p002: base_id + 200 + 40,
    LocationNames.key2_p002: base_id + 200 + 41,
    LocationNames.key3_p002: base_id + 200 + 42,
    LocationNames.key4_p002: base_id + 200 + 43,
    LocationNames.key5_p002: base_id + 200 + 44,

    LocationNames.key1_p003: base_id + 200 + 45,
    LocationNames.key2_p003: base_id + 200 + 46,
    LocationNames.key3_p003: base_id + 200 + 47,

    LocationNames.key_p004: base_id + 200 + 48,

    LocationNames.key1_p005: base_id + 200 + 49,
    LocationNames.key2_p005: base_id + 200 + 50,
    LocationNames.key3_p005: base_id + 200 + 51,
    LocationNames.key4_p005: base_id + 200 + 52,

    LocationNames.key1_r005: base_id + 200 + 53,
    LocationNames.key2_r005: base_id + 200 + 54,
    LocationNames.key3_r005: base_id + 200 + 55,

    LocationNames.key1_w027: base_id + 200 + 56,
    LocationNames.key2_w027: base_id + 200 + 57,
    LocationNames.key3_w027: base_id + 200 + 58,
}

location_table: typing.Dict[str, typing.Optional[int]] = {
    **upgrade_location_table,      # 0 - 27
    **monstertoken_location_table, # 100 - 120
    **key_location_table,          # 200 - 258
    LocationNames.Credits: None
}

lookup_id_to_name: typing.Dict[int, str] = {_id: name for name, _id in location_table.items()}
