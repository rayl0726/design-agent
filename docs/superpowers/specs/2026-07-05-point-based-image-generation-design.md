# 点位化效果图生成与反馈优化设计

## 背景与目标

当前系统为每个创意生成 5 张通用效果图，存在以下问题：
- 图片与具体点位不对应，甲方无法判断每个点位落地效果。
- 同一点位缺乏多角度（左/中/右）视图。
- 多点位之间缺少整体设计感。
- 用户无法对生成结果进行反馈和迭代优化。

本设计目标：
1. 按点位出图：每个独立点位生成左/中/右 3 张效果图。
2. 保证同一点位三张图内容一致、仅视角不同。
3. 保证不同点位之间有统一的设计语言。
4. 图片支持点击放大预览。
5. 用户输入不足时主动追问。
6. 支持用户对创意/单张图反馈，并基于反馈重新生成。

## 核心设计

### 1. 需求追问机制

当用户首次输入信息不足时，需求分析节点不进入工作流，而是返回追问消息。

必填维度：
- 项目主题
- 空间类型（购物中心 / 百货 / 快闪店 / 展厅等）
- 预算区间
- 点位清单：每个点位的名称、数量、尺寸/面积、位置说明
- 设计风格偏好
- 品牌色或必须出现的视觉元素
- 目标人群 / 调性
- 材质限制或偏好
- 整体串联元素偏好（如海浪弧线、珊瑚群组）

追问流程：
1. `requirement_analyst` 解析用户输入。
2. 检测缺失维度，按优先级列出最多 3 个问题。
3. 前端展示追问卡片，用户逐条回答。
4. 多轮回答合并为完整需求对象。
5. 当所有必填维度满足后，自动进入创意生成工作流。

### 2. 创意数据结构

每个项目生成 3 个创意方向。每个创意包含：

```json
{
  "title": "海浪涌动",
  "theme": "...",
  "concept": "...",
  "style": "...",
  "colorPalette": [...],
  "materials": "...",
  "designHighlights": "...",
  "atmosphere": "...",
  "estimatedBudget": "...",
  "design_system": {
    "core_element": "翻涌的海浪弧线",
    "color_palette": ["#2E5C8A", "#FFFFFF", "#F5A623"],
    "material_language": "亚克力 + 金属烤漆 + LED 灯带",
    "lighting_mood": "明亮通透，冷暖对比",
    "connection_across_points": "所有点位共享海浪弧线和蓝白渐变配色"
  },
  "points": [
    {
      "point_name": "中庭",
      "point_description": "...",
      "left_prompt": "...",
      "center_prompt": "...",
      "right_prompt": "...",
      "image_urls": ["/images/xxx.png", "/images/yyy.png", "/images/zzz.png"]
    }
  ]
}
```

### 3. Prompt 生成规则

#### 3.1 统一设计语言约束

每个创意的 `design_system` 必须在所有点位的 prompt 中体现：
- 核心视觉符号
- 全局色板
- 主材质
- 灯光调性

#### 3.2 同一点位视角约束

同一点位的 3 个 prompt 只能修改相机角度：
- `left_prompt`：`low angle from the left side, 45-degree view`
- `center_prompt`：`straight-on frontal view, eye level`
- `right_prompt`：`low angle from the right side, 45-degree view`

其他内容描述必须完全一致。

#### 3.3 背景与主体约束

每个 prompt 必须包含：
- `simple and clean background`
- `focus on the commercial display installation`
- `minimal surrounding distraction`
- `the installation is the hero of the image`

### 4. 图片生成流程

1. `concept_designer` 生成 3 个创意，每个创意包含 `design_system` 和 `points` 列表。
2. `visual_designer` 遍历 3 个创意 × N 个点位 × 3 个视角，串行调用图片生成服务。
3. 每个生成的图片下载到本地缓存，路径存入 `image_urls`。
4. `WorkflowService` 把本地路径转换为 `/images/{filename}` 可访问 URL。
5. 通过 SSE 推送 `idea_gallery` 消息到前端。

### 5. 前端展示

#### 5.1 创意卡片

