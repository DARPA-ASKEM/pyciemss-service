import pika, sys, os
import json
import redis
import time
import logging

from settings import settings

def mock_rabbitmq_consumer():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue='simulation-status')

    def callback(ch, method, properties, body):
        resp = json.loads(body)
        logging.info("job_id:%s; progress:%s", resp['job_id'], resp['progress'])


    channel.basic_consume(queue='simulation-status', on_message_callback=callback, auto_ack=True)

    logging.info(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


def gen_rabbitmq_hook(job_id):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
    channel = connection.channel()

    def hook(progress):
        channel.basic_publish(
            exchange='',
            routing_key='simulation-status',
            body=json.dumps({"job_id":job_id, "progress":progress})
        )
    return hook
