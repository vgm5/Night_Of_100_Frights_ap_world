﻿using HipHopFile;
using SharpDX;
using System.Collections.Generic;
using System.ComponentModel;

namespace IndustrialPark
{
    public class AssetPLAT : AssetWithMotion
    {
        private const string categoryName = "Platform";
        public override string AssetInfo => $"{PlatformType} {HexUIntTypeConverter.StringFromAssetID(Model)}";

        private PlatType _platformType;
        [Category(categoryName)]
        public PlatType PlatformType
        {
            get => _platformType;
            set
            {
                _platformType = value;

                if ((int)value > 3)
                    TypeFlag = (byte)value;
                else
                    TypeFlag = 0;

                switch ((PlatType)(byte)TypeFlag)
                {
                    case PlatType.ConveyorBelt:
                        PlatSpecific = new PlatSpecific_ConveryorBelt(game);
                        break;
                    case PlatType.FallingPlatform:
                        PlatSpecific = new PlatSpecific_FallingPlatform(game);
                        break;
                    case PlatType.FR:
                        PlatSpecific = new PlatSpecific_FR(game);
                        break;
                    case PlatType.BreakawayPlatform:
                        PlatSpecific = new PlatSpecific_BreakawayPlatform(game);
                        break;
                    case PlatType.Springboard:
                        PlatSpecific = new PlatSpecific_Springboard(game);
                        break;
                    case PlatType.TeeterTotter:
                        PlatSpecific = new PlatSpecific_TeeterTotter(game);
                        break;
                    case PlatType.Paddle:
                        PlatSpecific = new PlatSpecific_Paddle(game);
                        break;
                    default:
                        PlatSpecific = new PlatSpecific_Generic(game);
                        break;
                }

                switch (PlatformType)
                {
                    case PlatType.ExtendRetract:
                        Motion = new Motion_ExtendRetract(game);
                        break;
                    case PlatType.Orbit:
                        Motion = new Motion_Orbit(game);
                        break;
                    case PlatType.Spline:
                        Motion = new Motion_Spline(game);
                        break;
                    case PlatType.Pendulum:
                        Motion = new Motion_Pendulum(game);
                        break;
                    case PlatType.MovePoint:
                        Motion = new Motion_MovePoint(game, _position);
                        break;
                    case PlatType.Mechanism:
                        Motion = new Motion_Mechanism(game);
                        break;
                    default:
                        Motion = new Motion(game, MotionType.Other);
                        break;
                }
            }
        }

        [Category(categoryName)]
        public FlagBitmask PlatFlags { get; set; } = ShortFlagsDescriptor(
            "Shake on Mount",
            "Unknown",
            "Solid");

        private int motionStart(Game game) =>
            game == Game.Scooby ? 0x78 :
            game == Game.BFBB ? 0x90 :
            game == Game.Incredibles ? 0x8C : 0;

        public AssetPLAT(string assetName, Vector3 position, AssetTemplate template) : base(assetName, AssetType.Platform, BaseAssetType.Platform, position)
        {
            PlatformType = PlatType.Mechanism;
            PlatFlags.FlagValueShort = 4;

            switch (template)
            {
                case AssetTemplate.Hovering_Platform:
                    Model = 0x335EE0C8;
                    Animation = 0x730847B6;
                    Motion = new Motion_Mechanism(game)
                    {
                        Type = MotionType.Other,
                        MovementLoopMode = EMechanismFlags.ReturnToStart,
                        SlideAccelTime = 0.4f,
                        SlideDecelTime = 0.4f
                    };
                    break;
                case AssetTemplate.Texas_Hitch_Platform:
                case AssetTemplate.Swinger:
                    Model = "trailer_hitch";
                    break;
                case AssetTemplate.Springboard:
                    Model = 0x55E9EAB5;
                    Animation = 0x7AAA99BB;
                    PlatformType = PlatType.Springboard;
                    PlatSpecific = new PlatSpecific_Springboard(game)
                    {
                        Height1 = 10,
                        Height2 = 10,
                        Height3 = 10,
                        HeightBubbleBounce = 10,
                        Animation1 = 0x6DAE0759,
                        Animation2 = 0xBC4A9A5F,
                        DirectionY = 1f,
                    };
                    break;
                case AssetTemplate.CollapsePlatform_Planktopolis:
                case AssetTemplate.CollapsePlatform_ThugTug:
                case AssetTemplate.CollapsePlatform_Spongeball:
                    PlatformType = PlatType.BreakawayPlatform;
                    Animation = 0x7A9BF321;
                    if (template == AssetTemplate.CollapsePlatform_Planktopolis)
                    {
                        Model = 0x6F462432;
                    }
                    else if (template == AssetTemplate.CollapsePlatform_ThugTug)
                    {
                        Animation = 0x62C6520F;
                        Model = 0xED7F1021;
                    }
                    else if (template == AssetTemplate.CollapsePlatform_Spongeball)
                    {
                        Model = 0x1A38B9AB;
                    }
                    PlatSpecific = new PlatSpecific_BreakawayPlatform(template, game);
                    Motion = new Motion_Mechanism(game, MotionType.Other);
                    break;
                case AssetTemplate.Flower_Dig:
                    VisibilityFlags.FlagValueByte = 0;
                    Model = "path_dig_C.MINF";
                    PlatformType = PlatType.ExtendRetract;
                    var m = (Motion_ExtendRetract)Motion;
                    m.MotionFlags.FlagValueShort = 0x4;
                    m.RetractPositionX = _position.X;
                    m.RetractPositionY = _position.Y;
                    m.RetractPositionZ = _position.Z;
                    break;
            }
        }

