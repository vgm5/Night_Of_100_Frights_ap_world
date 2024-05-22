import asyncio
import collections
import os.path
import shutil
import subprocess
import time
import traceback
import zipfile
from enum import Enum
from enum import Flag
from queue import SimpleQueue
from typing import Callable, Optional, Any, Dict, Tuple

from .inc.packages import dolphin_memory_engine

import Utils
from CommonClient import CommonContext, server_loop, gui_enabled, ClientCommandProcessor, logger, \
    get_base_parser
from .Rom import NO100FDeltaPatch


class CheckTypes(Flag):
    UPGRADES = 1
    MONSTERTOKENS = 2
    KEYS = 3
    SNACKS = 4
    WARPGATES = 5


CONNECTION_REFUSED_GAME_STATUS = "Dolphin Connection refused due to invalid Game. Please load the US Version of NO100F."
CONNECTION_REFUSED_SAVE_STATUS = "Dolphin Connection refused due to invalid Save. " \
                                 "Please make sure you loaded a save file used on this slot and seed."
CONNECTION_LOST_STATUS = "Dolphin Connection was lost. Please restart your emulator and make sure NO100F is running."
CONNECTION_CONNECTED_STATUS = "Dolphin Connected"
CONNECTION_INITIAL_STATUS = "Dolphin Connection has not been initiated"

SCENE_OBJ_LIST_PTR_ADDR = 0x8025f0e0
SCENE_OBJ_LIST_SIZE_ADDR = 0x8025e5ac

CUR_SCENE_ADDR = 0x8025f0d0

HEALTH_ADDR = 0x80234DC8
SNACK_COUNT_ADDR = 0x80235094  #4 Bytes
UPGRADE_INVENTORY_ADDR = 0x80235098  #4 Bytes
MONSTER_TOKEN_INVENTORY_ADDR = 0x8023509C  #4 Bytes
MAX_GUM_COUNT_ADDR = 0x802350A8
MAX_SOAP_COUNT_ADDR = 0x802350AC
PLAYER_CONTROL_OWNER = 0x80234e90
MAP_ADDR = 0x8025F140
WARP_ADDR = 0x801b7ef4
VISITED_SCENES_ADDR = 0x8026af70

SLOT_NAME_ADDR = 0x801c5c9c
SEED_ADDR = SLOT_NAME_ADDR + 0x40
# we currently write/read 0x20 bytes starting from 0x817f0000 to/from save game
# expected received item index
EXPECTED_INDEX_ADDR = 0x817f0000
KEY_COUNT_ADDR = 0x817f0004
BOSS_KILLS_ADDR = 0x817f0019
# Free space for 1A and 1B
SAVED_WARP_ADDR = 0x817f001C
# delayed item
SAVED_SLOT_NAME_ADDR = 0x817f0020
SAVED_SEED_ADDR = SAVED_SLOT_NAME_ADDR + 0x40


class Upgrades(Enum):              #Bit assigned at 0x80235098
    GumPower = 0xD4FD7D3C          #xxxx xxxx xxxx xxxx x000 0000 0000 0001
    SoapPower = 0xE8A3B45F         #xxxx xxxx xxxx xxxx x000 0000 0000 0010
    BootsPower = 0x9133CECD        #xxxx xxxx xxxx xxxx x000 0000 0000 0100
    PlungerPower = 0xDA82A36C      #xxxx xxxx xxxx xxxx x000 0000 0000 1000
    SlippersPower = 0x9AD0813E     #xxxx xxxx xxxx xxxx x000 0000 0001 0000
    LampshadePower = 0x6FAFFB01    #xxxx xxxx xxxx xxxx x000 0000 0010 0000
    BlackKnightPower = 0xB00E719E  #xxxx xxxx xxxx xxxx x000 0000 0100 0000
    SpringPower = 0xD88133D6       #xxxx xxxx xxxx xxxx x000 0010 0000 0000
    PoundPower = 0x84D3E950        #xxxx xxxx xxxx xxxx x000 0100 0000 0000
    HelmetPower = 0x2F03BFDC       #xxxx xxxx xxxx xxxx x000 1000 0000 0000
    UmbrellaPower = 0xC889BB9E     #xxxx xxxx xxxx xxxx x001 0000 0000 0000
    ShovelPower = 0x866C5887       #xxxx xxxx xxxx xxxx x010 0000 0000 0000
    ShockwavePower = 0x1B0ADE07    #xxxx xxxx xxxx xxxx x100 0000 0000 0000
    GumOverAcid2 = 0xEAF330FE      #Gum upgrades increment 0x802350A8 by 5.
    GumPack = 0xFFD0E61E
    GumMaxAmmo = 0xFFFD7A85
    Gum_Upgrade = 0x362E34B4
    GumUpgrade = 0x7EDE8BAD
    BubblePack = 0xBF9B5D09
    Soap__Box = 0xD656A182         #Soap upgrades increment 0x802350AC by 5
    SoapBox1 = 0x3550C423
    SoapOverAcid2 = 0x0C7A534E
    Soap_Box = 0xDEC7BAA7
    SoapBox = 0xB380CBF0
    SoapPack = 0xDCC4E558


class MonsterTokens(Enum):       #Bit assigned at 0x8023509C
    MT_BLACKKNIGHT = 0x3A6FCC38  #xxxx xxxx xxx0 0000 0000 0000 0000 0001
    MT_MOODY = 0xDC98824E        #xxxx xxxx xxx0 0000 0000 0000 0000 0010
    MT_CAVEMAN = 0x56400EF1      #xxxx xxxx xxx0 0000 0000 0000 0000 0100
    MT_CREEPER = 0xDFA0C15E      #xxxx xxxx xxx0 0000 0000 0000 0000 1000
    MT_GARGOYLE = 0xFBBC715F     #xxxx xxxx xxx0 0000 0000 0000 0001 0000
    MT_GERONIMO = 0x94C56BF0     #xxxx xxxx xxx0 0000 0000 0000 0010 0000
    MT_GHOST = 0x74004B8A        #xxxx xxxx xxx0 0000 0000 0000 0100 0000
    MT_GHOSTDIVER = 0x2ACB9327   #xxxx xxxx xxx0 0000 0000 0000 1000 0000
    MT_GREENGHOST = 0xF077B0E1   #xxxx xxxx xxx0 0000 0000 0001 0000 0000
    MT_HEADLESS = 0x52CE630A     #xxxx xxxx xxx0 0000 0000 0010 0000 0000
    MT_MASTERMIND = 0x08D04C9B   #xxxx xxxx xxx0 0000 0000 0100 0000 0000
    MT_ROBOT = 0x699623C9        #xxxx xxxx xxx0 0000 0000 1000 0000 0000
    MT_REDBEARD = 0x0F7F79CB     #xxxx xxxx xxx0 0000 0001 0000 0000 0000
    MT_SCARECROW = 0xAB19F726    #xxxx xxxx xxx0 0000 0010 0000 0000 0000
    MT_SEACREATURE = 0x6CC29412  #xxxx xxxx xxx0 0000 0100 0000 0000 0000
    MT_SPACEKOOK = 0xFC42FAAC    #xxxx xxxx xxx0 0000 1000 0000 0000 0000
    MT_TARMONSTER = 0x2E849EB9   #xxxx xxxx xxx0 0001 0000 0000 0000 0000
    MT_WITCH = 0x8CFF4526        #xxxx xxxx xxx0 0010 0000 0000 0000 0000
    MT_WITCHDOC = 0x55794316     #xxxx xxxx xxx0 0100 0000 0000 0000 0000
    MT_WOLFMAN = 0x51D4A7D2      #xxxx xxxx xxx0 1000 0000 0000 0000 0000
    MT_ZOMBIE = 0x818F2933       #xxxx xxxx xxx1 0000 0000 0000 0000 0000


class Keys(Enum):
    DOORKEY = 0x13109411
    DOORKEY1 = 0xC17BC4E4
    DOORKEY2 = 0xC17BC4E5
    DOORKEY3 = 0xC17BC4E6
    DOORKEY4 = 0xC17BC4E7
    DUG_FISHING_KEY = 0xBB82B3B3
    HEDGE_KEY = 0xBBFA4948
    KEY = 0x0013C74B
    KEY_01 = 0x76E9B34A
    KEY_02 = 0x76E9B34B
    KEY_03 = 0x76E9B34C
    KEY_1 = 0x2DDAB334
    KEY_2 = 0x2DDAB335
    KEY_3 = 0x2DDAB336
    KEY_4 = 0x2DDAB337
    KEY01 = 0x2DDABB64
    KEY02 = 0x2DDABB65
    KEY03 = 0x2DDABB66
    KEY04 = 0x2DDABB67
    KEY1 = 0x0A1EFB92
    KEY2 = 0x0A1EFB93
    KEY3 = 0x0A1EFB94
    KEY4 = 0x0A1EFB95
    KEY5 = 0x0A1EFB96


class Warpgates(Enum):
    WARPPOINT = 0xD7341DE8
    WARP_GATE = 0x8B8D6C9B
    WARPGATE_POWERUP = 0xD399D40F


#Snacks are notated nearly exactly as they are in the game, but Space characters are replaced with "__"
class Snacks(Enum):
#    BOX__O__SNACKS__UNDER__SWINGER   =
#    BOX__O__SNACKS__UNDER__SWINGER0  =
#    BOX__O__SNACKS__UNDER__SWINGER00 =
    BOX__OF__SNACKS__01              = 0x19A254BC
    BOX__OF__SNACKS__02              = 0x19A254BD
    BOX__OF__SNACKS__03              = 0x19A254BE
    BOX__OF__SNACKS__04              = 0x19A254BF
    BOX__OF__SNACKS__05              = 0x19A254C0
    BOX__OF__SNACKS__06              = 0x19A254C1
    BOX__OF__SNACKS__07              = 0x19A254C2
    BOX__OF__SNACKS__1               = 0xAE1E8D5A
    BOX__OF__SNACKS__2               = 0xAE1E8D5B
    BOX__OF__SNACKS__3               = 0xAE1E8D5C
    BOX__OF__SNACKS__4               = 0xAE1E8D5D
    BOX__OF__SNACKS__5               = 0xAE1E8D5E
#    BOX__OVER__WITCH                 =
#    BOX10__SNACKBOX                  =
#    BOX11__SNACKBOX                  =
#    BOX13__SNACKBOX                  =
#    BOX2__SNACKBOX                   =
#    BOX3__SNACKBOX                   =
#    BOX5__SNACKBOX                   =
#    BOX6__SNACKBOX                   =
#    BOX8__SNACKBOX                   =
#    BP_SS03                          =
#    BP_SS04                          =
#    BP_SS05                          =
#    BP_SSBOX01                       =
#    BP_SSBOX03                       =
#    BP_SSBOX04                       =
#    CLIFF_SSBOX01                    =
#    CLIFF_SSBOX02                    =
#    CLIFF_SSBOX03                    =
#    CLIFF_SSBOX04                    =
#    CLIFF_SSBOX05                    =
#    CLIFF_SSBOX06                    =
#    CRATE__1__PRIZE                  =
#    CRATE__2__PRIZE                  =
#    CRATE__3__PRIZE                  =
    CRATE__PRIZE__1                  = 0x29CED7DE
    CRATE__PRIZE__10                 = 0x64D876CA
    CRATE__SNACKBOX__1               = 0x90B3757E
    CRATE__SNACKBOX__2               = 0x90B3757F
    CRATE__SNACKBOX__3               = 0x90B37580
    CRATE__SNACKBOX__4               = 0x90B37581
#    CRATE02__SNACKBOX                =
#    CRATE03__SNACKBOX                =
#    CRATE04__SNACKBOX                =
#    CRATE06__SNACKBOX                =
#    CRATE07__SNACKBOX                =
#    CRATE08__SNACKBOX                =
#    CRATE_SNACK01                    =
#    CRATE_SNACK02                    =
#    CRATE_SNACK03                    =
#    CRATE_SNACK04                    =
#    CRATE_SNACK05                    =
#    CRATE_SNACK06                    =
#    CRATE_SNACK08                    =
#    CRATE_SNACK09                    =
#    CRATE_SSBOX07                    =
#    DIG__2__SNACKBOX                 =
    DRYER__SNACKBOX__1               = 0x12E62152
    DRYER__SNACKBOX__2               = 0x12E62153
#    EX__CLUE__SNACK__BOX__1          =
#    EX__CLUE__SNACK__BOX__2          =
#    EX__CLUE__SNACK__BOX__3          =
#    EX__CLUE__SNACK__BOX__4          =
#    EX__CLUE__SNACK__BOX2            =
#    EX__CLUE__SNACK__BOX3            =
#    EX__CLUE__SNACK__BOX5            =
    EX__CLUE__SNACKBOX__1            = 0x2E3F1530
    EX__CLUE__SNACKBOX__2            = 0x2E3F1531
    EX__CLUE__SNACKBOX__3            = 0x2E3F1532
#    EX__CLUE__SNACKBOX__4            =
#    EX__CLUE__SNACKBOX1              =
    EX__CLUE__SNACKBOX2              = 0x1BB638E7
    EX__CLUE__SNACKBOX3              = 0x1BB638E8
    EX__CLUE__SNACKBOX30             = 0x2E3F1EE8
    EX__CLUE__SNACKBOX300            = 0xAA4CD0E8
    EX__CLUE__SNACKBOX3000           = 0x254EE6E8
    EX__CLUE__SNACKBOX4              = 0x1BB638E9
    EX__CLUE__SNACKBOX5              = 0x1BB638EA
#    EXCLUE__SNACKBOX__1              =
#    HIGH__SNACK__BOX                 =
    HIGH__SNACKBOX__1                = 0xA542AA10
    HIGH__SNACKBOX__10               = 0x911D0660
