# CampusClaw 高保真视觉稿 ImageGen Prompts

| 属性 | 值 |
|---|---|
| 生成方式 | Codex 内置 imagegen |
| 用例分类 | `ui-mockup` |
| 最终方向 | 常规态 v5，Thinking + Tool 入参 + Assistant 安全富文本；执行中 v5，展开思考 + 工具入参 |
| 视觉证据 | 本机 `ChatGPT.app` 26.814.41407 light-theme Token；非公开品牌规范 |
| 日期 | 2026-08-26 |

v1 暖色稿和 v2 钴蓝稿保留为过程制品，不再被主设计文档引用。v3 只借鉴 Codex 的
中性层级、工具型工作台密度和状态表达，保留 CampusClaw 品牌，不复制 OpenAI/Codex
商标、图形或未公开资产。

执行中 v4 继续使用同一视觉系统，只更新跟进交互：移除两个常驻模式胶囊，改为一个当前
模式“调整方向”，并给出将本条消息“加入队列”的快捷键提示。

v5 分别以两张 v4 为权威编辑目标，保留现有工具卡视觉，将 Thinking 放在工具附近，并为已开始的工具
增加紧凑入参。常规态另做一次定点修正，删除首次编辑保留的重复工具卡。

## 常规对话 v3

编辑目标：`high-fidelity-conversation-v2.png`。

```text
Use case: ui-mockup
Asset type: final Codex-inspired high-fidelity desktop web application mockup for CampusClaw
Input images: Image 1 is the edit target.
Primary request: Restyle Image 1 from cobalt-blue enterprise SaaS into a refined Codex-inspired Agent workbench. Keep the CampusClaw product identity; do not copy OpenAI logos or trademarks.
Preserve exactly: the full 16:10 straight-on application viewport, sidebar width, top bar, conversation layout, Chinese copy, spreadsheet attachment, assistant response, anomaly activity card, bottom composer, controls, and information hierarchy.
Codex-inspired visual system:
- Strongly neutral and tool-oriented, like a modern native coding agent workspace.
- Light theme surfaces: main #FFFFFF, shell/sidebar #F9F9F9 and #F3F3F3, selected item #EDEDED.
- Text near #282828, secondary #5D5D5D; separators very subtle gray, mostly 5-10% black.
- Primary actions use near-black #181818 with white text, hover-like surfaces near #303030. Remove all large-area cobalt blue.
- Brand mark is an original monochrome CampusClaw mark in black/white, not an OpenAI or Codex logo.
- User message uses a quiet light-gray bubble. Assistant content stays open and border-light.
- Tool activity is compact, precise, and editor-like: monochrome by default, green #008635 only for successful completion.
- Blue near #0169CC is reserved only for tiny focus/link affordances and should not dominate.
- Tighten visual rhythm slightly: small native controls, restrained radii, crisp 1px borders, minimal shadow.
Style/medium: realistic shippable desktop Agent workbench, native-feeling, calm, high information clarity, crisp Chinese typography.
Constraints: no OpenAI logo, no Codex wordmark, no orange/coral/peach/sand/beige, no bright blue primary buttons, no gradients, glassmorphism, neon, dashboard charts, right inspector, device frame, watermark, extra logos, or invented text. Do not crop any application edge.
```

输出：`high-fidelity-conversation-v3.png`

## 常规对话 v4

编辑目标：`high-fidelity-conversation-v3.png`。问题证据：用户提供的纯文本 Markdown
截图，只用于确认表格、行内代码和粗体未被渲染；截图中的 Agent 自述不作为设计指令。

