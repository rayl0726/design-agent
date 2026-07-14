export interface TraceItem {
  type: 'thought' | 'tool_call' | 'observation' | 'error'
  content?: string
  tool_name?: string
  reason?: string
}

export interface AgentOption {
  id: string
  name: string
  description?: string
}
