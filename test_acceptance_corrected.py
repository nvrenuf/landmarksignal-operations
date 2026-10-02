"""Isolated tests. Exit 2 means Windows acceptance was not run.

No test touches the live Kanban directory or the production mutex.
Passing this suite validates the library, not installation into Hermes.
"""
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import uuid

import execution_guard_v1_final as module
from execution_guard_v1_final import (
    ChildAuth, ExecutionGuard, ExecutionGuardError, LockHeldError,
    MutexUnavailableError, UnauthorizedError,
)


def worker(connection, directory, name, role):
    """Real subprocess using the production guard implementation."""
    try:
        if role == "owner":
            guard = ExecutionGuard("19", "owner", state_dir=directory, mutex_name=name, timeout=1)
            def task():
                connection.send(("owned", os.getpid()))
                if not connection.poll(20) or connection.recv() != "release":
                    raise RuntimeError("Owner release signal timed out")
            guard.execute(task)
            connection.send(("released", True))
        else:
            blocked = ExecutionGuard("19", "contender", state_dir=directory, mutex_name=name, timeout=0.15)
            try:
                blocked.execute(lambda: connection.send(("ILLEGAL_EXECUTION", True)))
            except LockHeldError:
                connection.send(("blocked", True))
            else:
                raise AssertionError("Contender executed while owner held lock")
            if not connection.poll(20) or connection.recv() != "retry":
                raise RuntimeError("Contender retry signal timed out")
            guard = ExecutionGuard("19", "contender", state_dir=directory, mutex_name=name, timeout=2)
            guard.execute(lambda: connection.send(("executed", guard.abandoned)))
            connection.send(("released", True))
    except BaseException as error:
        connection.send(("error", repr(error)))
        raise
    finally:
        connection.close()


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.auth = ChildAuth(state_dir=self.temporary.name)

    def test_unapproved_and_missing_records_are_denied(self):
        with self.assertRaises(UnauthorizedError):
            self.auth.verify("missing", "19")
        self.auth.propose("child", "19")
        with self.assertRaises(UnauthorizedError):
            self.auth.verify("child", "19")

    def test_issue_binding_and_approved_record(self):
        self.auth.propose("child", "19")
        with self.assertRaises(UnauthorizedError):
            self.auth.approve("child", "20")
        self.auth.approve("child", "19")
        self.assertTrue(self.auth.verify("child", "19"))
        with self.assertRaises(UnauthorizedError):
            self.auth.verify("child", "20")

    def test_malformed_wrong_child_and_nonboolean_approval_are_denied(self):
        self.auth.propose("child", "19")
        path = self.auth._path("child")
        for data in ([], {"child_id": "other"}, {
            "child_id": "child", "github_issue_id": "19",
            "status": "approved", "approved": "true",
        }):
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(UnauthorizedError):
                self.auth.verify("child", "19")
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(UnauthorizedError):
            self.auth.verify("child", "19")

    def test_proposal_does_not_overwrite_approval(self):
        self.auth.propose("child", "19")
        self.auth.approve("child", "19")
        with self.assertRaises(FileExistsError):
            self.auth.propose("child", "20")
        self.assertTrue(self.auth.verify("child", "19"))

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            self.auth.propose("../escape", "19")

    def test_child_cannot_execute_without_owned_scope(self):
        self.auth.propose("child", "19")
        self.auth.approve("child", "19")
        markers = []
        with self.assertRaises(UnauthorizedError):
            self.auth.execute("child", "19", lambda: markers.append("ran"),
                              guard=ExecutionGuard("19", "parent"))
        self.assertEqual(markers, [])


class PlatformTests(unittest.TestCase):
    @unittest.skipIf(module.HAS_WIN32EVENT, "Native Windows mutex is available")
    def test_unsupported_platform_fails_before_callback(self):
        markers = []
        with self.assertRaises(MutexUnavailableError):
            ExecutionGuard("19", "task").execute(lambda: markers.append("ran"))
        self.assertEqual(markers, [])


