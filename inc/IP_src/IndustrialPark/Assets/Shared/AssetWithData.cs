﻿using HipHopFile;
using System.ComponentModel;

namespace IndustrialPark
{
    public class AssetWithData : Asset
    {
        [Browsable(false)]
        public byte[] Data { get; set; }

        public override string AssetInfo => Data.Length.ToString() + " B";

        public AssetWithData(string assetName, AssetType assetType, byte[] data) : base(assetName, assetType)
        {
            Data = data;
        }

        public AssetWithData(Section_AHDR AHDR, Game game) : base(AHDR, game)
        {
            Data = AHDR.data;
        }

        public override void Serialize(EndianBinaryWriter writer)
        {
            writer.Write(Data);
        }

        public string RwVersion(int renderWareVersion)
        {
            var str = RenderWareFile.Shared.UnpackLibraryVersion(renderWareVersion).ToString("X5");
            return $"RW {str[0]}.{str[1]}.{str[2]}.{str[3]}{str[4]}";
        }
    }
}