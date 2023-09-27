import os
import enum
from typing import Optional
from pydantic import BaseModel, Field


class OutputFormat(enum.Enum):
    simple = "simple"
    json = "json"
    yaml = "yaml"


class HelpCmd(BaseModel):
    _description = "Show help message and exit"


class StartCmd(BaseModel):
    _description = (
        "Start a new log of a working session and start tracking time"
    )


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


class ResumeCmd(BaseModel):
    _description = "Resume tracking time of log"
    id: Optional[int] = Field(
        default=None,
        description="Id of Log to resume (default: last log)",
    )


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


class StatusCmd(BaseModel):
    _description = "Show status of all non-finished logs"


class ShowCmd(BaseModel):
    _description = "Show log"
    id: Optional[int] = Field(
        description="Id of log to show (default: active log)",
    )


class ListCmd(BaseModel):
    _description = "List all logs"
    # TODO: add filters

    format: OutputFormat = Field(
        default=OutputFormat.simple,
        description="Output format",
    )


class DeleteCmd(BaseModel):
    _description = "Delete log"
    id: Optional[int] = Field(
        description="Id of log to delete (default: last log)",
    )


class EditCmd(BaseModel):
    _description = "Edit log"
    id: Optional[int] = Field(
        description="Id of log to edit (default: active log)",
    )
    editor: str = Field(
        default=os.environ.get("EDITOR", "nano"),
        description=(
            "Editor to use (default: $EDITOR environment variable or nano)"
        ),
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
    delete: Optional[DeleteCmd] = Field(
        description=DeleteCmd._description,
    )
    edit: Optional[EditCmd] = Field(
        description=EditCmd._description,
    )

    class Config:
        validate_all = True
