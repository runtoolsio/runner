"""
Tests that :mod:`runner` sends correct notification to state observers.
:class:`TestStateObserver` is used for verifying the behavior.
"""

import pytest

import runtools.runner
from runtools.runcore.job import JobRun, InstanceTransitionObserver
from runtools.runcore.run import TerminationStatus, RunState, PhaseKeys, PhaseKey
from runtools.runcore.test.observer import TestTransitionObserver
from runtools.runner import runner, ExecutingPhase
from runtools.runner.execution import ExecutionException
from runtools.runner.test.execution import TestExecution


@pytest.fixture
def observer():
    observer = TestTransitionObserver()
    runner.register_transition_observer(observer)
    yield observer
    runner.deregister_transition_observer(observer)


EXEC = PhaseKey('EXEC', 'j1')


def test_passed_args(observer: TestTransitionObserver):
    runtools.runner.run_uncoordinated('j1', TestExecution())

    assert observer.job_runs[0].metadata.job_id == 'j1'
    assert observer.phases == [(PhaseKeys.INIT, EXEC), (EXEC, PhaseKeys.TERMINAL)]
    assert observer.run_states == [RunState.EXECUTING, RunState.ENDED]


def test_raise_exc(observer: TestTransitionObserver):
    with pytest.raises(Exception):
        runtools.runner.run_uncoordinated('j1', TestExecution(raise_exc=Exception))

    assert observer.run_states == [RunState.EXECUTING, RunState.ENDED]
    assert observer.job_runs[-1].termination.error.category == 'Exception'


def test_raise_exec_exc(observer: TestTransitionObserver):
    runtools.runner.run_uncoordinated('j1', TestExecution(raise_exc=ExecutionException))

    assert observer.run_states == [RunState.EXECUTING, RunState.ENDED]
    assert observer.job_runs[-1].termination.failure.category == 'ExecutionException'


def test_observer_raises_exception():
    """
    All exception raised by observer must be captured by runner and not to disrupt job execution
    """
    observer = ExceptionRaisingObserver(Exception('Should be captured by runner'))
    execution = TestExecution()
    job_instance = runtools.runner.job_instance('j1', [ExecutingPhase('', execution)])
    job_instance.add_observer_transition(observer)
    job_instance.run()
    assert execution.executed_latch.is_set()
    assert job_instance.job_run().termination.status == TerminationStatus.COMPLETED


class ExceptionRaisingObserver(InstanceTransitionObserver):

    def __init__(self, raise_exc: Exception):
        self.raise_exc = raise_exc

    def new_instance_phase(self, job_run: JobRun, previous_phase, new_phase, changed):
        raise self.raise_exc
