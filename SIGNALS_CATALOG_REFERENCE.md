# SIGNALS CATALOG REFERENCE

## Overview

**Total Signals: 195**

This comprehensive reference documents all signals available in the EDMC VKB Connector system. Signals are real-time game state indicators derived from Elite Dangerous telemetry data that can be used to create dynamic automation rules and triggers.

### What are Signals?

Signals represent the current state of various aspects of Elite Dangerous gameplay. Each signal has:
- **Name**: The identifier used in rule definitions (e.g., `docking_state`, `credits`)
- **Type**: The data type (enum, string, number, bool, array)
- **Category**: Thematic grouping for organization
- **Tier**: Visibility level (core=common, detail=advanced, advanced=technical)
- **Data Source**: Where the signal gets its data (dashboard, journal, state, capi)
- **Description**: What the signal represents

### How Signals are Used

Signals are referenced in rule conditions to trigger VKB actions. For example:
```json
{
  "condition": "docking_state == 'just_docked'",
  "action": "activate_profile_group"
}
```

## Data Sources

Signals are derived from four primary data sources in Elite Dangerous:

### 1. Dashboard (Status.json)
- **Update Frequency**: ~1 second
- **Contents**: Real-time status information
- **Includes**:
  - Ship flags and status
  - Power distribution (pips)
  - Fuel levels
  - Cargo status
  - UI focus state
  - Position and heading
  - Health and temperature
  - Oxygen levels

### 2. Journal (Journal Files)
- **Update Frequency**: On event occurrence
- **Contents**: Event-based gameplay logs
- **Coverage**: 200+ event types including:
  - Travel events (jumps, docking, undocking)
  - Combat events (attacks, kills, interdictions)
  - Trading and exploration events
  - Mission and community goal events
  - Ship and module transactions

### 3. State (Accumulated State)
- **Update Frequency**: On relevant journal event
- **Contents**: Accumulated game state
- **Includes**:
  - Commander information
  - Ship loadout and status
  - Cargo and materials inventory
  - Active missions
  - Ranks and reputation
  - Squadron and powerplay information
  - System and station data
  - Target information

### 4. CAPI (Frontier Companion API)
- **Update Frequency**: On request (typically at dock events)
- **Contents**: Detailed information
- **Includes**:
  - Detailed ship loadout specifications
  - Station market and trading data
  - Fleet carrier information
  - Outfitting and shipyard availability

## Signal Tiers

Signals are organized by complexity and frequency of use:

### Core (Common)
Most frequently used signals for basic automation. These represent common gameplay states like docking status, ship type, current system, etc.

### Detail (Advanced)
Additional useful signals for more sophisticated rules. These include rank progress, specific ship stats, detailed location information, etc.

### Advanced (Technical)
Raw flag values and low-level technical signals for power users. Direct access to binary flags from the dashboard Status.json file.

## Signal Operators

When using signals in conditions, these operators can be used:

| Operator | Symbol | Label | Usage |
|----------|--------|-------|-------|
| `eq` | `=` | Equals | `signal == value` |
| `ne` | `≠` | Not equal | `signal != value` |
| `in` | `∈` | In list | `signal in [val1, val2]` |
| `nin` | `∉` | Not in list | `signal not_in [val1, val2]` |
| `lt` | `<` | Less than | `signal < value` |
| `lte` | `≤` | Less or equal | `signal <= value` |
| `gt` | `>` | Greater than | `signal > value` |
| `gte` | `≥` | Greater or equal | `signal >= value` |
| `contains` | `⊇` | Contains | `array_signal contains value` |
| `exists` | `∃` | Exists | `signal exists` |
| `recent` | `⏱` | Recently occurred | `signal recently_occurred(5s)` |

## Bitfield Flags Reference

Some signals use bitfield flags for compact representation of multiple boolean states. These are mapped from the dashboard Status.json.

### Ship Flags (32-bit field)
Source: `dashboard.Flags`

| Bit | Name | Meaning |
|-----|------|---------|
| 0 | Docked | Ship is docked at a station |
| 1 | Landed | Ship is landed on a surface |
| 2 | Landing Gear Down | Landing gear deployed |
| 3 | Shields Up | Shield generator active |
| 4 | Supercruise | In supercruise |
| 5 | Flight Assist Off | Flight assist disabled |
| 6 | Hardpoints Deployed | Weapon hardpoints extended |
| 7 | In Wing | Part of a wing |
| 8 | Lights On | External lights on |
| 9 | Cargo Scoop Deployed | Cargo scoop extended |
| 10 | Silent Running | Silent running active |
| 11 | Scooping Fuel | Currently fuel scooping |
| 16 | FSD Mass Locked | FSD mass-locked by another ship |
| 17 | FSD Charging | FSD charging for jump |
| 18 | FSD Cooldown | FSD in cooldown |
| 19 | Low Fuel | Main fuel tank below 25% |
| 20 | Overheating | Ship overheating |
| 22 | In Danger | Being attacked or under threat |

