from .logger import LoggerInterface
import gevent
import urlparse
import redis as pyredis
import re
from .utils import LazyObject

try:
  # MongoKit's Connection object is just a wrapped MongoClient.
  from mongokit import Connection as MongoClient
except:
  from pymongo import MongoClient


# greenletid => Job object
_GREENLET_JOBS_REGISTRY = {}

_WORKER = None

_CONFIG = None

# Global log object, usable from all tasks
log = LoggerInterface(None, job="current")


def set_current_job(job):
  _GREENLET_JOBS_REGISTRY[id(gevent.getcurrent())] = job


def get_current_job(greenlet_id=None):
  if greenlet_id is None:
    greenlet_id = id(gevent.getcurrent())
  return _GREENLET_JOBS_REGISTRY.get(greenlet_id)


def set_current_worker(worker):
  global _WORKER
  _WORKER = worker
  set_current_config(worker.config)


def get_current_worker():
  global _WORKER
  return _WORKER


def set_current_config(config):
  global _CONFIG
  _CONFIG = config


def get_current_config():
  global _CONFIG
  return _CONFIG


def retry_current_job(**kwargs):
  get_current_job().retry(**kwargs)


def _connections_factory(attr):

  config = get_current_config()

  # Connection strings may be stored directly in config
  config_obj = config.get(attr)

  if attr == "redis":

    if type(config_obj) in [str, unicode]:

      urlparse.uses_netloc.append('redis')
      redis_url = urlparse.urlparse(config_obj)

      log.info("Connecting to Redis at %s..." % redis_url.hostname)

      redis_pool = pyredis.ConnectionPool(
        host=redis_url.hostname,
        port=redis_url.port,
        db=0,
        password=redis_url.password
      )
      return pyredis.StrictRedis(connection_pool=redis_pool)

    # Let's just assume we got a StrictRedis-like object!
    else:
      return config_obj

  elif attr.startswith("mongodb"):

    if type(config_obj) in [str, unicode]:

      (mongoAuth, mongoUsername, mongoPassword, mongoHosts, mongoDbName) = re.match(
        "mongodb://((\w+):(\w+)@)?([\w\.:,-]+)/([\w-]+)", config_obj).groups()

      log.debug("Connecting to MongoDB at %s/%s..." % (mongoHosts, mongoDbName))

      value = MongoClient(mongoHosts)[mongoDbName]
      if mongoUsername:
        value.authenticate(mongoUsername, mongoPassword)

      return value

    # Let's just assume we got a MongoDB-like object!
    else:
      return config_obj

connections = LazyObject()
connections.add_factory(_connections_factory)
del _connections_factory

