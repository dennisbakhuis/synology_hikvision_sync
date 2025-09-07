# Synology Hikvision Sync 📹

A Python-based container solution designed for **Synology NAS** systems that serve as **NFS storage** for **Hikvision cameras**. This tool replaces Surveillance Station by intelligently reorganizing the camera's native storage into clean, organized folders with timestamped filenames - leveraging the cameras' built-in smart features rather than requiring additional NVR software.

## 🎯 **Purpose & Use Case**

This script is specifically designed for setups where:
- 📂 **Synology NAS** acts as NFS storage target for Hikvision cameras
- 📹 **Hikvision cameras** record directly to NAS storage (bypassing Surveillance Station)
- 🧠 **Camera intelligence** handles motion detection, recording triggers, and smart features
- 🗂️ **Organization** is needed to convert Hikvision's proprietary storage format into accessible MP4/JPG files
- 🔄 **Automation** replaces manual file management or expensive NVR licenses

**Benefits over Surveillance Station:**
- ✅ No NVR license costs per camera
- ✅ Uses cameras' native intelligence and processing power  
- ✅ Direct NFS storage - no transcoding overhead
- ✅ Automated retention management
- ✅ Clean, accessible file organization
- ✅ Preserves original video quality

**Author**: Dennis Bakhuis  
**License**: MIT

## 🏗️ **System Architecture**

```
┌─────────────────┐    NFS Mount    ┌─────────────────┐    Docker Container    ┌─────────────────┐
│  Hikvision      │ ──────────────► │   Synology      │ ─────────────────────► │   This Script   │
│  Camera         │                 │   NAS           │                        │                 │
│                 │  Records to:    │                 │  Processes:            │  Outputs:       │
│ • Motion detect │  /volume3/      │ • NFS Server    │  • Extracts segments   │ • Clean MP4s    │
│ • Smart features│    Camera-Tuin/ │ • File Storage  │  • Converts formats    │ • Organized JPGs│
│ • H.264/H.265   │    Camera-Oprit/│ • Docker Host   │  • Applies retention   │ • Folder struct │
└─────────────────┘                 └─────────────────┘                        └─────────────────┘
```

**Setup Requirements:**
1. 🔧 Configure Hikvision cameras to use Synology NAS as NFS storage target
2. 📁 Cameras record directly to `/volume3/Camera-Name/` directories  
3. 🐳 Run this container to process and organize the footage
4. 📂 Access clean, organized files in `/volume1/organized/`

## 🚀 Quick Start with Docker

The easiest way to use this tool is with the pre-built container from GitHub Container Registry:

```bash
# Run continuously (every 10 minutes by default)
docker run -d \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume1/organized:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0

# Run once and exit
docker run --rm -e RUN_MODE=once \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume1/organized:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
```

### Camera Mounting Pattern
Each camera must be mounted separately to `/input/<camera-name>`:

```bash
# Multiple cameras with original names (Camera-Tuin, Camera-Oprit)
docker run -d \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume3/Camera-Front:/input/Camera-Front \
  -v /volume1/organized:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
  
# With camera renaming using CAMERA_TRANSLATION
docker run -d \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume3/Camera-Front:/input/Camera-Front \
  -v /volume1/organized:/output \
  -e CAMERA_TRANSLATION="Camera-Tuin:tuin,Camera-Oprit:driveway,Camera-Front:front" \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
```

This will create organized output like:
```
/volume1/organized/
├── tuin/           # Renamed from Camera-Tuin
│   ├── video/
│   └── images/
├── driveway/       # Renamed from Camera-Oprit  
│   ├── video/
│   └── images/
└── front/          # Renamed from Camera-Front
    ├── video/
    └── images/
```

## 🔧 Configuration

### Cron Scheduling
Control how frequently the sync runs:

```bash
# Run every 5 minutes
docker run -d -e CRON_INTERVAL=5 \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume1/organized:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0

# Run every hour  
docker run -d -e CRON_INTERVAL=60 \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume1/organized:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0

# Run every 6 hours
docker run -d -e CRON_INTERVAL=360 \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume1/organized:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
```

