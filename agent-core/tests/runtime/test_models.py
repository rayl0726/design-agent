from app.runtime.models import Task, TaskPlan, Evaluation, ToolCall


def test_task_plan_next_executable():
    t1 = Task(id="t1", goal="gather", dependencies=[])
    t2 = Task(id="t2", goal="retrieve", dependencies=["t1"])
    plan = TaskPlan(tasks=[t1, t2])
    assert plan.next_executable().id == "t1"
    plan.mark_complete("t1")
    assert plan.next_executable().id == "t2"


def test_evaluation_confidence_range():
    ev = Evaluation(confidence=0.95, reason="ok", suggested_action="accept")
    assert ev.is_acceptable(threshold=0.90)
    assert not ev.is_acceptable(threshold=0.96)
