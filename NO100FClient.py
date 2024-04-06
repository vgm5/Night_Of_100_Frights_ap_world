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
SNACK_COUNT_ADDR = 0x80235094   #4 Bytes
UPGRADE_INVENTORY_ADDR = 0x80235098 #4 Bytes
MONSTER_TOKEN_INVENTORY_ADDR = 0x8023509C   #4 Bytes
MAX_GUM_COUNT_ADDR = 0x802350A8
MAX_SOAP_COUNT_ADDR = 0x802350AC
PLAYER_CONTROL_OWNER = 0x80234e90
MAP_ADDR = 0x8025F140
WARP_ADDR = 0x801b7ef4

SLOT_NAME_ADDR = 0x801c5c9c
SEED_ADDR = SLOT_NAME_ADDR + 0x40
# we currently write/read 0x20 bytes starting from 0x817f0000 to/from save game
# expected received item index
EXPECTED_INDEX_ADDR = 0x817f0000
KEY_COUNT_ADDR = 0x817f0004
SAVED_WARP_ADDR = 0x817f001C
# delayed item
SAVED_SLOT_NAME_ADDR = 0x817f0020
SAVED_SEED_ADDR = SAVED_SLOT_NAME_ADDR + 0x40


class Upgrades(Enum):               #Bit assigned at 0x80235098
    GumPower         = 0xD4FD7D3C   #xxxx xxxx xxxx xxxx x000 0000 0000 0001
    SoapPower        = 0xE8A3B45F   #xxxx xxxx xxxx xxxx x000 0000 0000 0010
    BootsPower       = 0x9133CECD   #xxxx xxxx xxxx xxxx x000 0000 0000 0100
    PlungerPower     = 0xDA82A36C   #xxxx xxxx xxxx xxxx x000 0000 0000 1000
    SlippersPower    = 0x9AD0813E   #xxxx xxxx xxxx xxxx x000 0000 0001 0000
    LampshadePower   = 0x6FAFFB01   #xxxx xxxx xxxx xxxx x000 0000 0010 0000
    BlackKnightPower = 0xB00E719E   #xxxx xxxx xxxx xxxx x000 0000 0100 0000
    SpringPower      = 0xD88133D6   #xxxx xxxx xxxx xxxx x000 0010 0000 0000
    PoundPower       = 0x84D3E950   #xxxx xxxx xxxx xxxx x000 0100 0000 0000
    HelmetPower      = 0x2F03BFDC   #xxxx xxxx xxxx xxxx x000 1000 0000 0000
    UmbrellaPower    = 0xC889BB9E   #xxxx xxxx xxxx xxxx x001 0000 0000 0000
    ShovelPower      = 0x866C5887   #xxxx xxxx xxxx xxxx x010 0000 0000 0000
    ShockwavePower   = 0x1B0ADE07   #xxxx xxxx xxxx xxxx x100 0000 0000 0000
    GumOverAcid2     = 0xEAF330FE   #Gum upgrades increment 0x802350A8 by 5.
    GumPack          = 0xFFD0E61E
    GumMaxAmmo       = 0xFFFD7A85
    Gum_Upgrade      = 0x362E34B4
    GumUpgrade       = 0x7EDE8BAD
    BubblePack       = 0xBF9B5D09
    Soap__Box        = 0xD656A182   #Soap upgrades increment 0x802350AC by 5
    SoapBox1         = 0x3550C423
    SoapOverAcid2    = 0x0C7A534E
    Soap_Box         = 0xDEC7BAA7
    SoapBox          = 0xB380CBF0
    SoapPack         = 0xDCC4E558


class MonsterTokens(Enum):          #Bit assigned at 0x8023509C
    MT_BLACKKNIGHT = 0x3A6FCC38     #xxxx xxxx xxx0 0000 0000 0000 0000 0001
    MT_MOODY       = 0xDC98824E     #xxxx xxxx xxx0 0000 0000 0000 0000 0010
    MT_CAVEMAN     = 0x56400EF1     #xxxx xxxx xxx0 0000 0000 0000 0000 0100
    MT_CREEPER     = 0xDFA0C15E     #xxxx xxxx xxx0 0000 0000 0000 0000 1000
    MT_GARGOYLE    = 0xFBBC715F     #xxxx xxxx xxx0 0000 0000 0000 0001 0000
    MT_GERONIMO    = 0x94C56BF0     #xxxx xxxx xxx0 0000 0000 0000 0010 0000
    MT_GHOST       = 0x74004B8A     #xxxx xxxx xxx0 0000 0000 0000 0100 0000
    MT_GHOSTDIVER  = 0x2ACB9327     #xxxx xxxx xxx0 0000 0000 0000 1000 0000
    MT_GREENGHOST  = 0xF077B0E1     #xxxx xxxx xxx0 0000 0000 0001 0000 0000
    MT_HEADLESS    = 0x52CE630A     #xxxx xxxx xxx0 0000 0000 0010 0000 0000
    MT_MASTERMIND  = 0x08D04C9B     #xxxx xxxx xxx0 0000 0000 0100 0000 0000
    MT_ROBOT       = 0x699623C9     #xxxx xxxx xxx0 0000 0000 1000 0000 0000
    MT_REDBEARD    = 0x0F7F79CB     #xxxx xxxx xxx0 0000 0001 0000 0000 0000
    MT_SCARECROW   = 0xAB19F726     #xxxx xxxx xxx0 0000 0010 0000 0000 0000
    MT_SEACREATURE = 0x6CC29412     #xxxx xxxx xxx0 0000 0100 0000 0000 0000
    MT_SPACEKOOK   = 0xFC42FAAC     #xxxx xxxx xxx0 0000 1000 0000 0000 0000
    MT_TARMONSTER  = 0x2E849EB9     #xxxx xxxx xxx0 0001 0000 0000 0000 0000
    MT_WITCH       = 0x8CFF4526     #xxxx xxxx xxx0 0010 0000 0000 0000 0000
    MT_WITCHDOC    = 0x55794316     #xxxx xxxx xxx0 0100 0000 0000 0000 0000
    MT_WOLFMAN     = 0x51D4A7D2     #xxxx xxxx xxx0 1000 0000 0000 0000 0000
    MT_ZOMBIE      = 0x818F2933     #xxxx xxxx xxx1 0000 0000 0000 0000 0000