### Camera Translation (Optional)
Map camera folder names to friendly tags using environment variables:

```bash
docker run -d \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume3/Camera-Front:/input/Camera-Front \
  -v /volume1/organized:/output \
  -e CAMERA_TRANSLATION="Camera-Tuin:tuin,Camera-Oprit:driveway,Camera-Front:front" \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
```

**Translation Format**: `"original-name:new-name,another-original:another-new"`
- **Source mount**: `/volume3/Camera-Tuin` → **Container path**: `/input/Camera-Tuin` → **Output folder**: `/output/tuin/`

### Custom Retention Policy
```bash
# Keep files for 30 days
docker run -d -e RETENTION_DAYS=30 \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume1/organized:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
  
# Disable retention (keep all files)
docker run -d -e RETENTION_DAYS=0 \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume1/organized:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
```

### Advanced Configuration
```bash
docker run -d \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume3/Camera-Front:/input/Camera-Front \
  -v /volume1/organized:/output \
  -v /tmp/hikvision_cache:/cache \
  -e CRON_INTERVAL=15 \
  -e RETENTION_DAYS=60 \
  -e CAMERA_TRANSLATION="Camera-Tuin:garden,Camera-Oprit:driveway,Camera-Front:entrance" \
  -e CACHE_DIR=/cache \
  -e LOCK_FILE=/cache/processing.lock \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
```

## 📁 Directory Structure

### Input Structure (Hikvision NAS)
Each camera is mounted separately to its own path in `/input/`:
```
Host Synology:                    Container Input:
/volume3/Camera-Tuin/         →   /input/Camera-Tuin/
├── datadir0/                     ├── datadir0/
├── datadir1/                     ├── datadir1/
└── ...                           └── ...

/volume3/Camera-Oprit/        →   /input/Camera-Oprit/
├── datadir0/                     ├── datadir0/
└── ...                           └── ...
```

### Output Structure (Organized)
The container creates clean, organized folders in `/output/`:
```
Container Output:                 Host Synology:
/output/                      →   /volume1/organized/
├── tuin/                         ├── tuin/              # Renamed from Camera-Tuin
│   ├── video/                    │   ├── video/
│   │   ├── 2025-09-07_14-30-15-tuin.mp4     │   │   ├── 2025-09-07_14-30-15-tuin.mp4
│   │   └── 2025-09-07_14-32-20-tuin.mp4     │   │   └── 2025-09-07_14-32-20-tuin.mp4
│   └── images/                   │   └── images/
│       ├── 2025-09-07_14-30-15-tuin.jpg     │       ├── 2025-09-07_14-30-15-tuin.jpg
│       └── 2025-09-07_14-30-18-tuin.jpg     │       └── 2025-09-07_14-30-18-tuin.jpg
└── driveway/                     └── driveway/          # Renamed from Camera-Oprit
    ├── video/                        ├── video/
    └── images/                       └── images/
```

## ✨ Features

- 📂 **NFS Integration**: Designed specifically for Synology NAS as NFS storage target
- 🔄 **Automatic Discovery**: Discovers cameras from NFS-mounted directory structure  
- 📹 **Format Conversion**: Converts Hikvision's proprietary format to standard MP4/JPG files
- 🏷️ **Smart Organization**: Creates timestamped filenames with customizable camera tags
- 🗂️ **Surveillance Station Alternative**: Replaces expensive NVR licensing with camera intelligence
- ⏰ **Automated Retention**: Configurable file retention policies (default: 90 days)
- 🔒 **Safe Processing**: File locking prevents concurrent runs and data corruption
- 📊 **Comprehensive Logging**: Detailed progress and error reporting with timestamps
- 🐳 **Container Ready**: No dependencies to install, just run with Docker
- 🎯 **Purpose-built**: Uses the `libhikvision` library optimized for Hikvision storage extraction

## 🏗️ Building from Source

If you want to build your own container:

```bash
git clone https://github.com/dennisbakhuis/synology_hikvision_sync.git
cd synology_hikvision_sync
docker build -t hikvision-sync .
```

