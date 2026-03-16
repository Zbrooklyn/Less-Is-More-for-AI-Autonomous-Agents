"""Tests for multi-agent orchestration — supervisor, workers, shared context."""

import pytest

from src.orchestrator.context import SharedContext
from src.orchestrator.worker import Worker, WorkerTask, WorkerStatus
from src.orchestrator.supervisor import Supervisor, Plan


@pytest.fixture
def context(tmp_path):
    db_path = tmp_path / "test_context.db"
    ctx = SharedContext(db_path)
    yield ctx
    ctx.close()


@pytest.fixture
def supervisor(context):
    return Supervisor(context)


def make_worker(name, context):
    w = Worker(name, context)
    w.register_handler("default", lambda task: f"Done: {task.title}")
    return w


# === Shared Context ===

class TestSharedContext:
    def test_set_and_get(self, context):
        context.set("key1", "value1", owner="test")
        assert context.get("key1") == "value1"

    def test_get_missing(self, context):
        assert context.get("nonexistent") is None

    def test_get_all(self, context):
        context.set("a", "1", owner="test")
        context.set("b", "2", owner="test")
        all_ctx = context.get_all()
        assert all_ctx == {"a": "1", "b": "2"}

    def test_delete(self, context):
        context.set("key", "val", owner="test")
        context.delete("key")
        assert context.get("key") is None

    def test_overwrite(self, context):
        context.set("key", "old", owner="test")
        context.set("key", "new", owner="test")
        assert context.get("key") == "new"


class TestFileLocking:
    def test_lock_and_unlock(self, context):
        assert context.lock_file("src/main.py", "worker-1")
        assert context.is_file_locked("src/main.py") == "worker-1"

        assert context.unlock_file("src/main.py", "worker-1")
        assert context.is_file_locked("src/main.py") is None

    def test_lock_conflict(self, context):
        assert context.lock_file("src/main.py", "worker-1")
        assert not context.lock_file("src/main.py", "worker-2")

    def test_same_owner_relock(self, context):
        assert context.lock_file("src/main.py", "worker-1")
        assert context.lock_file("src/main.py", "worker-1")  # Same owner ok

    def test_wrong_owner_cant_unlock(self, context):
        context.lock_file("src/main.py", "worker-1")
        assert not context.unlock_file("src/main.py", "worker-2")

    def test_get_locked_files(self, context):
        context.lock_file("a.py", "w1")
        context.lock_file("b.py", "w2")
        locked = context.get_locked_files()
        assert len(locked) == 2


class TestMessagePassing:
    def test_send_and_receive(self, context):
        context.send_message("worker-1", "supervisor", "Task done", msg_type="complete")
        messages = context.get_messages("supervisor")
        assert len(messages) == 1
        assert messages[0]["content"] == "Task done"
        assert messages[0]["msg_type"] == "complete"

    def test_unread_filter(self, context):
        msg_id = context.send_message("w1", "supervisor", "Hello")
        assert len(context.get_messages("supervisor", unread_only=True)) == 1

        context.mark_read(msg_id)
        assert len(context.get_messages("supervisor", unread_only=True)) == 0
        assert len(context.get_messages("supervisor", unread_only=False)) == 1

    def test_messages_isolated_by_recipient(self, context):
        context.send_message("w1", "supervisor", "For supervisor")
        context.send_message("w1", "worker-2", "For worker-2")

        assert len(context.get_messages("supervisor")) == 1
        assert len(context.get_messages("worker-2")) == 1

    def test_broadcast(self, context):
        # Create message history so broadcast knows recipients
        context.send_message("supervisor", "w1", "setup")
        context.send_message("supervisor", "w2", "setup")
        # Clear read
        for m in context.get_messages("w1"):
            context.mark_read(m["id"])
        for m in context.get_messages("w2"):
            context.mark_read(m["id"])

        ids = context.broadcast("supervisor", "Attention all workers")
        assert len(ids) >= 2


# === Worker ===

class TestWorker:
    def test_accept_task(self, context):
        worker = make_worker("w1", context)
        task = WorkerTask(title="Fix bug", files=["src/main.py"])

        assert worker.accept_task(task)
        assert worker.status == WorkerStatus.WORKING
        assert context.is_file_locked("src/main.py") == "w1"

    def test_reject_task_when_busy(self, context):
        worker = make_worker("w1", context)
        task1 = WorkerTask(title="Task 1")
        task2 = WorkerTask(title="Task 2")

        worker.accept_task(task1)
        assert not worker.accept_task(task2)

    def test_file_conflict_blocks_worker(self, context):
        context.lock_file("shared.py", "other-worker")

        worker = make_worker("w1", context)
        task = WorkerTask(title="Edit shared", files=["shared.py"])

        assert not worker.accept_task(task)
        assert worker.status == WorkerStatus.BLOCKED

    def test_execute_task(self, context):
        worker = make_worker("w1", context)
        task = WorkerTask(title="Run tests", files=["test.py"])

        worker.accept_task(task)
        result = worker.execute()

        assert result == "Done: Run tests"
        assert worker.status == WorkerStatus.DONE
        assert context.is_file_locked("test.py") is None  # Lock released

    def test_execute_with_failure(self, context):
        worker = Worker("w1", context)
        worker.register_handler("default", lambda t: (_ for _ in ()).throw(ValueError("boom")))

        task = WorkerTask(title="Bad task")
        worker.accept_task(task)
        result = worker.execute()

        assert "failed" in result.lower() or "boom" in result.lower()
        assert worker.status == WorkerStatus.FAILED

    def test_report_progress(self, context):
        worker = make_worker("w1", context)
        worker.report_progress("50% done")

        messages = context.get_messages("supervisor")
        assert any("50%" in m["content"] for m in messages)

    def test_reset(self, context):
        worker = make_worker("w1", context)
        task = WorkerTask(title="Task")
        worker.accept_task(task)
        worker.execute()

        worker.reset()
        assert worker.status == WorkerStatus.IDLE
        assert worker.current_task is None


