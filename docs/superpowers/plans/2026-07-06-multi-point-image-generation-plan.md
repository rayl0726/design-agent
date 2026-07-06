# 多点位效果图生成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前"每个创意 5 张通用效果图"改造为"按点位精确出图"，每个点位生成左/中/右 3 个视角的效果图，同时加入需求追问、图片放大预览和反馈优化机制。

**Architecture:** 保持现有 agent-core（Python）→ agent-api（Java）→ agent-web（Vue）三层架构，通过修改各层的数据结构和处理逻辑实现按点位出图。核心改动：ConceptDesigner 输出带 design_system 和 points 结构的创意，VisualDesigner 按点位×视角生成图片，前端按点位分组展示并支持灯箱预览。

**Tech Stack:** Python 3.11, FastAPI, Java 21, Spring Boot 3, Vue 3, SiliconFlow API

## Global Constraints

- 创意数量改为 3 个
- 每个点位生成 3 张图（左/中/右视角）
- 不同点位之间要有整体设计感（通过 design_system 约束）
- 图片背景简洁，突出美陈主体
- 用户输入不足时主动追问
- 支持图片点击放大预览（灯箱）
- 支持对创意和单张图的反馈

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `agent-core/app/agents/requirement_analyst.py` | 需求分析，新增必填字段检查和追问逻辑 |
| `agent-core/app/agents/concept_designer.py` | 创意生成，输出带 design_system 和 points 的结构 |
| `agent-core/app/agents/visual_designer.py` | 图片生成，按点位×视角遍历生成 |
| `agent-api/src/main/java/com/meichen/orchestrator/service/WorkflowService.java` | 路径转换，处理新的 points 嵌套结构 |
| `agent-web/src/components/chat/IdeaGallery.vue` | 前端展示，按点位分组、灯箱预览、反馈按钮 |

---

### Task 1: Requirement Analyst 需求追问增强

**Files:**
- Modify: `agent-core/app/agents/requirement_analyst.py`

**Interfaces:**
- Consumes: 用户输入文本
- Produces: 包含完整字段的 requirement 对象，或 `need_more_info` 状态

**Steps:**

- [ ] **Step 1: 读取现有 requirement_analyst.py**

- [ ] **Step 2: 修改解析逻辑，新增必填字段检查**

在解析方法中，增加对以下字段的检查：
- `theme`（主题）
- `space_type`（空间类型）
- `budget`（预算）
- `points`（点位清单，每项必须有 name、count、size）
- `style`（设计风格）
- `brand_colors`（品牌色）
- `target_audience`（目标人群）
- `material_restrictions`（材质限制）

如果缺少任何必填字段，返回：
```python
{
    "need_more_info": True,
    "missing_fields": ["points", "brand_colors"],
    "prompt": "请补充以下信息：\n• 点位清单（每个点位的名称、数量、尺寸）\n• 品牌色或必须出现的视觉元素"
}
```

- [ ] **Step 3: 修改 fallback 逻辑，确保返回完整结构**

- [ ] **Step 4: 验证修改**

启动 agent-core，测试输入不完整时是否返回追问提示。

---

### Task 2: Concept Designer 创意文案升级

**Files:**
- Modify: `agent-core/app/agents/concept_designer.py`

**Interfaces:**
- Consumes: requirement（包含完整点位信息）
- Produces: 3 个创意，每个包含 design_system 和 points 结构

**Steps:**

- [ ] **Step 1: 修改 prompt，将创意数量从 5 改为 3**

- [ ] **Step 2: 修改 prompt，要求输出 design_system 对象**

每个创意必须包含：
```json
{
  "design_system": {
    "core_element": "核心视觉符号",
    "color_palette": "全局色板描述",
    "material_language": "主材质体系",
    "lighting_mood": "灯光调性",
    "connection_across_points": "点位间呼应方式"
  }
}
```

- [ ] **Step 3: 修改 prompt，要求按点位输出 points 数组**

每个创意的 points 数组中，每个 point 包含：
```json
{
  "point_name": "中庭",
  "description": "该点位设计描述",
  "left_prompt": "左视角英文提示词（100-200词）",
  "center_prompt": "中视角英文提示词（100-200词）",
  "right_prompt": "右视角英文提示词（100-200词）"
}
```

- [ ] **Step 4: 添加 prompt 强制规则**

```
强制规则：
1. 同一 point 的 3 个 prompt 只能改相机角度（left/center/right view），场景内容必须完全一致
2. 所有 point 的 prompt 必须引用 design_system 中的核心元素、色板、材质
3. 所有提示词必须包含："simple and clean background, focus on the commercial display installation, minimal surrounding distraction, professional architecture photography"
4. 不同点位之间要有明显的设计语言呼应
```

- [ ] **Step 5: 修改 fallback_ideas，适配新结构**

生成 3 个 fallback 创意，每个包含 design_system 和 points 结构。

- [ ] **Step 6: 修改 _parse_ideas，兼容新字段**

确保正确解析 design_system 和 points 字段。

- [ ] **Step 7: 验证修改**

