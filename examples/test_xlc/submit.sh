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

# Load the required modules
module load Miniforge/24.7.1-2 

# Change to working directory
cd /thfs3/home/sysu__netlab/xlc_DL_lab/packages/deepdrivewe
mamba activate deepdrivewe

echo "start run the example"
python -m deepdrivewe.examples.test_xlc.main