﻿using Assimp;
using RenderWareFile;
using RenderWareFile.Sections;
using SharpDX;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace IndustrialPark.Models
{
    public static class Assimp_IO
    {

        public const int TRI_AND_VERTEX_LIMIT = 65535;

        public static string GetImportFilter()
        {
            string[] formats = new AssimpContext().GetSupportedImportFormats();

            string filter = "All supported types|";

            foreach (string s in formats)
                filter += "*" + s + ";";

            filter += "*.dff|DFF Files|*.dff";

            foreach (string s in formats)
                filter += "|" + s.Substring(1).ToUpper() + " files|*" + s;

            filter += "|All files|*.*";

            return filter;
        }

        private static Texture_0006 RWTextureFromAssimpMaterial(TextureSlot texture) =>
            new Texture_0006()
            {
                textureStruct = new TextureStruct_0001()
                {
                    FilterMode = TextureFilterMode.FILTERLINEARMIPLINEAR,
                    AddressModeU = RWTextureAddressModeFromAssimp(texture.WrapModeU),
                    AddressModeV = RWTextureAddressModeFromAssimp(texture.WrapModeV),
                    UseMipLevels = 1
                },
                diffuseTextureName = new String_0002(Path.GetFileNameWithoutExtension(texture.FilePath)),
                alphaTextureName = new String_0002(""),
                textureExtension = new Extension_0003()
            };

        // use wrap as default
        public static TextureAddressMode RWTextureAddressModeFromAssimp(TextureWrapMode mode) =>
            mode == TextureWrapMode.Clamp ? TextureAddressMode.TEXTUREADDRESSCLAMP :
            mode == TextureWrapMode.Decal ? TextureAddressMode.TEXTUREADDRESSBORDER :
            mode == TextureWrapMode.Mirror ? TextureAddressMode.TEXTUREADDRESSMIRROR :
            TextureAddressMode.TEXTUREADDRESSWRAP;

        public static RWSection CreateDFFFromAssimp(string fileName, bool flipUVs, bool ignoreMeshColors)
        {
            PostProcessSteps pps =
                PostProcessSteps.Debone |
                PostProcessSteps.FindInstances |
                PostProcessSteps.FindInvalidData |
                PostProcessSteps.GenerateNormals |
                PostProcessSteps.JoinIdenticalVertices |
                PostProcessSteps.OptimizeGraph |
                PostProcessSteps.OptimizeMeshes |
                PostProcessSteps.PreTransformVertices |
                PostProcessSteps.Triangulate |
                (flipUVs ? PostProcessSteps.FlipUVs : 0);

            // NOTE:
            // Collada (.dae) files are imported incorrectly by Assimpnet.
            // The alpha channel in the vertex colors overrides the red channel,
            // and all the alpha values are set to 1.
            // See https://github.com/assimp/assimp/issues/1417
            Scene scene = new AssimpContext().ImportFile(fileName, pps);

            int vertexCount = scene.Meshes.Sum(m => m.VertexCount);
            int triangleCount = scene.Meshes.Sum(m => m.FaceCount);

            if (vertexCount > TRI_AND_VERTEX_LIMIT || triangleCount > TRI_AND_VERTEX_LIMIT)
                throw new ArgumentException("Model has too many vertices or triangles. Please import a simpler model.");

            var materials = new List<Material_0007>(scene.MaterialCount);

            bool atomicNeedsMaterialEffects = false;

            foreach (var m in scene.Materials)
            {
                materials.Add(new Material_0007()
                {
                    materialStruct = new MaterialStruct_0001()
                    {
                        unusedFlags = 0,
                        color = ignoreMeshColors ?
                        new RenderWareFile.Color(255, 255, 255, 255) :
                        new RenderWareFile.Color(
                            (byte)(m.ColorDiffuse.R * 255),
                            (byte)(m.ColorDiffuse.G * 255),
                            (byte)(m.ColorDiffuse.B * 255),
                            (byte)(m.ColorDiffuse.A * 255)),
                        unusedInt2 = 0x2DF53E84,
                        isTextured = m.HasTextureDiffuse ? 1 : 0,
                        ambient = ignoreMeshColors ? 1f : m.ColorAmbient.A,
                        specular = ignoreMeshColors ? 1f : m.ColorSpecular.A,
                        diffuse = ignoreMeshColors ? 1f : m.ColorDiffuse.A
                    },
                    texture = m.HasTextureDiffuse ? RWTextureFromAssimpMaterial(m.TextureDiffuse) : null,
                    materialExtension = new Extension_0003()
                    {
                        extensionSectionList = m.HasTextureReflection ? new List<RWSection>()
                        {
                            new MaterialEffectsPLG_0120()
                            {
                                isAtomicExtension = false,
                                value = MaterialEffectType.EnvironmentMap,
                                materialEffect1 = new MaterialEffectEnvironmentMap()
                                {
                                    EnvironmentMapTexture = RWTextureFromAssimpMaterial(m.TextureReflection),
                                    ReflectionCoefficient = m.Reflectivity,
                                    UseFrameBufferAlphaChannel = false
                                }
                            }
                        } : new List<RWSection>()
                    },
                });

                atomicNeedsMaterialEffects |= m.HasTextureReflection;
            }

            List<Vertex3> vertices = new List<Vertex3>();
            List<Vertex3> normals = new List<Vertex3>();
            List<Vertex2> textCoords = new List<Vertex2>();
            List<RenderWareFile.Color> vertexColors = new List<RenderWareFile.Color>();
            List<RenderWareFile.Triangle> triangles = new List<RenderWareFile.Triangle>();

            foreach (var m in scene.Meshes)
            {
                int totalVertices = vertices.Count;

                foreach (Vector3D v in m.Vertices)
                    vertices.Add(new Vertex3(v.X, v.Y, v.Z));

                foreach (Vector3D v in m.Normals)
                    normals.Add(new Vertex3(v.X, v.Y, v.Z));

                if (m.HasTextureCoords(0))
                    foreach (Vector3D v in m.TextureCoordinateChannels[0])
                        textCoords.Add(new Vertex2(v.X, v.Y));
                else
                    for (int i = 0; i < m.VertexCount; i++)
                        textCoords.Add(new Vertex2(0, 0));

                if (m.HasVertexColors(0))
                    foreach (Color4D c in m.VertexColorChannels[0])
                        vertexColors.Add(new RenderWareFile.Color(
                            (byte)(c.R * 255),
                            (byte)(c.G * 255),
                            (byte)(c.B * 255),
                            (byte)(c.A * 255)));
                else
                    for (int i = 0; i < m.VertexCount; i++)
                        vertexColors.Add(new RenderWareFile.Color(255, 255, 255, 255));

                foreach (var t in m.Faces)
                    if (t.IndexCount == 3)
                        triangles.Add(new RenderWareFile.Triangle()
                        {
                            vertex1 = (ushort)(t.Indices[0] + totalVertices),
                            vertex2 = (ushort)(t.Indices[1] + totalVertices),
                            vertex3 = (ushort)(t.Indices[2] + totalVertices),
                            materialIndex = (ushort)m.MaterialIndex
                        });
            }

            Vector3 max = new Vector3(vertices[0].X, vertices[0].Y, vertices[0].Z);
            Vector3 min = new Vector3(vertices[0].X, vertices[0].Y, vertices[0].Z);

            foreach (Vertex3 v in vertices)
            {
                if (v.X > max.X)
                    max.X = v.X;
                if (v.Y > max.Y)
                    max.Y = v.Y;
                if (v.Z > max.Z)
                    max.Z = v.Z;
                if (v.X < min.X)
                    min.X = v.X;
                if (v.Y < min.Y)
                    min.Y = v.Y;
                if (v.Z < min.Z)
                    min.Z = v.Z;
            }

            var binMeshes = new List<BinMesh>(materials.Count);

            for (int k = 0; k < materials.Count; k++)
            {
                List<int> indices = new List<int>(triangleCount * 3);

                foreach (var t in triangles)
                    if (t.materialIndex == k)
                    {
                        indices.Add(t.vertex1);
                        indices.Add(t.vertex2);
                        indices.Add(t.vertex3);
                    }

                if (indices.Count > 0)
                    binMeshes.Add(new BinMesh()
                    {
                        materialIndex = k,
                        indexCount = indices.Count(),
                        vertexIndices = indices.ToArray()
                    });
            }

            return ToClump(materials.ToArray(), new BoundingSphere(max + min / 2f, (max - min).Length()),
                vertices.ToArray(), normals.ToArray(), textCoords.ToArray(), vertexColors.ToArray(), triangles.ToArray(),
                binMeshes.ToArray(), atomicNeedsMaterialEffects);
        }

        private static RWSection ToClump
            (Material_0007[] materials, BoundingSphere boundingSphere,
            Vertex3[] vertices, Vertex3[] normals, Vertex2[] textCoords, RenderWareFile.Color[] vertexColors, RenderWareFile.Triangle[] triangles,
            BinMesh[] binMeshes, bool atomicNeedsMaterialEffects)
        {
            Clump_0010 clump = new Clump_0010()
            {
                clumpStruct = new ClumpStruct_0001()
                {
                    atomicCount = 1
                },
                frameList = new FrameList_000E()
                {
                    frameListStruct = new FrameListStruct_0001()
                    {
                        frames = new List<Frame>()
                        {
                            new Frame()
                            {
                                position = new Vertex3(),
                                rotationMatrix = RenderWareFile.Sections.Matrix3x3.Identity,
                                parentFrame = -1,
                                unknown = 131075
                            },
                            new Frame()
                            {
                                position = new Vertex3(),
                                rotationMatrix = RenderWareFile.Sections.Matrix3x3.Identity,
                                parentFrame = 0,
                                unknown = 0
                            }
                        }
                    },
                    extensionList = new List<Extension_0003>()
                    {
                        new Extension_0003(),
                        new Extension_0003()
                    }
                },
                geometryList = new GeometryList_001A()
                {
                    geometryListStruct = new GeometryListStruct_0001()
                    {
                        numberOfGeometries = 1
                    },
                    geometryList = new List<Geometry_000F>()
                    {
                        new Geometry_000F()
                        {
                            materialList = new MaterialList_0008()
                            {
                                materialListStruct = new MaterialListStruct_0001()
                                {
                                    materialCount = materials.Length
                                },
                                materialList = materials
                            },
                            geometryStruct = new GeometryStruct_0001()
                            {
                                geometryFlags =
                                GeometryFlags.hasLights |
                                GeometryFlags.modeulateMaterialColor |
                                GeometryFlags.hasTextCoords |
                                GeometryFlags.hasVertexColors |
                                GeometryFlags.hasVertexPositions |
                                GeometryFlags.hasNormals,
                                geometryFlags2 = (GeometryFlags2)1,
                                numTriangles = triangles.Length,
                                numVertices = vertices.Length,
                                numMorphTargets = 1,
                                ambient = 1f,
                                specular = 1f,
                                diffuse = 1f,
                                vertexColors = vertexColors,
                                textCoords = textCoords,
                                triangles = triangles,
                                morphTargets = new MorphTarget[]
                                {
                                    new MorphTarget()
                                    {
                                        hasNormals = 1,
                                        hasVertices = 1,
                                        sphereCenter = new Vertex3(
                                            boundingSphere.Center.X,
                                            boundingSphere.Center.Y,
                                            boundingSphere.Center.Z),
                                        radius = boundingSphere.Radius,
                                        vertices = vertices,
                                        normals = normals,
                                    }
                                }
                            },
                            geometryExtension = new Extension_0003()
                            {
                                extensionSectionList = new List<RWSection>()
                                {
                                    new BinMeshPLG_050E()
                                    {
                                        binMeshHeaderFlags =  BinMeshHeaderFlags.TriangleList,
                                        numMeshes = binMeshes.Length,
                                        totalIndexCount = binMeshes.Sum(b => b.indexCount),
                                        binMeshList = binMeshes
                                    }
                                }
                            }
                        }
                    }
                },
                atomicList = new List<Atomic_0014>() { new Atomic_0014()
                {
                    atomicStruct = new AtomicStruct_0001()
                    {
                        frameIndex = 1,
                        geometryIndex = 0,
                        flags = AtomicFlags.CollisionTestAndRender,
                        unused = 0
                    },
                    atomicExtension = new Extension_0003() // check this in case something fails
                    {
                        extensionSectionList = atomicNeedsMaterialEffects ? new List<RWSection>()
                        {
                            new MaterialEffectsPLG_0120()
                            {
                                isAtomicExtension = true,
                                value = (MaterialEffectType)1
                            }
                        }
                        : new List<RWSection>()
                    }
                }
                },

                clumpExtension = new Extension_0003()
            };

            return clump;
        }

        public static int MaximumBoundary => 1000;

        public static RWSection[] CreateBSPFromAssimp(string fileName, bool flipUVs, bool ignoreMeshColors)
        {
            PostProcessSteps pps =
                PostProcessSteps.Debone | PostProcessSteps.FindInstances |
                PostProcessSteps.FindInvalidData | PostProcessSteps.OptimizeGraph |
                PostProcessSteps.OptimizeMeshes | PostProcessSteps.Triangulate |
                PostProcessSteps.PreTransformVertices;

            Scene scene = new AssimpContext().ImportFile(fileName, pps);

            int vertexCount = scene.Meshes.Sum(m => m.VertexCount);
            int triangleCount = scene.Meshes.Sum(m => m.FaceCount);

            if (vertexCount > TRI_AND_VERTEX_LIMIT || triangleCount > TRI_AND_VERTEX_LIMIT)
                throw new ArgumentException("Model has too many vertices or triangles. Please import a simpler model.");

            List<Vertex3> vertices = new List<Vertex3>(vertexCount);
            List<RenderWareFile.Color> vColors = new List<RenderWareFile.Color>(vertexCount);
            List<Vertex2> textCoords = new List<Vertex2>(vertexCount);
            List<RenderWareFile.Triangle> triangles = new List<RenderWareFile.Triangle>(triangleCount);

            int totalVertices = 0;

            foreach (var m in scene.Meshes)
            {
                foreach (Vector3D v in m.Vertices)
                    vertices.Add(new Vertex3(v.X, v.Y, v.Z));

                if (m.HasTextureCoords(0))
                    foreach (Vector3D v in m.TextureCoordinateChannels[0])
                        textCoords.Add(new Vertex2(v.X, flipUVs ? -v.Y : v.Y));
                else
                    for (int i = 0; i < m.VertexCount; i++)
                        textCoords.Add(new Vertex2());

                if (m.HasVertexColors(0))
                    foreach (Color4D c in m.VertexColorChannels[0])
                        vColors.Add(new RenderWareFile.Color(
                            (byte)(c.R * 255),
                            (byte)(c.G * 255),
                            (byte)(c.B * 255),
                            (byte)(c.A * 255)));
                else
                    for (int i = 0; i < m.VertexCount; i++)
                        vColors.Add(new RenderWareFile.Color(255, 255, 255, 255));

                foreach (var t in m.Faces)
                    triangles.Add(new RenderWareFile.Triangle()
                    {
                        vertex1 = (ushort)(t.Indices[0] + totalVertices),
                        vertex2 = (ushort)(t.Indices[1] + totalVertices),
                        vertex3 = (ushort)(t.Indices[2] + totalVertices),
                        materialIndex = (ushort)m.MaterialIndex
                    });

                totalVertices += m.VertexCount;
            }

            if (vertices.Count != textCoords.Count || vertices.Count != vColors.Count)
                throw new ArgumentException("Internal error: texture coordinate or vertex color count is different from vertex count.");

            triangles = triangles.OrderBy(t => t.materialIndex).ToList();

            Vertex3 Max = new Vertex3(vertices[0].X, vertices[0].Y, vertices[0].Z);
            Vertex3 Min = new Vertex3(vertices[0].X, vertices[0].Y, vertices[0].Z);

            //foreach (Vertex3 i in vertices)
            //{
            //    if (i.X > Max.X)
            //        Max.X = i.X;
            //    if (i.Y > Max.Y)
            //        Max.Y = i.Y;
            //    if (i.Z > Max.Z)
            //        Max.Z = i.Z;
            //    if (i.X < Min.X)
            //        Min.X = i.X;
            //    if (i.Y < Min.Y)
            //        Min.Y = i.Y;
            //    if (i.Z < Min.Z)
            //        Min.Z = i.Z;
            //}

            Max = new Vertex3(MaximumBoundary, MaximumBoundary, MaximumBoundary);
            Min = new Vertex3(-MaximumBoundary, -MaximumBoundary, -MaximumBoundary);

            BinMesh[] binMeshes = new BinMesh[scene.MaterialCount];

            Material_0007[] materials = new Material_0007[scene.MaterialCount];

            for (int i = 0; i < scene.MaterialCount; i++)
            {
                List<int> indices = new List<int>(triangles.Count);
                foreach (RenderWareFile.Triangle f in triangles)
                    if (f.materialIndex == i)
                    {
                        indices.Add(f.vertex1);
                        indices.Add(f.vertex2);
                        indices.Add(f.vertex3);
                    }

                binMeshes[i] = new BinMesh()
                {
                    materialIndex = i,
                    indexCount = indices.Count(),
                    vertexIndices = indices.ToArray()
                };

                materials[i] = new Material_0007()
                {
                    materialStruct = new MaterialStruct_0001()
                    {
                        unusedFlags = 0,
                        color = ignoreMeshColors ?
                       new RenderWareFile.Color(255, 255, 255, 255) :
                       new RenderWareFile.Color(
                             (byte)(scene.Materials[i].ColorDiffuse.R / 255),
                             (byte)(scene.Materials[i].ColorDiffuse.G / 255),
                             (byte)(scene.Materials[i].ColorDiffuse.B / 255),
                             (byte)(scene.Materials[i].ColorDiffuse.A / 255)),
                        unusedInt2 = 0x2DF53E84,
                        isTextured = scene.Materials[i].HasTextureDiffuse ? 1 : 0,
                        ambient = ignoreMeshColors ? 1f : scene.Materials[i].ColorAmbient.A,
                        specular = ignoreMeshColors ? 1f : scene.Materials[i].ColorSpecular.A,
                        diffuse = ignoreMeshColors ? 1f : scene.Materials[i].ColorDiffuse.A
                    },
                    texture = scene.Materials[i].HasTextureDiffuse ? RWTextureFromAssimpMaterial(scene.Materials[i].TextureDiffuse) : null,
                    materialExtension = new Extension_0003()
                    {
                        extensionSectionList = new List<RWSection>()
                    },
                };
            }

            WorldFlags worldFlags = WorldFlags.HasOneSetOfTextCoords | WorldFlags.HasVertexColors | WorldFlags.WorldSectorsOverlap | (WorldFlags)0x00010000;

            World_000B world = new World_000B()
            {
                worldStruct = new WorldStruct_0001()
                {
                    rootIsWorldSector = 1,
                    inverseOrigin = new Vertex3(-0f, -0f, -0f),
                    numTriangles = (uint)triangleCount,
                    numVertices = (uint)vertexCount,
                    numPlaneSectors = 0,
                    numAtomicSectors = 1,
                    colSectorSize = 0,
                    worldFlags = worldFlags,
                    boxMaximum = Max,
                    boxMinimum = Min,
                },

                materialList = new MaterialList_0008()
                {
                    materialListStruct = new MaterialListStruct_0001()
                    {
                        materialCount = scene.MaterialCount
                    },
                    materialList = materials
                },

                firstWorldChunk = new AtomicSector_0009()
                {
                    atomicSectorStruct = new AtomicSectorStruct_0001()
                    {
                        matListWindowBase = 0,
                        numTriangles = triangleCount,
                        numVertices = vertexCount,
                        boxMaximum = Max,
                        boxMinimum = Min,
                        collSectorPresent = 0x2F50D984,
                        unused = 0,
                        vertexArray = vertices.ToArray(),
                        colorArray = vColors.ToArray(),
                        uvArray = textCoords.ToArray(),
                        triangleArray = triangles.ToArray()
                    },
                    atomicSectorExtension = new Extension_0003()
                    {
                        extensionSectionList = new List<RWSection>() {
                            new BinMeshPLG_050E()
                            {
                                binMeshHeaderFlags = BinMeshHeaderFlags.TriangleList,
                                numMeshes = binMeshes.Count(),
                                totalIndexCount = binMeshes.Sum(b => b.indexCount),
                                binMeshList = binMeshes
                            },
                            new CollisionPLG_011D_Scooby()
                            {
                                splits = new Split_Scooby[0],
                                startIndex_amountOfTriangles = new short[][] { new short[] { 0, (short)triangles.Count } },
                                triangles = TriangleRange(triangles.Count)
                            }
                        }
                    }
                },

                worldExtension = new Extension_0003()
            };

            return new RWSection[] { world };
        }

        private static int[] TriangleRange(int count)
        {
            var result = new int[count];
            for (int i = 0; i < count; i++)
                result[i] = i;
            return result;
        }

        public static void ExportAssimp(string fileName, RWSection[] bspFile, bool flipUVs, ExportFormatDescription format, string textureExtension, Matrix worldTransform)
        {
            Scene scene = new Scene();

            foreach (RWSection rw in bspFile)
                if (rw is World_000B w)
                    WorldToScene(scene, w, textureExtension);
                else if (rw is Clump_0010 c)
                    ClumpToScene(scene, c, textureExtension, worldTransform);

            scene.RootNode = new Node() { Name = "root" };

            Node latest = scene.RootNode;

            for (int i = 0; i < scene.MeshCount; i++)
            {
                latest.Children.Add(Newtonsoft.Json.JsonConvert.DeserializeObject<Node>(
                    "{\"Name\":\"" + scene.Meshes[i].Name + "\", \"MeshIndices\": [" + i.ToString() + "]}"));

                //latest = latest.Children[0];
            }

            new AssimpContext().ExportFile(scene, fileName, format.FormatId,
                PostProcessSteps.Debone |
                PostProcessSteps.FindInstances |
                //PostProcessSteps.GenerateNormals |
                PostProcessSteps.FindInvalidData |
                PostProcessSteps.JoinIdenticalVertices |
                PostProcessSteps.OptimizeGraph |
                PostProcessSteps.OptimizeMeshes |
                PostProcessSteps.PreTransformVertices |
                PostProcessSteps.RemoveRedundantMaterials |
                PostProcessSteps.Triangulate |
                PostProcessSteps.ValidateDataStructure |
                (flipUVs ? PostProcessSteps.FlipUVs : 0));
        }

        private static void WorldToScene(Scene scene, World_000B world, string textureExtension)
        {
            for (int i = 0; i < world.materialList.materialList.Length; i++)
            {
                var mat = world.materialList.materialList[i];

                scene.Materials.Add(new Material()
                {
                    ColorDiffuse = new Color4D(
                        mat.materialStruct.color.R / 255f,
                        mat.materialStruct.color.G / 255f,
                        mat.materialStruct.color.B / 255f,
                        mat.materialStruct.color.A / 255f),
                    TextureDiffuse = mat.materialStruct.isTextured != 0 ? new TextureSlot()
                    {
                        FilePath = mat.texture.diffuseTextureName.stringString + textureExtension,
                        TextureType = TextureType.Diffuse
                    } : default,
                    Name = mat.materialStruct.isTextured != 0 ? "mat_" + mat.texture.diffuseTextureName.stringString : default,
                });

                scene.Meshes.Add(new Mesh(PrimitiveType.Triangle)
                {
                    MaterialIndex = i,
                    Name = "mesh_" +
                    (mat.materialStruct.isTextured != 0 ? mat.texture.diffuseTextureName.stringString : ("default_" + i.ToString()))
                });
            }

            if (world.firstWorldChunk.sectionIdentifier == Section.AtomicSector)
                AtomicToScene(scene, (AtomicSector_0009)world.firstWorldChunk);
            else if (world.firstWorldChunk.sectionIdentifier == Section.PlaneSector)
                PlaneToScene(scene, (PlaneSector_000A)world.firstWorldChunk);
        }

        private static void PlaneToScene(Scene scene, PlaneSector_000A planeSection)
        {
            if (planeSection.leftSection is AtomicSector_0009 a1)
            {
                AtomicToScene(scene, a1);
            }
            else if (planeSection.leftSection is PlaneSector_000A p1)
            {
                PlaneToScene(scene, p1);
            }

            if (planeSection.rightSection is AtomicSector_0009 a2)
            {
                AtomicToScene(scene, a2);
            }
            else if (planeSection.rightSection is PlaneSector_000A p2)
            {
                PlaneToScene(scene, p2);
            }
        }

        private static void AtomicToScene(Scene scene, AtomicSector_0009 atomic)
        {
            if (atomic.atomicSectorStruct.isNativeData)
            {
                NativeDataGC n = null;

                foreach (RWSection rws in atomic.atomicSectorExtension.extensionSectionList)
                    if (rws is NativeDataPLG_0510 native)
                        n = native.nativeDataStruct.nativeData;

                if (n == null)
                    throw new Exception("Unable to find native data section");

                GetNativeTriangleList(scene, n);
                return;
            }

            int[] totalVertexIndices = new int[scene.MeshCount];

            for (int i = 0; i < scene.MeshCount; i++)
                totalVertexIndices[i] = scene.Meshes[i].VertexCount;

            foreach (RenderWareFile.Triangle t in atomic.atomicSectorStruct.triangleArray)
            {
                scene.Meshes[t.materialIndex].Faces.Add(new Face(new int[] {
                    t.vertex1 + totalVertexIndices[t.materialIndex],
                    t.vertex2 + totalVertexIndices[t.materialIndex],
                    t.vertex3 + totalVertexIndices[t.materialIndex]
                }));
            }

            foreach (Mesh mesh in scene.Meshes)
            {
                foreach (Vertex3 v in atomic.atomicSectorStruct.vertexArray)
                    mesh.Vertices.Add(new Vector3D(v.X, v.Y, v.Z));

                foreach (Vertex2 v in atomic.atomicSectorStruct.uvArray)
                    mesh.TextureCoordinateChannels[0].Add(new Vector3D(v.X, v.Y, 0f));

                foreach (RenderWareFile.Color c in atomic.atomicSectorStruct.colorArray)
                    mesh.VertexColorChannels[0].Add(new Color4D(
                        c.R / 255f,
                        c.G / 255f,
                        c.B / 255f,
                        c.A / 255f));
            }
        }

        private static void GetNativeTriangleList(Scene scene, NativeDataGC n, int totalMaterials = 0)
        {
            List<Vertex3> vertexList_init = new List<Vertex3>();
            List<Vertex3> normalList_init = new List<Vertex3>();
            List<RenderWareFile.Color> colorList_init = new List<RenderWareFile.Color>();
            List<Vertex2> textCoordList_init = new List<Vertex2>();

            foreach (Declaration d in n.declarations)
            {
                if (d.declarationType == Declarations.Vertex)
                {
                    var dec = (Vertex3Declaration)d;
                    foreach (var v in dec.entryList)
                        vertexList_init.Add(v);
                }
                else if (d.declarationType == Declarations.Normal)
                {
                    var dec = (Vertex3Declaration)d;
                    foreach (var v in dec.entryList)
                        normalList_init.Add(v);
                }
                else if (d.declarationType == Declarations.Color)
                {
                    var dec = (ColorDeclaration)d;
                    foreach (var c in dec.entryList)
                        colorList_init.Add(c);
                }
                else if (d.declarationType == Declarations.TextCoord)
                {
                    var dec = (Vertex2Declaration)d;
                    foreach (var v in dec.entryList)
                        textCoordList_init.Add(v);
                }
            }

            foreach (TriangleDeclaration td in n.triangleDeclarations)
            {
                Mesh mesh = new Mesh(PrimitiveType.Triangle)
                {
                    MaterialIndex = td.MaterialIndex + totalMaterials,
                    Name = scene.Materials[td.MaterialIndex + totalMaterials].Name.Replace("mat_", "mesh_") + "_" + (scene.MeshCount + 1).ToString()
                };

                foreach (TriangleList tl in td.TriangleListList)
                {
                    int totalVertexIndices = mesh.VertexCount;
                    int vcount = 0;

                    foreach (int[] objectList in tl.entries)
                    {
                        for (int j = 0; j < objectList.Count(); j++)
                        {
                            if (n.declarations[j].declarationType == Declarations.Vertex)
                            {
                                var v = vertexList_init[objectList[j]];
                                mesh.Vertices.Add(new Vector3D(v.X, v.Y, v.Z));
                                vcount++;
                            }
                            else if (n.declarations[j].declarationType == Declarations.Normal)
                            {
                                var v = normalList_init[objectList[j]];
                                mesh.Normals.Add(new Vector3D(v.X, v.Y, v.Z));
                            }
                            else if (n.declarations[j].declarationType == Declarations.Color)
                            {
                                var c = colorList_init[objectList[j]];
                                mesh.VertexColorChannels[0].Add(new Color4D(
                                        c.R / 255f,
                                        c.G / 255f,
                                        c.B / 255f,
                                        c.A / 255f));
                            }
                            else if (n.declarations[j].declarationType == Declarations.TextCoord)
                            {
                                var v = textCoordList_init[objectList[j]];
                                mesh.TextureCoordinateChannels[0].Add(new Vector3D(v.X, v.Y, 0f));
                            }
                        }
                    }

                    bool control = true;
                    for (int i = 2; i < vcount; i++)
                    {
                        if (control)
                        {
                            mesh.Faces.Add(new Face(new int[] {
                                i - 2 + totalVertexIndices,
                                i - 1 + totalVertexIndices,
                                i + totalVertexIndices
                            }));

                            control = false;
                        }
                        else
                        {
                            mesh.Faces.Add(new Face(new int[] {
                                i - 2 + totalVertexIndices,
                                i + totalVertexIndices,
                                i - 1 + totalVertexIndices
                            }));

                            control = true;
                        }
                    }
                }

                scene.Meshes.Add(mesh);
            }
        }

        private static void ClumpToScene(Scene scene, Clump_0010 clump, string textureExtension, Matrix worldTransform)
        {
            int totalMaterials = 0;

            for (int i = 0; i < clump.geometryList.geometryList.Count; i++)
            {
                Matrix transformMatrix = RenderWareModelFile.CreateMatrix(clump.frameList, clump.atomicList[i].atomicStruct.frameIndex);

                for (int j = 0; j < clump.geometryList.geometryList[i].materialList.materialList.Length; j++)
                {
                    var geo = clump.geometryList.geometryList[i].geometryStruct;
                    var mat = clump.geometryList.geometryList[i].materialList.materialList[j];

                    Material material = new Material()
                    {
                        ColorDiffuse = new Color4D(
                                mat.materialStruct.color.R / 255f,
                                mat.materialStruct.color.G / 255f,
                                mat.materialStruct.color.B / 255f,
                                mat.materialStruct.color.A / 255f),
                        Name = "default"
                    };

                    if (mat.materialStruct.isTextured != 0)
                    {
                        material.TextureDiffuse = new TextureSlot()
                        {
                            FilePath = mat.texture.diffuseTextureName.stringString + textureExtension,
                            TextureType = TextureType.Diffuse
                        };
                        material.Name = "mat_" + mat.texture.diffuseTextureName.stringString;
                    }

                    scene.Materials.Add(material);

                    Mesh mesh = new Mesh(PrimitiveType.Triangle)
                    {
                        MaterialIndex = j + totalMaterials,
                        Name = "mesh_" + material.Name.Replace("mat_", "")
                    };

                    if ((geo.geometryFlags2 & GeometryFlags2.isNativeGeometry) != 0)
                    {
                        NativeDataGC n = null;

                        foreach (RWSection rws in clump.geometryList.geometryList[i].geometryExtension.extensionSectionList)
                            if (rws is NativeDataPLG_0510 native)
                                n = native.nativeDataStruct.nativeData;

                        if (n == null)
                            throw new Exception("Unable to find native data section");

                        GetNativeTriangleList(scene, n, totalMaterials);
                    }
                    else
                    {
                        foreach (var v in geo.morphTargets[0].vertices)
                        {
                            var vt = Vector3.Transform((Vector3)Vector3.Transform(new Vector3(v.X, v.Y, v.Z), transformMatrix), worldTransform);
                            mesh.Vertices.Add(new Vector3D(vt.X, vt.Y, vt.Z));
                        }

                        if ((geo.geometryFlags & GeometryFlags.hasNormals) != 0)
                            foreach (var v in geo.morphTargets[0].normals)
                                mesh.Normals.Add(new Vector3D(v.X, v.Y, v.Z));

                        if ((geo.geometryFlags & GeometryFlags.hasTextCoords) != 0)
                            foreach (var v in geo.textCoords)
                                mesh.TextureCoordinateChannels[0].Add(new Vector3D(v.X, v.Y, 0));

                        if ((geo.geometryFlags & GeometryFlags.hasVertexColors) != 0)
                            foreach (var color in geo.vertexColors)
                                mesh.VertexColorChannels[0].Add(new Color4D(color.R / 255f, color.G / 255f, color.B / 255f, color.A / 255f));

                        foreach (var t in geo.triangles)
                            if (t.materialIndex == j)
                                mesh.Faces.Add(new Face(new int[] { t.vertex1, t.vertex2, t.vertex3 }));

                        scene.Meshes.Add(mesh);
                    }
                }
                totalMaterials = scene.Materials.Count;
            }
        }
    }
}
