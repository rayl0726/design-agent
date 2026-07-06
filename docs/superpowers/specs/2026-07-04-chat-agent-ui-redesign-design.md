# 设计文档：对话式 Agent UI 与会话管理改造

## 1. 背景与目标

当前前端采用表单创建项目 + Tab 页展示 L1/L2/L3 的交互模式。为强化"Agent"属性，提升用户迭代沟通体验，计划将前端改造为**对话式交互界面**：

- 左侧：会话历史列表
- 右侧：连续对话流
- AI 以消息卡片形式回复 L1/L2/L3 内容
- 用户在底部输入框持续沟通

同时新增**会话隔离与历史记录保存**，由 Java 后端统一维护会话消息和状态。

## 2. 核心交互流程

### 2.1 新建会话

用户点击"新建对话"后进入空白对话页。AI 主动发送开场白：

> 你好，我是你的美陈设计助手。请告诉我：
> 1. 项目主题（如：夏日海洋、新春国潮）
> 2. 空间类型（购物中心 / 百货 / 快闪店 / 展厅等）
> 3. 预算区间
> 4. 目标人群
> 5. 涉及哪些点位？（中庭、门头、DP点、座椅、灯饰画、连廊、立柱、橱窗等）每个点位各需要几个？

用户以自然语言回复，AI 通过 `input_parser` 提取结构化需求。若信息缺失，AI 继续追问。

### 2.2 前置信息收集完成

当主题、空间、预算、点位等关键信息确认后，AI 发送摘要卡片：

```
已确认需求：
- 主题：夏日海洋
- 空间：购物中心
- 点位：中庭×1、门头×2、DP点×3
- 预算：15万
是否基于以上信息生成 10 个创意方向？
[生成创意]
```

### 2.3 L1 创意生成

用户确认后，AI 调用后端生成 10 个创意方向，以**创意卡片网格**形式展示在对话流中：

每张卡片包含：
- 创意标题
- 设计主题
- 设计风格
- 适用点位分布
- 配色方案（色块 + HEX）
- 一句话创意总结
- 操作按钮："基于这个创意继续" / "收藏" / "驳回"

AI 在卡片组下方追加询问：

> 已生成 10 个创意方向，点击任意卡片可进入 L2 视觉方案生成；或告诉我调整方向重新生成。

### 2.4 L2 视觉方案生成

默认行为：仅给**用户选中的 1 个创意**出图。

每个创意包含多个点位，每个点位生成 **5 张现场效果图**：正、左、右、顶、底视图。

展示形式：**创意描述 + 多点位标签页 + 每个点位 5 张图轮播**。

可选行为：用户输入"把 10 个创意都出图"后，批量为所有创意生成对应点位图。

AI 在 L2 结果下方询问：

> 视觉方案已生成，是否继续生成 L3 可落地方案？
> [生成 L3] [调整创意] [重新生成 L2]

### 2.5 L3 落地方案生成

L3 输出为完整方案文档：

- 把 L1 创意描述 + L2 现场图进行排版
- 增加每个点位的材料、尺寸、价格说明
- 输出 **PPT** 和 **HTML** 两种格式
- 提供下载按钮

## 3. 前端设计

### 3.1 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  美陈设计 Agent                                   [新建对话]  │
├───────────────┬─────────────────────────────────────────────┤
│               │                                             │
│  会话列表      │          对话消息流                          │
│  ─────────    │                                             │
│  会话 1        │   用户：我要做一个夏日海洋主题方案...          │
│  会话 2        │                                             │
│  会话 3        │   AI：已确认需求...                           │
│               │                                             │
│               │   用户：确认生成 10 个创意                     │
│               │                                             │
│               │   AI：[10 张创意卡片]                         │
│               │                                             │
│               │   用户：基于第 3 个出图                        │
│               │                                             │
│               │   AI：[L2 多点位效果图]                        │
│               │                                             │
├───────────────┴─────────────────────────────────────────────┤
│  [输入框] [发送] [上传资料]                                   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 关键组件

| 组件 | 说明 |
|------|------|
| `ChatLayout` | 三栏布局：顶部 header、左侧会话列表、中间对话区、底部输入区 |
| `MessageList` | 消息滚动容器，支持用户/AI 消息气泡 |
| `UserMessage` | 用户文本消息 |
| `AiMessage` | AI 文本/卡片消息容器 |
| `RequirementSummaryCard` | 需求确认摘要卡片 |
| `CreativeIdeasGallery` | 10 个创意卡片网格 |
| `CreativeIdeaCard` | 单个创意卡片 |
| `VisualSchemePanel` | L2 视觉方案：点位标签 + 5 张图轮播 |
| `FinalProposalCard` | L3 方案文档下载卡片 |
| `ChatInput` | 底部输入框 + 发送 + 上传 |
| `SessionSidebar` | 左侧会话列表，支持新建、重命名、删除 |

### 3.3 视觉风格建议

- 整体采用简洁现代风格，主色可用深蓝/暖灰
- 用户消息靠右，浅色背景
- AI 消息靠左，白色卡片 + 轻微阴影
- 创意卡片使用圆角、hover 上浮效果
- 图片使用统一比例（16:9）和圆角
- 生成中使用 skeleton/loading 状态

## 4. 后端设计（Java）

### 4.1 数据模型

复用现有 `java_projects` 表作为会话容器，新增 `session_messages` 表存储消息历史。

#### Project 表扩展

