#!/usr/bin/env python3
# import time
# import sqlite3
# from sqlite3 import Error
import logging
from json import loads, dumps
from requests import put, get
from keycloak import KeycloakOpenID
from configparser import SafeConfigParser
# from vbcp_client import RelayClient
# from vmme_client.initialize import initialize_vmme
# from vmme_client.utils import select, generate_mqtt_topics
# from vmme_client.producer import Producer
# from vmme_client.client_settings import INFLUX_HOST, INFLUX_PORT, INFLUX_DB, password, db_path, DEMO

# Change these settings according to your claimed identity
# PASSWORD = 'ZYDk4WNtbLiQ7YxX'  # Ethereum account password
# KEYFILE = 'mpa_keyfile_vis.json'  # Ethereum keyfile location
# IDENTITY = "0x295b129d81B4bA9Cf84Cd531A7a040030290EEB0"  # Uport identity
# # Change this in order to match the internal endpoint, if necessary
# RELAY_ENDPOINT = 'http://oclk8k.static.otenet.gr:51001/api/'  # Relay server base url address
# # Do not touch these three settings
# TX_RELAY_ADDRESS = "0x6a006b131a0011021b22d00bdad1c4fdb35f5b4f"  # TxRelay address
# META_IDENTITY_MANAGER_ADDRESS = "0x1401a9b2f8511841953a65fdc7fab9b1ff5dde76"  # MetaIdentityManager address
# ENTITY_DATA_MANAGER_ADDRESS = "0x7e8cf20cbe1d6ce24bbff6d6820d88a20408b81f"  # Entity Data Manager address
# From here on, you may touch the code, to your liking

# Data (constants)
# Time threshold used to widen search of
GPS_POS_THRESHOLD = 250
#  a GPS trace for a given timestamp
AUTHURL = 'http://%s/auth/'  # Authentication URL (KeyCloak)
# vDFC Web Service endpoint to retrieve the
TRACEURL = 'http://%s/api/rmp/%s/trace/%d/%d'
#  GPS position of a drone given a point
#  in its flight time
# vDFC Web Service endpoint to send subplans
SUBPLANURL = 'http://%s/api/rmp/%s/subplan'
#  to the RMP (Reactive mission planner)
# vMPA Web Service endpoint to send alerts
ALARMURL = 'http://%s/api/mpa/alert/%s/%s/%s'
#  when recognization events occur

# Config
config = SafeConfigParser()

# Debug support for library (all instances)
DEBUG = False


def _(args):
    if DEBUG:
        print(args)


