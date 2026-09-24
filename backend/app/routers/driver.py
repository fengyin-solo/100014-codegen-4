"""司机管理接口：维护司机档案，覆盖安排上岗、排班休息、办理离职等动作。

所有接口通过请求头 ``X-Operator-Role`` 识别当前岗位，按 app.security 的口径
做越权拦截与字段裁剪；列表、详情、导出共用同一套字段权限，保证范围一致。
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from app.schemas import (
    ActionResult,
    DriverDetailResult,
    DriverExportResult,
    DriverListResult,
    EntryPayload,
)
from app import security
from app.services.driver import DriverService

router = APIRouter(prefix="/api/driver", tags=["司机管理"])

service = DriverService()


@router.get("", response_model=DriverListResult)
def list_entries(
    keyword: str | None = Query(default=None, description="按司机工号检索"),
    status: str | None = Query(default=None, description="待上岗、在岗、休息中、已离职"),
    page: int = 1,
    size: int = 20,
    x_operator_role: str | None = Header(default=None),
) -> DriverListResult:
    """按司机工号与状态过滤司机管理列表；按岗位裁剪敏感字段，没有数据时返回空页。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    role = security.normalize_role(x_operator_role)
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    items = [security.project_entry(item, role) for item in items]
    return DriverListResult(
        items=items, total=total, page=page, size=size,
        permission=security.permission_view(role),
    )


@router.get("/export", response_model=DriverExportResult)
def export_entries(x_operator_role: str | None = Header(default=None)) -> DriverExportResult:
    """导出司机管理清单：敏感字段同样按岗位裁剪，不能借导出绕过权限。"""
    role = security.normalize_role(x_operator_role)
    items, total = service.list_entries(page=1, size=10000)
    items = [security.project_entry(item, role) for item in items]
    return DriverExportResult(
        module="driver", total=total, items=items,
        permission=security.permission_view(role),
    )


@router.get("/{entry_id}", response_model=DriverDetailResult)
def get_entry(
    entry_id: int,
    x_operator_role: str | None = Header(default=None),
) -> DriverDetailResult:
    """读取单条司机档案明细；不存在时给出可读的错误说明，字段范围与列表页一致。"""
    role = security.normalize_role(x_operator_role)
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"司机档案 {entry_id} 不存在或已归档")
    return DriverDetailResult(
        entry=security.project_entry(entry, role),
        permission=security.permission_view(role),
    )


@router.post("", response_model=ActionResult)
def create_entry(
    payload: EntryPayload,
    x_operator_role: str | None = Header(default=None),
) -> ActionResult:
    """登记一条司机档案，仅运营管理员可提交；缺字段时说明原因而不是静默丢弃。"""
    role = security.normalize_role(x_operator_role)
    if not security.can_create(role):
        # 越权提交必须挡下：403 携带可读原因，前端原样展示在页面上
        raise HTTPException(status_code=403, detail=security.deny_create_message(role))
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(
            ok=False,
            message=f"缺少必填字段：{'、'.join(missing)}",
            permission=security.permission_view(role),
        )
    return ActionResult(
        ok=True, message="司机档案已登记",
        entry=security.project_entry(entry, role),
        permission=security.permission_view(role),
    )


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(
    entry_id: int,
    payload: EntryPayload,
    x_operator_role: str | None = Header(default=None),
) -> ActionResult:
    """对单条司机档案执行安排上岗、排班休息、办理离职；非运营管理员提交一律 403。"""
    role = security.normalize_role(x_operator_role)
    action = str(payload.values.get("action") or "").strip()
    # 非运营管理员提交一律挡下，即便伪造请求体也到不了业务层
    if role != "ops_admin":
        raise HTTPException(
            status_code=403,
            detail=security.deny_action_message(role, action or "未指定动作"),
        )
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(
            ok=False, message=message, permission=security.permission_view(role)
        )
    return ActionResult(
        ok=True, message=message,
        entry=security.project_entry(entry, role),
        permission=security.permission_view(role),
    )
