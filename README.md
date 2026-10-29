# uefi-zorn

红米 K80 12 GB + 256 GB（`zorn`，Qualcomm SM8650-AB）的 Mu-Silicium 板级包，用于临时引导 UniXNU / DarwinBoot。目标系统为 iPad7,1 / j120ap 的 iPadOS 17.7.11（21H461）。

**截至 2026-10-29，配合 UniXNU-zorn 已进入桌面，机主确认上滑解锁及图标点按正常。** 八核、8 GiB Data 保留和 XNU 阶段硬件低亮度已有证据；GPU 加速、多指、完整电源管理和长期稳定性尚未完成。当前镜像仍是会自动回 recovery 的调试配置。

## 仓库分工

本项目仅维护 [UniXNU-zorn](https://github.com/kerrinz/UniXNU-zorn) 和 [uefi-zorn](https://github.com/kerrinz/uefi-zorn) 两个设备仓库，不要求额外创建 SoC 或驱动仓库。

本仓库保存固件板级包、BootShim、菜单和打包工具；内核、UFS、Data、触控、八核及亮度实现归 UniXNU-zorn。**本仓库不是完整的 Mu-Silicium 检出**：Common、Silicon、ACPI、上游 BootShim 和共享 UniXNU 组件使用原有上游来源。

## 目录

| 路径 | 用途 |
| --- | --- |
| `BootShim/BootShim.S` | 板级 shim、页对齐与负载邮箱 |
| `Platforms/Xiaomi/zornPkg/` | DSC / FDF、内存图、ZornBootMemoryDxe 与触控供电交接 |
| `Resources/Configs/zorn.toml` | 固件基址和 Android 启动镜像参数 |
| `payload/EFI/UniXNU/unixnu.toml` | 菜单模板；倒计时 5 秒 |
| `scripts/stage-into-mu.sh` | 将板级包链接到现有 Mu-Silicium |
| `scripts/build-zorn-firmware.py` | 构建固件并记录 FD、模块和输入身份 |
| `scripts/make-zorn-payload.py` | 192 MiB FAT32、512 字节簇负载 |
| `scripts/package-zorn-boot.py` | header v4 / gzip 临时启动镜像 |
| `dts/zorn-splash.dts` | splash 区域参考，不追加进当前镜像 |
| `docs/` | 固件构建说明、阶段记录与证据摘录 |

## 移植记录

整机记录集中维护在 [UniXNU-zorn/porting.toml](https://github.com/kerrinz/UniXNU-zorn/blob/main/porting.toml)，使用与 [sheng 设备页](https://unixnu.com/zh/devices/sheng) 相同的区域组织；本仓库保留固件相关说明，不再重复维护一份整机状态表。

- [固件构建与交接](docs/build-and-handoff.md)。
- [桌面触控验收及镜像身份](docs/evidence/touch-desktop-fast-qualified.json)。
- [触控阶段记录](docs/progress-2026-10-29-touch-events.md)、[Data / 八核](docs/progress-2026-10-28-data-smp-touch.md)、[低亮度](docs/progress-2026-10-28-brightness.md)。

结构化记录位于相邻设备仓库的 `porting.toml`；跨仓库网页链接在两仓库提交并发布对应文件后可用。旧阶段文档中的未完成描述保留为历史，不代表当前状态。

## 已验证的固件范围

UEFI 菜单、DarwinBoot 交接、1440 × 3200 GOP、8 GiB XNU 内存窗口及显式提前 watchdog 已有真机结果。FT3683 供电交接为后续内核触控提供前提；桌面触控还依赖 UniXNU-zorn 的 HID、纵轴修正及快采样配置，不能只更新固件就获得相同结果。

| 项目 | 当前配置 |
| --- | --- |
| 固件卷 | 基址 `0xA7100000`；大小 `0x300000` |
| BootShim 解压窗口 | `0xA8000000`–`0xB8000000`，256 MiB |
| 负载邮箱 | `0xA7601000`，`ZORNPLD1` |
| framebuffer | `0xFC400000`；1440 × 3200；每行 5760 字节；32 bpp |
| 启动镜像 | Android header v4、gzip；无附加 DTB、无 Android ramdisk |

192 MiB FAT 负载和后续 XNU 的 8 GiB 窗口是不同分配。240 MiB FAT 曾顶满 shim 解压窗口，不能据内存标称容量直接扩大负载。

## 构建

需要与设备仓库匹配的 UniXNU、Mu-Silicium、工具链、SDK 和厂商 DXE 输入。现有 SM8650 DXE 依赖 Mu-Silicium 的 giulia 二进制输入，固件文件不在本仓库分发。

在三个仓库的共同父目录执行：

```sh
sh uefi-zorn/scripts/stage-into-mu.sh /path/to/Mu-Silicium
```

随后在 UniXNU 检出内选择设备：

```sh
./unixnu defconfig zorn_defconfig -D ../UniXNU-zorn
```

回到共同父目录构建带身份记录的固件：

```sh
python3 uefi-zorn/scripts/build-zorn-firmware.py --uefi /path/to/Mu-Silicium
```

输出为 Mu-Silicium 的 `Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd`，必须为 3 MiB。负载和完整桌面调试镜像由设备仓库统一构建器生成，见 [固件构建说明](docs/build-and-handoff.md)。

说明按格式 2 的区域组织，实际保留格式 1 构建入口。独立源码快照的路径布局对照 `3a8ac966` 已连续两次进入桌面；沿用原已验证 FD，没有重建或刷写固件。历史 ABI 输入和布局依赖仍须处理，见 [构建回归记录](docs/progress-2026-10-29-repro-build.md)。`stage-into-mu.sh` 只建立本机链接，不创建或发布额外仓库。

## 启动与回收

唯一目标为 `92988a43` / `zorn` / 槽位 `b`；`f85d4270` 是 CC9，禁止操作。仅允许定向 `fastboot boot`，不 flash、不 erase、不改槽位或 GPT。当前 userdata 已用于 iPadOS，**不要启动 Android 或重新刷入 userdata**。

使用 UniXNU-zorn 的 `run-zorn-debug.py` 核对 ready 清单、镜像身份并自动回收日志；它会保留手机在 recovery。当前持久写入边界由设备仓库的 Data、日志和 recovery BCB 规则定义，不在此另设写入范围。

## 参考与许可

- [设备仓库与发布](https://unixnu.com/zh/porting/device-repository#publish)、[UEFI 固件集成](https://unixnu.com/zh/porting/uefi-firmware)、[构建指南](https://unixnu.com/zh/building)。
- [UniXNU-zorn](https://github.com/kerrinz/UniXNU-zorn)：整机源码、结构化记录和构建依赖。

本仓库新增文件使用 [BSD-2-Clause-Patent](LICENSE)；上游文件保留各自版权头。IPSW、厂商固件、编译产物和启动镜像不提交到 Git。
