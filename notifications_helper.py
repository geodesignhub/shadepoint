from dashboard import create_app
from flask_sse import sse

def notify_shadow_complete(job, connection, result, *args, **kwargs):
    # send a message to the room / channel that the shadows is ready
    

    job_id = job.id  
    app = create_app()      
    with app.app_context():
        sse.publish({"shadow_key": job_id}, type='diagram_shadow_success')
        
def shadow_generation_failure(job, connection, type, value, traceback):
    print('Job with %s failed..'% str(job.id))