#    LASTFLOAT_SS02                   =
#    LASTFLOAT_SS03                   =
#    LASTFLOAT_SS04                   =
#    NEW__SNACKBOX                    =
#    NEW__SNACKBOX__2                 =
#    PLAT04_SS01                      =
#    PLAT04_SS010                     =
#    PLAT04_SS011                     =
#    PLAT04_SS012                     =
#    PLAT04_SS013                     =
#    PLAT06_SS01                      =
#    PLAT06_SS010                     =
#    PLAT06_SS011                     =
#    PLAT06_SS012                     =
#    PLAT06_SS013                     =
#    REEF_SS01                        =
#    REEF_SS02                        =
#    REEF_SS03                        =
#    REEF_SS04                        =
#    REEF_SS05                        =
#    REEF_SS06                        =
#    REEF_SS07                        =
#    REEF_SS08                        =
#    REEF_SS09                        =
#    REEF_SS10                        =
#    REEF_SS11                        =
#    REEF_SS12                        =
#    REEF_SS13                        =
#    REEF_SS14                        =
#    REEF_SS15                        =
#    S01                              =
#    S010                             =
#    S011                             =
#    S012                             =
#    S013                             =
#    S014                             =
#    S015                             =
#    S016                             =
#    S01_AIR                          =
#    S02                              =
#    S020                             =
#    S021                             =
#    S022                             =
#    S023                             =
#    S024                             =
#    S025                             =
#    S027                             =
#    S029                             =
#    S02_AIR                          =
#    S03                              =
#    S030                             =
#    S031                             =
#    S032                             =
#    S033                             =
#    S034                             =
#    S04                              =
#    S040                             =
#    S041                             =
#    S0411                            =
#    S0413                            =
#    S0415                            =
#    S0417                            =
#    S04181                           =
#    S04183                           =
#    S04185                           =
#    S042                             =
#    S043                             =
#    S044                             =
#    S045                             =
#    S046                             =
#    S047                             =
#    S049                             =
#    S05                              =
#    S06                              =
#    S07                              =
#    S08                              =
#    S080                             =
#    S09                              =
#    S090                             =
#    S1                               =
#    S10                              =
#    S100                             =
#    S10B                             =
#    S10C                             =
#    S10D                             =
#    S11                              =
#    S12                              =
#    S121                             =
#    S123                             =
#    S13                              =
#    S130                             =
#    S132                             =
#    S14                              =
#    S15                              =
#    S16                              =
#    S17                              =
#    S170                             =
#    S171                             =
#    S172                             =
#    S173                             =
#    S174                             =
#    S18                              =
#    S18B                             =
#    S19                              =
#    S190                             =
#    S191                             =
#    S192                             =
#    S193                             =
#    S195                             =
#    S197                             =
#    S199                             =
#    S19B                             =
#    S2                               =
#    S20                              =
#    S200                             =
#    S201                             =
#    S202                             =
#    S203                             =
#    S204                             =
#    S205                             =
#    S2061                            =
#    S20611                           =
#    S206121                          =
#    S2063                            =
#    S2065                            =
#    S2067                            =
#    S2069                            =
#    S20B                             =
#    S20C                             =
#    S20D                             =
#    S21                              =
#    S210                             =
#    S211                             =
#    S212                             =
#    S213                             =
#    S214                             =
#    S215                             =
#    S22                              =
#    S23                              =
#    S24                              =
#    S25                              =
#    S26                              =
#    S27                              =
#    S28                              =
#    S29                              =
#    S3                               =
#    S30                              =
#    S300                             =
#    S302                             =
#    S31                              =
#    S310                             =
#    S311                             =
#    S312                             =
#    S313                             =
#    S314                             =
#    S315                             =
#    S316                             =
#    S317                             =
#    S32                              =
#    S321                             =
#    S322                             =
#    S323                             =
#    S324                             =
#    S325                             =
#    S326                             =
#    S33                              =
#    S330                             =
#    S331                             =
#    S332                             =
#    S333                             =
#    S334                             =
#    S335                             =
#    S3350                            =
#    S3351                            =
#    S3352                            =
#    S3353                            =
#    S3354                            =
#    S34                              =
#    S340                             =
#    S341                             =
#    S342                             =
#    S343                             =
#    S344                             =
#    S345                             =
#    S346                             =
#    S3460                            =
#    S3461                            =
#    S3462                            =
#    S3463                            =
#    S3464                            =
#    S34_COUNT30                      =
#    S36                              =
#    S37                              =
#    S38                              =
#    S39                              =
#    S4                               =
#    S40                              =
#    S41                              =
#    S42                              =
#    S43                              =
#    S44                              =
#    S45                              =
#    S450                             =
#    S471                             =
#    S472                             =
#    S475                             =
#    S476                             =
#    S5                               =
#    S51                              =
#    S53                              =
#    S55                              =
#    S56                              =
#    S561                             =
#    S563                             =
#    S565                             =
#    S8                               =
#    S89                              =
#    S90                              =
#    S91                              =
#    S92                              =
#    S93                              =
#    S94                              =
#    S95                              =
#    S96                              =
#    S97                              =
#    S98                              =
#    S99                              =
#    SB__UP__TOP1                     =
#    SB__UP__TOP2                     =
#    SCARE__SNACK__BOX                =
#    SLOPE_SS01                       =
#    SLOPE_SS02                       =
#    SLOPE_SS03                       =
#    SLOPE_SS05                       =
#    SLOPE_SS06                       =
#    SLOPE_SS07                       =
#    SLOPE_SS09                       =
#    SLOPE_SS10                       =
#    SLOPE_SSBOX04                    =
#    SLOPE_SSBOX08                    =
#    SM100                            =
#    SM68                             =
#    SM69                             =
#    SM70                             =
#    SM71                             =
#    SM72                             =
#    SM73                             =
#    SM74                             =
#    SM75                             =
#    SM76                             =
#    SM77                             =
#    SM78                             =
#    SM79                             =
#    SM80                             =
#    SM81                             =
#    SM82                             =
#    SM83                             =
#    SM84                             =
#    SM85                             =
#    SM86                             =
#    SM87                             =
#    SM88                             =
#    SM89                             =
#    SM90                             =
#    SM91                             =
#    SM92                             =
#    SM93                             =
#    SM94                             =
#    SM95                             =
#    SM96                             =
#    SM97                             =
#    SM98                             =
#    SM99                             =
#    SN1                              =
#    SN10                             =
#    SN100                            =
#    SN101                            =
#    SN102                            =
#    SN103                            =
#    SN104                            =
#    SN105                            =
#    SN11                             =
#    SN12                             =
#    SN13                             =
#    SN14                             =
#    SN15                             =
#    SN16                             =
#    SN17                             =
#    SN18                             =
#    SN19                             =
#    SN2                              =
#    SN20                             =
#    SN21                             =
#    SN22                             =
#    SN23                             =
#    SN24                             =
#    SN25                             =
#    SN26                             =
#    SN27                             =
#    SN28                             =
#    SN29                             =
#    SN3                              =
#    SN30                             =
#    SN31                             =
#    SN32                             =
#    SN33                             =
#    SN34                             =
#    SN35                             =
#    SN36                             =
#    SN37                             =
#    SN38                             =
#    SN39                             =
#    SN4                              =
#    SN40                             =
#    SN41                             =
#    SN42                             =
#    SN43                             =
#    SN44                             =
#    SN45                             =
#    SN46                             =
#    SN47                             =
#    SN48                             =
#    SN480                            =
#    SN49                             =
#    SN5                              =
#    SN50                             =
#    SN51                             =
#    SN52                             =
#    SN53                             =
#    SN54                             =
#    SN55                             =
#    SN56                             =
#    SN57                             =
#    SN58                             =
#    SN59                             =
#    SN6                              =
#    SN60                             =
#    SN61                             =
#    SN62                             =
#    SN63                             =
#    SN64                             =
#    SN65                             =
#    SN66                             =
#    SN67                             =
#    SN68                             =
#    SN680                            =
#    SN6800                           =
#    SN69                             =
#    SN7                              =
#    SN70                             =
#    SN71                             =
#    SN72                             =
#    SN73                             =
#    SN74                             =
#    SN75                             =
#    SN76                             =
#    SN77                             =
#    SN78                             =
#    SN79                             =
#    SN8                              =
#    SN80                             =
#    SN81                             =
#    SN82                             =
#    SN83                             =
#    SN84                             =
#    SN840                            =
#    SN841                            =
#    SN842                            =
#    SN843                            =
#    SN844                            =
#    SN845                            =
#    SN846                            =
#    SN847                            =
#    SN85                             =
#    SN86                             =
#    SN87                             =
#    SN88                             =
#    SN89                             =
#    SN9                              =
#    SN90                             =
#    SN91                             =
#    SN92                             =
#    SN93                             =
#    SN94                             =
#    SN95                             =
#    SN96                             =
#    SN97                             =
#    SN98                             =
#    SN99                             =
    SNACK__001                       = 0x5F6E2F4B
    SNACK__0010                      = 0xD5623391
    SNACK__0012                      = 0xD5623393
    SNACK__0013                      = 0xD5623394
    SNACK__01                        = 0x432BD55F
    SNACK__010                       = 0x5F6E2FCD
    SNACK__011                       = 0x5F6E2FCE
    SNACK__0110                      = 0xD562769A
    SNACK__012                       = 0x5F6E2FCF
    SNACK__013                       = 0x5F6E2FD0
    SNACK__014                       = 0x5F6E2FD1
    SNACK__015                       = 0x5F6E2FD2
    SNACK__016                       = 0x5F6E2FD3
    SNACK__017                       = 0x5F6E2FD4
    SNACK__02                        = 0x432BD560
    SNACK__020                       = 0x5F6E3050
    SNACK__021                       = 0x5F6E3051
    SNACK__022                       = 0x5F6E3052
    SNACK__023                       = 0x5F6E3053
    SNACK__024                       = 0x5F6E3054
    SNACK__025                       = 0x5F6E3055
    SNACK__03                        = 0x432BD561
    SNACK__030                       = 0x5F6E30D3
    SNACK__031                       = 0x5F6E30D4
    SNACK__032                       = 0x5F6E30D5
    SNACK__033                       = 0x5F6E30D6
    SNACK__0330                      = 0xD562FDB2
    SNACK__0331                      = 0xD562FDB3
    SNACK__0332                      = 0xD562FDB4
    SNACK__0333                      = 0xD562FDB5
    SNACK__034                       = 0x5F6E30D7
    SNACK__035                       = 0x5F6E30D8
    SNACK__036                       = 0x5F6E30D9
    SNACK__037                       = 0x5F6E30DA
    SNACK__038                       = 0x5F6E30DB
    SNACK__039                       = 0x5F6E30DC
    SNACK__04                        = 0x432BD562
    SNACK__040                       = 0x5F6E3156
    SNACK__041                       = 0x5F6E3157
    SNACK__042                       = 0x5F6E3158
    SNACK__0420                      = 0xD5634038
    SNACK__0421                      = 0xD5634039
    SNACK__0422                      = 0xD563403A
    SNACK__043                       = 0x5F6E3159
    SNACK__044                       = 0x5F6E315A
    SNACK__045                       = 0x5F6E315B
    SNACK__046                       = 0x5F6E315C
    SNACK__047                       = 0x5F6E315D
    SNACK__048                       = 0x5F6E315E
    SNACK__049                       = 0x5F6E315F
    SNACK__05                        = 0x432BD563
    SNACK__050                       = 0x5F6E31D9
    SNACK__051                       = 0x5F6E31DA
    SNACK__052                       = 0x5F6E31DB
    SNACK__053                       = 0x5F6E31DC
    SNACK__054                       = 0x5F6E31DD
    SNACK__055                       = 0x5F6E31DE
    SNACK__056                       = 0x5F6E31DF
    SNACK__06                        = 0x432BD564
    SNACK__060                       = 0x5F6E325C
    SNACK__061                       = 0x5F6E325D
    SNACK__0610                      = 0xD563C5C7
    SNACK__062                       = 0x5F6E325E
    SNACK__063                       = 0x5F6E325F
    SNACK__064                       = 0x5F6E3260
    SNACK__065                       = 0x5F6E3261
    SNACK__066                       = 0x5F6E3262
    SNACK__067                       = 0x5F6E3263
    SNACK__068                       = 0x5F6E3264
    SNACK__07                        = 0x432BD565
    SNACK__070                       = 0x5F6E32DF
    SNACK__071                       = 0x5F6E32E0
    SNACK__072                       = 0x5F6E32E1
    SNACK__0720                      = 0xD5640953
    SNACK__0721                      = 0xD5640954
    SNACK__0722                      = 0xD5640955
    SNACK__073                       = 0x5F6E32E2
    SNACK__07330                     = 0x32310A3B
    SNACK__07331                     = 0x32310A3C
    SNACK__07332                     = 0x32310A3D
    SNACK__07333                     = 0x32310A3E
    SNACK__07334                     = 0x32310A3F
    SNACK__07335                     = 0x32310A40
    SNACK__07336                     = 0x32310A41
    SNACK__074                       = 0x5F6E32E3
    SNACK__075                       = 0x5F6E32E4
    SNACK__076                       = 0x5F6E32E5
    SNACK__077                       = 0x5F6E32E6
    SNACK__078                       = 0x5F6E32E7
    SNACK__079                       = 0x5F6E32E8
    SNACK__0790                      = 0xD5640CE8
    SNACK__0791                      = 0xD5640CE9
    SNACK__0792                      = 0xD5640CEA
    SNACK__0793                      = 0xD5640CEB
    SNACK__0794                      = 0xD5640CEC
    SNACK__08                        = 0x432BD566
    SNACK__080                       = 0x5F6E3362
    SNACK__081                       = 0x5F6E3363
    SNACK__082                       = 0x5F6E3364
    SNACK__083                       = 0x5F6E3365
    SNACK__0830                      = 0xD5644CDF
    SNACK__0831                      = 0xD5644CE0
    SNACK__0832                      = 0xD5644CE1
    SNACK__08320                     = 0x32535753
    SNACK__08321                     = 0x32535754
    SNACK__08322                     = 0x32535755
    SNACK__0833                      = 0xD5644CE2
    SNACK__084                       = 0x5F6E3366
    SNACK__085                       = 0x5F6E3367
    SNACK__09                        = 0x432BD567
    SNACK__090                       = 0x5F6E33E5
    SNACK__091                       = 0x5F6E33E6
    SNACK__092                       = 0x5F6E33E7
    SNACK__093                       = 0x5F6E33E8
    SNACK__094                       = 0x5F6E33E9
    SNACK__095                       = 0x5F6E33EA
    SNACK__096                       = 0x5F6E33EB
    SNACK__1                         = 0xB640D2BB
    SNACK__1__MIL                    = 0x40B0A1E7
    SNACK__10                        = 0x432BD5E1
    SNACK__100                       = 0x5F6E7253
    SNACK__101                       = 0x5F6E7254
    SNACK__102                       = 0x5F6E7255
    SNACK__103                       = 0x5F6E7256
    SNACK__104                       = 0x5F6E7257
    SNACK__105                       = 0x5F6E7258
    SNACK__106                       = 0x5F6E7259
    SNACK__107                       = 0x5F6E725A
    SNACK__108                       = 0x5F6E725B
    SNACK__109                       = 0x5F6E725C
    SNACK__11                        = 0x432BD5E2
    SNACK__110                       = 0x5F6E72D6
    SNACK__111                       = 0x5F6E72D7
    SNACK__112                       = 0x5F6E72D8
    SNACK__113                       = 0x5F6E72D9
    SNACK__1130                      = 0xD584C53B
    SNACK__1131                      = 0xD584C53C
    SNACK__114                       = 0x5F6E72DA
    SNACK__12                        = 0x432BD5E3
    SNACK__120                       = 0x5F6E7359
    SNACK__121                       = 0x5F6E735A
    SNACK__122                       = 0x5F6E735B
    SNACK__123                       = 0x5F6E735C
    SNACK__124                       = 0x5F6E735D
    SNACK__125                       = 0x5F6E735E
    SNACK__126                       = 0x5F6E735F
    SNACK__127                       = 0x5F6E7360
    SNACK__128                       = 0x5F6E7361
    SNACK__129                       = 0x5F6E7362
    SNACK__13                        = 0x432BD5E4
    SNACK__130                       = 0x5F6E73DC
    SNACK__131                       = 0x5F6E73DD
    SNACK__1310                      = 0xD5854A47
    SNACK__132                       = 0x5F6E73DE
    SNACK__133                       = 0x5F6E73DF
    SNACK__1330                      = 0xD5854B4D
    SNACK__1331                      = 0xD5854B4E
    SNACK__1332                      = 0xD5854B4F
    SNACK__1333                      = 0xD5854B50
    SNACK__138                       = 0x5F6E73E4
    SNACK__139                       = 0x5F6E73E5
    SNACK__14                        = 0x432BD5E5
    SNACK__140                       = 0x5F6E745F
    SNACK__141                       = 0x5F6E7460
    SNACK__142                       = 0x5F6E7461
    SNACK__143                       = 0x5F6E7462
    SNACK__144                       = 0x5F6E7463
    SNACK__15                        = 0x432BD5E6
    SNACK__150                       = 0x5F6E74E2
    SNACK__151                       = 0x5F6E74E3
    SNACK__152                       = 0x5F6E74E4
    SNACK__153                       = 0x5F6E74E5
    SNACK__154                       = 0x5F6E74E6
    SNACK__155                       = 0x5F6E74E7
    SNACK__156                       = 0x5F6E74E8
    SNACK__157                       = 0x5F6E74E9
    SNACK__158                       = 0x5F6E74EA
    SNACK__159                       = 0x5F6E74EB
    SNACK__16                        = 0x432BD5E7
    SNACK__160                       = 0x5F6E7565
    SNACK__161                       = 0x5F6E7566
    SNACK__162                       = 0x5F6E7567
    SNACK__163                       = 0x5F6E7568
    SNACK__164                       = 0x5F6E7569
    SNACK__165                       = 0x5F6E756A
    SNACK__17                        = 0x432BD5E8
    SNACK__170                       = 0x5F6E75E8
    SNACK__171                       = 0x5F6E75E9
    SNACK__172                       = 0x5F6E75EA
    SNACK__173                       = 0x5F6E75EB
    SNACK__174                       = 0x5F6E75EC
    SNACK__175                       = 0x5F6E75ED
    SNACK__176                       = 0x5F6E75EE
    SNACK__177                       = 0x5F6E75EF
    SNACK__178                       = 0x5F6E75F0
    SNACK__18                        = 0x432BD5E9
    SNACK__180                       = 0x5F6E766B
    SNACK__181                       = 0x5F6E766C
    SNACK__182                       = 0x5F6E766D
    SNACK__183                       = 0x5F6E766E
    SNACK__184                       = 0x5F6E766F
    SNACK__185                       = 0x5F6E7670
    SNACK__186                       = 0x5F6E7671
    SNACK__187                       = 0x5F6E7672
    SNACK__188                       = 0x5F6E7673
    SNACK__189                       = 0x5F6E7674
    SNACK__19                        = 0x432BD5EA
    SNACK__190                       = 0x5F6E76EE
    SNACK__191                       = 0x5F6E76EF
    SNACK__1910                      = 0xD586DC7D
    SNACK__1911                      = 0xD586DC7E
    SNACK__1912                      = 0xD586DC7F
    SNACK__1913                      = 0xD586DC80
    SNACK__1914                      = 0xD586DC81
    SNACK__1915                      = 0xD586DC82
    SNACK__1916                      = 0xD586DC83
    SNACK__1917                      = 0xD586DC84
    SNACK__1918                      = 0xD586DC85
    SNACK__1919                      = 0xD586DC86
    SNACK__192                       = 0x5F6E76F0
    SNACK__193                       = 0x5F6E76F1
    SNACK__194                       = 0x5F6E76F2
    SNACK__195                       = 0x5F6E76F3
    SNACK__196                       = 0x5F6E76F4
    SNACK__197                       = 0x5F6E76F5
    SNACK__198                       = 0x5F6E76F6
    SNACK__199                       = 0x5F6E76F7
    SNACK__2                         = 0xB640D2BC
    SNACK__20                        = 0X432BD664
    SNACK__200                       = 0x5F6EB55C
    SNACK__201                       = 0x5F6EB55D
    SNACK__202                       = 0x5F6EB55E
    SNACK__203                       = 0x5F6EB55F
    SNACK__2030                      = 0xD5A6CFCD
    SNACK__2031                      = 0xD5A6CFCE
    SNACK__2032                      = 0xD5A6CFCF
    SNACK__2033                      = 0xD5A6CFD0
    SNACK__20340                     = 0x545C5823
    SNACK__203400                    = 0x2B411A19
    SNACK__203401                    = 0x2B411A1A
    SNACK__203402                    = 0x2B411A1B
    SNACK__203403                    = 0x2B411A1C
    SNACK__2034040                   = 0x22505D07
    SNACK__20340400                  = 0x8F1F9AC5
    SNACK__20340401                  = 0x8F1F9AC6
    SNACK__20340402                  = 0x8F1F9AC7
    SNACK__20340403                  = 0x8F1F9AC8
    SNACK__20340404                  = 0x8F1F9AC9
    SNACK__204                       = 0x5F6EB560
    SNACK__21                        = 0x432BD665
    SNACK__210                       = 0x5F6EB5DF
    SNACK__211                       = 0x5F6EB5E0
    SNACK__2110                      = 0xD5A711D0
    SNACK__2112                      = 0xD5A711D2
    SNACK__2114                      = 0xD5A711D4
    SNACK__2116                      = 0xD5A711D6
    SNACK__212                       = 0x5F6EB5E1
    SNACK__213                       = 0x5F6EB5E2
    SNACK__214                       = 0x5F6EB5E3
    SNACK__2140                      = 0xD5A71359
    SNACK__21400                     = 0x547EE6BB
    SNACK__21401                     = 0x547EE6BC
    SNACK__21402                     = 0x547EE6BD
    SNACK__21403                     = 0x547EE6BE
    SNACK__21404                     = 0x547EE6BF
    SNACK__216                       = 0x5F6EB5E5
    SNACK__217                       = 0x5F6EB5E6
    SNACK__22                        = 0x432BD666
    SNACK__220                       = 0x5F6EB662
    SNACK__221                       = 0x5F6EB663
    SNACK__2210                      = 0xD5A754D9
    SNACK__2212                      = 0xD5A754DB
    SNACK__2214                      = 0xD5A754DD
    SNACK__2216                      = 0xD5A754DF
    SNACK__2218                      = 0xD5A754E1
    SNACK__222                       = 0x5F6EB664
    SNACK__223                       = 0x5F6EB665
    SNACK__224                       = 0x5F6EB666
    SNACK__226                       = 0x5F6EB668
    SNACK__228                       = 0x5F6EB66A
    SNACK__23                        = 0x432BD667
    SNACK__230                       = 0x5F6EB6E5
    SNACK__231                       = 0x5F6EB6E6
    SNACK__232                       = 0x5F6EB6E7
    SNACK__233                       = 0x5F6EB6E8
    SNACK__24                        = 0x432BD668
    SNACK__243                       = 0x5F6EB76B
    SNACK__244                       = 0x5F6EB76C
    SNACK__245                       = 0x5F6EB76D
    SNACK__246                       = 0x5F6EB76E
    SNACK__25                        = 0X432BD669
    SNACK__250                       = 0x5F6EB7EB
    SNACK__251                       = 0x5F6EB7EC
    SNACK__252                       = 0x5F6EB7ED
    SNACK__2520                      = 0xD5A81E77
    SNACK__2521                      = 0xD5A81E78
    SNACK__2522                      = 0xD5A81E79
    SNACK__25221                     = 0x5507981C
    SNACK__25222                     = 0x5507981D
    SNACK__252220                    = 0x82E2D707
    SNACK__252221                    = 0x82E2D708
    SNACK__252222                    = 0x82E2D709
    SNACK__2522220                   = 0xFA1409CB
    SNACK__2522221                   = 0xFA1409CC
    SNACK__2522222                   = 0xFA1409CD
    SNACK__25222220                  = 0xF8410417
    SNACK__25222221                  = 0xF8410418
    SNACK__25222222                  = 0xF8410419
    SNACK__252222220                 = 0x094518FB
    SNACK__252222221                 = 0x094518FC
    SNACK__252222222                 = 0x094518FD
    SNACK__2523                      = 0xD5A81E7A
    SNACK__253                       = 0x5F6EB7EE
    SNACK__2530                      = 0xD5A81EFA
    SNACK__2531                      = 0xD5A81EFB
    SNACK__2532                      = 0xD5A81EFC
    SNACK__254                       = 0x5F6EB7EF
    SNACK__255                       = 0x5F6EB7F0
    SNACK__256                       = 0x5F6EB7F1
    SNACK__257                       = 0x5F6EB7F2
    SNACK__258                       = 0x5F6EB7F3
    SNACK__259                       = 0x5F6EB7F4
    SNACK__260                       = 0x5F6EB86E
    SNACK__2610                      = 0xD5A860FD
    SNACK__2612                      = 0xD5A860FF
    SNACK__2614                      = 0xD5A86001
    SNACK__2616                      = 0xD5A86003
    SNACK__2618                      = 0xD5A86005
    SNACK__262                       = 0x5F6EB870
    SNACK__2620                      = 0xD5A86103
    SNACK__2622                      = 0xD5A86105
    SNACK__264                       = 0x5F6EB872
    SNACK__266                       = 0x5F6EB874
    SNACK__268                       = 0x5F6EB876
    SNACK__27                        = 0X432BD66B
    SNACK__270                       = 0x5F6EB8F1
    SNACK__271                       = 0x5F6EB8F2
    SNACK__272                       = 0x5F6EB8F3
    SNACK__273                       = 0x5F6EB8F4
    SNACK__274                       = 0x5F6EB8F5
    SNACK__275                       = 0x5F6EB8F6
    SNACK__276                       = 0x5F6EB8F7
    SNACK__277                       = 0x5F6EB8F8
    SNACK__278                       = 0x5F6EB8F9
    SNACK__28                        = 0x432BD66C
    SNACK__280                       = 0x5F6EB974
    SNACK__281                       = 0x5F6EB975
    SNACK__282                       = 0x5F6EB976
    SNACK__283                       = 0x5F6EB977
    SNACK__29                        = 0X432BD66D
    SNACK__292                       = 0x5F6EB9F9
    SNACK__3                         = 0xB640D2BD
    SNACK__30                        = 0x432BD6E7
    SNACK__300                       = 0x5F6EF685
    SNACK__301                       = 0x5F6EF686
    SNACK__3010                      = 0xD5C91C62
    SNACK__3011                      = 0xD5C91C63
    SNACK__3012                      = 0xD5C91C64
    SNACK__3013                      = 0xD5C91C65
    SNACK__3014                      = 0xD5C91C66
    SNACK__302                       = 0x5F6EF687
    SNACK__3020                      = 0xD5C91CE5
    SNACK__3021                      = 0xD5C91CE6
    SNACK__3022                      = 0xD5C91CE7
    SNACK__30220                     = 0x65E9CA65
    SNACK__30221                     = 0x65E9CA66
    SNACK__30222                     = 0x65E9CA67
    SNACK__303                       = 0x5F6EF688
    SNACK__3030                      = 0xD5C91D68
    SNACK__30300                     = 0x65EA0C68
    SNACK__30301                     = 0x65EA0C69
    SNACK__30302                     = 0x65EA0C6A
    SNACK__30303                     = 0x65EA0C6B
    SNACK__304                       = 0x5F6EF689
    SNACK__305                       = 0x5F6EF68A
    SNACK__306                       = 0x5F6EF68B
    SNACK__307                       = 0x5F6EF68C
    SNACK__308                       = 0x5F6EF68D
    SNACK__309                       = 0x5F6EF68E
    SNACK__31                        = 0x432BD6E8
    SNACK__310                       = 0x5F6EF8E8
    SNACK__311                       = 0x5F6EF8E9
    SNACK__312                       = 0x5F6EF8EA
    SNACK__313                       = 0x5F6EF8EB
    SNACK__3130                      = 0xD5C96071
    SNACK__31300                     = 0x660C5A03
    SNACK__31301                     = 0x660C5A04
    SNACK__31302                     = 0x660C5A05
    SNACK__31303                     = 0x660C5A06
    SNACK__313030                    = 0x38521142
    SNACK__313031                    = 0x38521143
    SNACK__313032                    = 0x38521144
    SNACK__313033                    = 0x38521145
    SNACK__314                       = 0x5F6EF8EC
    SNACK__32                        = 0x432BD6E9
    SNACK__320                       = 0x5F6EF96B
    SNACK__321                       = 0x5F6EF96C
    SNACK__3211                      = 0xD5C9A275
    SNACK__3213                      = 0xD5C9A277
    SNACK__322                       = 0x5F6EF96D
    SNACK__3220                      = 0xD5C9A2F7
    SNACK__3221                      = 0xD5C9A2F8
    SNACK__3222                      = 0xD5C9A2F9
    SNACK__32220                     = 0x662E659B
    SNACK__32221                     = 0x662E659C
    SNACK__32222                     = 0x662E659D
    SNACK__322220                    = 0x49BDFF87
    SNACK__322221                    = 0x49BDFF88
    SNACK__322222                    = 0x49BDFF89
    SNACK__323                       = 0x5F6EF96E
    SNACK__325                       = 0x5F6EF970
    SNACK__327                       = 0x5F6EF972
    SNACK__329                       = 0x5F6EF974
    SNACK__33                        = 0x432BD6EA
    SNACK__330                       = 0x5F6EF9EE
    SNACK__331                       = 0x5F6EF9EF
    SNACK__332                       = 0x5F6EF9F0
    SNACK__3320                      = 0xD5C9E600
    SNACK__3321                      = 0xD5C9E601
    SNACK__3322                      = 0xD5C9E602
    SNACK__333                       = 0x5F6EF9F1
    SNACK__334                       = 0x5F6EF9F2
    SNACK__340                       = 0x5F6EFA71
    SNACK__341                       = 0x5F6EFA72
    SNACK__3410                      = 0xD5CA2886
    SNACK__342                       = 0x5F6EFA73
    SNACK__343                       = 0x5F6EFA74
    SNACK__344                       = 0x5F6EFA75
    SNACK__345                       = 0x5F6EFA76
    SNACK__346                       = 0x5F6EFA77
    SNACK__347                       = 0x5F6EFA78
    SNACK__348                       = 0x5F6EFA79
    SNACK__349                       = 0x5F6EFA7A
    SNACK__355                       = 0x5F6EFAF9
    SNACK__3550                      = 0xD5CA6D9B
    SNACK__3552                      = 0xD5CA6D9D
    SNACK__3554                      = 0xD5CA6D9F
    SNACK__3556                      = 0xD5CA6DA1
    SNACK__36                        = 0x432BD6ED
    SNACK__361                       = 0x5F6EFB78
    SNACK__363                       = 0x5F6EFB7A
    SNACK__374                       = 0x5F6EFBFE
    SNACK__380                       = 0x5F6EFC7D
    SNACK__381                       = 0x5F6EFC7E
    SNACK__382                       = 0x5F6EFC7F
    SNACK__383                       = 0x5F6EFC80
    SNACK__390                       = 0x5F6EFD00
    SNACK__391                       = 0x5F6EFD01
    SNACK__392                       = 0x5F6EFD02
    SNACK__393                       = 0x5F6EFD03
    SNACK__4                         = 0xB640D2BE
    SNACK__40                        = 0x432BD76A
    SNACK__41                        = 0x432BD76B
    SNACK__42                        = 0x432BD76C
    SNACK__43                        = 0x432BD76D
    SNACK__5                         = 0xB640D2BF
    SNACK__50                        = 0x432BD7ED
    SNACK__51                        = 0x432BD7EE
    SNACK__52                        = 0x432BD7EF
    SNACK__53                        = 0x432BD7F0
    SNACK__530                       = 0x5F6F8000
    SNACK__531                       = 0x5F6F8001
    SNACK__6                         = 0xB640D2C0
    SNACK__60                        = 0x432BD76B
    SNACK__600                       = 0x5F6FC180
    SNACK__602                       = 0x5F6FC182
    SNACK__603                       = 0x5F6FC183
    SNACK__606                       = 0x5F6FC186
    SNACK__608                       = 0x5F6FC188
    SNACK__61                        = 0x432BD76C
    SNACK__666                       = 0x5F6FC498
    SNACK__7                         = 0xB640D2C1
    SNACK__70                        = 0x432BD8F3
    SNACK__700                       = 0x5F700489
    SNACK__701                       = 0x5F70048A
    SNACK__702                       = 0x5F70048B
    SNACK__703                       = 0x5F70048C
    SNACK__704                       = 0x5F70048D
    SNACK__705                       = 0x5F70048E
    SNACK__706                       = 0x5F70048F
    SNACK__71                        = 0x432BD8F4
    SNACK__72                        = 0x432BD8F5
    SNACK__73                        = 0x432BD8F6
    SNACK__74                        = 0x432BD8F7
    SNACK__8                         = 0xB640D2C2
    SNACK__80                        = 0x432BD976
    SNACK__800                       = 0x5F704792
    SNACK__801                       = 0x5F704793
    SNACK__802                       = 0x5F704794
    SNACK__803                       = 0x5F704795
    SNACK__804                       = 0x5F704796
    SNACK__805                       = 0x5F704797
    SNACK__806                       = 0x5F704798
    SNACK__807                       = 0x5F704799
    SNACK__808                       = 0x5F70479A
    SNACK__809                       = 0x5F70479B
    SNACK__81                        = 0x432BD977
    SNACK__9                         = 0xB640D2C3
    SNACK__90                        = 0x432BD9F9
    SNACK__91                        = 0x432BD9FA
    SNACK__BOX__1                    = 0x7168C90A
#    SNACK__BOX__1__MILLION           =
#    SNACK__BOX__10                   =
    SNACK__BOX__2                    = 0x7168C90B
#    SNACK__BOX__BEHIND__MOODY        =
#    SNACK__BOX__IN__SECRET           =
#    SNACK__BOX__LEFT__CORRIDOR       =
#    SNACK__BOX__LEFT__CORRIDOR__2    =
#    SNACK__BOX__OVER__PIT            =
#    SNACK__BOX__OVER__PIT__2         =
    SNACK001                         = 0x433005EF
    SNACK01                          = 0xB640DAEB
    SNACK010                         = 0x43300671
    SNACK011                         = 0x43300672
    SNACK012                         = 0x43300673
    SNACK013                         = 0x43300674
    SNACK014                         = 0x43300675
    SNACK015                         = 0x43300676
    SNACK02                          = 0xB640DAEC
    SNACK020                         = 0x433006F4
    SNACK022                         = 0x433006F6
    SNACK023                         = 0x433006F7
    SNACK03                          = 0xB640DAED
    SNACK030                         = 0x43300777
    SNACK031                         = 0x43300778
    SNACK032                         = 0x43300779
    SNACK040                         = 0x433007FA
    SNACK041                         = 0x433007FB
    SNACK042                         = 0x433007FC
    SNACK043                         = 0x433007FD
    SNACK050                         = 0x4330087D
    SNACK051                         = 0x4330087E
    SNACK052                         = 0x4330087F
    SNACK053                         = 0x43300880
    SNACK0530                        = 0x619459B0
    SNACK05300                       = 0xEEE9E540
    SNACK05301                       = 0xEEE9E541
    SNACK05302                       = 0xEEE9E542
    SNACK07                          = 0xB640DAF1
    SNACK070                         = 0x43300983
    SNACK071                         = 0x43300984
    SNACK08                          = 0xB640DAF2
    SNACK080                         = 0x43300A06
    SNACK081                         = 0x43300A07
    SNACK082                         = 0x43300A08
    SNACK083                         = 0x43300A09
    SNACK09                          = 0xB640DAF3
    SNACK090                         = 0x43300A89
    SNACK091                         = 0x43300A8A
    SNACK092                         = 0x43300A8B
    SNACK093                         = 0x43300A8C
    SNACK0930                        = 0x619565D4
    SNACK09300                       = 0xEF731BAC
    SNACK09301                       = 0xEF731BAD
    SNACK09303                       = 0xEF731BAF
    SNACK09304                       = 0xEF731BB0
    SNACK09305                       = 0xEF731BB1
#    SNACK1                           =
    SNACK10                          = 0xB640DB6D
    SNACK11                          = 0xB640DB6E
    SNACK110                         = 0x4330497A
#    SNACK1101                        =
#    SNACK110101                      =
#    SNACK110103                      =
#    SNACK110105                      =
#    SNACK110107                      =
#    SNACK110109                      =
#    SNACK1103                        =
#    SNACK1105                        =
#    SNACK1107                        =
#    SNACK1109                        =
    SNACK111                         = 0x4330497B
    SNACK112                         = 0x4330497C
    SNACK1120                        = 0x61B59AA4
    SNACK1121                        = 0x61B59AA5
    SNACK11210                       = 0xFFEE229F
    SNACK11211                       = 0xFFEE22A0
    SNACK1122                        = 0x61B59AA6
    SNACK1123                        = 0x61B59AA7
    SNACK1124                        = 0x61B59AA8
    SNACK1125                        = 0x61B59AA9
    SNACK1126                        = 0x61B59AAA
    SNACK1127                        = 0x61B59AAB
    SNACK1128                        = 0x61B59AAC
    SNACK1129                        = 0x61B59AAD
    SNACK113                         = 0x4330497D
    SNACK114                         = 0x4330497E
    SNACK115                         = 0x4330497F
    SNACK116                         = 0x43304980
    SNACK117                         = 0x43304981
    SNACK118                         = 0x43304982
    SNACK119                         = 0x43304983
    SNACK12                          = 0xB640DB6F
    SNACK120                         = 0x433049FD
    SNACK1200                        = 0x615BDCA7
    SNACK12010                       = 0x000FEA28
    SNACK12012                       = 0x000FEA2A
    SNACK12014                       = 0x000FEA2C
    SNACK12016                       = 0x000FEA2E
    SNACK12018                       = 0x000FEA30
    SNACK1202                        = 0x61B5DCA9
    SNACK1204                        = 0x61B5DCAB
    SNACK1206                        = 0x61B5DCAD
    SNACK1208                        = 0x61B5DCAF
    SNACK121                         = 0x433049FE
    SNACK122                         = 0x433049FF
    SNACK123                         = 0x43304A00
    SNACK124                         = 0x43304A01
    SNACK125                         = 0x43304A02
