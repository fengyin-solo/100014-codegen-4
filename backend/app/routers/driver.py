"""司机管理接口：维护司机档案，覆盖安排上岗、排班休息、办理离职等动作。

分工与权限：岗位由请求头 ``X-Operator-Role`` 标识，规则见
``app.services.driver_permission``。写操作在此被服务端强校验，
越权请求统一返回 403 并携带可在页面展示的中文原因。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.driver import DriverService
from app.services.driver_permission import (
    current_role,
    policy_for,
    project_entry,
    require_write,
)

router = APIRouter(prefix="/api/driver", tags=["司机管理"])

service = DriverService()

STATUSES = ["待上岗", "在岗", "休息中", "已离职"]


@router.get("/me")
def my_permissions(role: str | None = Depends(current_role)) -> dict[str, Any]:
    """返回当前岗位在司机模块的权限与可见字段。

    列表页与详情页都以这里的字段清单为准渲染，保证两处范围一致；
    无写权限时附带原因，页面直接用于只读提示。
    """
    return policy_for(role).to_dict()


@router.get("/export")
def export_entries(role: str | None = Depends(current_role)) -> dict[str, Any]:
    """导出司机管理清单：敏感字段按当前岗位裁剪后再导出，不能借导出绕过权限。"""
    policy = policy_for(role)
    items, total = service.list_entries(page=1, size=10000, policy=policy)
    return {"module": "driver", "total": total, "items": items}


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按司机工号检索"),
    status: str | None = Query(default=None, description="待上岗、在岗、休息中、已离职"),
    page: int = 1,
    size: int = 20,
    role: str | None = Depends(current_role),
) -> PageResult[dict]:
    """按司机工号与状态过滤司机管理列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    policy = policy_for(role)
    items, total = service.list_entries(
        keyword=keyword, status=status, page=page, size=size, policy=policy
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int, role: str | None = Depends(current_role)) -> dict:
    """读取单条司机档案明细；不存在时给出可读的错误说明。"""
    policy = policy_for(role)
    entry = service.get_entry(entry_id, policy)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"司机档案 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload, role: str | None = Depends(current_role)) -> ActionResult:
    """登记一条司机档案，缺字段时说明原因而不是静默丢弃；仅运营管理员可登记。"""
    require_write(role)
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="司机档案已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(
    entry_id: int, payload: EntryPayload, role: str | None = Depends(current_role)
) -> ActionResult:
    """对单条司机档案执行安排上岗、排班休息、办理离职；不允许的动作会被拦下并说明原因。"""
    policy = require_write(role)
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=project_entry(entry, policy))
