from app.runners.python_runner import run_python


def test_python_runner_passes_simple_case() -> None:
    result = run_python("print(input())", [{"input": "hello\n", "expected_output": "hello"}], 5, 256)
    assert result["status"] == "PASSED"

