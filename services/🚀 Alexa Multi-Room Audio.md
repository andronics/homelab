**Stream system-wide audio to synced Echo speakers using PulseAudio & AlexaMRM**

---
## **SOLUTION OVERVIEW**

### Core Components

|Component|Purpose|Key Advantage|
|---|---|---|
|**PulseAudio**|Linux sound server|System-wide audio capture & routing|
|**AlexaMRM**|Python bridge to Amazon MRM protocol|Direct Echo group communication|
|**Virtual Sink**|PulseAudio network endpoint|Audio redirection to Echo devices|

### Why This Solution?

- ✅ **Full System Audio**: Any application/game/browser audio
- ✅ **Perfect Sync**: Uses Amazon's native multi-room protocol
- ✅ **Arch Native**: Uses standard PulseAudio stack
- ✅ **Zero Latency Tweaks**: Configurable for <100ms delay

## **Prerequisites**

1. **Hardware**:
    - Amazon Echo devices (2+ for multi-room)
    - Arch Linux machine (must be on same network as Echos)
2. **Alexa Setup**:
    - Create speaker group in Alexa app:  
        `Devices → + → Combine Speakers → Multi-Room Music Group`
3. **Arch System**:
	```bash
	yay -Syu  # Fully updated system 
	```
    

---

## **📌** Quick Start

```sh
sudo pacman -S pulseaudio pavucontrol python-pip git
git clone https://github.com/danthedeckie/AlexaMRM.git && cd AlexaMRM
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 2. Configure
echo 'load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1;192.168.0.0/16' >> ~/.config/pulse/default.pa
pulseaudio -k && pulseaudio --start

# 3. Stream!
python alexa_mrm.py --group "YOUR_GROUP_NAME"
```

---
## **INSTALLATION & CONFIGURATION**

### 1. Install Dependencies

```sh
sudo pacman -Syu  # Fully updated system  
```

### 2. Configure PulseAudio

Edit PulseAudio config (`~/.config/pulse/default.pa`):

```sh
# Enable critical modules
load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1;192.168.0.0/16
load-module module-zeroconf-publish
load-module module-virtual-sink
```

Restart audio service:
```sh
pulseaudio -k && pulseaudio --start
```

### 3. Set Up AlexaMRM

```sh
git clone https://github.com/danthedeckie/AlexaMRM.git  
cd AlexaMRM  
python -m venv .venv  
source .venv/bin/activate  
pip install -r requirements.txt
```
### 4. Discover Alexa  Groups

```sh
python alexa_mrm.py --discover-groups
# Output: ["Living Room", "Whole House", "ArchCast"] 
```

### 5. Start Streaming

```sh
python alexa_mrm.py --group "ArchCast"  # Use your group name
```

---
## ⚡ **AUDIO ROUTING**

### System-Wide Audio

1. Open `pavucontrol`
2. Go to "Playback" tab
3. Set default sink to **AlexaMRM**

### Per-Application Routing

```sh
# Launch app targeting Echo group
PULSE_SINK=AlexaMRM firefox
```

---
## **ADVANCED CONFIGURATION**

### Reduce Latency

Edit `/etc/pulse/daemon.conf`:

```ini
default-fragments = 2  
default-fragment-size-msec = 5  
resample-method = speex-float-0
```

### Auto-Start Service

Create `~/.config/systemd/user/alexamrm.service`:

```ini
[Unit]  
Description=AlexaMRM Bridge  

[Service]  
ExecStart=/path/to/AlexaMRM/.venv/bin/python /path/to/AlexaMRM/alexa_mrm.py --group "ArchCast"  
Restart=on-failure  

[Install]  
WantedBy=default.target  
```

Enable with:

```sh
systemctl --user enable --now alexamrm  
```



---

## **TROUBLESHOOTING**

### Common Issues & Fixes

|Symptom|Solution|
|---|---|
|**No devices discovered**|`rm -r ~/.config/pulse; pulseaudio -k`|
|**Audio stuttering**|Add `--bitrate 192` to AlexaMRM command|
|**Auth errors**|Re-link Amazon account in Alexa app|
|**PulseAudio module fails**|Check ACL IP range matches your subnet|

### Diagnostic Commands

```sh
# Check active sinks
pacmd list-sinks | grep -e 'name:' -e 'index'

# Monitor AlexaMRM traffic
journalctl --user-unit=alexamrm -f
```
---

## **Alternative Solutions**

### 1. Snapcast + Alexa Bridge

```sh
sudo pacman -S snapcast
git clone https://github.com/nicokaiser/snapcast2alexa
# # Requires separate client devices for bridging
```

_Best for: Dedicated audio server setups_

### 2. Spotify Connect

```sh
yay -S spotifyd  # AUR package
spotifyd --device-name "ArchStreamer"
```

_Best for: Spotify-exclusive streaming_

---
## **Technical Architecture**

```mermaid
graph LR  
A[Linux Applications] --> B[PulseAudio Server]  
B --> C[Virtual Sink]  
C --> D[AlexaMRM Bridge]  
D --> E[Amazon MRM Protocol]  
E --> F[Echo Speaker Group]
```

---

	**Pro Tip**: For ultra-low latency applications (e.g., gaming), combine with [PipeWire](https://wiki.archlinux.org/title/PipeWire) instead of PulseAudio. Performance can reach <50ms latency with proper tuning.

**Final Verification**:

```sh
# Confirm streaming status
python alexa_mrm.py --status
# Output: Streaming to 'ArchCast' at 256kbps
```
