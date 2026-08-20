# CampusClaw 高保真视觉稿 ImageGen Prompts

| 属性 | 值 |
|---|---|
| 生成方式 | Codex 内置 imagegen |
| 用例分类 | `ui-mockup` |
| 最终方向 | v3，Codex-inspired light theme |
| 视觉证据 | 本机 `ChatGPT.app` 26.814.41407 light-theme Token；非公开品牌规范 |
| 日期 | 2026-08-20 |

v1 暖色稿和 v2 钴蓝稿保留为过程制品，不再被主设计文档引用。v3 只借鉴 Codex 的
中性层级、工具型工作台密度和状态表达，保留 CampusClaw 品牌，不复制 OpenAI/Codex
商标、图形或未公开资产。

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
