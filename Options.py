from dataclasses import dataclass

from Options import Toggle, DeathLink, Range, Choice, PerGameCommonOptions


class IncludeMonsterTokens(Toggle):
    """Include Monster Tokens as AP Locations/Items"""
    display_name = "Include Monster Tokens"
    default = 1


class IncludeKeys(Choice):
    """Include Keys as AP Locations/Items"""
    display_name = "Include Keys"
    option_vanilla = 0
    option_keys = 1
    option_keyrings = 2
    default = 0

class IncludeWarpGates(Toggle):
    """Include Warp Gates as AP Locations/Items
    Additionally, to offset issues with snack gates, you will start with 400 Scooby Snacks
    """
    display_name = "Include Warp Gates"
    default = 0

class IncludeSnacks(Toggle):
    """Include Snacks as AP Locations/Items (WIP)"""
    display_name = "Include Snacks"
    default = 0


class CompletionGoal(Choice):
    """
    Select which completion goal you want for this world:
    0 = Vanilla/Beat Mastermind
    1 = Bosses
    2 = Monster Tokens
    3 = Bosses/Tokens
    For Non-Vanilla options, Mastermind still needs to be defeated - you just can't fight him until the goal has been met
    """
    display_name = "Completion Goal"
    option_vanilla = 0
    option_bosses = 1
    option_tokens = 2
    option_both = 3
    default = 0

class BossesCount(Range):
    """Sets the number of bosses needed if Boss Completion Goal is being used"""
    display_name = "Boss Kills Count"
    range_start = 1
    range_end = 3
    default = 3

class MonsterTokensCount(Range):
    """Sets the number of tokens needed if Token Completion Goal is being used"""
    display_name = "Token Count"
    range_start = 1
    range_end = 21
    default = 21

class AdvancedLogic(Toggle):
    """Changes generation to expect certain tricks to be performed, intended for experienced players"""
    display_name = "Advanced Logic"
    default = 0

class ExpertLogic(Toggle):
    """Changes generation to expect certain tricks to be performed, intended for even MORE experienced players"""
    display_name = "Expert Logic"
    default = 0

class CreepyEarly(Toggle):
    """Changes generation to expect certain tricks to be performed (CREEPY EARLY [GCN]), intended for less sane players"""
    display_name = "Creepy Early"
    default = 0

class NoLogic(Toggle):
    """Disables all item Logic | USE AT YOUR OWN RISK"""
    display_name = "Disable Logic"
    default = 0

class Speedster(Toggle):
    """For Fun Setting, permanently makes scooby move at mach speed"""
    display_name = "Speedster"
    default = 0

@dataclass
class NO100FOptions(PerGameCommonOptions):
    include_monster_tokens: IncludeMonsterTokens
    include_keys: IncludeKeys
    include_warpgates: IncludeWarpGates
    include_snacks: IncludeSnacks
    death_link: DeathLink
    completion_goal: CompletionGoal
    boss_count: BossesCount
    token_count: MonsterTokensCount
    advanced_logic: AdvancedLogic
    expert_logic: ExpertLogic
    creepy_early: CreepyEarly
    no_logic: NoLogic
    speedster: Speedster