### On-Foot Flags (Odyssey, 32-bit field)
Source: `dashboard.Flags2`

| Bit | Name | Meaning |
|-----|------|---------|
| 0 | On Foot | Commander on foot (not in ship) |
| 1 | In Taxi | In a settlement taxi |
| 2 | In Multicrew | In multicrew session |
| 3 | On Foot In Station | On foot inside a station |
| 4 | On Foot On Planet | On foot on planet surface |
| 5 | Aim Down Sight | Aiming down weapon sights |
| 6 | Low Oxygen | Suit oxygen below threshold |
| 7 | Low Health | Suit health low |
| 8 | Cold | Environment cold |
| 9 | Hot | Environment hot |
| 10 | Very Cold | Environment very cold |
| 11 | Very Hot | Environment very hot |
| 15 | Glide Mode | In glide mode |

## Signal Count by Category

| Category | Count |
|----------|-------|
| Combat | 1 |
| Commander | 10 |
| Engineering | 2 |
| Fleet Carrier | 6 |
| HUD | 3 |
| Inventory | 5 |
| Location | 34 |
| Missions | 2 |
| On-Foot | 14 |
| Passengers | 3 |
| Powerplay | 6 |
| SRV | 7 |
| Session | 3 |
| Ship | 66 |
| Squadron | 4 |
| Statistics | 11 |
| Trading | 1 |
| Travel | 14 |
| Uncategorized | 3 |

## Complete Signal Reference

### Combat (1 signals)

#### `combat_event`
- **Label**: Combat event
- **Type**: `enum`
- **Tier**: core
- **Values**: 16 options

### Commander (10 signals)

#### `alliance_reputation`
- **Label**: Alliance reputation
- **Type**: `number`
- **Tier**: detail

#### `commander_name`
- **Label**: Commander name
- **Type**: `string`
- **Tier**: core

#### `comms_event`
- **Label**: Communications event
- **Type**: `enum`
- **Tier**: core
- **Values**: 5 options
  - `receive_text` = Received text
  - `send_text` = Sent text
  - `music` = Music changed
  - `friends` = Friends list
  - `none` = None

#### `credits`
- **Label**: Credit balance
- **Type**: `number`
- **Tier**: core

#### `empire_reputation`
- **Label**: Empire reputation
- **Type**: `number`
- **Tier**: detail

#### `federation_reputation`
- **Label**: Federation reputation
- **Type**: `number`
- **Tier**: detail

#### `financial_activity`
- **Label**: Financial activity
- **Type**: `enum`
- **Tier**: core
- **Values**: 6 options
  - `none` = None
  - `paid_fines` = Paid fines
  - `paid_bounties` = Paid bounties
  - `redeemed_voucher` = Redeemed voucher
  - `paid_legacy_fines` = Paid legacy fines
  - `cleared_impound` = Cleared impound

#### `independent_reputation`
- **Label**: Independent reputation
- **Type**: `number`
- **Tier**: detail

#### `legal_state`
- **Label**: Legal status
- **Type**: `enum`
- **Tier**: core
- **Values**: 7 options
  - `Clean` = Clean
  - `IllegalCargo` = Illegal cargo
  - `Speeding` = Speeding
  - `Wanted` = Wanted
  - `Hostile` = Hostile
  - `PassengerWanted` = Passenger wanted
  - `Warrant` = Warrant

#### `transport`
- **Label**: Current transport
- **Type**: `enum`
- **Tier**: core
- **Values**: 8 options
  - `ship` = Ship
  - `srv` = SRV
  - `fighter` = Fighter
  - `on_foot` = On foot
  - `in_taxi` = In Taxi
  - `in_multicrew` = In Multicrew
  - `in_wing` = In Wing
  - `unknown` = Unknown

### Engineering (2 signals)

#### `engineering_activity`
- **Label**: Engineering activity
- **Type**: `enum`
- **Tier**: core
- **Values**: 6 options
  - `none` = None
  - `crafted` = Module engineered
  - `progressed` = Engineer progress
  - `collected_material` = Material collected
  - `traded_materials` = Materials traded
  - `synthesized` = Synthesis crafted

#### `engineering_event`
- **Label**: Engineering event
- **Type**: `enum`
- **Tier**: core
- **Values**: 11 options

### Fleet Carrier (6 signals)

#### `carrier_event`
- **Label**: Fleet Carrier event
- **Type**: `enum`
- **Tier**: core
- **Values**: 17 options

#### `fleet_carrier_balance`
- **Label**: Carrier balance
- **Type**: `number`
- **Tier**: detail

