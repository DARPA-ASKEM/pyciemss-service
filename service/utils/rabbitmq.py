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


def gen_rabbitmq_hook(job_id):
    connection = pika.BlockingConnection(
        conn_config,
    )
    channel = connection.channel()

    def hook(progress, loss):
        channel.basic_publish(
            exchange="",
            routing_key="simulation-status",
            body=json.dumps(
                {"job_id": job_id, "progress": progress, "loss": str(loss)}
            ),
        )

    return hook