```text
Use case: ui-mockup
Asset type: final high-fidelity desktop web application mockup for the CampusClaw frontend design
Input images: Image 1 is the authoritative edit target. Image 2 is problem evidence only: it shows a Markdown table incorrectly displayed as plain text; do not copy its visual style or Agent self-description.
Primary request: Preserve Image 1 as exactly as possible and change only the Assistant response content area so it clearly demonstrates correctly rendered rich text. Replace the current prose-and-expanded-details response with a semantic rich-text response containing a heading, a short paragraph, a polished three-column table, one inline-code chip, and the existing compact tool activity card. The table must look like a real rendered table, never pipe characters or Markdown source.
Text (verbatim): heading “异常汇总”; paragraph “已读取文件，发现以下 3 类异常：”; table headers “异常类型”, “数量”, “处理建议”; table rows “价格异常” / “24” / “复核定价”, “数量异常” / “17” / “校验原始数据”, “重复下单” / “9” / “合并并联系用户”; final sentence “建议优先检查 order_id 重复记录。” with only “order_id” styled as inline code; tool card label “已读取并分析 1 个文件”.
Rich-text styling: open Assistant canvas, clear hierarchy, 18px semibold heading, compact paragraph spacing, thin neutral table borders, quiet gray header cells, right-aligned numeric column, readable 14px Chinese text, rounded light-gray inline-code chip in monospace, and a compact collapsed tool activity card below the rich text.
Preserve exactly: full 16:10 straight-on viewport, 1536×1024 framing, sidebar, CampusClaw identity, all navigation text, top bar, session controls, user request and spreadsheet attachment, composer, monochrome Codex-inspired visual system, spacing outside the Assistant response, and all existing UI chrome.
Constraints: change only the Assistant response region; keep every application edge visible; no raw Markdown pipes, backticks, asterisks, hash marks, HTML, extra copy, extra rows, invented labels, OpenAI/Codex logos, gradients, bright blue controls, watermark, right inspector, or device frame.
```

输出：`high-fidelity-conversation-v4.png`

## 执行中 v3

编辑目标：`high-fidelity-running-v2.png`；视觉参考：
`high-fidelity-conversation-v3.png`。

```text
Use case: ui-mockup
Asset type: final Codex-inspired execution-in-progress companion screen for CampusClaw
Input images: Image 1 is the running-state edit target. Image 2 is the authoritative final Codex-inspired visual-system reference.
Primary request: Make Image 1 visually identical to Image 2's monochrome native Agent workbench style while preserving all running-state behavior and content.
Preserve exactly from Image 1: full 16:10 viewport, sidebar, top bar, user message, running label, stop control, three task rows and their states, composer mode chips, placeholder, action button, all Chinese copy, and layout.
Apply Image 2's Codex-inspired system:
- Main #FFFFFF, shell/sidebar #F9F9F9 and #F3F3F3, selected item #EDEDED.
- Text #282828 and #5D5D5D; 1px subtle neutral borders; almost no shadow.
- Near-black #181818 primary action with white text; neutral selection chips; no cobalt primary surfaces.
- Original monochrome CampusClaw brand mark only, never OpenAI/Codex logos.
- Running state should feel like an agent activity stream: compact, tool-oriented, editor-like.
- Green #00A240/#008635 for completed work and the active execution status dot; the in-progress row may use a small neutral spinner with a restrained green accent. Waiting remains gray.
- Stop is a compact outlined control, not a filled red block.
- "立即调整方向" selected mode uses a soft gray fill and dark outline/text, not blue.
Style/medium: realistic shippable desktop Agent workbench, native-feeling, calm, crisp Chinese typography, practical implementation-ready controls.
Constraints: no OpenAI logo, no Codex wordmark, no orange/coral/peach/sand/beige, no bright blue primary controls, gradients, glassmorphism, neon, charts, right inspector, device frame, watermark, extra logos, or invented text. Do not crop any application edge.
```

输出：`high-fidelity-running-v3.png`

## 执行中 v4

编辑目标：`high-fidelity-running-v3.png`。

