2026-11-17最新280：上游Metal／runtime279与新版公共Turnip已组合为独立K80根／完整内核／启动包。kernel6d129fe3、rootd9856b43、boot29b7bb7d；原FD／BootShim／loader／manager固定输入保持，ADT仅绑定新根摘要。v1传输、源码重放、真实函数体ASan／UBSan、根签名／HFS／独立窗口算术和完整打包检查通过。未安装／启动，无FPS或新硬件资格；11878页／220组根增量审核、本地完整重放及固定安装入口检查已通过；未生成安装admission／claim，系统启动入口尚待准备。原278 ADB5039 preclaim拒绝归档保持，没有bootstrap／重试或新Recovery观察。权威记录：[UniXNU-zorn 280交接](https://github.com/kerrinz/UniXNU-zorn/blob/main/docs/handoff-2026-11-17-k80-ios26-gpu-v280-upstream-stack.md)。仅暂存，无新commit／push。

# K80 iOS26 and retained firmware — 2026-11-17

The companion UniXNU-zorn v261 candidate reached the iOS lockscreen/desktop. The owner confirms swipe,tap,long-press and unlock responses,then a freeze after long-pressing Settings. Both GPU and pure CPU paths have low frame rate;no ranking or measured FPS is claimed. GPU-path stability remains unresolved. This is partial functionality,not full GPU/Metal/display/touch acceptance.

One protected boot returned automatically to verifiedTWRP in333.628seconds with zero retries.39CDC frames/67975bytes and240seconds of silent USB-camera video were saved. Seven protected sample pairs matched and the BCB full-page/tail checks passed. The second native client had3325sampled calls without a sampled Close or process exit;first recorded backend error is method3 BoMap NoResources. The inner resource branch and the later Settings freeze are not yet causally linked. Existing120s CDC polling misses late UI behavior;next driver work is bounded late-window and real mapping diagnostics.

Exact inputs:

- Kernel: `fd74f710a949b40d1f7076e534d2836106aa140bf45e7365fecf718a9c4de90f`.
- Boot image: `0e2b7278b8d5cd54121f11add6a71cf02628d1411620f9e404d2a32b950b7596`.
- Reused FD: `1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`.
- ADT: `98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`.
- Retained installed252 root: `859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`.

The independent candidate changed the kernel payload only. Firmware,launcher,root,Android,Recovery,iPadOS17,Data,GPT and boot partitions retain their recorded scope;this is not a new firmware build or firmware installation. The default format2 iPadOS17 profile and historical inputs remain preserved. [Firmware reuse evidence](evidence/k80-ios26-v261-reused-firmware-2026-11-17.json) records the companion exact result;large raw logs and video remain in the local trial archive.

The authoritative device record belongs to [UniXNU-zorn](https://github.com/kerrinz/UniXNU-zorn). Its catalog fix moves the complete historical ledger out of the oversized root entry,keeps a concise root record below48KiB and adds a completeness guard. The complete published record parses;the official Blob.text ingestion path does not check truncation. Actual official-scanner controls accept complete data and reproduce the EOF error from deliberately truncated historical text. The authenticated API cutoff was not directly captured. This firmware repository does not create a duplicate whole-device porting.toml. See the companion catalog-ingestion note after publication and the [official record guide](https://unixnu.com/zh/porting/records).

Current companion source and results are included in the owner-requested local repository update. Publication of the corrected device revision and a subsequent official catalog scan/deployment are still required for the online page to change. Local commits are created at the owner’s explicit request. This synchronization makes no new phone operation,remote push or official-workflow request.

## v262实机与v263离线修复补记

v262单次无人值守启动约332.78秒自动返回核验TWRP，38帧串口与340秒主机相机采集成功，保护采样一致。真实VM预检捕获4096跨度元数据容量剩余572条、请求847条；已用3524条，共需4371条。之后客户端仍继续调用，不能据此断定最终Settings卡死根因。暗屏录像不作桌面或scanout通过证据，本次无手动／合成输入。

v263在实际K80 Board创建方将CPU跨度元数据容量调至8192，接通既有Domain实际容量观测，保留VM检查、CPU16KiB／GPU4KiB及资源生命周期；32对象／1398输入完整内核和独立启动包离线通过，尚未上机。继续复用原FD与启动器，没有新固件源码／构建／刷写。详见配套UniXNU-zorn的v263交接及精确源码清单；当前仍无完整GPU／Metal／显示／FT3683验收。新增进展暂存，不自动commit或push。

v263后续实机补记：真实运行容量8192生效，但后期剩余47条／请求842条仍被拒绝，扩大容量未解决。单次零重试约332.73秒自动回核验TWRP，38帧／66151字节、340秒录像及7组保护采样通过；210秒相机可见锁屏。最后surface834与fence834匹配，但不是GPU写像素或scanout证明。本次无输入场景，Settings卡死原因与完整验收仍未解决。继续核对固定houji后端容量和实际映射生命周期；FD／启动器继续复用。

v264离线补记：采用固定houji历史源中针对碎片化Metal池的131072条公共VM元数据配置，并新增真实成功map/unmap累计的原子CPU观测；不是复制houji板级参数。K80原VM事务／权限／正常回收／未知DMA保留不变，当前完整内核和启动包离线通过，尚待真机。继续复用FD／启动器，无新固件或存储布局变更。

v264实机补记：确认运行容量131072，38帧／68910字节采样窗口内无容量／后端拒绝，成功map1039／unmap700，说明正常回收确有发生但不证明无泄漏。单次零重试约332.67秒自动回核验TWRP，340秒录像可见锁屏，7组保护采样一致。Settings长按场景仍未实施，完整GPU／Metal／显示／触控验收未完成；当前设备已自动回Recovery，无活动试验。FD／启动器未变化。

v265离线补记：复用固定sheng源的SHOT／BGRX概念，连接实际K80 presenter完成点与原CDC owner；无sheng地址／分区／Linux shell输入。七片共用原38非终端帧并保留终端预算，实际普通帧确认语义保留。完整内核／启动包和源码／主机控制通过，尚未上机；CPU alias读取与完整传输仍需验证。现有1022字节参数／根／FD／启动器保持，无新固件或布局写入。

v265实机补记：31普通＋7图片片／77313字节传回真实48x104CPU framebuffer锁屏图像，boot／CRC／frame64／fence67关联通过；340秒相机采集成功，约332.75秒自动回核验TWRP，保护采样一致。当前设备空闲在Recovery。图像不作GPU写像素或物理scanout证明；Settings／完整GPU／Metal／触控验收未完成。本轮主机视频因版本替换误改使用HEVC，实际记录保留，下一候选恢复H264并加固定编码器检查；FD／启动器仍未改变。

v266离线：既有内核known-image任务／GPU后端不变，新增完成后CPU结果投影，核对真实fence／回读CRC／unmap／引用／taskOOB。完整内核／启动包及当前主机控制通过，尚待实机；仍复用固定FD、ADT、启动器和已安装252只读根。相机266恢复libx264并检查编码器不变量；没有新固件构建或存储变化。

v266实机补记：精确内核2afbaca4／boot5ac95441，已读到初始GPU任务raw0／phase6、真实fence2、CRCe843b26a、unmap／device refs0、table2:2与taskOOB释放。31普通＋7图片片84142字节、340秒H264相机成功，约332.61秒自动回核验TWRP，零重试、7组保护采样一致与BCB尾部／完整读回通过。锁屏截图不是普通Metal像素或物理scanout证明，完整验收仍未完成；无新固件构建、根安装或布局变化。

v267离线：完整内核8c14ac8c／boot749d6ebe／rootf3ad6b7b形成。复用固定FD和启动器，只更改ADT的root digest，与实际编译root头相配；完整原生链接／头依赖通过。独立Metal探针更新共享成员Query／Close断言；三文件根增量46页18组，本地完整重放和重新计算存储位置通过，未安装或启动。无新固件构建或Android／Data／17布局变化。

v267根安装补记：7395页实际既有覆盖／全部46预映像通过，18组46页读回聚合322963fa…，8组保护元数据一致；停留核验TWRP，无系统启动或重试。新首4KiB根页由真实写入读回绑定，独立boot候选继续保留offline状态并另查实际安装收据。

v267实机：Metal device／pipeline／GPU命令与IOSurface CRC718ed2ce通过，两个共享Query／Close成功，120次已知图像呈现及真实exit0。串口frame64／SID4／fence4棋盘与95秒真实相机4×4图案匹配；约332.79秒自动回TWRP、7组boot保护一致。原接收器残留251 ID导致汇总失败，原始字节离线用实际267 ID重解，失败原件保留，未重启补日志。CF采样一直优先能力拒绝记录，逐客户端Close证据仍不齐；268仅修CPU采样调度，无新固件／根变化。

v268离线：kernelbf0bbb45／boot4c88db3b，复用实际267root／ADT／FD／启动器／探针。仅CPU诊断轮询与boot身份变化，Store10264／快照104 ABI保持；32原生重编、1398输入、126关键头和当前受影响sanitizer通过。receiver实际程序ID及真实267报告回归通过，尚未268启动；无新固件／根／布局变化。

v268实机补记：4／4 native客户端CloseReturn成功，Metal CRC718ed2ce、120次呈现及exit0再次通过；串口frame64／SID4／fence4与95秒真实相机棋盘匹配。接收器当前ID验签通过，约332.70秒自动回核验TWRP、7组保护一致。固定FD／启动器／267root／ADT保持，无新固件构建或根写入；跨task、完整GPU桌面和FT3683仍未验收。

269离线：完整kernela36a9879／boote75703bb，实际267root／ADT／FD／启动器保持。新增仅在探针实际退出、4客户端关闭等CPU记录满足时执行的独立Virtual HID有界上滑和场景后串口截图；普通桌面仍CPU策略。当前原生链接／OS26 ABI／sanitizer／串口／113准入拒绝通过，尚未269设备启动；无新固件、根写入或布局变化，不能把合成输入当FT3683验收。

269实机补记：Metal／120呈现／exit0／4关闭再次通过，17合成接触及抬起返回，摄像录像观察到锁屏转入CPU策略桌面。串口只有过渡黑帧，不能代替最终桌面；332.75秒自动回核验TWRP，7组保护一致。原FD／启动器／根保持，无新固件或根写入，GPU桌面／Settings和FT3683物理验收仍未完成。

270离线：kernel57e5c0ac／boot6a147b4a，实际267root／FD／ADT／启动器保持。延迟30秒后用原265 checked sampler截取右上ROI，新增header CRC和保持原201stream的late Pending；原生完整链接／139关键头及当前sanitizer／接收／119准入拒绝通过。尚未270设备启动，无固件构建、根写入或布局变化；CPU策略诊断不等于GPU桌面或FT3683验收。

270实机补记：约332.19秒自动回核验TWRP、零重试、7组保护一致。真实延迟串口ROI清楚显示照片和设置图标，Metal／120呈现／exit0／4关闭再次通过。原接收器在回收后最终JSON因tuple键失败，失败文件／原raw保留；一行主机修复及实际JSON落盘回归通过，独立离线重解，无手机重试。桌面仍CPU策略，GPU桌面／Settings长按／FT物理验收未完成；FD／启动器／实际267根不变，无固件构建或根写入。

271实机：在明确批准的独立25页／9组根策略安装及7423页旧覆盖核对后，另起一次临时启动；原FD／启动器保持，kernel f90ba400／boot efc1d86d／root c60b198d。实际backboardd GPU来源准入、上滑／Settings长按／两次抬起返回，ROI frame265／SID299／fence268见图标减号和完成按钮，符合编辑态响应；332.12秒自动回核验TWRP、7组保护一致、接收器exit0。尚未验证退出编辑态后的继续响应，不能宣称历史卡死解决或完整GPU／FT验收。新根只切换backboardd策略并禁用既有probe，无新固件构建，17／Data／Android／GPT／Recovery保留。

273实机：同一FD／启动器／已安装271根／ADT保持，仅临时内核变化。802ms Settings按住及抬起后实际打开设置列表，尚未确认Liquid Glass菜单；前后完成fence260→263，ROI264为应用过渡浅色帧，相机随后显示列表。332.7633秒自动回核验TWRP、7组保护及BCB读回保持，零重试，无新根安装或固件构建。完整GPU桌面／长按菜单／FT物理验收仍未完成；未把静态列表当后续响应性证明。

274实机：kernel bd8e8eec／boot790b9300，固定FD／启动器／实际271根／ADT保持，无新根写入。1604ms Settings长按及抬起后实际串口／相机捕获圆角菜单；前后fence310→314，20秒延后ROI317。332.7768秒自动回核验TWRP、7组保护及BCB读回一致。尚无菜单出现后的后续点按，不能由静态菜单证明响应或卡死，也未验收Liquid Glass光学效果／完整GPU／FT；无反汇编或逆向。

275实机：kernel5b7668c3／boot716f24c1，原FD／启动器／实际271根／ADT保持。菜单显示后一次菜单外点按及抬起，录像204–208秒菜单、210秒后桌面，串口ROI302无菜单；CPU快照完成fence292→296→299、CF无后端错误／丢失。332.7782秒自动回核验TWRP，7组保护及BCB读回一致，无新根写入／固件构建／布局变化。只证明本次菜单后响应，历史卡死根因、Glass光学效果、应用后续导航、跨task和FT物理验收仍未完成。

277机主协助手动验收：kernelc2ccd636／boot18985374，原FD／ADT／启动器／实际271只读根保持，没有新固件构建或根写入。取消所有合成触摸，机主确认解锁、长按菜单出现／收起及Home返回有响应；设置列表不能滑动但系统仍可回桌面，并非整体卡死。按机主指示设置交互独立待修，GPU主线优先定位低帧率。9次CPU采样fence72..90、ROI93；CF无后端错误／丢失，compact丢失1。一次启动333.4819秒核验回TWRP，7组保护及BCB通过。相机340秒，手机大部分在镜头画外，完整触点身份／边缘、Metal／显示／生命周期／稳定性验收未完成。详见相邻UniXNU-zorn仓库docs/handoff-2026-11-17-k80-ios26-gpu-v277-manual-acceptance.md及匹配observed证据；无新commit／push。

278离线呈现耗时采样：kernel6bb95f1e／boot9d91967e，实际271只读root／FD／ADT／启动器保持，无新固件构建／根写入／布局变化。真实presenter分段CPU时钟计时与9次CPU采样已完成原生完整链接和主机检查。固定入口因已审核私有ADB5039监听不可达在claim前退出：boot0／无claim／无run／无手机命令；相机未见fresh boot而超时，未打开相机。没有278硬件或FPS结果，当前手机Recovery未重新核验，最后实机仍277。未bootstrap或重试。设置交互独立待修；参见相邻UniXNU-zorn的docs/handoff-2026-11-17-k80-ios26-gpu-v278-present-cost.md和精确offline证据。暂存，无新commit／push。

上游core更新：官方UniXNU main630b85a3已取得完整源码／Git树校验并建独立参考仓库，原origin/main同步，原main627c932及K80本地改动／17与26产物保留。新core41项主机测试通过、1项缺lzfse跳过，当前zorn官方记录／收录回归通过。GPU组件新钉点已记录但未初始化／集成；macOS Shader Cache注册修复不直接套入iOS26。详见相邻UniXNU-zorn/docs/upstream-refresh-2026-11-17.md；无新固件／根写入／手机操作／本地commit或push。

279上游用户态集成：精确AdrenoMetal8c7f9502／metal2vulkan46e7cc96＋官方0063已按iOS26 arm64e原生PAC编译并完成Metal bundle链接／签名；K80现有服务适配层重编，真实Mach公开接口和有界VM身份检查通过。保留既有v1 Turnip／固件／FD／启动器，没有新root／kernel／boot构建或安装。公共Mesa更新及硬件性能／完整验收待继续；未执行链接后指令重写、反汇编或逆向。详见相邻UniXNU-zorn/docs/handoff-2026-11-17-k80-ios26-gpu-v279-upstream-runtime.md及匹配offline证据。无手机操作、commit或push。

2026-11-18：配套282内核c8643edc／boot1d29fe20与原FD1bf94507、ADT9aaa913f、281根b87e132b完成一次真机测试。120次已知呈现、CRC718ed2ce、4客户端Close、exit0与严格零丢失判定通过；相机103秒帧显示4×4棋盘格。333.13秒自动返回TWRP，保护/BCB检查通过。未修改或重刷FD；283普通backboardd耗时采样仍为独立离线候选，完整GPU/FT验收未完成。

2026-11-18：专用26根策略22页／11组读回成功，只切换backboardd和禁用探针；283内核未启动。284保留FD／启动器，kernel93511957、boot6d6f4127、ADT5c01b2f6、实际根d9856b43，一次启动333.12秒回TWRP，保护／BCB通过。相机确认锁屏，9份CPU成本记录有效；533次复制／79.969秒包含空闲，不是物理FPS。show约16.02ms／lease约4.24ms，仍需归因；紧凑诊断丢失4保持公开。完整GPU／FT验收未完成，详见相邻仓库docs/progress-2026-11-18-ios26-upstream-gpu.md。


2026-11-18：285／286继续复用FD `1bf94507…`、DarwinBoot `ccae7c1d…` 和管理器 `ff9c6d7e…`，未重编或刷写固件。285根7454页、286根23页仅写专用iOS26根，前后保护／BCB与Recovery通过。两次各一次启动，分别333.20／332.91秒自动回TWRP。285第二份Metal计时报告晚到、仅传出768字节；286提前到20／60秒后完整收到8017字节journal中的两份上游报告，约40秒183次提交到回调累计24.815秒。CPU墙钟包含驱动与调度，不能当作GPU时间、FPS或性能提升；完整GPU／显示／FT验收仍未完成。精确kernel／ADT／根／日志与限制见配套UniXNU-zorn的[最新进展](https://github.com/kerrinz/UniXNU-zorn/blob/main/docs/progress-2026-11-18-ios26-upstream-gpu.md)。

2026-11-18：287／288继续复用原FD、DarwinBoot和管理器，未重编或刷写固件。287计到真实ABI1 IOKit墙钟，288完整内核dfdc82d1／bootacdc3516／根c33f8f56省去四个只读查询的进程页表切换；用户态沿用287实际签名字节。专用26根36页／9组仅更新日志标签，读回／保护／BCB通过。一次无人值守启动332.87秒自动回TWRP，相机锁屏、两份RPC计时完整，初始GPU任务／fence／CPU结果通过；时间戳／状态查询均值8.05／8.75毫秒，不能换算FPS或同负载收益。紧凑观察器丢失7到9保留，完整GPU／显示／FT仍未验收。精确证据见相邻UniXNU-zorn的最新进展；更改暂存，不生成commit或push。

2026-11-18：289内核60c33ec8／bootac852931／根3d59c447优化CPU映射／视图／租约并增加确切进程身份检查，原FD／启动器／用户态字节保持。专用26根仅16页／8组日志标签增量，读回和保护／BCB通过；一次无人值守启动333.13秒回TWRP、相机锁屏、初始GPU任务／fence／CPU结果通过。两份标量与8865B journal完整，但RPC观察器丢3条，严格RPC计时判定保持false；不由此宣称帧率提升。完整GPU／显示／FT仍未验收。没有新固件构建或刷写、commit或push。

2026-11-18：290继续复用原FD／DarwinBoot／管理器，没有固件重编或刷写。内核6b9db0da／boot32c71ce7／根449ce79a采用真实在途Submit上下文保留与重编用户态计数修复；原生PAC Rust保留。专用26根4292页／129组及父页面读回、保护／BCB通过，一次无人值守启动333.24秒回TWRP，相机锁屏，初始GPU任务／fence／CPU结果通过。9005B journal和两份RPC快照完整、零丢失；旧紧凑观察器仍丢8到36，客户端未退出。新构建已知图像／关闭及完整GPU／FT未验收，未据CPU墙钟计数宣称FPS提升。预检误改工具哈希的失败草稿已保留并修正，没有错误工具的手机尝试；未生成commit或push。

2026-11-18补充：291复用原FD／启动器与290用户态，332.80秒自动回TWRP、BCB和保护通过。相机99秒显示4×4绿／紫棋盘，原生四客户端Close记录均成功；但两处诊断过滤器误选backboardd，严格接收器因任务身份不一致拒绝完整验收，探针CRC／exit未被捕获。保留失败与旧紧凑丢失1；292以独立新内核修复过滤器，复用已安装291根，不增加根写入。无新固件构建；完整GPU／FT仍未完成。

292补充：修正探针stderr／journal选择后，严格新构建验收通过：Metal发现／pipeline／GPU绘制、CRC718ed2ce、120次呈现、四客户端Close与exit0，相机99秒显示物理棋盘。332.78秒自动回TWRP，BCB／Android／17／Data／GPT／根边界保护通过。复用291根、290用户态和原FD／ADT／启动器，本轮不增加根写入且无新固件构建。完整3192B journal无缺口，原生事件dropped0；旧stderr摘要容量省略13、旧顺序拒绝2保留。291失败记录不改写。完整桌面／FPS／FT仍待推进；293固定16次Metal绘制探针目前仅离线编译签名。

293 复用原 FD、DarwinBoot 和管理器。独立 iOS26 根安装 33 页，读回及保护检查通过。单次启动在 333.59 秒自动返回 TWRP。相机确认棋盘，16 条固定绘制计时和 CRC 读回完整，旧压缩诊断记录丢失 4 条，严格性能判定未通过。桌面 Liquid Glass 和实际 FPS 待单独验证。

294 使用内核 `846789a9…` 和启动包 `c9c3c995…`。复用 293 已安装根及相同 FD、ADT、DarwinBoot 和管理器。单次启动在 333.84 秒自动返回 TWRP，保护区和 BCB 检查通过。16 次固定 Metal 绘制和读回、物理棋盘、120 次呈现、四次 Close 和 exit0 全部通过，压缩诊断丢失为零。固定负载平均完成时间 35.87 ms。桌面 Liquid Glass 和实际帧率仍待同场验证。