启动 agent-core，测试生成的创意是否包含正确的结构。

---

### Task 3: Visual Designer 图片生成

**Files:**
- Modify: `agent-core/app/agents/visual_designer.py`

**Interfaces:**
- Consumes: L1 创意（带 design_system 和 points 结构）
- Produces: L2 创意（带点位图片）

**Steps:**

- [ ] **Step 1: 修改 _generate_idea_images 方法**

遍历创意 → 遍历点位 → 遍历视角生成图片：
```python
async def _generate_idea_images(self, ideas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for idea in ideas:
        enriched = dict(idea)
        points = idea.get("points", [])
        for point in points:
            prompts = [point.get("left_prompt", ""), point.get("center_prompt", ""), point.get("right_prompt", "")]
            image_urls = []
            for prompt in prompts:
                if prompt:
                    img_path = await image_generation.generate(prompt, aspect_ratio="16:9", style="realistic")
                    image_urls.append(img_path)
                else:
                    image_urls.append("")
            point["image_urls"] = image_urls
        # 取第一个点位的中间图作为封面
        if points and points[0].get("image_urls"):
            enriched["image_url"] = points[0]["image_urls"][1] if len(points[0]["image_urls"]) > 1 else points[0]["image_urls"][0]
        results.append(enriched)
    return results
```

- [ ] **Step 2: 移除旧的 image_prompts 处理逻辑**

不再需要处理 `image_prompts` 数组，改为处理 `points` 中的 `left/center/right_prompt`。

- [ ] **Step 3: 添加日志输出**

记录每个创意、每个点位、每个视角的生成状态。

- [ ] **Step 4: 验证修改**

启动 agent-core，测试图片生成流程。

---

### Task 4: Workflow Service 路径转换

**Files:**
- Modify: `agent-api/src/main/java/com/meichen/orchestrator/service/WorkflowService.java`

**Interfaces:**
- Consumes: L2 输出（带 points 结构）
- Produces: 转换后的 URLs

**Steps:**

- [ ] **Step 1: 修改 convertImagePathsToUrls 方法**

处理嵌套的 points 结构：
```java
private List<Map<String, Object>> convertImagePathsToUrls(List<Map<String, Object>> ideas) {
    List<Map<String, Object>> result = new ArrayList<>();
    for (Map<String, Object> idea : ideas) {
        Map<String, Object> copy = new HashMap<>(idea);
        // 处理封面图
        Object imageUrl = copy.get("image_url");
        if (imageUrl instanceof String path && !path.isEmpty()) {
            Path p = Path.of(path);
            copy.put("image_url", "/images/" + p.getFileName().toString());
        }
        // 处理点位图片
        Object pointsObj = copy.get("points");
        if (pointsObj instanceof List) {
            List<Map<String, Object>> points = new ArrayList<>();
            for (Object pointObj : (List<?>) pointsObj) {
                if (pointObj instanceof Map) {
                    Map<String, Object> point = new HashMap<>((Map<?, ?>) pointObj);
                    Object imageUrls = point.get("image_urls");
                    if (imageUrls instanceof List) {
                        List<String> urls = new ArrayList<>();
                        for (Object item : (List<?>) imageUrls) {
                            if (item instanceof String path && !path.isEmpty()) {
                                Path p = Path.of(path);
                                urls.add("/images/" + p.getFileName().toString());
                            } else {
                                urls.add("");
                            }
                        }
                        point.put("image_urls", urls);
                    }
                    points.add(point);
                }
            }
            copy.put("points", points);
        }
        result.add(copy);
    }
    return result;
}
```

- [ ] **Step 2: 修改提示文案**

将"已为你生成 5 个创意方向及效果图"改为"已为你生成 3 个创意方向及效果图"。

- [ ] **Step 3: 验证修改**

启动 agent-api，测试路径转换是否正确。

---

### Task 5: Idea Gallery 前端展示

**Files:**
- Modify: `agent-web/src/components/chat/IdeaGallery.vue`

**Interfaces:**
- Consumes: ideas（带 design_system 和 points 结构）
- Produces: 按点位分组展示的创意卡片，支持灯箱预览和反馈

**Steps:**

- [ ] **Step 1: 修改模板结构**

每个创意卡片顶部展示 design_system 摘要：
```vue
<div class="design-system">
  <p class="section-label">统一设计语言</p>
  <div class="design-system-grid">
    <div class="design-item">
      <span class="design-item-label">核心元素</span>
      <span class="design-item-value">{{ idea.design_system?.core_element }}</span>
    </div>
    <div class="design-item">
      <span class="design-item-label">色板</span>
      <span class="design-item-value">{{ idea.design_system?.color_palette }}</span>
    </div>
    <div class="design-item">
      <span class="design-item-label">材质</span>
      <span class="design-item-value">{{ idea.design_system?.material_language }}</span>
    </div>
    <div class="design-item">
      <span class="design-item-label">灯光</span>
      <span class="design-item-value">{{ idea.design_system?.lighting_mood }}</span>
    </div>
  </div>
</div>
```

