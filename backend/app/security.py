"""司机档案的分工与权限口径。

角色（岗位）：
- 运营管理员 ops_admin：登记司机、安排上岗等全部动作，可见全部字段（含联系电话等敏感信息）。
- 调度员 dispatcher：只查看司机在岗情况，不可提交任何动作；联系电话等敏感字段不可见。
- 其它岗位（含未识别角色）other：与调度员字段范围一致，敏感信息一律不可见。

字段模式：
- editable 可读可写（仅运营管理员）
- readonly 只读可见
- hidden   无权限，页面按只读占位展示，不返回真实值

列表页与详情页共用 :func:`project_entry` 与 :func:`permission_view`，保证两处字段范围一致。
"""
from __future__ import annotations

from typing import Any

# 岗位编码 → 页面展示名称
ROLE_LABELS: dict[str, str] = {
    "ops_admin": "运营管理员",
    "dispatcher": "调度员",
    "other": "其它岗位",
}
# 未携带或无法识别的岗位统一归入“其它岗位”，按最小权限处理
DEFAULT_ROLE = "other"

# 司机档案字段展示顺序
ALL_FIELDS = ["司机工号", "司机姓名", "联系电话", "驾驶证号", "从业资格证号", "所属车队", "在途状态"]
# 敏感字段：除运营管理员外一律不可见
SENSITIVE_FIELDS = ["联系电话", "驾驶证号", "从业资格证号"]
# 调度岗位及其他岗位可见的非敏感字段
PUBLIC_FIELDS = ["司机工号", "司机姓名", "所属车队", "在途状态"]

# 可对司机档案执行的动作
WRITE_ACTIONS = ["安排上岗", "排班休息", "办理离职"]

HIDDEN_PLACEHOLDER = "无权限查看"

# 各岗位看到的页面说明
ROLE_NOTICES: dict[str, str] = {
    "ops_admin": "运营管理员：可登记司机档案并安排上岗，可查看联系电话等全部信息。",
    "dispatcher": "调度岗位：仅可查看司机在岗情况，不能登记或调整司机；联系电话等敏感信息已隐藏。",
    "other": "当前岗位无司机档案维护权限，仅可查看基础在岗信息；联系电话等敏感信息已隐藏。",
}


def normalize_role(role: str | None) -> str:
    """把请求头里的岗位归并到已知角色；未知值按“其它岗位”最小权限处理。"""
    role = (role or "").strip().lower()
    return role if role in ROLE_LABELS else DEFAULT_ROLE


def can_create(role: str) -> bool:
    return role == "ops_admin"


def can_run_action(role: str, action: str) -> bool:
    return role == "ops_admin" and action in WRITE_ACTIONS


def can_view_sensitive(role: str) -> bool:
    return role == "ops_admin"


def field_modes(role: str) -> dict[str, str]:
    """返回每个字段在当前岗位下的模式：editable / readonly / hidden。"""
    if role == "ops_admin":
        return {field: "editable" for field in ALL_FIELDS}
    return {
        field: ("readonly" if field in PUBLIC_FIELDS else "hidden")
        for field in ALL_FIELDS
    }


def visible_fields(role: str) -> list[str]:
    """当前岗位可见（含真实值）的字段，列表页与详情页口径一致。"""
    if role == "ops_admin":
        return list(ALL_FIELDS)
    return [field for field in ALL_FIELDS if field in PUBLIC_FIELDS]


def project_entry(entry: dict[str, Any], role: str) -> dict[str, Any]:
    """按岗位裁剪单条司机档案：无权限的敏感字段不下发真实值。

    列表、详情、导出都经过这里，避免某个入口绕过字段管控。
    """
    modes = field_modes(role)
    projected: dict[str, Any] = {}
    for key, value in entry.items():
        if key in modes and modes[key] == "hidden":
            continue
        projected[key] = value
    return projected


def permission_view(role: str) -> dict[str, Any]:
    """下发给前端的权限元数据：字段模式 + 动作权限 + 页面说明。"""
    modes = field_modes(role)
    return {
        "role": role,
        "roleLabel": ROLE_LABELS[role],
        "fields": [
            {"name": field, "mode": modes[field], "sensitive": field in SENSITIVE_FIELDS}
            for field in ALL_FIELDS
        ],
        "canCreate": can_create(role),
        "canExport": True,
        "actions": [
            {"name": action, "enabled": can_run_action(role, action)}
            for action in WRITE_ACTIONS
        ],
        "notice": ROLE_NOTICES[role],
        "hiddenPlaceholder": HIDDEN_PLACEHOLDER,
    }


def deny_create_message(role: str) -> str:
    return (
        f"当前岗位为「{ROLE_LABELS[role]}」，没有司机档案登记权限；"
        "仅运营管理员可以登记司机，请联系运营管理员处理。"
    )


def deny_action_message(role: str, action: str) -> str:
    return (
        f"当前岗位为「{ROLE_LABELS[role]}」，无权执行「{action}」；"
        "司机上岗、休息与离职安排仅运营管理员可以操作。"
    )