#### `fleet_carrier_callsign`
- **Label**: Carrier callsign
- **Type**: `string`
- **Tier**: core

#### `fleet_carrier_fuel`
- **Label**: Carrier fuel
- **Type**: `number`
- **Tier**: detail

#### `fleet_carrier_name`
- **Label**: Carrier name
- **Type**: `string`
- **Tier**: core

#### `has_fleet_carrier`
- **Label**: Owns fleet carrier
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

### HUD (3 signals)

#### `gui_focus`
- **Label**: Focused screen
- **Type**: `enum`
- **Tier**: core
- **Values**: 12 options

#### `hud_mode`
- **Label**: HUD mode
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `combat` = Combat
  - `analysis` = Analysis

#### `night_vision`
- **Label**: Night vision
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `off` = Off
  - `on` = On

### Inventory (5 signals)

#### `cargo_inventory`
- **Label**: Cargo items
- **Type**: `array`
- **Tier**: detail

#### `encoded_materials_count`
- **Label**: Encoded data count
- **Type**: `number`
- **Tier**: core

#### `manufactured_materials_count`
- **Label**: Manufactured count
- **Type**: `number`
- **Tier**: core

#### `raw_materials_count`
- **Label**: Raw materials count
- **Type**: `number`
- **Tier**: core

#### `total_materials_count`
- **Label**: Total materials
- **Type**: `number`
- **Tier**: core

### Location (34 signals)

#### `altitude`
- **Label**: Altitude
- **Type**: `number`
- **Tier**: detail

#### `body_name`
- **Label**: Current body
- **Type**: `string`
- **Tier**: core

#### `body_proximity`
- **Label**: Body proximity
- **Type**: `enum`
- **Tier**: detail
- **Values**: 4 options
  - `far` = Far
  - `approaching` = Approaching
  - `orbital_cruise` = Orbital cruise
  - `leaving` = Leaving

#### `breathable_atmosphere`
- **Label**: Breathable atmosphere
- **Type**: `enum`
- **Tier**: detail
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `colonisation_event`
- **Label**: Colonisation event
- **Type**: `enum`
- **Tier**: core
- **Values**: 3 options
  - `none` = None
  - `colonisation_construction_depot` = Construction depot
  - `colonisation_contribution` = Contribution made

#### `gravity_level`
- **Label**: Gravity
- **Type**: `number`
- **Tier**: detail

#### `has_lat_long`
- **Label**: Position data available
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `heading`
- **Label**: Heading
- **Type**: `number`
- **Tier**: detail

#### `latitude`
- **Label**: Latitude
- **Type**: `number`
- **Tier**: detail

#### `longitude`
- **Label**: Longitude
- **Type**: `number`
- **Tier**: detail

#### `market_id`
- **Label**: Market ID
- **Type**: `number`
- **Tier**: advanced

#### `oxygen`
- **Label**: Oxygen
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `ok` = OK
  - `low` = Low

#### `oxygen_level`
- **Label**: Oxygen level
- **Type**: `number`
- **Tier**: detail

#### `station_allegiance`
- **Label**: Station allegiance
- **Type**: `enum`
- **Tier**: detail
- **Values**: 7 options
  - `unknown` = Unknown
  - `alliance` = Alliance
  - `empire` = Empire
  - `federation` = Federation
  - `independent` = Independent
  - `pirate` = Pirate
  - `pilotsfederation` = Pilots Federation

#### `station_distance_ls`
- **Label**: Distance from star (ls)
- **Type**: `number`
- **Tier**: detail

#### `station_economy`
- **Label**: Station economy
- **Type**: `enum`
- **Tier**: detail
- **Values**: 16 options

#### `station_faction`
- **Label**: Station faction
- **Type**: `string`
- **Tier**: detail

#### `station_government`
- **Label**: Station government
- **Type**: `enum`
- **Tier**: detail
- **Values**: 15 options

#### `station_name`
- **Label**: Station Name
- **Type**: `string`
- **Tier**: core

#### `station_type`
- **Label**: Station type
- **Type**: `enum`
- **Tier**: detail
- **Values**: 10 options
  - `unknown` = Unknown
  - `coriolis` = Coriolis Starport
  - `orbis` = Orbis Starport
  - `ocellus` = Ocellus Starport
  - `outpost` = Outpost
  - `crateroutpost` = Planetary Outpost
  - `craterport` = Planetary Port
  - `megaship` = Megaship
  - `asteroidbase` = Asteroid Base
  - `fleetcarrier` = Fleet Carrier

#### `system_address`
- **Label**: System address
- **Type**: `number`
- **Tier**: detail

