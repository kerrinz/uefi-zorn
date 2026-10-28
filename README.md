# uefi-zorn

**当前进度（2026-10-28）：已进入 iPadOS 系统锁屏，机主在现场确认；当前优先适配触控。** CPU0 保持，多核及硬件 GPU 后置。尚未验证触摸解锁或桌面操作。

[硬件低亮度](docs/progress-2026-10-28-brightness.md)已通过一次完整锁屏启动，DCS307→64并读回64；[Data](docs/progress-2026-10-28-data-smp-touch.md)首次跨重启读回同一初始化标志。第二次复测被亮度交接保护提前拒绝并自动回 recovery，未到 Data；因此尚不宣称重复启动稳定。现有 overlay 保留。

[触控记录](docs/progress-2026-10-28-touch.md)：真实芯片为 FT3683；首轮只读 XNU 探针证明触控 SE 时钟关闭、GPIO未启用。K80 专属 L14/3.2V 与 L12/1.8V 原生交接已在短测走通，时钟开启、控制器空闲。`bce3bdbe` 已实测读到芯片 ID `3683`、固件 `35`，三条读取均首次 CRC 通过并恢复 GPIO；下一步采集真实触点帧。按[启动与抓日志说明](docs/touch-test-instructions.md)回传结果（提供 Windows PowerShell 命令行包，仅需现有 adb/fastboot，无 Python 依赖）。尚无 HID 或物理触摸成功证据。

红米 K80（zorn，SM8650-AB）的 Mu-Silicium 板级包。设备仓库是 `UniXNU-zorn`，和本仓库分开发布。

**2026-10-27：UEFI 和 DarwinBoot 交接已完成；整机启动已进入原版 launchd 主循环并启动子服务；
已越过原版 AppleImage4 等待，SystemOS 实际只读挂载与 owner 授权通过。
尚无 iPadOS 图形桌面。**
已按机主指令恢复无人值守调试。最新 [GUI 续调记录](docs/progress-2026-10-27-gui.md) 已确认苹果标志和 SpringBoard 退出原因。见 [续调记录](docs/progress-2026-10-27-resumed.md)；
原有 [暂停快照](docs/progress-2026-10-27.md) 仍保留为历史记录。

SystemOS 已通过真实 UFS 块设备和原版存储栈挂载 `/dev/disk1s1`，只读状态、UUID 及 owner 授权通过（`OWNOK`）；原版 launchd 已输出 ptpd[48]、rapportd[56] 启动日志。UEFI 模式 2 停 CPU 测试已自动回 recovery；模式 1 的内核 `WON` 证明接管时 watchdog 已开启。主机 BCB 写入读回也已真机通过。

本轮新增独立 RAM Data 负载：512 MiB 逻辑 APFS、约 1 MiB DBRDISK1 编码，通过 DarwinBoot 的 `PackedRAMDisk` 交接；真机挂载和文件写入、读回、删除已通过。OS/SystemOS 仍是 UFS 只读输入，该历史易失配置已由10月28日受限 overlay 接入替代，最新资格见上文。历史完整记录见 [RAM Data 进度](docs/progress-2026-10-27-ram-data.md)。

