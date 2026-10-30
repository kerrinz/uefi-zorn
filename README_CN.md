# uefi-zorn

[English](README.md)

红米 K80（`zorn`，SM8650-AB，12 GB + 256 GB）的 Mu-Silicium 板级包，用于临时引导 UniXNU / DarwinBoot，目标系统为 iPad7,1 / j120ap 的 iPadOS 17.7.11（21H461）。

本仓库负责 K80 固件板级包、BootShim、菜单模板和镜像打包工具，不是完整的 Mu-Silicium 检出。Common、Silicon、ACPI、EDK II 及共享 UniXNU 组件沿用各自上游来源。[UniXNU-zorn](https://github.com/kerrinz/UniXNU-zorn) 负责内核、板级服务和权威的[结构化移植记录](https://github.com/kerrinz/UniXNU-zorn/blob/main/porting.toml)。

官方格式 2 设备文档从设备仓库根目录的 `board.toml` 和 `porting.toml` 生成；本固件仓库不重复发布整机记录。见[发布指南](https://unixnu.com/zh/porting/records#publishing-and-reuse)。

## 当前状态

截至 2026-10-30，组合移植已有机主确认的桌面和基本单指交互，以及八核检查、保留的 8 GiB Data、8 GiB XNU 内存窗口和亮度 64 结果。CPU1 窄页表根发布修正已有同内核对照和两个布局的证据。后续偶发停苹果标志的 GUI 问题仍未解决；最后一次 `c50ca7ea` 观察显示锁屏和全部核心的累计记账进展，随后自动回收。该结果不构成性能、系统多指手势或长期稳定性验收。

固件交接包括 UEFI 菜单、5 秒倒计时、DarwinBoot、GOP 和既有触控供电交接。最新 CPU / 显示观察沿用已记录的 FD；本次更新不代表新固件构建或手机运行。非 GPU 结果及边界已同步到[进度摘要](docs/progress-2026-10-30-non-gpu.md)，GPU 开发进度不在本次更新范围内。

## 前置条件

- 匹配的相邻 `UniXNU/` 和 `UniXNU-zorn/` 检出，使用其记录的源码 / 组件固定版本。
- 已有 Mu-Silicium 源码及所需子模块、匹配的 Xcode / SDK / 工具链，以及已记录的 giulia SM8650 DXE 输入。专有固件不随仓库分发。
- 完整镜像组装还需要匹配的原始 IPSW、trust cache、已准备的 Data / owner 输入和 ABI 审计产物；见 [UniXNU-zorn 构建说明](https://github.com/kerrinz/UniXNU-zorn/blob/main/docs/build-and-debug.md)。

请阅读 [UEFI 集成指南](https://unixnu.com/zh/porting/uefi-firmware)、[设备仓库指南](https://unixnu.com/zh/porting/device-repository)、[AGENTS.md](AGENTS.md)和[固件交接说明](docs/build-and-handoff.md)。

## 构建入口

从各仓库的共同父目录，将本板级包接入已有 Mu-Silicium 树，并使用固件构建器：

```sh
sh uefi-zorn/scripts/stage-into-mu.sh /path/to/Mu-Silicium
python3 uefi-zorn/scripts/build-zorn-firmware.py --help
```

实际构建需要选定保留的旧调试配置；配置步骤及完整命令见 [build-and-handoff.md](docs/build-and-handoff.md)。输出位于 Mu-Silicium 的 `Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd`，大小必须为 3 MiB。上述示例不刷写或启动设备。

UniXNU-zorn 现有格式 2 根配置，并为原调试构建器保留固定兼容配置。主机上的配置 / DTS / 构建树检查，与完整原生构建或真机等价性验收分开。不要用历史运行结果为新迁移的输出路径背书。

## 固件与镜像输入

- FD 基址：`0xA7100000`，大小 `0x300000`。
- BootShim 解压窗口：`0xA8000000`–`0xB8000000`（256 MiB）；负载邮箱：`0xA7601000`，`ZORNPLD1`。
- framebuffer：`0xFC400000`，1440 × 3200，每行 5760 字节，32 bpp。
- 负载：192 MiB FAT32，512 字节簇；Android 启动头 v4 和 gzip，无 Android ramdisk，不追加 DTB。

BootShim 窗口、FAT 分配与 XNU 拥有的内存窗口各自独立。不要依据标称 RAM 容量扩大负载。格式 2 的主机 DTS 不替换当前安装的固件 DTB。

## 目录

- `Platforms/Xiaomi/zornPkg/`：DSC / FDF、内存图、启动内存服务及触控供电交接。
- `BootShim/`、`Resources/Configs/zorn.toml`：板级 shim 与固件 / 镜像参数。
- `payload/EFI/UniXNU/unixnu.toml`：菜单模板。
- `scripts/`：接入、固件构建、负载打包与启动镜像打包。
- `docs/`：交接说明及同步的真机结果摘要。

## 临时启动与回收

使用 UniXNU-zorn 的固定目标 runner，核对匹配的 ready / 输入清单，并保留独立 watchdog。唯一目标为 `92988a43` / `zorn` / 槽位 `b`；`f85d4270` 是 CC9，禁止操作。不刷写、不擦除、不改槽位或 GPT。

禁止启动 Android 或重新安装 userdata。OS / SystemOS 保持只读。Data、单个日志块和 recovery BCB 沿用设备记录的准确边界；固件打包不扩大这些授权。默认 `42f3d518` 和两次桌面确认的 `3a8ac966` 基线均保留。自动工作目前按机主要求暂停。

## 许可

新增文件使用 [BSD-2-Clause-Patent](LICENSE)，上游文件保留各自声明。Apple 输入、厂商二进制和生成的固件 / 启动镜像不提交到本仓库。
