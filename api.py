import os
import requests
import time
import json

# Timings list of the form

#[Spawn, Takeoff, Actual, Current Time]

class Requester:

  def __init__(self):
    self.serverFlights = {}
    self.numberOfFlights = 0
    self.totalDataPoints = 0
    self.history = {}
    self.atc = {}
    self.conversion = {}
    self.flightToServer = {}
    self.disconnected = {}
    self.planesUpdated = []
    self.previousPlanesUpdated = []
    self.strikes = {}
    self.servers = ["df2a8d19-3a54-4ce5-ae65-0b722186e44c","45173539-5080-4c95-9b93-a24713d96ec8","d01006e4-3114-473c-8f69-020b89d02884"]
    self.url = 'https://api.infiniteflight.com/public/v2/'
    print('restart')

  def primaryUpdate(self, key):
    if key == os.getenv('IFHUBKEY'):
      numberOfFlights = 0
      totalDataPoints = 0
      self.planesUpdated = []
      self.conversion = {}
      self.flightToServer = {}
      self.serverFlights = {"df2a8d19-3a54-4ce5-ae65-0b722186e44c" : [],
                            "45173539-5080-4c95-9b93-a24713d96ec8" : [],
                            "d01006e4-3114-473c-8f69-020b89d02884" : []}
      currentTime = time.time()
      min = time.gmtime(currentTime).tm_min
      sec = time.gmtime(currentTime).tm_sec
      for server in self.servers:
        data = requests.get(self.url + 'flights/{}?apikey={}'.format(server, 'pjjcwjxr9f1o0fckie5s504jlzzgvyqh')).json()['result']
        self.serverFlights[server] = data
        self.serverFlights[server][0]['timeOfRequest'] = currentTime
        numberOfFlights += len(data)
        for i in range(len(data)):
          fid = data[i]['flightId']
          self.conversion[data[i]['callsign']] = fid
          self.conversion[data[i]['username']] = fid
          self.flightToServer[fid] = server
          lat = data[i]["latitude"]
          lon = data[i]["longitude"]
          alt = data[i]["altitude"]
          speed = data[i]["speed"]
          vs = data[i]["verticalSpeed"]
          try:
            self.serverFlights[server][i]['time'] = self.history[fid][0]['Time']
          except:
            pass
          if speed < 40:
            status = 'On the ground'
          else:
            if alt < 3000:
              if vs > 500:
                status = 'Taking off'
              else:
                status = 'Landing'
            elif vs > 500:
              status = 'Climbing'
            elif vs < -500:
              status = 'Descending'
            else:
              if alt > 10000:
                status = 'At Cruise'
              else:
                status = 'On Approach'

          self.planesUpdated.append(fid)
          self.strikes[fid] = 0
          if fid in self.history:
            if status != 'On the ground':
              # Stop glitch where takeoff is denoted as a landing. Only required in this part.
              if status == 'Landing' and self.history[fid][0]['BeenInAir'] == 'No':
                status = 'Taking off'
              self.history[fid][0]['BeenInAir'] = 'Yes'

            # Now specific cases

            if status == 'On the ground' and len(self.history[fid]) > 40:
              if self.history[fid][0]['BeenInAir'] == 'No':
                self.history[fid][0]['Time'] = 'Delayed'

            if len(self.history[fid]) >= 2:
              if status == 'Taking off' and self.history[fid][-2]['Status'] == 'On the ground':
                # check for multi-leg
                if self.history[fid][0]['Timings'][1] != 0:
                    self.history[fid][0]['Timings'][0] = currentTime
                self.history[fid][0]['Timings'][1] = currentTime
                self.history[fid][0]['Timings'][2] = 0 # for multi-leg flights

              if status == 'On the ground' and self.history[fid][-2]['Status'] == 'Landing':
                self.history[fid][0]['Timings'][2] = currentTime

            addToHistory = False
            if alt < 25000:
                addToHistory = True
            else:
                if min % 2 == 0:
                    if sec >= 30:
                        addToHistory = True
            if abs(vs) > 200:
                addToHistory = True

            if addToHistory == True:
                self.history[fid][0]['Timings'][3] = currentTime
                newData = {"Altitude" : alt, "Longitude" : lon, "Latitude" :lat, "Speed" : speed, "Status" : status}
                self.history[fid].append(newData)
                totalDataPoints += len(self.history[fid])
          else:
            newData = [{"Altitude" : alt, "Longitude" : lon, "Latitude" :lat, "Speed" : speed, "Status" : status, "Time" : 'On Time', 'BeenInAir' : 'No', "Timings" : [currentTime, 0, 0, currentTime]}]
            self.history[fid] = newData
            totalDataPoints += 1

          self.serverFlights[server][i]['length'] = len(self.history[fid])

      self.numberOfFlights = numberOfFlights
      self.totalDataPoints = totalDataPoints
      self.pruneFlights()


  def secondaryUpdate(self, key):
    if key == os.getenv('IFHUBKEY'):
      for server in self.servers:
        # DEPRECATED, NOW INDIVIDUAL CALL
        data = requests.get(self.url + 'sessions/{}/world?apikey={}'.format(server, 'pjjcwjxr9f1o0fckie5s504jlzzgvyqh')).json()
        self.atc[server] = data
        self.atc[server]['Time'] = time.time()

  def pruneFlights(self):
    # add new planes to disconnected list
    for plane in self.previousPlanesUpdated:
      if plane not in self.planesUpdated:
        self.disconnected[plane] = 1
    # delete connected planes
    for plane in self.planesUpdated:
      if plane in self.disconnected:
        del self.disconnected[plane]
    # update disconnected planes
    toRemove = []
    for plane in self.disconnected:
      self.disconnected[plane] += 1
      if self.disconnected[plane] > 3:
        del self.history[plane]
        toRemove.append(plane)
    # remove disconnected planes
    for plane in toRemove:
      del self.disconnected[plane]
    # update previousPlanesUpdated
    c = []
    for plane in self.planesUpdated:
      c.append(plane)
    self.previousPlanesUpdated = c
