export function parseToolMessage(content) {
  if (!content) {
    return { toolName: '工具', toolArguments: {}, observation: '', status: 'done', detail: '' }
  }

  // 新格式：JSON 字符串
  if (typeof content === 'string' && content.trim().startsWith('{')) {
    try {
      const data = JSON.parse(content)
      return {
        toolName: data.tool_name || '工具',
        toolArguments: data.arguments || {},
        observation: data.observation || '',
        status: data.status || 'done',
        detail: data.detail || '',
      }
    } catch (e) {
      return { toolName: '工具', toolArguments: {}, observation: content, status: 'done', detail: '' }
    }
  }

  // 兼容旧脏数据：assistant 文本中包含 <tool_call> XML
  if (typeof content === 'string' && content.includes('<tool_call>')) {
    const match = content.match(/<tool_call>([\s\S]*?)<\/tool_call>/)
    const raw = match ? match[1] : content
    const toolNameMatch = raw.match(/^(\w+)/)
    const queryMatch = raw.match(/<arg_key>query<\/arg_key>\s*<arg_value>([\s\S]*?)<\/arg_value>/)
    return {
      toolName: toolNameMatch ? toolNameMatch[1] : '工具',
      toolArguments: queryMatch ? { query: queryMatch[1].trim() } : {},
      observation: '',
      status: 'done',
      detail: '',
    }
  }

  return { toolName: '工具', toolArguments: {}, observation: content || '', status: 'done', detail: '' }
}

export function getToolStatusLabel(status) {
  if (status === 'searching') return '搜索中...'
  if (status === 'summarizing') return '总结中...'
  return '已完成'
}
