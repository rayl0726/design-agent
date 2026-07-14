import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AgentSelector from '../AgentSelector.vue'

describe('AgentSelector', () => {
  it('emits select on click', async () => {
    const wrapper = mount(AgentSelector, { props: { modelValue: 'generic' } })
    await wrapper.find('[data-testid="meichen"]').trigger('click')
    expect(wrapper.emitted('select')![0]).toEqual(['meichen'])
  })

  it('marks active agent', () => {
    const wrapper = mount(AgentSelector, { props: { modelValue: 'meichen' } })
    expect(wrapper.find('[data-testid="meichen"]').classes()).toContain('active')
    expect(wrapper.find('[data-testid="generic"]').classes()).not.toContain('active')
  })
})
