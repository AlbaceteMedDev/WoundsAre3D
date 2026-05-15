"""Tests for output/mesh_export: grid → OBJ conversion."""

from __future__ import annotations

import numpy as np
import pytest

from woundscan.output.mesh_export import grid_to_obj


def _grid(n: int = 5):
    x, y = np.meshgrid(
        np.linspace(-10, 10, n), np.linspace(-10, 10, n), indexing="xy"
    )
    z = (x**2 + y**2) / 100.0  # paraboloid in mm
    return x, y, z


class TestGridToOBJ:
    def test_emits_obj_header_and_body(self):
        x, y, z = _grid()
        mask = np.ones_like(x, dtype=bool)
        obj = grid_to_obj(x, y, z, mask).decode("utf-8")
        assert obj.startswith("# WoundScan reconstructed surface")
        assert "o WoundSurface" in obj
        assert "v " in obj
        assert "f " in obj

    def test_full_mask_produces_expected_vertex_count(self):
        x, y, z = _grid(5)
        mask = np.ones((5, 5), dtype=bool)
        obj = grid_to_obj(x, y, z, mask).decode("utf-8")
        vertex_count = sum(1 for line in obj.splitlines() if line.startswith("v "))
        assert vertex_count == 25  # 5×5 grid, all cells emitted

    def test_full_mask_produces_two_triangles_per_quad(self):
        x, y, z = _grid(5)
        mask = np.ones((5, 5), dtype=bool)
        obj = grid_to_obj(x, y, z, mask).decode("utf-8")
        face_count = sum(1 for line in obj.splitlines() if line.startswith("f "))
        # 4×4 quads × 2 triangles each = 32
        assert face_count == 32

    def test_empty_mask_emits_no_geometry(self):
        x, y, z = _grid(5)
        mask = np.zeros((5, 5), dtype=bool)
        obj = grid_to_obj(x, y, z, mask).decode("utf-8")
        assert not any(line.startswith("v ") for line in obj.splitlines())
        assert not any(line.startswith("f ") for line in obj.splitlines())

    def test_partial_mask_seals_at_boundary(self):
        x, y, z = _grid(7)
        mask = np.zeros((7, 7), dtype=bool)
        # Central 3×3 square of "wound bed" cells.
        mask[2:5, 2:5] = True
        obj = grid_to_obj(x, y, z, mask).decode("utf-8")
        v = sum(1 for line in obj.splitlines() if line.startswith("v "))
        f = sum(1 for line in obj.splitlines() if line.startswith("f "))
        # The neighbor-dilation is 4-connected: each True cell pulls in its
        # N/S/E/W neighbors, producing a plus-shaped region around the 3×3
        # core (9 core + 4 sides × 3 cells = 21 vertices).
        assert v == 21
        # At least one triangle should be emitted around the masked center.
        assert f > 0

    def test_shape_mismatch_raises(self):
        x, y, z = _grid(5)
        bad_mask = np.ones((3, 3), dtype=bool)
        with pytest.raises(ValueError):
            grid_to_obj(x, y, z, bad_mask)

    def test_output_is_utf8_bytes(self):
        x, y, z = _grid(3)
        mask = np.ones((3, 3), dtype=bool)
        result = grid_to_obj(x, y, z, mask)
        assert isinstance(result, bytes)
        # Round-trip through utf-8 must succeed.
        result.decode("utf-8")

    def test_vertices_are_in_millimeters_and_ordered(self):
        x, y, z = _grid(3)
        mask = np.ones((3, 3), dtype=bool)
        obj = grid_to_obj(x, y, z, mask).decode("utf-8")
        verts = [
            tuple(float(x) for x in line.split()[1:4])
            for line in obj.splitlines()
            if line.startswith("v ")
        ]
        # First vertex should be the top-left of the grid (-10, -10, computed z).
        assert verts[0][0] == pytest.approx(-10.0)
        assert verts[0][1] == pytest.approx(-10.0)
