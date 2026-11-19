# K80 iOS 26 固件构建与交接

iOS 26.6.2（23G90）候选绑定精确 FD、DarwinBoot、菜单、ADT、内核和根镜像。设备仓库维护当前组合及实机证据。 [iOS 26 主线](https://github.com/kerrinz/UniXNU-zorn/blob/main/docs/ios26-mainline.md)

## 板级包与构建

`uefi-zorn` 提供 K80 的 DSC／FDF、内存图、BootShim、启动服务、触控供电交接和封装工具。构建使用匹配的 Mu-Silicium 检出及 Common／Silicon／ACPI、EDK II、giulia SM8650 DXE 和 UniXNU 组件。

在独立工作区放置 `uefi-zorn`、`UniXNU-zorn`、`UniXNU` 和 `Mu-Silicium`。准备好的 Mu-Silicium 检出基于 `42fe563791e51bf5500c2e470ed294ca0c94b97c`，叠加 K80 所需的 DSC 调整并保留 giulia DXE 等依赖。固件构建还需要兼容视图锁定的 EDK II `cfb93724a06ff86ff5ba971413368a7809ee42a5`、匹配的 UniXNU／DarwinBoot 源码和 CLANGPDB 工具链。历史检出的本地调整和组件来源以对应 FD 清单为准。

```sh
mu="$PWD/Mu-Silicium"
sh uefi-zorn/scripts/stage-into-mu.sh "$mu"
python3 -B uefi-zorn/scripts/build-zorn-firmware.py --uefi "$mu" \
  --out "$PWD/out/zorn/firmware-review"
```

构建器按固定兼容视图解析板级参数，检查唯一的 AArch64 `ZornBootMemoryDxe` 与 3 MiB FD，并将 `firmware.inputs.json` 写入 `--out` 指定目录。iOS 26 的每个候选绑定自己的 FD 和加载器。v371 重封装使用原 v371 归档中 SHA-256 为 `1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab` 的 FD，配方及构建记录见设备仓库。[UniXNU 固件集成指南](https://unixnu.com/zh/porting/uefi-firmware) · [v371 构建记录](https://github.com/kerrinz/UniXNU-zorn/blob/main/docs/evidence/k80-ft3683-v371-early-smmu-cdc-offline-2026-11-19.json)

## 负载与交接

FD 基址为 `0xA7100000`，大小 `0x300000`。BootShim 解压窗口为 `0xA8000000`–`0xB8000000`，负载邮箱为 `0xA7601000`。固定封装使用 Android boot header v4、gzip 及 FAT32 载体。菜单路径为 `EFI/UniXNU/unixnu.toml`，由 DarwinBoot 加载精确候选的内核和 ADT。

K80 封装把 FAT 追加在 FD 后，再一起压入 Android boot 镜像的 kernel 字段。BootShim 把 FAT 的地址和长度写入邮箱，`ZornBootMemoryDxe` 检查范围和 ZORNESP 标记后发布只读 Block I/O，再由 DiskIoDxe 和 FAT DXE 发布文件系统。设备树仍可用于发现 DRAM 和提供备用 initrd。固件卷由板级 DXE 接管该职责，与官方 `UniXNURamDiskDxe` 的 FDT initrd 集成方式不同。[BootShim](../BootShim/BootShim.S) · [板级 DXE](../Platforms/Xiaomi/zornPkg/Drivers/ZornBootMemoryDxe/ZornBootMemoryDxe.c)

固件记录保持 GOP、PSCI 和触控供电交接来源。使用有界回收时，提前 watchdog 由候选 FAT 中 `0x180` 的 `ZORNGHWD` marker 显式选择。设备 runner 只操作 `92988a43`／`zorn`／slot A，先核验 Recovery、保护区和 BCB 整页再执行。 [当前存储与回收边界](storage-unixnu64.md)

iPadOS 17 GPU 适配已退役。 [历史 OS 适配记录](https://github.com/kerrinz/UniXNU-zorn/blob/main/docs/archived-os.md)
