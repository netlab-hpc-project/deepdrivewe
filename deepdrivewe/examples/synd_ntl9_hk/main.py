"""WESTPA example.

Adapted from:
https://github.com/westpa/westpa2_tutorials/tree/main/tutorial7.7-hamsm
"""

from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser
from functools import partial
from functools import update_wrapper
from pathlib import Path

from colmena.queue.python import PipeQueues
from colmena.task_server import ParslTaskServer
from proxystore.connectors.file import FileConnector
from proxystore.store import Store
from pydantic import Field
from pydantic import field_validator

from deepdrivewe import BaseModel
from deepdrivewe import BasisStates
from deepdrivewe import EnsembleCheckpointer
from deepdrivewe import TargetState
from deepdrivewe import WeightedEnsemble
from deepdrivewe.examples.synd_ntl9_hk.inference import InferenceConfig
from deepdrivewe.examples.synd_ntl9_hk.inference import run_inference
from deepdrivewe.parsl import ComputeConfigTypes
from deepdrivewe.simulation.synd import run_simulation
from deepdrivewe.simulation.synd import SynDBasisStateInitializer
from deepdrivewe.simulation.synd import SynDConfig
from deepdrivewe.workflows.westpa import WESTPAThinker


class ExperimentSettings(BaseModel):
    """Provide a YAML interface to configure the experiment."""

    output_dir: Path = Field(
        description='Directory in which to store the results.',
    )
    num_iterations: int = Field(
        ge=1,
        description='Number of iterations to run the weighted ensemble.',
    )
    basis_states: BasisStates = Field(
        description='The basis states for the weighted ensemble.',
    )
    target_states: list[TargetState] = Field(
        description='The target threshold for the progress coordinate to be'
        ' considered in the target state.',
    )
    simulation_config: SynDConfig = Field(
        description='Arguments for the simulation.',
    )
    inference_config: InferenceConfig = Field(
        description='Arguments for the inference.',
    )
    compute_config: ComputeConfigTypes = Field(
        description='Settings for the compute resources.',
    )

    @field_validator('output_dir')
    @classmethod
    def mkdir_validator(cls, value: Path) -> Path:
        """Resolve and make the output directory."""
        value = value.resolve()
        value.mkdir(parents=True, exist_ok=True)
        return value


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', required=True)
    args = parser.parse_args()
    cfg = ExperimentSettings.from_yaml(args.config)
    cfg.dump_yaml(cfg.output_dir / 'params.yaml')

    # Set up logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler(cfg.output_dir / 'runtime.log'),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Make the store
    store = Store(
        name='file-store',
        register=True,
        connector=FileConnector(store_dir=str(cfg.output_dir / 'proxy-store')),
    )

    # Make the queues
    queues = PipeQueues(
        serialization_method='pickle',
        topics=['simulation', 'inference'],
        proxystore_name='file-store',
        proxystore_threshold=10000,
    )

    # Define the parsl configuration (this can be done using the
    # get_parsl_config for common use cases or by defining your own config.)
    parsl_config = cfg.compute_config.get_parsl_config(
        cfg.output_dir / 'run-info',
    )

    # Create the checkpoint manager
    checkpointer = EnsembleCheckpointer(output_dir=cfg.output_dir)

    # Check if a checkpoint exists
    checkpoint = checkpointer.latest_checkpoint()

    if checkpoint is None:
        # Initialize the weighted ensemble
        ensemble = WeightedEnsemble(
            basis_states=cfg.basis_states,
            target_states=cfg.target_states,
        )

        # Setup the basis state initializer
        basis_state_initializer = SynDBasisStateInitializer(
            cfg.simulation_config,
        )

        # Initialize the simulations with the basis states
        ensemble.initialize_basis_states(basis_state_initializer)
    else:
        # Load the ensemble from a checkpoint if it exists
        ensemble = checkpointer.load(checkpoint)
        logging.info(f'Loaded ensemble from checkpoint {checkpoint}')

    # Print the input states
    logging.info(f'Basis states: {ensemble.basis_states}')
    logging.info(f'Target states: {ensemble.target_states}')

    # Assign constant settings to each task function
    my_run_simulation = partial(
        run_simulation,
        config=cfg.simulation_config,
        output_dir=cfg.output_dir / 'simulation',
    )
    my_run_inference = partial(
        run_inference,
        basis_states=ensemble.basis_states,
        target_states=ensemble.target_states,
        config=cfg.inference_config,
    )
    update_wrapper(my_run_simulation, run_simulation)
    update_wrapper(my_run_inference, run_inference)

    # Create the task server
    doer = ParslTaskServer(
        [my_run_simulation, my_run_inference],
        queues,
        parsl_config,
    )

    # Create the workflow thinker
    thinker = WESTPAThinker(
        queue=queues,
        result_dir=cfg.output_dir / 'result',
        ensemble=ensemble,
        checkpointer=checkpointer,
        num_iterations=cfg.num_iterations,
    )
    logging.info('Created the task server and task generator')

    try:
        # Launch the servers
        doer.start()
        thinker.start()
        logging.info('Launched the servers')

        # Wait for the task generator to complete
        thinker.join()
        logging.info('Task generator has completed')
    finally:
        queues.send_kill_signal()

        # Wait for the task server to complete
        doer.join()

        # Clean up proxy store
        store.close()