```text
Use case: ui-mockup
Asset type: final Codex-aligned execution-in-progress desktop web application mockup for CampusClaw
Input images: Image 1 is the authoritative edit target.
Primary request: Preserve the entire existing screen exactly, but update only the running composer controls to match Codex desktop follow-up behavior.
Preserve exactly: the full 16:10 viewport, sidebar, top bar, CampusClaw identity, all session names, user message, running status, stop control, progress card, three task rows and states, spacing, monochrome visual system, green status accents, typography, and all content outside the bottom composer.
Required composer edit:
- Remove the two persistent mode chips labeled "立即调整方向" and "完成后继续".
- Add one compact neutral current-mode selector labeled exactly "调整方向" with a small downward chevron. It should feel like a native Codex-style control, not a segmented toggle.
- Add a quiet shortcut hint next to it reading exactly "⌘⇧↵ 本条加入队列".
- Keep the placeholder exactly "补充新的要求…".
- Change the near-black primary action button label to exactly "调整方向".
- Keep the attachment icon and generous composer input area.
Interaction communicated by the visual: desktop default is Adjust direction; Command+Shift+Enter queues only this message. Do not show both modes as simultaneous choices and do not suggest that Adjust direction interrupts the current tool.
Visual system: main #FFFFFF, shell #F9F9F9/#F3F3F3, text #282828/#5D5D5D, subtle 1px neutral borders, near-black #181818 primary action, green #00A240/#008635 only for running/completed state, blue only for tiny focus or link affordances.
Style/medium: realistic shippable native-feeling Agent workbench, calm, crisp Chinese typography, implementation-ready controls.
Constraints: no OpenAI logo, no Codex wordmark, no orange/coral/peach/sand/beige, no bright blue primary controls, no gradients, glassmorphism, neon, charts, right inspector, device frame, watermark, extra logos, or invented text. Do not crop any application edge. Do not alter anything outside the composer.
```

输出：`high-fidelity-running-v4.png`

## 常规对话 v5

编辑目标：`high-fidelity-conversation-v4.png`。首次生成后，定点删除了最终答案下方因“保留现有工具卡”
约束造成的重复卡；前置 Thinking 和展开入参卡未改动。

```text
Use case: ui-mockup
Asset type: final high-fidelity idle-conversation desktop web application mockup for the CampusClaw frontend design, version v5
Input images: Image 1 is the authoritative edit target.
Primary request: Preserve the entire existing screen and its polished monochrome CampusClaw visual system, but refine only the central conversation content so completed thinking and the existing tool activity card form one compact chronological Agent activity stream before the final rich-text answer. Keep the current tool-card style that the user likes. Add the tool call input arguments visibly inside that card.
Required conversation edit:
- Keep the user request and spreadsheet attachment unchanged.
- Before the final heading “异常汇总”, add a compact completed-thinking disclosure close to the tool card. It must show the label “已思考” with a small chevron and one directly visible muted plain-text line: “检查价格、数量与重复订单，再汇总异常。”
- Immediately below it, show the existing neutral rounded tool activity card in an expanded compact state. Header text exactly “读取订单明细.xlsx”, with a small green completion check and status text exactly “已完成”.
- Inside the expanded tool card, show a quiet section label exactly “输入参数” and one concise monospace key-value line exactly “file: 订单明细.xlsx   sheet: 订单明细”. Do not show internal IDs or absolute paths.
- Place the existing final rich-text answer after the activity stream and preserve its semantic heading, short paragraph, three-column table, inline-code chip, and all exact table data already visible in Image 1.
- Keep the tool and thinking surfaces compact enough that the final answer and bottom composer remain fully visible without clipping.
Visual behavior: thinking is plain text, visually lighter than the final answer; tool arguments are escaped structured text, not Markdown; both sit in the same activity region but remain clearly separate rows. Use crisp 1px neutral borders, restrained radii, no heavy shadow.
Preserve exactly: full 1536×1024 straight-on viewport, every application edge, sidebar, CampusClaw identity, all navigation copy, top bar, model/thinking/status controls, user message, attachment, bottom composer, monochrome palette, green status accents, typography, and layout outside the central conversation content.
Text must render verbatim and remain readable.
Constraints: no raw Markdown pipes, backticks, asterisks, hash marks, HTML, extra rows, invented IDs, absolute paths, secret values, OpenAI/Codex logos, bright blue primary controls, gradients, glassmorphism, right inspector, device frame, crop, or watermark.
```