        public AssetPLAT(Section_AHDR AHDR, Game game, Endianness endianness) : base(AHDR, game, endianness)
        {
            using (var reader = new EndianBinaryReader(AHDR.data, endianness))
            {
                reader.BaseStream.Position = entityHeaderEndPosition;

                _platformType = (PlatType)reader.ReadByte();

                reader.ReadByte();

                PlatFlags.FlagValueShort = reader.ReadUInt16();

                switch ((PlatType)(byte)TypeFlag)
                {
                    case PlatType.ConveyorBelt:
                        PlatSpecific = new PlatSpecific_ConveryorBelt(reader, game);
                        break;
                    case PlatType.FallingPlatform:
                        PlatSpecific = new PlatSpecific_FallingPlatform(reader, game);
                        break;
                    case PlatType.FR:
                        PlatSpecific = new PlatSpecific_FR(reader, game);
                        break;
                    case PlatType.BreakawayPlatform:
                        PlatSpecific = new PlatSpecific_BreakawayPlatform(reader, game);
                        break;
                    case PlatType.Springboard:
                        PlatSpecific = new PlatSpecific_Springboard(reader, game);
                        break;
                    case PlatType.TeeterTotter:
                        PlatSpecific = new PlatSpecific_TeeterTotter(reader, game);
                        break;
                    case PlatType.Paddle:
                        PlatSpecific = new PlatSpecific_Paddle(reader, game);
                        break;
                    default:
                        PlatSpecific = new PlatSpecific_Generic(game);
                        break;
                }

                reader.BaseStream.Position = motionStart(game);

                switch (PlatformType)
                {
                    case PlatType.ExtendRetract:
                        Motion = new Motion_ExtendRetract(reader, game);
                        break;
                    case PlatType.Orbit:
                        Motion = new Motion_Orbit(reader, game);
                        break;
                    case PlatType.Spline:
                        Motion = new Motion_Spline(reader, game);
                        break;
                    case PlatType.Pendulum:
                        Motion = new Motion_Pendulum(reader, game);
                        break;
                    case PlatType.MovePoint:
                        Motion = new Motion_MovePoint(reader, game, _position);
                        break;
                    case PlatType.Mechanism:
                        Motion = new Motion_Mechanism(reader, game);
                        break;
                    default:
                        Motion = new Motion(reader, game);
                        break;
                }
            }
        }

        public override void Serialize(EndianBinaryWriter writer)
        {
            base.Serialize(writer);

            writer.Write((byte)_platformType);
            writer.Write((byte)0);
            writer.Write(PlatFlags.FlagValueShort);
            PlatSpecific.Serialize(writer);

            var motionStart = this.motionStart(game);
            while (writer.BaseStream.Length < motionStart)
                writer.Write((byte)0);
            Motion.Serialize(writer);

            int linkStart =
                game == Game.BFBB ? 0xC0 :
                game == Game.Incredibles ? 0xC8 :
                game == Game.Scooby ? 0xA8 : throw new System.ArgumentException("Invalid game");

            while (writer.BaseStream.Length < linkStart)
                writer.Write((byte)0);
            SerializeLinks(writer);
        }

        public static bool dontRender = false;

        public override bool DontRender => dontRender;

        [Category("Entity")]
        public override AssetSingle PositionX
        {
            get => base.PositionX;
            set
            {
                if (Motion is Motion_MovePoint mp)
                    mp.SetInitialPosition(_position);
                base.PositionX = value;
            }
        }

        [Category("Entity")]
        public override AssetSingle PositionY
        {
            get => base.PositionY;
            set
            {
                if (Motion is Motion_MovePoint mp)
                    mp.SetInitialPosition(_position);
                base.PositionY = value;
            }
        }

        [Category("Entity")]
        public override AssetSingle PositionZ
        {
            get => base.PositionZ;
            set
            {
                if (Motion is Motion_MovePoint mp)
                    mp.SetInitialPosition(_position);
                base.PositionZ = value;
            }
        }

        public override Matrix LocalWorld()
        {
            if (movementPreview)
            {
                if (isSkyBox)
                {
                    Vector3 skyTranslation = Program.MainForm.renderer.Camera.Position;
                    if (!skyBoxUseY)
                        skyTranslation.Y = PositionY;

                    return base.LocalWorld() * Matrix.Translation(-_position) * Matrix.Translation(skyTranslation);
                }

                if (PlatformType == PlatType.MovePoint)
                    return Matrix.Scaling(_scale)
                        * Matrix.RotationYawPitchRoll(_yaw, _pitch, _roll)
                        * PlatLocalTranslation();
                return base.LocalWorld();
            }

            return world;
        }

        [Category("Platform")]
        [TypeConverter(typeof(ExpandableObjectConverter))]
        public PlatSpecific_Generic PlatSpecific { get; set; }

        private bool isSkyBox = false;
        private bool skyBoxUseY = false;

        public override void Reset()
        {
            isSkyBox = false;
            skyBoxUseY = false;
            foreach (Link link in _links)
                if ((EventBFBB)link.EventSendID == EventBFBB.SetasSkydome && link.TargetAsset.Equals(assetID))
                {
                    isSkyBox = true;
                    if (link.FloatParameter2 == 1f)
                        skyBoxUseY = true;
                }
            base.Reset();
        }
    }
}