class Keys(Enum):
    DOORKEY         = 0x13109411
    DOORKEY1        = 0xC17BC4E4
    DOORKEY2        = 0xC17BC4E5
    DOORKEY3        = 0xC17BC4E6
    DOORKEY4        = 0xC17BC4E7
    DUG_FISHING_KEY = 0xBB82B3B3
    HEDGE_KEY       = 0xBBFA4948
    KEY             = 0x0013C74B
    KEY_01          = 0x76E9B34A
    KEY_02          = 0x76E9B34B
    KEY_03          = 0x76E9B34C
    KEY_1           = 0x2DDAB334
    KEY_2           = 0x2DDAB335
    KEY_3           = 0x2DDAB336
    KEY_4           = 0x2DDAB337
    KEY01           = 0x2DDABB64
    KEY02           = 0x2DDABB65
    KEY03           = 0x2DDABB66
    KEY04           = 0x2DDABB67
    KEY1            = 0x0A1EFB92
    KEY2            = 0x0A1EFB93
    KEY3            = 0x0A1EFB94
    KEY4            = 0x0A1EFB95
    KEY5            = 0x0A1EFB96

#Snacks are notated nearly exactly as they are in the game, but Space characters are replaced with "__"
#class Snacks(Enum):
#    BOX__O__SNACKS__UNDER__SWINGER   =
#    BOX__O__SNACKS__UNDER__SWINGER0  =
#    BOX__O__SNACKS__UNDER__SWINGER00 =
#    BOX__OF__SNACKS__01              =
#    BOX__OF__SNACKS__02              =
#    BOX__OF__SNACKS__03              =
#    BOX__OF__SNACKS__04              =
#    BOX__OF__SNACKS__05              =
#    BOX__OF__SNACKS__06              =
#    BOX__OF__SNACKS__07              =
#    BOX__OF__SNACKS__1               =
#    BOX__OF__SNACKS__2               =
#    BOX__OF__SNACKS__3               =
#    BOX__OF__SNACKS__4               =
#    BOX__OF__SNACKS__5               =
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
#    CRATE__PRIZE__1                  =
#    CRATE__PRIZE__10                 =
#    CRATE__SNACKBOX__1               =
#    CRATE__SNACKBOX__2               =
#    CRATE__SNACKBOX__3               =
#    CRATE__SNACKBOX__4               =
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
#    DRYER__SNACKBOX__1               =
#    DRYER__SNACKBOX__2               =
#    EX__CLUE__SNACK__BOX__1          =
#    EX__CLUE__SNACK__BOX__2          =
#    EX__CLUE__SNACK__BOX__3          =
#    EX__CLUE__SNACK__BOX__4          =
#    EX__CLUE__SNACK__BOX2            =
#    EX__CLUE__SNACK__BOX3            =
#    EX__CLUE__SNACK__BOX5            =
#    EX__CLUE__SNACKBOX__1            =
#    EX__CLUE__SNACKBOX__2            =
#    EX__CLUE__SNACKBOX__3            =
#    EX__CLUE__SNACKBOX__4            =
#    EX__CLUE__SNACKBOX1              =
#    EX__CLUE__SNACKBOX2              =
#    EX__CLUE__SNACKBOX3              =
#    EX__CLUE__SNACKBOX30             =
#    EX__CLUE__SNACKBOX300            =
#    EX__CLUE__SNACKBOX3000           =
#    EX__CLUE__SNACKBOX4              =
#    EX__CLUE__SNACKBOX5              =
#    EXCLUE__SNACKBOX__1              =
#    HIGH__SNACK__BOX                 =
#    HIGH__SNACKBOX__1                =
#    HIGH__SNACKBOX__10               =
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
#    SNACK__001                       =
#    SNACK__0010                      =
#    SNACK__0012                      =
#    SNACK__0013                      =
#    SNACK__01                        =
#    SNACK__010                       =
#    SNACK__011                       =
#    SNACK__0110                      =
#    SNACK__012                       =
#    SNACK__013                       =
#    SNACK__014                       =
#    SNACK__015                       =
#    SNACK__016                       =
#    SNACK__017                       =
#    SNACK__02                        =
#    SNACK__020                       =
#    SNACK__021                       =
#    SNACK__022                       =
#    SNACK__023                       =
#    SNACK__024                       =
#    SNACK__025                       =
#    SNACK__03                        =
#    SNACK__030                       =
#    SNACK__031                       =
#    SNACK__032                       =
#    SNACK__033                       =
#    SNACK__0330                      =
#    SNACK__0331                      =
#    SNACK__0332                      =
#    SNACK__0333                      =
#    SNACK__034                       =
#    SNACK__035                       =
#    SNACK__036                       =
#    SNACK__037                       =
#    SNACK__038                       =
#    SNACK__039                       =
#    SNACK__04                        =
#    SNACK__040                       =
#    SNACK__041                       =
#    SNACK__042                       =
#    SNACK__0420                      =
#    SNACK__0421                      =
#    SNACK__0422                      =
#    SNACK__043                       =
#    SNACK__044                       =
#    SNACK__045                       =
#    SNACK__046                       =
#    SNACK__047                       =
#    SNACK__048                       =
#    SNACK__049                       =
#    SNACK__05                        =
#    SNACK__050                       =
#    SNACK__051                       =
#    SNACK__052                       =
#    SNACK__053                       =
#    SNACK__054                       =
#    SNACK__055                       =
#    SNACK__056                       =
#    SNACK__06                        =
#    SNACK__060                       =
#    SNACK__061                       =
#    SNACK__0610                      =
#    SNACK__062                       =
#    SNACK__063                       =
#    SNACK__064                       =
#    SNACK__065                       =
#    SNACK__066                       =
#    SNACK__067                       =
#    SNACK__068                       =
#    SNACK__07                        =
#    SNACK__070                       =
#    SNACK__071                       =
#    SNACK__072                       =
#    SNACK__0720                      =
#    SNACK__0721                      =
#    SNACK__0722                      =
#    SNACK__073                       =
#    SNACK__07330                     =
#    SNACK__07331                     =
#    SNACK__07332                     =
#    SNACK__07333                     =
#    SNACK__07334                     =
#    SNACK__07335                     =
#    SNACK__07336                     =
#    SNACK__074                       =
#    SNACK__075                       =
#    SNACK__076                       =
#    SNACK__077                       =
#    SNACK__078                       =
#    SNACK__079                       =
#    SNACK__0790                      =
#    SNACK__0791                      =
#    SNACK__0792                      =
#    SNACK__0793                      =
#    SNACK__0794                      =
#    SNACK__08                        =
#    SNACK__080                       =
#    SNACK__081                       =
#    SNACK__082                       =
#    SNACK__083                       =
#    SNACK__0830                      =
#    SNACK__0831                      =
#    SNACK__0832                      =
#    SNACK__08320                     =
#    SNACK__08321                     =
#    SNACK__08322                     =
#    SNACK__0833                      =
#    SNACK__084                       =
#    SNACK__085                       =
#    SNACK__09                        =
#    SNACK__090                       =
#    SNACK__091                       =
#    SNACK__092                       =
#    SNACK__093                       =
#    SNACK__094                       =
#    SNACK__095                       =
#    SNACK__096                       =
#    SNACK__1                         =
#    SNACK__1__MIL                    =
#    SNACK__10                        =
#    SNACK__100                       =
#    SNACK__101                       =
#    SNACK__102                       =
#    SNACK__103                       =
#    SNACK__104                       =
#    SNACK__105                       =
#    SNACK__106                       =
#    SNACK__107                       =
#    SNACK__108                       =
#    SNACK__109                       =
#    SNACK__11                        =
#    SNACK__110                       =
#    SNACK__111                       =
#    SNACK__112                       =
#    SNACK__113                       =
#    SNACK__1130                      =
#    SNACK__1131                      =
#    SNACK__114                       =
#    SNACK__12                        =
#    SNACK__120                       =
#    SNACK__121                       =
#    SNACK__122                       =
#    SNACK__123                       =
#    SNACK__124                       =
#    SNACK__125                       =
#    SNACK__126                       =
#    SNACK__127                       =
#    SNACK__128                       =
#    SNACK__129                       =
#    SNACK__13                        =
#    SNACK__130                       =
#    SNACK__131                       =
#    SNACK__1310                      =
#    SNACK__132                       =
#    SNACK__133                       =
#    SNACK__1330                      =
#    SNACK__1331                      =
#    SNACK__1332                      =
#    SNACK__1333                      =
#    SNACK__138                       =
#    SNACK__139                       =
#    SNACK__14                        =
#    SNACK__140                       =
#    SNACK__141                       =
#    SNACK__142                       =
#    SNACK__143                       =
#    SNACK__144                       =
#    SNACK__15                        =
#    SNACK__150                       =
#    SNACK__151                       =
#    SNACK__152                       =
#    SNACK__153                       =
#    SNACK__154                       =
#    SNACK__155                       =
#    SNACK__156                       =
#    SNACK__157                       =
#    SNACK__158                       =
#    SNACK__159                       =
#    SNACK__16                        =
#    SNACK__160                       =
#    SNACK__161                       =
#    SNACK__162                       =
#    SNACK__163                       =
#    SNACK__164                       =
#    SNACK__165                       =
#    SNACK__17                        =
#    SNACK__170                       =
#    SNACK__171                       =
#    SNACK__172                       =
#    SNACK__173                       =
#    SNACK__174                       =
#    SNACK__175                       =
#    SNACK__176                       =
#    SNACK__177                       =
#    SNACK__178                       =
#    SNACK__18                        =
#    SNACK__180                       =
#    SNACK__181                       =
#    SNACK__182                       =
#    SNACK__183                       =
#    SNACK__184                       =
#    SNACK__185                       =
#    SNACK__186                       =
#    SNACK__187                       =
#    SNACK__188                       =
#    SNACK__189                       =
#    SNACK__19                        =
#    SNACK__190                       =
#    SNACK__191                       =
#    SNACK__1910                      =
#    SNACK__1911                      =
#    SNACK__1912                      =
#    SNACK__1913                      =
#    SNACK__1914                      =
#    SNACK__1915                      =
#    SNACK__1916                      =
#    SNACK__1917                      =
#    SNACK__1918                      =
#    SNACK__1919                      =
#    SNACK__192                       =
#    SNACK__193                       =
#    SNACK__194                       =
#    SNACK__195                       =
#    SNACK__196                       =
#    SNACK__197                       =
#    SNACK__198                       =
#    SNACK__199                       =
#    SNACK__2                         =
#    SNACK__20                        =
#    SNACK__200                       =
#    SNACK__201                       =
#    SNACK__202                       =
#    SNACK__203                       =
#    SNACK__2030                      =
#    SNACK__2031                      =
#    SNACK__2032                      =
#    SNACK__2033                      =
#    SNACK__20340                     =
#    SNACK__203400                    =
#    SNACK__203401                    =
#    SNACK__203402                    =
#    SNACK__203403                    =
#    SNACK__2034040                   =
#    SNACK__20340400                  =
#    SNACK__20340401                  =
#    SNACK__20340402                  =
#    SNACK__20340403                  =
#    SNACK__20340404                  =
#    SNACK__204                       =
#    SNACK__21                        =
#    SNACK__210                       =
#    SNACK__211                       =
#    SNACK__2110                      =
#    SNACK__2112                      =
#    SNACK__2114                      =
#    SNACK__2116                      =
#    SNACK__212                       =
#    SNACK__213                       =
#    SNACK__214                       =
#    SNACK__2140                      =
#    SNACK__21400                     =
#    SNACK__21401                     =
#    SNACK__21402                     =
#    SNACK__21403                     =
#    SNACK__21404                     =
#    SNACK__216                       =
#    SNACK__217                       =
#    SNACK__22                        =
#    SNACK__220                       =
#    SNACK__221                       =
#    SNACK__2210                      =
#    SNACK__2212                      =
#    SNACK__2214                      =
#    SNACK__2216                      =
#    SNACK__2218                      =
#    SNACK__222                       =
#    SNACK__223                       =
#    SNACK__224                       =
#    SNACK__226                       =
#    SNACK__228                       =
#    SNACK__23                        =
#    SNACK__230                       =
#    SNACK__231                       =
#    SNACK__232                       =
#    SNACK__233                       =
#    SNACK__24                        =
#    SNACK__243                       =
#    SNACK__244                       =
#    SNACK__245                       =
#    SNACK__246                       =
#    SNACK__25                        =
#    SNACK__250                       =
#    SNACK__251                       =
#    SNACK__252                       =
#    SNACK__2520                      =
#    SNACK__2521                      =
#    SNACK__2522                      =
#    SNACK__25221                     =
#    SNACK__25222                     =
#    SNACK__252220                    =
#    SNACK__252221                    =
#    SNACK__252222                    =
#    SNACK__2522220                   =
#    SNACK__2522221                   =
#    SNACK__2522222                   =
#    SNACK__25222220                  =
#    SNACK__25222221                  =
#    SNACK__25222222                  =
#    SNACK__252222220                 =
#    SNACK__252222221                 =
#    SNACK__252222222                 =
#    SNACK__2523                      =
#    SNACK__253                       =
#    SNACK__2530                      =
#    SNACK__2531                      =
#    SNACK__2532                      =
#    SNACK__254                       =
#    SNACK__255                       =
#    SNACK__256                       =
#    SNACK__257                       =
#    SNACK__258                       =
#    SNACK__259                       =
#    SNACK__260                       =
#    SNACK__2610                      =
#    SNACK__2612                      =
#    SNACK__2614                      =
#    SNACK__2616                      =
#    SNACK__2618                      =
#    SNACK__262                       =
#    SNACK__2620                      =
#    SNACK__2622                      =
#    SNACK__264                       =
#    SNACK__266                       =
#    SNACK__268                       =
#    SNACK__27                        =
#    SNACK__270                       =
#    SNACK__271                       =
#    SNACK__272                       =
#    SNACK__273                       =
#    SNACK__274                       =
#    SNACK__275                       =
#    SNACK__276                       =
#    SNACK__277                       =
#    SNACK__278                       =
#    SNACK__28                        =
#    SNACK__280                       =
#    SNACK__281                       =
#    SNACK__282                       =
#    SNACK__283                       =
#    SNACK__29                        =
#    SNACK__292                       =
#    SNACK__3                         =
#    SNACK__30                        =
#    SNACK__300                       =
#    SNACK__301                       =
#    SNACK__3010                      =
#    SNACK__3011                      =
#    SNACK__3012                      =
#    SNACK__3013                      =
#    SNACK__3014                      =
#    SNACK__302                       =
#    SNACK__3020                      =
#    SNACK__3021                      =
#    SNACK__3022                      =
#    SNACK__30220                     =
#    SNACK__30221                     =
#    SNACK__30222                     =
#    SNACK__303                       =
#    SNACK__3030                      =
#    SNACK__30300                     =
#    SNACK__30301                     =
#    SNACK__30302                     =
#    SNACK__30303                     =
#    SNACK__304                       =
#    SNACK__305                       =
#    SNACK__306                       =
#    SNACK__307                       =
#    SNACK__308                       =
#    SNACK__309                       =
#    SNACK__31                        =
#    SNACK__310                       =
#    SNACK__311                       =
#    SNACK__312                       =
#    SNACK__313                       =
#    SNACK__3130                      =
#    SNACK__31300                     =
#    SNACK__31301                     =
#    SNACK__31302                     =
#    SNACK__31303                     =
#    SNACK__313030                    =
#    SNACK__313031                    =
#    SNACK__313032                    =
#    SNACK__313033                    =
#    SNACK__314                       =
#    SNACK__32                        =
#    SNACK__320                       =
#    SNACK__321                       =
#    SNACK__3211                      =
#    SNACK__3213                      =
#    SNACK__322                       =
#    SNACK__3220                      =
#    SNACK__3221                      =
#    SNACK__3222                      =
#    SNACK__32220                     =
#    SNACK__32221                     =
#    SNACK__32222                     =
#    SNACK__322220                    =
#    SNACK__322221                    =
#    SNACK__322222                    =
#    SNACK__323                       =
#    SNACK__325                       =
#    SNACK__327                       =
#    SNACK__329                       =
#    SNACK__33                        =
#    SNACK__330                       =
#    SNACK__331                       =
#    SNACK__332                       =
#    SNACK__3320                      =
#    SNACK__3321                      =
#    SNACK__3322                      =
#    SNACK__333                       =
#    SNACK__334                       =
#    SNACK__340                       =
#    SNACK__341                       =
#    SNACK__3410                      =
#    SNACK__342                       =
#    SNACK__343                       =
#    SNACK__344                       =
#    SNACK__345                       =
#    SNACK__346                       =
#    SNACK__347                       =
#    SNACK__348                       =
#    SNACK__349                       =
#    SNACK__355                       =
#    SNACK__3550                      =
#    SNACK__3552                      =
#    SNACK__3554                      =
#    SNACK__3556                      =
#    SNACK__36                        =
#    SNACK__361                       =
#    SNACK__363                       =
#    SNACK__374                       =
#    SNACK__380                       =
#    SNACK__381                       =
#    SNACK__382                       =
#    SNACK__383                       =
#    SNACK__390                       =
#    SNACK__391                       =
#    SNACK__392                       =
#    SNACK__393                       =
#    SNACK__4                         =
#    SNACK__40                        =
#    SNACK__41                        =
#    SNACK__42                        =
#    SNACK__43                        =
#    SNACK__5                         =
#    SNACK__50                        =
#    SNACK__51                        =
#    SNACK__52                        =
#    SNACK__53                        =
#    SNACK__530                       =
#    SNACK__531                       =
#    SNACK__6                         =
#    SNACK__60                        =
#    SNACK__600                       =
#    SNACK__602                       =
#    SNACK__603                       =
#    SNACK__606                       =
#    SNACK__608                       =
#    SNACK__61                        =
#    SNACK__666                       =
#    SNACK__7                         =
#    SNACK__70                        =
#    SNACK__700                       =
#    SNACK__701                       =
#    SNACK__702                       =
#    SNACK__703                       =
#    SNACK__704                       =
#    SNACK__705                       =
#    SNACK__706                       =
#    SNACK__71                        =
#    SNACK__72                        =
#    SNACK__73                        =
#    SNACK__74                        =
#    SNACK__8                         =
#    SNACK__80                        =
#    SNACK__800                       =
#    SNACK__801                       =
#    SNACK__802                       =
#    SNACK__803                       =
#    SNACK__804                       =
#    SNACK__805                       =
#    SNACK__806                       =
#    SNACK__807                       =
#    SNACK__808                       =
#    SNACK__809                       =
#    SNACK__81                        =
#    SNACK__9                         =
#    SNACK__90                        =
#    SNACK__91                        =
#    SNACK__BOX__1                    =
#    SNACK__BOX__1__MILLION           =
#    SNACK__BOX__10                   =
#    SNACK__BOX__2                    =
#    SNACK__BOX__BEHIND__MOODY        =
#    SNACK__BOX__IN__SECRET           =
#    SNACK__BOX__LEFT__CORRIDOR       =
#    SNACK__BOX__LEFT__CORRIDOR__2    =
#    SNACK__BOX__OVER__PIT            =
#    SNACK__BOX__OVER__PIT__2         =
#    SNACK001                         =
#    SNACK01                          =
#    SNACK010                         =
#    SNACK011                         =
#    SNACK012                         =
#    SNACK013                         =
#    SNACK014                         =
#    SNACK015                         =
#    SNACK02                          =
#    SNACK020                         =
#    SNACK022                         =
#    SNACK023                         =
#    SNACK03                          =
#    SNACK030                         =
#    SNACK031                         =
#    SNACK032                         =
#    SNACK040                         =
#    SNACK041                         =
#    SNACK042                         =
#    SNACK043                         =
#    SNACK050                         =
#    SNACK051                         =
#    SNACK052                         =
#    SNACK053                         =
#    SNACK0530                        =
#    SNACK05300                       =
#    SNACK05301                       =
#    SNACK05302                       =
#    SNACK07                          =
#    SNACK070                         =
#    SNACK071                         =
#    SNACK08                          =
#    SNACK080                         =
#    SNACK081                         =
#    SNACK082                         =
#    SNACK083                         =
#    SNACK09                          =
#    SNACK090                         =
#    SNACK091                         =
#    SNACK092                         =
#    SNACK093                         =
#    SNACK0930                        =
#    SNACK09300                       =
#    SNACK09301                       =
#    SNACK09303                       =
#    SNACK09304                       =
#    SNACK09305                       =
#    SNACK1                           =
#    SNACK10                          =
#    SNACK11                          =
#    SNACK110                         =
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
#    SNACK111                         =
#    SNACK112                         =
#    SNACK1120                        =
#    SNACK1121                        =
#    SNACK11210                       =
#    SNACK11211                       =
#    SNACK1122                        =
#    SNACK1123                        =
#    SNACK1124                        =
#    SNACK1125                        =
#    SNACK1126                        =
#    SNACK1127                        =
#    SNACK1128                        =
#    SNACK1129                        =
#    SNACK113                         =
#    SNACK114                         =
#    SNACK115                         =
#    SNACK116                         =
#    SNACK117                         =
#    SNACK118                         =
#    SNACK119                         =
#    SNACK12                          =
#    SNACK120                         =
#    SNACK1200                        =
#    SNACK12010                       =
#    SNACK12012                       =
#    SNACK12014                       =
#    SNACK12016                       =
#    SNACK12018                       =
#    SNACK1202                        =
#    SNACK1204                        =
#    SNACK1206                        =
#    SNACK1208                        =
#    SNACK121                         =
#    SNACK122                         =
#    SNACK123                         =
#    SNACK124                         =
#    SNACK125                         =
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
#    SNACK13                          =
#    SNACK130                         =
#    SNACK1300                        =
#    SNACK132                         =
#    SNACK133                         =
#    SNACK14                          =
#    SNACK140                         =
#    SNACK141                         =
#    SNACK142                         =
#    SNACK143                         =
#    SNACK15                          =
#    SNACK16                          =
#    SNACK17                          =
#    SNACK18                          =
#    SNACK19                          =
#    SNACK190                         =
#    SNACK191                         =
#    SNACK192                         =
#    SNACK193                         =
#    SNACK194                         =
#    SNACK21                          =
#    SNACK210                         =
#    SNACK211                         =
#    SNACK212                         =
#    SNACK213                         =
#    SNACK2130                        =
#    SNACK21300                       =
#    SNACK21301                       =
#    SNACK21303                       =
#    SNACK21304                       =
#    SNACK21305                       =
#    SNACK240                         =
#    SNACK241                         =
#    SNACK242                         =
#    SNACK243                         =
#    SNACK26                          =
#    SNACK260                         =
#    SNACK261                         =
#    SNACK262                         =
#    SNACK263                         =
#    SNACK264                         =
#    SNACK27                          =
#    SNACK270                         =
#    SNACK271                         =
#    SNACK272                         =
#    SNACK273                         =
#    SNACK274                         =
#    SNACK29                          =
#    SNACK290                         =
#    SNACK291                         =
#    SNACK293                         =
#    SNACK294                         =
#    SNACK295                         =
#    SNACK296                         =
#    SNACK31                          =
#    SNACK310                         =
#    SNACK311                         =
#    SNACK312                         =
#    SNACK313                         =
#    SNACK314                         =
#    SNACK315                         =
#    SNACK32                          =
#    SNACK320                         =
#    SNACK321                         =
#    SNACK322                         =
#    SNACK323                         =
#    SNACK324                         =
#    SNACK325                         =
#    SNACK326                         =
#    SNACK33                          =
#    SNACK330                         =
#    SNACK331                         =
#    SNACK332                         =
#    SNACK333                         =
#    SNACK334                         =
#    SNACK335                         =
#    SNACK35                          =
#    SNACK36                          =
#    SNACK360                         =
#    SNACK361                         =
#    SNACK362                         =
#    SNACK363                         =
#    SNACK364                         =
#    SNACK365                         =
#    SNACK37                          =
#    SNACK370                         =
#    SNACK371                         =
#    SNACK372                         =
#    SNACK373                         =
#    SNACK39                          =
#    SNACK390                         =
#    SNACK391                         =
#    SNACK392                         =
#    SNACK393                         =
#    SNACK40                          =
#    SNACK400                         =
#    SNACK401                         =
#    SNACK402                         =
#    SNACK403                         =
#    SNACK404                         =
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
#    SNACKBOX__0                      =
#    SNACKBOX__1                      =
#    SNACKBOX__1__1                   =
#    SNACKBOX__1__10                  =
#    SNACKBOX__1__11                  =
#    SNACKBOX__1__12                  =
#    SNACKBOX__2                      =
#    SNACKBOX__2__1                   =
#    SNACKBOX__2__10                  =
#    SNACKBOX__2__11                  =
#    SNACKBOX__2__12                  =
#    SNACKBOX__2ND__LEVEL__1          =
#    SNACKBOX__2ND__LEVEL__2          =
#    SNACKBOX__3                      =
#    SNACKBOX__3__1                   =
#    SNACKBOX__3__10                  =
#    SNACKBOX__3__11                  =
#    SNACKBOX__3__12                  =
#    SNACKBOX__4                      =
#    SNACKBOX__4__1                   =
#    SNACKBOX__4__10                  =
#    SNACKBOX__4__11                  =
#    SNACKBOX__4__12                  =
#    SNACKBOX__5                      =
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
#    SNACKBOX1MILLION                 =
#    SNACKBOX1MILLION1                =
#    SNACKBOX2                        =
#    SNACKBOX3                        =
#    SNACKBOX30                       =
#    SNACKBOX5                        =
#    SNACKS__040                      =
#    SNACKS__041                      =
#    SNACKS__042                      =
#    Snacks.txt                       =
#    SS__999                          =
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
#    SS1                              =
#    SS10                             =
#    SS100                            =
#    SS1000                           =
#    SS1001                           =
#    SS1002                           =
#    SS10020                          =
#    SS10021                          =
#    SS10022                          =
#    SS1003                           =
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
#    SS101                            =
#    SS1010                           =
#    SS1011                           =
#    SS1012                           =
#    SS10120                          =
#    SS10121                          =
#    SS10122                          =
#    SS10123                          =
#    SS10124                          =
#    SS10125                          =
#    SS102                            =
#    SS1020                           =
#    SS1021                           =
#    SS1022                           =
#    SS1023                           =
#    SS10230                          =
#    SS10231                          =
#    SS103                            =
#    SS1030                           =
#    SS1031                           =
#    SS104                            =
#    SS1040                           =
#    SS1041                           =
#    SS1042                           =
#    SS1043                           =
#    SS105                            =
#    SS1050                           =
#    SS1051                           =
#    SS1052                           =
#    SS1053                           =
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
#    SS11                             =
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
#    SS12                             =
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
#    SS16                             =
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
#    SS19                             =
#    SS190                            =
#    SS191                            =
#    SS192                            =
#    SS1920                           =
#    SS1921                           =
#    SS193                            =
#    SS194                            =
#    SS195                            =
#    SS196                            =
#    SS1960                           =
#    SS1961                           =
#    SS1962                           =
#    SS1963                           =
#    SS1964                           =
#    SS1965                           =
#    SS1972                           =
#    SS1974                           =
#    SS2                              =
#    SS20                             =
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
#    SS21                             =
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
#    SS22                             =
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
#    SS23                             =
#    SS230                            =
#    SS231                            =
#    SS233                            =
#    SS235                            =
#    SS237                            =
#    SS24                             =
#    SS240                            =
#    SS2400                           =
#    SS241                            =
#    SS243                            =
#    SS245                            =
#    SS247                            =
#    SS25                             =
#    SS250                            =
#    SS251                            =
#    SS26                             =
#    SS260                            =
#    SS2600                           =
#    SS2601                           =
#    SS2602                           =
#    SS2603                           =
#    SS2604                           =
#    SS2605                           =
#    SS2606                           =
#    SS2607                           =
#    SS261                            =
#    SS263                            =
#    SS265                            =
#    SS267                            =
#    SS268                            =
#    SS2681                           =
#    SS2683                           =
#    SS2685                           =
#    SS2687                           =
#    SS27                             =
#    SS270                            =
#    SS271                            =
#    SS2711                           =
#    SS272                            =
#    SS274                            =
#    SS275                            =
#    SS28                             =
#    SS280                            =
#    SS281                            =
#    SS29                             =
#    SS29300                          =
#    SS293020                         =
#    SS2930210                        =
#    SS29302105                       =
#    SS3                              =
#    SS30                             =
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
#    SS31                             =
#    SS32                             =
#    SS33                             =
#    SS34                             =
#    SS35                             =
#    SS350                            =
#    SS351                            =
#    SS352                            =
#    SS353                            =
#    SS36                             =
#    SS360                            =
#    SS361                            =
#    SS362                            =
#    SS363                            =
#    SS364                            =
#    SS365                            =
#    SS37                             =
#    SS370                            =
#    SS371                            =
#    SS372                            =
#    SS373                            =
#    SS38                             =
#    SS380                            =
#    SS381                            =
#    SS382                            =
#    SS383                            =
#    SS384                            =
#    SS385                            =
#    SS386                            =
#    SS387                            =
#    SS39                             =
#    SS4                              =
#    SS40                             =
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
#    SS41                             =
#    SS42                             =
#    SS43                             =
#    SS430                            =
#    SS431                            =
#    SS4310                           =
#    SS4311                           =
#    SS43110                          =
#    SS43111                          =
#    SS431110                         =
#    SS44                             =
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
#    SS5                              =
#    SS50                             =
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
#    SS51                             =
#    SS511                            =
#    SS512                            =
#    SS513                            =
#    SS52                             =
#    SS53                             =
#    SS54                             =
#    SS541                            =
#    SS543_COUNT40                    =
#    SS55                             =
#    SS550                            =
#    SS551                            =
#    SS5510                           =
#    SS5511                           =
#    SS5512                           =
#    SS552                            =
#    SS553                            =
#    SS554                            =
#    SS555                            =
#    SS556                            =
#    SS557                            =
#    SS558                            =
#    SS559                            =
#    SS56                             =
#    SS57                             =
#    SS58                             =
#    SS59                             =
#    SS6                              =
#    SS60                             =
#    SS600                            =
#    SS6000                           =
#    SS601                            =
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
#    SS7                              =
#    SS70                             =
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
#    SS7741                           =
#    SS77411                          =
#    SS77412                          =
#    SS77413                          =
#    SS774130                         =
#    SS77414                          =
#    SS78                             =
#    SS79                             =
#    SS8                              =
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
#    SS850                            =
#    SS852                            =
#    SS854                            =
#    SS86                             =
#    SS87                             =
#    SS88                             =
#    SS89                             =
#    SS9                              =
#    SS90                             =
#    SS91                             =
#    SS910                            =
#    SS9100                           =
#    SS9101                           =
#    SS9102                           =
#    SS9103                           =
#    SS9105                           =
#    SS9106                           =
#    SS9107                           =
#    SS9108                           =
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
    b'MNU3', b'MNU4', # menus
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
        logger.info(f"Gusts 2 Keys {count}/3")

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
        self.included_check_types: CheckTypes = CheckTypes.UPGRADES
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
        self.use_qol = False
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
                self.included_check_types |= CheckTypes.MONSTERTOKENS
            if 'include_keys' in args['slot_data'] and args['slot_data']['include_keys']:
                self.included_check_types |= CheckTypes.KEYS
            if 'include_snacks' in args['slot_data'] and args['slot_data']['include_snacks']:
                self.included_check_types |= CheckTypes.SNACKS
            if 'apply_qol_fixes' in args['slot_data'] and args['slot_data']['apply_qol_fixes']:
                self.use_qol = True
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
    dolphin_memory_engine.write_word(UPGRADE_INVENTORY_ADDR, cur_upgrades + 2**bit)


