<template>
  <div class="idea-gallery">
    <p class="gallery-title">已为你生成 {{ ideas.length }} 个创意方向：</p>
    <div class="cards-list">
      <div v-for="(idea, idx) in ideas" :key="idx" class="idea-card">
        <div class="idea-header">
          <span class="idea-number">{{ idx + 1 }}</span>
          <h4 class="idea-title">{{ idea.title || `创意 ${idx + 1}` }}</h4>
        </div>

        <div class="idea-section">
          <p class="section-label">主题概念</p>
          <p class="section-content">{{ idea.theme || idea.concept || '暂无' }}</p>
        </div>

        <div class="idea-section">
          <p class="section-label">设计风格</p>
          <p class="section-content">{{ idea.style || '暂无' }}</p>
        </div>

        <div class="idea-section">
          <p class="section-label">色彩搭配</p>
          <div v-if="idea.colorPalette && idea.colorPalette.length" class="color-palette">
            <span
              v-for="(c, i) in idea.colorPalette"
              :key="i"
              class="color-dot"
              :style="{ background: c.hex || c }"
              :title="c.name || c"
            />
          </div>
          <p v-else class="section-content">暂无</p>
        </div>

        <div class="idea-section">
          <p class="section-label">材质运用</p>
          <p class="section-content">{{ idea.materials || idea.materialSuggestions?.join('、') || '暂无' }}</p>
        </div>

        <div v-if="idea.design_system" class="design-system-section">
          <p class="section-label">统一设计语言</p>
          <div class="design-system-grid">
            <div class="design-item">
              <span class="design-item-label">核心元素</span>
              <span class="design-item-value">{{ idea.design_system.core_element }}</span>
            </div>
            <div class="design-item">
              <span class="design-item-label">色板</span>
              <span class="design-item-value">{{ idea.design_system.color_palette }}</span>
            </div>
            <div class="design-item">
              <span class="design-item-label">材质</span>
              <span class="design-item-value">{{ idea.design_system.material_language }}</span>
            </div>
            <div class="design-item">
              <span class="design-item-label">灯光</span>
              <span class="design-item-value">{{ idea.design_system.lighting_mood }}</span>
            </div>
          </div>
          <p class="design-connection">{{ idea.design_system.connection_across_points }}</p>
        </div>

        <div class="idea-section">
          <p class="section-label">适用点位</p>
          <p class="section-content">{{ idea.applicablePoints || idea.applicable_points || '暂无' }}</p>
        </div>

        <div class="idea-section">
          <p class="section-label">空间布局</p>
          <p class="section-content">{{ idea.spatialLayout || idea.spatial_layout || '暂无' }}</p>
        </div>

        <div class="idea-section">
          <p class="section-label">设计亮点</p>
          <p class="section-content">{{ idea.designHighlights || idea.design_highlights || idea.highlights || '暂无' }}</p>
        </div>

        <div class="idea-section">
          <p class="section-label">氛围描述</p>
          <p class="section-content">{{ idea.atmosphere || idea.mood || '暂无' }}</p>
        </div>

        <div class="idea-section">
          <p class="section-label">预算参考</p>
          <p class="section-content">{{ idea.estimatedBudget || idea.estimated_budget || '暂无' }}</p>
        </div>

        <div v-if="idea.points && idea.points.length" class="points-section">
          <p class="section-label">点位效果图</p>
          <div v-for="(point, pIdx) in idea.points" :key="pIdx" class="point-block">
            <div class="point-header">
              <span class="point-name">{{ point.point_name }}</span>
              <span v-if="point.description" class="point-desc">{{ point.description }}</span>
            </div>
            <div class="point-images">
              <div
                v-for="(url, imgIdx) in point.image_urls"
                :key="imgIdx"
                class="point-image-wrapper"
                @click="openLightbox(idea, pIdx, imgIdx)"
              >
                <img
                  v-if="url"
                  :src="resolveImageUrl(url)"
                  :alt="`${point.point_name} ${['左', '中', '右'][imgIdx]}`"
                  class="point-image"
                  @error="handleImageError(point, imgIdx)"
                />
                <div v-else class="point-image-placeholder">
                  生成失败
                </div>
                <span class="image-label">{{ ['左', '中', '右'][imgIdx] }}</span>
                <button
                  class="image-feedback-btn"
                  @click.stop="openImageFeedback(idea, idx, point, imgIdx)"
                >
                  <el-icon><ChatRound /></el-icon>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="idea-image-section">
          <p class="section-label">效果图</p>
          <div v-if="hasImages(idea)" class="idea-image-grid">
            <div
              v-for="(url, imgIdx) in getImageUrls(idea)"
              :key="imgIdx"
              class="idea-image-wrapper"
              @click="openLightbox(idea, -1, imgIdx)"
            >
              <img
                v-if="url"
                :src="resolveImageUrl(url)"
                :alt="`效果图 ${imgIdx + 1}`"
                class="idea-image"
                @error="handleImageError(idea, imgIdx)"
              />
              <div v-else class="idea-image-placeholder">
                效果图生成失败
              </div>
            </div>
          </div>
          <div v-else class="idea-image-placeholder">
            效果图生成中或生成失败
          </div>
        </div>

        <div class="feedback-section">
          <button class="feedback-btn" @click="showFeedback(idx)">反馈创意</button>
        </div>
      </div>
    </div>

    <teleport to="body">
      <div v-if="lightboxOpen" class="lightbox-overlay" @click="closeLightbox">
        <button class="lightbox-close" @click="closeLightbox">×</button>
        <button class="lightbox-prev" @click="prevImage" v-if="currentImageIdx > 0">‹</button>
        <button class="lightbox-next" @click="nextImage" v-if="currentImageIdx < currentImages.length - 1">›</button>
        <img :src="resolveImageUrl(currentImages[currentImageIdx] || '')" class="lightbox-image" @click.stop />
        <p class="lightbox-caption">{{ currentCaption }}</p>
      </div>
    </teleport>

    <el-dialog
      v-model="feedbackDialogOpen"
      title="图片反馈"
      width="420px"
      :close-on-click-modal="false"
    >
      <p class="feedback-dialog-desc">
        对「{{ feedbackForm.point_name }} {{ ['左', '中', '右'][feedbackForm.image_index] }}视角」的反馈
      </p>
      <el-form label-position="top">
        <el-form-item label="反馈类型">
          <el-select v-model="feedbackForm.tag" placeholder="请选择">
            <el-option
              v-for="tag in feedbackTags"
              :key="tag.value"
              :label="tag.label"
              :value="tag.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="补充说明">
          <el-input
            v-model="feedbackForm.comment"
            type="textarea"
            :rows="3"
            placeholder="具体说说哪里不满意，或希望怎么调整..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="feedbackDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="feedbackSubmitting" @click="submitFeedback">
          提交反馈
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatRound } from '@element-plus/icons-vue'
import { feedbackApi } from '../../api/client.js'