本仓库不是一份完整的 Mu-Silicium。Common、Silicon、ACPI 和上游 BootShim 留在 Mu-Silicium 检出里。`--uefi` 指向链入本板级包之后的那份检出，见 [UEFI 固件](https://unixnu.com/zh/porting/uefi-firmware)。

现有 SM8650 DXE 依赖 Mu-Silicium 中的 giulia 二进制输入；这些依赖、IPSW、
固件 FD 和启动镜像不随本仓库提交。前几轮复用旧 FD；新增提前 watchdog 的 FD 已构建，默认无 marker 时该逻辑不启用；模式 1/2 的实际结果见续调记录。

```
BootShim/BootShim.S                 本机 shim：页对齐，邮箱 0xA7601000
Platforms/Xiaomi/zornPkg/           DSC、FDF、内存图、ZornBootMemoryDxe
Resources/Configs/zorn.toml         固件基址和 Android 启动镜像头
payload/EFI/UniXNU/unixnu.toml      真机菜单读到的配置
scripts/stage-into-mu.sh            把板级包链进 Mu-Silicium
scripts/make-zorn-payload.py        打 192 MiB、512 字节簇的 ZORNESP
scripts/package-zorn-boot.py        打 header v4 的启动镜像
dts/zorn-splash.dts                 参考节点，不打进镜像
docs/                              当前整机进度与冻结镜像身份
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

小米 ABL 从机上的 `vendor_boot` 取设备树。打包脚本不改 `vendor_boot`。`dts/zorn-splash.dts` 只记录连续 splash 区域，给对照用。

shim、固件卷和后面的 FAT 解压之后必须落在 BootShim 解压窗口里。240 MiB 的 FAT 把窗口顶满，屏幕是黑的，菜单没有出现。192 MiB 可以进菜单。DarwinBoot 的 XNU 内存另行从真实 UEFI ConventionalMemory 分配；当前 8 GiB 候选位于高地址 DRAM，不等于此 256 MiB 解压窗口。

## 构建

先把板级包链进 Mu-Silicium。链接落在那份检出里，不要提交到 Mu-Silicium。

```sh
scripts/stage-into-mu.sh /path/to/Mu-Silicium
```

然后在 UniXNU 检出里构建固件卷。DSC 是 `Platforms/Xiaomi/zornPkg/zorn.dsc`，输出是 `Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd`，大小必须是 `0x300000`。

```sh
./unixnu defconfig zorn_defconfig -D ../UniXNU-zorn
./unixnu build firmware --uefi /path/to/Mu-Silicium
```

带编译身份记录的本机入口，在三仓库共同父目录执行：

```sh
python3 uefi-zorn/scripts/build-zorn-firmware.py --uefi /path/to/Mu-Silicium
```

它保留 FD 和模块哈希到 `out/zorn/firmware.inputs.json`。提前 watchdog 由 FAT 引导代码区 `0x180` 的显式 `ZORNGHWD` marker 选择；普通负载没有 marker。模式 1 在 UEFI 使用 Gunyah SMC 配置 60/65 秒 bark/bite，内核 UFS 日志就绪后重新配置 45/55 秒；模式 2 为 5/7 秒并主动停 CPU。主机必须先准备并验证 recovery BCB，再启动带 marker 的镜像。模式 2 已实际自动回 recovery、内核日志保持不变；模式 1 后续记录 `WON`。bootreason 为空，具体复位源和精确超时未独立确认。

本机已有补丁工作树的统一构建/打包入口，以下在三仓库的共同父目录运行：

```sh
python3 UniXNU-zorn/scripts/build-zorn-debug.py \
  --incremental-patched-tree \
  --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw \
  --fd ../Mu-Silicium/Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd
```

默认只生成镜像；恢复真机调试时才加 `--boot`。构建失败或输入清单与镜像哈希
不匹配时停止后续启动。当前增量构建成功，全新检出的 XNU 补丁重放仍有冲突；
主 CLI overlay 和前置输入见 `UniXNU-zorn/README.md`，不能把这条命令称为全新克隆一键构建。

下面是已有内核的底层负载/镜像打包命令。它们本身不生成统一构建状态清单；
无人值守流程应使用上面的完整入口，而不是沿用旧的 `boot.inputs.json`。

```sh
python3 UniXNU-zorn/scripts/prepare-zorn-trustcache.py --ipsw iPad_Pro_HFR_17.7.11_21H461_Restore.ipsw
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

原版 trust cache bundle 必须匹配 `7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7`。
打包脚本保留输入 ADT，在副本添加 chosen/memory-map/TrustCache 零占位，并放入
`Payloads/kernel.macho.trustcache`，由现有 DarwinBoot 填入地址。不能漏掉此输入：
旧负载缺少缓存与内核运行时配置时，launchd 被 AMFI/Sandbox 拒绝。

`make-zorn-payload.py` 把簇固定成 512 字节，并清掉 mtools 留在引导扇区里的假分区表。EDK2 的 Fat 驱动只接受簇数不少于 65525 的 FAT32。通用 `unixnu build payload` 不处理这两件事，所以实测镜像走上面两条命令。

`root.img` 是早前使用的 `DBRDISK1` 恢复内存盘。当前验证策略候选省去它，菜单无 `initrd`；派生 ADT 也必须无 RAMDisk/PackedRAMDisk。DarwinBoot 会拒绝只删文件却保留占位的组合，打包器已处理并检查这一点。userdata 上只读 OS 为 `md0`；`md1` 是历史 SystemOS raw 诊断设备，正常 SystemOS 挂载使用真实 UFS IOBlockStorageDevice 发布的 IOMedia。独立 RAM Data 配置会保留合法的 PackedRAMDisk，不能套用只读基线的 --no-initrd。

启动前用 `fastboot -s 92988a43 getvar product` 和 `fastboot -s 92988a43 getvar current-slot` 核对 zorn／槽位 b，再用 `fastboot -s 92988a43 boot out/zorn/boot.img` 临时启动。无人值守调试使用 `python3 UniXNU-zorn/scripts/run-zorn-debug.py`，检查点或独立超时会设置 recovery BCB 并复位，详细范围见设备仓库说明。不要写 `boot`、`super`、`vbmeta`、`vendor_boot`，不要 `erase`，不要改槽位。`userdata` 上的系统卷由 UniXNU-zorn 说明，不要再刷。

## 进度

固件已经在真机上进过菜单。菜单标题是 Redmi K80，配置路径是 `\EFI\UniXNU\unixnu.toml`，倒计时 5 秒，然后把 `Boot XNU` 交给 DarwinBoot。

`ZornBootMemoryDxe` 只扫描 `EFI_MEMORY_WB`。邮箱在 DXE 阶段经常已经不在，驱动就在内核窗口里按 512 字节找 FAT 引导扇区，把整卷复制到 `EfiBootServicesData`，再挂载并打开配置。

2026-10-27 已通过 UFS 只读根、两块原版 trust cache、SIGPASS、INITOK、
PMGR 对象/服务发布、PAN 用户拷贝及第 32 次 EL0 SVC；已采到 PID1 的 libignition 文本。
当前自然停止是 `security.mac.img4.ignition_blob` 的原版处理函数进入后未返回，
独立 watchdog 随后自动进入 recovery。SystemOS 的单独挂载、可写 Data 和图形系统仍待完成。

当前菜单保留 `zorn_pmgr=2`、纯日志、55 秒独立超时与第 64 次 SVC 的诊断参数。
第 64 次检查点尚未命中，不能把自动超时当成检查点通过。UFS 后启用纯日志时
屏幕词不再更新，以 recovery 读回的持久日志为准。

早期暂停快照镜像 SHA256 为 `c3673d60b5b04a0ec5f7f28b8971a892fe834b7ff06bb41182f68bffb2299d38`。
该身份仅对应 [历史快照](docs/snapshot-2026-10-27.json)；当前轮次见 GUI 续调记录和构建清单。

## 许可

`Platforms/` 里的上游文件保留各自的版权头。本仓库新增的文件使用 [LICENSE](LICENSE) 的 BSD-2-Clause-Patent。

`--no-initrd` 会移除派生 chosen 中旧的 `ephemeral-storage` 声明；
独立 RAM Data 负载则同时生成 PackedRAMDisk 和对应临时存储标记。原始 ADT 保持不变。

GUI 诊断候选通过统一构建器的 `--gui-watch` 显式启用，依赖 display-mode 3。
`07ebe68e` 是恢复连接后的早期 GUI 诊断镜像，现已临时启动回收；后续增加固定诊断区。
当前结果见 [GUI 续调记录](docs/progress-2026-10-27-gui.md)，早期 [RAM Data 快照](docs/snapshot-2026-10-27-ram-data.json) 保留为历史身份。


## 临时网络身份对照

`make-zorn-payload.py --development-wifi-identity` 仅在 CPU GUI profile 下，
为 `/chosen/mac-address-wifi0` 提供从专用开发命名空间与 K80 序号派生的稳定本地单播地址。
这不是出厂 MAC 或 Wi-Fi 联网实现。默认关闭；拒绝长度、地址类型错误及现存冲突值。
移除新增属性后应逐字还原控制 ADT。首轮实机结果记入 GUI 续调文档。