def _give_gum_upgrade(ctx: NO100FContext):
    cur_max_gum = dolphin_memory_engine.read_word(MAX_GUM_COUNT_ADDR)
    dolphin_memory_engine.write_word(MAX_GUM_COUNT_ADDR, cur_max_gum + 5)


def _give_soap_upgrade(ctx: NO100FContext):
    cur_max_soap = dolphin_memory_engine.read_word(MAX_SOAP_COUNT_ADDR)
    dolphin_memory_engine.write_word(MAX_SOAP_COUNT_ADDR, cur_max_soap + 5)


def _give_monstertoken(ctx: NO100FContext, bit: int):
    cur_monster_tokens = dolphin_memory_engine.read_word(MONSTER_TOKEN_INVENTORY_ADDR)
    dolphin_memory_engine.write_word(MONSTER_TOKEN_INVENTORY_ADDR, cur_monster_tokens + 2**bit)


def _give_key(ctx: NO100FContext, offset: int):
    cur_count = dolphin_memory_engine.read_byte(KEY_COUNT_ADDR + offset)
    dolphin_memory_engine.write_byte(KEY_COUNT_ADDR + offset, cur_count + 1)


def _give_death(ctx: NO100FContext):
    if ctx.slot and dolphin_memory_engine.is_hooked() and ctx.dolphin_status == CONNECTION_CONNECTED_STATUS \
            and check_ingame(ctx) and check_control_owner(ctx, lambda owner: owner == 1):
        dolphin_memory_engine.write_word(HEALTH_ADDR, 0)


