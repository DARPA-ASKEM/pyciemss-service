[![Build and Publish](https://github.com/DARPA-ASKEM/service-template/actions/workflows/publish.yaml/badge.svg?event=push)](https://github.com/DARPA-ASKEM/service-template/actions/workflows/publish.yaml)

# PyCIEMSS Simulation API

## Startup

Follow the directions from NVIDIA for installing and enabling the NVIDIA container toolkit to your system. This is required to run CUDA on the container.

`https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker`

To start the PyCIEMSS Simulation API, first run: 

`make init`

in order to pull the PyCIEMSS repository in as a submodule and set up the environment file from the sample file. Next run:

`make up`

to start the containers and the API. The API url will be `http://localhost:8010` without any additional configuration changes.

## Endpoints

WIP


## License

[Apache License 2.0](LICENSE)
