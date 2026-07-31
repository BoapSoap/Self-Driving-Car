from car.control.watchdog import CommandWatchdog


def test_watchdog_timeout():
    now = [10.0]
    watchdog = CommandWatchdog(0.3, clock=lambda: now[0])
    assert watchdog.expired
    watchdog.refresh()
    now[0] += 0.299
    assert not watchdog.expired
    now[0] += 0.002
    assert watchdog.expired
