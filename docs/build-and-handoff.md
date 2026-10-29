# K80 固件构建与交接

本文记录现有格式 1 设备构建入口；整机结构化记录维护于相邻的 `UniXNU-zorn/porting.toml`。本次整理不重新构建、不启动手机、不改变现有归档。

## 板级包与上游

`uefi-zorn` 只包含 K80 板级包，不是 Mu-Silicium 的完整 fork。`stage-into-mu.sh /path/to/Mu-Silicium` 将平台和配置链接进已有检出，不复制固件，不创建额外 Git 仓库。这些本机链接不要提交到 Mu-Silicium。

依赖包括 Mu-Silicium 的 Common / Silicon / ACPI、EDK II、匹配的 UniXNU / DarwinBoot 组件和现有 giulia SM8650 DXE 二进制输入。DSC 为 `Platforms/Xiaomi/zornPkg/zorn.dsc`，对应 FDF 与内存图必须一起使用。厂商及 Apple 输入按原来源准备，不随本仓库发布。

## 固件构建

从共同父目录执行：

```sh
sh uefi-zorn/scripts/stage-into-mu.sh /path/to/Mu-Silicium
```

在 UniXNU 目录选择设备后，回到共同父目录使用固件入口：

```sh
# 在 UniXNU 目录执行
./unixnu defconfig zorn_defconfig -D ../UniXNU-zorn
```

```sh
# 在共同父目录执行
python3 uefi-zorn/scripts/build-zorn-firmware.py --uefi /path/to/Mu-Silicium
```

构建器核对 AArch64 PE 模块、源码与输出时间、唯一的 ZornBootMemoryDxe，以及 3 MiB FD。清单保存到共同父目录的 `out/zorn/firmware.inputs.json`，并保留按哈希命名的 FD 副本。清单里的 capability 不替代真实设备结果，真机范围仍以绑定运行日志的证据为准。

主 UniXNU 的本地 CLI overlay、完整内核依赖及干净补丁重放限制见相邻设备仓库的 `docs/build-and-debug.md`。仅重建 FD 不代表已经生成完整可用的桌面镜像。

## 负载与镜像

当前实际启动负载为 192 MiB FAT32，簇大小 512 字节，包含菜单、内核、派生 ADT、原版 trust cache 及配置要求的 PackedRAMDisk。打包器清除 mtools 写入的伪分区表，并检查 DarwinBoot sidecar 声明，避免出现菜单找不到或 ADT 残留占位。

原版 trust cache bundle SHA256：`7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7`。Data 配置需要合法 PackedRAMDisk；不能把早期只读基线的 `--no-initrd` 命令直接套到当前 8 GiB 持久 Data 配置。

完整参数由 `UniXNU-zorn/scripts/build-zorn-debug.py` 生成；当前桌面触控组合包含八核、8 GiB 内存、保留 Data、低亮度、触控供电、原版 HID 解析和快采样，见设备仓库 `docs/build-and-debug.md`。单独调用低层 `make-zorn-payload.py` / `package-zorn-boot.py` 不会自动生成统一 ready 清单，不能冒充完整调试构建结果。

启动镜像使用 Android header v4 和 gzip；不带 Android ramdisk、不追加 DTB。小米 ABL 使用现有 vendor_boot 的设备树，本打包器不修改该分区。`dts/zorn-splash.dts` 仅供对照。

BootShim、FD 与 FAT 解压后须适合 `0xA8000000`–`0xB8000000` 的 256 MiB 窗口。XNU 的 8 GiB 窗口从真实 UEFI ConventionalMemory 另行分配；不能将两者或标称 12 GiB 内存混为一谈。

## 交接与自动回收

`ZornBootMemoryDxe` 扫描可用 WB 内存中的 FAT 负载，复制至 BootServicesData 并发布文件系统。负载菜单为 `EFI/UniXNU/unixnu.toml`，倒计时 5 秒，由 DarwinBoot 交接内核。

提前 watchdog 只在 FAT 引导代码区 `0x180` 出现显式 `ZORNGHWD` marker 时启用，普通负载不隐式启用。模式 1 在 UEFI 配置 Gunyah bark / bite，内核接管后由受限日志与观察策略继续控制；模式 2 是 UEFI 停 CPU 的独立测试，不是正常启动模式。已有自动回 recovery 及内核 `WON` 证据，具体复位源和精确超时尚未独立测定。

提前 watchdog 镜像须由固定设备 runner 先准备并读回 recovery BCB。唯一目标 `92988a43` / `zorn` / 槽位 `b`；`f85d4270` 为 CC9，禁止操作。只执行临时 `fastboot boot`；OS / SystemOS 只读，Data、单页日志和 misc BCB 的授权边界由设备仓库维护。禁止启动 Android、flash / erase、改槽或改 GPT。

## 当前验收范围

`42f3d518` 的完整身份见 [桌面触控证据](evidence/touch-desktop-fast-qualified.json)：机主确认进入桌面及单指基本交互，八核检查、保留 Data 标志和亮度读回一起通过，自动回收取得新日志。GPIO 轮询触控、多指未验收、CPU1 前序偶发预检早退、无硬件 GPU 及长期稳定性均仍有边界。

亮度 64 是 XNU 阶段 DCS 控制的读回值，不是校准百分比，也不表示 UEFI 菜单或系统亮度滑块已适配。旧日期阶段文档中的未完成描述只代表当时状态。
