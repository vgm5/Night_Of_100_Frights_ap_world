﻿using HipHopFile;
using IndustrialPark.Models;
using SharpDX;
using System.Collections.Generic;
using System.ComponentModel;
using static IndustrialPark.ArchiveEditorFunctions;

namespace IndustrialPark
{
    public class DynaGObjectFlameEmitter : RenderableDynaBase
    {
        private const string dynaCategoryName = "game_object:flame_emitter";
        public override string TypeString => dynaCategoryName;

        protected override short constVersion => 4;

        [Category(dynaCategoryName)]
        public FlagBitmask Flags { get; set; } = IntFlagsDescriptor(null, "Visible");
        [Category(dynaCategoryName)]
        public AssetSingle DirectionX { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle DirectionY { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle DirectionZ { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle ScaleX { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle ScaleY { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle ScaleZ { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle HeatRandom { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle Damage { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle Knockback { get; set; }
        [Category(dynaCategoryName + " (Incredibles version only)")]
        public int Unknown { get; set; }

        [Category(dynaCategoryName)]
        public EVersionIncrediblesOthers AssetVersion { get; set; } = EVersionIncrediblesOthers.Others;

        public static bool dontRender = false;
        protected override bool DontRender => dontRender;

        public DynaGObjectFlameEmitter(Section_AHDR AHDR, Game game, Endianness endianness) : base(AHDR, DynaType.game_object__flame_emitter, game, endianness)
        {
            using (var reader = new EndianBinaryReader(AHDR.data, endianness))
            {
                reader.BaseStream.Position = dynaDataStartPosition;

                Flags.FlagValueInt = reader.ReadUInt32();
                _position = new Vector3(reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle());
                DirectionX = reader.ReadSingle();
                DirectionY = reader.ReadSingle();
                DirectionZ = reader.ReadSingle();
                ScaleX = reader.ReadSingle();
                ScaleY = reader.ReadSingle();
                ScaleZ = reader.ReadSingle();
                HeatRandom = reader.ReadSingle();
                Damage = reader.ReadSingle();
                Knockback = reader.ReadSingle();

                if (reader.BaseStream.Position - _links.Length * Link.sizeOfStruct != reader.BaseStream.Length)
                {
                    AssetVersion = EVersionIncrediblesOthers.Incredibles;
                    Unknown = reader.ReadInt32();
                }
                else
                    AssetVersion = EVersionIncrediblesOthers.Others;

                CreateTransformMatrix();
                AddToRenderableAssets(this);
            }
        }

        protected override void SerializeDyna(EndianBinaryWriter writer)
        {
            writer.Write(Flags.FlagValueInt);
            writer.Write(_position.X);
            writer.Write(_position.Y);
            writer.Write(_position.Z);
            writer.Write(DirectionX);
            writer.Write(DirectionY);
            writer.Write(DirectionZ);
            writer.Write(ScaleX);
            writer.Write(ScaleY);
            writer.Write(ScaleZ);
            writer.Write(HeatRandom);
            writer.Write(Damage);
            writer.Write(Knockback);

            if (AssetVersion == EVersionIncrediblesOthers.Incredibles)
                writer.Write(Unknown);
        }

        protected override List<Vector3> vertexSource => SharpRenderer.cubeVertices;

        protected override List<Triangle> triangleSource => SharpRenderer.cubeTriangles;

        public override void Draw(SharpRenderer renderer) => renderer.DrawCube(world, isSelected);
    }
}