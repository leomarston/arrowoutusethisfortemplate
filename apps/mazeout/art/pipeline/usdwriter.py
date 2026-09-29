"""Write PartMeshes to a USDZ: one Mesh prim per part, one UsdPreviewSurface material per material.

Layout:
  /<Item>            Xform, kind=component, defaultPrim
    /Geom/<part>     Mesh (points, normals[vertex], st[vertex] if textured, subdivisionScheme=none)
    /Materials/<mat> Material -> PreviewSurface (+ UsdUVTexture + PrimvarReader when textured)

Colours are authored linear (UsdPreviewSurface spec); textures are sRGB PNGs.
upAxis=Y, metersPerUnit=1 (1 unit = 1 board cell).
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile

import numpy as np
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdUtils, Vt

from mesher import bake_texture, srgb_to_linear


def _ident(s):
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    return s if not s[0].isdigit() else "_" + s


def write_usdz(item_name, meshes, out_path, log=print):
    tmpdir = tempfile.mkdtemp(prefix="mfusd_")
    try:
        root_name = _ident(item_name)
        usdc = os.path.join(tmpdir, f"{root_name}.usdc")
        stage = Usd.Stage.CreateNew(usdc)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        root = UsdGeom.Xform.Define(stage, f"/{root_name}")
        stage.SetDefaultPrim(root.GetPrim())
        Usd.ModelAPI(root.GetPrim()).SetKind("component")
        UsdGeom.Scope.Define(stage, f"/{root_name}/Geom")
        UsdGeom.Scope.Define(stage, f"/{root_name}/Materials")

        mats = {}
        for pm in meshes:
            m = pm.part.material
            if m.name in mats:
                continue
            mats[m.name] = _material(stage, f"/{root_name}/Materials/{_ident(m.name)}", m, tmpdir, root_name)

        all_lo, all_hi = [], []
        for pm in meshes:
            path = f"/{root_name}/Geom/{_ident(pm.part.name)}"
            mesh = UsdGeom.Mesh.Define(stage, path)
            v = pm.v.astype(np.float32)
            mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(v))
            mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(pm.f), 3, np.int32)))
            mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(pm.f.astype(np.int32).reshape(-1)))
            mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(pm.n.astype(np.float32)))
            mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
            mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
            mesh.CreateOrientationAttr(UsdGeom.Tokens.rightHanded)
            mesh.CreateDoubleSidedAttr(False)
            lo, hi = v.min(0), v.max(0)
            all_lo.append(lo); all_hi.append(hi)
            mesh.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, lo)), Gf.Vec3f(*map(float, hi))]))
            if pm.uv is not None:
                pv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
                pv.Set(Vt.Vec2fArray.FromNumpy(pm.uv.astype(np.float32)))
            UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mats[pm.part.material.name])
        stage.GetRootLayer().Save()
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        if os.path.exists(out_path):
            os.remove(out_path)
        # package by hand: root layer first, then textures (ZipFileWriter does the 64-byte alignment)
        with Sdf.ZipFileWriter.CreateNew(out_path) as zw:
            zw.AddFile(usdc, os.path.basename(usdc))
            tdir = os.path.join(tmpdir, "textures")
            if os.path.isdir(tdir):
                for fn in sorted(os.listdir(tdir)):
                    zw.AddFile(os.path.join(tdir, fn), f"textures/{fn}")
        return out_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def write_outline_usdz(item_name, outline, material, out_path):
    """The outline shell as its own USDZ: /<item>_outline/Geom/outline, same frame as <item>.usdz."""
    from mesher import Part, PartMesh
    pm = PartMesh(Part("outline", None, material, collide=False), outline["v"], outline["f"], outline["n"])
    return write_usdz(f"{item_name}_outline", [pm], out_path)


def _material(stage, path, m, tmpdir, root_name):
    mat = UsdShade.Material.Define(stage, path)
    sh = UsdShade.Shader.Define(stage, path + "/PreviewSurface")
    sh.CreateIdAttr("UsdPreviewSurface")
    lin = srgb_to_linear(m.color_srgb())
    if m.texture is not None:
        img = bake_texture(m)
        fname = f"textures/{_ident(m.name)}.png"
        os.makedirs(os.path.join(tmpdir, "textures"), exist_ok=True)
        Image.fromarray(img).save(os.path.join(tmpdir, fname), optimize=True)
        st = UsdShade.Shader.Define(stage, path + "/stReader")
        st.CreateIdAttr("UsdPrimvarReader_float2")
        st.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
        tex = UsdShade.Shader.Define(stage, path + "/diffuseTexture")
        tex.CreateIdAttr("UsdUVTexture")
        tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(fname))
        tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
        tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(st.ConnectableAPI(), "result")
        tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex.ConnectableAPI(), "rgb")
    else:
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*map(float, lin)))
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(m.roughness))
    sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(m.metallic))
    sh.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(float(m.clearcoat))
    sh.CreateInput("clearcoatRoughness", Sdf.ValueTypeNames.Float).Set(float(m.clearcoat_roughness))
    if m.specular_color:
        from mesher import hex_to_rgb
        sh.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Int).Set(1)
        sh.CreateInput("specularColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*map(float, srgb_to_linear(hex_to_rgb(m.specular_color)))))
    else:
        sh.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Int).Set(0)
    sh.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(float(m.ior))
    if getattr(m, "opacity", 1.0) < 1.0:
        sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(m.opacity))
    if m.emissive:
        from mesher import hex_to_rgb
        e = srgb_to_linear(hex_to_rgb(m.emissive))
        sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*map(float, e)))
    sh.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    return mat


def check_usdz(path):
    """Run USD's ARKit compliance checker; returns (errors, warnings)."""
    try:
        from pxr.UsdUtils import ComplianceChecker
    except Exception:
        return [], ["ComplianceChecker unavailable"]
    c = ComplianceChecker(arkit=True, skipARKitRootLayerCheck=False, rootPackageOnly=False, skipVariants=False)
    c.CheckCompliance(path)
    return list(c.GetErrors()) + list(c.GetFailedChecks()), list(c.GetWarnings())
