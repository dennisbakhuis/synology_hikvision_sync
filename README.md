# Synology Hikvsion Sync Script

Author: Dennis Bakhuis  
Date: 2025-09-05  
License: MIT

This script automates syncing both videos and images from multiple Hikvision cameras' NAS storage to organized destination folders with timestamped filenames. It converts `.pic` files to `.jpg` and organizes files into separate `video/` and `images/` directories.  

Designed for Synology NAS systems, but cross-platform compatible with Linux, macOS, and FreeBSD.

## Quick Start

**The easiest way to use this project:**

1. **Fork this repository** to your own GitHub account
2. **Clone your fork** to your local machine  
3. **Edit the scripts** to match your camera paths and preferences:
   - Update `CAMERAS` array in `src/sync_camera_synology.sh`
   - Configure retention settings in `src/apply_camera_retention.sh`
4. **Test locally** using `make test`
5. **Clone your customized repo directly on your Synology** via SSH:
   ```bash
   ssh admin@your-synology-ip
   cd /volume1
   git clone https://github.com/YOUR_USERNAME/synology_file_sync.git
   chmod +x synology_file_sync/src/*.sh
   ```
6. **Set up scheduled tasks** in DSM Task Scheduler

This approach gives you:
- ✅ **Version control** for your custom configuration  
- ✅ **Easy updates** by pulling from upstream
- ✅ **Backup** of your settings in your GitHub repo
- ✅ **Direct deployment** to Synology without file transfers

## Features
- **Multi-camera support**: Configure multiple cameras with different source/destination paths
- **File types**: Syncs both videos (`.mp4`) and images (`.pic` → `.jpg`)
- **Organization**: Separates files into `video/` and `images/` subdirectories
- **Safety checks**: Age validation, size stability checks, zero-byte file filtering
- **Atomic operations**: Temporary files + atomic moves prevent partial transfers
- **Cross-platform**: Compatible with Linux, macOS, and FreeBSD
- **Logging**: Timestamped actions and progress reporting
- **Locking**: Prevents overlapping executions
- **Timestamped filenames**: Human-readable format `YYYY-MM-DD_HH-MM-SS-<CAM_TAG>.(mp4|jpg)`

## Installation on Synology

### 1. Upload Scripts

**Using Make (Recommended):**
```bash
# Upload both scripts automatically
make install-synology SYNOLOGY_HOST=admin@your-synology-ip

# This will:
# - Create /volume1/scripts/ directory
# - Upload both src/sync_camera_synology.sh and src/apply_camera_retention.sh
# - Set correct executable permissions
```

