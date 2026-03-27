# Seafloor 3D Reconstruction

Semantic 3D reconstruction of coral reef seafloor from underwater GoPro video, using [DeepReefMap](https://josauder.github.io/deepreefmap/) (EPFL / Transnational Red Sea Center).

## What it does

- Takes an underwater video as input
- Estimates per-pixel depth using a neural network
- Tracks camera movement across frames
- Fuses everything into a TSDF 3D volume
- Outputs a dense colored point cloud + automatic benthic cover analysis (coral, sand, algae, etc.)

## Requirements

- Docker
- NVIDIA GPU + `nvidia-container-toolkit` (for GPU acceleration)
- ~5 GB free disk space
- CloudCompare (for visualization)

### Install nvidia-container-toolkit (GPU support)

```bash
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verify:
```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

## Input video

Filmed with a **GoPro Hero 10** at ~30fps, swimming 1–4m above the reef in a straight transect.

> Note: if the video has been edited/enhanced (not a raw GoPro file), the IMU gravity vectors cannot be extracted. Reconstruction still works, with a warning.

## Running the reconstruction

### Pull the Docker image

```bash
docker pull ghcr.io/josauder/mee-deepreefmap
```

### Basic run (GPU)

Output is named after the video file to avoid overwriting results:

```bash
VIDEO=/path/to/YOUR_VIDEO.MP4
VIDEO_NAME=$(basename "$VIDEO" .MP4)

docker run --gpus all \
    -v "$(dirname $VIDEO)":/input \
    -v "$(pwd)/output_${VIDEO_NAME}":/output \
    ghcr.io/josauder/mee-deepreefmap \
    --input_video=/input/"${VIDEO_NAME}".MP4 \
    --timestamp=0-38 \
    --out_dir=/output \
    --fps=30
```

`--timestamp` is in seconds: `START-END`. Use `0-<duration>` for full video.

### High-density run (fewer holes, recommended)

```bash
VIDEO=/path/to/YOUR_VIDEO.MP4
VIDEO_NAME=$(basename "$VIDEO" .MP4)
mkdir -p "output_${VIDEO_NAME}"

docker run --gpus all \
    -v "$(dirname $VIDEO)":/input \
    -v "$(pwd)/output_${VIDEO_NAME}":/output \
    ghcr.io/josauder/mee-deepreefmap \
    --input_video=/input/"${VIDEO_NAME}".MP4 \
    --timestamp=0-38 \
    --out_dir=/output \
    --fps=30 \
    --number_of_points_per_image=8000 \
    --distance_thresh=0.4 \
    --height=512 \
    --width=832 2>&1 | tee "output_${VIDEO_NAME}/reconstruction.log"
```

### Running multiple videos in parallel (multi-GPU)

Assign each video to a specific GPU using `--gpus '"device=N"'`:

```bash
VIDEO_DIR=/path/to/videos

# GPU 0 — first video
VIDEO_NAME=GX010236_synced_enhanced
mkdir -p output_${VIDEO_NAME}
docker run -d --gpus '"device=0"' \
    -v ${VIDEO_DIR}:/input \
    -v $(pwd)/output_${VIDEO_NAME}:/output \
    ghcr.io/josauder/mee-deepreefmap \
    --input_video=/input/${VIDEO_NAME}.MP4 \
    --timestamp=0-38 --out_dir=/output --fps=30 \
    --number_of_points_per_image=8000 --distance_thresh=0.4 \
    --height=512 --width=832

# GPU 1 — second video
VIDEO_NAME=GX010236
mkdir -p output_${VIDEO_NAME}
docker run -d --gpus '"device=1"' \
    -v ${VIDEO_DIR}:/input \
    -v $(pwd)/output_${VIDEO_NAME}:/output \
    ghcr.io/josauder/mee-deepreefmap \
    --input_video=/input/${VIDEO_NAME}.MP4 \
    --timestamp=0-38 --out_dir=/output --fps=30 \
    --number_of_points_per_image=8000 --distance_thresh=0.4 \
    --height=512 --width=832
```

### Key parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--fps` | 8 | Frames per second to extract (match your video fps for max density) |
| `--number_of_points_per_image` | 2000 | Points sampled per frame — increase to fill holes |
| `--distance_thresh` | 0.2 | Max distance from camera for a point to be included |
| `--height` / `--width` | 384 / 640 | Processing resolution — higher = more detail, slower |
| `--frames_per_volume` | 500 | Frames per TSDF sub-volume |
| `--tsdf_overlap` | 100 | Overlap between TSDF volumes |

### Multi-segment video (GoPro 4GB chunks)

```bash
docker run --gpus all ... \
    --input_video=/input/VIDEO_1.MP4,/input/VIDEO_2.MP4 \
    --timestamp=0-end,begin-120
```

## Output files

| File | Description |
|------|-------------|
| `point_cloud_tsdf.csv` | 3D point cloud — x,y,z + RGB + semantic class per point |
| `percentage_covers.json` | Benthic cover percentages per class (coral, sand, algae…) |
| `class_to_color.json` | Color palette for each semantic class |
| `results.npy` | Raw NumPy predictions |

## Visualizing with CloudCompare

1. Install: `sudo apt install cloudcompare` (Linux) or download from [cloudcompare.org](https://cloudcompare.org)
2. `File > Open` → select `point_cloud_tsdf.csv`
3. In the import dialog, assign:
   - Column 1 → `coord. X`
   - Column 2 → `coord. Y`
   - Column 3 → `coord. Z`
   - Column 4 → `Red (0-255)`
   - Column 5 → `Green (0-255)`
   - Column 6 → `Blue (0-255)`
   - Remaining columns → `Scalar`
4. After loading, click the cloud in **DB Tree** → in **Properties**, set `Colors` to `RGB`
5. Increase `Point size` to 3–4 to reduce visual holes

### Generate a solid mesh (optional)

In CloudCompare: `Edit > Mesh > Delaunay 2.5D (best fit plane)` — works well for relatively flat seafloor.

## Benthic cover example output

```json
{
  "branching alive": 0.339,
  "algae covered substrate": 0.231,
  "sand": 0.108,
  "massive/meandering alive": 0.104,
  "acropora alive": 0.062
}
```

## Notes on camera intrinsics

DeepReefMap defaults to GoPro Hero 10 intrinsics. For other cameras, provide an `intrinsics.json`:

```json
{
  "fx": 1000.0,
  "fy": 1000.0,
  "cx": 960.0,
  "cy": 540.0,
  "alpha": 0.0
}
```

Then add: `--intrinsics_file=/input/intrinsics.json`

## References

- [DeepReefMap project page](https://josauder.github.io/deepreefmap/)
- [GitHub: josauder/mee-deepreefmap](https://github.com/josauder/mee-deepreefmap)
- Paper: [Scalable Semantic 3D Mapping of Coral Reefs with Deep Learning](https://arxiv.org/abs/2309.12804) — Sauder et al., 2023
