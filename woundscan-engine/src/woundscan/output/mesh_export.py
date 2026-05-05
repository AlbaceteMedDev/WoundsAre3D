"""Export the fused depth surface as a 3D mesh (OBJ format).

The wound reconstruction is a regular (X, Y) grid with a per-cell depth Z,
restricted to the wound mask. We emit each masked cell as two triangles,
forming a closed surface that can be loaded directly by SceneKit / RealityKit
on iOS, or any WebGL/Blender viewer.

Coordinates are emitted in millimeters in the wound-local frame, with +Z
pointing INTO the wound (depth below skin surface). The iOS viewer flips Z
on load so that deeper regions sink visually.
"""

from __future__ import annotations

import io

import numpy as np


def grid_to_obj(
    x_mm: np.ndarray,
    y_mm: np.ndarray,
    z_mm: np.ndarray,
    mask: np.ndarray,
) -> bytes:
    """Convert a (Ny, Nx) depth grid + boolean mask into a Wavefront OBJ.

    Parameters
    ----------
    x_mm, y_mm : (Ny, Nx) meshgrid in millimeters
    z_mm       : (Ny, Nx) depth in millimeters (positive = below surface)
    mask       : (Ny, Nx) bool — only cells where mask is True become geometry

    Returns
    -------
    OBJ file contents as bytes (UTF-8). Single mesh, no materials.
    """
    if x_mm.shape != y_mm.shape or x_mm.shape != z_mm.shape or x_mm.shape != mask.shape:
        raise ValueError("x_mm, y_mm, z_mm, mask must all share shape")

    ny, nx = x_mm.shape
    # vertex_idx[i, j] = 1-based OBJ vertex index for (i, j), or 0 if not emitted
    vertex_idx = np.zeros((ny, nx), dtype=np.int64)

    buf = io.StringIO()
    buf.write("# WoundScan reconstructed surface\n")
    buf.write("# Units: millimeters; +Z = depth below skin\n")
    buf.write("o WoundSurface\n")

    # Emit one vertex per masked cell. We also include the immediate neighbors
    # of masked cells to avoid jagged boundaries (the mesh sealing happens at
    # mask-edge vertices, which we still emit even if their mask cell is False
    # but at least one neighbor is True).
    neighbor_mask = mask.copy()
    neighbor_mask[1:, :] |= mask[:-1, :]
    neighbor_mask[:-1, :] |= mask[1:, :]
    neighbor_mask[:, 1:] |= mask[:, :-1]
    neighbor_mask[:, :-1] |= mask[:, 1:]

    next_idx = 1
    for i in range(ny):
        for j in range(nx):
            if not neighbor_mask[i, j]:
                continue
            x = float(x_mm[i, j])
            y = float(y_mm[i, j])
            z = float(z_mm[i, j])
            buf.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
            vertex_idx[i, j] = next_idx
            next_idx += 1

    # Emit two triangles per masked quad. A quad (i, j) has corners
    # (i, j), (i, j+1), (i+1, j), (i+1, j+1). Emit only if all four corners
    # have indices AND at least one corner cell is in the mask (so we don't
    # bridge across detached neighbor regions).
    faces = 0
    for i in range(ny - 1):
        for j in range(nx - 1):
            v00 = vertex_idx[i, j]
            v01 = vertex_idx[i, j + 1]
            v10 = vertex_idx[i + 1, j]
            v11 = vertex_idx[i + 1, j + 1]
            if v00 == 0 or v01 == 0 or v10 == 0 or v11 == 0:
                continue
            if not (mask[i, j] or mask[i, j + 1] or mask[i + 1, j] or mask[i + 1, j + 1]):
                continue
            # OBJ winding: counter-clockwise as viewed from +Z (toward camera
            # looking down at the wound)
            buf.write(f"f {v00} {v10} {v11}\n")
            buf.write(f"f {v00} {v11} {v01}\n")
            faces += 2

    buf.write(f"# {next_idx - 1} vertices, {faces} triangles\n")
    return buf.getvalue().encode("utf-8")
