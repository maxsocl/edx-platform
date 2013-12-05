import datetime

import pytz
from pytz import UTC

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect

from django_future.csrf import ensure_csrf_cookie

from edxmako.shortcuts import render_to_response

from track import tracker
from track import contexts
from track.models import TrackingLog
from eventtracking import tracker as eventtracker


def log_event(event):
    """Capture a event by sending it to the register trackers"""
    tracker.send(event)


def user_track(request):
    """
    Log when POST call to "event" URL is made by a user. Uses request.REQUEST
    to allow for GET calls.

    GET or POST call should provide "event_type", "event", and "page" arguments.
    """
    try:  # TODO: Do the same for many of the optional META parameters
        username = request.user.username
    except:
        username = "anonymous"

    try:
        scookie = request.META['HTTP_COOKIE']  # Get cookies
        scookie = ";".join([c.split('=')[1] for c in scookie.split(";") if "sessionid" in c]).strip()  # Extract session ID
    except:
        scookie = ""

    try:
        agent = request.META['HTTP_USER_AGENT']
    except:
        agent = ''

    page = request.REQUEST['page']

    with eventtracker.get_tracker().context('edx.course.browser', contexts.course_context_from_url(page)):
        event = {
            "username": username,
            "session": scookie,
            "ip": request.META['REMOTE_ADDR'],
            "event_source": "browser",
            "event_type": request.REQUEST['event_type'],
            "event": request.REQUEST['event'],
            "agent": agent,
            "page": page,
            "time": datetime.datetime.now(UTC),
            "host": request.META['SERVER_NAME'],
            "context": eventtracker.get_tracker().resolve_context(),
        }

    log_event(event)

    return HttpResponse('success')


def server_track(request, event_type, event, page=None):
    """Log events related to server requests."""
    try:
        username = request.user.username
    except:
        username = "anonymous"

    try:
        agent = request.META['HTTP_USER_AGENT']
    except:
        agent = ''

    event = {
        "username": username,
        "ip": request.META['REMOTE_ADDR'],
        "event_source": "server",
        "event_type": event_type,
        "event": event,
        "agent": agent,
        "page": page,
        "time": datetime.datetime.now(UTC),
        "host": request.META['SERVER_NAME'],
        "context": eventtracker.get_tracker().resolve_context(),
    }

    if event_type.startswith("/event_logs") and request.user.is_staff:
        return  # don't log

    log_event(event)


def task_track(request_info, task_info, event_type, event, page=None):
    """
    Logs tracking information for events occuring within celery tasks.

    The `event_type` is a string naming the particular event being logged,
    while `event` is a dict containing whatever additional contextual information
    is desired.

    The `request_info` is a dict containing information about the original
    task request.  Relevant keys are `username`, `ip`, `agent`, and `host`.
    While the dict is required, the values in it are not, so that {} can be
    passed in.

    In addition, a `task_info` dict provides more information about the current
    task, to be stored with the `event` dict.  This may also be an empty dict.

    The `page` parameter is optional, and allows the name of the page to
    be provided.
    """

    # supplement event information with additional information
    # about the task in which it is running.
    full_event = dict(event, **task_info)

    # All fields must be specified, in case the tracking information is
    # also saved to the TrackingLog model.  Get values from the task-level
    # information, or just add placeholder values.
    with eventtracker.get_tracker().context('edx.course.task', contexts.course_context_from_url(page)):
        event = {
            "username": request_info.get('username', 'unknown'),
            "ip": request_info.get('ip', 'unknown'),
            "event_source": "task",
            "event_type": event_type,
            "event": full_event,
            "agent": request_info.get('agent', 'unknown'),
            "page": page,
            "time": datetime.datetime.now(UTC),
            "host": request_info.get('host', 'unknown'),
            "context": eventtracker.get_tracker().resolve_context(),
        }

    log_event(event)


@login_required
@ensure_csrf_cookie
def view_tracking_log(request, args=''):
    """View to output contents of TrackingLog model.  For staff use only."""
    if not request.user.is_staff:
        return redirect('/')
    nlen = 100
    username = ''
    if args:
        for arg in args.split('/'):
            if arg.isdigit():
                nlen = int(arg)
            if arg.startswith('username='):
                username = arg[9:]

    record_instances = TrackingLog.objects.all().order_by('-time')
    if username:
        record_instances = record_instances.filter(username=username)
    record_instances = record_instances[0:nlen]

    # fix dtstamp
    fmt = '%a %d-%b-%y %H:%M:%S'  # "%Y-%m-%d %H:%M:%S %Z%z"
    for rinst in record_instances:
        rinst.dtstr = rinst.time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime(fmt)

    return render_to_response('tracking_log.html', {'records': record_instances})
