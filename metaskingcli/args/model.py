import os
import enum
from typing import Optional
from datetime import datetime, timedelta

from dateutil import parser
from pydantic import BaseModel, Field, validator


class OutputFormat(enum.Enum):
    simple = "simple"
    json = "json"
    yaml = "yaml"


class HelpCmd(BaseModel):
    _description = "Show help message and exit"


class TuiCmd(BaseModel):
    _description = "Start TUI (text user interface)"

    read_only: bool = Field(
        default=False,
        description=(
            "Disable all editing operations " +
            "(this isn't safety feature, just a convenience)"
        ),
    )

    category: Optional[str] = Field(
        default=None,
        description="only show logs with this category",
    )
    task: Optional[str] = Field(
        default=None,
        description="only show logs with this task",
    )


class StartCmd(BaseModel):
    _description = (
        "Start a new work log and start tracking time" +
        ", any active log will be paused"
    )

    name: Optional[str] = Field(
        default=None,
        description="Name of log",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of log",
    )

    task: Optional[str] = Field(
        default=None,
        description="Name of task to assign the log to",
    )
    category: Optional[str] = Field(
        default=None,
        description="Name of category to assign the log to",
    )

    next: bool = Field(
        default=False,
        description="Stop active log instead of just pausing it",
    )

    time: Optional[datetime] = Field(
        default=None,
        description="Override start time of the log",
    )

    adjust: Optional[timedelta] = Field(
        default=None,
        description="Adjust the start time of the log",
    )

    @validator("time", pre=True, always=True)
    def parse_datetime(cls, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            # If it's already a datetime object, return it as is
            return value.astimezone()

        try:
            return parser.parse(value).astimezone()
        except Exception as e:
            raise ValueError(f"Failed to parse datetime: {e}")


class PauseCmd(BaseModel):
    _description = (
        "Pause tracking time of the current log (" +
        "only one log can be active at a time, " +
        "so providing an id is redundant and can be " +
        "used to make sure the active log did not change)"
    )
    id: Optional[int] = Field(
        default=None,
        description="Id of Log to pause (default: active log)",
    )

    time: Optional[datetime] = Field(
        default=None,
        description="Override end time of the record",
    )

    adjust: Optional[timedelta] = Field(
        default=None,
        description="Adjust the end time of the record",
    )

    @validator("time", pre=True, always=True)
    def parse_datetime(cls, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            # If it's already a datetime object, return it as is
            return value.astimezone()

        try:
            return parser.parse(value).astimezone()
        except Exception as e:
            raise ValueError(f"Failed to parse datetime: {e}")


class ResumeCmd(BaseModel):
    _description = "Resume tracking time of log"
    id: Optional[int] = Field(
        default=None,
        description="Id of Log to resume (default: last log)",
    )

    time: Optional[datetime] = Field(
        default=None,
        description="Override start time of the record",
    )

    adjust: Optional[timedelta] = Field(
        default=None,
        description="Adjust the start time of the record",
    )

    @validator("time", pre=True, always=True)
    def parse_datetime(cls, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            # If it's already a datetime object, return it as is
            return value.astimezone()

        try:
            return parser.parse(value).astimezone()
        except Exception as e:
            raise ValueError(f"Failed to parse datetime: {e}")


class StopCmd(BaseModel):
    _description = "Stop log - marking it as finished"
    id: Optional[int] = Field(
        default=None,
        description="Id of log to stop (default: last log)",
    )
    all: bool = Field(
        default=False,
        description="Stop all logs",
    )

    time: Optional[datetime] = Field(
        default=None,
        description="Override end time of the log",
    )

    adjust: Optional[timedelta] = Field(
        default=None,
        description="Adjust the end time of the log",
    )

    @validator("time", pre=True, always=True)
    def parse_datetime(cls, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            # If it's already a datetime object, return it as is
            return value.astimezone()

        try:
            return parser.parse(value).astimezone()
        except Exception as e:
            raise ValueError(f"Failed to parse datetime: {e}")


class StatusCmd(BaseModel):
    _description = "Show status of all non-finished logs"


class ShowCmd(BaseModel):
    _description = "Show log"
    id: Optional[int] = Field(
        description="Id of log to show (default: active log)",
    )
    format: OutputFormat = Field(
        default=OutputFormat.simple,
        description="Output format",
    )


class ListCmd(BaseModel):
    _description = "List all logs"
    # TODO: add filters

    order: Optional[str] = Field(
        default=None,
        description="Order of logs",
        regex="^(asc|desc)$",
    )

    since: Optional[datetime] = Field(
        default=None,
        description="only show logs since this date",
    )
    until: Optional[datetime] = Field(
        default=None,
        description="only show logs until this date",
    )

    category: Optional[str] = Field(
        default=None,
        description="only show logs with this category",
    )
    task: Optional[str] = Field(
        default=None,
        description="only show logs with this task",
    )

    description: Optional[str] = Field(
        default=None,
        description="only show logs with description containing these words",
    )

    flags: Optional[list[str]] = Field(
        default=None,
        description="only show logs with these flags",
    )

    format: OutputFormat = Field(
        default=OutputFormat.simple,
        description="Output format",
    )

    @validator("since", "until", pre=True, always=True)
    def parse_datetime(cls, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            # If it's already a datetime object, return it as is
            return value.astimezone()

        try:
            return parser.parse(value).astimezone()
        except Exception as e:
            raise ValueError(f"Failed to parse datetime: {e}")


class ReportCmd(BaseModel):
    _description = (
        "List sum of time spend for each day + total for all days"
    )
    # TODO: add filters

    since: Optional[datetime] = Field(
        default=None,
        description="only use logs since this date",
    )
    until: Optional[datetime] = Field(
        default=None,
        description="only use logs until this date",
    )

    category: Optional[str] = Field(
        default=None,
        description="only use logs with this category",
    )
    task: Optional[str] = Field(
        default=None,
        description="only use logs with this task",
    )

    flags: Optional[list[str]] = Field(
        default=None,
        description="only use logs with these flags",
    )

    @validator("since", "until", pre=True, always=True)
    def parse_datetime(cls, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            # If it's already a datetime object, return it as is
            return value.astimezone()

        try:
            return parser.parse(value).astimezone()
        except Exception as e:
            raise ValueError(f"Failed to parse datetime: {e}")


class DeleteCmd(BaseModel):
    _description = "Delete log"
    id: Optional[int] = Field(
        default=None,
        description="Id of log to delete (default: last log)",
    )


class EditCmd(BaseModel):
    _description = "Edit log"
    id: Optional[int] = Field(
        default=None,
        description="Id of log to edit (default: active log)",
    )
    force: bool = Field(
        default=False,
        description="Don't ask for confirmation before deleting records",
    )
    editor: str = Field(
        default=os.environ.get("EDITOR", "nano"),
        description=(
            "Editor to use (default: $EDITOR environment variable or nano)"
        ),
    )


class SetCmd(BaseModel):
    _description = (
        "Start properties of work log"
    )

    id: int = Field(
        description="Id of log to edit (default: active log)",
    )

    name: Optional[str] = Field(
        default=None,
        description="Name of log",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of log",
    )

    task: Optional[str] = Field(
        default=None,
        description="Name of task to assign the log to",
    )
    category: Optional[str] = Field(
        default=None,
        description="Name of category to assign the log to",
    )


class CliArgs(BaseModel):
    server: str = Field(
        default=os.environ.get("METASKING_SERVER", "http://localhost:8000"),
        description="Server address",
    )
    verbose: bool = Field(
        default=False,
        description="enable output of logged debug",
    )

    help: Optional[HelpCmd] = Field(
        description=HelpCmd._description,
    )
    tui: Optional[TuiCmd] = Field(
        description=TuiCmd._description,
    )
    start: Optional[StartCmd] = Field(
        description=StartCmd._description,
    )
    pause: Optional[PauseCmd] = Field(
        description=PauseCmd._description,
    )
    resume: Optional[ResumeCmd] = Field(
        description=ResumeCmd._description,
    )
    stop: Optional[StopCmd] = Field(
        description=StopCmd._description,
    )
    status: Optional[StatusCmd] = Field(
        description=StatusCmd._description,
    )
    show: Optional[ShowCmd] = Field(
        description=ShowCmd._description,
    )
    list: Optional[ListCmd] = Field(
        description=ListCmd._description,
    )
    report: Optional[ReportCmd] = Field(
        description=ReportCmd._description,
    )
    delete: Optional[DeleteCmd] = Field(
        description=DeleteCmd._description,
    )
    edit: Optional[EditCmd] = Field(
        description=EditCmd._description,
    )
    set: Optional[SetCmd] = Field(
        description=SetCmd._description,
    )

    class Config:
        validate_all = True
