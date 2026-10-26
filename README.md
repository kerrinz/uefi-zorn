# uefi-zorn

红米 K80（zorn，SM8650-AB）的 Mu-Silicium 板级包。设备仓库是 `UniXNU-zorn`，和本仓库分开发布。

**2026-10-27：UEFI 和 DarwinBoot 交接已完成；整机启动已进入早期用户态，
当前停在原版 AppleImage4 的 `security.mac.img4.ignition_blob` 查询。尚无 iPadOS 桌面。**
本轮按机主要求暂停，手机留在 recovery。见 [暂停快照](docs/progress-2026-10-27.md)。

本仓库不是一份完整的 Mu-Silicium。Common、Silicon、ACPI 和上游 BootShim 留在 Mu-Silicium 检出里。`--uefi` 指向链入本板级包之后的那份检出，见 [UEFI 固件](https://unixnu.com/zh/porting/uefi-firmware)。

现有 SM8650 DXE 依赖 Mu-Silicium 中的 giulia 二进制输入；这些依赖、IPSW、
固件 FD 和启动镜像不随本仓库提交。本次内核调试复用了先前验证过的固件 FD。

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
| 内核窗口 | `0xA8000000`–`0xB8000000`，256 MiB |
| 邮箱 | `0xA7601000`，魔数 `ZORNPLD1` |
| framebuffer | `0xFC400000`，1440×3200，每行 5760 字节，32 bpp |
| GOP | 1440×3200×32 |
| SoC | `SOC_TYPE=2`，SM8650-AB |
| 启动镜像 | header v4，gzip，不附加设备树，镜像内不带 Android ramdisk |

小米 ABL 从机上的 `vendor_boot` 取设备树。打包脚本不改 `vendor_boot`。`dts/zorn-splash.dts` 只记录连续 splash 区域，给对照用。

shim、固件卷和后面的 FAT 解压之后必须落在内核窗口里。240 MiB 的 FAT 把窗口顶满，屏幕是黑的，菜单没有出现。192 MiB 可以进菜单。

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
  --root out/zorn/root.img \
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

`root.img` 是从 iPadOS 17.7.11 IPSW 抽出的恢复内存盘，再压成 `DBRDISK1`。它不在本仓库里。菜单里的 `initrd` 仍指向它。内核在登记这张恢复盘之前，先把 `userdata` 上的 OS 容器登记成 `md0`。

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

最后真机镜像 SHA256 为 `c3673d60b5b04a0ec5f7f28b8971a892fe834b7ff06bb41182f68bffb2299d38`。
完整身份见 [机器可读快照](docs/snapshot-2026-10-27.json)。

## 许可

`Platforms/` 里的上游文件保留各自的版权头。本仓库新增的文件使用 [LICENSE](LICENSE) 的 BSD-2-Clause-Patent。
