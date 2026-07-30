import pytest

from car.config import ESCConfig
from car.hardware.dry_run_backend import DryRunBackend
from car.hardware.esc import ESC, ESCState


@pytest.fixture
def esc():
    return ESC(DryRunBackend(echo=False), ESCConfig(2, 1000, 1000, 1100, 1200, 2000))


def test_does_not_arm_during_construction(esc):
    assert esc.state is ESCState.DISABLED
    assert esc.backend.events == []


def test_rejects_throttle_before_arming(esc):
    with pytest.raises(RuntimeError):
        esc.set_throttle(0.1)


def test_arm_and_forward_state_transitions(esc):
    esc.safe()
    assert esc.state is ESCState.SAFE
    esc.arm(0, sleep=lambda _: None)
    assert esc.state is ESCState.ARMED
    output = esc.set_throttle(0.5)
    assert output.state is ESCState.FORWARD
    assert output.pulse_us == 1150
    assert esc.set_throttle(0).state is ESCState.ARMED


def test_rejects_reverse_even_after_arming(esc):
    esc.arm(0, sleep=lambda _: None)
    with pytest.raises(ValueError):
        esc.set_throttle(-0.01)


def test_fault_commands_safe(esc):
    output = esc.fault()
    assert output.state is ESCState.FAULT
    assert esc.backend.outputs[2] == 1000
