#!/usr/bin/python

import travian
import time
import os
import sys
import getopt
from sets import Set

import socket
import mechanize
import httplib
import urllib2
import random

SOFT_RESERVE=1
HARD_RESERVE=2

def addv(va, vb):
  vc = []
  for i in range(0, len(va)):
    vc.append(va[i] + vb[i])
  return vc

def vequal(va, vb):
  for i in range(0, len(va)):
    if va[i] != vb[i]:
      return 0
  return 1

def subv(a, b):
  return addv(a, multv(b, -1))

def multv(v, s):
  vc = []
  for i in range(0, len(v)):
    vc.append(v[i] * s)
  return vc

def maxv(v, s):
  vc = []
  for i in range(0, len(v)):
    vc.append(max(v[i], s))
  return vc

def troops_more_than(a, b):
  for i in range(0, 10):
    if a[i] < b[i]:
      return 0
  return 1


class Swarm:
  def __init__(self, baseurl, username, password, targetfile, stopfile=None, raid_sound=None):
    self.travian = travian.Session(baseurl, username, password)
#    self.travian.browser.load_cookies("cookies")
    self.loadTargetFile(targetfile)
    if stopfile != None:
      self.loadStopFile(stopfile)
    else:
      self.stopList = []
    self.loadHistoryFile()
    self.raidSound = raid_sound
