# uefi-zorn

红米 K80（zorn，SM8650-AB）的 Mu-Silicium 板级包。设备仓库是 `UniXNU-zorn`，和本仓库分开发布。

本仓库不是一份完整的 Mu-Silicium。Common、Silicon、ACPI 和上游 BootShim 留在 Mu-Silicium 检出里。`--uefi` 指向链入本板级包之后的那份检出，见 [UEFI 固件](https://unixnu.com/zh/porting/uefi-firmware)。

```
BootShim/BootShim.S                 本机 shim：页对齐，邮箱 0xA7601000
Platforms/Xiaomi/zornPkg/           DSC、FDF、内存图、ZornBootMemoryDxe
Resources/Configs/zorn.toml         固件基址和 Android 启动镜像头
payload/EFI/UniXNU/unixnu.toml      真机菜单读到的配置
scripts/stage-into-mu.sh            把板级包链进 Mu-Silicium
scripts/make-zorn-payload.py        打 192 MiB、512 字节簇的 ZORNESP
scripts/package-zorn-boot.py        打 header v4 的启动镜像
dts/zorn-splash.dts                 参考节点，不打进镜像
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

负载和启动镜像：

```sh
python3 ../uefi-zorn/scripts/make-zorn-payload.py \
  --kernel out/zorn/kernel/kernel.macho \
  --adt out/zorn/kernel.macho.adt \
  --root out/zorn/root.img \
  -o out/zorn/payload.img

python3 ../uefi-zorn/scripts/package-zorn-boot.py \
  --fd /path/to/Mu-Silicium/Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd \
  --ramdisk out/zorn/payload.img \
  -o out/zorn/boot.img
```

`make-zorn-payload.py` 把簇固定成 512 字节，并清掉 mtools 留在引导扇区里的假分区表。EDK2 的 Fat 驱动只接受簇数不少于 65525 的 FAT32。通用 `unixnu build payload` 不处理这两件事，所以实测镜像走上面两条命令。

`root.img` 是从 iPadOS 17.7.11 IPSW 抽出的恢复内存盘，再压成 `DBRDISK1`。它不在本仓库里。菜单里的 `initrd` 仍指向它。内核在登记这张恢复盘之前，先把 `userdata` 上的 OS 容器登记成 `md0`。

启动前用 `fastboot getvar product` 和 `fastboot getvar current-slot` 确认这是 zorn、而且当前槽位仍是原来的 Android 槽。然后只执行 `fastboot boot boot.img`。不要写 `boot`、`super`、`vbmeta`、`vendor_boot`，不要 `erase`，不要改槽位。`userdata` 上的系统卷由 UniXNU-zorn 说明，不要再刷。

## 进度

固件已经在真机上进过菜单。菜单标题是 Redmi K80，配置路径是 `\EFI\UniXNU\unixnu.toml`，倒计时 5 秒，然后把 `Boot XNU` 交给 DarwinBoot。

`ZornBootMemoryDxe` 只扫描 `EFI_MEMORY_WB`。邮箱在 DXE 阶段经常已经不在，驱动就在内核窗口里按 512 字节找 FAT 引导扇区，把整卷复制到 `EfiBootServicesData`，再挂载并打开配置。

内核从菜单之后走到哪里，写在 UniXNU-zorn 的 README。2026-10-26 停在 `MEND`。

## 许可

`Platforms/` 里的上游文件保留各自的版权头。本仓库新增的文件使用 [LICENSE](LICENSE) 的 BSD-2-Clause-Patent。
