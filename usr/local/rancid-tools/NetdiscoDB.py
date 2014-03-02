# Definition for the Netdisco database and a connector class to pull
# out data in rancid format.
#
# For our environment, we have had problems with extremes and rancid so
# chose to ignore them in our device up-list.
#

import os
import datetime
import ConfigParser
import socket
from sqlalchemy import create_engine
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class device_table(Base):
    """ Table definition for netdisco devices """
    __tablename__ = 'device'

    ip = Column(String, primary_key=True)
    creation = Column(DateTime)
    dns = Column(String)
    description = Column(String)
    uptime = Column(Integer)
    contact = Column(String)
    name = Column(String)
    location = Column(String)
    layers = Column(String(8))
    ports = Column(Integer)                      
    mac = Column(String(20))                      
    serial = Column(String)
    model = Column(String)
    ps1_type = Column(String)
    ps2_type = Column(String)
    ps1_status = Column(String) 
    ps2_status = Column(String)
    fan = Column(String)
    slots = Column(Integer)
    vendor = Column(String)
    os = Column(String)
    os_ver = Column(String)
    log = Column(String)
    snmp_ver = Column(Integer)
    snmp_comm = Column(String)
    vtp_domain = Column(String)
    last_discover = Column(DateTime)
    last_macsuck = Column(DateTime)                               
    last_arpnip = Column(DateTime)


class NetdiscoDB(object):
    """Netdisco database connector class"""

    def __init__(self, user=None, passwd=None, hostname='localhost'):
        """
            Take in credentials or get them from a cfg file connect.cfg.
            Can also specify host for the location of the postgres database.
        """
        script_dir = os.path.dirname(os.path.realpath(__file__))
        cfg_file = os.path.join(script_dir,"connect.cfg")
        try:
            if not user or not passwd:
                open(cfg_file)
                self.cfg = ConfigParser.RawConfigParser()
                self.cfg.read(cfg_file)
                user = self.cfg.get('NetDiscoCredentials', 'user')
                passwd = self.cfg.get('NetDiscoCredentials', 'pass')
        except (ConfigParser.Error, IOError): 
            raise UserWarning('Problems with getting credentials for user db')

        self.uri = hostname
        read_engine = create_engine('postgresql://{0}:{1}@{2}/netdisco'.format(
                                    user, passwd, self.uri))
        session = sessionmaker(bind=read_engine)
        self.db = session()

    def GetVendor(self, ip):
        """
            Determine vendor of a device based off IP
        """
        try:
            owner = self.db.query(device_table.vendor).filter(device_table.ip==ip)[0]
            return owner[0]
        except:
            return None

    def SwitchIsUp(self, ip, hrs=24):
        """
            Return True is device was discovered with configurable number of
            hours.
        """
        try:
            last_discovered = self.db.query(device_table.last_discover).filter(
                                            device_table.ip==ip).first()[0]
            now = datetime.datetime.now()
            past_delta = now - datetime.timedelta(hours=hrs)
            if last_discovered > past_delta:
                # switch was discovered within the past x hours
                return True
            else: return False
        except Exception: return None

    def SkipRouter(self, test_router,
                ignore_routers=['router.domain.com']):
        """ Put in equipment that needs to be skipped """
        for skip_router in ignore_routers:
            if test_router.lower() == skip_router: return True
        return False

    def PrintRancidDB(self, file_location, 
                        ignore_vendor='extreme',
                        do_not_dns_pattern='private'):
        """ Save a router.db file for rancid. Specify pattern and
            any vendors to ignore.

            Sample line:
                10.10.50.1:cisco:up
        """
        f = open(file_location,'w')
        for device in (self.db.query(device_table.ip)
                    .order_by(device_table.ip.desc())
                    .all()):
            try:
                ip = device.ip
                dns = socket.gethostbyaddr(ip)[0]
                # If dns contains this pattern, leave as an IP in file
                if do_not_dns_pattern in dns: raise socket.herror
            except socket.herror: dns = ip
            except: continue

            vendor = self.GetVendor(ip)
            # ignore specific vendor or router
            if vendor == ignore_vendor or self.SkipRouter(dns): status = 'down'
            else: status = 'up' if self.SwitchIsUp(ip) else 'down'
            # write out to file
            f.write(":".join([dns.lower(),vendor,status])+'\n')
        f.close()
	
    def GenerateClogin(self, clogin_location='/usr/local/rancid/.cloginrc',
                router_classes=['*domain.com','10.0.25*']):
        """ 
            Generate a .cloginrc file for rancid.
            All extremes will be set to autoenable.

        """
        f = open(clogin_location,'w')
        for router in router_classes:
            f.write('add user {0} {1}\n'.format(
                                    router,
                                    self.cfg.get('SWCredentials','user' )))
            f.write('add password {0} {1} {1}\n'.format(
                                    router,
                                    self.cfg.get('SWCredentials','pass' )))
            f.write('add method {0} ssh\n'.format(router))
        for device in self.db.query(device_table.ip).filter(
                device_table.vendor=='extreme'):
            try:
                ip = device.ip
                dns = socket.gethostbyaddr(ip)[0].lower()
            except socket.herror: dns = ip
            except: continue
            if not self.SwitchIsUp(ip): continue
            f.write('add autoenable {0} 1\n'.format(dns))
        f.close()
