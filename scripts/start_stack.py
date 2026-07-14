from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

SUPPORTED_PROVIDERS = {
    "nvidia",
    "gemini",
    "ollama",
    "openai",
    "openai_compatible",
}


def run(
    command: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"\n> {' '.join(command)}")

    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        check=check,
    )


def read_env_value(name: str) -> str:
    if not ENV_FILE.exists():
        raise RuntimeError(
            f"Missing environment file: {ENV_FILE}\n"
            "Create it from .env.example first."
        )

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)

        if key.strip() == name:
            return value.strip().strip("'\"")

    return ""


def read_provider() -> str:
    provider = read_env_value("LLM_PROVIDER").lower()

    if not provider:
        raise RuntimeError("LLM_PROVIDER is not configured in .env.")

    if provider not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise RuntimeError(
            f"Unsupported LLM_PROVIDER={provider!r}. "
            f"Supported providers: {supported}"
        )

    return provider


def remove_ollama_if_present() -> None:
    # A previously running Ollama container would continue consuming VRAM
    # even when the current provider is remote.
    run(
        [
            "docker",
            "compose",
            "--profile",
            "ollama",
            "rm",
            "--stop",
            "--force",
            "ollama",
        ],
        check=False,
    )


def start_ollama() -> None:
    timeout = read_env_value("OLLAMA_START_TIMEOUT_SECONDS") or "1800"

    print(
        "LLM_PROVIDER=ollama: starting Ollama and waiting "
        "for model pull, warm-up, and GPU verification."
    )

    run(
        [
            "docker",
            "compose",
            "--profile",
            "ollama",
            "up",
            "--detach",
            "--build",
            "--wait",
            "--wait-timeout",
            timeout,
            "ollama",
        ]
    )


def start_application(provider: str) -> None:
    command = ["docker", "compose"]

    if provider == "ollama":
        command.extend(["--profile", "ollama"])

    command.extend(
        [
            "up",
            "--detach",
            "--build",
            "--remove-orphans",
        ]
    )

    run(command)


def main() -> int:
    if shutil.which("docker") is None:
        print(
            "Docker CLI was not found on PATH. "
            "Start Docker Desktop and verify `docker version` works.",
            file=sys.stderr,
        )
        return 1

    try:
        provider = read_provider()
        print(f"Selected LLM provider: {provider}")

        # Validate the Compose file before changing containers.
        run(["docker", "compose", "config", "--quiet"])

        if provider == "ollama":
            start_ollama()
        else:
            print(
                f"Remote provider {provider!r} selected; "
                "Ollama will not be started."
            )
            remove_ollama_if_present()

        start_application(provider)

        print("\nApplication startup completed.")
        print("Frontend: http://localhost:5173")
        print("Backend health: http://localhost:8000/api/health")

        return 0

    except subprocess.CalledProcessError as exc:
        print(
            f"Command failed with exit code {exc.returncode}.",
            file=sys.stderr,
        )
        return exc.returncode

    except Exception as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())