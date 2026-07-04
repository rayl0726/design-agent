<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">新建项目</h2>
        <p class="page-subtitle">填写需求并上传相关资料，AI 将自动开始设计</p>
      </div>
    </div>

    <div class="form-card">
      <el-form :model="form" label-position="top" size="large">
        <el-row :gutter="32">
          <el-col :span="16">
            <el-form-item label="需求描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="6"
                placeholder="请描述您的设计需求，例如：夏日海洋主题中庭吊饰，预算15万，工期2周，目标人群为年轻家庭..."
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="项目主题">
              <el-input v-model="form.theme" placeholder="如：夏日海洋" />
            </el-form-item>
            <el-form-item label="空间类型">
              <el-select v-model="form.spaceType" placeholder="选择空间类型" style="width: 100%">
                <el-option label="中庭" value="中庭" />
                <el-option label="走廊" value="走廊" />
                <el-option label="入口" value="入口" />
                <el-option label="快闪店" value="快闪店" />
                <el-option label="展览" value="展览" />
              </el-select>
            </el-form-item>
            <el-form-item label="预算区间">
              <el-input v-model="form.budget" placeholder="如：15万" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider />

        <el-form-item label="资料上传">
          <el-upload
            drag
            multiple
            :auto-upload="false"
            :on-change="handleFileChange"
            accept=".jpg,.jpeg,.png,.pdf,.ppt,.pptx,.dxf,.dwg"
            class="upload-area"
          >
            <el-icon :size="40" class="upload-icon"><Upload /></el-icon>
            <div class="upload-text">
              <p>拖拽文件到此处，或 <em>点击上传</em></p>
              <p class="upload-hint">支持：照片 / CAD图纸 / PDF / PPT / 参考图</p>
            </div>
          </el-upload>
        </el-form-item>

        <div class="form-actions">
          <el-button size="large" @click="$router.push('/')">取消</el-button>
          <el-button size="large" type="primary" :loading="submitting" @click="submit">
            创建项目
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Upload } from '@element-plus/icons-vue'
import { projectApi } from '../api/client.js'
import { ElMessage } from 'element-plus'

const router = useRouter()
const submitting = ref(false)
const uploadedFiles = ref([])

const form = ref({
  description: '',
  theme: '',
  spaceType: '',
  budget: '',
})

const handleFileChange = (file, fileList) => {
  uploadedFiles.value = fileList
}

const submit = async () => {
  if (!form.value.description) {
    ElMessage.warning('请填写需求描述')
    return
  }
  submitting.value = true
  try {
    // 构造 inputs 数组
    const inputs = []
    if (form.value.description) {
      inputs.push({ type: 'text', content: form.value.description })
    }
    uploadedFiles.value.forEach((f) => {
      const ext = f.name.split('.').pop().toLowerCase()
      let type = 'image'
      if (ext === 'dxf' || ext === 'dwg') type = 'cad'
      else if (ext === 'pdf') type = 'pdf'
      else if (ext === 'ppt' || ext === 'pptx') type = 'ppt'
      inputs.push({ type, fileName: f.name, content: f.raw })
    })

    const res = await projectApi.create({
      name: form.value.theme || form.value.description.slice(0, 20),
      inputs,
    })
    ElMessage.success('项目创建成功')
    router.push(`/project/${res.data.id}`)
  } catch (e) {
    console.error(e)
    ElMessage.error('创建失败：' + (e.response?.data?.message || e.message))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #888;
  margin-top: 6px;
}

.form-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  padding: 40px;
  border-radius: 12px;
  border-style: dashed;
  border-color: #dcdfe6;
  background: #fafafa;
}

.upload-icon {
  color: #c0c4cc;
  margin-bottom: 12px;
}

.upload-text p {
  margin: 4px 0;
  color: #606266;
  font-size: 14px;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-hint {
  font-size: 12px !important;
  color: #909399 !important;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #eee;
}
</style>
