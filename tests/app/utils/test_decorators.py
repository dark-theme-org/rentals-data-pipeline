"""Test the @task decorator wraps a callable with logging and exit-on-failure."""

from pytest_mock import MockerFixture

from app.utils.decorators import task


def test_task_runs_callable_on_success_path() -> None:
    """Test @task invokes the wrapped callable with its arguments on success."""
    captured: list[int] = []

    @task(label="ok")
    def func(x: int) -> None:
        captured.append(x)

    times = 7
    func(times)
    assert captured == [times]


def test_task_exits_on_exception(mocker: MockerFixture) -> None:
    """Test @task calls sys.exit(1) when the wrapped callable raises."""
    sys_exit = mocker.patch("app.utils.decorators.sys.exit")

    @task(label="boom")
    def func() -> None:
        raise RuntimeError("nope")

    func()
    sys_exit.assert_called_once_with(1)


def test_task_discards_return_value() -> None:
    """Test @task returns None even when the wrapped callable returns a value."""

    @task(label="returns")
    def func() -> int:
        return 42

    assert func() is None