#    SNACK1271                        =
#    SNACK12710                       =
#    SNACK1272                        =
#    SNACK1273                        =
#    SNACK1274                        =
#    SNACK1275                        =
#    SNACK1276                        =
#    SNACK1277                        =
#    SNACK1278                        =
#    SNACK1279                        =
    SNACK13                          = 0xB640DB70
    SNACK130                         = 0x43304A80
    SNACK1300                        = 0x61B61FB0
    SNACK132                         = 0x43304A82
    SNACK133                         = 0x43304A83
    SNACK14                          = 0xB640DB71
    SNACK140                         = 0x43304B03
    SNACK141                         = 0x43304B04
    SNACK142                         = 0x43304B05
    SNACK143                         = 0x43304B06
    SNACK15                          = 0xB640DB72
    SNACK16                          = 0xB640DB73
    SNACK17                          = 0xB640DB74
    SNACK18                          = 0xB640DB75
    SNACK19                          = 0xB640DB76
    SNACK190                         = 0x43304D92
    SNACK191                         = 0x43304D93
    SNACK192                         = 0x43304D94
    SNACK193                         = 0x43304D95
    SNACK194                         = 0x43304D96
    SNACK21                          = 0xB640DBF1
    SNACK210                         = 0x43308C83
    SNACK211                         = 0x43308C84
    SNACK212                         = 0x43308C85
    SNACK213                         = 0x43308C86
    SNACK2130                        = 0x61D7E8C2
    SNACK21300                       = 0x117C1B76
    SNACK21301                       = 0x117C1B77
    SNACK21303                       = 0x117C1B79
    SNACK21304                       = 0x117C1B7A
    SNACK21305                       = 0x117C1B7B
    SNACK240                         = 0x43308E0C
    SNACK241                         = 0x43308E0D
    SNACK242                         = 0x43308E0E
    SNACK243                         = 0x43308E0F
    SNACK26                          = 0xB640DBF6
    SNACK260                         = 0x43308F12
    SNACK261                         = 0x43308F13
    SNACK262                         = 0x43308F14
    SNACK263                         = 0x43308F15
    SNACK264                         = 0x43308F16
    SNACK27                          = 0xB640DBF7
    SNACK270                         = 0x43308F95
    SNACK271                         = 0x43308F96
    SNACK272                         = 0x43308F97
    SNACK273                         = 0x43308F98
    SNACK274                         = 0x43308F99
    SNACK29                          = 0xB640DBF9
    SNACK290                         = 0x4330909B
    SNACK291                         = 0x4330909C
    SNACK293                         = 0x4330909E
    SNACK294                         = 0x4330909F
    SNACK295                         = 0x433090A0
    SNACK296                         = 0x433090A1
    SNACK31                          = 0xB640DC74
    SNACK310                         = 0x4330CF8C
    SNACK311                         = 0x4330CF8D
    SNACK312                         = 0x4330CF8E
    SNACK313                         = 0x4330CF8F
    SNACK314                         = 0x4330CF90
    SNACK315                         = 0x4330CF91
    SNACK32                          = 0xB640DC75
    SNACK320                         = 0x4330D00F
    SNACK321                         = 0x4330D010
    SNACK322                         = 0x4330D011
    SNACK323                         = 0x4330D012
    SNACK324                         = 0x4330D013
    SNACK325                         = 0x4330D014
    SNACK326                         = 0x4330D015
    SNACK33                          = 0xB640DC76
    SNACK330                         = 0x4330D092
    SNACK331                         = 0x4330D093
    SNACK332                         = 0x4330D094
    SNACK333                         = 0x4330D095
    SNACK334                         = 0x4330D096
    SNACK335                         = 0x4330D097
    SNACK35                          = 0xB640DC78
    SNACK36                          = 0xB640DC79
    SNACK360                         = 0x4330D21B
    SNACK361                         = 0x4330D21C
    SNACK362                         = 0x4330D21D
    SNACK363                         = 0x4330D21E
    SNACK364                         = 0x4330D21F
    SNACK365                         = 0x4330D220
    SNACK37                          = 0xB640DC7A
    SNACK370                         = 0x4330D29E
    SNACK371                         = 0x4330D29F
    SNACK372                         = 0x4330D2A0
    SNACK373                         = 0x4330D2A1
    SNACK39                          = 0xB640DC7C
    SNACK390                         = 0x4330D3A4
    SNACK391                         = 0x4330D3A5
    SNACK392                         = 0x4330D3A6
    SNACK393                         = 0x4330D3A7
    SNACK40                          = 0xB640DCF6
    SNACK400                         = 0x43311212
    SNACK401                         = 0x43311213
    SNACK402                         = 0x43311214
    SNACK403                         = 0x43311215
    SNACK404                         = 0x43311216
#    SNACK43                          =
#    SNACK51                          =
#    SNACK52                          =
#    SNACK53                          =
#    SNACK54                          =
#    SNACK55                          =
#    SNACK57                          =
#    SNACK58                          =
#    SNACK59                          =
#    SNACK60                          =
#    SNACK61                          =
#    SNACK62                          =
#    SNACK63                          =
#    SNACK64                          =
#    SNACK65                          =
#    SNACK66                          =
#    SNACK67                          =
#    SNACK68                          =
#    SNACK69                          =
#    SNACK70                          =
#    SNACK71                          =
#    SNACK72                          =
#    SNACK73                          =
#    SNACKBOX                         =
    SNACKBOX__0                      = 0x2E6640CD
    SNACKBOX__1                      = 0x2E6640CE
    SNACKBOX__1__1                   = 0x648E41CF
    SNACKBOX__1__10                  = 0x74EDFAB8
    SNACKBOX__1__11                  = 0x74EDFAB9
    SNACKBOX__1__12                  = 0x74EDFABA
    SNACKBOX__2                      = 0x2E6640CF
    SNACKBOX__2__1                   = 0x648E84D8
    SNACKBOX__2__10                  = 0x74EDFAB8
    SNACKBOX__2__11                  = 0x74EDFAB9
    SNACKBOX__2__12                  = 0x74EDFABA
#    SNACKBOX__2ND__LEVEL__1          =
#    SNACKBOX__2ND__LEVEL__2          =
    SNACKBOX__3                      = 0x2E6640D0
    SNACKBOX__3__1                   = 0x648EC7E1
    SNACKBOX__3__10                  = 0x75104853
    SNACKBOX__3__11                  = 0x75104854
    SNACKBOX__3__12                  = 0x75104855
    SNACKBOX__4                      = 0x2E6640D1
    SNACKBOX__4__1                   = 0x648F0AEA
    SNACKBOX__4__10                  = 0x753295EE
    SNACKBOX__4__11                  = 0x753295EF
    SNACKBOX__4__12                  = 0x753295F0
    SNACKBOX__5                      = 0x2E6640D2
#    SNACKBOX__CHAND__2               =
#    SNACKBOX__FOR__TOKEN2            =
#    SNACKBOX__FOR__TOKEN3            =
#    SNACKBOX__FOR__TOKEN4            =
#    SNACKBOX__FOR__TOKEN5            =
#    SNACKBOX__SECRET__AREA           =
#    SNACKBOX0                        =
#    SNACKBOX00                       =
#    SNACKBOX1                        =
#    SNACKBOX10                       =
#    SNACKBOX11                       =
    SNACKBOX1MILLION                 = 0xCF7E693C
    SNACKBOX1MILLION1                = 0x2DAFD9E5
    SNACKBOX2                        = 0x6404B071
    SNACKBOX3                        = 0x6404B072
#    SNACKBOX30                       =
    SNACKBOX5                        = 0x6404B074
    SNACKS__040                      = 0x5278AD8D
    SNACKS__041                      = 0x5278AD8E
    SNACKS__042                      = 0x5278AD8F
    SS__999                          = 0x412F5051
#    SS01                             =
#    SS010                            =
#    SS0100                           =
#    SS0101                           =
#    SS0102                           =
#    SS0103                           =
#    SS0104                           =
#    SS011                            =
#    SS0110                           =
#    SS0111                           =
#    SS012                            =
#    SS013                            =
#    SS014                            =
#    SS015                            =
#    SS016                            =
#    SS017                            =
#    SS018                            =
#    SS019                            =
#    SS01A                            =
#    SS01A1                           =
#    SS01A3                           =
#    SS01A5                           =
#    SS01A7                           =
#    SS01B                            =
#    SS02                             =
#    SS020                            =
#    SS021                            =
#    SS0210                           =
#    SS0211                           =
#    SS022                            =
#    SS023                            =
#    SS024                            =
#    SS025                            =
#    SS026                            =
#    SS027                            =
#    SS029                            =
#    SS02A                            =
#    SS02A1                           =
#    SS02A3                           =
#    SS02A5                           =
#    SS02A7                           =
#    SS02B                            =
#    SS03                             =
#    SS030                            =
#    SS031                            =
#    SS032                            =
#    SS033                            =
#    SS034                            =
#    SS035                            =
#    SS037                            =
#    SS03A                            =
#    SS03B                            =
#    SS03B1                           =
#    SS03B3                           =
#    SS03B5                           =
#    SS03B7                           =
#    SS04                             =
#    SS040                            =
#    SS041                            =
#    SS0410                           =
#    SS0411                           =
#    SS0412                           =
#    SS042                            =
#    SS043                            =
#    SS045                            =
#    SS047                            =
#    SS048                            =
#    SS049                            =
#    SS04A                            =
#    SS04B                            =
#    SS04B1                           =
#    SS04B3                           =
#    SS04B5                           =
#    SS04B7                           =
#    SS05                             =
#    SS050                            =
#    SS051                            =
#    SS052                            =
#    SS053                            =
#    SS054                            =
#    SS055                            =
#    SS057                            =
#    SS058                            =
#    SS05A                            =
#    SS05B                            =
#    SS06                             =
#    SS061                            =
#    SS0610                           =
#    SS0611                           =
#    SS06110                          =
#    SS06111                          =
#    SS06112                          =
#    SS061130                         =
#    SS061131                         =
#    SS061132                         =
#    SS061133                         =
#    SS0611330                        =
#    SS06113310                       =
#    SS061133100                      =
#    SS0611331010                     =
#    SS0611331011                     =
#    SS0611331012                     =
#    SS0611331013                     =
#    SS06113310130                    =
#    SS0612                           =
#    SS0614                           =
#    SS0615                           =
#    SS06150                          =
#    SS06151                          =
#    SS06152                          =
#    SS06153                          =
#    SS061530                         =
#    SS061531                         =
#    SS061532                         =
#    SS061533                         =
#    SS063                            =
#    SS064                            =
#    SS065                            =
#    SS066                            =
#    SS067                            =
#    SS068                            =
#    SS069                            =
#    SS06A                            =
#    SS06B                            =
#    SS07                             =
#    SS070                            =
#    SS071                            =
#    SS0711                           =
#    SS0713                           =
#    SS0715                           =
#    SS0717                           =
#    SS0719                           =
#    SS072                            =
#    SS0721                           =
#    SS0723                           =
#    SS0725                           =
#    SS073                            =
#    SS075                            =
#    SS077                            =
#    SS079                            =
#    SS07A                            =
#    SS07B                            =
#    SS08                             =
#    SS080                            =
#    SS081                            =
#    SS08A                            =
#    SS08B                            =
#    SS09                             =
#    SS090                            =
#    SS091                            =
#    SS092                            =
#    SS093                            =
#    SS09A                            =
#    SS09B                            =
    SS1                              = 0x0015E695
    SS10                             = 0x0B34FE6F
    SS100                            = 0xBC1E32FD
    SS1000                           = 0x437417A7
    SS1001                           = 0x437417A8
    SS1002                           = 0x437417A9
#    SS10020                          =
#    SS10021                          =
#    SS10022                          =
    SS1003                           = 0x437417AA
#    SS1004                           =
#    SS10040                          =
#    SS1005                           =
#    SS10050                          =
#    SS10051                          =
#    SS1006                           =
#    SS10060                          =
#    SS10061                          =
#    SS1007                           =
#    SS10070                          =
#    SS10071                          =
#    SS1008                           =
#    SS10080                          =
#    SS10081                          =
#    SS10082                          =
#    SS10083                          =
#    SS1009                           =
#    SS10090                          =
#    SS10091                          =
#    SS10092                          =
#    SS10093                          =
    SS101                            = 0xBC1E32FE
#    SS1010                           =
#    SS1011                           =
#    SS1012                           =
#    SS10120                          =
#    SS10121                          =
#    SS10122                          =
#    SS10123                          =
#    SS10124                          =
#    SS10125                          =
    SS102                            = 0xBC1E32FF
#    SS1020                           =
#    SS1021                           =
#    SS1022                           =
#    SS1023                           =
#    SS10230                          =
#    SS10231                          =
#    SS103                            =
#    SS1030                           =
#    SS1031                           =
    SS104                            = 0xBC1E3301
    SS1040                           = 0x437419B3
    SS1041                           = 0x437419B4
    SS1042                           = 0x437419B5
    SS1043                           = 0x437419B6
    SS105                            = 0xBC1E3302
    SS1050                           = 0x43741A36
    SS1051                           = 0x43741A37
    SS1052                           = 0x43741A38
    SS1053                           = 0x43741A39
#    SS106                            =
#    SS1060                           =
#    SS1061                           =
#    SS1062                           =
#    SS1063                           =
#    SS1064                           =
#    SS1065                           =
#    SS107                            =
#    SS1070                           =
#    SS1071                           =
#    SS1072                           =
#    SS108                            =
#    SS1080                           =
#    SS1081                           =
#    SS1082                           =
#    SS109                            =
#    SS1090                           =
#    SS1091                           =
#    SS1092                           =
    SS11                             = 0x0B34FE70
#    SS110                            =
#    SS1100                           =
#    SS11000                          =
#    SS110000                         =
#    SS1100000                        =
#    SS11000000                       =
#    SS1101                           =
#    SS1102                           =
#    SS11020                          =
#    SS11021                          =
#    SS11022                          =
#    SS1103                           =
#    SS1104                           =
#    SS1105                           =
#    SS1106                           =
#    SS1107                           =
#    SS1109                           =
#    SS111                            =
#    SS1110                           =
#    SS1111                           =
#    SS1112                           =
#    SS1113                           =
#    SS11131                          =
#    SS11132                          =
#    SS11133                          =
#    SS111330                         =
#    SS111331                         =
#    SS111332                         =
#    SS111333                         =
#    SS1113330                        =
#    SS1113331                        =
#    SS1113332                        =
#    SS112                            =
#    SS113                            =
#    SS114                            =
#    SS114_COUNT70                    =
#    SS115                            =
#    SS1150                           =
#    SS1151                           =
#    SS1152                           =
#    SS1153                           =
#    SS1154                           =
#    SS1155                           =
#    SS1156                           =
#    SS116                            =
#    SS1163                           =
#    SS117                            =
#    SS119                            =
#    SS11A                            =
    SS12                             = 0x0B34FE71
#    SS120                            =
#    SS121                            =
#    SS1210                           =
#    SS122                            =
#    SS123                            =
#    SS1233                           =
#    SS124                            =
#    SS1240                           =
#    SS1241                           =
#    SS12410                          =
#    SS124100                         =
#    SS124101                         =
#    SS125                            =
#    SS126                            =
#    SS128                            =
#    SS12A                            =
#    SS12B                            =
#    SS13                             =
#    SS130                            =
#    SS131                            =
#    SS132                            =
#    SS133                            =
#    SS134                            =
#    SS135                            =
#    SS136                            =
#    SS13A                            =
#    SS13B                            =
#    SS14                             =
#    SS140                            =
#    SS141                            =
#    SS142                            =
#    SS143                            =
#    SS144                            =
#    SS145                            =
#    SS147                            =
#    SS14B                            =
#    SS15                             =
#    SS150                            =
#    SS1500                           =
#    SS150000                         =
#    SS151                            =
#    SS1510                           =
#    SS152                            =
#    SS1520                           =
#    SS153                            =
#    SS1530                           =
#    SS154                            =
#    SS1540                           =
#    SS155                            =
#    SS157                            =
    SS16                             = 0x0B34FE75
#    SS160                            =
#    SS1600                           =
#    SS161                            =
#    SS162                            =
#    SS16222                          =
#    SS163                            =
#    SS164                            =
#    SS165                            =
#    SS167                            =
#    SS17                             =
#    SS170                            =
#    SS1700                           =
#    SS171                            =
#    SS172                            =
#    SS173                            =
#    SS174                            =
#    SS175                            =
#    SS177                            =
#    SS18                             =
#    SS180                            =
#    SS181                            =
#    SS1811                           =
#    SS182                            =
#    SS183                            =
#    SS184                            =
#    SS185                            =
#    SS1851                           =
#    SS1853                           =
#    SS1855                           =
#    SS1861                           =
#    SS1862                           =
#    SS1863                           =
#    SS187                            =
#    SS189                            =
#    SS1891                           =
#    SS1893                           =
#    SS1895                           =
    SS19                             = 0x0B34FE78
    SS190                            = 0xBC1E3798
    SS191                            = 0xBC1E3799
    SS192                            = 0xBC1E379A
#    SS1920                           =
#    SS1921                           =
    SS193                            = 0xBC1E379B
    SS194                            = 0xBC1E379C
    SS195                            = 0xBC1E379D
#    SS196                            =
#    SS1960                           =
#    SS1961                           =
#    SS1962                           =
#    SS1963                           =
#    SS1964                           =
#    SS1965                           =
    SS1972                           = 0x4376768F
    SS1974                           = 0x43767691
    SS2                              = 0x0015e696
    SS20                             = 0x0B34FEF2
#    SS200                            =
#    SS2000                           =
#    SS20000                          =
#    SS200000                         =
#    SS2000000                        =
#    SS20000000                       =
#    SS200000000                      =
#    SS201                            =
#    SS2010                           =
#    SS2011                           =
#    SS202                            =
#    SS203                            =
#    SS204                            =
#    SS205                            =
#    SS206                            =
#    SS207                            =
#    SS208                            =
#    SS209                            =
    SS21                             = 0x0B34FEF3
#    SS210                            =
#    SS211                            =
#    SS212                            =
#    SS2120                           =
#    SS2121                           =
#    SS21210                          =
#    SS21211                          =
#    SS21212                          =
#    SS21213                          =
#    SS21214                          =
#    SS21215                          =
#    SS21216                          =
#    SS2122                           =
#    SS2123                           =
#    SS2124                           =
#    SS2126                           =
#    SS2129                           =
#    SS213                            =
#    SS214                            =
#    SS215                            =
#    SS216                            =
    SS22                             = 0x0B34FEF4
#    SS220                            =
#    SS221                            =
#    SS222                            =
#    SS2220                           =
#    SS2221                           =
#    SS22210                          =
#    SS22211                          =
#    SS22212                          =
#    SS22213                          =
#    SS22214                          =
#    SS22215                          =
#    SS22216                          =
#    SS22217                          =
#    SS22218                          =
#    SS223                            =
#    SS224                            =
    SS23                             = 0x0B34FEF5
#    SS230                            =
#    SS231                            =
#    SS233                            =
#    SS235                            =
#    SS237                            =
    SS24                             = 0x0B34FEF6
#    SS240                            =
    SS2400                           = 0x43977166
#    SS241                            =
#    SS243                            =
#    SS245                            =
#    SS247                            =
    SS25                             = 0x0B34FEF7
#    SS250                            =
#    SS251                            =
    SS26                             = 0x0B34FEF8
    SS260                            = 0xBC1E7918
#    SS2600                           =
#    SS2601                           =
#    SS2602                           =
#    SS2603                           =
#    SS2604                           =
#    SS2605                           =
#    SS2606                           =
#    SS2607                           =
    SS261                            = 0xBC1E7919
    SS263                            = 0xBC1E791B
    SS265                            = 0xBC1E791D
    SS267                            = 0xBC1E791F
    SS268                            = 0xBC1E7920
    SS2681                           = 0x4397FB91
    SS2683                           = 0x4397FB93
    SS2685                           = 0x4397FB95
    SS2687                           = 0x4397FB97
    SS27                             = 0x0B34FEF9
#    SS270                            =
#    SS271                            =
#    SS2711                           =
#    SS272                            =
    SS274                            = 0xBC1E799F
    SS275                            = 0xBC1E79A0
    SS28                             = 0x0B34FEFA
    SS280                            = 0xBC1E7A1E
#    SS281                            =
    SS29                             = 0x0B34FEFB
#    SS29300                          =
#    SS293020                         =
#    SS2930210                        =
#    SS29302105                       =
    SS3                              = 0x0015e697
    SS30                             = 0x0B34FF75
#    SS300                            =
#    SS301                            =
#    SS3010                           =
#    SS3011                           =
#    SS3012                           =
#    SS3013                           =
#    SS3014                           =
#    SS302                            =
#    SS303                            =
#    SS3030                           =
#    SS3031                           =
#    SS3032                           =
#    SS3033                           =
#    SS3034                           =
#    SS304                            =
#    SS305                            =
    SS31                             = 0x0B34FF76
    SS32                             = 0x0B34FF77
#    SS33                             =
#    SS34                             =
    SS35                             = 0x0B34FF7A
    SS350                            = 0xBC1EBB9E
    SS351                            = 0xBC1EBB9F
    SS352                            = 0xBC1EBBA0
    SS353                            = 0xBC1EBBA1
    SS36                             = 0x0B34FF7B
#    SS360                            =
#    SS361                            =
#    SS362                            =
#    SS363                            =
#    SS364                            =
#    SS365                            =
    SS37                             = 0x0B34FF7C
    SS370                            = 0xBC1EBCA4
    SS371                            = 0xBC1EBCA5
    SS372                            = 0xBC1EBCA6
    SS373                            = 0xBC1EBCA7
    SS38                             = 0x0B34FF7D
    SS380                            = 0xBC1EBD27
    SS381                            = 0xBC1EBD27
    SS382                            = 0xBC1EBD27
    SS383                            = 0xBC1EBD27
    SS384                            = 0xBC1EBD27
    SS385                            = 0xBC1EBD27
    SS386                            = 0xBC1EBD27
    SS387                            = 0xBC1EBD27
#    SS39                             =
    SS4                              = 0x0015e698
    SS40                             = 0x0B34FFF8
#    SS400                            =
#    SS401                            =
#    SS4010                           =
#    SS4011                           =
#    SS40110                          =
#    SS4012                           =
#    SS4014                           =
#    SS4015                           =
#    SS4016                           =
#    SS402                            =
#    SS403                            =
#    SS4030                           =
#    SS40300                          =
#    SS40301                          =
#    SS40302                          =
#    SS40303                          =
#    SS40304                          =
#    SS40305                          =
#    SS40306                          =
#    SS40307                          =
#    SS40308                          =
#    SS40309                          =
#    SS404                            =
#    SS405                            =
#    SS406                            =
#    SS407                            =
#    SS408                            =
#    SS409                            =
    SS41                             = 0x0B34FFF9
    SS42                             = 0x0B34FFFA
    SS43                             = 0x0B34FFFB
#    SS430                            =
#    SS431                            =
#    SS4310                           =
#    SS4311                           =
#    SS43110                          =
#    SS43111                          =
#    SS431110                         =
    SS44                             = 0x0B34FFFC
#    SS45                             =
#    SS46                             =
#    SS47                             =
#    SS470                            =
#    SS471                            =
#    SS472                            =
#    SS473                            =
#    SS48                             =
#    SS480                            =
#    SS481                            =
#    SS482                            =
#    SS483                            =
#    SS484                            =
#    SS49                             =
    SS5                              = 0x0015e699
    SS50                             = 0x0B35007B
#    SS500                            =
#    SS501                            =
#    SS502                            =
#    SS503                            =
#    SS504                            =
#    SS5040                           =
#    SS50400                          =
#    SS50401                          =
#    SS50402                          =
#    SS50403                          =
#    SS50404                          =
#    SS50405                          =
#    SS50406                          =
#    SS50407                          =
#    SS50408                          =
#    SS50409                          =
#    SS505                            =
#    SS506                            =
#    SS508                            =
#    SS509                            =
    SS51                             = 0x0B35007C
    SS511                            = 0xBC1F3FA5
    SS512                            = 0xBC1F3FA6
    SS513                            = 0xBC1F3FA7
    SS52                             = 0x0B35007D
    SS53                             = 0x0B35007E
    SS54                             = 0x0B35007F
#    SS541                            =
#    SS543_COUNT40                    =
#    SS55                             =
    SS550                            = 0xBC1F41B0
    SS551                            = 0xBC1F41B1
    SS5510                           = 0x43FE9DC3
    SS5511                           = 0x43FE9DC4
    SS5512                           = 0x43FE9DC5
    SS552                            = 0xBC1F41B2
    SS553                            = 0xBC1F41B3
    SS554                            = 0xBC1F41B4
    SS555                            = 0xBC1F41B5
    SS556                            = 0xBC1F41B6
    SS557                            = 0xBC1F41B7
    SS558                            = 0xBC1F41B8
    SS559                            = 0xBC1F41B9
#    SS56                             =
#    SS57                             =
#    SS58                             =
#    SS59                             =
    SS6                              = 0x0015e69A
    SS60                             = 0x0B3500FE
    SS600                            = 0xBC1F822A
#    SS6000                           =
    SS601                            = 0xBC1F822B
#    SS602                            =
#    SS6020                           =
#    SS60200                          =
#    SS6021                           =
#    SS6022                           =
#    SS61                             =
#    SS610                            =
#    SS62                             =
#    SS63                             =
#    SS64                             =
#    SS65                             =
#    SS650                            =
#    SS651                            =
#    SS652                            =
#    SS66                             =
#    SS67                             =
#    SS68                             =
#    SS69                             =
#    SS690                            =
#    SS691                            =
#    SS692                            =
    SS7                              = 0x0015e69B
    SS70                             = 0x0B350181
#    SS700                            =
#    SS7000                           =
#    SS701                            =
#    SS702                            =
#    SS71                             =
#    SS72                             =
#    SS73                             =
#    SS730                            =
#    SS732                            =
#    SS74                             =
#    SS75                             =
#    SS76                             =
#    SS77                             =
    SS7741                           = 0x4443C095
    SS77411                          = 0xEEAB8C70
    SS77412                          = 0xEEAB8C71
    SS77413                          = 0xEEAB8C72
    SS774130                         = 0x21C8DE86
    SS77414                          = 0xEEAB8C73
#    SS78                             =
#    SS79                             =
    SS8                              = 0x0015e69C
