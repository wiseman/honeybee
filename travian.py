import twill.commands
import re
import urlparse
import time


def stringbegins(string, pattern):
  return len(string) >= len(pattern) and string[0:len(pattern)] == pattern


class LoginException(Exception):
  def __init__(self, message=None):
    self.message = message

  def str(self):
    return "LoginException: %s" % (self.message,)


MAX_LOGIN_TRIES = 10

class Session:

  # Creates a Travian session (but does not login).
  #
  # baseurl  - The base url for your Travian server, e.g.
  #            "http://s3.travian.com/"
  # username - Your account's username.
  # password - your account's password.
  def __init__(self, baseurl, username, password):
    self.baseURL = baseurl
    self.username = username
    self.password = password
    self.browser = twill.commands.get_browser()
    twill.commands.agent("Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en) AppleWebKit/417.9 (KHTML, like Gecko) Safari/417.8")
    self.cache_html = None
    self.cache_url = None
    self.cache_time = time.time()
    self.cache_lifetime = 120

  def get_html(self):
    if self.cache_html == None or time.time() - self.cache_time > self.cache_lifetime:
      raise "HTML cache is stale"
    return self.cache_html

  # Go to a relative URL (which will be merged with the base Travian
  # URL), and login if neccessary.
  def go(self, url, auto_login=1):
    if not self.cache_valid(url):
      self.goWithLogin(url, auto_login)
      self.cache_time = time.time()
      self.cache_url = url
      self.cache_html = self.browser.get_html()

  def cache_valid(self, url):
    if url != self.cache_url or time.time() - self.cache_time > self.cache_lifetime:
      return False
    else:
      return True

  def invalidateCache(self):
    self.cache_url = None
      
  # Used internally. Visits a URL, logging in if neccessary.
  #
  # FIXME: Doesn't actually retry failed login attempts.
  def goWithLogin(self, url, auto_login, try_count=0):
    if try_count > MAX_LOGIN_TRIES:
      print self.browser.get_html()
      raise LoginException("Unable to login after %s attempts." % (try_count,))
    fullURL = urlparse.urljoin(self.baseURL, url)
    self.browser.go(fullURL)
    if auto_login and self.atLoginPage():
      self.login()
      self.changeCity("34136")
      self.goWithLogin(url, auto_login, try_count + 1)

  def changeCity(self, id):
    self.go("dorf1.php?newdid=%s" % (id,))
    
  # Used internally.  Are we at a login page?
  def atLoginPage(self):
    html = self.browser.get_html()
    if re.compile("To login you must enable cookies").search(html) == None:
      return 0
    else:
      return 1
  
  # Used internally.  Logs us in.
  def login(self):
    try:
      print "Logging in"
      self.go("login.php", auto_login=0)
      login_form = self.browser._browser.forms()[0]
