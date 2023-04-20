# KiloOSF

## Prerequisites
* OS: Ubuntu 20.04.2 LTS
* GPU: >= NVIDIA GTX 1080 Ti with >= 460.73.01 driver
* Python package manager `conda`

## Setup
```
conda env create -f environment.yml
source activate kiloosf-env
```

## CUDA extension installation
please make a copy of [cuda](https://github.com/creiser/kilonerf/tree/master/cuda) in the root directory of this repo and follow the steps in [CUDA extension installation](https://github.com/creiser/kilonerf).

## Usage

To train a model yourself run
`bash train.sh`

To test a trained model on the testing set, run
`bash benchmark.sh`

To render spiral demo, run
`bash demo.sh`

You can adjust the dataset by setting the dataset variable in the respective script.

## Acknowledgement

Part of our code is derived from [kilenerf](https://github.com/creiser/kilonerf), thanks to the authors for the great works.