```java
@Entity
@Table(name = "java_projects")
public class Project {
    // 已有字段...

    // 当前阶段
    @Column(length = 20)
    private String currentStage; // INIT / REQUIREMENT / L1 / L2 / L3

    // 选中的创意索引（用于 L2/L3）
    private Integer selectedIdeaIndex;

    // 已解析的需求 JSON
    @Column(columnDefinition = "TEXT")
    private String requirementJson;
}
```

#### SessionMessage 表

```java
@Entity
@Table(name = "session_messages")
public class SessionMessage {
    @Id
    @Column(length = 36)
    private String id;

    @ManyToOne
    @JoinColumn(name = "project_id")
    private Project project;

    // user / assistant / system
    @Column(length = 20)
    private String role;

    // text / idea_gallery / visual_scheme / proposal / summary
    @Column(length = 30)
    private String messageType;

    // 文本内容或 JSON 字符串
    @Column(columnDefinition = "LONGTEXT")
    private String content;

    @CreationTimestamp
    private LocalDateTime createdAt;
}
```

### 4.2 API 设计

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/sessions` | 新建会话 | 返回 sessionId |
| `GET /api/v1/sessions` | 会话列表 | 按时间倒序 |
| `GET /api/v1/sessions/{id}/messages` | 获取会话消息 | 含 L1/L2/L3 数据 |
| `POST /api/v1/sessions/{id}/messages` | 发送用户消息 | 触发 AI 回复 |
| `POST /api/v1/sessions/{id}/actions/select-idea` | 选择创意 | 传入 ideaIndex |
| `POST /api/v1/sessions/{id}/actions/generate-l2` | 生成 L2 | 基于选中创意 |
| `POST /api/v1/sessions/{id}/actions/generate-l3` | 生成 L3 | 基于 L1+L2 |
| `POST /api/v1/sessions/{id}/actions/regenerate-l1` | 重新生成 L1 | 附带反馈 |

### 4.3 会话状态机

```
INIT → REQUIREMENT → L1_PENDING → L1_CONFIRMED → L2_PENDING → L2_CONFIRMED → L3_DONE
```

每个状态转换由用户操作触发，后端持久化到 `Project` 表。

## 5. Python agent-core 调整

### 5.1 Input Parser

增强意图识别，支持从对话中提取：

- 主题、风格、预算、空间类型
- 点位清单及数量
- 用户反馈（重新生成、调整方向、选第几个）

输出结构化 `Requirement` 对象：

```json
{
  "theme": "夏日海洋",
  "style": "现代简约",
  "budget": "15万",
  "space_type": "购物中心",
  "target_audience": "年轻家庭",
  "locations": [
    {"type": "中庭", "count": 1},
    {"type": "门头", "count": 2},
    {"type": "DP点", "count": 3}
  ],
  "extra_requirements": "..."
}
```

### 5.2 Concept Designer（L1）

每个创意需包含多点位规划：

```json
{
  "title": "方案标题",
  "story": "设计故事",
  "concept": "核心概念",
  "style": "设计风格",
  "color_palette": [...],
  "locations": [
    {
      "type": "中庭",
      "count": 1,
      "description": "该点位如何布置",
      "keywords": [...]
    }
  ]
}
```

### 5.3 Visual Designer（L2）

为每个点位的每个创意生成 5 张现场图：

- Prompt 模板：
  ```
  A commercial display installation in a shopping mall atrium,
  [theme] theme, [style] style, front view,
  realistic on-site rendering, shoppers in background,
  professional photography, 4K
  ```
- 视角：front / left / right / top / bottom
- 默认生成选中创意的全部点位图
- 可选批量生成所有创意

### 5.4 Technical Designer（L3）

L3 输出调整为方案文档：

- 整合 L1 创意描述
- 整合 L2 现场图
- 补充每个点位的材料、尺寸、价格
- 调用 `doc_generator` 生成 PPT 和 HTML

## 6. 图片生成策略

当前图片生成链路：Pollinations（免费）→ ComfyUI（本地）→ Placeholder。

建议新增智谱 CogView-3 Provider：

- 使用同一个智谱 API Key
- 生成质量和中文理解优于 Pollinations
- 新用户有免费额度

图片生成 Provider 优先级：

```text
智谱 CogView-3 → Pollinations → ComfyUI → Placeholder
```

## 7. 实施阶段建议

考虑到改动范围较大，建议分阶段实施：

### 阶段 1：前端对话框架
- 新建 `ChatView.vue` 替换现有详情页
- 左侧会话列表 + 右侧消息流 + 底部输入框
- 消息历史从后端读取

### 阶段 2：Java 后端会话层
- 新增 `SessionMessage` 实体和 Repository
- 扩展 `Project` 表字段
- 新增消息相关 API

### 阶段 3：L1 创意卡片展示
- 前端创意卡片网格组件
- 后端返回 10 个创意 JSON
- 用户点击卡片后进入 L2

### 阶段 4：L2 多点位多视角出图
- 修改 `concept_designer` 输出多点位规划
- 修改 `visual_designer` 生成 5 视图现场图
- 前端多点位标签页 + 图片轮播

### 阶段 5：L3 PPT/HTML 输出
- 修改 `technical_designer` 输出排版文档
- 对接 `doc_generator` 生成 PPT/HTML
- 前端提供下载按钮

## 8. 风险与注意事项

1. **图片生成成本**：10 个创意 × 4 个点位 × 5 张图 = 200 张图，默认只出 1 个创意，避免成本爆炸。
2. **生图速度**：即使使用智谱，每张图也需要数秒，多图并行需控制并发。
3. **会话消息体积**：L1/L2/L3 JSON 可能较大，前端需做分页或懒加载。
4. **向后兼容**：现有 `Project` 表字段保留，新增字段不影响旧数据。