const props = defineProps({ ideas: Array, projectId: String })

const emit = defineEmits(['feedback'])

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

const lightboxOpen = ref(false)
const currentIdea = ref(null)
const currentPointIdx = ref(-1)
const currentImageIdx = ref(0)

const feedbackDialogOpen = ref(false)
const feedbackForm = ref({
  feedback_type: 'image',
  idea_index: 0,
  point_name: '',
  image_index: 0,
  image_url: '',
  tag: '',
  comment: ''
})
const feedbackSubmitting = ref(false)

const feedbackTags = [
  { value: 'style', label: '风格/调性' },
  { value: 'composition', label: '构图/视角' },
  { value: 'content', label: '内容' },
  { value: 'material_lighting', label: '材质/灯光' }
]

function resolveImageUrl(url) {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  // 兼容 agent-core 早期返回的绝对本地路径，只取文件名
  const match = url.match(/[\\/]([^\\/]+\.png|[^\\/]+\.jpg|[^\\/]+\.jpeg|[^\\/]+\.webp)$/i)
  const fileName = match ? match[1] : url
  if (fileName.startsWith('/')) return `${API_BASE}${fileName}`
  return `${API_BASE}/images/${fileName}`
}

function getImageUrls(idea) {
  if (idea.image_urls && Array.isArray(idea.image_urls) && idea.image_urls.length) {
    return idea.image_urls
  }
  if (idea.image_url) {
    return [idea.image_url]
  }
  return []
}

function hasImages(idea) {
  return getImageUrls(idea).length > 0
}

function handleImageError(item, imgIdx) {
  if (item.image_urls && Array.isArray(item.image_urls)) {
    item.image_urls[imgIdx] = ''
  } else if (item.image_url) {
    item.image_url = ''
  }
}

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
  const maxIdx = currentImages.value.length - 1
  if (currentImageIdx.value < maxIdx) {
    currentImageIdx.value++
  }
}

const currentImages = computed(() => {
  if (!currentIdea.value) return []
  if (currentPointIdx.value >= 0 && currentIdea.value.points) {
    return currentIdea.value.points[currentPointIdx.value]?.image_urls || []
  }
  return getImageUrls(currentIdea.value)
})

const currentCaption = computed(() => {
  if (!currentIdea.value) return ''
  if (currentPointIdx.value >= 0 && currentIdea.value.points) {
    const point = currentIdea.value.points[currentPointIdx.value]
    const labels = ['左视角', '中视角', '右视角']
    return `${point?.point_name || ''} - ${labels[currentImageIdx.value] || ''}`
  }
  return `效果图 ${currentImageIdx.value + 1}`
})

function showFeedback(ideaIdx) {
  emit('feedback', { ideaIndex: ideaIdx, idea: props.ideas[ideaIdx] })
}

