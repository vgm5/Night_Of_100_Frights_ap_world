import typing
from BaseClasses import Location
from .names import LocationNames


class NO100FLocation(Location):
    game: str = "Night of 100 Frights"


base_id = 1490000

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

location_table: typing.Dict[str, typing.Optional[int]] = {
    **upgrade_location_table,      # 0 - 27
    **monstertoken_location_table, #100-120
    LocationNames.Credits: None
}

lookup_id_to_name: typing.Dict[int, str] = {_id: name for name, _id in location_table.items()}
