#!/usr/bin/env python3
"""
Convert DeepReefMap point_cloud_tsdf.csv to a solid mesh using Open3D Poisson reconstruction.
Outputs a .ply mesh that can be opened in CloudCompare or MeshLab.

Usage:
    python3 build_mesh.py <path_to_point_cloud_tsdf.csv> [output.ply]

Example:
    python3 build_mesh.py output_GX010236/point_cloud_tsdf.csv output_GX010236/mesh.ply
"""

import sys
import numpy as np
import pandas as pd
import open3d as o3d

def build_mesh(csv_path: str, output_path: str = None, poisson_depth: int = 10):
    if output_path is None:
        output_path = csv_path.replace("point_cloud_tsdf.csv", "mesh.ply")

    print(f"Loading {csv_path} ...")
    df = pd.read_csv(csv_path)
    print(f"  {len(df):,} points loaded")

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(df[["x", "y", "z"]].values)
    pcd.colors = o3d.utility.Vector3dVector(df[["r", "g", "b"]].values / 255.0)

    # Downsample slightly to speed up normal estimation while keeping density
    print("Downsampling ...")
    pcd = pcd.voxel_down_sample(voxel_size=0.002)
    print(f"  {len(pcd.points):,} points after downsampling")

    # Estimate normals — radius tuned to bounding box size
    bbox = pcd.get_axis_aligned_bounding_box()
    diag = np.linalg.norm(np.array(bbox.max_bound) - np.array(bbox.min_bound))
    radius = diag * 0.01
    print(f"  Bounding box diagonal: {diag:.4f}, normal radius: {radius:.4f}")

    print("Estimating normals ...")
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=30)
    )
    print("Orienting normals ...")
    pcd.orient_normals_consistent_tangent_plane(30)

    # Poisson surface reconstruction
    print(f"Running Poisson reconstruction (depth={poisson_depth}) ...")
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=poisson_depth, scale=1.1, linear_fit=False
    )

    # Remove low-density vertices (artifacts at the edges)
    densities = np.asarray(densities)
    threshold = np.quantile(densities, 0.05)
    vertices_to_remove = densities < threshold
    mesh.remove_vertices_by_mask(vertices_to_remove)
    mesh.compute_vertex_normals()
    print(f"  Mesh: {len(mesh.vertices):,} vertices, {len(mesh.triangles):,} triangles")

    print(f"Saving mesh to {output_path} ...")
    o3d.io.write_triangle_mesh(output_path, mesh)
    print("Done.")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    csv_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    depth = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    build_mesh(csv_path, output_path, poisson_depth=depth)
