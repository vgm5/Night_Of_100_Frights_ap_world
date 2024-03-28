from dataclasses import dataclass

from Options import Toggle, DeathLink, Range, Choice, PerGameCommonOptions


class IncludeMonsterTokens(Toggle):
    """Include Monster Tokens as AP Locations/Items"""
    display_name = "Include Monster Tokens"
    default = 1


#class IncludeKeys(Toggle):
#    """Include Keys as AP Locations/Items(WIP)"""
#    display_name = "Include Keys"
#    default = 0


#class IncludeSnacks(Toggle):
#    """Include Snacks as AP Locations/Items (WIP)"""
#    display_name = "Include Snacks"
#    default = 0

class NoLogic(Toggle):
    """Disables all item Logic | USE AT YOUR OWN RISK"""
    display_name = "Disable Logic"
    default = 0

@dataclass
class NO100FOptions(PerGameCommonOptions):
    include_monster_tokens: IncludeMonsterTokens
 #   include_keys: IncludeKeys
  #  include_snacks: IncludeSnacks
    death_link: DeathLink
    no_logic: NoLogic
