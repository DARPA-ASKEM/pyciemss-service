import pika, sys, os
import json
import redis
import time
import logging

from settings import settings

r = redis.Redis(host=settings.REDIS, port=6379, decode_responses=True)


def mock_rabbitmq_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue='simulation-status')

    def callback(ch, method, properties, body):
        print(" [x] Received %r" % body)
        resp = json.loads(body)
        r.set(resp.get('job_id'), resp.get('progress'))


    channel.basic_consume(queue='simulation-status', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
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
