from dataclasses import dataclass

from Options import Toggle, DeathLink, Range, Choice, PerGameCommonOptions



class IncludeMonsterTokens(Toggle):
    """Include Monster Tokens as AP Locations/Items"""
    display_name = "Include Socks"
    default = 1


class IncludeKeys(Toggle):
    """Include Keys as AP Locations/Items"""
    display_name = "Include Skills"
    default = 1

@dataclass
class BfBBOptions(PerGameCommonOptions):
    include_monster_tokens: IncludeMonsterTokens
    include_keys: IncludeKeys
    death_link: DeathLink
