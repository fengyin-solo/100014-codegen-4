"""司机档案的分工与权限规则。

岗位归属（由请求头 ``X-Operator-Role`` 标识，未识别岗位按最低权限处理）：

- 运营管理员（ops_admin）：登记司机、安排上岗等全部动作，可见全部字段（含联系电话）。
- 调度岗（dispatcher）：只读，只能查看司机在岗情况；看不到联系电话、证照号等敏感字段。
- 其它岗位（other）：只读，可查看基础档案，联系电话等敏感字段一律不返回。

权限口径只在这里定义，路由层做拦截、服务层做字段投影，
列表页与详情页共用同一份字段清单，保证两处展示范围一致。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Header, HTTPException

#: 岗位编码 -> 岗位中文名
ROLES: dict[str, str] = {
    "ops_admin": "运营管理员",
    "dispatcher": "调度岗",
    "other": "其它岗位",
}
DEFAULT_ROLE = "other"

#: 联系电话等敏感信息：仅运营管理员可见，其它岗位一律不返回
SENSITIVE_FIELDS: tuple[str, ...] = ("联系电话", "驾驶证号", "从业资格证号")

#: 各岗位在列表页与详情页可见的档案字段；状态列与在岗查看相关，所有可访问岗位都给
ALL_FIELDS: tuple[str, ...] = (
    "司机工号", "司机姓名", *SENSITIVE_FIELDS, "所属车队", "在途状态",
)
DISPATCHER_FIELDS: tuple[str, ...] = ("司机工号", "司机姓名", "在途状态")
BASE_FIELDS: tuple[str, ...] = ("司机工号", "司机姓名", "所属车队", "在途状态")

#: 可登记/执行动作的岗位
WRITE_ROLES: frozenset[str] = frozenset({"ops_admin"})

#: 无写权限时页面上展示的原因
READ_ONLY_REASON = "当前岗位为{role}，仅可查看司机档案，登记与上岗安排请联系运营管理员"


class PermissionDenied(HTTPException):
    """越权提交：403，detail 为可直接展示在页面上的中文原因。"""

    def __init__(self, reason: str) -> None:
        super().__init__(status_code=403, detail=reason)


@dataclass(frozen=True)
class RolePolicy:
    """单个岗位在司机模块的权限描述，原样返回给前端用于按钮与字段控制。"""

    code: str
    name: str
    can_create: bool
    can_run_actions: bool
    visible_fields: tuple[str, ...]
    denied_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.code,
            "role_name": self.name,
            "can_create": self.can_create,
            "can_run_actions": self.can_run_actions,
            # 列表页与详情页共用同一份字段清单
            "visible_fields": list(self.visible_fields),
            "denied_reason": self.denied_reason,
        }


def resolve_role(role: str | None) -> str:
    """把请求头里的岗位归并到受支持的岗位，未知值按最低权限的其它岗位处理。"""
    return role if role in ROLES else DEFAULT_ROLE


def policy_for(role: str | None) -> RolePolicy:
    code = resolve_role(role)
    writable = code in WRITE_ROLES
    if code == "ops_admin":
        visible = ALL_FIELDS
    elif code == "dispatcher":
        visible = DISPATCHER_FIELDS
    else:
        visible = BASE_FIELDS
    reason = "" if writable else READ_ONLY_REASON.format(role=ROLES[code])
    return RolePolicy(
        code=code,
        name=ROLES[code],
        can_create=writable,
        can_run_actions=writable,
        visible_fields=visible,
        denied_reason=reason,
    )


def require_write(role: str | None) -> RolePolicy:
    """写操作（登记、上岗/休息/离职动作）的服务端拦截。

    越权时抛出 403，detail 为可直接展示在页面上的中文原因。
    """
    policy = policy_for(role)
    if not policy.can_run_actions:
        raise PermissionDenied(policy.denied_reason)
    return policy


def project_entry(entry: dict[str, Any], policy: RolePolicy) -> dict[str, Any]:
    """按岗位裁剪单条档案：敏感字段不进入响应体，列表与详情范围完全一致。

    列表页和详情页共用 ``visible_fields`` 同一份口径；内部 status 不参与列裁剪，
    单独透传给页面做在岗统计与状态展示。
    """
    projected: dict[str, Any] = {"id": entry.get("id")}
    for field_name in policy.visible_fields:
        if field_name in entry:
            projected[field_name] = entry[field_name]
    if "status" in entry:
        projected["status"] = entry["status"]
    return projected


def current_role(x_operator_role: str | None = Header(default=None)) -> str | None:
    """FastAPI 依赖：读取岗位请求头，未知值原样交给 policy 层归并。"""
    return x_operator_role