**Manual Method:**
1. Open **File Station** in DSM
2. Create directory: `/volume1/scripts/` (if it doesn't exist)
3. Upload both scripts to `/volume1/scripts/`
4. Right-click → **Properties** → **Permission** → Check **Executable**

**SSH Method:**
```bash
# Upload scripts and make executable
scp src/sync_camera_synology.sh admin@your-synology-ip:/volume1/scripts/
scp src/apply_camera_retention.sh admin@your-synology-ip:/volume1/scripts/
ssh admin@your-synology-ip
chmod +x /volume1/scripts/sync_camera_synology.sh
chmod +x /volume1/scripts/apply_camera_retention.sh
```

### 2. Configure Cameras
Edit the script to configure your cameras:
```bash
CAMERAS=(
  "/volume3/Camera-Tuin:/volume3/Camera/Tuin:garden"
  "/volume3/Camera-Oprit:/volume3/Camera/Oprit:driveway"
  "/volume3/Camera-Front:/volume3/Camera/Front:front"
)
```

Format: `"source_hikvision_path:destination_clean_path:camera_tag"`

### 3. Set Up Scheduled Task
1. Open **Control Panel** → **Task Scheduler**
2. Click **Create** → **Scheduled Task** → **User-defined script**
3. **General tab**:
   - Task name: `Camera Sync`
   - User: `root` (or admin user)
4. **Schedule tab**:
   - Run on: `Daily`
   - Frequency: `Every 5 minutes`
   - First run time: Current time + 5 minutes
5. **Task Settings tab**:
   - User-defined script: `/volume1/scripts/sync_camera_synology.sh`
   - Send run details by email: ✓ (optional, for debugging)
6. Click **OK**

### 4. Test Manually
```bash
# SSH into your Synology
ssh admin@your-synology-ip

# Test the script
/volume1/scripts/sync_camera_synology.sh

# Check logs in real-time
tail -f /var/log/messages | grep sync_camera
```

## Configuration Examples

### Single Camera Setup
```bash
CAMERAS=(
  "/volume1/Hikvision:/volume1/CleanVideos/BackYard:backyard"
)
```

### Multi-Camera Setup
```bash
CAMERAS=(
  "/volume3/Camera-Garden:/volume3/Organized/Garden:garden"
  "/volume3/Camera-Driveway:/volume3/Organized/Driveway:driveway"
  "/volume3/Camera-Front:/volume3/Organized/Front:front"
  "/volume3/Camera-Side:/volume3/Organized/Side:side"
)
```

## Output Structure
After running, your destination folders will look like:
```
/volume3/Camera/Garden/
├── video/
│   ├── 2025-09-05_14-30-15-garden.mp4
│   ├── 2025-09-05_14-32-20-garden.mp4
│   └── ...
└── images/
    ├── 2025-09-05_14-30-15-garden.jpg
    ├── 2025-09-05_14-30-18-garden.jpg
    └── ...
```

## Troubleshooting

### Find Your Hikvision Storage Location
```bash
# SSH into Synology and find where cameras store files
find /volume* -name "datadir*" -type d 2>/dev/null
find /volume* -name "*.mp4" -o -name "*.pic" 2>/dev/null | head -10
```

### Check Script Logs
```bash
# View system logs for script activity
sudo tail -f /var/log/messages | grep sync_camera

# Check Task Scheduler history in DSM
# Control Panel → Task Scheduler → Select your task → Action → View Result
```

### Common Issues
- **Permission denied**: Ensure script is executable and Task Scheduler runs as `root`
- **Directory not found**: Verify source paths match your Hikvision storage location
- **No files processed**: Check `AGE_SEC` setting (default 120s) - files must be older than this

## Advanced Configuration

### Adjust Processing Delays
```bash
# Only process files older than 300 seconds (5 minutes)
AGE_SEC=300
```

### Add More File Types
```bash
# If your cameras store different image formats
IMAGE_PATTERNS=("*.pic" "*.jpg" "*.jpeg")
```

## File Retention Management

The project includes a companion script `apply_camera_retention.sh` for automatic file retention policy management.

### Features
- **Automatic cleanup**: Deletes files older than specified retention period (default: 90 days)
- **Dry-run mode**: Preview what would be deleted before actual cleanup
- **Size reporting**: Shows freed disk space after cleanup
- **Multi-camera support**: Works with the same camera configuration
- **Cross-platform**: Compatible with Linux, macOS, and FreeBSD
- **Safe execution**: File locking prevents overlapping cleanup runs

### Setup Retention Script

#### 1. Configure Cleanup Script
Edit `apply_camera_retention.sh` to match your camera destinations:
```bash
CAMERAS=(
  "/volume3/Camera/Tuin:garden"
  "/volume3/Camera/Oprit:driveway"
  "/volume3/Camera/Front:front"
)

RETENTION_DAYS=90  # Delete files older than 90 days
DRY_RUN=false     # Set to true for preview mode
```

**Note**: Use only the destination paths from your sync script (not the source paths).

#### 2. Upload and Test
```bash
# Upload retention script
scp src/apply_camera_retention.sh admin@your-synology-ip:/volume1/scripts/
ssh admin@your-synology-ip
chmod +x /volume1/scripts/apply_camera_retention.sh

# Test with dry-run (safe preview)
sed -i 's/DRY_RUN=false/DRY_RUN=true/' /volume1/scripts/apply_camera_retention.sh
/volume1/scripts/apply_camera_retention.sh

# Enable actual retention when ready
sed -i 's/DRY_RUN=true/DRY_RUN=false/' /volume1/scripts/apply_camera_retention.sh
```

#### 3. Schedule Cleanup Task
1. Open **Control Panel** → **Task Scheduler**
2. Click **Create** → **Scheduled Task** → **User-defined script**
3. **General tab**:
   - Task name: `Camera Retention Policy`
   - User: `root`
4. **Schedule tab**:
   - Run on: `Daily`
   - Time: `02:00` (2 AM - low activity time)
5. **Task Settings tab**:
   - User-defined script: `/volume1/scripts/apply_camera_retention.sh`
6. Click **OK**

### Retention Configuration Examples

#### Conservative Retention (6 months)
```bash
RETENTION_DAYS=180
```

#### Aggressive Retention (30 days)
```bash
RETENTION_DAYS=30
```

#### Preview Mode for Testing
```bash
DRY_RUN=true  # Shows what would be deleted without actually deleting
```

### Monitor Cleanup Activity
```bash
# View retention logs
sudo tail -f /var/log/messages | grep apply_camera_retention

# Check Task Scheduler history
# Control Panel → Task Scheduler → Camera Retention Policy → Action → View Result
```

## Testing

The project includes comprehensive testing tools for validating script functionality before deployment.

### Testing Options

#### 1. Bats Framework (Recommended)
**Bats** is the bash equivalent of pytest - a dedicated testing framework for shell scripts.

```bash
# Install Bats on macOS
brew install bats-core

# Install Bats on Linux
git clone https://github.com/bats-core/bats-core.git
cd bats-core
sudo ./install.sh /usr/local

# Run tests
bats tests/test_sync_camera.bats
```

#### 2. Manual Testing with Mock Data
For quick testing without installing frameworks:

```bash
# Generate realistic test data
chmod +x tests/setup_test_data.sh
./tests/setup_test_data.sh

# This creates:
# - Mock Hikvision camera directories with .mp4 and .pic files
# - Files with different ages (some too new, some ready to process)
# - Empty .pic files (should be skipped)
# - Pre-existing cleaned files for retention testing
```

### Test Coverage

The test suite validates:
- ✅ **Script syntax**: Bash syntax validation
- ✅ **Cross-platform compatibility**: stat/date command variations
- ✅ **File age logic**: Only processes files older than AGE_SEC
- ✅ **Size validation**: Skips zero-byte .pic files
- ✅ **Directory creation**: Creates video/ and images/ folders
- ✅ **Error handling**: Graceful handling of missing directories
- ✅ **File locking**: Prevents concurrent execution
- ✅ **Dry-run mode**: Cleanup preview without deletion
- ✅ **Logging format**: Timestamp formatting validation

### Running Tests

#### Using Make (Recommended)
```bash
# Run all tests (syntax + bats tests)
make test

# Run individual test suites
make test-sync          # Sync script tests only
make test-retention     # Retention script tests only
make test-pretty        # Tests with colorized output

# Check syntax without execution
make syntax-check

# Check dependencies
make check-deps
```

#### Manual Testing Commands
```bash
# Validate script syntax (no execution)
bash -n src/sync_camera_synology.sh
bash -n src/apply_camera_retention.sh

# Run individual test suites
bats tests/test_sync_camera.bats
bats tests/test_retention.bats

# Run specific test
bats tests/test_sync_camera.bats -f "cross-platform"
```

#### Manual Testing Workflow

**Using Make:**
```bash
# 1. Create test environment
make test-data

# 2. Edit scripts to use test paths from ./test_data_output/test_config.sh
# 3. Test scripts safely on mock data
# 4. Clean up when done
make clean
```

**Manual approach:**
```bash
# 1. Set up test environment
./tests/setup_test_data.sh ./my_test_data

# 2. Edit scripts to use test data
# Replace CAMERAS array with test paths from my_test_data/test_config.sh

# 3. Test sync script (safe - uses test data)
./src/sync_camera_synology.sh

# 4. Test retention in dry-run mode
DRY_RUN=true ./src/apply_camera_retention.sh

# 5. Clean up test data
rm -rf ./my_test_data
```

### Integration Testing on Synology

Before deploying to production:

```bash
# 1. Test on Synology with real paths but dry-run retention
ssh admin@your-synology-ip
/volume1/scripts/sync_camera_synology.sh  # Run sync once
sed -i 's/DRY_RUN=false/DRY_RUN=true/' /volume1/scripts/apply_camera_retention.sh
/volume1/scripts/apply_camera_retention.sh  # Preview retention policy

# 2. Monitor logs during test
tail -f /var/log/messages | grep -E "(sync_camera|apply_camera_retention)"

# 3. Enable actual retention when satisfied
sed -i 's/DRY_RUN=true/DRY_RUN=false/' /volume1/scripts/apply_camera_retention.sh
```