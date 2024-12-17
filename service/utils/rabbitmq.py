import pika
import json
import time
import logging

from settings import settings

creds = pika.PlainCredentials(settings.RABBITMQ_USERNAME, settings.RABBITMQ_PASSWORD)

if settings.RABBITMQ_SSL:
    conn_config = pika.URLParameters(
        "amqps://"
        + settings.RABBITMQ_USERNAME
        + ":"
        + settings.RABBITMQ_PASSWORD
        + "@"
        + settings.RABBITMQ_HOST
        + ":"
        + str(settings.RABBITMQ_PORT)
        + "/"
    )
else:
    conn_config = pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=creds
    )


def mock_rabbitmq_consumer():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    # TODO: Conditionally start on status of rabbitmq
    time.sleep(10)
    connection = pika.BlockingConnection(conn_config)
    channel = connection.channel()

    channel.queue_declare(queue="simulation-status")

    def callback(ch, method, properties, body):
        resp = json.loads(body)
        logging.info(
            "job_id:%s; progress:%s; loss:%s",
            resp["job_id"],
            resp["progress"],
            resp["loss"],
        )

    channel.basic_consume(
        queue="simulation-status", on_message_callback=callback, auto_ack=True
    )

    logging.info(" [*] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()


def gen_calibrate_rabbitmq_hook(job_id):
    def get_new_rabbit_conn():
        connection = pika.BlockingConnection(
            conn_config,
        )
        return connection

    # FIXME: https://github.com/DARPA-ASKEM/pyciemss-service/issues/128 Nasty temp hack to get around weird test setup that depends on connection to fail
    conn_dummy = get_new_rabbit_conn()
    conn_dummy.close()

    def hook(progress, loss):
        conn = get_new_rabbit_conn()
        channel = conn.channel()
        channel.basic_publish(
            exchange="",
            routing_key="simulation-status",
            body=json.dumps(
                {
                    "job_id": job_id,
                    "type": "calibrate",
                    "progress": progress,
                    "loss": str(loss),
                }
            ),
        )
        conn.close()

    return hook


class OptimizeHook:
    def __init__(self, job_id, total_possible_iterations):
        connection = pika.BlockingConnection(
            conn_config,
        )
        self.channel = connection.channel()
        self.job_id = job_id
        self.type = "optimize"
        self.result = []
        self.step = 0
        self.total_possible_iterations = total_possible_iterations

    def __call__(self, current_results):
        self.step += 1
        self.channel.basic_publish(
            exchange="",
            routing_key="simulation-status",
            body=json.dumps(
                {
                    "job_id": self.job_id,
                    "progress": self.step,
                    "type": self.type,
                    "current_results": current_results.tolist(),
                    "total_possible_iterations": self.total_possible_iterations,
                }
            ),
        )