#    SS80                             =
#    SS800                            =
#    SS801                            =
#    SS802_COUNT50                    =
#    SS803                            =
#    SS804                            =
#    SS805                            =
#    SS81                             =
#    SS82                             =
#    SS83                             =
#    SS84                             =
#    SS85                             =
    SS850                            = 0xBC200ACB
    SS852                            = 0xBC200ACD
    SS854                            = 0xBC200ACF
#    SS86                             =
#    SS87                             =
#    SS88                             =
#    SS89                             =
    SS9                              = 0x0015e69D
#    SS90                             =
#    SS91                             =
#    SS910                            =
    SS9100                           = 0x4486C788
    SS9101                           = 0x4486C789
    SS9102                           = 0x4486C78A
    SS9103                           = 0x4486C78B
    SS9105                           = 0x4486C78D
    SS9106                           = 0x4486C78E
    SS9107                           = 0x4486C78F
    SS9108                           = 0x4486C790
#    SS911                            =
#    SS912                            =
#    SS913                            =
#    SS914                            =
#    SS92                             =
#    SS93                             =
#    SS94                             =
#    SS95                             =
#    SS96                             =
#    SS97                             =
#    SS98                             =
#    SS99                             =
#    SS990                            =
#    SS991                            =
#    SS9910                           =
#    SS9911                           =
#    SS9912                           =
#    SS9913                           =
#    SS9915                           =
#    SS9916                           =
#    SS9918                           =
#    SS99181                          =
#    SS9919                           =
#    SS992                            =
#    SS9921                           =
#    SS9923                           =
#    SS9925                           =
#    SS99251                          =
#    SS993                            =
#    SS994                            =
#    SS995                            =
#    SS996                            =
#    SS997                            =
#    SS998                            =
#    SS999                            =
#    SSBOX01                          =
#    SSBOX02                          =
#    SSBOX03                          =
#    SSBOX03_AIR                      =
#    SSBOX04                          =
#    SSBOX04_AIR                      =
#    SSBOX05                          =
#    SSBOX06                          =
#    SSBOX07                          =
#    SSBOX08                          =
#    SSBOX09                          =
#    SSBOX10                          =
#    SSBOX11                          =
#    SSBOX12                          =
#    SSBOX13                          =
#    SSBOX14                          =
#    SSBOX18                          =
#    SSBOX25                          =
#    SSBOX26                          =
#    SSBOX27                          =
#    SSBOX28                          =
#    SSBOX87                          =
#    SSBOX_GD01A                      =
#    SSBOX_GD01B                      =
#    SSBOX_GD02A                      =
#    SSBOX_GD02B                      =
#    SSCONV                           =
#    SSCONV1                          =
#    SSCONV11                         =
#    SSCONV13                         =
#    SSCONV15                         =
#    SSCONV151                        =
#    SSCONV1511                       =
#    SSCONV1513                       =
#    SSCONV153                        =
#    SSCONV155                        =
#    SSCONV157                        =
#    SSCONV159                        =
#    SSCONV3                          =
#    SSCONV5                          =
#    SSCONV7                          =
#    SSCONV9                          =
#    SSRP01                           =
#    SSRP010                          =
#    SSRP011                          =
#    SSRP01_BOX                       =
#    SSRP02                           =
#    SSRP020                          =
#    SSRP021                          =
#    SSRP03                           =
#    SSRP030                          =
#    SSRP031                          =
#    SSRP04                           =
#    SSRP040                          =
#    SSRP041                          =
#    SSRP05                           =
#    SSRP051                          =
#    SS_BP04                          =
#    SS_BP09                          =
#    SS_BP14                          =
#    SS_BP26                          =
#    SS_BP28                          =
#    SS_BP31                          =
#    SS_BP34                          =
#    SS_BP46                          =
#    SS_BP55                          =
#    SS_BP64                          =
#    SWINGER__SNACK__LINE             =
#    SWINGER__SNACK__LINE0            =
#    SWINGER__SNACK__LINE00           =
#    SWINGER__SNACK__LINE1            =
#    SWINGER__SNACK__LINE10           =
#    SWINGER__SNACK__LINE100          =
#    SWINGER01_SS01                   =
#    SWINGER01_SS010                  =
#    SWINGER01_SS011                  =
#    SWINGER01_SS012                  =
#    SWINGER01_SS013                  =
#    SWINGER01_SS014                  =
#    SWINGER01_SS015                  =
#    SWINGER01_SS016                  =
#    SWINGER01_SS017                  =
#    SWINGER01_SS018                  =
#    SWINGER01_SS019                  =
#    SWINGER02_SS01                   =
#    SWINGER02_SS010                  =
#    SWINGER02_SS011                  =
#    SWINGER02_SS012                  =
#    SWINGER02_SS013                  =
#    SWINGER02_SS014                  =
#    SWINGER02_SS015                  =
#    SWINGER02_SS016                  =
#    SWINGER02_SS017                  =
#    SWINGER02_SS018                  =
#    SWINGER02_SS019                  =
#    SWINGER03_SS01                   =
#    SWINGER03_SS010                  =
#    SWINGER03_SS011                  =
#    SWINGER03_SS012                  =
#    SWINGER03_SS013                  =
#    SWINGER03_SS014                  =
#    SWINGER03_SS015                  =
#    SWINGER03_SS016                  =
#    SWINGER03_SS017                  =
#    SWINGER03_SS018                  =
#    SWINGER03_SS019                  =
#    SWINGER04_SS01                   =
#    SWINGER04_SS010                  =
#    SWINGER04_SS011                  =
#    SWINGER04_SS012                  =
#    SWINGER04_SS013                  =
#    SWINGER04_SS014                  =
#    SWINGER04_SS015                  =
#    SWINGER04_SS016                  =
#    SWINGER04_SS017                  =
#    SWINGER04_SS018                  =
#    SWINGER04_SS019                  =
#    SWINGER10_SS01                   =
#    SWINGER10_SS02                   =
#    SWINGER10_SS03                   =
#    SWINGER10_SS04                   =
#    SWINGER10_SS06                   =
#    SWINGER10_SS07                   =
#    SWINGER10_SS08                   =
#    SWINGER10_SSBOX05                =
#    SWINGER10_SSBOX09                =
#    SWINGER5_SS01                    =
#    SWINGER5_SS02                    =
#    SWINGER5_SS03                    =
#    SWINGER5_SS04                    =
#    SWINGER5_SS06                    =
#    SWINGER5_SS07                    =
#    SWINGER5_SSBOX05                 =
#    SWINGER6_SS01                    =
#    SWINGER6_SS02                    =
#    SWINGER6_SS03                    =
#    SWINGER6_SS04                    =
#    SWINGER6_SS06                    =
#    SWINGER6_SS07                    =
#    SWINGER6_SSBOX05                 =
#    SWINGER7_SS01                    =
#    SWINGER7_SS02                    =
#    SWINGER7_SS03                    =
#    SWINGER7_SS04                    =
#    SWINGER7_SS06                    =
#    SWINGER7_SS07                    =
#    SWINGER7_SSBOX05                 =
#    SWINGER8_SS01                    =
#    SWINGER8_SS02                    =
#    SWINGER8_SS03                    =
#    SWINGER8_SS04                    =
#    SWINGER8_SS06                    =
#    SWINGER8_SS07                    =
#    SWINGER8_SSBOX05                 =
#    SWINGER9_SS01                    =
#    SWINGER9_SS02                    =
#    SWINGER9_SS03                    =
#    SWINGER9_SS04                    =
#    SWINGER9_SS06                    =
#    SWINGER9_SS07                    =
#    SWINGER9_SSBOX05                 =
#    TUNNEL__SNACK__BOX               =
#    UPPERDECK_SSBOX04                =
#    UPPERDECK_SSBOX06                =
#    UPPER_SS01                       =
#    UPPER_SS02                       =
#    UPPER_SS03                       =
#    UPPER_SS04                       =
#    UPPER_SS05                       =
#    UPPER_SS06                       =
#    UPPER_SS08                       =
#    UPPER_SS09                       =
#    UPPER_SS10                       =
#    URN__1__PRIZE                    =
#    URN__2__PRIZE                    =


base_id = 1495000

UPGRADES_PICKUP_IDS = {
    (base_id + 0): (b'W028', Upgrades.GumPower.value),
    (base_id + 1): (b'B004', Upgrades.SoapPower.value),
    (base_id + 2): (b'O008', Upgrades.BootsPower.value),
    (base_id + 3): (b'P003', Upgrades.PlungerPower.value),
    (base_id + 4): (b'E002', Upgrades.SlippersPower.value),
    (base_id + 5): (b'E002', Upgrades.LampshadePower.value),
    (base_id + 6): (b'R004', Upgrades.BlackKnightPower.value),
    (base_id + 7): (b'F010', Upgrades.SpringPower.value),
    (base_id + 8): (b'L017', Upgrades.PoundPower.value),
    (base_id + 9): (b'E009', Upgrades.HelmetPower.value),
    (base_id + 10): (b'G009', Upgrades.UmbrellaPower.value),
    (base_id + 11): (b'H001', Upgrades.ShovelPower.value),
    (base_id + 12): (b'C007', Upgrades.ShockwavePower.value),
    (base_id + 13): (b'C003', Upgrades.GumPack.value),
    (base_id + 14): (b'L011', Upgrades.GumMaxAmmo.value),
    (base_id + 15): (b'F003', Upgrades.GumUpgrade.value),
    (base_id + 16): (b'S005', Upgrades.GumOverAcid2.value),
    (base_id + 17): (b'O001', Upgrades.Gum_Upgrade.value),
    (base_id + 18): (b'G006', Upgrades.GumPack.value),
    (base_id + 19): (b'R020', Upgrades.BubblePack.value),
    (base_id + 20): (b'E007', Upgrades.SoapBox1.value),
    (base_id + 21): (b'G003', Upgrades.Soap__Box.value),
    (base_id + 22): (b'R005', Upgrades.SoapPack.value),
    (base_id + 23): (b'R021', Upgrades.SoapPack.value),
    (base_id + 24): (b'L019', Upgrades.SoapBox.value),
    (base_id + 25): (b'S005', Upgrades.SoapOverAcid2.value),
    (base_id + 26): (b'W023', Upgrades.SoapBox.value),
    (base_id + 27): (b'F001', Upgrades.Soap_Box.value),
}

MONSTERTOKENS_PICKUP_IDS = {
    (base_id + 100 + 0): (b'O001', MonsterTokens.MT_BLACKKNIGHT.value),
    (base_id + 100 + 1): (b'W022', MonsterTokens.MT_MOODY.value),
    (base_id + 100 + 2): (b'L013', MonsterTokens.MT_CAVEMAN.value),
    (base_id + 100 + 3): (b'O002', MonsterTokens.MT_CREEPER.value),
    (base_id + 100 + 4): (b'H002', MonsterTokens.MT_GARGOYLE.value),
    (base_id + 100 + 5): (b'I005', MonsterTokens.MT_GERONIMO.value),
    (base_id + 100 + 6): (b'G005', MonsterTokens.MT_GHOST.value),
    (base_id + 100 + 7): (b'F007', MonsterTokens.MT_GHOSTDIVER.value),
    (base_id + 100 + 8): (b'C005', MonsterTokens.MT_GREENGHOST.value),
    (base_id + 100 + 9): (b'I001', MonsterTokens.MT_HEADLESS.value),
    (base_id + 100 + 10): (b'S003', MonsterTokens.MT_MASTERMIND.value),
    (base_id + 100 + 11): (b'S002', MonsterTokens.MT_ROBOT.value),
    (base_id + 100 + 12): (b'W025', MonsterTokens.MT_REDBEARD.value),
    (base_id + 100 + 13): (b'G008', MonsterTokens.MT_SCARECROW.value),
    (base_id + 100 + 14): (b'L014', MonsterTokens.MT_SEACREATURE.value),
    (base_id + 100 + 15): (b'B001', MonsterTokens.MT_SPACEKOOK.value),
    (base_id + 100 + 16): (b'F004', MonsterTokens.MT_TARMONSTER.value),
    (base_id + 100 + 17): (b'E003', MonsterTokens.MT_WITCH.value),
    (base_id + 100 + 18): (b'R020', MonsterTokens.MT_WITCHDOC.value),
    (base_id + 100 + 19): (b'E001', MonsterTokens.MT_WOLFMAN.value),
    (base_id + 100 + 20): (b'G002', MonsterTokens.MT_ZOMBIE.value),
}

KEYS_PICKUP_IDS = {
    # +3
    (base_id + 200 + 0): (b'B002', Keys.KEY1.value),
    (base_id + 200 + 1): (b'B002', Keys.KEY2.value),
    (base_id + 200 + 2): (b'B002', Keys.KEY3.value),

    # +4
    (base_id + 200 + 3): (b'B003', Keys.KEY1.value),
    (base_id + 200 + 4): (b'B003', Keys.KEY2.value),
    (base_id + 200 + 5): (b'B003', Keys.KEY3.value),
    (base_id + 200 + 6): (b'B003', Keys.KEY4.value),

    # +5
    (base_id + 200 + 7): (b'C005', Keys.KEY_1.value),
    (base_id + 200 + 8): (b'C005', Keys.KEY_2.value),
    (base_id + 200 + 9): (b'C005', Keys.KEY_3.value),
    (base_id + 200 + 10): (b'C005', Keys.KEY_4.value),

    # +6
    (base_id + 200 + 11): (b'F005', Keys.KEY01.value),
    (base_id + 200 + 12): (b'F005', Keys.KEY02.value),
    (base_id + 200 + 13): (b'F005', Keys.KEY03.value),
    (base_id + 200 + 14): (b'F005', Keys.KEY04.value),

    # +7
    (base_id + 200 + 15): (b'G001', Keys.KEY_01.value),
    (base_id + 200 + 16): (b'G001', Keys.KEY_02.value),
    (base_id + 200 + 17): (b'G001', Keys.KEY_03.value),

    # +8
    (base_id + 200 + 18): (b'G007', Keys.KEY.value),

    # +9
    (base_id + 200 + 19): (b'G009', Keys.KEY_1.value),
    (base_id + 200 + 20): (b'G009', Keys.KEY_2.value),

    # +1
    (base_id + 200 + 21): (b'H001', Keys.HEDGE_KEY.value),

    # +2
    (base_id + 200 + 22): (b'H001', Keys.DUG_FISHING_KEY.value),

    # +0
    (base_id + 200 + 23): (b'I001', Keys.KEY.value),

    # +10
    (base_id + 200 + 24): (b'I003', Keys.DOORKEY.value),

    # +11
    (base_id + 200 + 25): (b'I005', Keys.DOORKEY1.value),
    (base_id + 200 + 26): (b'I005', Keys.DOORKEY2.value),
    (base_id + 200 + 27): (b'I005', Keys.DOORKEY3.value),
    (base_id + 200 + 28): (b'I005', Keys.DOORKEY4.value),

    # +12
    (base_id + 200 + 29): (b'L011', Keys.KEY01.value),
    (base_id + 200 + 30): (b'L011', Keys.KEY02.value),
    (base_id + 200 + 31): (b'L011', Keys.KEY03.value),
    (base_id + 200 + 32): (b'L011', Keys.KEY04.value),

    # +13
    (base_id + 200 + 33): (b'O003', Keys.KEY1.value),
    (base_id + 200 + 34): (b'O003', Keys.KEY2.value),
    (base_id + 200 + 35): (b'O003', Keys.KEY3.value),

    # +14
    (base_id + 200 + 36): (b'O006', Keys.KEY1.value),
    (base_id + 200 + 37): (b'O006', Keys.KEY2.value),
    (base_id + 200 + 38): (b'O006', Keys.KEY3.value),
    (base_id + 200 + 39): (b'O006', Keys.KEY4.value),

    # +15
    (base_id + 200 + 40): (b'P002', Keys.KEY1.value),
    (base_id + 200 + 41): (b'P002', Keys.KEY2.value),
    (base_id + 200 + 42): (b'P002', Keys.KEY3.value),
    (base_id + 200 + 43): (b'P002', Keys.KEY4.value),
    (base_id + 200 + 44): (b'P002', Keys.KEY5.value),

    # +16
    (base_id + 200 + 45): (b'P003', Keys.KEY1.value),
    (base_id + 200 + 46): (b'P003', Keys.KEY2.value),
    (base_id + 200 + 47): (b'P003', Keys.KEY3.value),

    # +17
    (base_id + 200 + 48): (b'P004', Keys.KEY1.value),

    # +18
    (base_id + 200 + 49): (b'P005', Keys.KEY1.value),
    (base_id + 200 + 50): (b'P005', Keys.KEY2.value),
    (base_id + 200 + 51): (b'P005', Keys.KEY3.value),
    (base_id + 200 + 52): (b'P005', Keys.KEY4.value),

    # +19
    (base_id + 200 + 53): (b'R005', Keys.KEY1.value),
    (base_id + 200 + 54): (b'R005', Keys.KEY2.value),
    (base_id + 200 + 55): (b'R005', Keys.KEY3.value),

    # 20
    (base_id + 200 + 56): (b'W027', Keys.KEY01.value),
    (base_id + 200 + 57): (b'W027', Keys.KEY02.value),
    (base_id + 200 + 58): (b'W027', Keys.KEY03.value),
    (base_id + 200 + 59): (b'W027', Keys.KEY04.value),
}

WARPGATE_PICKUP_IDS = {
    (base_id + 300 + 0): (b'B004', Warpgates.WARP_GATE.value),
    (base_id + 300 + 1): (b'C004', Warpgates.WARPPOINT.value),
    (base_id + 300 + 2): (b'E004', Warpgates.WARPPOINT.value),
    (base_id + 300 + 3): (b'E006', Warpgates.WARPPOINT.value),
    (base_id + 300 + 4): (b'E009', Warpgates.WARPPOINT.value),
    (base_id + 300 + 5): (b'F003', Warpgates.WARPPOINT.value),
    (base_id + 300 + 6): (b'F007', Warpgates.WARPPOINT.value),
    (base_id + 300 + 7): (b'O001', Warpgates.WARPPOINT.value),
    (base_id + 300 + 8): (b'G005', Warpgates.WARPPOINT.value),
    (base_id + 300 + 9): (b'G008', Warpgates.WARPPOINT.value),
    (base_id + 300 + 11): (b'I003', Warpgates.WARPPOINT.value),
    (base_id + 300 + 12): (b'I006', Warpgates.WARPPOINT.value),
    (base_id + 300 + 13): (b'L014', Warpgates.WARPPOINT.value),
    (base_id + 300 + 14): (b'L018', Warpgates.WARPPOINT.value),
    (base_id + 300 + 15): (b'O004', Warpgates.WARPPOINT.value),
    (base_id + 300 + 16): (b'O006', Warpgates.WARPPOINT.value),
    (base_id + 300 + 17): (b'P003', Warpgates.WARP_GATE.value),
    (base_id + 300 + 18): (b'P005', Warpgates.WARPPOINT.value),
    (base_id + 300 + 19): (b'R003', Warpgates.WARPPOINT.value),
    (base_id + 300 + 20): (b'S002', Warpgates.WARPPOINT.value),
    (base_id + 300 + 21): (b'W022', Warpgates.WARPPOINT.value),
    (base_id + 300 + 22): (b'W026', Warpgates.WARPPOINT.value),
    (base_id + 300 + 23): (b'L015', Warpgates.WARPPOINT.value),
    (base_id + 300 + 24): (b'G001', Warpgates.WARPPOINT.value),
    (base_id + 300 + 25): (b'H003', Warpgates.WARPGATE_POWERUP.value),
}

