# uefi-zorn

红米 K80（zorn，SM8650-AB）的 Mu-Silicium 板级包。设备仓库是 `UniXNU-zorn`，和本仓库分开发布；内核配置、系统卷和整机适配由设备仓库说明。

本仓库不是一份完整的 Mu-Silicium。Common、Silicon、ACPI 和上游 BootShim 留在 Mu-Silicium 检出里。`--uefi` 指向链入本板级包之后的那份检出，见 [UEFI 固件](https://unixnu.com/zh/porting/uefi-firmware)。现有 SM8650 DXE 依赖其中的 giulia 二进制输入；这些依赖、IPSW、固件 FD 和启动镜像不随本仓库提交。

```text
BootShim/BootShim.S                 本机 shim：页对齐，邮箱 0xA7601000
Platforms/Xiaomi/zornPkg/           DSC、FDF、内存图、ZornBootMemoryDxe
Resources/Configs/zorn.toml         固件基址和 Android 启动镜像头
payload/EFI/UniXNU/unixnu.toml       真机菜单读到的配置
scripts/stage-into-mu.sh            把板级包链进 Mu-Silicium
scripts/build-zorn-firmware.py      构建固件并记录 FD、模块哈希
scripts/make-zorn-payload.py        打 192 MiB、512 字节簇的 ZORNESP
scripts/package-zorn-boot.py        打 header v4 的启动镜像
dts/zorn-splash.dts                 参考节点，不打进镜像
docs/                              整机阶段记录与镜像身份
```

## 地址

`Resources/Configs/zorn.toml` 和打包脚本使用这些值。

| 项 | 值 |
| --- | --- |
| 固件卷 | 基址 `0xA7100000`，大小 `0x300000` |
| BootShim 解压窗口 | `0xA8000000`–`0xB8000000`，256 MiB |
| 邮箱 | `0xA7601000`，魔数 `ZORNPLD1` |
| framebuffer | `0xFC400000`，1440×3200，每行 5760 字节，32 bpp |
| GOP | 1440×3200×32 |
| SoC | `SOC_TYPE=2`，SM8650-AB |
| 启动镜像 | header v4，gzip，不附加设备树，镜像内不带 Android ramdisk |

小米 ABL 从机上的 `vendor_boot` 取设备树，打包脚本不改该分区。`dts/zorn-splash.dts` 只记录连续 splash 区域供对照。

shim、固件卷和后面的 FAT 解压后必须落在 BootShim 解压窗口里。240 MiB 的 FAT 曾顶满窗口而黑屏，192 MiB 可以进入菜单。DarwinBoot 的 XNU 内存另从真实 UEFI ConventionalMemory 分配；8 GiB 高地址 DRAM 候选与此 256 MiB 解压窗口无关。

## 构建

下文按发布后的目录名 `uefi-zorn`、`UniXNU-zorn` 编写。在本仓库目录先把板级包链进 Mu-Silicium，链接不提交到 Mu-Silicium：

```sh
scripts/stage-into-mu.sh /path/to/Mu-Silicium
```

然后在 UniXNU 检出里构建固件卷。DSC 是 `Platforms/Xiaomi/zornPkg/zorn.dsc`，输出为 `Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd`，大小必须是 `0x300000`。

```sh
./unixnu defconfig zorn_defconfig -D ../UniXNU-zorn
./unixnu build firmware --uefi /path/to/Mu-Silicium
```

带编译身份记录的本机入口，在三仓库共同父目录执行：

```sh
python3 uefi-zorn/scripts/build-zorn-firmware.py --uefi /path/to/Mu-Silicium
```

它将 FD 和模块哈希保存到 `out/zorn/firmware.inputs.json`。本机已有补丁工作树的统一构建、打包入口也在共同父目录执行：

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --incremental-patched-tree \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw \
  --fd ../Mu-Silicium/Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd
```

默认只生成镜像，真机试验才加 `--boot`。构建失败或 `ready` 清单与镜像 SHA256 不符时，停止后续 USB 操作。当前增量构建成功，全新检出的 XNU 补丁重放仍有冲突；CLI overlay、源码针和输入要求见设备仓库 README，不能将此命令称为全新克隆一键构建。

下面是已有内核的底层负载、镜像打包命令，在共同父目录执行。它们不生成统一构建状态清单，无人值守应使用完整入口，不能沿用旧 `boot.inputs.json`。

```sh
python3 UniXNU-zorn/scripts/prepare-zorn-trustcache.py \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw
python3 uefi-zorn/scripts/make-zorn-payload.py \
  --kernel UniXNU/out/zorn/kernel/kernel.macho \
  --adt out/zorn/kernel.macho.adt \
  --no-initrd \
  --trust-cache out/zorn/original-trustcache/original-static-system.bundle \
  -o out/zorn/payload.img

python3 uefi-zorn/scripts/package-zorn-boot.py \
  --fd /path/to/Mu-Silicium/Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd \
  --ramdisk out/zorn/payload.img \
  -o out/zorn/boot.img
```

| 负载项 | 值 |
| --- | --- |
| 卷标与大小 | `ZORNESP`，192 MiB FAT32 |
| 簇大小 | 512 字节，清除 mtools 的假分区表 |
| 菜单 | Redmi K80，`\EFI\UniXNU\unixnu.toml`，Boot XNU，倒计时 5 秒 |
| trust cache | 两份原版模块，bundle SHA256 `7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7` |
| 只读根 | userdata OS 容器 `md0`，SystemOS 使用真实 UFS 块设备与 IOMedia/APFS |
| RAM Data | 独立 512 MiB APFS，经合法 PackedRAMDisk 交接；持久 overlay 的资格见进度节 |

EDK2 Fat 驱动要求 FAT32 簇数不少于 65525。通用 `unixnu build payload` 不处理本机的簇大小与假分区表条件，因此实测镜像由本仓库脚本打包。

打包器保留原始 ADT，在副本中添加 chosen/memory-map/TrustCache 占位，并放入 `Payloads/kernel.macho.trustcache`，由 DarwinBoot 填入地址。旧负载缺少 trust cache 与内核运行时配置时，launchd 曾被 AMFI/Sandbox 拒绝，不能漏掉该输入。

历史 `root.img` 是 DBRDISK1 恢复内存盘，当前只读基线不携带它，菜单无 `initrd`，派生 ADT 同时移除 RAMDisk/PackedRAMDisk 和 ephemeral-storage。独立 RAM Data 配置则保留合法 PackedRAMDisk 及临时存储标记，不能直接套用 `--no-initrd`。SystemOS raw `md1` 仅保留为历史诊断，正常挂载使用真实存储栈。

提前 watchdog 由 FAT 引导代码区 `0x180` 的 `ZORNGHWD` marker 显式选择，普通负载不带 marker。模式 1 在 UEFI 配置 60/65 秒 bark/bite，内核 UFS 日志就绪后改为 45/55 秒；模式 2 为 5/7 秒并主动停 CPU。主机必须先准备、读回验证 recovery BCB。模式 2 已自动回 recovery 且内核日志未变；模式 1 记录 `WON`，但具体复位源及精确超时未独立确认。

`--development-wifi-identity` 仅在 CPU GUI profile 下，为 `/chosen/mac-address-wifi0` 提供开发命名空间与 K80 序号派生的稳定本地单播地址。默认关闭，拒绝无效或冲突值，移除新增属性后应还原控制 ADT；它不是出厂 MAC，也未实现 Wi-Fi 联网。

启动前核对固定设备及槽位，只做临时启动：

```sh
fastboot -s 92988a43 getvar product
fastboot -s 92988a43 getvar current-slot
fastboot -s 92988a43 boot out/zorn/boot.img
```

必须确认 product 为 `zorn`、槽位为 `b`。`f85d4270` 是小米 CC9 / pyxis，禁止操作。无人值守使用 `python3 UniXNU-zorn/scripts/run-zorn-debug.py`，由检查点或独立超时回 recovery，核对每轮日志是否更新。不要启动 Android，不写 `boot`、`super`、`vbmeta`、`vendor_boot`，不要 `erase` 或改槽；userdata 系统卷不要再刷。

## 进度

2026-10-28 已进入 iPadOS 系统锁屏，机主已确认。当前优先适配触控，CPU0 保持，多核及硬件 GPU 后置；尚未验证触摸解锁或桌面操作。

| 阶段 | 状态 |
| --- | --- |
| UEFI | 真机菜单工作，1440×3200 framebuffer、5 秒倒计时 |
| 负载 | 192 MiB FAT32 可挂载，内核、ADT、原版 trust cache 和 RAM Data 已交接 |
| DarwinBoot | 已完成内核交接；XNU 高地址 8 GiB 窗口的分配及控制路径通过，整窗压力测试未通过 |
| 存储与根卷 | OS/SystemOS 只读，真实 IOMedia/APFS 挂载、UUID 及 owner 授权通过 `OWNOK` |
| 用户态与显示 | 原版 launchd 主循环、子服务及 CPU 显示路径已到系统锁屏；桌面操作未验证 |
| 自动回收 | UEFI 模式 2、内核模式 1 及主机 BCB 写入读回已有真机证据 |

`ZornBootMemoryDxe` 只扫描 `EFI_MEMORY_WB`。DXE 阶段邮箱可能已不在，驱动就在窗口内按 512 字节寻找 FAT 引导扇区，复制整卷到 `EfiBootServicesData` 后挂载并打开配置。

| 功能 | 状态 |
| --- | --- |
| 亮度 | [低亮度交接](docs/progress-2026-10-28-brightness.md)为 DCS 307 → 64，读回 64，一次完整锁屏启动通过 |
| Data | [受限持久 overlay](docs/progress-2026-10-28-data-smp-touch.md)首次跨启动读回同一初始化标志；第二次在亮度保护处提前回 recovery，未到 Data，重复启动稳定性未证明 |
| CPU | 仅 CPU0，多核未适配 |
| 触控 | FT3683 芯片 ID 和固件读取通过，真实触点与 HID 尚未验证 |
| GPU 及其他外设 | 硬件 GPU、网络、音频等尚未完成 |

[触控记录](docs/progress-2026-10-28-touch.md)说明 K80 专属 L14 / 3.2 V、L12 / 1.8 V 交接与时钟已短测走通；`bce3bdbe` 读到 ID `3683`、固件 `35`，三条读取均首次 CRC 通过并恢复 GPIO。下一步采集真实触点帧。[启动与抓日志说明](docs/touch-test-instructions.md)提供仅依赖 adb/fastboot 的 Windows PowerShell 命令行包。

早期 512 MiB 易失 RAM Data 已通过挂载、文件写入、读回与删除；当前已接入受限 overlay，不能用历史易失测试证明重复启动稳定。OS/SystemOS 始终只读，新增持久写入仅限设备仓库说明的独立 Data 窗口、既有 4 KiB 日志块和保留尾部并读回验证的 misc recovery BCB。

整机镜像身份、显示及内核证据见 [GUI 续调记录](docs/progress-2026-10-27-gui.md)和 [续调记录](docs/progress-2026-10-27-resumed.md)。[早期暂停记录](docs/progress-2026-10-27.md)、[暂停快照](docs/snapshot-2026-10-27.json)与 [RAM Data 快照](docs/snapshot-2026-10-27-ram-data.json)只对应历史轮次；当时的 AppleImage4 等待等阻塞已越过，不能当作当前卡点。

## 许可

`Platforms/` 里的上游文件保留各自的版权头。本仓库新增文件使用 [BSD-2-Clause-Patent](LICENSE)。