#      username_control = login_form.find_control(predicate=lambda (x): stringbegins(x.name, "name"))
#      password_control = login_form.find_control(predicate=lambda (x): stringbegins(x.name, "pw"))
      username_control = login_form.controls[2]
      password_control = login_form.controls[3]
      username_control.value = self.username
      password_control.value = self.password
      
      self.browser.submit("s1")
    except Exception, e:
      print self.browser.get_html()
      raise LoginException("Unable to login: %s" % (str(e),))
    if self.browser.get_code() != 200:
      raise LoginException("Server returned code %s." % (self.browser.get_code()),)
    if re.search("Wrong password", self.browser.get_html()):
      raise LoginException("Password incorrrect")
    
  # Launches a raid against a village.
  #
  # village_id - The target village.
  # troops     - a 10-tuple specifying the makeup of troops to send, e.g.
  #              [0, 0, 30, 0, 0, 15, 0, 0, 0, 0] would send 30
  #              Axefighters and 15 Teutonic Knights (for a Tetuonic
  #              player).
  def raidVillage(self, village_id, troops):
    self.go("a2b.php?z=%s" % (village_id,))
    attack_form = self.browser._browser.forms()[0]
    for i in range(1, 10):
      attack_form["t%s" % (i,)] = "%s" % (troops[i - 1],)
      attack_form["c"] = ["4",] # 4 ==raid
    self.browser.submit("s1")
    self.browser.submit("s1")

  def getVillageAlliance(self, village_id):
    self.go("karte.php?d=%s" % (village_id,))
    html = self.get_html()
    regex_str = "<td>Alliance:</td><td><a href=.allianz.php.aid=([0-9]+).>.*</a></td>"
    regex = re.compile(regex_str, re.MULTILINE)
    match = regex.search(html)
    if (match == None):
      return None
    else:
      return match.group(1)

  # Queries current troop levels in the barracks (troops that are in
  # their home village, neither on their way to an attack nor on their
  # way back).  The result is a 10-tuple interpreted the same way as
  # the tuple passed to raidVillage.
  #
  # FIXME: This function will only work for Teutons.
  def getTroopLevels(self):
    self.go("dorf1.php")
    html = self.get_html()
    return parse_troop_levels(html)

  def getFoodLevel(self):
    if not (self.cache_valid("dorf1.php") or self.cache_valid("dorf2.php")):
      self.go("dorf1.php")
    html = self.get_html()
    return parse_food_level(html)

  def determineMarketHex(self):
    self.go("dorf2.php")
    html = self.get_html()
    regex_str = "<area href=.build.php.id=([0-9]+). title=.Marketplace"
    regex = re.compile(regex_str, re.MULTILINE)
    match = regex.search(html)
    if match == None:
      return 0
    else:
      return match.group(1)

  def sendResources(self, resources, coords):
    print "sending resources %s to %s" % (resources, coords)
    marketHex = self.determineMarketHex()
    if marketHex != 0:
      self.go("build.php?id=%s" % (marketHex))
      merchant_form = self.browser._browser.forms()[0]
      merchant_form["x"] = str(coords[0])
      merchant_form["y"] = str(coords[1])
      for i in range(1, 5):
        merchant_form["r%s" % (i,)] = str(resources[i - 1])
      self.browser.submit("s1")
      self.browser.submit("s1")

  # Queries the earliest time at which troops returning from attacks
  # ("Reinf.", as Travian reports it) will arrive back at their home
  # base and returns the result as the number of seconds until their
  # return.  If no troops happen to be returning from attacks -1 will
  # be returned.
  #
  # If all your troops are at home or on their way to an attack, this
  # will return -1.
  def getTimeUntilNextReinforcement(self):
    self.go("dorf1.php")
    html = self.get_html()
    return parse_next_reinforcement_time(html)


def parse_food_level(html):
  regex_str = "<img.*title=.Crop.></td>\n<td id=l4 title=.*>([0-9]+)/[0-9]+</td>"
  regex = re.compile(regex_str, re.MULTILINE)
  match = regex.search(html)
  if (match == None):
    return 0
  else:
    return int(match.group(1))
  
  
def parse_troop_level(name, html):
  regex_str = "<b>([0-9]+)</b></td><td>%s" % (name,)
  regex = re.compile(regex_str, re.MULTILINE)
  match = regex.search(html)
  if (match == None):
    return 0
  else:
    return match.group(1)
  
def parse_troop_levels(html):
  troop_levels = []
  for troop in ("Clubswinger", "Spearfighter", "Axefighter", "Scout", "Paladin", "Teuton Knight", "Ram", "Catapult", "Chief", "Settler"):
    troop_levels.append(int(parse_troop_level(troop, html)))
  return troop_levels

def parse_next_reinforcement_time(html):
  regex = re.compile("Reinf.*?([0-9]+):([0-9]+):([0-9]+)")
  match = regex.search(html.replace("\r", " ").replace("\n", " "))
  if (match == None):
    return -1
  else:
    return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))
                     
def parse_server_time(html):
  regex = re.compile("""Servertime: <b><span id=tp1>([0-9:]+)</span>""")
  timetuple = time.strptime(regex.search(html).group(1), "%H:%M:%S")
  timetuple = (time.localtime()[0],) + timetuple[1:]
  return time.mktime(timetuple)


UnitCarryingCapacities = [60, 40, 50, 0, 110, 80, 0, 0, 0, 1600]

