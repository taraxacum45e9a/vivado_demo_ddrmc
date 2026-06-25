import os
import shutil
from argparse import ArgumentParser
from importlib import resources
from pathlib import Path
from subprocess import check_call
from typing import Dict, List, Optional

from rich import print


def _first_existing(candidates: List[str]) -> Optional[str]:
    """Return the first path in candidates that exists, or None."""
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    return None


def fixed_environment_with_udev_ld_preload() -> Dict[str, str]:
    """
    Create a dictionary of environment variables (based on the current one),
    that works around a weird issue when running Vivado in a container.

    Details:
    https://adaptivesupport.amd.com/s/question/0D54U00005Sgst2SAB/failed-batch-mode-execution-in-linux-docker-running-under-windows-host?language=en_US
    https://community.flexera.com/t5/InstallAnywhere-Forum/Issues-when-running-Xilinx-tools-or-Other-vendor-tools-in-docker/m-p/245820#M10647

    The preload is inherited by the bundled MicroBlaze cross-compiler that builds
    the DDRMC firmware (phy_ddrmc.elf) under a restricted library path, so a
    forced library must bring its own dependencies. On Ubuntu 24.04 libudev.so.1
    needs libcap.so.2, so preloading libudev alone makes that compiler abort
    ("libcap.so.2: cannot open shared object file") and silently drops the ELF.
    Preload libcap alongside it. On 22.04 libudev has no libcap dependency, so
    preloading it there has no effect.
    """
    env = dict(os.environ)
    libudev = _first_existing(
        ["/lib/x86_64-linux-gnu/libudev.so.1", "/lib64/libudev.so.1"]
    )
    if libudev is None:
        return env
    preload = [libudev]
    libcap = _first_existing(
        ["/lib/x86_64-linux-gnu/libcap.so.2", "/lib64/libcap.so.2"]
    )
    if libcap is not None:
        preload.append(libcap)
    env["LD_PRELOAD"] = ":".join(preload)
    return env


def _environment_with_udev_ld_preload() -> Dict[str, str]:
    """
    Create a dictionary of environment variables (based on the current one),
    that works around a weird issue when running Vivado in a container.

    Details:
    https://adaptivesupport.amd.com/s/question/0D54U00005Sgst2SAB/failed-batch-mode-execution-in-linux-docker-running-under-windows-host?language=en_US
    https://community.flexera.com/t5/InstallAnywhere-Forum/Issues-when-running-Xilinx-tools-or-Other-vendor-tools-in-docker/m-p/245820#M10647
    """
    possible_paths = [
        Path("/lib/x86_64-linux-gnu/libudev.so.1"),
        Path("/lib64/libudev.so.1"),
    ]
    existing_paths = [str(path) for path in possible_paths if path.is_file()]
    env = dict(os.environ)
    if len(existing_paths) > 0:
        env["LD_PRELOAD"] = ":".join(existing_paths)
    return env


def create_build_project(vivado_bin: Path, preload: str) -> None:
    with resources.as_file(
        resources.files("demo.scripts").joinpath("create_project.tcl")
    ) as tcl_path:
        if not tcl_path.exists():
            raise FileNotFoundError(f"create_project.tcl not found: {tcl_path}")

        args = [vivado_bin, "-mode", "batch", "-nojournal", "-source", str(tcl_path)]

        if preload == "orig":
            env = _environment_with_udev_ld_preload()

        if preload == "fix":
            env = fixed_environment_with_udev_ld_preload()

        if preload == "none":
            env = os.environ

        print("LD_PRELOAD:", env.get("LD_PRELOAD", "(not set)"))
        return check_call(args, env=env)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--vivado", type=str, default=shutil.which("vivado"))
    parser.add_argument("--preload", choices=["none", "orig", "fix"], default="none")
    args = parser.parse_args()

    if not args.vivado:
        raise ValueError("vivado is required")

    vivado = Path(args.vivado).expanduser().resolve()
    if not vivado.exists():
        raise FileNotFoundError(f"vivado not found: {vivado}")

    create_build_project(vivado, args.preload)