SNACK_PICKUP_IDS = {
    (base_id + 400 + 0): (b'B001', Snacks.SS1.value),
    (base_id + 400 + 1): (b'B001', Snacks.SS2.value),
    (base_id + 400 + 2): (b'B001', Snacks.SS3.value),
    (base_id + 400 + 3): (b'B001', Snacks.SS4.value),
    (base_id + 400 + 4): (b'B001', Snacks.SS5.value),
    (base_id + 400 + 5): (b'B001', Snacks.SS6.value),
    (base_id + 400 + 6): (b'B001', Snacks.SS7.value),
    (base_id + 400 + 7): (b'B001', Snacks.SS8.value),
    (base_id + 400 + 8): (b'B001', Snacks.SS9.value),
    (base_id + 400 + 9): (b'B001', Snacks.SS10.value),
    (base_id + 400 + 10): (b'B001', Snacks.SS11.value),
    (base_id + 400 + 11): (b'B001', Snacks.SS12.value),
    (base_id + 400 + 12): (b'B001', Snacks.SS19.value),
    (base_id + 400 + 13): (b'B001', Snacks.SS190.value),
    (base_id + 400 + 14): (b'B001', Snacks.SS191.value),
    (base_id + 400 + 15): (b'B001', Snacks.EX__CLUE__SNACKBOX4.value),
    (base_id + 400 + 16): (b'B001', Snacks.HIGH__SNACKBOX__1.value),
    (base_id + 400 + 17): (b'B001', Snacks.HIGH__SNACKBOX__10.value),
    (base_id + 400 + 18): (b'B001', Snacks.EX__CLUE__SNACKBOX2.value),
    (base_id + 400 + 19): (b'B001', Snacks.EX__CLUE__SNACKBOX3.value),         # Accessed from B003
    (base_id + 400 + 20): (b'B001', Snacks.EX__CLUE__SNACKBOX30.value),
    (base_id + 400 + 21): (b'B001', Snacks.EX__CLUE__SNACKBOX300.value),
    (base_id + 400 + 22): (b'B001', Snacks.EX__CLUE__SNACKBOX3000.value),

    (base_id + 400 + 23): (b'B002', Snacks.SNACK10.value),
    (base_id + 400 + 24): (b'B002', Snacks.SNACK1200.value),
    (base_id + 400 + 25): (b'B002', Snacks.SNACK12.value),
    (base_id + 400 + 26): (b'B002', Snacks.SNACK1202.value),
    (base_id + 400 + 27): (b'B002', Snacks.SNACK14.value),
    (base_id + 400 + 28): (b'B002', Snacks.SNACK1204.value),
    (base_id + 400 + 29): (b'B002', Snacks.SNACK16.value),
    (base_id + 400 + 30): (b'B002', Snacks.SNACK1206.value),
    (base_id + 400 + 31): (b'B002', Snacks.SNACK18.value),
    (base_id + 400 + 32): (b'B002', Snacks.SNACK1208.value),
    (base_id + 400 + 33): (b'B002', Snacks.SNACK110.value),
    (base_id + 400 + 34): (b'B002', Snacks.SNACK12010.value),
    (base_id + 400 + 35): (b'B002', Snacks.SNACK112.value),
    (base_id + 400 + 36): (b'B002', Snacks.SNACK12012.value),
    (base_id + 400 + 37): (b'B002', Snacks.SNACK114.value),
    (base_id + 400 + 38): (b'B002', Snacks.SNACK12014.value),
    (base_id + 400 + 39): (b'B002', Snacks.SNACK116.value),
    (base_id + 400 + 40): (b'B002', Snacks.SNACK12016.value),
    (base_id + 400 + 41): (b'B002', Snacks.SNACK118.value),
    (base_id + 400 + 42): (b'B002', Snacks.SNACK12018.value),
    (base_id + 400 + 43): (b'B002', Snacks.SS4.value),                      # Snacks in the air
    (base_id + 400 + 44): (b'B002', Snacks.EX__CLUE__SNACKBOX__2.value),
    (base_id + 400 + 45): (b'B002', Snacks.SS601.value),
    (base_id + 400 + 46): (b'B002', Snacks.SS60.value),
    (base_id + 400 + 47): (b'B002', Snacks.SS6.value),
    (base_id + 400 + 48): (b'B002', Snacks.SS600.value),
    (base_id + 400 + 49): (b'B002', Snacks.EX__CLUE__SNACKBOX__3.value),
    (base_id + 400 + 50): (b'B002', Snacks.EX__CLUE__SNACKBOX__1.value),

    (base_id + 400 + 51): (b'B003', Snacks.SS513.value),
    (base_id + 400 + 52): (b'B003', Snacks.SS512.value),
    (base_id + 400 + 53): (b'B003', Snacks.SS511.value),
    (base_id + 400 + 54): (b'B003', Snacks.SS5.value),
    (base_id + 400 + 55): (b'B003', Snacks.SS50.value),
    (base_id + 400 + 56): (b'B003', Snacks.SS51.value),
    (base_id + 400 + 57): (b'B003', Snacks.SS52.value),
    (base_id + 400 + 58): (b'B003', Snacks.SS53.value),
    (base_id + 400 + 59): (b'B003', Snacks.SS54.value),
    (base_id + 400 + 60): (b'B003', Snacks.SNACKBOX1MILLION1.value),
    (base_id + 400 + 61): (b'B003', Snacks.SS7741.value),
    (base_id + 400 + 62): (b'B003', Snacks.SS774130.value),
    (base_id + 400 + 63): (b'B003', Snacks.SS77411.value),
    (base_id + 400 + 64): (b'B003', Snacks.SS77412.value),
    (base_id + 400 + 65): (b'B003', Snacks.SS77413.value),
    (base_id + 400 + 66): (b'B003', Snacks.SS77414.value),
    (base_id + 400 + 67): (b'B003', Snacks.SS850.value),
    (base_id + 400 + 68): (b'B003', Snacks.SS852.value),
    (base_id + 400 + 69): (b'B003', Snacks.SS854.value),
    (base_id + 400 + 70): (b'B003', Snacks.SS43.value),
    (base_id + 400 + 71): (b'B003', Snacks.SS36.value),
    (base_id + 400 + 72): (b'B003', Snacks.SS32.value),
    (base_id + 400 + 73): (b'B003', Snacks.SS31.value),
    (base_id + 400 + 74): (b'B003', Snacks.SS30.value),
    (base_id + 400 + 75): (b'B003', Snacks.SS29.value),
    (base_id + 400 + 76): (b'B003', Snacks.SNACKBOX1MILLION.value),
    (base_id + 400 + 77): (b'B003', Snacks.SS__999.value),                  # Helmet Needed
    (base_id + 400 + 78): (b'B003', Snacks.EX__CLUE__SNACKBOX3.value),
    (base_id + 400 + 79): (b'B003', Snacks.SS190.value),
    (base_id + 400 + 80): (b'B003', Snacks.SS191.value),
    (base_id + 400 + 81): (b'B003', Snacks.SS192.value),
    (base_id + 400 + 82): (b'B003', Snacks.EX__CLUE__SNACKBOX5.value),
    (base_id + 400 + 83): (b'B003', Snacks.SS1972.value),
    (base_id + 400 + 84): (b'B003', Snacks.SS1974.value),
    (base_id + 400 + 85): (b'B003', Snacks.EX__CLUE__SNACKBOX4.value),

    (base_id + 400 + 86): (b'B004', Snacks.SS6.value),
    (base_id + 400 + 87): (b'B004', Snacks.SS7.value),
    (base_id + 400 + 88): (b'B004', Snacks.SS70.value),
    (base_id + 400 + 89): (b'B004', Snacks.SS24.value),
    (base_id + 400 + 90): (b'B004', Snacks.SNACKBOX3.value),
    (base_id + 400 + 91): (b'B004', Snacks.SS5.value),
    (base_id + 400 + 92): (b'B004', Snacks.SS1.value),
    (base_id + 400 + 93): (b'B004', Snacks.SS8.value),
    (base_id + 400 + 94): (b'B004', Snacks.SS2400.value),
    (base_id + 400 + 95): (b'B004', Snacks.SS4.value),
    (base_id + 400 + 96): (b'B004', Snacks.SS2.value),
    (base_id + 400 + 97): (b'B004', Snacks.SS3.value),
    (base_id + 400 + 98): (b'B004', Snacks.SNACKBOX5.value),
    (base_id + 400 + 99): (b'B004', Snacks.SS6.value),
    (base_id + 400 + 100): (b'B004', Snacks.SS9.value),
    (base_id + 400 + 101): (b'B004', Snacks.SS10.value),
    (base_id + 400 + 102): (b'B004', Snacks.SNACK10.value),  #Soap Area
    (base_id + 400 + 103): (b'B004', Snacks.SNACK12.value),
    (base_id + 400 + 104): (b'B004', Snacks.SNACK14.value),
    (base_id + 400 + 105): (b'B004', Snacks.SNACK16.value),
    (base_id + 400 + 106): (b'B004', Snacks.SNACK18.value),
    (base_id + 400 + 107): (b'B004', Snacks.SNACK110.value),
    (base_id + 400 + 108): (b'B004', Snacks.SNACK1120.value),
    (base_id + 400 + 109): (b'B004', Snacks.SNACK1122.value),
    (base_id + 400 + 110): (b'B004', Snacks.SNACK1124.value),
    (base_id + 400 + 111): (b'B004', Snacks.SNACK1126.value),
    (base_id + 400 + 112): (b'B004', Snacks.SNACK1128.value),
    (base_id + 400 + 113): (b'B004', Snacks.SNACK11210.value),
    (base_id + 400 + 114): (b'B004', Snacks.SS20.value),
    (base_id + 400 + 115): (b'B004', Snacks.SS21.value),
    (base_id + 400 + 116): (b'B004', Snacks.SS22.value),
    (base_id + 400 + 117): (b'B004', Snacks.SS23.value),
    (base_id + 400 + 118): (b'B004', Snacks.SNACKBOX2.value),
    (base_id + 400 + 119): (b'B004', Snacks.DRYER__SNACKBOX__1.value),
    (base_id + 400 + 120): (b'B004', Snacks.DRYER__SNACKBOX__2.value),

    (base_id + 400 + 121): (b'C001', Snacks.SS2.value),
    (base_id + 400 + 122): (b'C001', Snacks.SS20.value),
    (base_id + 400 + 123): (b'C001', Snacks.SS21.value),
    (base_id + 400 + 124): (b'C001', Snacks.SS42.value),
    (base_id + 400 + 125): (b'C001', Snacks.SS23.value),
    (base_id + 400 + 126): (b'C001', Snacks.SS24.value),
    (base_id + 400 + 127): (b'C001', Snacks.SS3.value),
    (base_id + 400 + 128): (b'C001', Snacks.SS4.value),
    (base_id + 400 + 129): (b'C001', Snacks.SS40.value),
    (base_id + 400 + 130): (b'C001', Snacks.SS41.value),
    (base_id + 400 + 131): (b'C001', Snacks.SNACK__1.value),
    (base_id + 400 + 132): (b'C001', Snacks.SS43.value),
    (base_id + 400 + 133): (b'C001', Snacks.SS44.value),
    (base_id + 400 + 134): (b'C001', Snacks.SS5.value),
    (base_id + 400 + 135): (b'C001', Snacks.SS100.value),
    (base_id + 400 + 136): (b'C001', Snacks.SS1000.value),
    (base_id + 400 + 137): (b'C001', Snacks.SS1001.value),
    (base_id + 400 + 138): (b'C001', Snacks.SS1002.value),
    (base_id + 400 + 139): (b'C001', Snacks.SS1003.value),
    (base_id + 400 + 140): (b'C001', Snacks.SS101.value),
    (base_id + 400 + 141): (b'C001', Snacks.SS102.value),
    (base_id + 400 + 142): (b'C001', Snacks.BOX__OF__SNACKS__3.value),
    (base_id + 400 + 143): (b'C001', Snacks.SS104.value),
    (base_id + 400 + 144): (b'C001', Snacks.SS1040.value),
    (base_id + 400 + 145): (b'C001', Snacks.SS1041.value),
    (base_id + 400 + 146): (b'C001', Snacks.SS1042.value),
    (base_id + 400 + 147): (b'C001', Snacks.SS1043.value),  #Helmet
    (base_id + 400 + 148): (b'C001', Snacks.SS550.value),
    (base_id + 400 + 149): (b'C001', Snacks.SS551.value),
    (base_id + 400 + 150): (b'C001', Snacks.SS552.value),
    (base_id + 400 + 151): (b'C001', Snacks.SS553.value),
    (base_id + 400 + 152): (b'C001', Snacks.SS554.value),
    (base_id + 400 + 153): (b'C001', Snacks.SS555.value),
    (base_id + 400 + 154): (b'C001', Snacks.SS556.value),
    (base_id + 400 + 155): (b'C001', Snacks.SS557.value),
    (base_id + 400 + 156): (b'C001', Snacks.SS558.value),
    (base_id + 400 + 157): (b'C001', Snacks.SS559.value),
    (base_id + 400 + 158): (b'C001', Snacks.SS5510.value),
    (base_id + 400 + 159): (b'C001', Snacks.SS5511.value),
    (base_id + 400 + 160): (b'C001', Snacks.SS5512.value),
    (base_id + 400 + 161): (b'C001', Snacks.SS16.value),
    (base_id + 400 + 162): (b'C001', Snacks.BOX__OF__SNACKS__2.value),
    (base_id + 400 + 163): (b'C001', Snacks.SS19.value),
    (base_id + 400 + 164): (b'C001', Snacks.SS190.value),
    (base_id + 400 + 165): (b'C001', Snacks.SS191.value),
    (base_id + 400 + 166): (b'C001', Snacks.SS192.value),
    (base_id + 400 + 167): (b'C001', Snacks.SS193.value),
    (base_id + 400 + 168): (b'C001', Snacks.SS194.value),
    (base_id + 400 + 169): (b'C001', Snacks.SS195.value),
    (base_id + 400 + 170): (b'C001', Snacks.SS22.value),
    (base_id + 400 + 171): (b'C001', Snacks.SS274.value),
    (base_id + 400 + 172): (b'C001', Snacks.SS275.value),
    (base_id + 400 + 173): (b'C001', Snacks.SS28.value),
    (base_id + 400 + 174): (b'C001', Snacks.SS280.value),
    (base_id + 400 + 175): (b'C001', Snacks.SS29.value),
    (base_id + 400 + 176): (b'C001', Snacks.BOX__OF__SNACKS__4.value),
    (base_id + 400 + 177): (b'C001', Snacks.SS387.value),
    (base_id + 400 + 178): (b'C001', Snacks.SS386.value),
    (base_id + 400 + 179): (b'C001', Snacks.SS385.value),
    (base_id + 400 + 180): (b'C001', Snacks.SS384.value),
    (base_id + 400 + 181): (b'C001', Snacks.SS383.value),
    (base_id + 400 + 182): (b'C001', Snacks.SS382.value),
    (base_id + 400 + 183): (b'C001', Snacks.SS381.value),
    (base_id + 400 + 184): (b'C001', Snacks.SS380.value),
    (base_id + 400 + 185): (b'C001', Snacks.SS38.value),
    (base_id + 400 + 186): (b'C001', Snacks.SS35.value),
    (base_id + 400 + 187): (b'C001', Snacks.SS350.value),
    (base_id + 400 + 188): (b'C001', Snacks.SS351.value),
    (base_id + 400 + 189): (b'C001', Snacks.SS352.value),
    (base_id + 400 + 190): (b'C001', Snacks.SS353.value),
    (base_id + 400 + 191): (b'C001', Snacks.SS36.value),
    (base_id + 400 + 192): (b'C001', Snacks.SS373.value),
    (base_id + 400 + 193): (b'C001', Snacks.SS372.value),
    (base_id + 400 + 194): (b'C001', Snacks.SS371.value),
    (base_id + 400 + 195): (b'C001', Snacks.SS370.value),
    (base_id + 400 + 196): (b'C001', Snacks.SS37.value),
    (base_id + 400 + 197): (b'C001', Snacks.SS1053.value),
    (base_id + 400 + 198): (b'C001', Snacks.SS1052.value),
    (base_id + 400 + 199): (b'C001', Snacks.SS1051.value),
    (base_id + 400 + 200): (b'C001', Snacks.SS1050.value),
    (base_id + 400 + 201): (b'C001', Snacks.SS105.value),

    (base_id + 400 + 202): (b'C002', Snacks.SNACK__01.value),
    (base_id + 400 + 203): (b'C002', Snacks.SNACK__02.value),
    (base_id + 400 + 204): (b'C002', Snacks.SNACK__03.value),
    (base_id + 400 + 205): (b'C002', Snacks.SNACK__04.value),
    (base_id + 400 + 206): (b'C002', Snacks.BOX__OF__SNACKS__1.value),
    (base_id + 400 + 207): (b'C002', Snacks.SNACK__06.value),
    (base_id + 400 + 208): (b'C002', Snacks.SNACK__07.value),
    (base_id + 400 + 209): (b'C002', Snacks.SNACK__08.value),
    (base_id + 400 + 210): (b'C002', Snacks.SNACK__09.value),
    (base_id + 400 + 211): (b'C002', Snacks.SNACK__10.value),
    (base_id + 400 + 212): (b'C002', Snacks.SNACK__112.value),
    (base_id + 400 + 213): (b'C002', Snacks.SNACK__111.value),
    (base_id + 400 + 214): (b'C002', Snacks.SNACK__110.value),
    (base_id + 400 + 215): (b'C002', Snacks.SNACK__11.value),
    (base_id + 400 + 216): (b'C002', Snacks.SNACK__12.value),
    (base_id + 400 + 217): (b'C002', Snacks.SNACK__13.value),
    (base_id + 400 + 218): (b'C002', Snacks.SNACK__14.value),
    (base_id + 400 + 219): (b'C002', Snacks.SNACK__15.value),
    (base_id + 400 + 220): (b'C002', Snacks.SNACK__150.value),
    (base_id + 400 + 221): (b'C002', Snacks.SNACK__151.value),
    (base_id + 400 + 222): (b'C002', Snacks.SNACK__152.value),
    (base_id + 400 + 223): (b'C002', Snacks.SNACK__153.value),
    (base_id + 400 + 224): (b'C002', Snacks.SNACK__154.value),
    (base_id + 400 + 225): (b'C002', Snacks.SNACK__155.value),
    (base_id + 400 + 226): (b'C002', Snacks.SNACK__156.value),
    (base_id + 400 + 227): (b'C002', Snacks.SNACK__157.value),
    (base_id + 400 + 228): (b'C002', Snacks.SNACK__158.value),
    (base_id + 400 + 229): (b'C002', Snacks.SNACK__159.value),
    (base_id + 400 + 230): (b'C002', Snacks.SNACK__165.value),
    (base_id + 400 + 231): (b'C002', Snacks.SNACK__164.value),
    (base_id + 400 + 232): (b'C002', Snacks.SNACK__163.value),
    (base_id + 400 + 233): (b'C002', Snacks.SNACK__162.value),
    (base_id + 400 + 234): (b'C002', Snacks.SNACK__161.value),
    (base_id + 400 + 235): (b'C002', Snacks.SNACK__160.value),
    (base_id + 400 + 236): (b'C002', Snacks.SNACK__16.value),
    (base_id + 400 + 237): (b'C002', Snacks.SNACK__17.value),
    (base_id + 400 + 238): (b'C002', Snacks.SNACK__18.value),
    (base_id + 400 + 239): (b'C002', Snacks.SNACK__19.value),
    (base_id + 400 + 240): (b'C002', Snacks.SNACK__20.value),
    (base_id + 400 + 241): (b'C002', Snacks.BOX__OF__SNACKS__2.value),
    (base_id + 400 + 242): (b'C002', Snacks.SNACK__25.value),
    (base_id + 400 + 243): (b'C002', Snacks.SNACK__250.value),
    (base_id + 400 + 244): (b'C002', Snacks.SNACK__251.value),
    (base_id + 400 + 245): (b'C002', Snacks.SNACK__252.value),
    (base_id + 400 + 246): (b'C002', Snacks.SNACK__253.value),
    (base_id + 400 + 247): (b'C002', Snacks.SNACK__2530.value),
    (base_id + 400 + 248): (b'C002', Snacks.SNACK__2531.value),
    (base_id + 400 + 249): (b'C002', Snacks.SNACK__2532.value),
    (base_id + 400 + 250): (b'C002', Snacks.SNACK__067.value),  #Umbrella
    (base_id + 400 + 251): (b'C002', Snacks.SNACK__060.value),
    (base_id + 400 + 252): (b'C002', Snacks.SNACK__061.value),
    (base_id + 400 + 253): (b'C002', Snacks.SNACK__062.value),
    (base_id + 400 + 254): (b'C002', Snacks.SNACK__063.value),
    (base_id + 400 + 255): (b'C002', Snacks.SNACK__064.value),
    (base_id + 400 + 256): (b'C002', Snacks.SNACK__065.value),
    (base_id + 400 + 257): (b'C002', Snacks.SNACK__066.value),

    (base_id + 400 + 258): (b'C003', Snacks.SNACK__01.value),
    (base_id + 400 + 259): (b'C003', Snacks.SNACK__010.value),
    (base_id + 400 + 260): (b'C003', Snacks.SNACK__011.value),
    (base_id + 400 + 261): (b'C003', Snacks.SNACK__012.value),
    (base_id + 400 + 262): (b'C003', Snacks.SNACK__013.value),
    (base_id + 400 + 263): (b'C003', Snacks.SNACK__014.value),
    (base_id + 400 + 264): (b'C003', Snacks.SNACK__015.value),
    (base_id + 400 + 265): (b'C003', Snacks.SNACK__016.value),
    (base_id + 400 + 266): (b'C003', Snacks.SNACK__017.value),
    (base_id + 400 + 267): (b'C003', Snacks.SNACK__06.value),
    (base_id + 400 + 268): (b'C003', Snacks.SNACK__18.value),
    (base_id + 400 + 269): (b'C003', Snacks.SNACK__19.value),
    (base_id + 400 + 270): (b'C003', Snacks.SNACK__190.value),
    (base_id + 400 + 271): (b'C003', Snacks.SNACK__191.value),
    (base_id + 400 + 272): (b'C003', Snacks.SNACK__192.value),
    (base_id + 400 + 273): (b'C003', Snacks.SNACK__193.value),
    (base_id + 400 + 274): (b'C003', Snacks.BOX__OF__SNACKS__1.value),
    (base_id + 400 + 275): (b'C003', Snacks.SNACK__04.value),
    (base_id + 400 + 276): (b'C003', Snacks.SNACKS__040.value),
    (base_id + 400 + 277): (b'C003', Snacks.SNACKS__041.value),
    (base_id + 400 + 278): (b'C003', Snacks.SNACKS__042.value),
    (base_id + 400 + 279): (b'C003', Snacks.SNACK__05.value),
    (base_id + 400 + 280): (b'C003', Snacks.SNACK__050.value),
    (base_id + 400 + 281): (b'C003', Snacks.SNACK__051.value),
    (base_id + 400 + 282): (b'C003', Snacks.SNACK__052.value),
    (base_id + 400 + 283): (b'C003', Snacks.BOX__OF__SNACKS__2.value),
    (base_id + 400 + 284): (b'C003', Snacks.SNACK__14.value),   # To Button
    (base_id + 400 + 285): (b'C003', Snacks.SNACK__15.value),
    (base_id + 400 + 286): (b'C003', Snacks.SNACK__16.value),
    (base_id + 400 + 287): (b'C003', Snacks.SNACK__17.value),   # End To Button
    (base_id + 400 + 288): (b'C003', Snacks.SNACK__220.value),
    (base_id + 400 + 289): (b'C003', Snacks.SNACK__222.value),
    (base_id + 400 + 290): (b'C003', Snacks.SNACK__224.value),
    (base_id + 400 + 291): (b'C003', Snacks.SNACK__226.value),
    (base_id + 400 + 292): (b'C003', Snacks.SNACK__228.value),
    (base_id + 400 + 293): (b'C003', Snacks.SNACK__2210.value),
    (base_id + 400 + 294): (b'C003', Snacks.SNACK__2212.value),
    (base_id + 400 + 295): (b'C003', Snacks.SNACK__2214.value),
    (base_id + 400 + 296): (b'C003', Snacks.SNACK__2216.value),
    (base_id + 400 + 297): (b'C003', Snacks.SNACK__2218.value),
    (base_id + 400 + 298): (b'C003', Snacks.SNACK__07.value),
    (base_id + 400 + 299): (b'C003', Snacks.SNACK__2116.value),
    (base_id + 400 + 300): (b'C003', Snacks.SNACK__2114.value),
    (base_id + 400 + 301): (b'C003', Snacks.SNACK__2112.value),
    (base_id + 400 + 302): (b'C003', Snacks.SNACK__2110.value),
    (base_id + 400 + 303): (b'C003', Snacks.SNACK__217.value),
    (base_id + 400 + 304): (b'C003', Snacks.SNACK__216.value),
    (base_id + 400 + 305): (b'C003', Snacks.SNACK__214.value),
    (base_id + 400 + 306): (b'C003', Snacks.SNACK__212.value),
    (base_id + 400 + 307): (b'C003', Snacks.SNACK__210.value),
    (base_id + 400 + 308): (b'C003', Snacks.SNACK__246.value),  # Button Ledge
    (base_id + 400 + 309): (b'C003', Snacks.SNACK__245.value),
    (base_id + 400 + 310): (b'C003', Snacks.SNACK__244.value),
    (base_id + 400 + 311): (b'C003', Snacks.SNACK__243.value),
    (base_id + 400 + 312): (b'C003', Snacks.SNACK__231.value),
    (base_id + 400 + 313): (b'C003', Snacks.SNACK__230.value),
    (base_id + 400 + 314): (b'C003', Snacks.SNACK__23.value),
    (base_id + 400 + 315): (b'C003', Snacks.SNACK__1310.value),
    (base_id + 400 + 316): (b'C003', Snacks.SNACK__139.value),
    (base_id + 400 + 317): (b'C003', Snacks.SNACK__138.value),
    (base_id + 400 + 318): (b'C003', Snacks.SNACK__130.value),
    (base_id + 400 + 319): (b'C003', Snacks.SNACK__131.value),
    (base_id + 400 + 320): (b'C003', Snacks.SNACK__132.value),
    (base_id + 400 + 321): (b'C003', Snacks.SNACK__13.value),   # End Button Ledge
    (base_id + 400 + 322): (b'C003', Snacks.BOX__OF__SNACKS__3.value),
    (base_id + 400 + 323): (b'C003', Snacks.SNACK__30.value),
    (base_id + 400 + 324): (b'C003', Snacks.SNACK__300.value),
    (base_id + 400 + 325): (b'C003', Snacks.SNACK__301.value),
    (base_id + 400 + 326): (b'C003', Snacks.SNACK__302.value),
    (base_id + 400 + 327): (b'C003', Snacks.SNACK__303.value),
    (base_id + 400 + 328): (b'C003', Snacks.SNACK__304.value),
    (base_id + 400 + 329): (b'C003', Snacks.SNACK__305.value),
    (base_id + 400 + 330): (b'C003', Snacks.SNACK__306.value),
    (base_id + 400 + 331): (b'C003', Snacks.SNACK__307.value),
    (base_id + 400 + 332): (b'C003', Snacks.SNACK__308.value),
    (base_id + 400 + 333): (b'C003', Snacks.SNACK__309.value),
    (base_id + 400 + 334): (b'C003', Snacks.SNACK__3010.value),
    (base_id + 400 + 335): (b'C003', Snacks.SNACK__3011.value),
    (base_id + 400 + 336): (b'C003', Snacks.SNACK__3012.value),
    (base_id + 400 + 337): (b'C003', Snacks.SNACK__3013.value),
    (base_id + 400 + 338): (b'C003', Snacks.SNACK__3014.value),

    (base_id + 400 + 339): (b'C004', Snacks.SNACK__07.value),
    (base_id + 400 + 340): (b'C004', Snacks.SNACK__071.value),
    (base_id + 400 + 341): (b'C004', Snacks.SNACK__073.value),
    (base_id + 400 + 342): (b'C004', Snacks.SNACK__075.value),
    (base_id + 400 + 343): (b'C004', Snacks.SNACK__076.value),
    (base_id + 400 + 344): (b'C004', Snacks.BOX__OF__SNACKS__01.value),
    (base_id + 400 + 345): (b'C004', Snacks.SNACK__06.value),
    (base_id + 400 + 346): (b'C004', Snacks.SNACK__061.value),
    (base_id + 400 + 347): (b'C004', Snacks.SNACK__064.value),
    (base_id + 400 + 348): (b'C004', Snacks.SNACK__066.value),
    (base_id + 400 + 349): (b'C004', Snacks.SNACK__068.value),
    (base_id + 400 + 350): (b'C004', Snacks.SNACK__0610.value),
    (base_id + 400 + 351): (b'C004', Snacks.SNACK__12.value),
    (base_id + 400 + 352): (b'C004', Snacks.SNACK__121.value),
    (base_id + 400 + 353): (b'C004', Snacks.SNACK__123.value),
    (base_id + 400 + 354): (b'C004', Snacks.SNACK__13.value),
    (base_id + 400 + 355): (b'C004', Snacks.SNACK__14.value),
    (base_id + 400 + 356): (b'C004', Snacks.SNACK__380.value),
    (base_id + 400 + 357): (b'C004', Snacks.SNACK__381.value),
    (base_id + 400 + 358): (b'C004', Snacks.SNACK__382.value),
    (base_id + 400 + 359): (b'C004', Snacks.SNACK__383.value),
    (base_id + 400 + 360): (b'C004', Snacks.SNACK__150.value),
    (base_id + 400 + 361): (b'C004', Snacks.SNACK__151.value),
    (base_id + 400 + 362): (b'C004', Snacks.SNACK__152.value),
    (base_id + 400 + 363): (b'C004', Snacks.SNACK__390.value),
    (base_id + 400 + 364): (b'C004', Snacks.SNACK__391.value),
    (base_id + 400 + 365): (b'C004', Snacks.SNACK__392.value),
    (base_id + 400 + 366): (b'C004', Snacks.SNACK__393.value),
    (base_id + 400 + 367): (b'C004', Snacks.BOX__OF__SNACKS__02.value),
    (base_id + 400 + 368): (b'C004', Snacks.SNACK__171.value),
    (base_id + 400 + 369): (b'C004', Snacks.SNACK__172.value),
    (base_id + 400 + 370): (b'C004', Snacks.SNACK__173.value),
    (base_id + 400 + 371): (b'C004', Snacks.SNACK__174.value),
    (base_id + 400 + 372): (b'C004', Snacks.SNACK__175.value),
    (base_id + 400 + 373): (b'C004', Snacks.SNACK__176.value),
    (base_id + 400 + 374): (b'C004', Snacks.SNACK__177.value),
    (base_id + 400 + 375): (b'C004', Snacks.SNACK__178.value),
    (base_id + 400 + 376): (b'C004', Snacks.SNACK__180.value),
    (base_id + 400 + 377): (b'C004', Snacks.SNACK__182.value),
    (base_id + 400 + 378): (b'C004', Snacks.SNACK__184.value),
    (base_id + 400 + 379): (b'C004', Snacks.SNACK__186.value),
    (base_id + 400 + 380): (b'C004', Snacks.SNACK__188.value),
    (base_id + 400 + 381): (b'C004', Snacks.SNACK__19.value),
    (base_id + 400 + 382): (b'C004', Snacks.BOX__OF__SNACKS__03.value),
    (base_id + 400 + 383): (b'C004', Snacks.SNACK__60.value),    # Umbrella
    (base_id + 400 + 384): (b'C004', Snacks.SNACK__600.value),
    (base_id + 400 + 385): (b'C004', Snacks.SNACK__602.value),
    (base_id + 400 + 386): (b'C004', Snacks.SNACK__603.value),
    (base_id + 400 + 387): (b'C004', Snacks.SNACK__606.value),
    (base_id + 400 + 388): (b'C004', Snacks.SNACK__608.value),
    (base_id + 400 + 389): (b'C004', Snacks.SNACK__70.value),
    (base_id + 400 + 390): (b'C004', Snacks.SNACK__700.value),
    (base_id + 400 + 391): (b'C004', Snacks.SNACK__701.value),
    (base_id + 400 + 392): (b'C004', Snacks.SNACK__702.value),
    (base_id + 400 + 393): (b'C004', Snacks.SNACK__703.value),
    (base_id + 400 + 394): (b'C004', Snacks.SNACK__704.value),
    (base_id + 400 + 395): (b'C004', Snacks.SNACK__705.value),
    (base_id + 400 + 396): (b'C004', Snacks.SNACK__706.value),  # End Umbrella
    (base_id + 400 + 397): (b'C004', Snacks.SNACK__32.value),
    (base_id + 400 + 398): (b'C004', Snacks.SNACK__321.value),
    (base_id + 400 + 399): (b'C004', Snacks.SNACK__323.value),
    (base_id + 400 + 400): (b'C004', Snacks.SNACK__325.value),
    (base_id + 400 + 401): (b'C004', Snacks.SNACK__327.value),
    (base_id + 400 + 402): (b'C004', Snacks.SNACK__329.value),
    (base_id + 400 + 403): (b'C004', Snacks.SNACK__3211.value),
    (base_id + 400 + 404): (b'C004', Snacks.SNACK__3213.value),
    (base_id + 400 + 405): (b'C004', Snacks.SNACK__36.value),
    (base_id + 400 + 406): (b'C004', Snacks.SNACK__361.value),
    (base_id + 400 + 407): (b'C004', Snacks.SNACK__363.value),
    (base_id + 400 + 408): (b'C004', Snacks.SNACK__41.value),
    (base_id + 400 + 409): (b'C004', Snacks.BOX__OF__SNACKS__05.value),
    (base_id + 400 + 410): (b'C004', Snacks.BOX__OF__SNACKS__04.value),
    (base_id + 400 + 411): (b'C004', Snacks.BOX__OF__SNACKS__06.value),
    (base_id + 400 + 412): (b'C004', Snacks.SNACK__260.value),
    (base_id + 400 + 413): (b'C004', Snacks.SNACK__262.value),
    (base_id + 400 + 414): (b'C004', Snacks.SNACK__264.value),
    (base_id + 400 + 415): (b'C004', Snacks.SNACK__266.value),
    (base_id + 400 + 416): (b'C004', Snacks.SNACK__268.value),
    (base_id + 400 + 417): (b'C004', Snacks.SNACK__2610.value),
    (base_id + 400 + 418): (b'C004', Snacks.SNACK__2612.value),
    (base_id + 400 + 419): (b'C004', Snacks.SNACK__2614.value),
    (base_id + 400 + 420): (b'C004', Snacks.SNACK__2616.value),
    (base_id + 400 + 421): (b'C004', Snacks.SNACK__2618.value),
    (base_id + 400 + 422): (b'C004', Snacks.SNACK__2620.value),
    (base_id + 400 + 423): (b'C004', Snacks.SNACK__2622.value),
    (base_id + 400 + 424): (b'C004', Snacks.BOX__OF__SNACKS__07.value),
    (base_id + 400 + 425): (b'C004', Snacks.SNACK__31.value),
    (base_id + 400 + 426): (b'C004', Snacks.SNACK__310.value),
    (base_id + 400 + 427): (b'C004', Snacks.SNACK__311.value),
    (base_id + 400 + 428): (b'C004', Snacks.SNACK__312.value),
    (base_id + 400 + 429): (b'C004', Snacks.SNACK__313.value),
    (base_id + 400 + 430): (b'C004', Snacks.SNACK__3130.value),
    (base_id + 400 + 431): (b'C004', Snacks.SNACK__31300.value),
    (base_id + 400 + 432): (b'C004', Snacks.SNACK__31301.value),
    (base_id + 400 + 433): (b'C004', Snacks.SNACK__31302.value),
    (base_id + 400 + 434): (b'C004', Snacks.SNACK__313030.value),
    (base_id + 400 + 435): (b'C004', Snacks.SNACK__31303.value),
    (base_id + 400 + 436): (b'C004', Snacks.SNACK__313031.value),
    (base_id + 400 + 437): (b'C004', Snacks.SNACK__313032.value),
    (base_id + 400 + 438): (b'C004', Snacks.SNACK__313033.value),
    (base_id + 400 + 439): (b'C004', Snacks.SNACK__355.value),
    (base_id + 400 + 440): (b'C004', Snacks.SNACK__3550.value),
    (base_id + 400 + 441): (b'C004', Snacks.SNACK__3552.value),
    (base_id + 400 + 442): (b'C004', Snacks.SNACK__3554.value),
    (base_id + 400 + 443): (b'C004', Snacks.SNACK__3556.value),
    (base_id + 400 + 444): (b'C004', Snacks.SNACK__340.value),
    (base_id + 400 + 445): (b'C004', Snacks.SNACK__341.value),
    (base_id + 400 + 446): (b'C004', Snacks.SNACK__342.value),
    (base_id + 400 + 447): (b'C004', Snacks.SNACK__343.value),
    (base_id + 400 + 448): (b'C004', Snacks.SNACK__344.value),
    (base_id + 400 + 449): (b'C004', Snacks.SNACK__345.value),
    (base_id + 400 + 450): (b'C004', Snacks.SNACK__346.value),
    (base_id + 400 + 451): (b'C004', Snacks.SNACK__347.value),
    (base_id + 400 + 452): (b'C004', Snacks.SNACK__348.value),
    (base_id + 400 + 453): (b'C004', Snacks.SNACK__349.value),
    (base_id + 400 + 454): (b'C004', Snacks.SNACK__3410.value),

    (base_id + 400 + 456): (b'C005', Snacks.SNACKBOX__1.value),
    (base_id + 400 + 457): (b'C005', Snacks.SNACK__01.value),
    (base_id + 400 + 458): (b'C005', Snacks.SNACK__02.value),
    (base_id + 400 + 459): (b'C005', Snacks.SNACK__03.value),
    (base_id + 400 + 460): (b'C005', Snacks.SNACK__04.value),
    (base_id + 400 + 461): (b'C005', Snacks.SNACK__05.value),
    (base_id + 400 + 462): (b'C005', Snacks.SNACK__06.value),
    (base_id + 400 + 463): (b'C005', Snacks.SNACK__07.value),
    (base_id + 400 + 464): (b'C005', Snacks.SNACK__08.value),
    (base_id + 400 + 465): (b'C005', Snacks.SNACK__09.value),
    (base_id + 400 + 466): (b'C005', Snacks.SNACK__10.value),
    (base_id + 400 + 467): (b'C005', Snacks.SNACK__100.value),
    (base_id + 400 + 468): (b'C005', Snacks.SNACK__101.value),
    (base_id + 400 + 469): (b'C005', Snacks.SNACK__102.value),
    (base_id + 400 + 470): (b'C005', Snacks.SNACK__103.value),
    (base_id + 400 + 471): (b'C005', Snacks.SNACK__104.value),
    (base_id + 400 + 472): (b'C005', Snacks.SNACK__105.value),
    (base_id + 400 + 473): (b'C005', Snacks.SNACK__106.value),
    (base_id + 400 + 474): (b'C005', Snacks.SNACK__107.value),
    (base_id + 400 + 475): (b'C005', Snacks.SNACK__108.value),
    (base_id + 400 + 476): (b'C005', Snacks.SNACK__109.value),
    (base_id + 400 + 477): (b'C005', Snacks.SNACK__12.value),
    (base_id + 400 + 478): (b'C005', Snacks.SNACK__120.value),
    (base_id + 400 + 479): (b'C005', Snacks.SNACK__121.value),
    (base_id + 400 + 480): (b'C005', Snacks.SNACK__122.value),
    (base_id + 400 + 481): (b'C005', Snacks.SNACK__123.value),
    (base_id + 400 + 482): (b'C005', Snacks.SNACK__124.value),
    (base_id + 400 + 483): (b'C005', Snacks.SNACK__125.value),
    (base_id + 400 + 484): (b'C005', Snacks.SNACK__126.value),
    (base_id + 400 + 485): (b'C005', Snacks.SNACK__127.value),
    (base_id + 400 + 486): (b'C005', Snacks.SNACK__128.value),
    (base_id + 400 + 487): (b'C005', Snacks.SNACK__129.value),
    (base_id + 400 + 488): (b'C005', Snacks.SNACKBOX__2.value),
    (base_id + 400 + 489): (b'C005', Snacks.SNACKBOX__3.value),
    (base_id + 400 + 490): (b'C005', Snacks.SNACK__19.value),
    (base_id + 400 + 491): (b'C005', Snacks.SNACK__190.value),
    (base_id + 400 + 492): (b'C005', Snacks.SNACK__191.value),
    (base_id + 400 + 493): (b'C005', Snacks.SNACK__192.value),
    (base_id + 400 + 494): (b'C005', Snacks.SNACK__193.value),
    (base_id + 400 + 495): (b'C005', Snacks.SNACK__194.value),
    (base_id + 400 + 496): (b'C005', Snacks.SNACK__195.value),
    (base_id + 400 + 497): (b'C005', Snacks.SNACK__196.value),
    (base_id + 400 + 498): (b'C005', Snacks.SNACK__197.value),
    (base_id + 400 + 499): (b'C005', Snacks.SNACK__198.value),
    (base_id + 400 + 500): (b'C005', Snacks.SNACK__199.value),
    (base_id + 400 + 501): (b'C005', Snacks.SNACK__1910.value),
    (base_id + 400 + 502): (b'C005', Snacks.SNACK__1911.value),
    (base_id + 400 + 503): (b'C005', Snacks.SNACK__1912.value),
    (base_id + 400 + 504): (b'C005', Snacks.SNACK__1913.value),
    (base_id + 400 + 505): (b'C005', Snacks.SNACK__1914.value),
    (base_id + 400 + 506): (b'C005', Snacks.SNACK__1915.value),
    (base_id + 400 + 507): (b'C005', Snacks.SNACK__1916.value),
    (base_id + 400 + 508): (b'C005', Snacks.SNACK__1917.value),
    (base_id + 400 + 509): (b'C005', Snacks.SNACK__1918.value),
    (base_id + 400 + 510): (b'C005', Snacks.SNACK__1919.value),

    (base_id + 400 + 511): (b'C006', Snacks.SNACK__01.value),
    (base_id + 400 + 512): (b'C006', Snacks.SNACK__010.value),
    (base_id + 400 + 513): (b'C006', Snacks.SNACK__011.value),
    (base_id + 400 + 514): (b'C006', Snacks.SNACK__012.value),
    (base_id + 400 + 515): (b'C006', Snacks.SNACK__013.value),
    (base_id + 400 + 516): (b'C006', Snacks.SNACK__014.value),
    (base_id + 400 + 517): (b'C006', Snacks.SNACK__02.value),
    (base_id + 400 + 518): (b'C006', Snacks.SNACK__020.value),
    (base_id + 400 + 519): (b'C006', Snacks.SNACK__021.value),
    (base_id + 400 + 520): (b'C006', Snacks.SNACK__022.value),
    (base_id + 400 + 521): (b'C006', Snacks.SNACK__023.value),
    (base_id + 400 + 522): (b'C006', Snacks.SNACK__024.value),
    (base_id + 400 + 523): (b'C006', Snacks.CRATE__SNACKBOX__1.value),
    (base_id + 400 + 524): (b'C006', Snacks.CRATE__SNACKBOX__2.value),
    (base_id + 400 + 525): (b'C006', Snacks.SNACK__03.value),
    (base_id + 400 + 526): (b'C006', Snacks.SNACK__030.value),
    (base_id + 400 + 527): (b'C006', Snacks.SNACK__031.value),
    (base_id + 400 + 528): (b'C006', Snacks.SNACK__032.value),
    (base_id + 400 + 529): (b'C006', Snacks.SNACK__033.value),
    (base_id + 400 + 530): (b'C006', Snacks.SNACK__034.value),
    (base_id + 400 + 531): (b'C006', Snacks.SNACK__05.value),
    (base_id + 400 + 532): (b'C006', Snacks.SNACK__050.value),
    (base_id + 400 + 533): (b'C006', Snacks.SNACK__051.value),
    (base_id + 400 + 534): (b'C006', Snacks.SNACK__052.value),
    (base_id + 400 + 535): (b'C006', Snacks.SNACK__053.value),
    (base_id + 400 + 536): (b'C006', Snacks.SNACK__07.value),
    (base_id + 400 + 537): (b'C006', Snacks.SNACK__070.value),
    (base_id + 400 + 538): (b'C006', Snacks.SNACK__071.value),
    (base_id + 400 + 539): (b'C006', Snacks.SNACK__072.value),
    (base_id + 400 + 540): (b'C006', Snacks.SNACK__0720.value),
    (base_id + 400 + 541): (b'C006', Snacks.SNACK__0721.value),
    (base_id + 400 + 542): (b'C006', Snacks.SNACK__0722.value),
    (base_id + 400 + 543): (b'C006', Snacks.SNACK__804.value),
    (base_id + 400 + 544): (b'C006', Snacks.SNACK__803.value),
    (base_id + 400 + 545): (b'C006', Snacks.SNACK__802.value),
    (base_id + 400 + 546): (b'C006', Snacks.SNACK__801.value),
    (base_id + 400 + 547): (b'C006', Snacks.SNACK__800.value),
    (base_id + 400 + 548): (b'C006', Snacks.SNACK__80.value),
    (base_id + 400 + 549): (b'C006', Snacks.SNACK__805.value),
    (base_id + 400 + 550): (b'C006', Snacks.SNACK__806.value),
    (base_id + 400 + 551): (b'C006', Snacks.SNACK__807.value),
    (base_id + 400 + 552): (b'C006', Snacks.SNACK__808.value),
    (base_id + 400 + 553): (b'C006', Snacks.SNACK__809.value),
    (base_id + 400 + 554): (b'C006', Snacks.SNACKBOX__3.value),
    (base_id + 400 + 555): (b'C006', Snacks.SNACK__BOX__2.value),

    (base_id + 400 + 556): (b'C007', Snacks.BOX__OF__SNACKS__1.value),
    (base_id + 400 + 557): (b'C007', Snacks.SNACK__01.value),
    (base_id + 400 + 558): (b'C007', Snacks.SNACK__010.value),
    (base_id + 400 + 559): (b'C007', Snacks.SNACK__011.value),
    (base_id + 400 + 560): (b'C007', Snacks.SNACK__012.value),
    (base_id + 400 + 561): (b'C007', Snacks.SNACK__013.value),
    (base_id + 400 + 562): (b'C007', Snacks.SNACK__014.value),
    (base_id + 400 + 563): (b'C007', Snacks.SNACK__015.value),
    (base_id + 400 + 564): (b'C007', Snacks.SNACK__03.value),
    (base_id + 400 + 565): (b'C007', Snacks.SNACK__030.value),
    (base_id + 400 + 566): (b'C007', Snacks.SNACK__031.value),
    (base_id + 400 + 567): (b'C007', Snacks.SNACK__032.value),
    (base_id + 400 + 568): (b'C007', Snacks.SNACK__033.value),
    (base_id + 400 + 569): (b'C007', Snacks.SNACK__034.value),
    (base_id + 400 + 570): (b'C007', Snacks.SNACK__04.value),
    (base_id + 400 + 571): (b'C007', Snacks.SNACK__040.value),
    (base_id + 400 + 572): (b'C007', Snacks.SNACK__041.value),
    (base_id + 400 + 573): (b'C007', Snacks.SNACK__042.value),
    (base_id + 400 + 574): (b'C007', Snacks.SNACK__043.value),
    (base_id + 400 + 575): (b'C007', Snacks.SNACK__044.value),
    (base_id + 400 + 576): (b'C007', Snacks.SNACK__045.value),
    (base_id + 400 + 577): (b'C007', Snacks.BOX__OF__SNACKS__3.value),
    (base_id + 400 + 578): (b'C007', Snacks.SNACK__074.value),
    (base_id + 400 + 579): (b'C007', Snacks.SNACK__073.value),
    (base_id + 400 + 580): (b'C007', Snacks.SNACK__072.value),
    (base_id + 400 + 581): (b'C007', Snacks.SNACK__071.value),
    (base_id + 400 + 582): (b'C007', Snacks.SNACK__070.value),
    (base_id + 400 + 583): (b'C007', Snacks.SNACK__07.value),
    (base_id + 400 + 584): (b'C007', Snacks.SNACK__075.value),
    (base_id + 400 + 585): (b'C007', Snacks.SNACK__076.value),
    (base_id + 400 + 586): (b'C007', Snacks.SNACK__077.value),
    (base_id + 400 + 587): (b'C007', Snacks.SNACK__078.value),
    (base_id + 400 + 588): (b'C007', Snacks.SNACK__079.value),
    (base_id + 400 + 589): (b'C007', Snacks.SNACK__0790.value),
    (base_id + 400 + 590): (b'C007', Snacks.SNACK__0791.value),
    (base_id + 400 + 591): (b'C007', Snacks.SNACK__0792.value),
    (base_id + 400 + 592): (b'C007', Snacks.SNACK__0793.value),
    (base_id + 400 + 593): (b'C007', Snacks.SNACK__0794.value),
    (base_id + 400 + 594): (b'C007', Snacks.SNACK__10.value),
    (base_id + 400 + 595): (b'C007', Snacks.SNACK__100.value),
    (base_id + 400 + 596): (b'C007', Snacks.SNACK__101.value),
    (base_id + 400 + 597): (b'C007', Snacks.SNACK__102.value),
    (base_id + 400 + 598): (b'C007', Snacks.SNACK__103.value),
    (base_id + 400 + 599): (b'C007', Snacks.SNACK__104.value),
    (base_id + 400 + 600): (b'C007', Snacks.SNACK__105.value),
    (base_id + 400 + 601): (b'C007', Snacks.SNACK__106.value),
    (base_id + 400 + 602): (b'C007', Snacks.SNACK__12.value),
    (base_id + 400 + 603): (b'C007', Snacks.SNACK__120.value),
    (base_id + 400 + 604): (b'C007', Snacks.SNACK__121.value),
    (base_id + 400 + 605): (b'C007', Snacks.SNACK__122.value),
    (base_id + 400 + 606): (b'C007', Snacks.SNACK__123.value),
    (base_id + 400 + 607): (b'C007', Snacks.SNACK__124.value),
    (base_id + 400 + 608): (b'C007', Snacks.SNACK__125.value),
    (base_id + 400 + 609): (b'C007', Snacks.SNACK__164.value),
    (base_id + 400 + 610): (b'C007', Snacks.SNACK__163.value),
    (base_id + 400 + 611): (b'C007', Snacks.SNACK__162.value),
    (base_id + 400 + 612): (b'C007', Snacks.SNACK__161.value),
    (base_id + 400 + 613): (b'C007', Snacks.SNACK__160.value),
    (base_id + 400 + 614): (b'C007', Snacks.SNACK__16.value),
    (base_id + 400 + 615): (b'C007', Snacks.SNACK__17.value),
    (base_id + 400 + 616): (b'C007', Snacks.SNACK__174.value),
    (base_id + 400 + 617): (b'C007', Snacks.SNACK__175.value),
    (base_id + 400 + 618): (b'C007', Snacks.SNACK__176.value),
    (base_id + 400 + 619): (b'C007', Snacks.SNACK__177.value),
    (base_id + 400 + 620): (b'C007', Snacks.SNACK__178.value),
    (base_id + 400 + 621): (b'C007', Snacks.BOX__OF__SNACKS__4.value),
    (base_id + 400 + 622): (b'C007', Snacks.SNACK__180.value),
    (base_id + 400 + 623): (b'C007', Snacks.SNACK__181.value),
    (base_id + 400 + 624): (b'C007', Snacks.SNACK__182.value),
    (base_id + 400 + 625): (b'C007', Snacks.SNACK__183.value),
    (base_id + 400 + 626): (b'C007', Snacks.SNACK__184.value),
    (base_id + 400 + 627): (b'C007', Snacks.SNACK__185.value),
    (base_id + 400 + 628): (b'C007', Snacks.SNACK__186.value),
    (base_id + 400 + 629): (b'C007', Snacks.SNACK__187.value),
    (base_id + 400 + 630): (b'C007', Snacks.SNACK__188.value),
    (base_id + 400 + 631): (b'C007', Snacks.SNACK__189.value),
    (base_id + 400 + 632): (b'C007', Snacks.SNACK__193.value),
    (base_id + 400 + 633): (b'C007', Snacks.SNACK__192.value),
    (base_id + 400 + 634): (b'C007', Snacks.SNACK__191.value),
    (base_id + 400 + 635): (b'C007', Snacks.SNACK__190.value),
    (base_id + 400 + 636): (b'C007', Snacks.SNACK__19.value),
    (base_id + 400 + 637): (b'C007', Snacks.SNACK__194.value),
    (base_id + 400 + 638): (b'C007', Snacks.SNACK__195.value),
    (base_id + 400 + 639): (b'C007', Snacks.SNACK__196.value),
    (base_id + 400 + 640): (b'C007', Snacks.SNACK__197.value),
    (base_id + 400 + 641): (b'C007', Snacks.SNACK__198.value),
    (base_id + 400 + 642): (b'C007', Snacks.BOX__OF__SNACKS__2.value),
    (base_id + 400 + 643): (b'C007', Snacks.SNACK__204.value),
    (base_id + 400 + 644): (b'C007', Snacks.SNACK__203.value),
    (base_id + 400 + 645): (b'C007', Snacks.SNACK__202.value),
    (base_id + 400 + 646): (b'C007', Snacks.SNACK__201.value),
    (base_id + 400 + 647): (b'C007', Snacks.SNACK__200.value),
    (base_id + 400 + 648): (b'C007', Snacks.SNACK__20.value),
    (base_id + 400 + 649): (b'C007', Snacks.SNACK__213.value),
    (base_id + 400 + 650): (b'C007', Snacks.SNACK__212.value),
    (base_id + 400 + 651): (b'C007', Snacks.SNACK__211.value),
    (base_id + 400 + 652): (b'C007', Snacks.SNACK__210.value),
    (base_id + 400 + 653): (b'C007', Snacks.SNACK__21.value),
    (base_id + 400 + 654): (b'C007', Snacks.SNACK__223.value),
    (base_id + 400 + 655): (b'C007', Snacks.SNACK__222.value),
    (base_id + 400 + 656): (b'C007', Snacks.SNACK__221.value),
    (base_id + 400 + 657): (b'C007', Snacks.SNACK__220.value),
    (base_id + 400 + 658): (b'C007', Snacks.SNACK__22.value),
    (base_id + 400 + 659): (b'C007', Snacks.CRATE__PRIZE__1.value),
    (base_id + 400 + 660): (b'C007', Snacks.CRATE__PRIZE__10.value),




}

