"""Intelligent notifications based on presence."""
import logging
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.const import STATE_ON, STATE_OFF, STATE_HOME, STATE_NOT_HOME

from homeassistant.components.notify import ATTR_DATA, PLATFORM_SCHEMA, BaseNotificationService

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'iq_notify'

CONF_PAIRS = 'pairs'
CONF_PAIR_ENTITY = 'entity'
CONF_PAIR_SERVICE = 'service'
CONF_TIME = 'time'
CONF_MODE = 'mode'

DEFAULT_TIME = 2  # minutes

# send notification to all, default
MODE_ALL = 'all'

# send notification to only present users
MODE_ONLY_HOME = 'only_home'

# send notification to only away users
MODE_ONLY_AWAY = 'only_away'

# send notification to users that arrived in last CONF_TIME
MODE_JUST_ARRIVED = 'just_arrived'

# send notification to users that left in last CONF_TIME
MODE_JUST_LEFT = 'just_left'

# send notification to present users that are present for at least CONF_TIME
MODE_STAYING_HOME = 'staying_home'

# send notification to away users that are away for at least CONF_TIME
MODE_STAYING_AWAY = 'staying_away'

# try to send notification to present but if no one present - send to away users
MODE_ONLY_HOME_THEN_AWAY = 'only_home_then_away'

# try to send notification to users that left in last CONF_TIME but if that includes no one - send to away users
MODE_JUST_LEFT_THEN_AWAY = 'just_left_then_away'


PAIRS_CONFIG_SCHEMA = vol.Schema({
    vol.Optional(CONF_PAIR_ENTITY): cv.string,
    vol.Optional(CONF_PAIR_SERVICE): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_PAIRS, default={}): vol.Any(cv.ensure_list, [PAIRS_CONFIG_SCHEMA]),
    vol.Optional(CONF_TIME, default=DEFAULT_TIME): cv.positive_int
})


def get_service(hass, config, discovery_info=None):
    """Get the notification service."""
    _LOGGER.debug('Setting up iq_notify platform...')

    pairs = config[CONF_PAIRS]
    time = config[CONF_TIME]

    return IqNotify(pairs, time)


class IqNotify(BaseNotificationService):

    def __init__(self, pairs, time):
        self._pairs = pairs
        self._time = time

    def send_message(self, message="", **kwargs):
        """Send a message."""

        print(kwargs)

        mode = MODE_ALL
        time = self._time
        data = {}

        # Get mode and time override
        if kwargs.get(ATTR_DATA) is not None:
            data = kwargs.get(ATTR_DATA)
            if data.get(CONF_MODE) is not None:
                mode = data.get(CONF_MODE)
                data.pop(CONF_MODE)
            if data.get(CONF_TIME) is not None:
                time = data.get(CONF_TIME)
                data.pop(CONF_TIME)

        _LOGGER.debug('IqNotify: using mode: ' + mode + ' and message: ' + message)

        looking_since = dt_util.utcnow() - timedelta(minutes=time)
        
        # Check if anyone is home (for MODE_ONLY_HOME_THEN_AWAY) or just left (for MODE_JUST_LEFT_THEN_AWAY)
        anyone_home = False
        anyone_just_left = False
        for pair in self._pairs:
            entity = pair.get(CONF_PAIR_ENTITY)
            if entity in self.hass.states._states:
                state = self.hass.states.get(entity)
                cur_state = state.state
                state_since = state.last_changed
                
                
                if cur_state == STATE_ON or cur_state == STATE_HOME:
                    anyone_home = True
                elif looking_since < state_since:
                    anyone_just_left = True
                

        service_data = kwargs
        # Append message
        service_data['message'] = message
        # Alter data
        service_data['data'] = data

        print(service_data)


        # Check and notify each entity
        for pair in self._pairs:
            entity = pair.get(CONF_PAIR_ENTITY)
            service = pair.get(CONF_PAIR_SERVICE)

            if entity in self.hass.states._states:
                state = self.hass.states.get(entity)
                cur_state = state.state
                state_since = state.last_changed
                
                if cur_state == STATE_ON or cur_state == STATE_HOME:
                    user_is_home = True
                else:
                    user_is_home = False
                
                notify = False
                
                if mode == MODE_ALL:
                    notify = True
                elif mode == MODE_ONLY_HOME and user_is_home:
                    notify = True
                elif mode == MODE_ONLY_AWAY and not user_is_home:
                    notify = True
                elif mode == MODE_JUST_ARRIVED and user_is_home:
                    if looking_since < state_since:
                        notify = True
                elif mode == MODE_JUST_LEFT and not user_is_home:
                    if looking_since < state_since:
                        notify = True
                elif mode == MODE_STAYING_HOME and user_is_home:
                    if looking_since > state_since:
                        notify = True
                elif mode == MODE_STAYING_AWAY and not user_is_home:
                    if looking_since > state_since:
                        notify = True
                elif mode == MODE_ONLY_HOME_THEN_AWAY:
                    if not anyone_home:
                        notify = True
                    elif anyone_home and user_is_home:
                        notify = True
                elif mode == MODE_JUST_LEFT_THEN_AWAY:
                    if not user_is_home:
                        if not anyone_just_left:
                            notify = True
                        elif anyone_just_left:
                            if looking_since < state_since:
                                notify = True

                _LOGGER.debug('\nentity: ' + entity)
                _LOGGER.debug('cur_state: ' + str(cur_state))
                _LOGGER.debug('looking_since: ' + str(looking_since))
                _LOGGER.debug('state_since: ' + str(state_since))
                _LOGGER.debug('looking_since < state_since: ' + str(looking_since < state_since))
                _LOGGER.debug('user_is_home: ' + str(user_is_home))
                _LOGGER.debug('anyone_just_left: ' + str(anyone_just_left))

                if notify:
                    self.hass.services.call('notify', service, service_data)
                    _LOGGER.info('Notifying notify.' + service + ' via ' + mode + ' mode' + '\n');
