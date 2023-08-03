# PyCIEMSS Simulation Service

The service is a light wrapper service around [pyciemss](https://github.com/ciemss/pyciemss).
Both a FastAPI and RQ tasks are provided so jobs can be run asynchronously for long periods
of time. The service must also [conform to this spec](https://github.com/DARPA-ASKEM/simulation-api-spec).

Experimental: `sciml` engine can be chosen for `simulate`.

## Startup

To start the PyCIEMSS Simulation API, first run: 

`make init`

in order to pull the PyCIEMSS repository in as a submodule and set up the environment file from the sample file. Next run:

`make up`

to start the containers and the API. The API url will be `http://localhost:8010` by default 

## Notes

### Result Files
Every operation saves 3 files to S3
- `result.csv`
- `eval.csv` (if pyciemss engine is used)
- `visualization.json` (if pyciemss engine is used)

### RabbitMQ
Only the `calibrate` operation reports progress to RabbitMQ. This is to 
the `simulation-status` queue with a payload that looks like `{"job_id": "some string", "progress": "float between 0 and 1"}`.

The Docker Compose starts rabbitmq AND a mock consumer for the messages. The 
mock consumer is only helpful for testing without the full stack. 


## License

[Apache License 2.0](LICENSE)