#### `system_allegiance`
- **Label**: System allegiance
- **Type**: `enum`
- **Tier**: detail
- **Values**: 6 options
  - `unknown` = Unknown
  - `alliance` = Alliance
  - `empire` = Empire
  - `federation` = Federation
  - `independent` = Independent
  - `pirate` = Pirate

#### `system_economy`
- **Label**: System economy
- **Type**: `enum`
- **Tier**: detail
- **Values**: 11 options

#### `system_event`
- **Label**: System event
- **Type**: `enum`
- **Tier**: core
- **Values**: 20 options

#### `system_faction`
- **Label**: System faction
- **Type**: `string`
- **Tier**: detail

#### `system_government`
- **Label**: System government
- **Type**: `enum`
- **Tier**: detail
- **Values**: 11 options

#### `system_name`
- **Label**: System Name
- **Type**: `string`
- **Tier**: core

#### `system_population`
- **Label**: System population
- **Type**: `number`
- **Tier**: detail

#### `system_security`
- **Label**: System security
- **Type**: `enum`
- **Tier**: detail
- **Values**: 6 options
  - `unknown` = Unknown
  - `$system_security_low;` = Low Security
  - `$system_security_medium;` = Medium Security
  - `$system_security_high;` = High Security
  - `$galaxy_map_info_state_anarchy;` = Anarchy
  - `$system_security_lawless;` = Lawless

#### `system_x`
- **Label**: System coord X
- **Type**: `number`
- **Tier**: advanced

#### `system_y`
- **Label**: System coord Y
- **Type**: `number`
- **Tier**: advanced

#### `system_z`
- **Label**: System coord Z
- **Type**: `number`
- **Tier**: advanced

#### `temperature_state`
- **Label**: Temperature state
- **Type**: `enum`
- **Tier**: core
- **Values**: 5 options
  - `ok` = OK
  - `cold` = Cold
  - `hot` = Hot
  - `very_cold` = Very cold
  - `very_hot` = Very hot

#### `temperature_value`
- **Label**: Temperature (K)
- **Type**: `number`
- **Tier**: detail

### Missions (2 signals)

#### `mission_event`
- **Label**: Mission event
- **Type**: `enum`
- **Tier**: core
- **Values**: 10 options
  - `none` = None
  - `mission_accepted` = Mission accepted
  - `mission_completed` = Mission completed
  - `mission_failed` = Mission failed
  - `mission_abandoned` = Mission abandoned
  - `community_goal` = CG update
  - `mission_redirected` = Mission redirected
  - `community_goal_join` = Joined community goal
  - `community_goal_discard` = Abandoned CG
  - `community_goal_reward` = CG reward received

#### `missions_active_count`
- **Label**: Active missions count
- **Type**: `number`
- **Tier**: core

### On-Foot (14 signals)

#### `aim`
- **Label**: Aim
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `normal` = Normal
  - `aiming` = Aiming

#### `flag_aim_down_sight`
- **Label**: Aiming down sight
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `flag_low_health`
- **Label**: Low health
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `normal` = Normal
  - `low` = Low

#### `flag_low_oxygen`
- **Label**: Low oxygen
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `normal` = Normal
  - `low` = Low

#### `flag_on_foot`
- **Label**: On foot
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `health`
- **Label**: Health
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `ok` = OK
  - `low` = Low

#### `health_level`
- **Label**: Health level
- **Type**: `number`
- **Tier**: detail

#### `on_foot_location`
- **Label**: Where you are on foot
- **Type**: `enum`
- **Tier**: core
- **Values**: 6 options
  - `none` = Unknown
  - `station` = In station
  - `planet` = On planet
  - `hangar` = In hangar
  - `social_space` = Social space
  - `exterior` = Exterior

#### `onfoot_event`
- **Label**: On-Foot event
- **Type**: `enum`
- **Tier**: core
- **Values**: 24 options

#### `selected_weapon`
- **Label**: Selected weapon
- **Type**: `enum`
- **Tier**: detail
- **Values**: 11 options

#### `suit`
- **Label**: Suit
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `none` = None
  - `purchased` = Purchased
  - `sold` = Sold
  - `upgraded` = Upgraded

#### `temperature`
- **Label**: Environment temperature
- **Type**: `enum`
- **Tier**: core
- **Values**: 5 options
  - `very_cold` = Very cold
  - `cold` = Cold
  - `normal` = Normal
  - `hot` = Hot
  - `very_hot` = Very hot

#### `transport_activity`
- **Label**: Transport activity
- **Type**: `enum`
- **Tier**: detail
- **Values**: 5 options
  - `none` = None
  - `taxi_booked` = Taxi booked
  - `taxi_cancelled` = Taxi cancelled
  - `dropship_booked` = Dropship booked
  - `dropship_cancelled` = Dropship cancelled