@unittest.skipUnless(module.HAS_WIN32EVENT, "Requires native Windows and pywin32")
class WindowsMutexTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = self.temporary.name
        self.name = "LandmarkSignalV1Acceptance_" + uuid.uuid4().hex
        self.children = []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for process, connection in self.children:
            if process.is_alive():
                process.terminate()
            process.join(3)
            if process.is_alive():
                process.kill()
                process.join(3)
            connection.close()
            process.close()
        self.temporary.cleanup()

    def guard(self, task="parent", **kwargs):
        return ExecutionGuard("19", task, state_dir=self.directory,
                              mutex_name=self.name, timeout=0.2, **kwargs)

    def start(self, role):
        context = mp.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=worker, args=(child, self.directory, self.name, role))
        process.start()
        child.close()
        self.children.append((process, parent))
        return process, parent

    def expect(self, connection, label):
        self.assertTrue(connection.poll(10), "Timed out waiting for " + label)
        result = connection.recv()
        self.assertEqual(result[0], label, repr(result))
        return result[1]

    def completed(self, process):
        process.join(5)
        self.assertFalse(process.is_alive(), "Worker did not exit")
        self.assertEqual(process.exitcode, 0)

    def test_two_processes_block_during_execute_then_proceed(self):
        owner, first = self.start("owner")
        self.expect(first, "owned")
        before = Path(self.directory, "current.lock").read_bytes()
        contender, second = self.start("contender")
        self.expect(second, "blocked")
        self.assertTrue(owner.is_alive())
        self.assertEqual(Path(self.directory, "current.lock").read_bytes(), before)
        first.send("release")
        self.expect(first, "released")
        self.completed(owner)
        second.send("retry")
        self.assertFalse(self.expect(second, "executed"))
        self.expect(second, "released")
        self.completed(contender)

    def test_crashed_owner_recovers_actual_abandoned_mutex(self):
        owner, first = self.start("owner")
        self.expect(first, "owned")
        # Preserve kernel object identity across owner death.
        keeper = module.win32event.CreateMutex(None, False, self.name)
        try:
            contender, second = self.start("contender")
            self.expect(second, "blocked")
            owner.terminate()
            owner.join(5)
            self.assertFalse(owner.is_alive())
            self.assertNotEqual(owner.exitcode, 0)
            self.assertTrue(Path(self.directory, "current.lock").exists())
            second.send("retry")
            self.assertTrue(self.expect(second, "executed"), "Expected WAIT_ABANDONED ownership")
            self.expect(second, "released")
            self.completed(contender)
            self.assertFalse(Path(self.directory, "current.lock").exists())
        finally:
            keeper.Close()

    def test_expired_metadata_cannot_displace_live_owner(self):
        owner, first = self.start("owner")
        self.expect(first, "owned")
        path = Path(self.directory, "current.lock")
        data = json.loads(path.read_text())
        data["expiry"] = 0
        path.write_text(json.dumps(data))
        contender, second = self.start("contender")
        self.expect(second, "blocked")
        self.assertTrue(owner.is_alive())
        self.assertEqual(json.loads(path.read_text())["token"], data["token"])
        first.send("release")
        self.expect(first, "released")
        self.completed(owner)
        second.send("retry")
        self.expect(second, "executed")
        self.expect(second, "released")
        self.completed(contender)

    def test_recursion_and_wrong_thread_release_preserve_owner(self):
        guard = self.guard()
        guard.acquire()
        try:
            with self.assertRaises(LockHeldError):
                guard.acquire()
            with self.assertRaises(LockHeldError):
                self.guard("nested").acquire()
            results = []
            thread = threading.Thread(target=lambda: results.append(guard.release()))
            thread.start()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(results, [False])
            self.assertTrue(guard._acquired)
            self.assertTrue(Path(self.directory, "current.lock").exists())
            contender, second = self.start("contender")
            self.expect(second, "blocked")
        finally:
            self.assertTrue(guard.release())
        second.send("retry")
        self.expect(second, "executed")
        self.expect(second, "released")
        self.completed(contender)

    def test_callback_exception_releases_ownership(self):
        def failure():
            raise RuntimeError("deliberate callback failure")
        with self.assertRaisesRegex(RuntimeError, "deliberate"):
            self.guard().execute(failure)
        self.assertEqual(self.guard("next").execute(lambda: "ran"), "ran")

    def test_metadata_setup_failure_releases_ownership(self):
        blocker = Path(self.directory, "not-a-directory")
        blocker.write_text("blocker")
        bad = ExecutionGuard("19", "bad", state_dir=blocker, mutex_name=self.name, timeout=0.2)
        with self.assertRaises(ExecutionGuardError):
            bad.acquire()
        self.assertEqual(self.guard("next").execute(lambda: "ran"), "ran")

    def test_child_execution_boundary_checks_before_callback(self):
        auth = ChildAuth(state_dir=self.directory)
        auth.propose("child", "19")
        auth.propose("wrong-issue", "20")
        auth.approve("wrong-issue", "20")
        parent = self.guard()
        markers = []
        def parent_task():
            for child in ("child", "wrong-issue", "missing"):
                with self.assertRaises(UnauthorizedError):
                    auth.execute(child, "19", lambda: markers.append("forbidden"), guard=parent)
            self.assertEqual(markers, [])
            # Test fixture approval only; not evidence of a real human gate.
            auth.approve("child", "19")
            self.assertEqual(auth.execute("child", "19", lambda: markers.append("approved") or "ok",
                                         guard=parent), "ok")
        parent.execute(parent_task)
        self.assertEqual(markers, ["approved"])


if __name__ == "__main__":
    portable = "--portable" in sys.argv
    classes = [ApprovalTests, PlatformTests]
    if not portable:
        classes.append(WindowsMutexTests)
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in classes)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    if not portable and not module.HAS_WIN32EVENT:
        print("BLOCKED: Windows acceptance was not run. Native Windows and pywin32 required.")
        sys.exit(2)
    print("Library tests complete. Hermes integration has NOT been validated by this suite.")
