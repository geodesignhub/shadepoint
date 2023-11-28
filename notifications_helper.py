from dashboard import create_app
from flask_sse import sse
import time


def notify_shadow_complete(job, connection, result, *args, **kwargs):
    # send a message to the room / channel that the shadows is ready

    job_id = job.id + "_gdh_buildings_canopy_shadow"
    app, babel = create_app()
    with app.app_context():
        sse.publish({"shadow_key": job_id}, type="gdh_shadow_generation_success")


def shadow_generation_failure(job, connection, type, value, traceback):
    print("Job with %s failed.." % str(job.id))


def existing_buildings_notify_shadow_complete(job, connection, result, *args, **kwargs):
    # send a message to the room / channel that the shadows is ready

    job_id = job.id + "_existing_buildings_canopy_shadow"
    app, babel = create_app()
    with app.app_context():
        sse.publish(
            {"shadow_key": job_id}, type="existing_buildings_shadow_generation_success"
        )


def existing_buildings_shadow_generation_failure(
    job, connection, type, value, traceback
):
    print("Job with %s failed.." % str(job.id))


def notify_roads_download_complete(job, connection, result, *args, **kwargs):
    # send a message to the room / channel that the shadows is ready

    job_id = job.id
    app, babel = create_app()
    with app.app_context():
        time.sleep(3)
        sse.publish({"roads_key": job_id}, type="roads_download_success")

    print("Job with id %s downloaded roads data successfully.." % str(job.id))


def notify_roads_download_failure(job, connection, type, value, traceback):
    print("Job with %s failed.." % str(job.id))


def notify_gdh_roads_shadow_intersection_complete(
    job, connection, result, *args, **kwargs
):
    # send a message to the room / channel that the shadows is ready

    job_id = job.id
    app, babel = create_app()
    with app.app_context():
        sse.publish({"roads_shadow_stats_key": job_id}, type="roads_shadow_complete")

    print(
        "Job with id %s completed the shadow intersection successfully.." % str(job.id)
    )


def notify_gdh_roads_shadow_intersection_failure(
    job, connection, type, value, traceback
):
    print("Job with %s failed.." % str(job.id))


def notify_trees_download_complete(job, connection, result, *args, **kwargs):
    # send a message to the room / channel that the shadows is ready

    job_id = job.id
    app, babel = create_app()
    with app.app_context():
        time.sleep(3)
        sse.publish({"trees_key": job_id}, type="trees_download_success")

    print("Job with id %s downloaded trees data successfully.." % str(job.id))


def notify_trees_download_failure(job, connection, type, value, traceback):
    print("Job with %s failed.." % str(job.id))


def notify_buildings_download_complete(job, connection, result, *args, **kwargs):
    # send a message to the room / channel that the shadows is ready

    job_id = job.id
    app, babel = create_app()
    with app.app_context():
        sse.publish(
            {"existing_buildings_key": job_id},
            type="existing_buildings_download_success",
        )

    print("Job with id %s downloaded buildings data successfully.." % str(job.id))


def notify_buildings_download_failure(job, connection, type, value, traceback):
    print("Job with %s failed.." % str(job.id))
