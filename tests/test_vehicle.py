from car.config import simulation_config
from car.control.vehicle import Vehicle
from car.hardware.dry_run_backend import DryRunBackend


class OrderedBackend(DryRunBackend):
    def __init__(self):
        super().__init__(echo=False)
        self.order = []

    def set_pulse_us(self, channel, pulse_us):
        self.order.append(("pulse", channel, pulse_us))
        super().set_pulse_us(channel, pulse_us)

    def shutdown(self):
        self.order.append(("shutdown",))
        super().shutdown()


def test_safe_startup_emergency_stop_and_cleanup_order():
    config = simulation_config()
    backend = OrderedBackend()
    vehicle = Vehicle(backend, config)
    for name, esc in config.motors.items():
        assert backend.outputs[esc.channel] == esc.safe_us
    vehicle.arm = lambda: None
    vehicle.emergency_stop()
    assert vehicle.emergency_stopped
    for esc in config.motors.values():
        assert backend.outputs[esc.channel] == esc.safe_us
    vehicle.close()
    shutdown_index = backend.order.index(("shutdown",))
    assert any(item[0] == "pulse" for item in backend.order[:shutdown_index])
    assert backend.is_shutdown


def test_vehicle_rejects_throttle_before_arm():
    config = simulation_config()
    vehicle = Vehicle(DryRunBackend(echo=False), config)
    try:
        try:
            vehicle.set_throttle(0.1)
        except RuntimeError:
            pass
        else:
            raise AssertionError("throttle was accepted before arming")
    finally:
        vehicle.close()