#### `weapon`
- **Label**: Weapon
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `none` = None
  - `purchased` = Purchased
  - `sold` = Sold
  - `upgraded` = Upgraded

### Passengers (3 signals)

#### `has_vip_passengers`
- **Label**: Has VIP passengers
- **Type**: `enum`
- **Tier**: detail
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `has_wanted_passengers`
- **Label**: Has wanted passengers
- **Type**: `enum`
- **Tier**: detail
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `passengers_count`
- **Label**: Passenger count
- **Type**: `number`
- **Tier**: core

### Powerplay (6 signals)

#### `powerplay_activity`
- **Label**: Powerplay activity
- **Type**: `enum`
- **Tier**: core
- **Values**: 9 options
  - `none` = None
  - `joined` = Pledged to power
  - `left` = Left power
  - `defected` = Defected from power
  - `delivered` = Delivered cargo
  - `collected` = Collected commodity
  - `voted` = Voted on action
  - `received_salary` = Received salary
  - `received_voucher` = Received voucher

#### `powerplay_merits`
- **Label**: Powerplay merits
- **Type**: `number`
- **Tier**: detail

#### `powerplay_pledged`
- **Label**: Pledged to power
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `powerplay_power`
- **Label**: Pledged power
- **Type**: `enum`
- **Tier**: core
- **Values**: 12 options

#### `powerplay_rank`
- **Label**: Powerplay rank
- **Type**: `number`
- **Tier**: detail

#### `powerplay_time_pledged`
- **Label**: Time pledged (seconds)
- **Type**: `number`
- **Tier**: detail

### SRV (7 signals)

#### `flag_srv_turret`
- **Label**: Turret
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `retracted` = Retracted
  - `deployed` = Deployed

#### `srv`
- **Label**: SRV
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `none` = None
  - `deployed` = Deployed
  - `docked` = Docked
  - `destroyed` = Destroyed

#### `srv_deployed_state`
- **Label**: Deployment
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `stowed` = Stowed
  - `deployed` = Deployed
  - `just_launched` = Just launched
  - `just_docked` = Just docked

#### `srv_drive_assist`
- **Label**: Drive assist
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `off` = Off
  - `on` = On

#### `srv_handbrake`
- **Label**: Handbrake
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `off` = Off
  - `on` = On

#### `srv_high_beam`
- **Label**: Lights
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `off` = Off
  - `on` = On

#### `srv_under_ship`
- **Label**: Under ship
- **Type**: `enum`
- **Tier**: detail
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

### Session (3 signals)

#### `game_mode`
- **Label**: Game mode
- **Type**: `enum`
- **Tier**: core
- **Values**: 3 options
  - `Open` = Open
  - `Solo` = Solo
  - `Group` = Private Group

#### `game_version`
- **Label**: Game version
- **Type**: `enum`
- **Tier**: core
- **Values**: 3 options
  - `base` = Base game
  - `horizons` = Horizons
  - `odyssey` = Odyssey

#### `group_name`
- **Label**: Private group name
- **Type**: `string`
- **Tier**: detail

### Ship (66 signals)

#### `cargo_activity`
- **Label**: Cargo activity
- **Type**: `enum`
- **Tier**: detail
- **Values**: 3 options
  - `none` = None
  - `collected` = Collected
  - `ejected` = Ejected

#### `cargo_count`
- **Label**: Cargo count
- **Type**: `number`
- **Tier**: core

#### `cargo_hatch`
- **Label**: Cargo hatch
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `retracted` = Retracted
  - `deployed` = Deployed

#### `cockpit_status`
- **Label**: Cockpit status
- **Type**: `enum`
- **Tier**: detail
- **Values**: 2 options
  - `intact` = Intact
  - `breached` = Breached

#### `combat_state`
- **Label**: Combat state
- **Type**: `enum`
- **Tier**: core
- **Values**: 5 options
  - `peaceful` = Peaceful
  - `under_attack` = Under attack
  - `killed_target` = Killed target
  - `destroyed` = Destroyed
  - `got_bounty` = Bounty awarded

#### `crew_activity`
- **Label**: Crew activity
- **Type**: `enum`
- **Tier**: core
- **Values**: 15 options

#### `docking_request_state`
- **Label**: Request
- **Type**: `enum`
- **Tier**: detail
- **Values**: 6 options
  - `none` = None
  - `requested` = Requested
  - `granted` = Granted
  - `denied` = Denied
  - `cancelled` = Cancelled
  - `timeout` = Timed out

#### `docking_state`
- **Label**: Docking state
- **Type**: `enum`
- **Tier**: core
- **Values**: 7 options
  - `in_space` = In space
  - `landed` = Landed
  - `docked` = Docked
  - `just_docked` = Just docked
  - `just_undocked` = Just undocked
  - `just_landed` = Just landed
  - `just_lifted_off` = Just lifted off

