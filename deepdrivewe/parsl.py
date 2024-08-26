"""Utilities to build Parsl configurations."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Literal
from typing import Sequence
from typing import Union

from parsl.config import Config
from parsl.executors import HighThroughputExecutor
from parsl.providers import LocalProvider
from pydantic import Field

from deepdrivewe.api import BaseModel


class BaseComputeConfig(BaseModel, ABC):
    """Compute config (HPC platform, number of GPUs, etc)."""

    name: Literal[''] = ''
    """Name of the platform to use."""

    @abstractmethod
    def get_parsl_config(self, run_dir: str | Path) -> Config:
        """Create a new Parsl configuration.

        Parameters
        ----------
        run_dir : str | Path
            Path to store monitoring DB and parsl logs.

        Returns
        -------
        Config
            Parsl configuration.
        """
        ...


class LocalConfig(BaseComputeConfig):
    """Local compute config."""

    name: Literal['local'] = 'local'  # type: ignore[assignment]
    max_workers: int = 1
    cores_per_worker: float = 1.0
    worker_port_range: tuple[int, int] = (10000, 20000)
    label: str = 'cpu_htex'

    def get_parsl_config(self, run_dir: str | Path) -> Config:
        """Generate a Parsl configuration for local execution."""
        return Config(
            run_dir=str(run_dir),
            strategy=None,
            executors=[
                HighThroughputExecutor(
                    address='localhost',
                    label=self.label,
                    max_workers=self.max_workers,
                    cores_per_worker=self.cores_per_worker,
                    worker_port_range=self.worker_port_range,
                    provider=LocalProvider(init_blocks=1, max_blocks=1),
                ),
            ],
        )


class WorkstationConfig(BaseComputeConfig):
    """Compute config for a workstation."""

    name: Literal['workstation'] = 'workstation'  # type: ignore[assignment]
    """Name of the platform."""
    available_accelerators: int | Sequence[str] = 8
    """Number of GPU accelerators to use."""
    worker_port_range: tuple[int, int] = (10000, 20000)
    """Port range."""
    retries: int = 1
    label: str = 'gpu_htex'

    def get_parsl_config(self, run_dir: str | Path) -> Config:
        """Generate a Parsl configuration for workstation execution."""
        return Config(
            run_dir=str(run_dir),
            retries=self.retries,
            executors=[
                HighThroughputExecutor(
                    address='localhost',
                    label=self.label,
                    cpu_affinity='block',
                    available_accelerators=self.available_accelerators,
                    worker_port_range=self.worker_port_range,
                    provider=LocalProvider(init_blocks=1, max_blocks=1),
                ),
            ],
        )


class HybridWorkstationConfig(BaseComputeConfig):
    """Run simulations on CPU and AI models on GPU."""

    cpu_config: LocalConfig = Field(
        description='Config for the CPU executor to run simulations.',
    )
    gpu_config: WorkstationConfig = Field(
        description='Config for the GPU executor to run AI models.',
    )

    def get_parsl_config(self, run_dir: str | Path) -> Config:
        """Generate a Parsl configuration for hybrid execution."""
        return Config(
            run_dir=str(run_dir),
            retries=self.gpu_config.retries,
            executors=[
                HighThroughputExecutor(
                    address='localhost',
                    label=self.cpu_config.label,
                    max_workers=self.cpu_config.max_workers,
                    cores_per_worker=self.cpu_config.cores_per_worker,
                    worker_port_range=self.cpu_config.worker_port_range,
                    provider=LocalProvider(init_blocks=1, max_blocks=1),
                ),
                HighThroughputExecutor(
                    address='localhost',
                    label=self.gpu_config.label,
                    cpu_affinity='block',
                    available_accelerators=self.gpu_config.available_accelerators,
                    worker_port_range=self.gpu_config.worker_port_range,
                    provider=LocalProvider(init_blocks=1, max_blocks=1),
                ),
            ],
        )


ComputeConfigTypes = Union[
    LocalConfig,
    WorkstationConfig,
    HybridWorkstationConfig,
]