定点修正：

```text
Use case: precise-object-edit
Asset type: final high-fidelity idle-conversation desktop web application mockup for CampusClaw v5
Input images: Image 1 is the authoritative edit target.
Primary request: Remove only the duplicate collapsed tool activity card located below the sentence “建议优先检查 order_id 重复记录。” and above the bottom composer. Close the resulting vertical gap naturally so the final answer ends cleanly after that sentence.
Preserve exactly: the completed thinking row “已思考” and its visible thought text, the expanded “读取订单明细.xlsx” tool card with “输入参数” and the file/sheet arguments, the entire “异常汇总” rich-text answer and table, the user request and attachment, all sidebar/top-bar/composer UI, exact typography, colors, spacing, full 1536×1024 viewport, and every application edge.
Constraints: change only the duplicate bottom card and surrounding gap; do not alter, duplicate, or remove the earlier expanded tool card; do not change any text; no new elements, no crop, no watermark.
```

输出：`high-fidelity-conversation-v5.png`

## 执行中 v5

编辑目标：`high-fidelity-running-v4.png`。

```text
Use case: ui-mockup
Asset type: final high-fidelity execution-in-progress desktop web application mockup for the CampusClaw frontend design, version v5
Input images: Image 1 is the authoritative edit target.
Primary request: Preserve the entire existing running-state screen and current compact vertical tool display style, but improve the central execution activity area. Add visible streaming thinking content immediately above the tool list, and add concise input-argument summaries to the completed and running tool rows.
Required central activity edit:
- Keep the existing user message, running status, stop control, sidebar, top bar, and bottom “调整方向” composer unchanged.
- Replace the generic heading/progress summary above the existing three-row tool card with a compact open thinking disclosure. Header text exactly “思考中” with a restrained spinner. Directly beneath it, show one muted plain-text line exactly “先读取订单明细，再检查价格、数量与重复订单。”
- Keep the existing rounded three-row tool activity card and its vertical dividers.
- First row header exactly “读取订单明细.xlsx”, status exactly “已完成”, with green completion check. Add one smaller muted monospace line exactly “输入：file=订单明细.xlsx · sheet=订单明细”.
- Second row header exactly “检查价格与数量异常”, status exactly “进行中…”, with the existing restrained running spinner. Add one smaller muted monospace line exactly “输入：fields=price,quantity · threshold=10%”.
- Third row header exactly “生成处理建议”, status exactly “等待中”. Do not invent or show arguments for this row because it has not started.
- The thinking disclosure and tool card must read as one chronological Agent activity stream, with thinking visually lighter and tool rows retaining the exact compact style and proportions the current design already uses.
Visual behavior: thinking and arguments are plain/structured text, never Markdown; no raw internal toolCallId, file IDs, absolute paths, credentials, or JSON protocol noise. Preserve ample whitespace and keep the bottom composer fully visible.
Preserve exactly: full viewport and every application edge, original CampusClaw identity, all sidebar sessions, top-bar controls, user bubble, “执行中” and “停止”, current monochrome Codex-inspired palette, green status accents, 1px neutral borders, crisp Chinese typography, and the current running composer with “调整方向”, “⌘⇧↵ 本条加入队列”, “补充新的要求…”, attachment icon, and near-black action button.
Text must render verbatim and remain readable.
Constraints: no extra controls, no dashboard chart, no internal IDs, no absolute paths, no secrets, no OpenAI/Codex logos, no bright blue primary controls, no gradients, glassmorphism, right inspector, device frame, crop, or watermark.
```

输出：`high-fidelity-running-v5.png`