#### `fighter`
- **Label**: Fighter
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `none` = None
  - `launched` = Launched
  - `docked` = Docked
  - `destroyed` = Destroyed

#### `fire_group`
- **Label**: Fire group
- **Type**: `number`
- **Tier**: detail

#### `flag_flight_assist_off`
- **Label**: Flight assist disabled
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `on` = On
  - `off` = Off

#### `flag_hardpoints_deployed`
- **Label**: Hardpoints deployed
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `retracted` = Retracted
  - `deployed` = Deployed

#### `flag_in_wing`
- **Label**: In a wing
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `flag_shields_up`
- **Label**: Shields up
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `down` = Down
  - `up` = Up

#### `flight_assist`
- **Label**: Flight assist
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `on` = On
  - `off` = Off

#### `fsd_state`
- **Label**: FSD state
- **Type**: `enum`
- **Tier**: core
- **Values**: 6 options
  - `idle` = Idle
  - `charging` = Charging
  - `cooldown` = Cooldown
  - `jump_active` = Jump active
  - `supercruise` = Supercruise
  - `gliding` = Gliding

#### `fuel`
- **Label**: Fuel status
- **Type**: `enum`
- **Tier**: core
- **Values**: 8 options
  - `ok` = OK
  - `low` = Low
  - `critical` = Critical
  - `scooping` = Actively scooping
  - `scooped` = Just scooped
  - `full_refuel` = Full refuel
  - `partial_refuel` = Partial refuel
  - `reservoir_filled` = Reservoir filled

#### `fuel_main`
- **Label**: Main fuel tank
- **Type**: `number`
- **Tier**: detail

#### `fuel_reservoir`
- **Label**: Reserve fuel tank
- **Type**: `number`
- **Tier**: detail

#### `hardpoints`
- **Label**: Hardpoints
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `retracted` = Retracted
  - `deployed` = Deployed

#### `has_npc_crew`
- **Label**: Has NPC crew
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `heat_status`
- **Label**: Heat status
- **Type**: `enum`
- **Tier**: core
- **Values**: 3 options
  - `normal` = Normal
  - `overheating` = Overheating
  - `heat_damage` = Taking heat damage

#### `hull_state`
- **Label**: Hull state
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `ok` = OK
  - `damaged` = Damaged
  - `critical` = Critical
  - `taking_damage` = Taking damage

#### `landing_gear`
- **Label**: Landing gear
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `retracted` = Retracted
  - `deployed` = Deployed

#### `lights`
- **Label**: External lights
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `off` = Off
  - `on` = On

#### `limpets`
- **Label**: Limpets
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `none` = None
  - `purchased` = Purchased
  - `launched` = Launched
  - `sold` = Sold

#### `mass_locked`
- **Label**: Mass locked
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `module_activity`
- **Label**: Module activity
- **Type**: `enum`
- **Tier**: core
- **Values**: 6 options
  - `none` = None
  - `bought` = Module bought
  - `sold` = Module sold
  - `swapped` = Module swapped
  - `stored` = Module stored
  - `retrieved` = Module retrieved

#### `npc_crew_count`
- **Label**: NPC crew count
- **Type**: `number`
- **Tier**: detail

#### `pips_eng`
- **Label**: Engine
- **Type**: `enum`
- **Tier**: detail
- **Values**: 9 options
  - `0` = 0 pips
  - `1` = 0.5 pips
  - `2` = 1 pip
  - `3` = 1.5 pips
  - `4` = 2 pips
  - `5` = 2.5 pips
  - `6` = 3 pips
  - `7` = 3.5 pips
  - `8` = 4 pips

#### `pips_sys`
- **Label**: Systems
- **Type**: `enum`
- **Tier**: detail
- **Values**: 9 options
  - `0` = 0 pips
  - `1` = 0.5 pips
  - `2` = 1 pip
  - `3` = 1.5 pips
  - `4` = 2 pips
  - `5` = 2.5 pips
  - `6` = 3 pips
  - `7` = 3.5 pips
  - `8` = 4 pips

#### `pips_wep`
- **Label**: Weapon
- **Type**: `enum`
- **Tier**: detail
- **Values**: 9 options
  - `0` = 0 pips
  - `1` = 0.5 pips
  - `2` = 1 pip
  - `3` = 1.5 pips
  - `4` = 2 pips
  - `5` = 2.5 pips
  - `6` = 3 pips
  - `7` = 3.5 pips
  - `8` = 4 pips

#### `power_distribution`
- **Label**: Power distribution
- **Type**: `enum`
- **Tier**: detail
- **Values**: 5 options
  - `balanced` = Balanced
  - `defensive` = Defensive
  - `aggressive` = Aggressive
  - `evasive` = Evasive
  - `custom` = Custom