# === Supervisor ===

class TestSupervisor:
    def test_decompose_default(self, supervisor, context):
        plan = supervisor.decompose("Fix all the bugs")
        assert isinstance(plan, Plan)
        assert len(plan.tasks) == 1
        assert plan.tasks[0].title == "Fix all the bugs"

    def test_decompose_custom(self, supervisor, context):
        supervisor.set_decomposer(lambda desc: [
            {"title": "Fix frontend", "description": "CSS issues", "files": ["style.css"]},
            {"title": "Fix backend", "description": "API errors", "files": ["api.py"]},
        ])

        plan = supervisor.decompose("Fix everything")
        assert len(plan.tasks) == 2
        assert plan.tasks[0].title == "Fix frontend"
        assert plan.tasks[1].title == "Fix backend"

    def test_assign_tasks(self, supervisor, context):
        w1 = make_worker("w1", context)
        w2 = make_worker("w2", context)
        supervisor.add_worker(w1)
        supervisor.add_worker(w2)

        supervisor.set_decomposer(lambda desc: [
            {"title": "Task A", "files": ["a.py"]},
            {"title": "Task B", "files": ["b.py"]},
        ])
        supervisor.decompose("Do work")

        assignments = supervisor.assign_tasks()
        assert len(assignments) == 2

    def test_execute_all(self, supervisor, context):
        w1 = make_worker("w1", context)
        supervisor.add_worker(w1)

        supervisor.decompose("Single task")
        supervisor.assign_tasks()
        results = supervisor.execute_all()

        assert len(results) == 1

    def test_check_progress(self, supervisor, context):
        w1 = make_worker("w1", context)
        supervisor.add_worker(w1)

        supervisor.decompose("Task")
        supervisor.assign_tasks()

        progress = supervisor.check_progress()
        assert progress["total_tasks"] == 1
        # Task is in_progress (not completed or failed), counted under pending
        assert progress["completed"] == 0

    def test_full_lifecycle(self, supervisor, context):
        """Full lifecycle: decompose → assign → execute → finalize."""
        w1 = make_worker("w1", context)
        w2 = make_worker("w2", context)
        supervisor.add_worker(w1)
        supervisor.add_worker(w2)

        supervisor.set_decomposer(lambda desc: [
            {"title": "Part 1", "files": ["a.py"]},
            {"title": "Part 2", "files": ["b.py"]},
        ])

        # Decompose
        plan = supervisor.decompose("Big task")
        assert plan.status == "pending"

        # Assign
        assignments = supervisor.assign_tasks()
        assert len(assignments) == 2

        # Execute
        results = supervisor.execute_all()
        assert len(results) == 2

        # Check
        assert supervisor.is_complete()

        # Finalize
        summary = supervisor.finalize()
        assert summary["status"] == "completed"
        assert len(summary["results"]) == 2

    def test_conflict_detection(self, supervisor, context):
        """Two workers trying to edit the same file."""
        w1 = make_worker("w1", context)
        w2 = make_worker("w2", context)
        supervisor.add_worker(w1)
        supervisor.add_worker(w2)

        # Manually create conflicting tasks
        task1 = WorkerTask(title="Edit shared", files=["shared.py"])
        task2 = WorkerTask(title="Also edit shared", files=["shared.py"])

        assert w1.accept_task(task1)
        assert not w2.accept_task(task2)  # Blocked

        # Supervisor should see conflict messages
        messages = context.get_messages("supervisor")
        conflicts = [m for m in messages if m["msg_type"] == "conflict"]
        assert len(conflicts) >= 1

    def test_replan(self, supervisor, context):
        w1 = make_worker("w1", context)
        supervisor.add_worker(w1)

        supervisor.decompose("Original plan")
        # Don't assign/execute — replan immediately

        new_plan = supervisor.replan("Requirements changed")
        assert new_plan is not None
        assert "Replanned" in new_plan.title

    def test_remove_worker(self, supervisor, context):
        w1 = make_worker("w1", context)
        supervisor.add_worker(w1)
        assert "w1" in supervisor.workers

        supervisor.remove_worker("w1")
        assert "w1" not in supervisor.workers
