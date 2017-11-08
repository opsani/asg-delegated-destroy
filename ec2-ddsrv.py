#!/usr/bin/python
"""
# Copyright (c) 2017, Opsani.

EXAMPLE server process that implements 'delegated termination' API for use with
the ec2-asg plugin.

To use this server, install:
- python 2.7
- web.py (e.g., apt-get install python-webpy)
- Amazon boto3 for Python2 (pip install boto3,
  on newer OS-es apt-get install python-boto3 should work, too)

Run it like this:
python ec2-dd.py [host:port]

The default for host:port is localhost:8000.

The server expects that access to the EC2 API is configured, either by running
it on an EC2 instance with an appropriate role set up, or by having a file
~/.aws/credentials with the necessary keys.

The supplied Dockerfile can be used to package the server as a container.
IMPORTANT: See README for info on running this in a container.

"""

from __future__ import print_function

import sys
import os
import signal

import boto3
import botocore.exceptions # $#!+, not easily accessible via boto3

import web
import web.httpserver

try:
    import simplejson as json
except ImportError:
    import json
_json_dec = json.JSONDecoder().decode

# === boto client setup
sessions = {}
def clt(n,region_name):
    s = sessions.get(region_name)
    if not s:
        s = boto3.session.Session(region_name=region_name)
        sessions[region_name] = s
    return s.client(n)

# === signal handlers
def sigchld(s,f):
    """reap status of forked processes"""
    while True:
        try:
            pid, c = os.waitpid(-1, os.WNOHANG)
        except OSError as e:
            if e.errno != 10: # 'No child processes'
               raise
            pid = 0
        if pid == 0:
            return
        print("child {} completed, status={}".format(pid,os.WEXITSTATUS(c)), file=sys.stderr)

def sigterm(s,f):
    raise SystemExit

# === remote request handlers
def handle_post():
    data = web.data()
    try:
        data = _json_dec(data)
    except Exception:
        raise web.badrequest('invalid json data')
    if not isinstance(data, dict):
        raise web.badrequest('input data should be a JSON object')
    reg = data.get('ec2_region','us-east-1')
    ec2 = clt('ec2',reg)
    inst_lst = data.get("ec2_instance_ids")
    if not inst_lst:
        inst_lst = data.get("ec2_instance_id")
        if not inst_lst: raise  web.badrequest('no instances in the request dat')
        inst_lst = [inst_lst]

    # destroy the instance(s) after 10sec
    if os.fork() == 0:
        import time
        time.sleep(10)
        try:
            ec2.terminate_instances(InstanceIds=inst_lst)
        except Exception as e: # TODO: trap only boto exc
            print('terminate instances failed: '+repr(e),file=sys.stderr)
            sys.stderr.flush()
            os._exit(1) # don't use sys.exit() here, we don't want the SystemExit handlers from the parent process
        os._exit(0)
    else:
        print('terminating {} in 10s'.format(repr(inst_lst)), file=sys.stderr)

    # reply with empty text
    v = b""
    web.header("Content-length", str(len(v)))
    web.header("Content-type","text/plain")
    return v

def handle_get():
    v = b""
    web.header("Content-length", str(len(v)))
    web.header("Content-type","text/plain")
    return v

# === web.py setup

# we give instances of this to web.py as the 'handler class'
# An instance of wpy_handler is callable (and returns itself), so that
# it behaves like a 'class constructor'
class _wpy_handler(object):
    def __init__(self):
        pass

    def __call__(self):
        return self
    # GET, POST and other methods will be set dynamically, using setattr, so they aren't 'bound methods', but regular functions

handler = _wpy_handler()
setattr(handler, 'GET', handle_get)
setattr(handler, 'POST', handle_post)

bind_host = 'localhost'
bind_port = 8000
web.config.debug = False

if __name__ == "__main__":
    # === cmd line arg
    if len(sys.argv)>1:
        a = sys.argv[1].split(':')
        if len(a) != 2:
            print("invalid argument, host:port expected",file=sys.stderr)
            sys.exit(2)
        bind_host = a[0]
        try:
            bind_port = int(a[1])
        except ValueError:
            print("{} is not integer".format(repr(a[1])),file=sys.stderr)
            sys.exit(2)

    # === signals
    # set up SIGCHLD handler
    signal.signal(signal.SIGCHLD,sigchld)
    # set up SIGTERM handler (raise SystemExit, to stop the server gracefully on kill())
    signal.signal(signal.SIGTERM,sigterm)

    # === set up http server
    dtbl = [ "/delayed-termination", "handler" ]
    app = web.application(dtbl, globals(), autoreload=False)
    #TODO (cosmetic): add nicer custom handlers for various errors:
    #app.notfound = _NotFound
    #app.internalerror = _InternalError

    # create a basic un-improved server, don't use api.run() - it adds a lot of stuff we don't want
    func = app.wsgifunc()
    server = web.httpserver.WSGIServer((bind_host, bind_port), func)

    # === run
    try:
        server.start()
    except (KeyboardInterrupt, SystemExit):
        server.stop()
