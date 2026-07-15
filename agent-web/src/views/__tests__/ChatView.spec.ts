import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import ChatView from '../ChatView.vue'

// 测试运行期间持有最后一次传入 fetchEventSource 的 onmessage 处理器
let lastOnMessage: ((msg: { event: string; data: string }) => void) | null = null

vi.mock('@microsoft/fetch-event-source', () => ({
  fetchEventSource: vi.fn((_url: string, options: any) => {
    lastOnMessage = options.onmessage
    return Promise.resolve()
  }),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    token: 'test-token',
    phone: '13800138000',
    logout: vi.fn(),
  }),
}))

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router')
  return {
    ...actual,
    useRoute: () => ({ params: { id: 'proj-1' } }),
    useRouter: () => ({ push: vi.fn() }),
  }
})

vi.mock('../../api/client.js', () => ({
  projectApi: {
    list: vi.fn(() => Promise.resolve({ data: [] })),
    get: vi.fn(() => Promise.resolve({ data: { id: 'proj-1', name: '测试会话' } })),
  },
  messageApi: {
    list: vi.fn(() => Promise.resolve({ data: [] })),
  },
  thinkingApi: {
    list: vi.fn(() => Promise.resolve({ data: [] })),
  },
  stageLogApi: {
    list: vi.fn(() => Promise.resolve({ data: [] })),
  },
}))

// Element Plus 组件 stub，避免在单元测试中加载完整 UI 库
const ElButton = defineComponent({ name: 'ElButton', render: () => h('button') })
const ElInput = defineComponent({ name: 'ElInput', render: () => h('input') })
const ElIcon = defineComponent({ name: 'ElIcon', render: () => h('span') })
const ElEmpty = defineComponent({ name: 'ElEmpty', render: () => h('div') })
const ElDialog = defineComponent({ name: 'ElDialog', render: () => h('div') })
const ElDrawer = defineComponent({ name: 'ElDrawer', render: () => h('div') })
const ElDropdown = defineComponent({ name: 'ElDropdown', render: () => h('div') })
const ElDropdownMenu = defineComponent({ name: 'ElDropdownMenu', render: () => h('div') })
const ElDropdownItem = defineComponent({ name: 'ElDropdownItem', render: () => h('div') })
const ElTag = defineComponent({ name: 'ElTag', render: () => h('span') })

const mockedMessage = vi.hoisted(() => ({ error: vi.fn(), success: vi.fn() }))
const mockedMessageBox = vi.hoisted(() => ({ confirm: vi.fn(() => Promise.reject('cancel')) }))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...(actual as any),
    ElMessage: mockedMessage,
    ElMessageBox: mockedMessageBox,
  }
})

describe('ChatView SSE tool_result', () => {
  beforeEach(() => {
    lastOnMessage = null
  })

  it('updates the matching tool card by id and sets status to done', async () => {
    const wrapper = mount(ChatView, {
      global: {
        stubs: {
          ElButton,
          ElInput,
          ElIcon,
          ElEmpty,
          ElDialog,
          ElDrawer,
          ElDropdown,
          ElDropdownMenu,
          ElDropdownItem,
          ElTag,
          TextMessage: defineComponent({ render: () => h('div') }),
          IdeaGallery: defineComponent({ render: () => h('div') }),
          ThinkingProcess: defineComponent({ render: () => h('div') }),
          RecognitionDebug: defineComponent({ render: () => h('div') }),
          AgentSelector: defineComponent({ render: () => h('div') }),
          ReasoningTrace: defineComponent({ render: () => h('div') }),
        },
      },
    })

    await flushPromises()
    expect(lastOnMessage).not.toBeNull()

    // 创建两张工具卡片
    lastOnMessage!({ event: 'tool_start', data: JSON.stringify({ id: 'call-1', tool_name: 'web_search', arguments: { query: 'a' } }) })
    lastOnMessage!({ event: 'tool_start', data: JSON.stringify({ id: 'call-2', tool_name: 'web_search', arguments: { query: 'b' } }) })

    await nextTick()

    // 仅更新 id 为 call-2 的卡片
    lastOnMessage!({
      event: 'tool_result',
      data: JSON.stringify({ id: 'call-2', tool_name: 'web_search', arguments: { query: 'b' }, observation: '结果 B' }),
    })

    await nextTick()

    const messages = (wrapper.vm as any).messages
    expect(messages.length).toBe(2)

    const call1 = JSON.parse(messages[0].content)
    expect(call1.id).toBe('call-1')
    expect(call1.observation).toBe('')
    expect(call1.status).toBe('searching')

    const call2 = JSON.parse(messages[1].content)
    expect(call2.id).toBe('call-2')
    expect(call2.observation).toBe('结果 B')
    expect(call2.status).toBe('done')
  })
})
