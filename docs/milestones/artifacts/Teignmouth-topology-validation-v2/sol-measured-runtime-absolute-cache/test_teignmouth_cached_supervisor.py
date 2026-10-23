from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from torquay_pipeline.road_surface_validation_transition_v2 import (
    TransitionDeadlineExceeded,
    TransitionDeadlines,
)


@pytest.fixture
def wrapper():
    return runpy.run_path(
        str(Path(__file__).parents[1] / "scripts/run_teignmouth_topology_validation_v2.py")
    )


def test_absolute_membership_resolves_once_but_polls_every_line(wrapper, monkeypatch) -> None:
    run = wrapper["_run_validation_phase"]
    path = str(wrapper["ROOT"] / "synthetic_cached_supervisor.py")
    calls = []
    original_path = Path

    def tracked_path(value):
        if value == path:
            calls.append(value)
        return original_path(value)

    monkeypatch.setitem(run.__globals__, "Path", tracked_path)
    namespace = {}
    exec(
        compile(
            "def work():\n    total = 0\n    for i in range(1000):\n"
            "        total += i\n    return total\n",
            path,
            "exec",
        ),
        namespace,
    )
    observed = SimpleNamespace(polls=0)

    def clock():
        observed.polls += 1
        return 100.0

    result = run(
        namespace["work"],
        (),
        {},
        deadlines=TransitionDeadlines(100.0),
        clock=clock,
        label="cache-poll-regression",
    )
    assert result == 499500
    assert calls == [path]
    assert observed.polls >= 2000
    assert sys.gettrace() is None


@pytest.mark.parametrize("offset", [125.0, 125.000001, 135.0])
def test_cached_workspace_guard_rejects_next_line_at_cutoff(wrapper, offset) -> None:
    clock = SimpleNamespace(now=100.0)
    observed = {}
    namespace = {"clock": clock, "observed": observed, "offset": offset}
    exec(
        compile(
            "def work():\n    clock.now = 100. + offset\n"
            "    observed['late'] = True\n    return True\n",
            str(wrapper["ROOT"] / "synthetic_cache_cutoff.py"),
            "exec",
        ),
        namespace,
    )
    with pytest.raises(TransitionDeadlineExceeded):
        wrapper["_run_validation_phase"](
            namespace["work"],
            (),
            {},
            deadlines=TransitionDeadlines(100.0),
            clock=lambda: clock.now,
            label="exact-boundary",
        )
    assert observed == {}
    assert sys.gettrace() is None


def test_relative_code_names_remain_uncached(wrapper, monkeypatch) -> None:
    run = wrapper["_run_validation_phase"]
    calls = []

    def tracked_path(value):
        if value == "relative_supervisor.py":
            calls.append(value)
        return Path(value)

    monkeypatch.setitem(run.__globals__, "Path", tracked_path)
    namespace = {}
    exec(
        compile(
            "def work():\n    a = 1\n    a += 1\n    return a\n", "relative_supervisor.py", "exec"
        ),
        namespace,
    )
    assert (
        run(
            namespace["work"],
            (),
            {},
            deadlines=TransitionDeadlines(100.0),
            clock=lambda: 100.0,
            label="relative-name",
        )
        == 2
    )
    assert len(calls) >= 3


def test_native_or_external_late_return_is_still_rejected(wrapper, tmp_path) -> None:
    clock = SimpleNamespace(now=100.0)
    namespace = {"clock": clock}
    exec(
        compile(
            "def work():\n    clock.now = 226.\n    return True\n",
            str(tmp_path / "external.py"),
            "exec",
        ),
        namespace,
    )
    with pytest.raises(TransitionDeadlineExceeded):
        wrapper["_run_validation_phase"](
            namespace["work"],
            (),
            {},
            deadlines=TransitionDeadlines(100.0),
            clock=lambda: clock.now,
            label="external-return",
        )
    assert sys.gettrace() is None
