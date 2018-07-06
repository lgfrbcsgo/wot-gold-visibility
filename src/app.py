import os
import sys
import json
from io import BytesIO
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError
from rq_dashboard import default_settings as dashboard_settings, blueprint as dashboard_blueprint
from flask import Flask, send_file, request, jsonify, redirect, url_for, abort, make_response
from flask_cors import cross_origin
from flask_dance.contrib.github import make_github_blueprint, github
from werkzeug.contrib.fixers import ProxyFix
from wand.image import Image
from wand.exceptions import WandException

from mod import make_mod
from worker import conn, redis_url


# GitHub user IDs authorized to use the Queue Dashboard
AUTHORIZED_USERS = json.loads(os.environ.get('AUTHORIZED_GH_USERS', '[]'))

# Key set to dev will disable auth!
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev')

q = Queue(connection=conn)
application = Flask(__name__)

application.wsgi_app = ProxyFix(application.wsgi_app)
application.secret_key = SECRET_KEY
application.config.from_object(dashboard_settings)
application.config['REDIS_URL'] = redis_url
github_bp = make_github_blueprint(
    client_id=os.environ.get('GITHUB_OAUTH_CLIENT_ID'),
    client_secret=os.environ.get('GITHUB_OAUTH_CLIENT_SECRET')
)


@dashboard_blueprint.before_request
def check_auth():
    if SECRET_KEY == 'dev':
        return
    if not github.authorized:
        return redirect(url_for('github.login'))
    resp = github.get('/user')
    if not resp.ok or resp.json()['id'] not in AUTHORIZED_USERS:
        return abort(401)


application.register_blueprint(github_bp, url_prefix='/login')
application.register_blueprint(dashboard_blueprint, url_prefix='/rq')


@application.route('/create', methods=['POST'])
@cross_origin()
def handle_mod_request():
    file = None
    if 'file' in request.files:
        file = request.files['file'].read()

        # validate image
        if len(file) > (200 * 1024):
            return jsonify({'status': 'error', 'errorMsg': 'Image file size exceeds 200 KB!'}), 400
        try:
            with Image(blob=file) as img:
                if img.width > 512 or img.height > 512:
                    return jsonify({'status': 'error', 'errorMsg': 'Image exceeds maximum size of 512x512 pixels!'}), 400
        except WandException:
            return jsonify({'status': 'error', 'errorMsg': 'Not a valid image!'}), 400

    color = request.args.get('color')
    luminize = True if request.args.get('luminize', '') == 'true' else False
    job = q.enqueue_call(func=make_mod, args=(color, file, luminize), timeout='100s', ttl='5m', result_ttl='10s')

    return jsonify({'status': 'created', 'jobId': job.get_id()}), 200


@application.route('/status/<mod_id>', methods=['GET'])
@cross_origin()
def get_mod_status(mod_id):
    try:
        job = Job.fetch(mod_id, connection=conn)
    except NoSuchJobError:
        return jsonify({'status': 'error', 'errorMsg': 'Job not found!'}), 500
    if job.is_finished:
        return jsonify({'status': 'finished', 'jobId': mod_id}), 200
    elif job.is_queued:
        return jsonify({'status': 'created', 'jobId': mod_id}), 200
    elif job.is_started:
        return jsonify({'status': 'started', 'jobId': mod_id}), 200
    elif job.is_failed:
        return jsonify({'status': 'error', 'errorMsg': 'Job failed!'}), 500


@application.route('/download/<mod_id>', methods=['GET'])
@cross_origin()
def get_mod_result(mod_id):
    try:
        job = Job.fetch(mod_id, connection=conn)
    except NoSuchJobError:
        return '', 500

    if job.is_finished:
        result = BytesIO(job.result)
        response = make_response(send_file(result, as_attachment=True, attachment_filename='goldvisibility.color.wotmod'))
        response.headers['Content-Length'] = len(job.result)
        return response
    else:
        return '', 500


@application.route('/')
def index():
    return redirect('/rq', code=301)


if __name__ == '__main__':
    application.run(host='0.0.0.0')
