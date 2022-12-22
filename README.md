# IqNotify - Intelligent notifications in Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

## How to install

### HACS method
1. Add this repository as a custom-repository into HACS
2. Click download
3. Restart Home Assistant

### Manual method
1. Clone repository into $HASS_HOME/custom_components/iq_notify.
2. Restart Home Assistant.

### Configuration
- Update your configuration.yaml - example below.

The contents of this repository should be in a directory named `iq_notify` inside `custom_components` of your Home Assistant.

Therefore you must have access to your Home Assistant files, no Add-on avilable.

## How can you notify?

- Notify only people present at home. (`only_home`)
- Notify only people away from home. (`only_away`)
- Notify people that just arrived home. (`just_arrived`)
- Notify people that just left home. (`just_left`)
- Notify people that are present at home for particular time. (`staying_home`)
- Notify people that are away from home for particular time. (`staying_away`)
- Try to notify people at home, but if none – notify people away. (`only_home_then_away`)
- Try to notify people that just left home, but if none – notify people away. (`just_left_then_away`)

## Configuration reference

```yaml
notify:
  - platform: iq_notify # the platform to use
    name: iphones       # alias name for notify.{name}
    time: 2             # time offset in which we assume someone "just left/arrived" or "is staying"
    pairs:              # a list of presence entities are corresponding notify services
      - entity: binary_sensor.presence_person1  # presence entity id #1
        service: person1_iphone                 # notify service to use for above entity, without domain (notify.)
      - entity: device_tracker.person2          # presence entity id #2
        service: person2_phone                  # notify service to use for above entity, without domain (notify.)
```

> `time` (defaults to 2)
>
> In minutes as offset to analyze if someone "just left/arrived". If someone will be at given state longer than given `time` – he/she won't be considered as someone that "just ...". This is also used for "staying home/away". Someone must be minimum of `time` in given state to be considered as "staying ...".

> `entity` (required)
>
> ID of any entity that state for "present" is `on` or `home` and `off` or `not_home` for "away".
> Can be `input_boolean`, `binary_sensor`, `group`, `switch`, `device_tracker` etc.

> `service` (required)
>
> Is a service to use for notification without `notify.` domain.

## Example automations

##### Send notification only to people that are present at home.

```yaml
- alias: "Notify: on garbage disposal"
  trigger:
    platform: state
    entity_id: calendar.garbage_disposal
    to: "on"
  condition:
    condition: state
    entity_id: binary_sensor.people_present
    state: "on"
  action:
    - service: notify.iphones
      data:
        title: Garbage disposal
        message: "{{ states.calendar.garbage_disposal.attributes.message }}"
        data:
          mode: only_home
```

If there is someone present – notify people that are present that today is the day of garbage disposal. We don't want to notify people that are away, because they wouldn't take the garbage out in front of the house.

##### Send notification to last person who just left home and this way armed the alarm.

```yaml
automation:
  - alias: "Alarm: arm away when everyone left"
    trigger:
      platform: state
      entity_id: binary_sensor.people_present
      to: "off"
    action:
      - service: alarm_control_panel.alarm_arm_away
        entity_id: alarm_control_panel.alarm

  - alias: "Alarm: send notification on arming"
    trigger:
      - platform: state
        entity_id: alarm_control_panel.alarm
        to: "armed_away"
    action:
      - service: notify.iphones
        data:
          title: Alarm
          message: Alarm has been armed.
          data:
            mode: just_left
```

First automation tracks if everyone left home. If so – arms the alarm. After alarm is armed – second notification notifies only the person who "just left" that the alarm was armed successfully. The last person is responsible for arming the alarm.

##### Notify only people that are home, but if there are none – notify those away.

```yaml
automation:
  - alias: "Door: remind on garage door kept opened"
    trigger:
      platform: state
      entity_id: binary_sensor.garage_door_contact
      to: "on"
      for: "00:05:00"
    action:
      - service: notify.iphones
        data:
          title: Garage door
          message: Garage door kept opened for 5mins.
          data:
            mode: only_home_then_away
```

Will let users that are home know about the door that is left open. If no one is home, let everyone know (because it might be a security breach).
