﻿using HipHopFile;
using IndustrialPark.Models;
using SharpDX;
using System.Collections.Generic;
using System.ComponentModel;
using static IndustrialPark.ArchiveEditorFunctions;

namespace IndustrialPark
{
    public class DynaEffectRumbleSphere : RenderableDynaBase
    {
        private const string dynaCategoryName = "effect:Rumble Spherical Emitter";
        public override string TypeString => dynaCategoryName;
        public override string AssetInfo => HexUIntTypeConverter.StringFromAssetID(Rumble);

        protected override short constVersion => 1;

        [Category(dynaCategoryName), ValidReferenceRequired]
        public AssetID Rumble { get; set; }
        [Category(dynaCategoryName)]
        public AssetSingle Radius { get; set; }
        [Category(dynaCategoryName)]
        public AssetByte OnlyRumbleOnY { get; set; }
        [Category(dynaCategoryName)]
        public AssetByte FallOff { get; set; }
        [Category(dynaCategoryName)]
        public AssetByte OnlyOnFloor { get; set; }

        public static bool dontRender = false;
        protected override bool DontRender => dontRender;

        public DynaEffectRumbleSphere(Section_AHDR AHDR, Game game, Endianness endianness) : base(AHDR, DynaType.effect__RumbleSphericalEmitter, game, endianness)
        {
            using (var reader = new EndianBinaryReader(AHDR.data, endianness))
            {
                reader.BaseStream.Position = dynaDataStartPosition;

                Rumble = reader.ReadUInt32();
                Radius = reader.ReadSingle();
                _position = new Vector3(reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle());
                OnlyRumbleOnY = reader.ReadByte();
                FallOff = reader.ReadByte();
                OnlyOnFloor = reader.ReadByte();

                CreateTransformMatrix();
                AddToRenderableAssets(this);
            }
        }

        protected override void SerializeDyna(EndianBinaryWriter writer)
        {
            writer.Write(Rumble);
            writer.Write(Radius);
            writer.Write(PositionX);
            writer.Write(PositionY);
            writer.Write(PositionZ);
            writer.Write(OnlyRumbleOnY);
            writer.Write(FallOff);
            writer.Write(OnlyOnFloor);
            writer.Write((byte)0);
        }

        protected override List<Vector3> vertexSource => SharpRenderer.cubeVertices;

        protected override List<Triangle> triangleSource => SharpRenderer.cubeTriangles;

        public override void Draw(SharpRenderer renderer)
        {
            renderer.DrawCube(world, isSelected);
        }
    }
}