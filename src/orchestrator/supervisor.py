"""Supervisor agent — decomposes tasks, assigns to workers, monitors, resolves conflicts."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from src.orchestrator.context import SharedContext
from src.orchestrator.worker import Worker, WorkerTask, WorkerStatus


@dataclass
class Plan:
    """A decomposed plan with ordered tasks."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    tasks: list[WorkerTask] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed, replanning
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Supervisor:
    """Supervisor agent that coordinates multiple workers.

    Responsibilities:
    - Decompose complex tasks into worker assignments
    - Assign tasks to workers (respecting file-level conflicts)
    - Monitor progress and handle failures
    - Resolve conflicts between workers
    - Replan when reality doesn't match the plan
    """

    def __init__(self, context: SharedContext):
        self.context = context
        self.workers: dict[str, Worker] = {}
        self.current_plan: Optional[Plan] = None
        self._decomposer: Optional[Callable] = None
        self._conflict_resolver: Optional[Callable] = None

    def add_worker(self, worker: Worker):
        """Register a worker."""
        self.workers[worker.name] = worker

    def remove_worker(self, name: str):
        """Remove a worker."""
        self.workers.pop(name, None)

    def set_decomposer(self, fn: Callable[[str], list[dict]]):
        """Set the task decomposition function.

        fn receives a task description string and returns a list of dicts:
        [{"title": str, "description": str, "files": list[str]}, ...]
        """
        self._decomposer = fn

    def set_conflict_resolver(self, fn: Callable[[str, str, str], str]):
        """Set the conflict resolution function.

        fn receives (file_path, worker_a, worker_b) and returns the winner's name.
        """
        self._conflict_resolver = fn

    def decompose(self, task_description: str) -> Plan:
        """Decompose a task into a plan of worker assignments.

        Uses the registered decomposer, or falls back to a single-task plan.
        """
        if self._decomposer:
            subtasks_data = self._decomposer(task_description)
        else:
            # Default: single task for the first available worker
            subtasks_data = [{
                "title": task_description,
                "description": task_description,
                "files": [],
            }]

        tasks = []
        for data in subtasks_data:
            tasks.append(WorkerTask(
                title=data.get("title", ""),
                description=data.get("description", ""),
                files=data.get("files", []),
            ))

        plan = Plan(title=task_description, tasks=tasks)
        self.current_plan = plan

        # Store plan in shared context
        self.context.set("plan:current", plan.id, owner="supervisor")
        self.context.set(f"plan:{plan.id}:status", "pending", owner="supervisor")
        self.context.set(f"plan:{plan.id}:task_count", str(len(tasks)), owner="supervisor")

        return plan

    def assign_tasks(self) -> dict[str, str]:
        """Assign plan tasks to available workers.

        Returns a dict of {task_id: worker_name} for successful assignments.
        """
        if not self.current_plan:
            return {}

        assignments = {}
        pending_tasks = [t for t in self.current_plan.tasks if t.status == "pending"]
        available_workers = [w for w in self.workers.values() if w.status == WorkerStatus.IDLE]

        for task, worker in zip(pending_tasks, available_workers):
            if worker.accept_task(task):
                assignments[task.id] = worker.name

        if assignments:
            self.current_plan.status = "in_progress"
            self.context.set(
                f"plan:{self.current_plan.id}:status",
                "in_progress",
                owner="supervisor",
            )

        return assignments

    def execute_all(self) -> dict[str, str]:
        """Execute all assigned tasks and collect results."""
        results = {}

        for worker in self.workers.values():
            if worker.status == WorkerStatus.WORKING:
                result = worker.execute()
                if worker.current_task:
                    results[worker.current_task.id] = result or ""

        return results

    def check_progress(self) -> dict:
        """Check the status of all tasks and workers."""
        if not self.current_plan:
            return {"status": "no_plan"}

        task_statuses = {}
        for task in self.current_plan.tasks:
            task_statuses[task.id] = {
                "title": task.title,
                "status": task.status,
                "assigned_to": task.assigned_to,
                "result": task.result,
            }

        worker_statuses = {}
        for name, worker in self.workers.items():
            worker_statuses[name] = worker.status.value

        # Check for messages (conflicts, completions)
        messages = self.context.get_messages("supervisor")

        completed = sum(1 for t in self.current_plan.tasks if t.status == "completed")
        failed = sum(1 for t in self.current_plan.tasks if t.status == "failed")
        total = len(self.current_plan.tasks)

        return {
            "plan_id": self.current_plan.id,
            "plan_status": self.current_plan.status,
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "pending": total - completed - failed,
            "tasks": task_statuses,
            "workers": worker_statuses,
            "messages": messages,
        }

    def handle_conflicts(self) -> list[str]:
        """Process conflict messages and resolve file-level conflicts.

        Returns list of resolution descriptions.
        """
        messages = self.context.get_messages("supervisor")
        conflicts = [m for m in messages if m["msg_type"] == "conflict"]
        resolutions = []

        for msg in conflicts:
            self.context.mark_read(msg["id"])

            if self._conflict_resolver:
                # Parse conflict info from message
                resolution = f"Conflict acknowledged: {msg['content']}"
                resolutions.append(resolution)
            else:
                resolutions.append(f"Unresolved conflict: {msg['content']}")

        return resolutions

    def replan(self, reason: str) -> Optional[Plan]:
        """Replan when reality doesn't match expectations.

        Cancels incomplete tasks, creates a new plan from remaining work.
        """
        if not self.current_plan:
            return None

        self.current_plan.status = "replanning"

        # Gather incomplete tasks
        incomplete = [
            t for t in self.current_plan.tasks
            if t.status not in ("completed",)
        ]

        if not incomplete:
            self.current_plan.status = "completed"
            return None

        # Release all locks for incomplete tasks
        for task in incomplete:
            for path in task.files:
                owner = self.context.is_file_locked(path)
                if owner:
                    self.context.unlock_file(path, owner)

        # Reset workers
        for worker in self.workers.values():
            if worker.status in (WorkerStatus.WORKING, WorkerStatus.BLOCKED):
                worker.reset()

        # Create new plan from remaining work
        remaining_desc = "; ".join(t.title for t in incomplete)
        new_plan = self.decompose(f"Replanned ({reason}): {remaining_desc}")

        # Broadcast replan notification
        self.context.send_message(
            "supervisor", "all",
            f"Replanning: {reason}. {len(incomplete)} tasks remaining.",
            msg_type="replan",
        )

        return new_plan

    def is_complete(self) -> bool:
        """Check if the current plan is fully complete."""
        if not self.current_plan:
            return True

        return all(
            t.status in ("completed",)
            for t in self.current_plan.tasks
        )

    def finalize(self) -> dict:
        """Finalize the plan — clean up locks, summarize results."""
        if not self.current_plan:
            return {"status": "no_plan"}

        self.current_plan.status = "completed"

        # Clean up any remaining locks
        locked = self.context.get_locked_files()
        for lock in locked:
            self.context.unlock_file(lock["path"], lock["owner"])

        # Collect results
        results = {}
        for task in self.current_plan.tasks:
            results[task.title] = {
                "status": task.status,
                "result": task.result,
                "assigned_to": task.assigned_to,
            }

        # Reset all workers
        for worker in self.workers.values():
            worker.reset()

        self.context.set(
            f"plan:{self.current_plan.id}:status",
            "completed",
            owner="supervisor",
        )

        return {
            "plan_id": self.current_plan.id,
            "status": "completed",
            "results": results,
        }
