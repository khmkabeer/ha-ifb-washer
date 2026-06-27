# IFB Washer for Home Assistant

Custom Home Assistant integration for Wi-Fi IFB washing machines using the My IFB cloud APIs.

This is an early read-only integration built from observed My IFB app traffic. It supports OTP login, automatic washer discovery, REST progress polling, and MQTT status updates.

## Current Features

- UI config flow
- Phone or email OTP login
- Automatic PKCE token exchange
- Automatic Wi-Fi washer discovery
- MQTT status subscription
- REST fallback polling every 30 seconds
- Sensors:
  - Phase
  - Remaining time
  - Program time
  - Progress
  - Raw state
- Binary sensors:
  - Online
  - Running
  - Child lock

## Install

Copy `custom_components/ifb_washer` into your Home Assistant `custom_components` directory and restart Home Assistant.

Then go to:

Settings -> Devices & services -> Add integration -> IFB Washer

The setup flow asks for IFB OAuth credentials used to sign the My IFB login endpoints. These values are not included in this public repository.

## Notes

- This integration is read-only. It does not send washer control commands.
- MQTT uses the same broker observed in the My IFB app: `mqtt2.ifbcloud.in:8883`.
- Some phase names are based on observed captures and may vary by model.

## Observed State Mapping

| State | Name |
| --- | --- |
| 0 | selected |
| 1 | standby |
| 4 | main_wash |
| 8 | first_rinse |
| 9 | second_rinse |
| 10 | final_rinse |
| 11 | final_spin |
| 13 | complete |
| 14 | paused |
| 17 | heating |
| 18 | draining |

## Disclaimer

This project is unofficial and is not affiliated with IFB.
