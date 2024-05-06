from dataclasses import dataclass

from Options import Toggle, DeathLink, Range, Choice, PerGameCommonOptions


class IncludeMonsterTokens(Toggle):
    """Include Monster Tokens as AP Locations/Items"""
    display_name = "Include Monster Tokens"
    default = 1


class IncludeKeys(Toggle):
    """Include Keys as AP Locations/Items"""
    display_name = "Include Keys"
    default = 0

class IncludeWarpGates(Toggle):
    """Include Warp Gates as AP Locations/Items"""
    display_name = "Include Warp Gates"
    default = 0

#class IncludeSnacks(Toggle):
#    """Include Snacks as AP Locations/Items (WIP)"""
#    display_name = "Include Snacks"
#    default = 0

class ApplyQOL(Toggle):
    """Applies various QOL fixes to the game"""
    display_name = "Apply QOL Fixes"
    default = 1

class CompletionGoal(Choice):
    """
    Select which completion goal you want for this world:
    0 = Vanilla/Beat Mastermind
    1 = All Bosses
    2 = All Monster Tokens

    For Non-Vanilla options, Mastermind still needs to be defeated - just you can't fight him until the other goal has been met
    """
    display_name = "Completion Goal"
    option_vanilla = 0
    option_bosses = 1
    option_alltokens = 2
    default = 0

class NoLogic(Toggle):
    """Disables all item Logic | USE AT YOUR OWN RISK"""
    display_name = "Disable Logic"
    default = 0

@dataclass
class NO100FOptions(PerGameCommonOptions):
    include_monster_tokens: IncludeMonsterTokens
    include_keys: IncludeKeys
    include_warpgates: IncludeWarpGates
    #  include_snacks: IncludeSnacks
    death_link: DeathLink
    apply_qol_fixes: ApplyQOL
    completion_goal: CompletionGoal
    no_logic: NoLogic