def _check_cur_scene(ctx: NO100FContext, scene_id: bytes, scene_ptr: Optional[int] = None):
    cur_scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    return cur_scene == scene_id


def _give_item(ctx: NO100FContext, item_id: int):
    true_id = item_id - base_id     # Use item_id to generate offset for use with functions
    if 0 <= true_id <= 56:      # ID is expected value

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

    else:
        logger.warning(f"Received unknown item with id {item_id}")


def _set_platform_state(ctx: NO100FContext, ptr, state):
    dolphin_memory_engine.write_byte(ptr + 0x14, state)


def _check_platform_state(ctx: NO100FContext, ptr):
   return dolphin_memory_engine.read_byte(ptr + 0x14)


def _set_trigger_state(ctx: NO100FContext, ptr, state):
    dolphin_memory_engine.write_byte(ptr + 0x7, state)


def _set_counter_value(ctx: NO100FContext, ptr, count):
    dolphin_memory_engine.write_byte(ptr + 0x15, count)


def _set_pickup_active(ctx: NO100FContext, ptr, state):
    dolphin_memory_engine.write_byte(ptr + 0x7, state)

async def apply_qol_fixes(ctx: NO100FContext):
    scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    ptr = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_PTR_ADDR)
    if not _is_ptr_valid(ptr):
        return
    size = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_SIZE_ADDR)

    if scene == b'W023':
        fix_ptr = _find_obj_in_obj_table(0xD2C0B716, ptr, size)
        if not fix_ptr == None:
            if dolphin_memory_engine.read_word(UPGRADE_INVENTORY_ADDR) & 2**11:
                _set_trigger_state(ctx, fix_ptr, 0x1d)

            else:
                _set_trigger_state(ctx, fix_ptr, 0x1c)

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
                fix_ptr = _find_obj_in_obj_table(0x1e1157c3, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)
                fix_ptr = _find_obj_in_obj_table(0x586E19B9, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

    if scene == b'H001':
        fix_ptr = _find_obj_in_obj_table(0xC20224F3, ptr, size)
        if not fix_ptr == None:
            if ctx.hedge_key >= 1:  # The Hedge key is collected, open the gate
                fix_ptr = _find_obj_in_obj_table(0xC20224F3, ptr, size)
                _set_platform_state(ctx, fix_ptr, 0)

                fix_ptr = _find_obj_in_obj_table(0xE8B3FF9B, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1c)

                fix_ptr = _find_obj_in_obj_table(0xD72B66B7, ptr, size)
                _set_trigger_state(ctx, fix_ptr, 0x1d)

            else:   # Hedge Key is not collected, make sure the gate is closed
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

            else:   # Fishing Key is not collected, make sure the gate is closed
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
                fix_ptr2 = _find_obj_in_obj_table(0x7FCDBE0F, ptr, size)
                if _check_platform_state(ctx, fix_ptr2) == 1:
                    _set_pickup_active(ctx, fix_ptr, 0x1f)
                    _set_platform_state(ctx, fix_ptr, 1)
                    _set_pickup_state(ctx, fix_ptr, 0x41)
                else:
                    _set_pickup_state(ctx, fix_ptr, 0x48)

            else:
                _set_pickup_active(ctx, fix_ptr, 0x1e)

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
            else:
                _set_pickup_active(ctx, fix_ptr, 0x1c)

    if scene == b'I005':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.MyM2_keys >= 4:
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
                return
            else:
                _set_counter_value(ctx, fix_ptr, 4)

    if scene == b'P002':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.CCitH2_keys >= 4:
                 None
            else:
                _set_counter_value(ctx, fix_ptr, 4)
            fix_ptr = _find_obj_in_obj_table(0x0a1efb96, ptr, size)
            if ctx.CCitH2_keys >= 5:
                _set_pickup_active(ctx, fix_ptr, 0x1d)
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
            else:
                _set_pickup_active(ctx, fix_ptr, 0x1c)

    if scene == b'P005':
        fix_ptr = _find_obj_in_obj_table(0x060e343c, ptr, size)
        if not fix_ptr == None:
            if ctx.GAU2_keys >= 4:
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
    if CheckTypes.KEYS in ctx.included_check_types:
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

    # Credits Location
    if scene == b"S005" and not ctx.finished_game:  # We have not finished, and we are in the final room
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

                dolphin_memory_engine.write_byte(fix_ptr + 0x7,0x1d)    # Force Shovel Pickup Availability

            # Black Knight Fix
            if v[1] == Upgrades.BootsPower.value:   #Only do this for the Boots Power Up in O008

                fix_ptr = _find_obj_in_obj_table(0x7B9BA1C7, ptr, size)
                if fix_ptr is None: break

                BK_Alive = dolphin_memory_engine.read_byte(fix_ptr + 0x15) #Check Fight Over Counter
                if BK_Alive == 0:  #Is he dead?
                    locations_checked.add(k)
                    ctx.post_boss = True

            # Green Ghost Fix
            if v[1] == Upgrades.UmbrellaPower.value:    # Only do this for the Umbrella Power Up in G009

                # Fix Check Itself
                fix_ptr = _find_obj_in_obj_table(0xB6C6E412 , ptr, size)
                if fix_ptr is None: break

                GG_Defeated = dolphin_memory_engine.read_byte(fix_ptr + 0x16)
                if GG_Defeated == 0x1f:
                    locations_checked.add(k)
                    ctx.post_boss = True

                # Fix Broken Fight Trigger
                fix_ptr1 = _find_obj_in_obj_table(0x060E343c, ptr, size)
                if fix_ptr1 is None: break

                dolphin_memory_engine.write_byte(fix_ptr1 + 0x7, 0x1d)  # Re-enable Key Counter
                GG_Alive = dolphin_memory_engine.read_byte(fix_ptr + 0x14)

                fix_ptr2 = _find_obj_in_obj_table(0xA11635BD, ptr, size)
                if fix_ptr2 is None: break

                if GG_Alive == 0 and GG_Defeated == 0x1b: # Green Ghost has not been defeated, and he is not yet present
                    dolphin_memory_engine.write_byte(fix_ptr2 + 0x7, 0x1f)
                else:
                    dolphin_memory_engine.write_byte(fix_ptr2 + 0x7, 0x1e)

            # Red Beard Fix
            if v[1] == Upgrades.GumPower.value:   # Only do this for the Gum Powerup in W028

                fix_ptr = _find_obj_in_obj_table(0x5A3B5C98, ptr, size)
                if fix_ptr is None: break

                RB_Alive = dolphin_memory_engine.read_byte(fix_ptr + 0x15) # Check Fight Over Counter
                if RB_Alive == 0:  # Is he dead?
                    locations_checked.add(k)
                    ctx.post_boss = True

            if check_cb(ctx, obj_ptr):
                locations_checked.add(k)

                # Lampshade Fix
                if v[1] == Upgrades.SlippersPower.value:  # We are checking the slipper power up
                    locations_checked.add(k+1)  # Add the lampshade check as well
                break


async def _check_upgrades(ctx: NO100FContext, locations_checked: set):
    await _check_objects_by_id(ctx, locations_checked, UPGRADES_PICKUP_IDS, _check_pickup_state)


async def _check_monstertokens(ctx: NO100FContext, locations_checked: set):
    await _check_objects_by_id(ctx, locations_checked, MONSTERTOKENS_PICKUP_IDS, _check_pickup_state)


async def _check_keys(ctx: NO100FContext, locations_checked: set):
    await _check_objects_by_id(ctx, locations_checked, KEYS_PICKUP_IDS, _check_pickup_state)


# async def _check_snacks(ctx: NO100FContext, locations_checked: set):
#    await _check_objects_by_id(ctx, locations_checked, SNACKIDS, _check_pickup_state)

async def apply_level_fixes(ctx: NO100FContext):
    scene = dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4)
    ptr = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_PTR_ADDR)
    if not _is_ptr_valid(ptr):
        return
    size = dolphin_memory_engine.read_word(SCENE_OBJ_LIST_SIZE_ADDR)

    dolphin_memory_engine.write_word(MAP_ADDR, 0x1)     # Force the Map Into Inventory

    if scene == b'H001' or b'h001':
       if CheckTypes.KEYS not in ctx.included_check_types:
            fix_ptr = _find_obj_in_obj_table(0xBBFA4948, ptr, size)
            if not fix_ptr == None:
                if _check_pickup_state(ctx, fix_ptr):     #The Hedge key is collected, open the gate
                    fix_ptr = _find_obj_in_obj_table(0xC20224F3, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)

                    fix_ptr = _find_obj_in_obj_table(0xE8B3FF9B, ptr, size)
                    _set_trigger_state(ctx, fix_ptr, 0x1c)

                    fix_ptr = _find_obj_in_obj_table(0xD72B66B7, ptr, size)
                    _set_trigger_state(ctx, fix_ptr, 0x1d)

            fix_ptr = _find_obj_in_obj_table(0xBB82B3B3, ptr, size)
            if not fix_ptr == None:
                if _check_pickup_state(ctx, fix_ptr):     #The Fishing key is collected, open the gate
                    fix_ptr = _find_obj_in_obj_table(0x42A3128E, ptr, size)
                    _set_platform_state(ctx, fix_ptr, 0)