function openImageFeedback(idea, ideaIdx, point, imageIdx) {
  feedbackForm.value = {
    feedback_type: 'image',
    idea_index: ideaIdx,
    point_name: point?.point_name || '',
    image_index: imageIdx,
    image_url: point?.image_urls?.[imageIdx] || idea?.image_urls?.[imageIdx] || '',
    tag: '',
    comment: ''
  }
  feedbackDialogOpen.value = true
}

async function submitFeedback() {
  if (!props.projectId) {
    ElMessage.warning('缺少项目 ID，无法提交反馈')
    return
  }
  if (!feedbackForm.value.tag && !feedbackForm.value.comment.trim()) {
    ElMessage.warning('请选择反馈类型或填写补充说明')
    return
  }
  feedbackSubmitting.value = true
  try {
    await feedbackApi.create(props.projectId, feedbackForm.value)
    ElMessage.success('反馈已提交')
    feedbackDialogOpen.value = false
  } catch (e) {
    ElMessage.error('反馈提交失败')
  } finally {
    feedbackSubmitting.value = false
  }
}

function handleKeydown(e) {
  if (lightboxOpen.value) {
    if (e.key === 'Escape') closeLightbox()
    if (e.key === 'ArrowLeft') prevImage()
    if (e.key === 'ArrowRight') nextImage()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.idea-gallery {
  width: 100%;
}
.gallery-title {
  font-weight: 500;
  margin-bottom: 16px;
  color: #334155;
  line-height: 1.6;
}
.cards-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.idea-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 20px;
  transition: box-shadow 0.2s;
}
.idea-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}
.idea-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.idea-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}
.idea-title {
  margin: 0;
  font-size: 17px;
  color: #1e293b;
  font-weight: 600;
}
.idea-image-section {
  margin-bottom: 16px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #f1f5f9;
  background: #f8fafc;
  padding: 12px;
}
.idea-image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}
.idea-image-wrapper {
  border-radius: 8px;
  overflow: hidden;
  background: #f1f5f9;
  aspect-ratio: 16 / 9;
  cursor: pointer;
}
.idea-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.2s;
}
.idea-image:hover {
  transform: scale(1.02);
}
.idea-image-placeholder {
  width: 100%;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  border-radius: 8px;
  color: #94a3b8;
  font-size: 14px;
}
.idea-section {
  margin-bottom: 12px;
}
.section-label {
  margin: 0 0 4px;
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.section-content {
  margin: 0;
  font-size: 14px;
  color: #475569;
  line-height: 1.6;
}
.color-palette {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.color-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid #e2e8f0;
}
.design-system-section {
  margin-bottom: 12px;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
}
.design-system-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 8px;
}
.design-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.design-item-label {
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.design-item-value {
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}
.design-connection {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
}
.points-section {
  margin-bottom: 16px;
}
.point-block {
  margin-bottom: 16px;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  overflow: hidden;
}
.point-header {
  background: #f8fafc;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.point-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}
.point-desc {
  font-size: 12px;
  color: #64748b;
  flex: 1;
}
.point-images {
  display: flex;
  gap: 0;
}
.point-image-wrapper {
  flex: 1;
  position: relative;
  aspect-ratio: 16 / 9;
  cursor: pointer;
  overflow: hidden;
}
.point-image-wrapper:not(:last-child) {
  border-right: 1px solid #f1f5f9;
}
.point-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.2s;
}
.point-image:hover {
  transform: scale(1.05);
}
.point-image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  color: #94a3b8;
  font-size: 12px;
}
.image-label {
  position: absolute;
  bottom: 8px;
  left: 8px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}
.feedback-section {
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
}

.image-feedback-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s, background 0.2s;
}

.point-image-wrapper:hover .image-feedback-btn {
  opacity: 1;
}

.image-feedback-btn:hover {
  background: rgba(59, 130, 246, 0.9);
}

.feedback-dialog-desc {
  margin: 0 0 16px;
  color: #64748b;
  font-size: 14px;
}
.feedback-btn {
  padding: 6px 16px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.feedback-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}
.lightbox-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}
.lightbox-close {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 28px;
  cursor: pointer;
  border-radius: 50%;
  transition: background 0.2s;
}
.lightbox-close:hover {
  background: rgba(255, 255, 255, 0.3);
}
.lightbox-prev,
.lightbox-next {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 50px;
  height: 50px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 32px;
  cursor: pointer;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.lightbox-prev:hover,
.lightbox-next:hover {
  background: rgba(255, 255, 255, 0.3);
}
.lightbox-prev {
  left: 20px;
}
.lightbox-next {
  right: 20px;
}
.lightbox-image {
  max-width: 90vw;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 8px;
}
.lightbox-caption {
  color: #fff;
  font-size: 14px;
  margin-top: 16px;
  text-align: center;
}
</style>