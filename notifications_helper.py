import os, time
from flask import current_app as app
from flask_sse import sse

def notify_shadow_complete(job, connection, result, *args, **kwargs):
    # send a message to the room / channel that the shadows is ready
    

    job_id = job.id    
    with app.app_context():
        sse.publish({"job_id": job_id}, type='diagram_shadow_success')
    
    
def shadow_generation_failure(job, connection, type, value, traceback):
    print('Job with %s failed..'% str(job.id))
