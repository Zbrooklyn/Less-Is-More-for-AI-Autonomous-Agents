"""Worker agent — executes tasks with bounded autonomy and reports back."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional

from src.orchestrator.context import SharedContext


class WorkerStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"


@dataclass
class WorkerTask:
    """A task assigned to a worker."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    assigned_to: str = ""
    files: list[str] = field(default_factory=list)  # files this task may touch
    status: str = "pending"
    result: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None


class Worker:
    """A worker agent with bounded autonomy.

    Workers:
    - Receive tasks from the supervisor
    - Lock files they need to edit
    - Execute within their scope
    - Report progress and results
    - Release locks when done
    """

    def __init__(self, name: str, context: SharedContext):
        self.name = name
        self.context = context
        self.status = WorkerStatus.IDLE
        self.current_task: Optional[WorkerTask] = None
        self._handlers: dict[str, Callable] = {}

    def register_handler(self, task_type: str, handler: Callable[[WorkerTask], str]):
        """Register a handler for a task type. Handler returns result string."""
        self._handlers[task_type] = handler

    def accept_task(self, task: WorkerTask) -> bool:
        """Accept a task from the supervisor.

        Acquires file locks for all files the task needs to touch.
        Returns False if any required file is locked by another worker.
        """
        if self.status == WorkerStatus.WORKING:
            return False

        # Try to lock all required files
        locked_files = []
        for path in task.files:
            if self.context.lock_file(path, self.name):
                locked_files.append(path)
            else:
                # Conflict — release files we already locked
                for locked in locked_files:
                    self.context.unlock_file(locked, self.name)

                self.status = WorkerStatus.BLOCKED
                self.context.send_message(
                    self.name, "supervisor",
                    f"Cannot accept task '{task.title}': file '{path}' is locked by "
                    f"{self.context.is_file_locked(path)}",
                    msg_type="conflict",
                )
                return False

        self.current_task = task
        self.current_task.assigned_to = self.name
        self.current_task.status = "in_progress"
        self.status = WorkerStatus.WORKING

        # Notify supervisor
        self.context.send_message(
            self.name, "supervisor",
            f"Accepted task: {task.title}",
            msg_type="status",
        )

        return True

    def execute(self) -> Optional[str]:
        """Execute the current task using registered handlers.

        Returns the result string, or None if no handler matches.
        """
        if not self.current_task or self.status != WorkerStatus.WORKING:
            return None

        task = self.current_task
        handler = self._handlers.get(task.status) or self._handlers.get("default")

        if not handler:
            # No handler — try to execute based on description
            result = f"No handler registered for task: {task.title}"
            self._complete_task(result, failed=True)
            return result

        try:
            result = handler(task)
            self._complete_task(result)
            return result
        except Exception as e:
            error_msg = f"Task failed: {e}"
            self._complete_task(error_msg, failed=True)
            return error_msg

    def _complete_task(self, result: str, failed: bool = False):
        """Mark current task as complete and release locks."""
        if not self.current_task:
            return

        self.current_task.result = result
        self.current_task.status = "failed" if failed else "completed"
        self.current_task.completed_at = datetime.now(timezone.utc).isoformat()

        # Release file locks
        for path in self.current_task.files:
            self.context.unlock_file(path, self.name)

        # Update shared context with result
        self.context.set(
            f"task:{self.current_task.id}:result",
            result,
            owner=self.name,
        )

        # Notify supervisor
        msg_type = "error" if failed else "complete"
        self.context.send_message(
            self.name, "supervisor",
            f"Task '{self.current_task.title}': {result}",
            msg_type=msg_type,
        )

        self.status = WorkerStatus.DONE if not failed else WorkerStatus.FAILED

    def report_progress(self, message: str):
        """Send a progress update to the supervisor."""
        self.context.send_message(
            self.name, "supervisor", message, msg_type="progress",
        )

    def check_messages(self) -> list[dict]:
        """Check for messages from supervisor or other workers."""
        return self.context.get_messages(self.name)

    def reset(self):
        """Reset worker to idle state for next task."""
        self.current_task = None
        self.status = WorkerStatus.IDLE
