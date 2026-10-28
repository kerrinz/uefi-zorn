# zorn 固件：2026-10-27 恢复调试

按机主新指令恢复无人值守内存启动，固定目标 `92988a43` / zorn / 槽位 b。
历史暂停快照保留。前几轮使用已验证 FD：
`702bc1dba9890aa5d72f5bb377f8d86dd9c80f7726f6aa4319c1d73083f5b138`。

内核侧已在真机定位原版 AppleImage4 无限等待 `IOAESAccelerator`。
接入上游 SoftwareAES 并完成 181 个 ABI 槽位的前后校验后，libignition
继续解析启动参数，第 64 次 EL0 SVC 检查点主动回收成功。
对应镜像为 `0b886dcd932f5c3d26c5b532162312a92f4a034bca72e93bf56947f621f3d346`。

菜单保持 5 秒，`zorn_checkpoint=NOHIT`，内核 watchdog 为 55 秒 bite。
自然运行已定位 dyld 缺少 `libSystem.B.dylib` / dyld cache。SystemOS 只读
`md1` 发布及首块/只读/越界检查通过后，现已接通真实存储栈并挂载 SystemOS，
owner 路径在 `OWNOK` 主动回收成功；完整缓存映射仍未获证明。
长轮次 `20261027-100050-478cdb22` 已取得原版 launchd 主循环生成的
ptpd[48] 和 rapportd[56] 服务日志。可写 Data、XNU 显示服务和桌面仍未完成。

移除恢复盘后，一份负载遗漏 RAMDisk ADT 占位清理，触发 DarwinBoot 明确的
拒绝条件，180 秒内未回 recovery。打包器已修正并检查实际 FAT 中的 ADT。
这次未回收不能算作新 owner 验证/挂载函数的运行时结果。

为覆盖 UFS 就绪前的失败，已编译新的显式 UEFI watchdog FD：
`2a43a7994a264a37022d9639eebcc2977a538e376f2f9a44f24be9a12c9e2a2b`。
仅 FAT 引导代码区的 `ZORNGHWD` marker 启用此路径；普通负载无 marker。
模式 1 为 60/65 秒 bark/bite，模式 2 为 5/7 秒并停 CPU。主机先准备并
验证 recovery BCB。机主物理回 fastboot 后，模式 2 的独立停止试验
已自动回 recovery，内核日志未变化；后续模式 1 内核记录 `WON`。
bootreason 为空，不能据此断言具体复位源和精确 bite 时长。
主机 BCB 的 4096 字节页写入与尾部保留已在真机逐字节读回验证。

随后 OS/SystemOS owner 签名和区块验证通过，OS 根卷身份授权通过；
原版 APFS 日志将失败先定位为 fsindex -1，继而是缺少 IOKit 卷节点。
接入真实只读 IOBlockStorageDevice 和原版存储栈后，运行
`20261027-094852-4997cc98` 已挂载 `/dev/disk1s1`，UUID/只读/owner 授权
到达阶段 6、错误 0、授权 1（`OWNOK`）。该轮成功后主动回收；现已恢复
自然运行以验证缓存。设备仓库同名续调记录保存详细证据。

新候选省去恢复盘，也删除派生 ADT 的 RAMDisk/PackedRAMDisk，占位非零则
拒绝；保留 trust cache 占位。加入验证表后仍使用 192 MiB FAT，启动镜像
约 77 MiB。各自构建身份见 [续调快照](snapshot-2026-10-27-resumed.json)。

系统卷只读，诊断写入仍
限于既有日志块与 recovery BCB；不刷 boot/super/vbmeta/vendor_boot，不改槽位。

最新轮次 `20261027-102912-28793d46` 在派生 ADT 中移除了无 RAMDisk 时
残留的 ephemeral-storage，保留原始输入。`system` domain 已生成 logd
的 xpcproxy（65）和 distnoted 的 xpcproxy（66）；19 条完整用户输出已取回。
这仍不是图形桌面。当前默认镜像 SHA256 为
`28793d4656c2a0126c1f6fe98f391dd09b2622f8e6d59797eaf41bdb938bc059`，
主机回收等待 300 秒；签名进度 pet 只在前 120 秒内、已认证 chunk 完成后允许。
