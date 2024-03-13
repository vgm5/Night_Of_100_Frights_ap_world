﻿using HipHopFile;
using IndustrialPark.AssetEditorColors;
using System.ComponentModel;

namespace IndustrialPark
{
    public abstract class DynaUI : AssetDYNA
    {
        private const string dynaCategoryName = "ui";

        [Category(dynaCategoryName)]
        public AssetSingle PositionX { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle PositionY { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle PositionZ { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle Width { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle Height { get; set; }
        [Category(dynaCategoryName)]
        public FlagBitmask Flags { get; set; } = IntFlagsDescriptor();
        [Category(dynaCategoryName)]
        public AssetColor Color { get; set; }
        [Category(dynaCategoryName)]
        public AssetID UIMotion_Selected { get; set; }
        [Category(dynaCategoryName)]
        public AssetID UIMotion_Unselected { get; set; }
        [Category(dynaCategoryName)]
        public byte Brightness { get; set; }
        [Category(dynaCategoryName)]
        public AssetID autoMenuUp { get; set; }
        [Category(dynaCategoryName)]
        public AssetID autoMenuDown { get; set; }
        [Category(dynaCategoryName)]
        public AssetID autoMenuLeft { get; set; }
        [Category(dynaCategoryName)]
        public AssetID autoMenuRight { get; set; }
        [Category(dynaCategoryName)]
        public AssetID custom { get; set; }
        [Category(dynaCategoryName)]
        public AssetID customWidget { get; set; }

        protected int dynaUIEnd => dynaDataStartPosition + 64;

        public DynaUI(Section_AHDR AHDR, DynaType type, Game game, Endianness endianness) : base(AHDR, type, game, endianness)
        {
            using (var reader = new EndianBinaryReader(AHDR.data, endianness))
            {
                reader.BaseStream.Position = dynaDataStartPosition;

                PositionX = reader.ReadSingle();
                PositionY = reader.ReadSingle();
                PositionZ = reader.ReadSingle();
                Width = reader.ReadSingle();
                Height = reader.ReadSingle();
                Flags.FlagValueInt = reader.ReadUInt32();
                Color = reader.ReadColor();
                UIMotion_Selected = reader.ReadUInt32();
                UIMotion_Unselected = reader.ReadUInt32();
                Brightness = reader.ReadByte();
                reader.ReadByte();
                reader.ReadByte();
                reader.ReadByte();
                autoMenuUp = reader.ReadUInt32();
                autoMenuDown = reader.ReadUInt32();
                autoMenuLeft = reader.ReadUInt32();
                autoMenuRight = reader.ReadUInt32();
                custom = reader.ReadUInt32();
                customWidget = reader.ReadUInt32();
            }
        }

        protected void SerializeDynaUI(EndianBinaryWriter writer)
        {
            writer.Write(PositionX);
            writer.Write(PositionY);
            writer.Write(PositionZ);
            writer.Write(Width);
            writer.Write(Height);
            writer.Write(Flags.FlagValueInt);
            writer.Write(Color);
            writer.Write(UIMotion_Selected);
            writer.Write(UIMotion_Unselected);
            writer.Write(Brightness);
            writer.Write((byte)0);
            writer.Write((byte)0);
            writer.Write((byte)0);
            writer.Write(autoMenuUp);
            writer.Write(autoMenuDown);
            writer.Write(autoMenuLeft);
            writer.Write(autoMenuRight);
            writer.Write(custom);
            writer.Write(customWidget);
        }
    }
}