import os, time
from flask_socketio import SocketIO, emit


def notify_shadow_complete(job, connection, result, *args, **kwargs):
    # send a message to the room / channel that the shadows is ready
    
    redis_url = os.getenv('REDIS_URL','redis://')
    socketio = SocketIO(message_queue = redis_url)
    job_id = job.id    
    
    time.sleep(2)
    socketio.emit('message_from_server',{'message':'Diagram shadow generated', 'shadow_key':job_id})
    
    
def shadow_generation_failure(job, connection, type, value, traceback):
    print('Job with %s failed..'% str(job.id))
