import { describe, it, expect } from 'vitest'
import { parseToolMessage, getToolStatusLabel } from '../toolMessage'

describe('parseToolMessage', () => {
  it('parses searching status', () => {
    const content = JSON.stringify({ id: 'c1', tool_name: 'web_search', arguments: { query: 'x' }, status: 'searching' })
    const display = parseToolMessage(content)
    expect(display.status).toBe('searching')
    expect(display.toolArguments.query).toBe('x')
    expect(display.toolName).toBe('web_search')
  })

  it('parses summarizing status with detail', () => {
    const content = JSON.stringify({ id: 'c1', tool_name: 'web_search', arguments: {}, status: 'summarizing', detail: '分析 3 个网页' })
    const display = parseToolMessage(content)
    expect(display.status).toBe('summarizing')
    expect(display.detail).toBe('分析 3 个网页')
  })

  it('parses old dirty assistant tool_call XML', () => {
    const content = '<tool_call>web_search\n<arg_key>query</arg_key>\n<arg_value>北京天气</arg_value>\n</tool_call>'
    const display = parseToolMessage(content)
    expect(display.toolName).toBe('web_search')
    expect(display.toolArguments.query).toBe('北京天气')
    expect(display.status).toBe('done')
  })
})

describe('getToolStatusLabel', () => {
  it('returns correct labels', () => {
    expect(getToolStatusLabel('searching')).toBe('搜索中...')
    expect(getToolStatusLabel('summarizing')).toBe('总结中...')
    expect(getToolStatusLabel('done')).toBe('已完成')
    expect(getToolStatusLabel('')).toBe('已完成')
  })
})
