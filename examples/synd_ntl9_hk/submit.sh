#!/bin/bash
#SBATCH -J idev1
#SBATCH -o idev1.o%j
#SBATCH -N 4
#SBATCH --ntasks-per-node=1
#SBATCH -p gh-dev
#SBATCH -t 00:60:00
#SBATCH -A ASC24062
#------------------------------------------------------
# Source the bashrc to add conda
source ~/.bashrc 

# chmod +x /thfs3/home/sysu__netlab/xlc_DL_lab/packages/deepdrivewe/examples/openmm_ntl9_ddwe_vista/submit.sh
# Load the required modules
module load Miniforge/24.7.1-2 GCC/9.3.0 mpich/mpi-x-gcc9.3.0 hdf5/1.12.0-gcc9.3.0-mpi-x proxy/proxy

# Change to working directory
cd /thfs3/home/sysu__netlab/xlc_DL_lab/packages/deepdrivewe
mamba activate deepdrivewe

# Get the config file for this example
CONFIG_FILE=/thfs3/home/sysu__netlab/xlc_DL_lab/packages/deepdrivewe/examples/synd_ntl9_hk/config.yaml

# Run the example
echo "start run the example"
python -m deepdrivewe.examples.synd_ntl9_hk.main --config $CONFIG_FILE
