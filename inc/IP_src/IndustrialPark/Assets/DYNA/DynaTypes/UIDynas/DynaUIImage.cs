﻿using HipHopFile;
using IndustrialPark.AssetEditorColors;
using System.ComponentModel;

namespace IndustrialPark
{
    public class DynaUIImage : DynaUI
    {
        private const string dynaCategoryName = "ui:image";
        public override string TypeString => dynaCategoryName;
        public override string AssetInfo => HexUIntTypeConverter.StringFromAssetID(Texture);

        protected override short constVersion => 1;

        [Category(dynaCategoryName)]
        public AssetID Texture { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle uv1u { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle uv1v { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle uv2u { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle uv2v { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle uv3u { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle uv3v { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle uv4u { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle uv4v { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle rotation { get; set; }
        [Category(dynaCategoryName)]
        public FlagBitmask UIImageFlags { get; set; } = ShortFlagsDescriptor();
        [Category(dynaCategoryName)]
        public byte addreasMoveU { get; set; }
        [Category(dynaCategoryName)]
        public byte addreasMoveV { get; set; }
        [Category(dynaCategoryName)]
        public AssetColor Color1 { get; set; }
        [Category(dynaCategoryName)]
        public AssetColor Color2 { get; set; }
        [Category(dynaCategoryName)]
        public AssetColor Color3 { get; set; }
        [Category(dynaCategoryName)]
        public AssetColor Color4 { get; set; }

        [Category(dynaCategoryName + " (Incredibles version only)")]
        public int Unknown { get; set; }

        [Category(dynaCategoryName)]
        public EVersionIncrediblesOthers AssetVersion { get; set; } = EVersionIncrediblesOthers.Others;

        public DynaUIImage(Section_AHDR AHDR, Game game, Endianness endianness) : base(AHDR, DynaType.ui__image, game, endianness)
        {
            using (var reader = new EndianBinaryReader(AHDR.data, endianness))
            {
                reader.BaseStream.Position = dynaUIEnd;

                Texture = reader.ReadUInt32();
                uv1u = reader.ReadSingle();
                uv1v = reader.ReadSingle();
                uv2u = reader.ReadSingle();
                uv2v = reader.ReadSingle();
                uv3u = reader.ReadSingle();
                uv3v = reader.ReadSingle();
                uv4u = reader.ReadSingle();
                uv4v = reader.ReadSingle();
                rotation = reader.ReadSingle();
                UIImageFlags.FlagValueShort = reader.ReadUInt16();
                addreasMoveU = reader.ReadByte();
                addreasMoveV = reader.ReadByte();
                Color1 = reader.ReadColor();
                Color2 = reader.ReadColor();
                Color3 = reader.ReadColor();
                Color4 = reader.ReadColor();

                if (reader.BaseStream.Position != linkStartPosition(reader.BaseStream.Length, _links.Length))
                {
                    AssetVersion = EVersionIncrediblesOthers.Incredibles;
                    Unknown = reader.ReadInt32();
                }
                else
                    AssetVersion = EVersionIncrediblesOthers.Others;
            }
        }

        protected override void SerializeDyna(EndianBinaryWriter writer)
        {
            SerializeDynaUI(writer);
            writer.Write(Texture);
            writer.Write(uv1u);
            writer.Write(uv1v);
            writer.Write(uv2u);
            writer.Write(uv2v);
            writer.Write(uv3u);
            writer.Write(uv3v);
            writer.Write(uv4u);
            writer.Write(uv4v);
            writer.Write(rotation);
            writer.Write(UIImageFlags.FlagValueShort);
            writer.Write(addreasMoveU);
            writer.Write(addreasMoveV);
            writer.Write(Color1);
            writer.Write(Color2);
            writer.Write(Color3);
            writer.Write(Color4);

            if (AssetVersion == EVersionIncrediblesOthers.Incredibles)
                writer.Write(Unknown);
        }
    }
}