- 顶部：创意标题 + 主题概念
- 中部：`design_system` 摘要（核心元素、色板、材质、灯光）
- 下部：按点位分组，每个点位横向展示 3 张小图，分别标注"左/中/右"
- 每个创意卡片提供"整体反馈"按钮

#### 5.2 图片灯箱

- 点击任意小图弹出 `ImageLightbox` 组件。
- 灯箱内展示当前点位的 3 张图，支持左右切换。
- 支持 ESC 关闭、点击遮罩关闭。
- 每张图下方显示"左/中/右"标签和"反馈"按钮。

### 6. 反馈与优化机制

#### 6.1 反馈类型

- **整体创意反馈**："太复杂""颜色太艳""不够高端""与主题不符"
- **单张图反馈**："背景太乱""角度偏左""主体太小""材质不对"
- **整体方案反馈**："整体太卡通""点位间不统一""要更商业感"

#### 6.2 优化动作

| 反馈对象 | 优化动作 |
|---------|---------|
| 整体方案 | 把反馈作为全局约束，重新调用 `concept_designer` 生成 3 个新创意 |
| 单个创意 | 修正该创意的 `design_system` 和相关描述，重新生成该创意下所有点位的图 |
| 单张图 | 仅针对该 point + 该视角的 prompt 做局部调整，重新生成这一张 |

#### 6.3 偏好持久化

- 每次反馈内容和优化后的 prompt 存入项目偏好表。
- 后续同一项目生成时携带偏好，减少重复沟通。

## 接口与数据流

### 关键接口变更

1. `POST /agents/concept-designer/design`
   - 输入：`requirement_analyze`, `knowledge_retrieve`
   - 输出：`{ level: "L1", ideas: [...] }`，每个 idea 包含 `design_system` 和 `points`

2. `POST /agents/visual-designer/design`
   - 输入：`concept_design`, `requirement_analyze`
   - 输出：`{ level: "L2", ideas: [...] }`，每个 idea 的每个 point 包含 `image_urls`

3. `POST /api/v1/projects/{id}/feedback`（新增）
   - 输入：`{ target: "idea|point|image", ideaIndex, pointName?, imageIndex?, feedback }`
   - 输出：重新生成的结果或确认消息

### 前端组件

1. `IdeaGallery.vue`：展示 3 个创意卡片，每个卡片按点位分组。
2. `PointImageGroup.vue`：单个点位的 3 张图 + 左中右标签。
3. `ImageLightbox.vue`：图片放大预览 + 切换 + 反馈入口。
4. `FeedbackForm.vue`：反馈弹窗，选择反馈类型并填写补充说明。

## 风险与应对

| 风险 | 影响 | 应对 |
|-----|------|------|
| 图量激增 | 3 创意 × N 点位 × 3 图，生成时间变长 | 前端增加进度提示；必要时对单个 point 内 3 张图做并发生成 |
| 费用增加 | 图片 API 调用量同比增加 | 先使用 SiliconFlow 免费额度；反馈优化时只重生成必要图片 |
| LLM 不严格遵守 prompt 约束 | 同一点位三张图内容不一致 | 在 prompt 中反复强调，并在解析时校验；失败后重试 |
| 整体设计感不足 | 不同点位像独立方案 | 通过 `design_system` 强制约束 + 用户反馈迭代 |

## 实施阶段建议

### 第一阶段：核心改造
1. 修改 `requirement_analyst` 支持追问。
2. 修改 `concept_designer` 输出 `design_system` + `points`。
3. 修改 `visual_designer` 按点位/视角生成图片。
4. 修改 `WorkflowService` 处理新数据结构。
5. 修改 `IdeaGallery.vue` 按点位展示 + 灯箱预览。

### 第二阶段：反馈优化
1. 新增反馈 API 和数据库表。
2. 前端增加反馈入口。
3. 根据反馈类型实现重新生成逻辑。
4. 持久化用户偏好。

## 成功标准

- 用户输入不足时，系统能给出清晰的追问。
- 每个创意展示 3 个点位，每个点位 3 张图，共 27 张（以 3 点位为例）。
- 同一点位左/中/右三张图在内容上高度一致。
- 不同点位共享核心视觉元素和色板。
- 图片点击可放大预览。
- 用户反馈后，系统能在 30 秒内给出优化后的结果。
