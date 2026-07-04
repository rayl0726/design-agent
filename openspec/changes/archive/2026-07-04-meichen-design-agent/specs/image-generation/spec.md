## 新增需求

### 需求：生成 Moodboard 图像
系统须基于设计概念 Prompt 生成用于 Moodboard 合成的艺术参考图。

#### 场景：Moodboard 图像生成
- **当** 概念设计 Agent 为"夏日海洋"主题请求 Moodboard 图像
- **则** 图像生成服务构建英文 Prompt："moodboard, summer ocean themed retail atrium installation, blue and coral color palette, hanging decorations, soft natural lighting, architectural photography style, high detail"
- **且** 调用 Pollinations.AI，参数 aspect_ratio="16:9"，seed 随机
- **且** 返回图片 URL 及本地缓存路径
- **且** 生成超时设为 60 秒；超时则返回占位图并异步重试

### 需求：生成概念效果图
系统须生成建筑可视化风格的效果图，展示设计在场地中的呈现。

#### 场景：效果图生成
- **当** 视觉设计 Agent 请求概念效果图
- **则** 系统构建详细英文 Prompt，包含：空间上下文、设计元素、材料、灯光、摄像机角度、风格修饰词
- **且** 调用 Pollinations.AI，参数 aspect_ratio="16:9"
- **且** 若 Pollinations 返回低质量或跑题结果，系统使用简化 Prompt（移除次要元素）重试

#### 场景：效果图本地降级
- **当** Pollinations.AI 触发速率限制或无法访问
- **则** 系统检查本地 ComfyUI 是否可用
- **且** 若可用，通过其 HTTP API 将生成任务加入队列
- **且** 若均不可用，返回带文字的占位图："效果图生成服务暂不可用，请稍后重试"

### 需求：生成色彩材质合成图
系统须生成一张合成图，将色块和材料缩略图按设计板布局排列。

#### 场景：合成板生成
- **当** 视觉设计 Agent 请求色彩材质板
- **则** 系统使用 Pillow（非 AI 生成）创建合成图：纯色矩形作为色块、color hex 和材料名称的文本标签、材料数据库中的可选纹理缩略图
- **且** 输出为 1200x800 PNG，排版整洁
- **且** 此操作为纯程序化处理，不调用外部图像生成 API

### 需求：抽象提供者接口
系统须暴露统一的图像生成接口，屏蔽底层提供者的差异。

#### 场景：提供者切换
- **当** 组件调用 image-generation.generate(prompt, aspect_ratio, style)
- **则** 系统将请求路由至配置的提供者（Pollinations 或 ComfyUI）
- **且** 返回标准化响应：{image_url, local_path, provider_used, generation_time_ms, prompt_sent}
- **且** 若当前提供者失败，按顺序尝试降级：Pollinations → ComfyUI → 占位图
