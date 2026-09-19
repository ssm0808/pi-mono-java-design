// Navigation and coverage for the shared HTML fixtures. Interaction rules live in scenario Markdown.
window.frontendScenes = [
  {
    "id": "sessions",
    "title": "创建与管理会话",
    "goal": "进入合适的 Agent 会话，并能快速找到、整理已有任务。",
    "frame": "frontend-review.html",
    "view": "chat",
    "states": [
      {
        "id": "ready",
        "label": "管理会话"
      },
      {
        "id": "new",
        "label": "新建会话",
        "frame": "plan-workbench.html",
        "view": "plan"
      }
    ],
    "coverage": "演示新会话空态、选择、置顶与原位改名。搜索、删除、Agent 目录及刷新恢复按设计验收，尚未在该原型完整模拟。",
    "directory": "01-创建与管理会话",
    "doc": "../场景/01-创建与管理会话/README.md"
  },
  {
    "id": "message",
    "title": "发送消息与附件",
    "goal": "提交目标与材料，确认请求是否被接收，并继续编辑后续草稿。",
    "frame": "frontend-review.html",
    "view": "chat",
    "states": [
      {
        "id": "ready",
        "label": "编辑消息"
      },
      {
        "id": "uncertain",
        "label": "提交结果待确认"
      },
      {
        "id": "offline",
        "label": "断线恢复"
      },
      {
        "id": "token-ready",
        "label": "发送前自动刷新",
        "frame": "token-refresh.html",
        "view": "token"
      },
      {
        "id": "token-refreshing",
        "label": "正在更新 Token",
        "frame": "token-refresh.html",
        "view": "token"
      },
      {
        "id": "token-failed",
        "label": "刷新失败 · 草稿保留",
        "frame": "token-refresh.html",
        "view": "token"
      }
    ],
    "coverage": "包含自动更新 Token、成功后提交、失败保留输入和配置变更取消的本地演示；附件仍为示例材料，上传与 READY 绑定需服务实现。",
    "directory": "02-发送消息与附件",
    "doc": "../场景/02-发送消息与附件/README.md"
  },
  {
    "id": "execution",
    "title": "查看执行与停止",
    "goal": "理解当前进展、查看真实工具结果，并在需要时停止任务。",
    "frame": "plan-workbench.html",
    "view": "plan",
    "states": [
      {
        "id": "executing",
        "label": "实施进度"
      },
      {
        "id": "stopped",
        "label": "已停止"
      },
      {
        "id": "offline",
        "label": "断线恢复",
        "frame": "frontend-review.html",
        "view": "chat"
      }
    ],
    "coverage": "可展开活动、推进示例任务、停止并模拟回执和终态。结构化工具 viewer 的深层数据降级由技术验收覆盖。",
    "directory": "03-查看执行与停止",
    "doc": "../场景/03-查看执行与停止/README.md"
  },
  {
    "id": "permission",
    "title": "工具授权",
    "goal": "在操作执行前理解影响范围，明确允许或拒绝本次工具调用。",
    "frame": "frontend-review.html",
    "view": "chat",
    "states": [
      {
        "id": "confirming",
        "label": "等待确认"
      },
      {
        "id": "uncertain",
        "label": "决定结果待确认"
      }
    ],
    "coverage": "模拟允许、拒绝、拒绝原因、回执与结果；真实授权和并发消费由服务端保证。",
    "directory": "04-工具授权",
    "doc": "../场景/04-工具授权/README.md"
  },
  {
    "id": "question",
    "title": "回答问题",
    "goal": "逐题澄清目标与约束，完整提交答案后继续原任务。",
    "frame": "plan-workbench.html",
    "view": "plan",
    "states": [
      {
        "id": "question",
        "label": "Plan 提问"
      },
      {
        "id": "buildQuestion",
        "label": "Build 提问"
      }
    ],
    "coverage": "演示逐题导航、整批校验、已回答摘要、草稿隔离、断线及其他端处理。",
    "directory": "05-回答问题",
    "doc": "../场景/05-回答问题/README.md"
  },
  {
    "id": "plan",
    "title": "审核与修改计划",
    "goal": "检查实施范围、步骤、验证和回退方式，再批准实施或提出修改。",
    "frame": "plan-workbench.html",
    "view": "plan",
    "states": [
      {
        "id": "review",
        "label": "待审核"
      },
      {
        "id": "planIdle",
        "label": "开始规划"
      },
      {
        "id": "research",
        "label": "调研中"
      },
      {
        "id": "recovering",
        "label": "恢复审核"
      },
      {
        "id": "executing",
        "label": "批准后实施"
      }
    ],
    "coverage": "演示复制、修改意见、批准、回执、修订后新方案、实施任务和恢复。",
    "directory": "06-审核与修改计划",
    "doc": "../场景/06-审核与修改计划/README.md"
  },
  {
    "id": "commands",
    "title": "命令与技能",
    "goal": "在当前会话快速发现命令、填写参数，并理解命令结果如何影响任务。",
    "frame": "plan-workbench.html",
    "view": "plan",
    "states": [
      {
        "id": "slash",
        "label": "会话内命令"
      },
      {
        "id": "catalog",
        "label": "完整命令清单",
        "frame": "slash-command-review.html",
        "view": "slash"
      },
      {
        "id": "argument",
        "label": "命令参数",
        "frame": "slash-command-review.html",
        "view": "slash"
      },
      {
        "id": "running",
        "label": "运行中命令",
        "frame": "slash-command-review.html",
        "view": "slash"
      },
      {
        "id": "help",
        "label": "临时结果",
        "frame": "slash-command-review.html",
        "view": "slash"
      }
    ],
    "coverage": "演示清单过滤、标签选择、参数、临时结果及问答/计划期间的可用命令。Skill 的真实执行需要对应 Gateway。",
    "directory": "07-命令与技能",
    "doc": "../场景/07-命令与技能/README.md"
  },
  {
    "id": "settings",
    "title": "开发者设置",
    "goal": "在开发环境配置连接、认证和请求头，理解配置何时生效。",
    "frame": "frontend-review.html",
    "view": "headers",
    "states": [
      {
        "id": "headers",
        "label": "Headers 与认证助手"
      },
      {
        "id": "token-ready",
        "label": "发送前自动刷新",
        "frame": "token-refresh.html",
        "view": "token"
      },
      {
        "id": "token-refreshing",
        "label": "正在更新 Token",
        "frame": "token-refresh.html",
        "view": "token"
      },
      {
        "id": "token-failed",
        "label": "刷新失败 · 草稿保留",
        "frame": "token-refresh.html",
        "view": "token"
      }
    ],
    "coverage": "Header 编辑与手动获取沿用现有原型；自动刷新演示含配置面板、关闭不取消发送、保存配置取消准备。均为本地合成数据，不证明真实认证或完整设置持久化。",
    "directory": "08-开发者设置",
    "doc": "../场景/08-开发者设置/README.md"
  }
];