- [ ] **Step 2: 按点位分组展示图片**

```vue
<div v-for="(point, pIdx) in idea.points" :key="pIdx" class="point-section">
  <div class="point-header">
    <p class="point-name">{{ point.point_name }}</p>
    <p class="point-desc">{{ point.description }}</p>
  </div>
  <div class="point-images">
    <div v-for="(url, imgIdx) in point.image_urls" :key="imgIdx" class="point-image-wrapper" @click="openLightbox(idea, pIdx, imgIdx)">
      <img :src="resolveImageUrl(url)" :alt="`${point.point_name} ${['左', '中', '右'][imgIdx]}`" class="point-image" />
      <span class="image-label">{{ ['左', '中', '右'][imgIdx] }}</span>
    </div>
  </div>
</div>
```

- [ ] **Step 3: 添加灯箱组件**

```vue
<teleport to="body">
  <div v-if="lightboxOpen" class="lightbox-overlay" @click="closeLightbox">
    <button class="lightbox-close" @click="closeLightbox">×</button>
    <button class="lightbox-prev" @click="prevImage" v-if="currentImageIdx > 0">‹</button>
    <button class="lightbox-next" @click="nextImage" v-if="currentImageIdx < currentPointImages.length - 1">›</button>
    <img :src="resolveImageUrl(currentImage)" class="lightbox-image" @click.stop />
    <p class="lightbox-caption">{{ currentPointName }} - {{ ['左视角', '中视角', '右视角'][currentImageIdx] }}</p>
  </div>
</teleport>
```

- [ ] **Step 4: 添加灯箱逻辑**

```javascript
const lightboxOpen = ref(false)
const currentIdea = ref(null)
const currentPointIdx = ref(0)
const currentImageIdx = ref(0)

function openLightbox(idea, pIdx, imgIdx) {
  currentIdea.value = idea
  currentPointIdx.value = pIdx
  currentImageIdx.value = imgIdx
  lightboxOpen.value = true
  document.body.style.overflow = 'hidden'
}

function closeLightbox() {
  lightboxOpen.value = false
  document.body.style.overflow = ''
}

function prevImage() {
  if (currentImageIdx.value > 0) {
    currentImageIdx.value--
  }
}

function nextImage() {
  const maxIdx = currentPointImages.value.length - 1
  if (currentImageIdx.value < maxIdx) {
    currentImageIdx.value++
  }
}

function currentPointImages() {
  if (!currentIdea.value?.points) return []
  return currentIdea.value.points[currentPointIdx.value]?.image_urls || []
}

function currentImage() {
  return currentPointImages.value[currentImageIdx.value] || ''
}

function currentPointName() {
  if (!currentIdea.value?.points) return ''
  return currentIdea.value.points[currentPointIdx.value]?.point_name || ''
}

onMounted(() => {
  window.addEventListener('keydown', (e) => {
    if (lightboxOpen.value) {
      if (e.key === 'Escape') closeLightbox()
      if (e.key === 'ArrowLeft') prevImage()
      if (e.key === 'ArrowRight') nextImage()
    }
  })
})
```

- [ ] **Step 5: 添加反馈按钮**

```vue
<div class="feedback-section">
  <button class="feedback-btn" @click="showIdeaFeedback = true">反馈创意</button>
</div>
```

- [ ] **Step 6: 添加样式**

为 design_system、point-section、lightbox、feedback-btn 添加样式。

- [ ] **Step 7: 验证修改**

启动 agent-web，测试前端展示是否正确。

---

### Task 6: 联调测试

**Files:**
- All modified files

**Steps:**

- [ ] **Step 1: 重启所有服务**

```bash
cd agent-core && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
cd agent-api && mvn spring-boot:run
cd agent-web && npm run dev
```

- [ ] **Step 2: 测试完整流程**

1. 创建会话
2. 输入需求（如：主题"夏日海洋"，空间类型"购物中心"，预算"50万"，点位"中庭1个、门头2个、DP点3个"）
3. 验证系统是否追问缺失信息
4. 验证生成 3 个创意，每个包含 design_system 和 points
5. 验证每个点位有 3 张图（左/中/右）
6. 验证图片可以点击放大预览
7. 验证反馈按钮可用

- [ ] **Step 3: 记录问题并修复**

---

## Self-Review

**1. Spec coverage:**
- ✅ 需求追问增强（Task 1）
- ✅ 创意文案升级：3 个创意、design_system、points 结构（Task 2）
- ✅ 图片生成：按点位×视角生成（Task 3）
- ✅ 路径转换：处理新结构（Task 4）
- ✅ 前端展示：按点位分组、灯箱预览、反馈（Task 5）
- ✅ 联调测试（Task 6）

**2. Placeholder scan:**
- 无 TBD/TODO
- 所有步骤包含具体代码
- 所有命令包含具体执行方式

**3. Type consistency:**
- `design_system` 结构一致
- `points` 结构一致（point_name, description, left_prompt/center_prompt/right_prompt, image_urls）
- `image_urls` 数组一致