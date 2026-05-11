"""Test the @task decorator wraps a callable with logging and exit-on-failure."""

from pytest_mock import MockerFixture

from app.utils.decorators import task

_SYS_EXIT = "app.utils.decorators.sys.exit"


def test_task_runs_callable_on_success_path() -> None:
    """Test @task invokes the wrapped callable with its arguments on success."""
    captured: list[int] = []

    @task(label="ok")
    def func(x: int) -> None:
        captured.append(x)

    func(7)

    assert captured == [7]


def test_task_exits_on_exception(mocker: MockerFixture) -> None:
    """Test @task calls sys.exit(1) when the wrapped callable raises."""
    sys_exit = mocker.patch(_SYS_EXIT)

    @task(label="boom")
    def func() -> None:
        raise RuntimeError("nope")

    func()

    sys_exit.assert_called_once_with(1)
