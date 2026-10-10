# 统一历史设计验证

版本 1.0.0 · 2026-10-10。[主设计](unified-event-persistence.md)与[源码证据](unified-event-persistence-evidence.md)分别维护目标和事实。

## 制品与检查范围

- 起点为设计仓 origin/main `ec05afd28c766a55df26ad324c8ad0240c568b15`；仅修改统一历史、受影响模块引用、Skill 统计、图源与生成物，不修改产品实现。
- 四仓默认分支重新确认并隔离 fetch；源码结论绑定证据页的完整 SHA/路径/符号，Cron 最新设计沿用 0.31.2 的受理及生命周期边界。
- 新建统一专题三个稳定图块，更新 M03 Child 与 M05 两个图块，共六张有语义变化的图；完整目标图保留入口、应用编排、Factory/运行实例、core 端口、投影与数据库链。
- 对六张图实际查看原尺寸和 840px 文档宽度的白底 PNG；调整全局类图为约 954px 宽纵向布局，并修正关系标签、事务重复路径和调用提交顺序。箭头、文字、分支、返回及取消未决边界可辨认。
- M03 同文件其他六张 SVG 因源行号移动而重新生成；去除 data-source-line 与 plantuml-src 元数据后，与原 SVG 内容一致，没有修改其业务图形。
- `python3 scripts/check-diagrams.py --render`：37 个专题、136 个块、56 张时序图，0 错误；ASCII、无 Mermaid、生成同步、SVG XML、图片及图源块锚检查通过。
- 唯一复杂度提示为既有 managed_session_compaction 的三组条件；其源块及图形语义未改，本任务不合并安全窗口、结果与失败边界来压低数量。
- `python3 scripts/render-diagram-index.py` 更新图索引；修改 Markdown 的本地路径/锚点补充检查和 `git diff --check` 通过。
- SQL 静态核对表名 t_、中文 COMMENT、结果唯一关联、父子来源与 fork 区别、同事务累计及清理缺口；仅是目标片段，不是公司 GaussDB 执行证明。

## 待实现与未运行的验收

没有修改 Java、运行新方案单元/数据库/多实例测试，也没有执行生产 DDL。U1–U5 的原子受理、必达调用/结果提交、并行失败、取消竞争、删除/保留、异常回执、热点累计锁与性能仍待验收。外部业务副作用与本库不能被描述为 exactly-once。

M05 的 from/to、日汇总和保留需求仍待核实；子历史管理端入口尚未完成精确 API 对齐。本设计不借由文档生成或历史测试宣称这些能力已经交付。
