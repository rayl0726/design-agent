import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AgentSelector from '../AgentSelector.vue'

describe('AgentSelector', () => {
  it('generic mode shows only meichen toggle button', () => {
    const wrapper = mount(AgentSelector, { props: { modelValue: 'generic' } })
    expect(wrapper.find('[data-testid="meichen"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="generic"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('美陈 Agent')
  })

  it('meichen mode shows only generic toggle button', () => {
    const wrapper = mount(AgentSelector, { props: { modelValue: 'meichen' } })
    expect(wrapper.find('[data-testid="generic"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="meichen"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('通用 Agent')
  })

  it('emits select when toggling from generic to meichen', async () => {
    const wrapper = mount(AgentSelector, { props: { modelValue: 'generic' } })
    await wrapper.find('[data-testid="meichen"]').trigger('click')
    expect(wrapper.emitted('select')![0]).toEqual(['meichen'])
  })

  it('emits select when toggling from meichen to generic', async () => {
    const wrapper = mount(AgentSelector, { props: { modelValue: 'meichen' } })
    await wrapper.find('[data-testid="generic"]').trigger('click')
    expect(wrapper.emitted('select')![0]).toEqual(['generic'])
  })
})
