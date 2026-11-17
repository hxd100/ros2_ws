# ros2_ws — Jetson 小车 ROS 2 工作区（快照备份）

> 环境：Ubuntu 22.04 / **ROS 2 Humble** / JetPack 6.2 (L4T 36.5) / Jetson Orin Nano 8GB
> 快照时间：2026-11-17

本仓库是 `/home/hxd100/ros2_ws/src` 的**完整快照**，用于换机/重装后一键恢复。
`build/`、`install/`、`log/` 不入库（可重新编译生成）。

## 目录结构

```
src/
├── tb6612_car/          # 底盘桥接：串口 <-> ROS 2，里程计、TF、GUI、Nav2 配置
├── my-bot/              # 机器人模型（URDF/Xacro）、Gazebo 仿真、相机 launch
├── lidar_pkg/           # RPLidar A1 驱动（C++，/dev/lidar -> /scan）
└── ros2_astra_camera/   # Orbbec Astra Pro Plus 深度相机驱动（上游快照）
maps/                    # 建图结果（sim_map=仿真, test_map=实车）
configs/roshub/          # ROSHub 项目配置（7 个项目，可一键导入）
```

## 各包说明

| 包 | 来源 | 说明 |
| --- | --- | --- |
| `tb6612_car` | 自建 → [github.com/hxd100/tb6612_car](https://github.com/hxd100/tb6612_car) | 主开发仓库，本仓库为快照 |
| `my-bot` | 自建 → [github.com/hxd100/my-bot](https://github.com/hxd100/my-bot) | 主开发仓库，本仓库为快照 |
| `lidar_pkg` | 自建 | 依赖 udev 规则 `/dev/lidar` |
| `ros2_astra_camera` | 上游 [orbbec/ros2_astra_camera](https://github.com/orbbec/ros2_astra_camera) | 有本地改动（launch/install.sh） |

## 恢复步骤

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws
git clone <本仓库地址> /tmp/wsbak
cp -r /tmp/wsbak/src/* ~/ros2_ws/src/
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build
source install/setup.bash
```

## 硬件与关键参数

| 项 | 值 |
| --- | --- |
| 轮径 | **0.065 m**（半径 0.0325） |
| 轮距 | 0.35 m |
| 编码器 | `ticks_per_meter = 10000`（待实测标定） |
| 串口 | CH340 `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`，115200 8N1 |
| 雷达 | RPLidar A1，`/dev/lidar` → ttyACM0，`/scan` 约 6 Hz |
| 相机 | Orbbec Astra Pro Plus，彩色/深度 30 Hz，深度 0.6–8 m |

## 实车启动

```bash
ros2 launch tb6612_car real_bringup.launch.py          # 全套
ros2 launch tb6612_car real_bringup.launch.py use_chassis:=false  # 只跑传感器
```

## 仿真启动

```bash
ros2 launch my_bot launch_sim.launch.py use_rviz:=false \
  gz_args:="-r -s \$HOME/ros2_ws/install/my_bot/share/my_bot/worlds/empty.world"
```