valid_scenes = [
    b'B001', b'B002', b'B003', b'B004',
    b'C001', b'C002', b'C003', b'C004', b'C005', b'C006', b'C007',
    b'E001', b'E002', b'E003', b'E004', b'E005', b'E006', b'E007', b'E008', b'E009',
    b'F001', b'F003', b'F004', b'F005', b'F006', b'F007', b'F008', b'F009', b'F010',
    b'G001', b'G002', b'G003', b'G004', b'G005', b'G006', b'G007', b'G008', b'G009',
    b'H001', b'H002', b'H003', b'h001',
    b'I001', b'I003', b'I004', b'I005', b'I006', b'I020', b'I021',
    b'L011', b'L013', b'L014', b'L015', b'L017', b'L018', b'L019',
    b'O001', b'O002', b'O003', b'O004', b'O005', b'O006', b'O008',
    b'P001', b'P002', b'P003', b'P004', b'P005',
    b'R001', b'R002', b'R003', b'R004', b'R005', b'R020', b'R021',
    b'S001', b'S002', b'S003', b'S004', b'S005', b'S006',
    b'W020', b'W021', b'W022', b'W023', b'W025', b'W026', b'W027', b'W028',
]

invalid_scenes = [
    b'MNU3', b'MNU4',  # menus
]


class NO100FCommandProcessor(ClientCommandProcessor):
    def __init__(self, ctx: CommonContext):
        super().__init__(ctx)

    def _cmd_dolphin(self):
        """Check Dolphin Connection State"""
        if isinstance(self.ctx, NO100FContext):
            logger.info(f"Dolphin Status: {self.ctx.dolphin_status}")

    def _cmd_resetscooby(self):
        """Force Kill Scooby to escape softlocks"""
        if dolphin_memory_engine.is_hooked():
            dolphin_memory_engine.write_word(HEALTH_ADDR, 69)
            logger.info("Killing Scooby :(")

    def _cmd_keys(self):
        """Displays current key counts and the number expected in a room"""
        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR)
        logger.info(f"Clamor 1 Keys {count}/1")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 1)
        logger.info(f"Hedge Maze Keys {count}/1")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 2)
        logger.info(f"Fishing Village Keys {count}/1")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 3)
        logger.info(f"Cellar 2 Keys {count}/3")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 4)
        logger.info(f"Cellar 3 Keys {count}/4")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 5)
        logger.info(f"Cavein Keys {count}/4")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 6)
        logger.info(f"Fishy Clues Keys {count}/4")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 7)
        logger.info(f"Graveplot Keys {count}/3")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 8)
        logger.info(f"Tomb 1 Keys {count}/1")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 9)
        logger.info(f"Tomb 3 Keys {count}/2")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 10)
        logger.info(f"Clamor 4 Keys {count}/1")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 11)
        logger.info(f"MYM Keys {count}/4")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 12)
        logger.info(f"Coast Keys {count}/4")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 13)
        logger.info(f"Attic Keys {count}/3")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 14)
        logger.info(f"Knight Keys {count}/4")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 15)
        logger.info(f"Creepy 2 Keys {count}/5")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 16)
        logger.info(f"Creepy 3 Keys {count}/3")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 17)
        logger.info(f"Gusts 1 Keys {count}/1")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 18)
        logger.info(f"Gusts 2 Keys {count}/4")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 19)
        logger.info(f"DLD Keys {count}/3")

        count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 20)
        logger.info(f"Shiver Keys {count}/4")


