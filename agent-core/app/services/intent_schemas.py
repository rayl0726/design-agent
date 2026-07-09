from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IntentOutput(BaseModel):
    """LLM 结构化输出 schema，覆盖封闭字段与开放字段。"""

    model_config = ConfigDict(extra="ignore")

    space_type: str | None = Field(
        None,
        description="空间类型，如购物中心中庭、快闪店、百货入口。允许使用 taxonomy 之外的值。",
    )
    points: list[str] = Field(
        default_factory=list,
        description="点位列表，如门头、DP点、中庭。",
    )
    theme: str | None = Field(
        None,
        description="主题/概念，如圣诞节、春日花园、国潮。开放字段。",
    )
    budget: int | str | None = Field(
        None,
        description="预算，可以是整数（元）或字符串（如30万、300k）。",
    )
    budget_level: str | None = Field(
        None,
        description="预算等级：low/medium/high。",
    )
    style: str | None = Field(
        None,
        description="风格，如现代简约、国潮、轻奢。",
    )
    material_restrictions: list[str] = Field(
        default_factory=list,
        description="禁用的材质或元素列表。",
    )
    allowed_materials: list[str] = Field(
        default_factory=list,
        description="明确允许使用的材质或元素列表。",
    )
    color_preference: str | None = Field(
        None,
        description="颜色偏好，如红色、金色、马卡龙色。开放字段。",
    )
    brand_positioning: str | None = Field(
        None,
        description="品牌定位或目标客群，如亲子家庭、年轻潮人。开放字段。",
    )
    target_audience: str | None = Field(
        None,
        description="目标受众，如儿童、情侣、上班族。开放字段。",
    )
    timeline: str | None = Field(
        None,
        description="工期/时间要求，如1个月、春节前完成。开放字段。",
    )
    design_system_preference: str | None = Field(
        None,
        description="整体串联元素偏好，如灯光画、吊旗、绿植。",
    )
    special_requirements: list[str] = Field(
        default_factory=list,
        description="其他特殊要求。",
    )