#### `refuel_status`
- **Label**: Refuel status
- **Type**: `enum`
- **Tier**: detail
- **Values**: 3 options
  - `none` = None
  - `partial_refueled` = Partial refuel
  - `full_refueled` = Full refuel

#### `repair_status`
- **Label**: Repair status
- **Type**: `enum`
- **Tier**: detail
- **Values**: 4 options
  - `none` = None
  - `module_repaired` = Module repaired
  - `full_repaired` = Full repair
  - `rebooting` = Rebooting

#### `shield_state`
- **Label**: Shield state
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `down` = Down
  - `up` = Up
  - `just_failed` = Just failed
  - `just_restored` = Just restored

#### `ship_cargo_capacity`
- **Label**: Cargo capacity
- **Type**: `number`
- **Tier**: detail

#### `ship_event`
- **Label**: Ship event
- **Type**: `enum`
- **Tier**: core
- **Values**: 37 options

#### `ship_fuel_capacity_main`
- **Label**: Main fuel capacity
- **Type**: `number`
- **Tier**: detail

#### `ship_fuel_capacity_reserve`
- **Label**: Reserve fuel capacity
- **Type**: `number`
- **Tier**: detail

#### `ship_hull_health`
- **Label**: Hull health %
- **Type**: `number`
- **Tier**: core

#### `ship_hull_value`
- **Label**: Hull value
- **Type**: `number`
- **Tier**: detail

#### `ship_ident`
- **Label**: Ship ID
- **Type**: `string`
- **Tier**: detail

#### `ship_max_jump_range`
- **Label**: Max jump range
- **Type**: `number`
- **Tier**: detail

#### `ship_modules_value`
- **Label**: Modules value
- **Type**: `number`
- **Tier**: detail

#### `ship_name`
- **Label**: Ship name
- **Type**: `string`
- **Tier**: core

#### `ship_purchase_activity`
- **Label**: Ship purchase activity
- **Type**: `enum`
- **Tier**: core
- **Values**: 6 options
  - `none` = None
  - `bought` = Ship bought
  - `sold` = Ship sold
  - `swapped` = Ship swapped
  - `transferred` = Transfer initiated
  - `renamed` = Ship renamed

#### `ship_rebuy_cost`
- **Label**: Rebuy cost
- **Type**: `number`
- **Tier**: detail

#### `ship_status`
- **Label**: Ship legal status
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `clean` = Clean
  - `wanted` = Wanted

#### `ship_type`
- **Label**: Ship model
- **Type**: `enum`
- **Tier**: core
- **Values**: 42 options

#### `ship_unladen_mass`
- **Label**: Unladen mass
- **Type**: `number`
- **Tier**: detail

#### `silent_running`
- **Label**: Silent running
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `off` = Off
  - `on` = Active

#### `status`
- **Label**: Status
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `safe` = Safe
  - `in_danger` = In danger
  - `under_attack` = Under attack
  - `being_interdicted` = Being Interdicted

#### `target_bounty`
- **Label**: Target bounty value
- **Type**: `number`
- **Tier**: detail

#### `target_faction`
- **Label**: Target faction
- **Type**: `string`
- **Tier**: detail

#### `target_hull_health`
- **Label**: Target hull health %
- **Type**: `number`
- **Tier**: detail

#### `target_legal_status`
- **Label**: Target legal status
- **Type**: `enum`
- **Tier**: detail
- **Values**: 4 options
  - `unknown` = Unknown
  - `clean` = Clean
  - `wanted` = Wanted
  - `lawless` = Lawless

#### `target_locked`
- **Label**: Target locked
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `target_pilot_name`
- **Label**: Target pilot name
- **Type**: `string`
- **Tier**: detail

#### `target_pilot_rank`
- **Label**: Target pilot rank
- **Type**: `enum`
- **Tier**: detail
- **Values**: 10 options
  - `unknown` = Unknown
  - `harmless` = Harmless
  - `mostly_harmless` = Mostly Harmless
  - `novice` = Novice
  - `competent` = Competent
  - `expert` = Expert
  - `master` = Master
  - `dangerous` = Dangerous
  - `deadly` = Deadly
  - `elite` = Elite

#### `target_scan_stage`
- **Label**: Target scan stage
- **Type**: `number`
- **Tier**: detail

#### `target_shield_health`
- **Label**: Target shield health %
- **Type**: `number`
- **Tier**: detail

#### `target_ship_type`
- **Label**: Target ship type
- **Type**: `enum`
- **Tier**: detail
- **Values**: 42 options

#### `target_state`
- **Label**: Target state
- **Type**: `enum`
- **Tier**: detail
- **Values**: 3 options
  - `none` = No target
  - `locked` = Locked
  - `lost` = Lost