## 🧪 Development

### Running Tests
```bash
# Install dependencies
uv sync

# Run full test suite
make test

# Run specific tests
uv run python -m pytest tests/ -v
```

### Local Development
```bash
# Install dependencies
uv sync

# Run locally
uv run python src/process_hikvision_folder.py
```

## 📋 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RUN_MODE` | `cron` | Execution mode: `cron` (continuous) or `once` (single run) |
| `CRON_INTERVAL` | `10` | Minutes between sync runs (1-1440) |
| `RETENTION_DAYS` | `90` | Days to keep files (0 = disabled) |
| `INPUT_DIR` | `/input` | Directory containing camera folders |
| `OUTPUT_DIR` | `/output` | Directory for organized output |
| `CACHE_DIR` | `/tmp/hikvision_cache` | Temporary extraction cache |
| `LOCK_FILE` | `/tmp/process_hikvision_folder.lock` | Lock file location |
| `CAMERA_TRANSLATION` | `""` | Camera name mappings (optional) |

## 🔧 Synology Integration

### Using Docker on Synology
1. Enable Docker package in Package Center
2. Open Docker app and go to Registry
3. Search for container or use command line:

```bash
# SSH into your Synology
ssh admin@your-synology-ip

# Run the container
sudo docker run --rm \
  -v /volume1/your-camera-path:/input \
  -v /volume1/organized-output:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
```

### Persistent Container Setup  
1. **SSH into Synology** and run:
   ```bash
   # Start persistent container with automatic restart
   docker run -d --name hikvision-sync --restart unless-stopped \
     -v /volume3/Camera-Tuin:/input/Camera-Tuin \
     -v /volume3/Camera-Oprit:/input/Camera-Oprit \
     -v /volume3/Camera-Front:/input/Camera-Front \
     -v /volume1/organized:/output \
     -e CRON_INTERVAL=10 \
     -e CAMERA_TRANSLATION="Camera-Tuin:tuin,Camera-Oprit:driveway,Camera-Front:front" \
     ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
   ```

2. **Monitor logs**:
   ```bash
   # View logs
   docker logs hikvision-sync
   
   # Follow logs in real-time  
   docker logs -f hikvision-sync
   ```

### Alternative: One-time Task Setup
If you prefer the old approach using Task Scheduler:
1. **Control Panel** → **Task Scheduler**
2. **Create** → **Scheduled Task** → **User-defined script**  
3. Configure:
   - **General**: Task name: "Camera Sync"
   - **Schedule**: Daily, every 10 minutes
   - **Task Settings**:
   ```bash
   docker run --rm -e RUN_MODE=once \
     -v /volume3/Camera-Tuin:/input/Camera-Tuin \
     -v /volume3/Camera-Oprit:/input/Camera-Oprit \
     -v /volume3/Camera-Front:/input/Camera-Front \
     -v /volume1/organized:/output \
     -e CAMERA_TRANSLATION="Camera-Tuin:tuin,Camera-Oprit:driveway,Camera-Front:front" \
     ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0
   ```

## 🐛 Troubleshooting

### Finding Camera Storage
```bash
# SSH into Synology and locate Hikvision data
find /volume* -name "datadir*" -type d 2>/dev/null
```

### Container Logs
```bash
# Run with verbose logging (one-time)
docker run --rm -e RUN_MODE=once \
  -v /volume3/Camera-Tuin:/input/Camera-Tuin \
  -v /volume3/Camera-Oprit:/input/Camera-Oprit \
  -v /volume1/organized:/output \
  ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0

# Monitor running container logs
docker logs -f hikvision-sync
```

### Common Issues
- **No cameras found**: Check that input directory contains camera folders
- **Permission denied**: Ensure Docker has access to mount paths
- **Extraction failures**: Verify Hikvision data format is supported

## 📈 Container Registry

The container is automatically built and published to:
- `ghcr.io/dennisbakhuis/synology_hikvision_sync:v0.1.0` (current version)
- `ghcr.io/dennisbakhuis/synology_hikvision_sync:latest` (latest stable release)
- Tagged versions for specific releases

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.