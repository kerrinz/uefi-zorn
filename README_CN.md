# uefi-zorn

[English](README.md)

红米 K80（`zorn`，SM8650-AB，12 GB + 256 GB）的 Mu-Silicium 板级包。**iOS 26.6.2（23G90）是当前 UniXNU 主线。** 已退役的 iPadOS 17 GPU 适配见设备仓库的[历史 OS 适配记录](https://github.com/kerrinz/UniXNU-zorn/blob/main/docs/archived-os.md)。

本仓库维护板级固件、BootShim、启动菜单和镜像封装。构建使用已有的 Mu-Silicium 检出及其 Common、Silicon、ACPI、EDK II 输入。[UniXNU-zorn](https://github.com/kerrinz/UniXNU-zorn) 维护内核、设备驱动、精确构建证据和[整机适配记录](https://github.com/kerrinz/UniXNU-zorn/blob/main/porting.toml)。

## 构建与交接

按[固件构建与交接指南](docs/build-and-handoff.md)在独立 Mu-Silicium 工作区准备固定输入并构建。指南记录 BootShim 邮箱和 `ZornBootMemoryDxe` 发布的只读 Block I/O。iOS 26 实机试验绑定对应候选的 FD、加载器、ADT、菜单和根镜像。

- `Platforms/Xiaomi/zornPkg/` 存放 DSC／FDF、内存图、启动内存服务和触控供电交接。
- `BootShim/` 与 `Resources/Configs/zorn.toml` 存放 shim 和镜像参数。
- `payload/` 存放菜单模板与存储描述，`scripts/` 存放准备和封装工具。

实机启动由固定 runner 从已核验的 Recovery 操作 `92988a43`／`zorn`／slot A，并启用独立看门狗，遵循 Android 和 Data 保护边界。 [存储与回收边界](docs/storage-unixnu64.md)

新增固件代码使用 [BSD-2-Clause-Patent](LICENSE)。厂商二进制和生成镜像留在本地工作区。
