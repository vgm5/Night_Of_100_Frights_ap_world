import hashlib
import json
import logging
import os
import sys
import tempfile
import zipfile
from enum import Enum
from typing import Any

import Utils
from worlds.Files import AutoPatchRegister, APContainer
from . import Patches
from .inc.wwrando.wwlib.gcm import GCM
from .names import ConnectionNames

NO100F_HASH = "6f078c687c81e26b8e81127ba4b747ba"

class NO100FDeltaPatch(APContainer, metaclass=AutoPatchRegister):
    hash = NO100F_HASH
    game = "Night of 100 Frights"
    patch_file_ending: str = ".apno100f"
    result_file_ending: str = ".gcm"
    zip_version: int = 1
    logger = logging.getLogger("NO100FPatch")

    def __init__(self, *args: Any, **kwargs: Any):
        self.include_monster_tokens: int = kwargs['include_monster_tokens']
        #self.include_snacks: int = kwargs['include_snacks']
        #self.include_keys: int = kwargs['include_keys']
        self.seed: bytes = kwargs['seed']
        del kwargs['include_monster_tokens']
        #del kwargs['include_snacks']
        #del kwargs['include_keys']
        del kwargs['seed']
        super(NO100FDeltaPatch, self).__init__(*args, **kwargs)

    def write_contents(self, opened_zipfile: zipfile.ZipFile):
        super(NO100FDeltaPatch, self).write_contents(opened_zipfile)
        opened_zipfile.writestr("zip_version",
                                self.zip_version.to_bytes(1, "little"),
                                compress_type=zipfile.ZIP_STORED)
        opened_zipfile.writestr("include_monster_tokens",
                                self.include_monster_tokens.to_bytes(1, "little"),
                                compress_type=zipfile.ZIP_STORED)
        #opened_zipfile.writestr("include_snacks",
        #                        self.include_snacks.to_bytes(1, "little"),
        #                        compress_type=zipfile.ZIP_STORED)
        #opened_zipfile.writestr("include_keys",
        #                        self.include_keys.to_bytes(1, "little"),
        #                       compress_type=zipfile.ZIP_STORED)
        m = hashlib.md5()
        m.update(self.seed)
        opened_zipfile.writestr("seed",
                                m.digest(),
                                compress_type=zipfile.ZIP_STORED)

    def read_contents(self, opened_zipfile: zipfile.ZipFile) -> None:
        super(NO100FDeltaPatch, self).read_contents(opened_zipfile)

    @classmethod
    def get_int(cls, opened_zipfile: zipfile.ZipFile, name: str):
        if name not in opened_zipfile.namelist():
            cls.logger.warning(f"couldn't find {name} in patch file")
            return 0
        return int.from_bytes(opened_zipfile.read(name), "little")

    @classmethod
    def get_bool(cls, opened_zipfile: zipfile.ZipFile, name: str):
        if name not in opened_zipfile.namelist():
            cls.logger.warning(f"couldn't find {name} in patch file")
            return False
        return bool.from_bytes(opened_zipfile.read(name), "little")

    @classmethod
    def get_json_obj(cls, opened_zipfile: zipfile.ZipFile, name: str):
        if name not in opened_zipfile.namelist():
            cls.logger.warning(f"couldn't find {name} in patch file")
            return None
        with opened_zipfile.open(name, "r") as f:
            obj = json.load(f)
        return obj

    @classmethod
    def get_seed_hash(cls, opened_zipfile: zipfile.ZipFile):
        return opened_zipfile.read("seed")

    @classmethod
    async def apply_hiphop_changes(cls, opened_zipfile: zipfile.ZipFile, source_iso, dest_iso):
        #include_keys = NO100FDeltaPatch.get_bool(opened_zipfile, "include_keys")
        #if not include_keys:
        return  #No need for HIPHOP changes until Keys are implemented
        # extract dependencies need to patch with IP
        world_path = os.path.join(__file__[:__file__.find('worlds') + len('worlds')], 'no100f.apworld')
        is_ap_world = os.path.exists(world_path)
        lib_path = os.path.abspath(os.path.dirname(__file__) + '/inc/')
        if is_ap_world:
            lib_path = os.path.expandvars('%APPDATA%/no100f_ap/')
            with zipfile.ZipFile(world_path) as world_zip:
                for file in world_zip.namelist():
                    if file.startswith('no100f/inc/packages') or file.startswith('no100f/inc/IP'):
                        try:
                            world_zip.extract(file, lib_path)
                        except:
                            cls.logger.warning(f"warning: couldn't overwrite dependency: {file}")
            lib_path = lib_path + 'no100f/inc/'
        if lib_path not in sys.path:
            sys.path.append(lib_path)
        # print(sys.path)
        cls.logger.debug('--before pythonnet.load--')
        # setup pythonnet
        from packages.pythonnet import load
        load()
        import clr
        # extract ISO content
        extraction_temp_dir = tempfile.TemporaryDirectory()
        extraction_path = extraction_temp_dir.name
        gcm = GCM(source_iso)
        gcm.read_entire_disc()
        generator = gcm.export_disc_to_folder_with_changed_files(output_folder_path=extraction_path,
                                                                 only_changed_files=False)
        cls.logger.info('--extracting--')
        while True:
            file_path, files_done = next(generator)
            # cls.logger.debug((file_path, files_done))
            if files_done == -1:
                break
        cls.logger.info('--extraction done--')
        cls.logger.info('--making changes--')
        # load and setup IP libs
        clr.AddReference(os.path.abspath(lib_path + '/IP/IndustrialPark.dll'))
        clr.AddReference(os.path.abspath(lib_path + '/IP/HipHopFile.dll'))
        clr.AddReference(os.path.abspath(lib_path + '/IP/Randomizer.dll'))
        from HipHopFile import Platform, Game
        from IndustrialPark import ArchiveEditorFunctions, Link, HexUIntTypeConverter, AutomaticUpdater
        from IndustrialPark.Randomizer import RandomizableArchive

        if not os.path.exists(f'{lib_path}/IP/Resources/IndustrialPark-EditorFiles/IndustrialPark-EditorFiles-master/'):
            import requests
            import io
            editor_files_url = "https://github.com/igorseabra4/IndustrialPark-EditorFiles/archive/master.zip"
            response = requests.get(editor_files_url)
            # Check if the request was successful
            if response.status_code == 200:
                # Read the content of the response
                zip_content = io.BytesIO(response.content)

                # Open the zip file
                with zipfile.ZipFile(zip_content, 'r') as zip_ref:
                    # Extract all files to a directory (change the path accordingly)
                    zip_ref.extractall(f'{lib_path}/IP/Resources/IndustrialPark-EditorFiles/')

                cls.logger.info("File successfully downloaded and extracted editor files.")
            else:
                cls.logger.warning("Failed to download editor file.")

        class EventIDs(Enum):
            Increment = 0x000B
            Decrement = 0x000C
            GivePowerUp = 0x0101
            GiveCollectables = 0x01C2

        class LinkData:
            event = 0
            target = 0

            def __init__(self, event: EventIDs, target):
                self.event = event.value
                self.target = target

            def compare(self, link: Link):
                return link.EventSendID == self.event and link.TargetAsset.op_Implicit(link.TargetAsset) == self.target

        files_to_check: dict[str, dict[int, list[LinkData]]] = {}
        HexUIntTypeConverter.Legacy = True
        editor_funcs = RandomizableArchive()
        editor_funcs.SkipTextureDisplay = True
        editor_funcs.Platform = Platform.GameCube
        editor_funcs.Game = Game.Scooby
        editor_funcs.standalone = True
        editor_funcs.NoLayers = True
        editor_funcs.editorFilesFolder = f'{lib_path}/IP/Resources/IndustrialPark-EditorFiles/IndustrialPark-EditorFiles-master/'
        # make changes with IP
        for name, assets_to_check in files_to_check.items():
            editor_funcs.OpenFile(extraction_path + f'/files/{name[:-2]}/{name}.HIP', False, Platform.Unknown)
            for id, links_to_check in assets_to_check.items():
                assert id in editor_funcs.assetDictionary, f"{id} is not a valid id in {name}.HIP"
                links = editor_funcs.assetDictionary[id].Links
                links_to_remove = []
                for data in links_to_check:
                    found = False
                    for link in links:
                        if data.compare(link):
                            # cls.logger.debug(f"removing link {link.ToString()} from 0x{id:x} in {name}.HIP")
                            links_to_remove.append(link)
                            found = True
                    if not found:
                        assert False, f"link not found {data.event} => 0x{data.target:x} on 0x{id:x} in {name}.HIP"
                editor_funcs.assetDictionary[id].Links = [link for link in links if link not in links_to_remove]
            editor_funcs.Save()

        cls.logger.info('--done making changes--')
        # repack ISO (as gcm for better distinction)
        cls.logger.info('--repacking--')
        num = gcm.import_all_files_from_disk(input_directory=extraction_path)
        generator = gcm.export_disc_to_iso_with_changed_files(dest_iso)
        while True:
            file_path, files_done = next(generator)
            # cls.logger.debug((file_path, files_done))
            if files_done == -1:
                break
        cls.logger.info('--repacking done--')
        # clean up
        extraction_temp_dir.cleanup()

    @classmethod
    async def apply_binary_changes(cls, opened_zipfile: zipfile.ZipFile, iso):
        cls.logger.info('--binary patching--')
        # get slot name and seed hash
        manifest = NO100FDeltaPatch.get_json_obj(opened_zipfile, "archipelago.json")
        slot_name = manifest["player_name"]
        slot_name_bytes = slot_name.encode('utf-8')
        slot_name_offset = 0x1e0c9c
        seed_hash = NO100FDeltaPatch.get_seed_hash(opened_zipfile)
        seed_hash_offset = slot_name_offset + 0x40
        # always apply these patches
        patches = [Patches.AP_SAVE_LOAD, Patches.UPGRADE_REWARD_FIX]
        # conditional patches
        include_monster_tokens = NO100FDeltaPatch.get_bool(opened_zipfile, "include_monster_tokens")
        #include_snacks = NO100FDeltaPatch.get_bool(opened_zipfile, "include_snacks")
        #include_keys = NO100FDeltaPatch.get_bool(opened_zipfile, "include_keys")
        if include_monster_tokens:
            patches += [Patches.MONSTER_TOKEN_FIX]
        #if include_snacks:
        #    patches += [Patches.SNACK_REWARD_FIX]
        #if include_keys:
        #    patches += [Patches.KEY_REWARD_FIX]

        with open(iso, "rb+") as stream:
            # write patches
            for patch in patches:
                cls.logger.info(f"applying patch {patches.index(patch) + 1}/{len(patches)}")
                for addr, val in patch.items():
                    stream.seek(addr, 0)
                    if isinstance(val, bytes):
                        stream.write(val)
                    else:
                        stream.write(val.to_bytes(0x4, "big"))
            # write slot name
            cls.logger.debug(f"writing slot_name {slot_name} to 0x{slot_name_offset:x} ({slot_name_bytes})")
            stream.seek(slot_name_offset, 0)
            stream.write(slot_name_bytes)
            cls.logger.debug(f"writing seed_hash {seed_hash} to 0x{seed_hash_offset:x}")
            stream.seek(seed_hash_offset, 0)
            stream.write(seed_hash)
        cls.logger.info('--binary patching done--')

    @classmethod
    def get_rom_path(cls) -> str:
        return get_base_rom_path()

    @classmethod
    def check_hash(cls):
        if not validate_hash():
            Exception(f"Supplied Base Rom does not match known MD5 for Scooby Doo! Night of 100 Frights.iso. "
                      "Get the correct game and version.")

    @classmethod
    def check_version(cls, opened_zipfile: zipfile.ZipFile) -> bool:
        version_bytes = opened_zipfile.read("zip_version")
        version = 0
        if version_bytes is not None:
            version = int.from_bytes(version_bytes, "little")
        if version != cls.zip_version:
            return False
        return True


def get_base_rom_path(file_name: str = "") -> str:
    options: Utils.OptionsType = Utils.get_options()
    if not file_name:
        # file_name = options["no100f_options"]["rom_file"]
        file_name = "Scooby-Doo! Night of 100 Frights.iso"
    if not os.path.exists(file_name):
        file_name = Utils.user_path(file_name)
    return file_name


def validate_hash(file_name: str = ""):
    file_name = get_base_rom_path(file_name)
    with open(file_name, "rb") as file:
        base_rom_bytes = bytes(file.read())
    basemd5 = hashlib.md5()
    basemd5.update(base_rom_bytes)
    return NO100FDeltaPatch == basemd5.hexdigest()
