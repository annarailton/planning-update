"""Temporal workflow schemas."""

from typing import Optional

from pydantic import Field

from .base import CamelCaseModel


class WorkflowStatusResponse(CamelCaseModel):
    """Response for workflow status check."""

    enabled: bool = Field(..., description="Whether Temporal is enabled")
    message: str = Field(..., description="Status message with UI URL if enabled")
    ui_url: Optional[str] = Field(default=None, description="Temporal UI base URL")


class StartWorkflowRequest(CamelCaseModel):
    """Request to start a file processing workflow."""

    file_id: Optional[str] = Field(
        default=None, description="File ID (auto-generated if not provided)"
    )
    bucket_name: str = Field(default="demo-bucket", description="GCS bucket name")
    user_id: Optional[str] = Field(
        default=None, description="User ID (auto-generated if not provided)"
    )


class StartWorkflowResponse(CamelCaseModel):
    """Response after starting a workflow."""

    workflow_id: str = Field(..., description="Temporal workflow ID")
    message: str = Field(..., description="Status message with monitoring URL")


class WorkflowInfoResponse(CamelCaseModel):
    """Response with workflow information."""

    workflow_id: str = Field(..., description="Temporal workflow ID")
    status: Optional[str] = Field(
        default=None,
        description="Workflow status",
        examples=["RUNNING", "COMPLETED", "FAILED"],
    )
    start_time: Optional[str] = Field(
        default=None, description="Workflow start time (ISO format)"
    )
    close_time: Optional[str] = Field(
        default=None, description="Workflow close time (ISO format)"
    )
    result: Optional[dict] = Field(
        default=None, description="Workflow result (if completed)"
    )
    error: Optional[str] = Field(default=None, description="Error message (if failed)")