#### `target_subsystem`
- **Label**: Targeted subsystem
- **Type**: `enum`
- **Tier**: detail
- **Values**: 11 options

#### `target_subsystem_health`
- **Label**: Subsystem health %
- **Type**: `number`
- **Tier**: detail

### Squadron (4 signals)

#### `in_squadron`
- **Label**: In a squadron
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `squadron_activity`
- **Label**: Squadron activity
- **Type**: `enum`
- **Tier**: core
- **Values**: 13 options

#### `squadron_name`
- **Label**: Squadron name
- **Type**: `string`
- **Tier**: core

#### `squadron_rank`
- **Label**: Squadron rank
- **Type**: `number`
- **Tier**: detail

### Statistics (11 signals)

#### `stat_bounty_hunting_profit`
- **Label**: Bounty hunting profit
- **Type**: `number`
- **Tier**: detail

#### `stat_combat_bonds`
- **Label**: Combat bonds earned
- **Type**: `number`
- **Tier**: detail

#### `stat_exploration_profit`
- **Label**: Exploration profits
- **Type**: `number`
- **Tier**: detail

#### `stat_hyperspace_jumps`
- **Label**: Total jumps
- **Type**: `number`
- **Tier**: detail

#### `stat_insurance_claims`
- **Label**: Insurance claims
- **Type**: `number`
- **Tier**: detail

#### `stat_mining_profit`
- **Label**: Mining profits
- **Type**: `number`
- **Tier**: detail

#### `stat_spent_on_ships`
- **Label**: Spent on ships
- **Type**: `number`
- **Tier**: detail

#### `stat_systems_visited`
- **Label**: Systems visited
- **Type**: `number`
- **Tier**: detail

#### `stat_time_played`
- **Label**: Time played (seconds)
- **Type**: `number`
- **Tier**: detail

#### `stat_total_wealth`
- **Label**: Current wealth
- **Type**: `number`
- **Tier**: detail

#### `stat_trading_profit`
- **Label**: Market profits
- **Type**: `number`
- **Tier**: detail

### Trading (1 signals)

#### `trading_event`
- **Label**: Trading event
- **Type**: `enum`
- **Tier**: core
- **Values**: 11 options

### Travel (14 signals)

#### `destination_system`
- **Label**: Destination system
- **Type**: `string`
- **Tier**: detail

#### `exploration_event`
- **Label**: Exploration event
- **Type**: `enum`
- **Tier**: core
- **Values**: 18 options

#### `flag_altitude_from_avg_radius`
- **Label**: Altitude from radius
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `flag_hud_analysis_mode`
- **Label**: Analysis mode
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `flag_in_danger`
- **Label**: In danger
- **Type**: `enum`
- **Tier**: advanced
- **Values**: 2 options
  - `safe` = Safe
  - `danger` = Danger

#### `fsd_target_remaining_jumps`
- **Label**: Jumps to FSD target
- **Type**: `number`
- **Tier**: detail

#### `fsd_target_system`
- **Label**: FSD target system
- **Type**: `string`
- **Tier**: core

#### `has_route`
- **Label**: Route plotted
- **Type**: `enum`
- **Tier**: core
- **Values**: 2 options
  - `no` = No
  - `yes` = Yes

#### `jet_cone_boost_state`
- **Label**: Jet cone boost
- **Type**: `enum`
- **Tier**: detail
- **Values**: 3 options
  - `none` = None
  - `boosted` = Boosted
  - `damaged` = Damaged

#### `jump_type`
- **Label**: Jump type
- **Type**: `enum`
- **Tier**: detail
- **Values**: 3 options
  - `none` = None
  - `hyperspace` = Hyperspace
  - `supercruise` = Supercruise

#### `next_system_in_route`
- **Label**: Next system in route
- **Type**: `string`
- **Tier**: core

#### `route_length`
- **Label**: Route jumps remaining
- **Type**: `number`
- **Tier**: core

#### `supercruise_state`
- **Label**: Supercruise state
- **Type**: `enum`
- **Tier**: core
- **Values**: 4 options
  - `off` = Normal space
  - `on` = Supercruise
  - `entering` = Entering
  - `exiting` = Exiting

#### `travel_event`
- **Label**: Travel event
- **Type**: `enum`
- **Tier**: core
- **Values**: 24 options

### Uncategorized (3 signals)

#### `commander_progress`
- **Label**: commander_progress
- **Type**: `unknown`
- **Tier**: core

#### `commander_promotion`
- **Label**: commander_promotion
- **Type**: `unknown`
- **Tier**: core

#### `commander_ranks`
- **Label**: commander_ranks
- **Type**: `unknown`
- **Tier**: core

