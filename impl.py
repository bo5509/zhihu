from flask import Flask
from flask import render_template
from flask import request, jsonify

import re
import redis

app = Flask(__name__)


def get_redis():
    redis_conf = {
        'host': '127.0.0.1',
        'port': 6379,
        'db': 0
    }
    pool = redis.ConnectionPool(host=redis_conf['host'], port=redis_conf['port'], db=redis_conf['db'])
    return redis.StrictRedis(connection_pool=pool)


redis = get_redis()


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/send/', methods=['POST'])
def send():
    email = request.form.get("email", None)
    address = request.form.get("address", None)
    address = re.sub("/answer/\d+", '', address)
    if email and address:
        redis.lpush("kindle", address + ";" + email)
        return jsonify({"code": 0})
    return jsonify({"code": 412})