async def check_locations(ctx: NO100FContext):
    await _check_upgrades(ctx, ctx.locations_checked)
    if CheckTypes.MONSTERTOKENS in ctx.included_check_types:
        await _check_monstertokens(ctx, ctx.locations_checked)
    if CheckTypes.KEYS in ctx.included_check_types:
        await _check_keys(ctx, ctx.locations_checked)

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
        if dolphin_memory_engine.read_bytes(CUR_SCENE_ADDR, 0x4) == b'F003':  # Avoid Creepy Early Trigger causing erroneous DL Sends
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
            warp_gate_map += 2**i

    if warp_gate_map == 0x400:  # The game is at the default state, attempt to load instead of saving
        if not dolphin_memory_engine.read_word(SAVED_WARP_ADDR) == 0 and not _check_cur_scene(ctx, b'MNU3'):
            await load_warp_gates(ctx)
        return

    dolphin_memory_engine.write_word(SAVED_WARP_ADDR, warp_gate_map)

async def load_warp_gates(ctx: NO100FContext):
    warp_gates = dolphin_memory_engine.read_word(SAVED_WARP_ADDR)
    for i in range(26):
        if warp_gates & 2**i == 2**i:
            dolphin_memory_engine.write_word(WARP_ADDR + (12 * i), 1)


async def force_death(ctx:NO100FContext):
    cur_health = dolphin_memory_engine.read_word(HEALTH_ADDR)

    if cur_health == 69 and not ctx.post_boss:    # Funny number, but also good luck accidentally setting your health this high
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
                    if "DeathLink" in ctx.tags:
                        await check_death(ctx)
                    await give_items(ctx)
                    await check_locations(ctx)
                    await apply_level_fixes(ctx)
                    await save_warp_gates(ctx)
                    if ctx.use_qol:
                        await apply_qol_fixes(ctx)
                    await apply_key_fixes(ctx)
                    await force_death(ctx)
                    if not (_check_cur_scene(ctx,b'O008') or _check_cur_scene(ctx, b'S005') or _check_cur_scene(ctx, b'G009') or _check_cur_scene(ctx, b'W028')):
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
