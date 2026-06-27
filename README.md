# IFB Washer for Home Assistant

Unofficial Home Assistant custom integration for Wi-Fi IFB washing machines using the My IFB cloud APIs.

This integration is based on observed My IFB Android app traffic. It supports OTP login, automatic washer discovery, REST progress polling, and MQTT status updates.

## Status

Early read-only release.

Supported today:

- UI config flow
- Phone or email OTP login
- Automatic PKCE token exchange
- Automatic Wi-Fi washer discovery
- MQTT status subscription
- REST fallback polling every 30 seconds
- Phase, remaining time, program time, progress, raw state
- Online, running, and child-lock binary sensors

Not supported yet:

- Start, pause, cancel, or power commands
- Program selection
- Multi-washer selection UI

## Installation

### HACS Custom Repository

1. Open HACS.
2. Go to Custom repositories.
3. Add this repository URL.
4. Select category `Integration`.
5. Install `IFB Washer`.
6. Restart Home Assistant.

### Manual

Copy this folder into Home Assistant:

```text
custom_components/ifb_washer
```

Then restart Home Assistant.

## Setup

Go to:

Settings -> Devices & services -> Add integration -> IFB Washer

Enter your My IFB phone number or email. The integration will request an OTP, verify it, exchange the token, and discover the Wi-Fi washer automatically.

The setup flow also asks for IFB OAuth credentials used to sign the My IFB login endpoints. These values are not included in this public repository.

## Entities

Sensors:

- Phase
- Remaining time
- Program time
- Progress
- Raw state

Binary sensors:

- Online
- Running
- Child lock

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

## Privacy

The integration stores IFB access and refresh tokens in the Home Assistant config entry, like other cloud integrations. Do not publish diagnostic files that include tokens.

## Disclaimer

This project is unofficial and is not affiliated with IFB.
