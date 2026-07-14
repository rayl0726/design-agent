from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any

from app.runtime.models import AgentContext, TaskPlan, Task, ToolCall, AgentLoopResult, Evaluation
from app.runtime.tool_registry import ToolRegistry
from app.runtime.tool import ToolContext


@dataclass
class AgentLoop:
    tool_registry: ToolRegistry
    max_iterations: int = 10
    max_duration_seconds: float = 300.0
    repeat_action_threshold: int = 2

    async def run(self, context: AgentContext, plan: TaskPlan) -> AgentLoopResult:
        start = time.time()
        tool_calls: list[ToolCall] = []
        reasoning_trace: list[dict[str, Any]] = []
        last_actions: list[tuple[str, str]] = []

        for iteration in range(1, self.max_iterations + 1):
            if time.time() - start > self.max_duration_seconds:
                reasoning_trace.append({"type": "error", "reason": "max duration exceeded"})
                break

            task = plan.next_executable()
            if not task:
                break

            reasoning_trace.append({"type": "thought", "content": f"Executing task {task.id}: {task.goal}"})
            task.status = "running"

            try:
                result = await self._execute_task(task, context, iteration)
                tool_calls.extend(result.tool_calls)
                reasoning_trace.extend(result.reasoning_trace)

                if result.is_final:
                    return AgentLoopResult(
                        final_answer=result.final_answer,
                        tool_calls=tool_calls,
                        reasoning_trace=reasoning_trace,
                    )

                task.status = "completed"
            except Exception as e:
                task.status = "failed"
                reasoning_trace.append({"type": "error", "task": task.id, "reason": str(e)})

            action_key = (task.type, str(task.result)[:100])
            last_actions.append(action_key)
            if len(last_actions) >= self.repeat_action_threshold and len(set(last_actions[-self.repeat_action_threshold:])) == 1:
                reasoning_trace.append({"type": "error", "reason": "repeated action detected, aborting loop"})
                break

        return AgentLoopResult(
            final_answer={"status": "incomplete", "reasoning": reasoning_trace[-1] if reasoning_trace else {}},
            tool_calls=tool_calls,
            reasoning_trace=reasoning_trace,
        )

    async def _execute_task(self, task: Task, context: AgentContext, iteration: int):
        tool_context = ToolContext(
            conversation_id=context.conversation_id,
            agent_type=context.agent_type,
            working_memory=context.working_memory,
        )

        extracted = context.working_memory.get("extracted_fields", {})
        tool, inputs = self._select_tool(task, extracted)

        start = time.time()
        output = await tool.execute(inputs, tool_context)
        duration_ms = int((time.time() - start) * 1000)
        is_final = tool.name in ("respond_to_user", "invoke_meichen_workflow") and task.id != "information_gathering"
        return _TaskExecutionResult(
            is_final=is_final,
            final_answer=output.data,
            tool_calls=[ToolCall(iteration=iteration, tool_name=tool.name, inputs=inputs, output_summary=output.observation, duration_ms=duration_ms)],
            reasoning_trace=[],
        )

    def _select_tool(self, task: Task, extracted_fields: dict):
        if task.id in ("generate_ideas", "invoke_meichen_workflow"):
            return self.tool_registry.get("invoke_meichen_workflow"), extracted_fields

        if task.id == "information_gathering" and task.required_fields:
            missing = [f for f in task.required_fields if f not in extracted_fields]
            if missing:
                return self.tool_registry.get("ask_user"), {"question": f"请补充以下信息：{', '.join(missing)}"}
            return self.tool_registry.get("respond_to_user"), {"answer": "信息已收集完整"}

        return self.tool_registry.get("respond_to_user"), {"answer": f"任务 {task.id} 已完成"}


@dataclass
class _TaskExecutionResult:
    is_final: bool
    final_answer: dict[str, Any]
    tool_calls: list[ToolCall]
    reasoning_trace: list[dict[str, Any]]
