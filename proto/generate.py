import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO_DIR = ROOT / "proto"

SERVICES = {
    "auth": ["auth.proto"],
    "projects": ["projects.proto"],
    "gateway": ["auth.proto", "projects.proto"],
}


def main() -> None:
    """Генерирует Python-код из proto-файлов для каждого сервиса."""
    for service, protos in SERVICES.items():
        service_dir = ROOT / "services" / service
        (service_dir / "app" / "grpc_gen").mkdir(parents=True, exist_ok=True)
        (service_dir / "app" / "grpc_gen" / "__init__.py").touch()
        for proto in protos:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "grpc_tools.protoc",
                    f"-Iapp/grpc_gen={PROTO_DIR}",
                    "--python_out=.",
                    "--grpc_python_out=.",
                    "--pyi_out=.",
                    str(PROTO_DIR / proto),
                ],
                cwd=service_dir,
                check=True,
            )
        print(f"{service}: ok")


if __name__ == "__main__":
    main()
