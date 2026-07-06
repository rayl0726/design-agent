# 多点位效果图生成设计方案

## 概述

将当前"每个创意 5 张通用效果图"的方案改造为"按点位精确出图"，每个点位生成左/中/右 3 个视角的效果图，同时加入需求追问、图片放大预览和反馈优化机制。

## 核心目标

1. **按点位出图**：每个点位（中庭、门头、DP点等）各生成 3 张图（左/中/右视角）
2. **统一设计语言**：不同点位之间要有整体设计感，通过 `design_system` 约束实现
3. **图片质量优化**：背景简洁，突出美陈主体
4. **需求追问**：用户输入信息不足时主动追问，直到收集到足够信息
5. **图片预览**：支持点击图片放大预览（灯箱）
6. **反馈闭环**：支持用户对创意和单张图进行反馈，用于后续优化

## 数据结构变更

### 需求信息（Requirement）

新增必填字段：
- `points`: 点位清单，每项包含 `name`（名称）、`count`（数量）、`size`（尺寸）、`location`（位置说明）
- `design_system_preference`: 整体串联元素偏好
- `brand_colors`: 品牌色/必现元素
- `target_audience`: 目标人群
- `material_restrictions`: 材质限制或偏好

### 创意输出（ConceptDesigner）

每个创意结构：
```json
{
  "title": "创意标题",
  "theme": "主题概念",
  "concept": "核心概念",
  "style": "设计风格",
  "colorPalette": [...],
  "materials": "材质描述",
  "design_system": {
    "core_element": "核心视觉符号",
    "color_palette": "全局色板",
    "material_language": "主材质体系",
    "lighting_mood": "灯光调性",
    "connection_across_points": "点位间呼应方式"
  },
  "points": [
    {
      "point_name": "中庭",
      "description": "该点位设计描述",
      "left_prompt": "左视角提示词",
      "center_prompt": "中视角提示词",
      "right_prompt": "右视角提示词"
    }
  ],
  "applicablePoints": "...",
  "spatialLayout": "...",
  "designHighlights": "...",
  "atmosphere": "...",
  "estimatedBudget": "..."
}
```

### 视觉输出（VisualDesigner）

```json
{
  "level": "L2",
  "ideas": [
    {
      "title": "...",
      "design_system": {...},
      "points": [
        {
          "point_name": "中庭",
          "description": "...",
          "image_urls": ["左图路径", "中图路径", "右图路径"]
        }
      ]
    }
  ]
}
```

## 实施步骤

### 1. Requirement Analyst 需求追问增强

**文件**: `agent-core/app/agents/requirement_analyst.py`

- 新增必填字段检查：主题、空间类型、预算、点位清单（名称/数量/尺寸）、风格、品牌色/必现元素、目标人群、材质限制
- 新增字段：整体串联元素偏好
- 如果信息不足，返回 `need_more_info` 状态，前端展示追问卡片

### 2. Concept Designer 创意文案升级

**文件**: `agent-core/app/agents/concept_designer.py`

- 创意数量从 5 改为 3
- 每个创意新增 `design_system` 对象
- 每个创意下按点位输出 `points` 数组，每个 point 包含：
  - `point_name`
  - `description`
  - `left_prompt` / `center_prompt` / `right_prompt`（英文提示词）
- Prompt 强制规则：
  - 同一 point 的 3 个 prompt 只改视角，不改内容
  - 所有 point 的 prompt 必须引用 `design_system` 元素
  - 加入 `simple background, focus on installation` 约束

### 3. Visual Designer 图片生成

**文件**: `agent-core/app/agents/visual_designer.py`

- 遍历 3 个创意 × N 个点位 × 3 个视角生成图片
- 返回结构：`ideas[i].points[j].image_urls[3]`
- 保留 `image_url` 作为封面（取第一个点位的中间图）

### 4. Workflow Service 路径转换

**文件**: `agent-api/src/main/java/com/meichen/orchestrator/service/WorkflowService.java`

- 更新 `convertImagePathsToUrls` 方法，处理新的 `points` 嵌套结构
- 更新提示文案，改为"已为你生成 3 个创意方向及效果图"

### 5. Idea Gallery 前端展示

**文件**: `agent-web/src/components/chat/IdeaGallery.vue`

- 每个创意卡片顶部展示 `design_system` 摘要
- 下方按点位分组，每个点位横向展示 3 张小图（左/中/右）
- 点击小图弹出灯箱（ImageLightbox），支持当前点位 3 张图内切换、ESC 关闭、点击遮罩关闭

### 6. 反馈机制

**文件**: `agent-web/src/components/chat/IdeaGallery.vue`

- 每个创意卡片上加"反馈"按钮
- 每张效果图上加"反馈"按钮
- 反馈类型：风格/调性、构图/视角、内容、材质/灯光

## 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 图片生成数量大（3创意×6点位×3图=54张） | 高 | 生成时间长（3.5-9分钟） | 前端显示loading进度，支持异步生成 |
| 图片生成费用增加 | 中 | 成本上升 | 优化缓存策略，支持按需生成 |
| LLM 执行设计系统约束不一致 | 中 | 点位间统一感不足 | 强化 prompt 约束，增加反馈优化循环 |

## 验收标准

1. 用户输入不完整时，系统主动追问缺失信息
2. 每个创意包含 `design_system` 对象
3. 每个点位包含左/中/右 3 个视角的提示词和图片
4. 前端按点位分组展示图片，支持点击放大预览
5. 图片背景简洁，美陈主体突出
6. 不同点位之间有明显的设计语言呼应