class NO100FContext(CommonContext):
    command_processor = NO100FCommandProcessor
    game = "Scooby-Doo! Night of 100 Frights"
    items_handling = 0b111  # full remote

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.items_received_2 = []
        self.dolphin_sync_task = None
        self.dolphin_status = CONNECTION_INITIAL_STATUS
        self.awaiting_rom = False
        #self.snack_count = 0
        self.LAST_STATE = [bytes([0, 0]), bytes([0, 0]), bytes([0, 0])]
        self.last_rev_index = -1
        self.has_send_death = False
        self.forced_death = False
        self.post_boss = False
        self.last_death_link_send = time.time()
        self.current_scene_key = None
        self.use_tokens = False
        self.use_keys = False
        self.use_warpgates = False
        self.use_snacks = False
        self.current_scene = None
        self.previous_scene = None
        self.CitM1_key = 0
        self.hedge_key = 0
        self.fish_key = 0
        self.WYitC2_keys = 0
        self.WYitC3_keys = 0
        self.MCaC_keys = 0
        self.FCfS_keys = 0
        self.TSfaGP_keys = 0
        self.GDDitT1_key = 0
        self.GDDitT3_keys = 0
        self.CitM4_key = 0
        self.MyM2_keys = 0
        self.CfsG1_keys = 0
        self.PitA2_keys = 0
        self.ADaSK2_keys = 0
        self.CCitH2_keys = 0
        self.CCitH3_keys = 0
        self.GAU1_key = 0
        self.GAU2_keys = 0
        self.DLDS2_keys = 0
        self.SYTS1_keys = 0

    async def disconnect(self, allow_autoreconnect: bool = False):
        self.auth = None
        await super().disconnect(allow_autoreconnect)

    def on_package(self, cmd: str, args: dict):
        if cmd == 'Connected':
            self.current_scene_key = f"NO100F_current_scene_T{self.team}_P{self.slot}"
            self.set_notify(self.current_scene_key)
            self.last_rev_index = -1
            self.items_received_2 = []
            self.included_check_types = CheckTypes.UPGRADES
            if 'death_link' in args['slot_data']:
                Utils.async_start(self.update_death_link(bool(args['slot_data']['death_link'])))
            if 'include_monster_tokens' in args['slot_data'] and args['slot_data']['include_monster_tokens']:
                self.use_tokens = True
            if 'include_keys' in args['slot_data'] and args['slot_data']['include_keys']:
                self.use_keys = True
            if 'include_warpgates' in args['slot_data'] and args['slot_data']['include_warpgates']:
                self.use_warpgates = True
            if 'include_snacks' in args['slot_data'] and args['slot_data']['include_snacks']:
                self.use_snacks = True
            if 'completion_goal' in args['slot_data']:
                self.completion_goal = args['slot_data']['completion_goal']
        if cmd == 'ReceivedItems':
            if args["index"] >= self.last_rev_index:
                self.last_rev_index = args["index"]
                for item in args['items']:
                    self.items_received_2.append((item, self.last_rev_index))
                    self.last_rev_index += 1
            self.items_received_2.sort(key=lambda v: v[1])

    def on_deathlink(self, data: Dict[str, Any]) -> None:
        super().on_deathlink(data)
        _give_death(self)

    #def _update_item_counts(self, args: dict):
    #self.snack_count = len([item for item in self.items_received if item.item == base_id + 0])

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            logger.info('Enter the password required to join this game:')
            self.password = await self.console_input()
            return self.password
        if not self.auth:
            if self.awaiting_rom:
                return
            self.awaiting_rom = True
            logger.info('Awaiting connection to Dolphin to get player information')
            return
        await self.send_connect()

    def run_gui(self):
        from kvui import GameManager

        class NO100FManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago")
            ]
            base_title = "Archipelago Scooby Doo: Night of 100 Frights Client"

        self.ui = NO100FManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")


def _is_ptr_valid(ptr):
    return 0x80000000 <= ptr < 0x817fffff


def _is_scene_visited(target_scene: bytes):
    current_index = VISITED_SCENES_ADDR
    current_value = 1
    while not current_value == 0:
        current_value = dolphin_memory_engine.read_word(current_index)
        if current_value == int.from_bytes(target_scene, "big"):
            return True
        current_index += 0x10
    return False


def _find_obj_in_obj_table(id: int, ptr: Optional[int] = None, size: Optional[int] = None):
    if size is None:
        size = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_SIZE_ADDR)
    if ptr is None:
        ptr = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_PTR_ADDR)
        if not _is_ptr_valid(ptr): return None
    try:
        counter_list_entry = 0
        # this is our initial index "guess"
        idx = id & (size - 1)
        skip = False
        for i in range(0, size):
            # addr for entry in the list at idx
            counter_list_entry = ptr + idx * 0x8
            if not _is_ptr_valid(counter_list_entry):
                return None
            # get id from the entry
            obj_id = dolphin_memory_engine.read_word(counter_list_entry)
            # if the id matches, we are at the right entry
            if obj_id == id:
                break
            # the returns NULL if it encounters id 0, so just skip if we do
            if obj_id == 0:
                break
            # we are not at the right entry so look at the next
            idx += 1
            # rollover at end of list
            if idx == size:
                idx = 0
        if skip: return -1
        # read counter pointer from the entry
        obj_ptr = dolphin_memory_engine.read_word(counter_list_entry + 0x4)
        if not _is_ptr_valid(obj_ptr):
            return None
        return obj_ptr
    except:
        return None


# def _give_snack(ctx: NO100FContext):
#    cur_snack_count = dolphin_memory_engine.read_word(SNACK_COUNT_ADDR)
#    dolphin_memory_engine.write_word(SNACK_COUNT_ADDR, cur_snack_count + 1)
#    if cur_snack_count > ctx.snack_count:
#        logger.info("!Some went wrong with the snack count!")

def _give_powerup(ctx: NO100FContext, bit: int):
    cur_upgrades = dolphin_memory_engine.read_word(UPGRADE_INVENTORY_ADDR)

    if bit == 4:    # Progressive Sneak Upgrade
        if not cur_upgrades & 2 ** 4:
            cur_upgrades += 2 ** 4
        elif not cur_upgrades & 2 ** 5:
            cur_upgrades += 2 ** 5
        elif not cur_upgrades & 2 ** 6:
            cur_upgrades += 2 ** 6
        dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, cur_upgrades)

    if bit == 9:    # Progressive Jump Upgrade
        if not cur_upgrades & 2 ** 9:
            cur_upgrades += 2 ** 9
        elif not cur_upgrades & 2 ** 12:
            cur_upgrades += 2 ** 12
        dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, cur_upgrades)

    if ((bit == 13) and cur_upgrades & 2 ** 7):  # Player is getting a shovel and currently has the fake
        cur_upgrades -= 2 ** 7
        dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, cur_upgrades)

    if cur_upgrades & 2 ** bit == 0:
        dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, cur_upgrades + 2 ** bit)


def _give_gum_upgrade(ctx: NO100FContext):
    cur_max_gum = dolphin_memory_engine.read_word(MAX_GUM_COUNT_ADDR)
    dolphin_memory_engine.write_word(MAX_GUM_COUNT_ADDR, cur_max_gum + 5)


def _give_soap_upgrade(ctx: NO100FContext):
    cur_max_soap = dolphin_memory_engine.read_word(MAX_SOAP_COUNT_ADDR)
    dolphin_memory_engine.write_word(MAX_SOAP_COUNT_ADDR, cur_max_soap + 5)


def _give_monstertoken(ctx: NO100FContext, bit: int):
    cur_monster_tokens = dolphin_memory_engine.read_word(MONSTER_TOKEN_INVENTORY_ADDR)
    if cur_monster_tokens & 2 ** bit == 0:
        dolphin_memory_engine.write_word(MONSTER_TOKEN_INVENTORY_ADDR, cur_monster_tokens + 2 ** bit)


def _give_key(ctx: NO100FContext, offset: int):
    cur_count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + offset)
    dolphin_memory_engine.write_byte(KEY_COUNT_ADDR + offset, cur_count + 1)


def _give_warp(ctx: NO100FContext, offset: int):
    cur_warps = dolphin_memory_engine.read_word(SAVED_WARP_ADDR)
    if not cur_warps & 2 ** offset == 2 ** offset:
        cur_warps += 2 ** offset
        dolphin_memory_engine.write_word(SAVED_WARP_ADDR, cur_warps)


def _give_death(ctx: NO100FContext):
    if ctx.slot and dolphin_memory_engine.is_hooked() and ctx.dolphin_status == CONNECTION_CONNECTED_STATUS \
            and check_ingame(ctx) and check_control_owner(ctx, lambda owner: owner == 1):
        dolphin_memory_engine.write_word(HEALTH_ADDR, 0)


def _check_cur_scene(ctx: NO100FContext, scene_id: bytes, scene_ptr: Optional[int] = None):
    cur_scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    return cur_scene == scene_id


def _give_item(ctx: NO100FContext, item_id: int):
    true_id = item_id - base_id  # Use item_id to generate offset for use with functions
    if 0 <= true_id <= 82:  # ID is expected value

        if true_id < 7:
            _give_powerup(ctx, true_id)

        elif true_id < 13:
            _give_powerup(ctx, true_id + 2)  # There are 2 unused bits at 8 and 9, offset remaining actual upgrades.

        elif true_id == 13:
            _give_gum_upgrade(ctx)

        elif true_id == 14:
            _give_soap_upgrade(ctx)

        if 14 < true_id < 36:
            _give_monstertoken(ctx, true_id - 15)

        if 36 <= true_id <= 56:
            _give_key(ctx, true_id - 36)

        if 57 <= true_id <= 82:
            _give_warp(ctx, true_id - 57)

    else:
        logger.warning(f"Received unknown item with id {item_id}")


def _set_platform_state(ctx: NO100FContext, ptr, state):
    dolphin_memory_engine.write_byte(ptr + 0x14, state)


def _set_platform_collision_state(ctx: NO100FContext, ptr, state):
    dolphin_memory_engine.write_byte(ptr + 0x28, state)


def _check_platform_state(ctx: NO100FContext, ptr):
    return dolphin_memory_engine.read_byte(ptr + 0x14)


def _set_trigger_state(ctx: NO100FContext, ptr, state):
    dolphin_memory_engine.write_byte(ptr + 0x7, state)


def _set_counter_value(ctx: NO100FContext, ptr, count):
    dolphin_memory_engine.write_byte(ptr + 0x15, count)


def _set_pickup_active(ctx: NO100FContext, ptr, state):
    dolphin_memory_engine.write_byte(ptr + 0x7, state)


async def apply_key_fixes(ctx: NO100FContext):
    scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    ptr = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_PTR_ADDR)
    if not _is_ptr_valid(ptr):
        return
    size = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_SIZE_ADDR)

    if scene == b'I001':
        fix_ptr = _find_obj_in_obj_table(0x1e1157c3, ptr, size)
        if not fix_ptr == None:
            if ctx.CitM1_key >= 1:  # The Key is collected, allow door to open
                fix_ptr = _find_obj_in_obj_table(0x1e1157c3, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)
                fix_ptr = _find_obj_in_obj_table(0x586E19B9, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)

            if ctx.CitM1_key == 0:  # The Key is not collected, block door from opening
              #  fix_ptr = _find_obj_in_obj_table(0x1e1157c3, ptr, size)
              #  _set_trigger_state(ctx, fix_ptr, 0x1c)
                fix_ptr = _find_obj_in_obj_table(0x586E19B9, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

    if scene == b'H001' or b'h001':
        fix_ptr = _find_obj_in_obj_table(0xC20224F3, ptr, size)
        if not fix_ptr == None:
            if ctx.hedge_key >= 1:  # The Hedge key is collected, open the gate
                fix_ptr = _find_obj_in_obj_table(0xC20224F3, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0xE8B3FF9B, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

                fix_ptr = _find_obj_in_obj_table(0xD72B66B7, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)

            else:  # Hedge Key is not collected, make sure the gate is closed
                fix_ptr = _find_obj_in_obj_table(0xC20224F3, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0xE8B3FF9B, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)

                fix_ptr = _find_obj_in_obj_table(0xD72B66B7, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

        fix_ptr = _find_obj_in_obj_table(0x42A3128E, ptr, size)
        if not fix_ptr == None:
            if ctx.fish_key >= 1:  # The Fishing key is collected, open the gate
                fix_ptr = _find_obj_in_obj_table(0x42A3128E, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0xD74DB452, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

                fix_ptr = _find_obj_in_obj_table(0x2E8B6D0E, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1E)

            else:  # Fishing Key is not collected, make sure the gate is closed
                fix_ptr = _find_obj_in_obj_table(0x42A3128E, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0xD74DB452, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

                fix_ptr = _find_obj_in_obj_table(0x2E8B6D0E, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

    if scene == b'B002':
        fix_ptr = _find_obj_in_obj_table(0xc71019dc, ptr, size)
        if not fix_ptr == None:
            if ctx.WYitC2_keys >= 3:
                fix_ptr = _find_obj_in_obj_table(0xc71019dc, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)

                fix_ptr = _find_obj_in_obj_table(0x0dcb1cd3, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

            else:
                fix_ptr = _find_obj_in_obj_table(0xc71019dc, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

                fix_ptr = _find_obj_in_obj_table(0x0dcb1cd3, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)

    if scene == b'B003':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.WYitC3_keys >= 4:
                fix_ptr = _find_obj_in_obj_table(0xE7196747, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr, 0)
                _set_platform_state(ctx, fix_ptr, 0)
                return
            else:
                _set_counter_value(ctx, fix_ptr, 4)

    if scene == b'C005':
        fix_ptr = _find_obj_in_obj_table(0xD6E6CB86, ptr, size)
        if not fix_ptr == None:
            if ctx.MCaC_keys >= 4:  # Keys collected, open the gate
                fix_ptr = _find_obj_in_obj_table(0xD6E6CB86, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

                fix_ptr = _find_obj_in_obj_table(0x44BC97A7, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x44BC97A8, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x44BC97A9, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x44BC97AA, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

            else:  # Keys not collected, make sure the gate is closed
                fix_ptr = _find_obj_in_obj_table(0xD6E6CB86, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

                fix_ptr = _find_obj_in_obj_table(0x44BC97A7, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x44BC97A8, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x44BC97A9, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x44BC97AA, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

    if scene == b'F005':
        fix_ptr = _find_obj_in_obj_table(0xD0798EC6, ptr, size)
        if not fix_ptr == None:
            if ctx.FCfS_keys >= 4:  # Keys collected, open the gate
                fix_ptr = _find_obj_in_obj_table(0xD0798EC6, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)

                fix_ptr = _find_obj_in_obj_table(0x7D81EA8F, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB518, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB519, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51A, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51B, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

            else:  # Keys not collected, make sure the gate is closed
                fix_ptr = _find_obj_in_obj_table(0xD0798EC6, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

                fix_ptr = _find_obj_in_obj_table(0x7D81EA8F, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB518, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB519, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51A, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51B, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

    if scene == b'G001':
        fix_ptr = _find_obj_in_obj_table(0x7fcdbe0f, ptr, size)
        if not fix_ptr == None:
            if ctx.TSfaGP_keys >= 3:  # The keys are collected, open the gate
                fix_ptr = _find_obj_in_obj_table(0x7fcdbe0f, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0xD77001EE, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

                fix_ptr = _find_obj_in_obj_table(0xA433F2EC, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

            else:  # Keys not collected, make sure the gate is closed
                fix_ptr = _find_obj_in_obj_table(0x7fcdbe0f, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0xD77001EE, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

                fix_ptr = _find_obj_in_obj_table(0xA433F2EC, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

    if scene == b'G007':
        fix_ptr = _find_obj_in_obj_table(0x0013c74b, ptr, size)
        if not fix_ptr == None:
            if ctx.GDDitT1_key >= 1:
                fix_ptr2 = _find_obj_in_obj_table(0x4A884EB4, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr2, 0)
                _set_platform_state(ctx, fix_ptr2, 0)

                fix_ptr2 = _find_obj_in_obj_table(0x4A884EB5, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr2, 0)
                _set_platform_state(ctx, fix_ptr2, 0)

                fix_ptr2 = _find_obj_in_obj_table(0x7FCDBE0F, ptr, size)
                if _check_platform_state(ctx, fix_ptr2) == 1:
                    _set_pickup_active(ctx, fix_ptr, 0x1f)
                    _set_platform_state(ctx, fix_ptr, 1)
                    _set_pickup_state(ctx, fix_ptr, 0x41)
                else:
                    _set_pickup_state(ctx, fix_ptr, 0x48)

            else:
                _set_pickup_active(ctx, fix_ptr, 0x1e)
                _set_platform_state(ctx, fix_ptr, 1)

    if scene == b'G009':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.GDDitT3_keys >= 2:
                return
            else:
                _set_counter_value(ctx, fix_ptr, 2)

    if scene == b'I003':
        fix_ptr = _find_obj_in_obj_table(0x13109411, ptr, size)
        if not fix_ptr == None:
            if ctx.CitM4_key >= 1:
                _set_pickup_active(ctx, fix_ptr, 0x1d)
                fix_ptr = _find_obj_in_obj_table(0x7B5AC815, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr, 0)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0xDa0349cc, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0x1e)
            else:
                _set_pickup_active(ctx, fix_ptr, 0x1c)

    if scene == b'I005':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.MyM2_keys >= 4:
                fix_ptr = _find_obj_in_obj_table(0xD4FBFFD9, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr, 0)
                _set_platform_state(ctx, fix_ptr, 0)
                return
            else:
                _set_counter_value(ctx, fix_ptr, 4)

    if scene == b'L011':
        fix_ptr = _find_obj_in_obj_table(0xD14760E8, ptr, size)
        if not fix_ptr == None:
            if ctx.CfsG1_keys >= 4:  # Keys collected, open the gate
                fix_ptr = _find_obj_in_obj_table(0xD14760E8, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)

                fix_ptr = _find_obj_in_obj_table(0x7334b00b, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB518, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB519, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51A, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51B, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

            else:  # Keys not collected, make sure the gate is closed
                fix_ptr = _find_obj_in_obj_table(0xD14760E8, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

                fix_ptr = _find_obj_in_obj_table(0x7334b00b, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB518, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB519, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51A, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51B, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

    if scene == b'O003':
        fix_ptr = _find_obj_in_obj_table(0xB418244E, ptr, size)
        if not fix_ptr == None:
            if ctx.PitA2_keys >= 3:  # Keys collected, open the gate
                fix_ptr = _find_obj_in_obj_table(0xB418244E, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

                fix_ptr = _find_obj_in_obj_table(0x9F625B9C, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB518, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB519, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51A, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

            else:  # Keys not collected, make sure the gate is closed
                fix_ptr = _find_obj_in_obj_table(0xB418244E, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

                fix_ptr = _find_obj_in_obj_table(0x09F625B9C, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB518, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB519, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51A, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

    if scene == b'O006':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.ADaSK2_keys >= 4:
                fix_ptr = _find_obj_in_obj_table(0x4DE2CB91, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr, 0)
                _set_platform_state(ctx, fix_ptr, 0)
                fix_ptr = _find_obj_in_obj_table(0xc9e0fb6A, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)
                return
            else:
                _set_counter_value(ctx, fix_ptr, 4)

    if scene == b'P002':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.CCitH2_keys >= 4:
                fix_ptr = _find_obj_in_obj_table(0xE7196746, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr, 0)
                _set_platform_state(ctx, fix_ptr, 0)
                fix_ptr = _find_obj_in_obj_table(0x4ac3ac06, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)
            else:
                _set_counter_value(ctx, fix_ptr, 4)
            fix_ptr = _find_obj_in_obj_table(0x0a1efb96, ptr, size)
            if ctx.CCitH2_keys >= 5:
                _set_pickup_active(ctx, fix_ptr, 0x1d)
                fix_ptr = _find_obj_in_obj_table(0xE7196749, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr, 0)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0xE719674B, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr, 0)
                _set_platform_state(ctx, fix_ptr, 0)
            else:
                _set_pickup_active(ctx, fix_ptr, 0x1c)

    if scene == b'P003':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.CCitH3_keys >= 3:
                return
            else:
                _set_counter_value(ctx, fix_ptr, 3)

    if scene == b'P004':
        fix_ptr = _find_obj_in_obj_table(0x0a1efb92, ptr, size)
        if not fix_ptr == None:
            if ctx.GAU1_key >= 1:
                _set_pickup_active(ctx, fix_ptr, 0x1d)
                fix_ptr = _find_obj_in_obj_table(0xE7196747, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr, 0)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x18E5F2D9, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)
            else:
                _set_pickup_active(ctx, fix_ptr, 0x1c)

    if scene == b'P005':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.GAU2_keys >= 4:
                fix_ptr = _find_obj_in_obj_table(0xB3FDF2CE, ptr, size)
                _set_platform_collision_state(ctx, fix_ptr, 0)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0xA25C26B4, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)
                _set_platform_state(ctx, fix_ptr, 0)
                return
            else:
                _set_counter_value(ctx, fix_ptr, 4)

    if scene == b'R005':
        fix_ptr = _find_obj_in_obj_table(0xc71019dc, ptr, size)
        if not fix_ptr == None:
            if ctx.DLDS2_keys >= 3:
                fix_ptr = _find_obj_in_obj_table(0xc71019dc, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

                fix_ptr = _find_obj_in_obj_table(0x510f16db, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1E)

            else:
                fix_ptr = _find_obj_in_obj_table(0xc71019dc, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

                fix_ptr = _find_obj_in_obj_table(0x510f16db, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

    if scene == b'W027':
        fix_ptr = _find_obj_in_obj_table(0xD2c0b719, ptr, size)
        if not fix_ptr == None:
            if ctx.SYTS1_keys >= 4:  # Keys collected, open the gate
                fix_ptr = _find_obj_in_obj_table(0xD2c0b719, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

                fix_ptr = _find_obj_in_obj_table(0x7D81EA8F, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB518, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB519, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51A, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51B, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

            else:  # Keys not collected, make sure the gate is closed
                fix_ptr = _find_obj_in_obj_table(0xD2c0b719, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1e)

                fix_ptr = _find_obj_in_obj_table(0x7D81EA8F, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1f)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB518, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB519, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51A, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)

                fix_ptr = _find_obj_in_obj_table(0x1F0FB51B, ptr, size)
                _set_platform_state(ctx, fix_ptr, 1)


async def update_key_items(ctx: NO100FContext):
    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR)
    ctx.CitM1_key = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 1)
    ctx.hedge_key = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 2)
    ctx.fish_key = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 3)
    ctx.WYitC2_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 4)
    ctx.WYitC3_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 5)
    ctx.MCaC_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 6)
    ctx.FCfS_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 7)
    ctx.TSfaGP_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 8)
    ctx.GDDitT1_key = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 9)
    ctx.GDDitT3_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 10)
    ctx.CitM4_key = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 11)
    ctx.MyM2_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 12)
    ctx.CfsG1_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 13)
    ctx.PitA2_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 14)
    ctx.ADaSK2_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 15)
    ctx.CCitH2_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 16)
    ctx.CCitH3_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 17)
    ctx.GAU1_key = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 18)
    ctx.GAU2_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 19)
    ctx.DLDS2_keys = count

    count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + 20)
    ctx.SYTS1_keys = count


async def give_items(ctx: NO100FContext):
    if ctx.use_keys:
        await update_key_items(ctx)
    expected_idx = dolphin_memory_engine.read_word(EXPECTED_INDEX_ADDR)
    # we need to loop some items
    for item, idx in ctx.items_received_2:
        if check_control_owner(ctx, lambda owner: owner == 0):
            return
        if expected_idx <= idx:
            item_id = item.item
            _give_item(ctx, item_id)
            dolphin_memory_engine.write_word(EXPECTED_INDEX_ADDR, idx + 1)
            await asyncio.sleep(.01)  # wait a bit for values to update


def _check_pickup_state(ctx: NO100FContext, obj_ptr: int):
    if not _is_ptr_valid(obj_ptr + 0xec):
        return False
    obj_state = dolphin_memory_engine.read_word(obj_ptr + 0xec)
    return obj_state & 0x08 > 0 and obj_state & 0x37 == 0


def _set_pickup_state(ctx: NO100FContext, obj_ptr: int, state: int):
    if not _is_ptr_valid(obj_ptr + 0xef):
        return False
    dolphin_memory_engine.write_byte(obj_ptr + 0xef, state)


async def _check_objects_by_id(ctx: NO100FContext, locations_checked: set, id_table: dict, check_cb: Callable):
    scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    ptr = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_PTR_ADDR)
    if not _is_ptr_valid(ptr):
        return
    size = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_SIZE_ADDR)

    for k, v in id_table.items():
        if k in locations_checked:
            continue
        if v[0] is not None and v[0] != scene:
            continue
        for i in range(1, len(v)):
            obj_ptr = _find_obj_in_obj_table(v[i], ptr, size)
            if obj_ptr is None: break
            if obj_ptr == -1: continue

            # Shovel Fix
            if v[1] == Upgrades.ShovelPower.value:  # Only do this for the Shovel Power Up in H001

                fix_ptr = _find_obj_in_obj_table(0xD5159008, ptr, size)
                if fix_ptr is None: break

                dolphin_memory_engine.write_byte(fix_ptr + 0x7, 0x1d)  # Force Shovel Pickup Availability

            # Slippers Fix
            if v[1] == Upgrades.SlippersPower.value:  # Only do this for the Shovel Power Up in H001

                fix_ptr = _find_obj_in_obj_table(0xF08C8F07, ptr, size)
                if fix_ptr is None: break

                _set_counter_value(ctx, fix_ptr, 0xa0)  # Force Counter to large value

            # Black Knight Fix
            if v[1] == Upgrades.BootsPower.value:  #Only do this for the Boots Power Up in O008

                fix_ptr = _find_obj_in_obj_table(0x7B9BA1C7, ptr, size)
                if fix_ptr is None: break

                BK_Alive = dolphin_memory_engine.read_byte(fix_ptr + 0x15)  #Check Fight Over Counter
                if BK_Alive == 0:  #Is he dead?
                    locations_checked.add(k)
                    ctx.post_boss = True
                    boss_kills = dolphin_memory_engine.read_byte(BOSS_KILLS_ADDR)
                    boss_kills += 1
                    dolphin_memory_engine.write_byte(BOSS_KILLS_ADDR, boss_kills)

            # Green Ghost Fix
            if v[1] == Upgrades.UmbrellaPower.value:  # Only do this for the Umbrella Power Up in G009

                # Fix Check Itself
                fix_ptr = _find_obj_in_obj_table(0xB6C6E412, ptr, size)
                if fix_ptr is None: break

                GG_Defeated = dolphin_memory_engine.read_byte(fix_ptr + 0x16)
                if GG_Defeated == 0x1f:
                    locations_checked.add(k)
                    ctx.post_boss = True
                    boss_kills = dolphin_memory_engine.read_byte(BOSS_KILLS_ADDR)
                    boss_kills += 1
                    dolphin_memory_engine.write_byte(BOSS_KILLS_ADDR, boss_kills)

                # Fix Broken Fight Trigger
                fix_ptr1 = _find_obj_in_obj_table(0x060E343c, ptr, size)
                if fix_ptr1 is None: break

                dolphin_memory_engine.write_byte(fix_ptr1 + 0x7, 0x1d)  # Re-enable Key Counter
                GG_Alive = dolphin_memory_engine.read_byte(fix_ptr + 0x14)

                fix_ptr2 = _find_obj_in_obj_table(0xA11635BD, ptr, size)
                if fix_ptr2 is None: break

                if GG_Alive == 0 and GG_Defeated == 0x1b:  # Green Ghost has not been defeated, and he is not yet present
                    dolphin_memory_engine.write_byte(fix_ptr2 + 0x7, 0x1f)
                else:
                    dolphin_memory_engine.write_byte(fix_ptr2 + 0x7, 0x1e)

            # Red Beard Fix
            if v[1] == Upgrades.GumPower.value:  # Only do this for the Gum Powerup in W028

                fix_ptr = _find_obj_in_obj_table(0x5A3B5C98, ptr, size)
                if fix_ptr is None: break

                RB_Alive = dolphin_memory_engine.read_byte(fix_ptr + 0x15)  # Check Fight Over Counter
                if RB_Alive == 0:  # Is he dead?
                    locations_checked.add(k)
                    ctx.post_boss = True
                    boss_kills = dolphin_memory_engine.read_byte(BOSS_KILLS_ADDR)
                    boss_kills += 1
                    dolphin_memory_engine.write_byte(BOSS_KILLS_ADDR, boss_kills)

            if check_cb(ctx, obj_ptr):
                locations_checked.add(k)

                # Lampshade/Slippers Fix
                if v[1] == Upgrades.SlippersPower.value:  # We are checking the slipper power up
                    locations_checked.add(k + 1)  # Add the lampshade check as well

                    fix_ptr = _find_obj_in_obj_table(0xF08C8F07, ptr, size)
                    _set_counter_value(ctx, fix_ptr, 0x1)  # Force Counter to 1

                break


async def _check_upgrades(ctx: NO100FContext, locations_checked: set):
    await _check_objects_by_id(ctx, locations_checked, UPGRADES_PICKUP_IDS, _check_pickup_state)


async def _check_monstertokens(ctx: NO100FContext, locations_checked: set):
    await _check_objects_by_id(ctx, locations_checked, MONSTERTOKENS_PICKUP_IDS, _check_pickup_state)


async def _check_keys(ctx: NO100FContext, locations_checked: set):
    await _check_objects_by_id(ctx, locations_checked, KEYS_PICKUP_IDS, _check_pickup_state)


async def _check_warpgates(ctx: NO100FContext, locations_checked: set):
    await _check_warpgates_location(ctx, locations_checked, WARPGATE_PICKUP_IDS)


# async def _check_snacks(ctx: NO100FContext, locations_checked: set):
#    await _check_objects_by_id(ctx, locations_checked, SNACKIDS, _check_pickup_state)

async def _check_warpgates_location(ctx: NO100FContext, locations_checked: set, id_table : dict):
    scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    ptr = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_PTR_ADDR)
    if not _is_ptr_valid(ptr):
        return
    size = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_SIZE_ADDR)

    for k, v in id_table.items():
        if k in locations_checked:
            continue
        if v[0] is not None and v[0] != scene:
            continue
        bit = k - 300 - base_id
        value = dolphin_memory_engine.read_word(WARP_ADDR + (12 * bit))
        if value == 1:
            locations_checked.add(k)

    warp_gates = dolphin_memory_engine.read_word(SAVED_WARP_ADDR)
    if warp_gates == 0:
        dolphin_memory_engine.write_word(SAVED_WARP_ADDR, 0X400)
    for i in range(26):
        if warp_gates & 2 ** i == 2 ** i:
            dolphin_memory_engine.write_word(WARP_ADDR + (12 * i), 1)
        else:
            dolphin_memory_engine.write_word(WARP_ADDR + (12 * i), 0)

async def enable_map_warping(ctx: NO100FContext):
    scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    ptr = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_PTR_ADDR)
    if not _is_ptr_valid(ptr):
        return
    size = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_SIZE_ADDR)

    fix_ptr = _find_obj_in_obj_table(0x8542BAD4, ptr, size)
    if not fix_ptr == None:
        for i in range(18):
            _set_trigger_state(ctx, fix_ptr + (0x14 * i), 0x1d)

    fix_ptr = _find_obj_in_obj_table(0x6887e731, ptr, size)
    if not fix_ptr == None:
        for i in range(7):
            _set_trigger_state(ctx, fix_ptr + (0x14 * i), 0x1d)
    if ctx.use_warpgates:
        saved_warps = dolphin_memory_engine.read_word(SAVED_WARP_ADDR)
        if not saved_warps & 2**8:  # Haven't found Crypt Warp
            dolphin_memory_engine.write_word(0x801B7F54, 1)
            fix_ptr = _find_obj_in_obj_table(0x78A1C3B8, ptr, size)
            _set_trigger_state(ctx, fix_ptr, 0x1c)


