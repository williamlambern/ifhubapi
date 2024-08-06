from flask import Flask, send_from_directory, render_template, request,jsonify
from flask_cors import CORS, cross_origin

import os
import requests
import json

from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread
from api import *

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

api = Requester()
'''
with open('cache.json', 'r') as f:
  try:
    api.history = json.load(f)
  except:
    api.history = {}
'''
def primaryUpdate():
  api.primaryUpdate(os.getenv('IFHUBKEY'))

def secondaryUpdate():
  api.secondaryUpdate(os.getenv('IFHUBKEY'))

def updateCacheFile():
  api.updateCacheFile()

@app.route('/')
def index():
    return 'The API that powers IFHub.'

@app.route('/flights')
def flights():
  apikey = request.args.get('apikey')
  sessionid = request.args.get('sessionid')
  if apikey == os.getenv('IFHUBKEY'):
    try:
      return jsonify(api.serverFlights[sessionid])
    except:
      return 'incorrect sessionid'
  else:
    return 'access denied'

@app.route('/flightDetails')
def flightDetails():
  apikey = request.args.get('apikey')
  flightid = request.args.get('flightid')
  if apikey == os.getenv('IFHUBKEY'):
    return jsonify(api.history[flightid])

  else:
    return 'access denied'

@app.route('/getAtcFacilities')
def atcActive():
  apikey = request.args.get('apikey')
  sessionid = request.args.get('sessionid')
  if apikey == os.getenv('IFHUBKEY'):
    try:
      return jsonify(api.atc[sessionid])
    except:
      return 'incorrect sessionid'
  else:
    return 'access denied'

@app.route('/getFlightPlans')
def fpl():
  apikey = request.args.get('apikey')
  sessionid = request.args.get('sessionid')
  if apikey == os.getenv('IFHUBKEY'):
    try:
      return jsonify(api.serverFPL[sessionid])
    except:
      return 'incorrect sessionid'
  else:
    return 'access denied'

@app.route('/getWebsiteData')
def website():
  apikey = request.args.get('apikey')
  if apikey == os.getenv('IFHUBKEY'):
    return jsonify([api.numberOfFlights, api.totalDataPoints])

@app.route('/search')
def search():
  apikey = request.args.get('apikey')
  name = request.args.get('q')
  if apikey == os.getenv('IFHUBKEY'):
    if name in api.conversion:
      return jsonify({'response' : api.conversion[name], 'server' : api.flightToServer[api.conversion[name]], 'status' : api.history[api.conversion[name]][-1]['Status']})
    else:
      return jsonify({'response' : 'Invalid callsign / username'})

def run():
  app.run(host='0.0.0.0', port=8080)

sched = BackgroundScheduler(daemon=True, job_defaults={'max_instances': 2})
sched.add_job(primaryUpdate,'interval',minutes=0.5)
sched.add_job(secondaryUpdate,'interval',minutes=1.2)
#sched.add_job(updateCacheFile,'interval',minutes=2.1)
sched.start()

t = Thread(target=run)
t.start()