class NDMWS:
    ''' Main class to talk to NDM Web Services.

        NDM public web services are at endpoints:
        - /api/mprc: MAVProxy Remote Console services (add, remove, list and update data)
        - /api/rmp: Reactive Mission Planner services (send or retrieve subplan, get GPS pos)

        In order to use these service, an authentication bearer is required that should be
        sent along with the request to any service. The NDMWS library helps with this
        authentication and provides several shortcuts to common sequences of service
        requests.

        A tipical use of the library could be:
        1. Connect to Keycloak (retrieve the authentication bearer)
        2. Create a custom subplan
        3. Send the subplan to the RMP

        Other tipical (shorter) use could be:
        1. Connect to Keycloak (retrieve the authentication bearer)
        2. Trigger a predefined alarm (with its mapped subplan)

        In this last case, the alarm is only a label identifying a predefined mapping
        that we want to call use. This requires an association between the alarm and a
        subplan that should be defined in the configuration file in advance. The alarm
        is then sent to the vMPA and the mapped subplan is sent to the vDFC for execution.
    '''

    def __init__(self, dfcaddr=None, droneid=None, mpaaddr=None, inifile='ndmws.ini', debug=False):
        ''' Creates an instance of the helper to call NDM Web Services.

            This is the first object to instantiate and the one to start WS interaction.
            You can specify `dfcaddr`, `mpaaddr` and a `droneid` or you can leave it blank.
            In this case, you an alternativelly inform the `inifile` name or leave the
            defaults. Debug is `False` by default, so you'll have to set `debug=True` to
            see config variables, i.e.
        '''
        global DEBUG
        DEBUG = debug
        config.read(inifile)
        if dfcaddr == None:
            _('Using config: %s' % inifile)
            self.dfcaddr = config.get('dfc', 'hostport')
        else:
            self.dfcaddr = dfcaddr
        if mpaaddr == None:
            self.mpaaddr = config.get('mpa', 'hostport')
            _('Using mpaaddr: %s' % self.mpaaddr)
        else:
            self.mpaaddr = mpaaddr
        if droneid == None:
            self.droneid = config.get('dfc', 'droneid')
            _('Using droneid: %s' % self.droneid)
        else:
            self.droneid = droneid
        self.logger = logging.getLogger(__name__)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        # create formatter and add it to the handlers
        formatter = logging.Formatter("%(asctime)s.%(msecs)03d[%(levelname)-8s]:%(created).3f %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        ch.setFormatter(formatter)
        # add the handlers to logger
        if (self.logger.hasHandlers()):
           self.logger.handlers.clear()
        self.logger.addHandler(ch)
        self.logger.propagate = False
      
        self.authenticate()
        
        self.last_t_subplan = 0
        
        # self.relay_bcp_client = RelayClient(
        #     password=PASSWORD,
        #     keyfile=KEYFILE,
        #     identity=IDENTITY,  # can be set afterwards by calling `client.set_identity(identity)`
        #     tx_relay_address=TX_RELAY_ADDRESS,
        #     meta_identity_manager_address=META_IDENTITY_MANAGER_ADDRESS,
        #     entity_data_manager_address=ENTITY_DATA_MANAGER_ADDRESS,
        #     relay_server_address=RELAY_ENDPOINT,)
            
        # self.vmme_producer = None
        # self.initialized_vmme = False
    
    def authenticate(self, hostport=None, username=None, password=None):
        ''' Authentication with Keycloak is required before any API interaction.

            Realm is hardcoded to 'ndmws' and client 'ndmws-client', so no other
            configuration is required. Note that the communication is always
            encrypted so no plain text is on the wire, but you should protect your
            configuration file from unathorized access (i.e. don't ever commit your
            ndmws.ini file in your repo).
        '''
        if hostport == None or username == None or password == None:
            hostport = config.get('auth', 'hostport')
            _('Using auth hostport: %s' % hostport)
            username = config.get('auth', 'username')
            _('Using auth username: %s' % username)
            password = config.get('auth', 'password')
            _('Using auth password: %s' % password)
            _('Using auth url: %s' % (AUTHURL % hostport))
        self.kc = KeycloakOpenID(server_url=AUTHURL % hostport,
                                 client_id='ndmws-client', realm_name='ndmws')
        self.token = self.kc.token(username, password)
        self.logger.info(self.token)

    def userinfo(self):
        ''' Get keycloak user info from the identity server.

            This is only required if you want to be sure that the user you are
            authenticating with is the one allowed to interact with the
            web services, also no estrictly neccessary.
        '''
        return self.kc.userinfo(self.token['access_token'])

    def getpos(self, ts, th):
        ''' Get the GPS position of the flying drone when time = `ts`.

            While the drone (in config) is flying, every instant can be resolved
            to a known GPS position. This method retrieves the GPS position from
            the done `traces` before the drone lands. The opposite is not true,
            since the drone might (and usually does) pass twice or more to the
            same GPS position.
        '''
        auth = self.token['access_token']
        trace_url = TRACEURL % (self.dfcaddr, self.droneid, ts, th)
        r = get(trace_url, headers={'Authorization': 'Bearer %s' % auth})
        self.logger.info("RESPONSE GETPOS: {}".format(r.text))
        if r.status_code == 200:
            j = loads(r.text)
            return {'time': j['time'], 'pos': j['pos']}
        else:
            return {'code': r.status_code, 'msg': r.json()['msg']}

    def sendplan(self, data):
        ''' Send a subplan to the vDFC for a subplan change.

            With this method you can arbitrarily send a hand-made subplan (JSON)
            or a plan constructed using the `Subplan` fluent language builder.
            The plan will be executed only if the drone is not currently executing
            a subplan. If the drone is yet executing a subplan, an 409 error will be
            issued, but you can catch and ignore it as you wish, since no exception
            is raised at this moment.
        '''
        auth = self.token['access_token']
        r = put(SUBPLANURL % (self.dfcaddr, self.droneid),
                json=loads(data) if type(data) == str else data,
                headers={'Authorization': 'Bearer %s' % auth})
        self.logger.info('SUBPLAN RESPONSE: {}'.format(r.text))
        if r.status_code == 200:
            return r.text
        else:
            return {'code': r.status_code, 'msg': r.json()['msg']}

    def sendalarm(self, src, obj, ts):
        ''' Send an alarm to the vMPA for notification.

            Use this method to send a notification to the vMPA party.
            This notification could be sent in parallel to a subplan change (i.e.
            senplan) in the vDFC, so that both parties are notified of
            the alarm at the same time or sent by itself when an uploaded video
            is being processed. The 'src' param should be self.droneid if the
            video source comes from a drone live video or the label id (user
            supplied when a video is uploaded. 'object' identification and actual
            time 'ts' should also be passed as a way to enrich the alert message.
        '''
        auth = self.token['access_token']
        r = put(ALARMURL % (self.mpaaddr, src, obj, ts),
                headers={'Authorization': 'Bearer %s' % auth})
        self.logger.info("Response ALARM:{}".format(r.text))
        if r.status_code == 200:
            return r.text
        else:
            return {'code': r.status_code, 'msg': r.json()['msg']}

    def triggeralarm(self, alarm, t, subplan_time_space=60, send_subplan=False, threshold=GPS_POS_THRESHOLD):
        ''' Trigger an alarm and send a predefined subplan to the RMP (Reactive Mission Planner).

            Predefined subplans could be configured in the configuration file easily
            following this structure:

            [alarmmap]
            ALARM = SP_SUBPLAN_NAME

            By adding a mapping between an alarm name and a suplan name, the library knows
            which subplan should be loaded when an alarm is triggered.

            [ALARM]
            reason = reason_text
            object = object_text

            A new section should be added for every new alarm, specifying two keys, `reason`
            and `object` that will be substituted into every subplan mapped to this alarm.

            [subplans]
            SP_SUBPLAN_NAME = { subplan: [ ... ] }

            A new key should be added to the `subplans` section to write the JSON corresponding
            to the subplan. Of course, the subplan object can (and should) include substitution
            variables that need to be escaped (use a double `%`) to avoid early template subtitution.

            Allowed template variables are as follows:
            - clientid
            - reason
            - obj
            - lat
            - lon
            - alt
        '''
        try:
            resp = self.getpos(t, threshold)
            if 'code' in resp:
                # self.logger.info('Exception of drone not flying')
                raise Exception('%d: %s' % (resp['code'], resp['msg']))
            else:
                _('Event: %s' % alarm)
                sp = config.get('alarmmap', alarm)
                _('Subplan name: %s' % sp)
                if sp == None:
                    raise Exception(
                        'ERROR: alarm `%s` has no mapped subplan' % alarm)
                subplan = config.get('subplans', sp)
                _('Subplan: %s' % subplan)
                reason = config.get(alarm, 'reason')
                obj = config.get(alarm, 'object')
                _('Sending alert of object %s at time %d' % (obj, t))
                self.sendalarm(self.droneid, obj, t)
                if t > (self.last_t_subplan + subplan_time_space * 1000) and send_subplan:
                    clientid = config.get('client', 'clientid')
                    params = resp['pos']
                    params.update({'clientid': clientid, 'reason': reason, 'obj': obj})
                    _('Subplan params: %s' % params.__str__())
                    self.logger.info(('Subplan params: %s' % params.__str__()))
                    subplan = subplan % params
                    _('Sending subplan: %s' % subplan)
                    # vBCP client
                    # params["ts"] = t
                    # self.send_bcp_data(params)
                    # vMME client
                    # self.send_mme_data(params)
                    # self.last_t_subplan = t
                    self.logger.info("sending subplan")
                    return self.sendplan(subplan)
                else:
                    # if (int((t-self.last_t_subplan)*0.001)) % 10 == 0:
                        # self.logger.info('No subplans allowed. Last one sent {}(s) ago'.format(int((t-self.last_t_subplan)*0.001)))
                    return {'code': 200, 'msg': 'No subplans allowed'}
        except Exception:
            pass

    def send_bcp_data(self, data):
        payload = dumps(data)
        # Relay the payload as a signed message to the  Relay Server. The message will be forwarded to the vMCM.
        self.logger.info('Relaying signed payload to the server: {}'.format(payload))
        # status = self.relay_bcp_client.relay_signed_message(payload)
        # self.logger.info('Got status code : {}'.format(status))
        tx_hash = self.relay_bcp_client.register_mpa_data(payload)
        self.logger.info('Got transaction hash : {}'.format(tx_hash))
        self.logger.info("data has been sent to vBCP")

    # def init_mme(self, data):
    #     device_data = self.generate_mme_data(data)
    #     send_init_msg_influx(device_data)

    def generate_mme_data(self, data):
        topic = generate_mqtt_topics()
        device_data = {
            "device_id": "DEVICE_ID_VMPA",
            "device_name": "DEVICE_NAME_VMPA",
            "device_ip": self.droneid,
            "lat": data['lat'],
            "lon": data['lon'],
            "prev_mme": "none",
            "sender": "device",
            "device_topic": topic,
        # data["topic"] if "topic" in data.keys() else data["reason"],
            "entity_type": "drone"}
        return device_data

    def send_mme_data(self, data):
        db_path = "vmme_client/device.db"
        device_data = self.generate_mme_data(data)
        self.write_mme_data(db_path, device_data)
        self.logger.info("Data has been sent to vMME")
        
    def write_mme_data(self, db_path, device_data):
        self.logger.info("On write_mme_data")
        self.logger.info(self.initialized_vmme)
        if self.initialized_vmme == False:
            self.logger.info("TO INITIALIZE VMME")
            initialize_vmme(db_path, device_data)
#             send_init_msg_influx(device_data)
#             FIRST_BROKER = select(db_path, device_data["device_id"])
# #             if DEMO:
# #                 try:
# #                     base = BaseClient(password=password,
# #                                       keyfile="vmme_client/keyfile.json")
# #                     base.create_keyfile()
# #                     vmme_wallet_addr = base._fetch_signer_address()
# #                     identity_hash_response = create_identity(vmme_wallet_addr)
# #                     identity_hash = identity_hash_response.json()
# #                     valid_identity(identity_hash["tx_hash"].strip(), vmme_wallet_addr, device_data["entity_type"])
# #                     self.logger.info("The device registration to the vAAA was successful: \n")
# #                 except Exception as e:
# #                     self.logger.info(e)
#             insert_ip(db_path, FIRST_BROKER)
#             insert_device_data(db_path, device_data)
            self.vmme_producer = Producer() 
            self.initialized_vmme = True
            self.logger.info("Initialized vMME")
        if self.vmme_producer:
            self.vmme_producer.operate(device_data["device_id"])
        self.logger.info("Out of write mme data")


class Subplan:
    ''' Subplan helper class: temporal plan for an alarm.

        The subplan class is a fluent interface object constructor that allows to
        build a syntactically correct JSON object to call the /subplan web service.

        Also the subplan could be built in such a way that variable substitution
        could be used instead of params of the methods. These variables will be
        lazily evaluated then the subplan in about to be executed, i.e. when the
        `data()` method is issued to validate the supblan semantics.

        A tipical construction should be like this:

        subplan = lambda p : Subplan('videoproc', 'recognized', 'human', p)
          .action.delay(0).mode('guided').guided('%(lat)f', '%(lon)f', '%(alt)d')
          .action.at('%(lat)f', '%(lon)f', '%(alt)d').rc(3, 1500).mode('circle')
          .action.delay(60).mode('auto')
        self.logger.info(subplan(pos).data())

        As you can see in this example, the parameters are not given to the lambda
        function when the `subplan` object is created, but later, in the call to
        `data()`. This allow to create templates of subplans that can be shared
        and instantiated with different params upon creation.
    '''

    def __init__(self, s, reason=None, obj=None, p=None):
        ''' Create an instance of Subplan with informative fields '''
        if type(s) == dict:  # constructor for 'action'
            self._s = s
        else:
            self._s = {'client': s, 'reason': reason,
                       'object': obj, 'params': p, 'subplan': []}

    def __getattr__(self, name):
        ''' Catch any unknown attribute - currently, only `action`.

            In a fluent interface, attributes are used as syntactic sugar to make the
            declarations more readable, althouth some syntactic check could be issued.

            In this case, `action` is our only attribute; all other keywords are
            functions receiving arguments that requires type checking.
        '''
        if name == 'action':
            # If action follows action, previous action should contain a
            # `command`
            if len(self._s['subplan']) > 0 and 'command' not in self._s['subplan'][-1]:
                raise Exception('Action must have at least one `command`')
            # Create an empty subplan
            self._s['subplan'] += [{}]
            return Subplan(self._s)
        else:
            raise Exception('Invalid keyword `{0}`'.format(name))

    def __mod__(self, name, arg):
        ''' Modifier (`at` or `delay`) of a command for an action.

            Both `at` and `delay` are 'modifiers' that acts delaying a command for a fixed
            amount of seconds (delay) or for the time needed for the drone to reach a given
            GPS coordinate (at).
        '''
        if len(self._s['subplan']) == 0:
            raise Exception(
                '`Modifier {0}` must be added to an `action`'.format(name))
        action = self._s['subplan'][-1]  # Modifies last action
        if not 'delay' in action and not 'at' in action:
            action[name] = arg
        else:  # Prevent duplicate modifiers
            raise Exception('Action already has a modifier')
        return self

    def __cmd__(self, *args):
        ''' Command (i.e. `mode`): all args are blank separated, but can add more commands.

            A command is, by now, a MAVProxy command that requires some arguments. In
            MAVProxy, arguments are blank separated, but some type checking is always required.
            Since MAVProxy allows several commands to be issued in the same command line by
            separating them by a semicolon, you can also build a subplan action with several
            commands, that will be issued with the same modifier.

            Some restrictions apply to the commands. First, a command are part of an action, so
            it must follow an `action` attribute. Also, `at` or `delay` must be added *before*
            any command, since every action requires a modifier.
        '''
        if len(self._s['subplan']) == 0:
            raise Exception('Command must be added to an `action`')
        action = self._s['subplan'][-1]  # Command for the last action
        if 'delay' in action or 'at' in action:  # Ensure a modifier exist
            # Arguments are blank separated
            cmd = ' '.join([str(a) for a in args])
            action['command'] = '; '.join(
                [action['command'], cmd]) if 'command' in action else cmd
        else:  # alwais `at` or `delay` should go before any command
            raise Exception('Must give `at` or `delay` before any command')
        return self

    def __valid__(self, v, name, typeclass, exp):
        ''' Validate, substitute (if required) and convert an argument to the required type.

            Every command argument must be correctly typed, so a type validation is performed
            by the subplan parser on every argument of commands. There is a caveat on this: the
            argument could be a template placeholder ('%(arg)t'). This is a special case to
            trigger the substitution of the placeholder by and actual value stored in the
            `params` dict. This, of course, could be done early or lazily by using a lambda
            expression.
        '''
        try:
            # if it's a param, try substitution
            if self._s['params'] and type(v) == str:
                v = v % self._s['params']
            # if conversion fails, a ValueError should be raised
            return typeclass(v)
        except ValueError:
            raise Exception('Argument `{0}` must be {1} or compatible ({2})'
                            .format(name, str(typeclass), exp))

    def data(self):
        ''' Performs last checks and return working python object.

            A last validation is always required for the subplan to be ready. This method is
            required *always* to ensure that the plan is syntax and type correct, and return
            the underlying dict carrying the subplan. This dict can be then used in the
            `sendsubplan` method, because the object is warrantied to be correct.
        '''
        if len(self._s['subplan']) == 0:
            raise Exception('Subplan must have at least one action')
        if 'command' not in self._s['subplan'][-1]:
            raise Exception('Action must have at least one `command`')
        # Params is only a working object, no need to return
        del self._s['params']
        return self._s

    def delay(self, s):
        ''' Delay modifier: action modifier to delay execution of a command a given secs. '''
        s = self.__valid__(s, 'delay', int, 'number of seconds')
        return self.__mod__('delay', s)

    def at(self, lat, lon, alt):
        ''' At (GPS position) modifier: the action command(s) will be delayed until the drone
            reaches the position specified. '''
        lat = self.__valid__(lat, 'lat', float, 'degrees')
        lon = self.__valid__(lon, 'lon', float, 'degrees')
        alt = self.__valid__(alt, 'alt', int, 'relative altitude')
        return self.__mod__('at', {"lat": lat, "lon": lon, "alt": alt})

    def mode(self, m):
        ''' Fligh mode change command. No valid mode validation is made. MAVProxy will
            silently discard mode change if the mode name is unknown. The command issued is
            MODE <mode>'''
        m = self.__valid__(m, 'mode', str, 'flight mode')
        self.__cmd__('mode', m)
        return self

    def guided(self, lat, lon, alt):
        ''' Guided command, with a GPS position (see MAVProxy command). This method issue a
            GUIDED <lat> <lon> <alt> command.'''
        lat = self.__valid__(lat, 'lat', float, 'degrees')
        lon = self.__valid__(lon, 'lon', float, 'degrees')
        alt = self.__valid__(alt, 'alt', int, 'relative altitude')
        self.__cmd__('guided', lat, lon, alt)
        return self

    def rc(self, n, v):
        ''' Remote control command (see MAVProxy command). This method will issue a
            RC <n> <value> command. '''
        n = self.__valid__(n, 'rc', int, 'rc number')
        v = self.__valid__(v, 'throttle', int, 'throttle value')
        self.__cmd__('rc', n, v)
        return self

    def arm(self, o):
        ''' ARM control command (see MAVProxy command). No validation is issued over the
            object argument, MAVProxy will fail to execute this command is the object is
            unknown. '''
        o = self.__valid__(o, 'param', str, 'arm param')
        self.__cmd__('arm', o)
        return self

    def takeoff(self, a):
        ''' Issue a TAKEOFF control command (see MAVProxy command) to the given altitude '''
        a = self.__valid__(a, 'alt', int, 'altitude')
        self.__cmd__('takeoff', a)
        return self


# Simple test: lambda is needed for lazy evaluation of the param dict
if __name__ == '__main__':
    pos = {'lat':-35.039403, 'lon': 149.309403, 'alt': 15}

    def subplan(p):
        return Subplan('videoproc', 'recognized', 'human', p)\
            .action.delay(0).mode('guided').guided('%(lat)f', '%(lon)f', '%(alt)d')\
            .action.at('%(lat)f', '%(lon)f', '%(alt)d').rc(3, 1500).mode('circle')\
            .action.delay(60).mode('auto')

    print(subplan(pos).data())
