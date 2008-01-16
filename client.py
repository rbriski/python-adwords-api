#!/usr/local/bin/python
#
# Originally started from Google's adwords-client.py
# but it's been changed pretty significantly since then.
#

"""pyadwords-client: A python client for the AdWords API

   AdWordsClient: Encapsulates all AdWords services and headers
"""

import os
import distutils.dir_util
import urllib
import SOAPpy

class AdWordsClient(object):
  """ Provides quick easy access to the Google AdWords API"""


  # A list of all services that will be loaded from the
  # AdWords API

  services = (
    'Account',
    'AdGroup',
    'Ad',
    'Campaign',
    'Criterion',
    #'Info',
    #'KeywordTool',
    'Report'
    #'SiteSuggestion',
    #'TrafficEstimator'
    )

  def __init__(self,
               email=None,
               password=None,
               developer_token=None,
               application_token=None,
               user_agent=None,
               client_email=None,
               server='https://adwords.google.com',
               version='v11',
               cache_dir='/tmp'):
    """ Creates a client object
    
    Args:
      email: string (optional) The <email> element.
      password: string (optional) The <password> element.
      developer_token: string (optional) The <developerToken> element.
      application_token: string (optional) The <applicationToken> element.
      user_agent: string (optional) The <useragent> element.
      client_email: string (optional) The <clientEmail> element.
      server: string (optional) API server to use.
      version: string (optional) Version of the API to use.
      cache_dir: string (optional) Directory in which WSDLs will be cached.
      """

    self.email = email
    self.password = password
    self.developer_token = developer_token
    self.application_token = application_token
    self.user_agent = user_agent
    self.__client_email = client_email
    self.server = server
    self.version = version
    self.cache_dir = cache_dir
  
    self.buildServices()
          

  def __SetClientEmail(self, email):
    """ Sets the client_email header and rebuilds the header
    
    Args:
      email: string
      """
    self.__client_email = email
    self.buildServices()

  def __GetClientEmail(self):
    """ Gets the client_email header
    
    Returns:
      string
    """
    return self.__client_email

  client_email = property(__GetClientEmail, __SetClientEmail,
                            doc = """Get or set client_email header""")

  def expectsList(self, fn):
    """Decorator that guarantees that the
    return value of a function is a list
    
    Args:
      fn: function
    Returns:
      function
      """
    def returnList(*args, **kwargs):
      out = fn(*args, **kwargs)

      #Quack, quack: duck typing
      if not hasattr(out, 'reverse'):
        if not hasattr(out, 'id'):
          #Empty return? Return an empty list
          return []
        #Single return element? Return it in a list
        return [out]
      #Otherwise, it must already be a list
      return out
    return returnList
    
  def buildServices(self):
    """Loads all API methods into this module.  Wraps all methods
    that need to return a list with *expectsList*
    
    """
    for service in AdWordsClient.services:
      fullName = "%sService" % service
      wsdlLoc = self.getServiceLocation(fullName, wsdl=True, cached=True)
      wsdl = SOAPpy.WSDL.Proxy(wsdlLoc)
      service = self.getService(fullName)

      plurals = self.getPluralMethods(wsdl)
      for meth in wsdl.methods.keys():
        methFn = getattr(service, meth)
        if meth in plurals:
          methFn = self.expectsList(methFn)
        setattr(self, meth, methFn)        

  def getServiceLocation(self, service_name, wsdl=False, cached=False):
    """ Gets the location of a service or WSDL. Also caches the WSDL.
    
    Args:
      service_name: (string) Name of the service
      wsdl: (boolean) If true, fetches the WSDL, otherwise just the service location
      cached: (boolean) If true, returns the cached WSDL, otherwise refreshes the WSDL
      """
    serviceBranch = os.path.join('api/adwords', self.version, service_name)
    if wsdl:
      serviceBranch += "?wsdl"
    liveLoc = os.path.join(self.server, serviceBranch)
        
    if wsdl:
      #Build the cache dir
      cachedLoc = os.path.join(self.cache_dir, serviceBranch)
      if sys.platform[:3] == 'win':
        cachedLoc = cachedLoc.replace('?', '.')
        
      distutils.dir_util.mkpath(os.path.dirname(cachedLoc))

      #Always returns the cached version, but if cached is False
      #the cached version is refreshed
      if not (os.path.exists(cachedLoc) and cached):
        urllib.urlretrieve(liveLoc, cachedLoc)  

      return cachedLoc

    return liveLoc

  def getService(self, service_name):
    """ Gets the SOAP Proxy of the service

    Args:
      service_name: (string) name of the SOAP service
      """
      
    headers = SOAPpy.Types.headerType()
    headers.email = self.email
    headers.password = self.password
    headers.useragent = self.user_agent
    headers.developerToken = self.developer_token
    headers.applicationToken = self.application_token
    headers.clientEmail = self.client_email
    
    return SOAPpy.SOAPProxy(self.getServiceLocation(service_name),
                            header=headers)

  def getPluralMethods(self, wsdl):
    """ Gets a dict of methods that are expected to return
    a list

    Args:
      wsdl: (SOAP.Proxy.WSDL) WSDL
    Returns
      plurals: dict with plural methods as keys
      """
    plurals = {}

    #Getting to the actual data that holds whether the return type
    #is expected to be a list is convoluted.  This is the best
    #way I've found
    for typ in wsdl.wsdl.types:
      for el in typ.elements:
        if not hasattr(el.content, 'content'): continue
        if not hasattr(el.content.content, 'content') : continue
        if not el.attributes['name'].endswith('Response'): continue

        #If the return value is expected to be a list, add the method name
        #to our *plurals* dict
        if el.content.content.content[0].attributes['maxOccurs'] == 'unbounded':
          methName = el.attributes['name'][:-8]
          plurals[methName] = 1

    return plurals
              

def client_from_config(configuration, prefix='adwords.', **kwargs):
  """Simple way to get a client from a configuration.  Specifically,
  a pylons or other WSGI framework's configuration.

  Args:
    configuration: (dict) The site's config dict
    prefix: (string) Prefix of config options
    **kwargs: Any config options you'd like to override or add

  Return:
    An AdWordsClient object
  """
  options = dict([(key[len(prefix):], configuration[key])
                  for key in configuration if key.startswith(prefix)])
  options.update(kwargs)

  return AdWordsClient(**options)

