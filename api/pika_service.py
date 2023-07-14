import pika, sys, os
import json
import redis
import time
import logging
PIKA_HOST = os.getenv("PIKA_HOST","pika.pyciemss")
REDIS = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS, port=6379, decode_responses=True)

def pika_service():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=PIKA_HOST))
    channel = connection.channel()

    channel.queue_declare(queue='terarium')

    def callback(ch, method, properties, body):
        print(" [x] Received %r" % body)
        resp = json.loads(body)
        r.set(resp.get('job_id'), resp.get('progress'))


    channel.basic_consume(queue='terarium', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