#    self.softReserve = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#    self.hardReserve = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    self.softReserve = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    self.hardReserve = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    self.raidingParties = [
      [0, 0, 30, 0, 0, 0, 0, 0, 0, 0],  # 60 Axefighers
      [0, 30, 0, 0, 0, 0, 0, 0, 0, 0],  # 60 Spearfighters
      [0, 0, 0, 0, 10, 0, 0, 0, 0, 0],  # 4 Paladins
      [0, 0, 0, 0, 0, 10, 0, 0, 0, 0]   # 5 Teuton Knights
      ]
    self.old_food_level = 60000
    self.lastAttacked = None
    self.lastTroopLevels = None
    self.potentiallyInvalidTargets = Set()
    self.farms = [80332, 95532, 102252, 100721, 83354, 32891, 79102, 73978, 100537, 87909]
                  

  def getRaidingParty(self, troops, reserve=SOFT_RESERVE):
    # First determine what kind of reserve to keep.
    reserve_troops = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    if reserve == SOFT_RESERVE:
      reserve_troops = self.softReserve
    elif reserve == HARD_RESERVE:
      reserve_troops == self.hardReserve
    troops = maxv(subv(troops, reserve_troops), 0)

    # Now our potential troop pool against defined raiding parties.
    for raiding_party in self.raidingParties:
      print [troops, raiding_party]
      if troops_more_than(troops, raiding_party):
        return raiding_party
    return None

  def loadTargetFile(self, path):
    file = open(path, "r")
    line = file.readline()
    targets = []
    while line != "":
      targets.append(int(line))
      line = file.readline()
    self.targets = targets
    file.close()

  def loadStopFile(self, path):
    file = open(path, "r")
    line = file.readline()
    targets = []
    while line != "":
      targets.append(int(line))
      line = file.readline()
    self.stopList = targets
    file.close()

  def loadHistoryFile(self):
    try:
      file = open("honeybee.history", "r")
      self.history = eval(file.read())
      file.close()
    except Exception, e:
      warn("Unable to open history file 'honeybee.history': %s" % (str(e),))
      self.history = {}
      
  def saveHistory(self):
    try:
      file = open("honeybee.history", "w")
      file.write(str(self.history))
      file.close()
    except:
      warn("Unable to save history file 'honeybee.history")

  # Sends out as many troops as possible to raid targets.
  def sendAllTroops(self):
    time.sleep(5)
    print "Sending toops"
    troops = self.travian.getTroopLevels()
    print "Have %s troops." % (troops,)
    raiding_party = self.getRaidingParty(troops)
    if raiding_party == None:
      print "Insufficient troops for raiding party."
    else:
      if self.lastTroopLevels != None:
        if vequal(self.lastTroopLevels, troops):
          print "%s may be an invalid target" % (self.lastAttacked,)
          self.potentiallyInvalidTargets.add(self.lastAttacked)
          print "list of potentially invalid targets: %s" % (self.potentiallyInvalidTargets,)
      self.lastTroopLevels = troops
      target = self.getNextTarget()
      target_alliance = self.travian.getVillageAlliance(target)
      if (self.travian.getVillageAlliance(target) != "0"):
        print "Village %s is a member of alliance %s, aborting attack." % (target, target_alliance)
        self.stopList = self.stopList + [target,]
      else:
        self.raidVillage(target, raiding_party)
      self.sendAllTroops()

  # Waits to have enough troops to send out on raids.
  def waitForTroops(self):
    print "Checking troop levels."
    self.travian.invalidateCache()
    troops = self.travian.getTroopLevels()
    if self.getRaidingParty(troops) == None:
      delay = min(1800, self.travian.getTimeUntilNextReinforcement())
      if delay == -1:
        delay = 1800
      print "%s Waiting %s s for reinforcements." % (time.strftime("%H:%M:%S"), delay)
      time.sleep(delay + 3)
      self.waitForTroops()

  def raidVillage(self, target, troops):
    print "Launching raid against village %s." % (target,)
    if self.raidSound != None:
      os.system("open %s" % (self.raidSound,))
    self.travian.raidVillage(target, troops)
    self.recordAttack(target)

  def recordAttack(self, target):
    self.history[target] = time.mktime(time.localtime())
    self.saveHistory()
    self.lastAttacked = target

  def getNextTarget(self):
    oldest_target = 0
    oldest_time = -1
    for target in self.targets:
      if (not target in self.stopList) and (not target in self.potentiallyInvalidTargets):
        if not self.history.has_key(target):
          print "Village %s has not been raided." % (target,)
          return target
        else:
          if self.history[target] < oldest_time or oldest_time == -1:
            oldest_target = target
            oldest_time = self.history[target]
    print "Village %s has not been raided in %s seconds." % (oldest_target, time.mktime(time.localtime()) - oldest_time)
    return oldest_target

  def ensureFood(self):
    currentFoodLevel = self.travian.getFoodLevel()
    print "old food level: %s  current food level: %s" % (self.old_food_level, currentFoodLevel)
    if ((self.old_food_level >= 50000) and (currentFoodLevel < 50000)) or (currentFoodLevel < 5000):
      print "Low on food, having merchants sent."
      random.shuffle(self.farms)
      for farm in self.farms[0:2]:
        try:
          self.sendFoodFrom(farm, 10000)
        except:
          print "Sending food didn't work, oh well."
          pass
    else:
      print "Food %s is ok." % (currentFoodLevel,)
    self.old_food_level = currentFoodLevel

  def sendFoodFrom(self, farm, amount):
    self.travian.changeCity(farm)
    self.travian.sendResources([0, 0, 0, 10000], [210, 7])
    self.travian.changeCity("34136")

  def gather(self):
    errorCount = 0
    while errorCount <= 100:
      try:
        self.ensureFood()
        self.waitForTroops()
        self.sendAllTroops()
        errorCount = 0
      except (socket.error, mechanize._mechanize.BrowserStateError, httplib.BadStatusLine, urllib2.URLError):
        errorCount = errorCount + 1
        sleepTime = errorCount * 5;
        sys.stderr.write("Got exception, waiting %s seconds to retry." % (sleepTime,))
        time.sleep(sleepTime)


def warn(message):
  print "Warning: %s" % (message,)
  


class HoneybeeApp:
  def usage(self):
    print "Usage: %s [--sound=<soundfile>] <url> <username> <password>" % (sys.argv[0],)

  def run(self):
    try:
      opts, args = getopt.getopt(sys.argv[1:], "", ["soundfile="])
    except getopt.GetoptError:
      self.usage()
      sys.exit(1)

    if len(args) != 4:
      self.usage()
      sys.exit(1)

    soundFile = None
    for option, value in opts:
      if option == "--soundfile":
        soundFile = value
      else:
        warn("Unknown option '%s'." % (option,))
        self.usage()
        sys.exit(1)

    swarm = Swarm(args[0], args[1], args[2], args[3], soundFile)
    swarm.gather()


#if __name__ == "__main__":
 # app = HoneybeeApp()
  #app.run()
  
      