async def apply_level_fixes(ctx: NO100FContext):
    scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    ptr = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_PTR_ADDR)
    if not _is_ptr_valid(ptr):
        return
    size = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_SIZE_ADDR)

    dolphin_memory_engine.write_word(MAP_ADDR, 0x1)  # Force the Map Into Inventory
    if scene == b'I001':
        upgrades = dolphin_memory_engine.read_word(UPGRADE_INVENTORY_ADDR)
        if not upgrades & 2 ** 13:  # Player does not have the shovel, give them a fake
            upgrades += (2 ** 13 + 2 ** 7)
            dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, upgrades)

        fix_ptr = _find_obj_in_obj_table(0x22B1A6E6, ptr, size)  # Holly Trigger #1
        _set_trigger_state(ctx, fix_ptr, 0x1c)

        fix_ptr = _find_obj_in_obj_table(0xC0E867E2, ptr, size)  # Holly Trigger #2
        _set_trigger_state(ctx, fix_ptr, 0x1e)

        fix_ptr = _find_obj_in_obj_table(0xFA854786, ptr, size)  # Holly Collision and Visibility Disabled
        _set_platform_collision_state(ctx, fix_ptr, 0)
        _set_platform_state(ctx, fix_ptr, 0)

        if _is_scene_visited(b'R001'):
            fix_ptr = _find_obj_in_obj_table(0x4f81e846, ptr, size)  # Doorway Trigger
            _set_trigger_state(ctx, fix_ptr, 0x1d)

            fix_ptr = _find_obj_in_obj_table(0xDE90259F, ptr, size)  # Text Trigger
            _set_trigger_state(ctx, fix_ptr, 0x1c)

        if _is_scene_visited(b'S005'):
            fix_ptr = _find_obj_in_obj_table(0xB0d216d1, ptr, size)  # Load Trigger
            _set_trigger_state(ctx, fix_ptr, 0x1d)

            fix_ptr = _find_obj_in_obj_table(0xc402cded, ptr, size)  # Disable Armoire Collision and Visibility
            _set_platform_collision_state(ctx, fix_ptr, 0)
            _set_platform_state(ctx, fix_ptr, 0x1c)

    if scene == b'E001':
        upgrades = dolphin_memory_engine.read_word(UPGRADE_INVENTORY_ADDR)
        if not upgrades & 2 ** 13:  # Player does not have the shovel, give them a fake
            upgrades += (2 ** 13 + 2 ** 7)
            dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, upgrades)

        if upgrades & 2 ** 7:  # Player has a fake shovel, don't let them dig
            fix_ptr = _find_obj_in_obj_table(0xb37f36c7, ptr, size)
            _set_trigger_state(ctx, fix_ptr, 0x1c)

    if scene == b'F001':
        upgrades = dolphin_memory_engine.read_word(UPGRADE_INVENTORY_ADDR)
        if not upgrades & 2 ** 13:  # Player does not have the shovel, give them a fake
            upgrades += (2 ** 13 + 2 ** 7)
            dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, upgrades)

    if scene == b'H002':
        upgrades = dolphin_memory_engine.read_word(UPGRADE_INVENTORY_ADDR)
        if not upgrades & 2 ** 13:  # Player does not have the shovel, give them a fake
            upgrades += (2 ** 13 + 2 ** 7)
            dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, upgrades)

    if scene == b'H003':
        upgrades = dolphin_memory_engine.read_word(UPGRADE_INVENTORY_ADDR)
        if not upgrades & 2 ** 13:  # Player does not have the shovel, give them a fake
            upgrades += (2 ** 13 + 2 ** 7)
            dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, upgrades)

    if not (scene == b'I001' or scene == b'E001' or scene == b'F001' or scene == b'H002' or scene == b'H003'):
        upgrades = dolphin_memory_engine.read_word(UPGRADE_INVENTORY_ADDR)
        if upgrades & 2 ** 7:  # Player has a fake shovel, get rid of it
            upgrades -= (2 ** 7 + 2 ** 13)
            dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, upgrades)

    if scene == b'h001':
        if ctx.use_warpgates:
            cur_snacks = dolphin_memory_engine.read_word(SNACK_COUNT_ADDR)
            if cur_snacks == 0:
                dolphin_memory_engine.write_word(SNACK_COUNT_ADDR, 400)

    if scene == b'H001' or b'h001':

        # Clear Monster Gallery Snack Gate
        fix_ptr = _find_obj_in_obj_table(0x7E8E16F5, ptr, size)
        if not fix_ptr == None:
            _set_platform_state(ctx, fix_ptr, 0)
            fix_ptr = _find_obj_in_obj_table(0xD7924F8A, ptr, size)
            _set_trigger_state(ctx, fix_ptr, 0x1f)

        if not ctx.use_keys:
            fix_ptr = _find_obj_in_obj_table(0xBBFA4948, ptr, size)
            if not fix_ptr == None:
                if _check_pickup_state(ctx, fix_ptr):  #The Hedge key is collected, open the gate
                    fix_ptr = _find_obj_in_obj_table(0xC20224F3, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)

                    fix_ptr = _find_obj_in_obj_table(0xE8B3FF9B, ptr, size)
                    _set_trigger_state(ctx, fix_ptr, 0x1c)

                    fix_ptr = _find_obj_in_obj_table(0xD72B66B7, ptr, size)
                    _set_trigger_state(ctx, fix_ptr, 0x1d)

            fix_ptr = _find_obj_in_obj_table(0xBB82B3B3, ptr, size)
            if not fix_ptr == None:
                if _check_pickup_state(ctx, fix_ptr):  #The Fishing key is collected, open the gate
                    fix_ptr = _find_obj_in_obj_table(0x42A3128E, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)

    if scene == b'R021':
        if _is_scene_visited(b'R003'):
            fix_ptr = _find_obj_in_obj_table(0xcbd0A98D, ptr, size)  # Holly Collision and Visibility Disabled
            _set_platform_collision_state(ctx, fix_ptr, 0)
            _set_platform_state(ctx, fix_ptr, 0)

    if scene == b"P003":
        fix_ptr = _find_obj_in_obj_table(0x0A1EFB92, ptr, size)
        if not fix_ptr == None:
            if ctx.previous_scene == b'P004' and _check_platform_state(ctx, fix_ptr) == 1:
                dolphin_memory_engine.write_word(HEALTH_ADDR, 5)    # Give scooby health to teleport out if entering creepy backwards

    # Credits Location
    if scene == b"S005":  #We are in the final room

        if not ctx.completion_goal == 0:
            fix_ptr = _find_obj_in_obj_table(0x79f90e17, ptr, size)
            if fix_ptr is not None:
                in_arena = dolphin_memory_engine.read_byte(fix_ptr + 0x7)
                conditions_met = False
                if ctx.completion_goal == 1:    #Fixes for all bosses
                    bosseskilled = dolphin_memory_engine.read_byte(BOSS_KILLS_ADDR)
                    if bosseskilled == 3:
                        conditions_met = True

                if ctx.completion_goal == 2:
                    tokens = dolphin_memory_engine.read_word(MONSTER_TOKEN_INVENTORY_ADDR)
                    if tokens == 0x1FFFFF:
                        conditions_met = True

                if conditions_met and in_arena == 0x1d:
                    fix_ptr = _find_obj_in_obj_table(0x2b2cea8a, ptr, size)
                    _set_trigger_state(ctx, fix_ptr, 0x1f)
                elif not conditions_met:
                    fix_ptr = _find_obj_in_obj_table(0x2b2cea8a, ptr, size)
                    _set_trigger_state(ctx, fix_ptr, 0x1e)
                    fix_ptr = _find_obj_in_obj_table(0x78CFEF58, ptr, size)
                    _set_trigger_state(ctx, fix_ptr, 0x1c)
                    fix_ptr = _find_obj_in_obj_table(0x3C433393, ptr, size)
                    _set_trigger_state(ctx, fix_ptr, 0x1c)
                    fix_ptr = _find_obj_in_obj_table(0x0C413492, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)
                    fix_ptr = _find_obj_in_obj_table(0x9AA96044, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)
                    fix_ptr = _find_obj_in_obj_table(0xCF095CD7, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)
                    fix_ptr = _find_obj_in_obj_table(0x1480DF86, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)
                    fix_ptr = _find_obj_in_obj_table(0xD046F599, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)
                    fix_ptr = _find_obj_in_obj_table(0x08E9D051, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)

                if not conditions_met and in_arena == 0x1c:
                    fix_ptr = _find_obj_in_obj_table(0x2854c118, ptr, size)
                    _set_platform_collision_state(ctx, fix_ptr, 0)
                    _set_platform_state(ctx, fix_ptr, 0)

                if conditions_met and in_arena == 0x1c:
                    fix_ptr = _find_obj_in_obj_table(0x2b2cea8a, ptr, size)
                    _set_trigger_state(ctx, fix_ptr, 0x1e)



        if not ctx.finished_game:  # We have not finished
            fix_ptr = _find_obj_in_obj_table(0x21D3EDA4, ptr, size)
            if fix_ptr is not None:
                MM_Alive = dolphin_memory_engine.read_byte(fix_ptr + 0x15)
                if MM_Alive == 0:
                    print("send done")
                    await ctx.send_msgs([
                        {"cmd": "StatusUpdate",
                         "status": 30}
                    ])
                    ctx.finished_game = True
                    ctx.post_boss = True


async def check_locations(ctx: NO100FContext):
    await _check_upgrades(ctx, ctx.locations_checked)
    if ctx.use_tokens:
        await _check_monstertokens(ctx, ctx.locations_checked)
    if ctx.use_keys:
        await _check_keys(ctx, ctx.locations_checked)
    if ctx.use_warpgates:
        await _check_warpgates(ctx, ctx.locations_checked)

    # ignore already in server state
    locations_checked = ctx.locations_checked.difference(ctx.checked_locations)
    if locations_checked:
        await ctx.send_msgs([
            {"cmd": "LocationChecks",
             "locations": locations_checked}
        ])
        print([ctx.location_names[location] for location in locations_checked])


async def check_alive(ctx: NO100FContext):
    cur_health = dolphin_memory_engine.read_word(HEALTH_ADDR)
    return not (cur_health <= 0 or check_control_owner(ctx, lambda owner: owner == 0))


async def check_death(ctx: NO100FContext):
    cur_health = dolphin_memory_engine.read_word(HEALTH_ADDR)

    if cur_health > 0:
        ctx.forced_death = False

    if cur_health <= 0 and not ctx.forced_death and not ctx.post_boss:
        if dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR,
                                            0x4) == b'F003':  # Avoid Creepy Early Trigger causing erroneous DL Sends
            await asyncio.sleep(3)
            if dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4) != b'F003':
                return
        if not ctx.has_send_death and time.time() >= ctx.last_death_link + 3:
            ctx.has_send_death = True
            await ctx.send_death("NO100F")
    else:
        ctx.has_send_death = False


def check_ingame(ctx: NO100FContext, ignore_control_owner: bool = False) -> bool:
    scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    if scene not in valid_scenes:
        return False
    update_current_scene(ctx, scene.decode('ascii'))
    return True


def update_current_scene(ctx: NO100FContext, scene: str):
    if not ctx.slot and not ctx.auth:
        return
    if ctx.current_scene_key is None or ctx.current_scene_key not in ctx.stored_data:
        return
    if ctx.stored_data[ctx.current_scene_key] == scene:
        return
    Utils.async_start(ctx.send_msgs([{
        "cmd": "Set",
        "key": ctx.current_scene_key,
        "default": None,
        "want_reply": True,
        "operations": [{
            "operation": "replace",
            "value": scene,
        }],
    }]))


def check_control_owner(ctx: NO100FContext, check_cb: Callable[[int], bool]) -> bool:
    owner = dolphin_memory_engine.read_word(PLAYER_CONTROL_OWNER)
    return check_cb(owner)


async def save_warp_gates(ctx: NO100FContext):
    warp_gate_map = 0
    await asyncio.sleep(1)
    for i in range(26):
        cur_gate = dolphin_memory_engine.read_word(WARP_ADDR + (12 * i))
        if cur_gate == 1:
            warp_gate_map += 2 ** i

    if warp_gate_map == 0x400:  # The game is at the default state, attempt to load instead of saving
        if not dolphin_memory_engine.read_word(SAVED_WARP_ADDR) == 0 and not _check_cur_scene(ctx, b'MNU3'):
            await load_warp_gates(ctx)
        return

    dolphin_memory_engine.write_word(SAVED_WARP_ADDR, warp_gate_map)


async def load_warp_gates(ctx: NO100FContext):
    warp_gates = dolphin_memory_engine.read_word(SAVED_WARP_ADDR)
    if warp_gates == 0:
        dolphin_memory_engine.write_word(SAVED_WARP_ADDR, 0X400)
    for i in range(26):
        if warp_gates & 2 ** i == 2 ** i:
            dolphin_memory_engine.write_word(WARP_ADDR + (12 * i), 1)
        else:
            dolphin_memory_engine.write_word(WARP_ADDR + (12 * i), 0)


async def force_death(ctx: NO100FContext):
    cur_health = dolphin_memory_engine.read_word(HEALTH_ADDR)

    if cur_health == 69 and not ctx.post_boss:  # Funny number, but also good luck accidentally setting your health this high
        ctx.forced_death = True
        dolphin_memory_engine.write_word(HEALTH_ADDR, 0)


def validate_save(ctx: NO100FContext) -> bool:
    saved_slot_bytes = dolphin_memory_engine.read_bytes(SAVED_SLOT_NAME_ADDR, 0x40).strip(b'\0')
    slot_bytes = dolphin_memory_engine.read_bytes(SLOT_NAME_ADDR, 0x40).strip(b'\0')
    saved_seed_bytes = dolphin_memory_engine.read_bytes(SAVED_SEED_ADDR, 0x10).strip(b'\0')
    seed_bytes = dolphin_memory_engine.read_bytes(SEED_ADDR, 0x10).strip(b'\0')
    if len(slot_bytes) > 0 and len(seed_bytes) > 0:
        if len(saved_slot_bytes) == 0 and len(saved_seed_bytes) == 0:
            # write info to save
            dolphin_memory_engine.write_bytes(SAVED_SLOT_NAME_ADDR, slot_bytes)
            dolphin_memory_engine.write_bytes(SAVED_SEED_ADDR, seed_bytes)
            return True
        elif slot_bytes == saved_slot_bytes and seed_bytes == saved_seed_bytes:
            return True
    return False


async def dolphin_sync_task(ctx: NO100FContext):
    logger.info("Starting Dolphin connector. Use /dolphin for status information")
    while not ctx.exit_event.is_set():
        try:
            if dolphin_memory_engine.is_hooked() and ctx.dolphin_status == CONNECTION_CONNECTED_STATUS:
                if not check_ingame(ctx):
                    # reset AP values when on main menu
                    if _check_cur_scene(ctx, b'MNU3'):
                        for i in range(0, 0x80, 0x4):
                            cur_val = dolphin_memory_engine.read_word(EXPECTED_INDEX_ADDR + i)
                            if cur_val != 0:
                                dolphin_memory_engine.write_word(EXPECTED_INDEX_ADDR + i, 0)

                    await asyncio.sleep(.1)
                    continue
                # _print_player_info(ctx)
                if ctx.slot:
                    if not validate_save(ctx):
                        logger.info(CONNECTION_REFUSED_SAVE_STATUS)
                        ctx.dolphin_status = CONNECTION_REFUSED_SAVE_STATUS
                        dolphin_memory_engine.un_hook()
                        await ctx.disconnect()
                        await asyncio.sleep(5)
                        continue
                    ctx.current_scene_key = f"NO100F_current_scene_T{ctx.team}_P{ctx.slot}"
                    ctx.set_notify(ctx.current_scene_key)
                    if not _check_cur_scene(ctx, ctx.current_scene):
                        scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 4)
                        ctx.previous_scene = ctx.current_scene
                        ctx.current_scene = scene
                    if "DeathLink" in ctx.tags:
                        await check_death(ctx)
                    await give_items(ctx)
                    await check_locations(ctx)
                    await apply_level_fixes(ctx)
                    if not ctx.use_warpgates:
                        await save_warp_gates(ctx)
                    if ctx.use_keys:
                        await apply_key_fixes(ctx)
                    await force_death(ctx)
                    await enable_map_warping(ctx)
                    if not (_check_cur_scene(ctx, b'O008') or _check_cur_scene(ctx, b'S005') or _check_cur_scene(ctx,
                                                                                                                 b'G009') or _check_cur_scene(
                            ctx, b'W028')):
                        ctx.post_boss = False
                else:
                    if not ctx.auth:
                        ctx.auth = dolphin_memory_engine.read_bytes(SLOT_NAME_ADDR, 0x40).decode('utf-8').strip(
                            '\0')
                        if ctx.auth == '\x02\x00\x00\x00\x04\x00\x00\x00\x02\x00\x00\x00\x04\x00\x00\x00\x02\x00\x00' \
                                       '\x00\x02\x00\x00\x00\x04\x00\x00\x00\x04':
                            logger.info("Vanilla game detected. Please load the patched game.")
                            ctx.dolphin_status = CONNECTION_REFUSED_GAME_STATUS
                            ctx.awaiting_rom = False
                            dolphin_memory_engine.un_hook()
                            await ctx.disconnect()
                            await asyncio.sleep(5)
                    if ctx.awaiting_rom:
                        await ctx.server_auth()
                await asyncio.sleep(.5)
            else:
                if ctx.dolphin_status == CONNECTION_CONNECTED_STATUS:
                    logger.info("Connection to Dolphin lost, reconnecting...")
                    ctx.dolphin_status = CONNECTION_LOST_STATUS
                logger.info("Attempting to connect to Dolphin")
                dolphin_memory_engine.hook()
                if dolphin_memory_engine.is_hooked():
                    if dolphin_memory_engine.read_bytes(0x80000000, 6) == b'GIHE78':
                        logger.info(CONNECTION_CONNECTED_STATUS)
                        ctx.dolphin_status = CONNECTION_CONNECTED_STATUS
                        ctx.locations_checked = set()
                    else:
                        logger.info(CONNECTION_REFUSED_GAME_STATUS)
                        ctx.dolphin_status = CONNECTION_REFUSED_GAME_STATUS
                        dolphin_memory_engine.un_hook()
                        await asyncio.sleep(1)
                else:
                    logger.info("Connection to Dolphin failed, attempting again in 5 seconds...")
                    ctx.dolphin_status = CONNECTION_LOST_STATUS
                    await ctx.disconnect()
                    await asyncio.sleep(5)
                    continue
        except Exception:
            dolphin_memory_engine.un_hook()
            logger.info("Connection to Dolphin failed, attempting again in 5 seconds...")
            logger.error(traceback.format_exc())
            ctx.dolphin_status = CONNECTION_LOST_STATUS
            await ctx.disconnect()
            await asyncio.sleep(5)
            continue


async def patch_and_run_game(ctx: NO100FContext, patch_file):
    try:
        result_path = os.path.splitext(patch_file)[0] + NO100FDeltaPatch.result_file_ending
        with zipfile.ZipFile(patch_file, 'r') as patch_archive:
            if not NO100FDeltaPatch.check_version(patch_archive):
                logger.error(
                    "apNO100F version doesn't match this client.  Make sure your generator and client are the same")
                raise Exception("apNO100F version doesn't match this client.")

        # check hash
        NO100FDeltaPatch.check_hash()

        shutil.copy(NO100FDeltaPatch.get_rom_path(), result_path)
        await NO100FDeltaPatch.apply_binary_changes(zipfile.ZipFile(patch_file, 'r'), result_path)

        logger.info('--patching success--')
        os.startfile(result_path)

    except Exception as msg:
        logger.info(msg, extra={'compact_gui': True})
        logger.debug(traceback.format_exc())
        ctx.gui_error('Error', msg)


def main(connect=None, password=None, patch_file=None):
    # Text Mode to use !hint and such with games that have no text entry
    Utils.init_logging("NO100FClient")

    # logger.warning(f"starting {connect}, {password}, {patch_file}")

    async def _main(connect, password, patch_file):
        ctx = NO100FContext(connect, password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()

        ctx.patch_task = None
        if patch_file:
            ext = os.path.splitext(patch_file)[1]
            if ext == NO100FDeltaPatch.patch_file_ending:
                logger.info("apNO100F file supplied, beginning patching process...")
                ctx.patch_task = asyncio.create_task(patch_and_run_game(ctx, patch_file), name="PatchGame")
            elif ext == NO100FDeltaPatch.result_file_ending:
                os.startfile(patch_file)
            else:
                logger.warning(f"Unknown patch file extension {ext}")

        if ctx.patch_task:
            await ctx.patch_task

        await asyncio.sleep(1)

        ctx.dolphin_sync_task = asyncio.create_task(dolphin_sync_task(ctx), name="DolphinSync")

        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()

        if ctx.dolphin_sync_task:
            await asyncio.sleep(3)
            await ctx.dolphin_sync_task

    import colorama

    colorama.init()
    asyncio.run(_main(connect, password, patch_file))
    colorama.deinit()


if __name__ == '__main__':
    parser = get_base_parser()
    parser.add_argument('patch_file', default="", type=str, nargs="?",
                        help='Path to an .apno100f patch file')
    args = parser.parse_args()
    main(args.connect, args.password, args.patch_file)
