# PyCIEMSS Simulation Service

The service is a light wrapper service around [pyciemss](https://github.com/ciemss/pyciemss).
Both a FastAPI and RQ tasks are provided so jobs can be run asynchronously for long periods
of time. The service must also [conform to this spec](https://github.com/DARPA-ASKEM/simulation-api-spec).

## Startup

To start the PyCIEMSS Simulation API, first run: 

`make init`

in order to pull the PyCIEMSS repository in as a submodule and set up the environment file from the sample file. Next run:

`make up`

to start the containers and the API. The API url will be `http://localhost:8010` by default 

## Notes
Every operation saves 3 files to S3
- `result.csv`
- `eval.csv`
- `visualization.json`


## License

[Apache License 2.0](LICENSE)
