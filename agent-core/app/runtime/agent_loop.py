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
        # Placeholder: real implementation selects tool based on task type
        tool = self.tool_registry.get("respond_to_user")
        tool_context = ToolContext(
            conversation_id=context.conversation_id,
            agent_type=context.agent_type,
            working_memory=context.working_memory,
        )
        start = time.time()
        output = await tool.execute({"task": task.id}, tool_context)
        duration_ms = int((time.time() - start) * 1000)
        return _TaskExecutionResult(
            is_final=True,
            final_answer=output.data,
            tool_calls=[ToolCall(iteration=iteration, tool_name=tool.name, inputs={"task": task.id}, output_summary=output.observation, duration_ms=duration_ms)],
            reasoning_trace=[],
        )


@dataclass
class _TaskExecutionResult:
    is_final: bool
    final_answer: dict[str, Any]
    tool_calls: list[ToolCall]
    reasoning_trace: list[dict[str, Any]]
