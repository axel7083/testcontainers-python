from dataclasses import dataclass
from logging import getLogger
from os import PathLike, path
from subprocess import CompletedProcess, CalledProcessError, run as subprocess_run
from types import TracebackType
from typing import Optional, Union
import re

logger = getLogger(__name__)

def parse_kube_play_stdout(stdout: str) -> dict[str, list[str]]:
    pattern = re.compile(r"(^.+?):\n((?:[a-f0-9]+\n?)*)", re.MULTILINE)
    result = {}
    for key, values in pattern.findall(stdout):
        # split values by newline, remove empties
        value_list = [v for v in values.strip().splitlines() if v]
        result[key] = value_list
    return result

@dataclass
class KubePlay:
    kube_play_file: Union[str, PathLike[str]]
    context: Optional[str] = None
    podman_command_path: str = "podman"
    build: bool = False
    keep_volumes: bool = False
    replace: bool = False


    _pods: Optional[list[str]] = None

    def __enter__(self) -> "KubePlay":
        self.start()
        return self

    def __exit__(
        self, exc_type: Optional[type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self.stop(force=not self.keep_volumes)

    def start(self) -> None:
        start_cmd = [self.podman_command_path, "kube", "play", str(self.kube_play_file)]

        # build means modifying the up command
        if self.build:
            start_cmd.append("--build")

        if self.replace:
            start_cmd.append("--replace")

        result = self._run_command(cmd=start_cmd)
        if result.returncode != 0:
            raise RuntimeError(f"Podman command failed with exit code {result.returncode}")

        info = parse_kube_play_stdout(result.stdout.decode("utf-8"))
        self._pods = info['Pod']


    def stop(self, force: bool = False) -> None:
        down_cmd = [self.podman_command_path, "kube", "down", self.kube_play_file]

        if force:
            # Tear down the volumes linked to the PersistentVolumeClaims as part of --down
            down_cmd.append("--force")

        self._run_command(cmd=down_cmd)
        self._pods = None

    def get_pods(self) -> list[str]:
        return self._pods if self._pods is not None else []

    def _run_command(
        self,
        cmd: Union[str, list[str]],
    ) -> CompletedProcess[bytes]:
        context =  self.context if self.context else path.dirname(self.kube_play_file)
        try:
            return subprocess_run(
                cmd,
                capture_output=True,
                check=True,
                cwd=context,
            )
        except CalledProcessError as e:
            logger.error(f"Command '{e.cmd}' failed with exit code {e.returncode}")
            logger.error(f"STDOUT:\n{e.stdout.decode(errors='ignore')}")
            logger.error(f"STDERR:\n{e.stderr.decode(errors='ignore')}")
            raise e from e