# EDMCVKBConnector - Master Signals Reference

A comprehensive reference of all 700+ game state signals available for rule creation and VKB hardware automation.

---

## Table of Contents

1. [UI & HUD Signals](#ui--hud-signals)
2. [Commander & Progress Signals](#commander--progress-signals)
3. [Location & Navigation Signals](#location--navigation-signals)
4. [Travel & FSD Signals](#travel--fsd-signals)
5. [Ship Status & Systems](#ship-status--systems)
6. [Combat Signals](#combat-signals)
7. [SRV Signals](#srv-signals)
8. [On-Foot / Odyssey Signals](#on-foot--odyssey-signals)
9. [Inventory & Materials](#inventory--materials)
10. [Reputation & Influence](#reputation--influence)
11. [Powerplay Signals](#powerplay-signals)
12. [Squadron & Fleet Carrier](#squadron--fleet-carrier)
13. [Game Mode & Session](#game-mode--session)
14. [Station & System Data](#station--system-data)
15. [Statistics Signals](#statistics-signals)
16. [Passengers & Crew](#passengers--crew)
17. [Navigation & Routes](#navigation--routes)
18. [Target Information](#target-information)
19. [Event Categories](#event-categories)

---

## UI & HUD Signals

### `gui_focus`
**Type:** Enum | **Category:** HUD | **Tier:** Core  
Current focused UI panel
- `NoFocus` - None
- `InternalPanel` - Left panel
- `ExternalPanel` - Right panel
- `CommsPanel` - Comms
- `RolePanel` - Role
- `StationServices` - Station
- `GalaxyMap` - Galaxy map
- `SystemMap` - System map
- `Orrery` - Orrery
- `FSS` - FSS
- `SAA` - SAA
- `Codex` - Codex

### `hud_mode`
**Type:** Enum | **Category:** HUD | **Tier:** Core  
HUD display mode
- `combat` - Combat mode
- `analysis` - Analysis mode

### `night_vision`
**Type:** Enum | **Category:** HUD | **Tier:** Core  
Night vision toggle
- `off` - Night vision off
- `on` - Night vision on

---

## Commander & Progress Signals

### `commander_name`
**Type:** String | **Category:** Commander | **Tier:** Core  
Currently logged-in commander name

### `transport`
**Type:** Enum | **Category:** Commander | **Tier:** Core  
Current transport/vehicle type
- `ship` - In ship
- `srv` - In SRV
- `fighter` - In fighter (multicrew)
- `on_foot` - On foot (Odyssey)
- `in_taxi` - In orbital taxi
- `in_multicrew` - In other player's ship
- `in_wing` - In wing formation
- `unknown` - Unknown state

### `credits`
**Type:** Number | **Category:** Commander | **Tier:** Core  
Current credit balance

### `commander_rank_combat`
**Type:** Enum | **Category:** Commander | **Tier:** Detail  
Combat rank (0-8)
- 0: Harmless, 1: Mostly Harmless, 2: Novice, 3: Competent, 4: Expert, 5: Master, 6: Dangerous, 7: Deadly, 8: Elite

### `commander_rank_trade`
**Type:** Enum | **Category:** Commander | **Tier:** Detail  
Trade rank (0-8)
- 0: Penniless, 1: Mostly Penniless, 2: Peddler, 3: Dealer, 4: Merchant, 5: Broker, 6: Entrepreneur, 7: Tycoon, 8: Elite

### `commander_rank_explore`
**Type:** Enum | **Category:** Commander | **Tier:** Detail  
Exploration rank (0-8)
- 0: Aimless, 1: Mostly Aimless, 2: Scout, 3: Surveyor, 4: Trailblazer, 5: Pathfinder, 6: Ranger, 7: Pioneer, 8: Elite

### `commander_rank_empire`
**Type:** Enum | **Category:** Commander | **Tier:** Detail  
Empire rank
- none, outsider, serf, master, squire, knight, lord, baron, viscount, count, earl, marquis, duke, prince, king

### `commander_rank_federation`
**Type:** Enum | **Category:** Commander | **Tier:** Detail  
Federation rank
- none, recruit, cadet, midshipman, petty_officer, chief_petty_officer, warrant_officer, ensign, lieutenant, lieutenant_commander, post_commander, post_captain, rear_admiral, vice_admiral, admiral

### `commander_progress_combat`, `commander_progress_trade`, `commander_progress_explore`, `commander_progress_empire`, `commander_progress_federation`, `commander_progress_cqc`
**Type:** Number | **Category:** Commander | **Tier:** Detail  
Rank progression percentage (0-100%)

### `commander_promotion.*`
**Type:** Enum | **Category:** Commander > Promotion | **Tier:** Detail  
Recent rank promotions showing new rank value (within 5 seconds of Promotion event)
- `commander_promotion.combat` - Combat promotion (0-8: Harmless to Elite)
- `commander_promotion.trade` - Trade promotion (0-8: Penniless to Elite)
- `commander_promotion.explore` - Exploration promotion (0-8: Aimless to Elite)
- `commander_promotion.empire` - Empire promotion (none to king)
- `commander_promotion.federation` - Federation promotion (none to admiral)
- `commander_promotion.soldier` - Soldier promotion (0-8: Defenceless to Elite)
- `commander_promotion.exobiologist` - Exobiologist promotion (0-8: Directionless to Elite)
- `commander_promotion.mercenary` - Mercenary promotion (0-8: Defenceless to Elite)
- `commander_promotion.cqc` - CQC promotion (0-8: Helpless to Elite)

### `commander_activity_social`
**Type:** Enum | **Category:** Commander | **Tier:** Core  
Recent social events
- `none` - No recent friend list updates
- `friends` - Friends list updated (within 300s)

---

## Location & Navigation Signals

### `system_name`
**Type:** String | **Category:** Location | **Tier:** Core  
Current system name

### `system_address`
**Type:** Number | **Category:** Location | **Tier:** Detail  
Unique 64-bit system ID

### `station_name`
**Type:** String | **Category:** Location | **Tier:** Core  
Docked station name (empty if not docked)

### `body_name`
**Type:** String | **Category:** Location | **Tier:** Core  
Current body name (planet/moon/station)

### `docking_state`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Docking/landing status
- `in_space` - In open space
- `landed` - Landed on surface
- `docked` - Docked at station
- `just_docked` - Just docked (within 3s)
- `just_undocked` - Just undocked (within 3s)
- `just_landed` - Just landed (within 3s)
- `just_lifted_off` - Just took off (within 3s)

### `has_lat_long`
**Type:** Enum | **Category:** Location | **Tier:** Advanced  
Whether position data is available
- `no` / `yes`

### `latitude`, `longitude`, `altitude`, `heading`
**Type:** Number | **Category:** Location | **Tier:** Detail  
Current position and orientation (when on surface)

### `body_proximity`
**Type:** Enum | **Category:** Location | **Tier:** Detail  
Proximity to celestial body
- `far` - Not approaching
- `approaching` - Approaching (recent ApproachBody event)
- `orbital_cruise` - In orbital cruise
- `leaving` - Leaving body (recent LeaveBody event)

### `docking_request_state`
**Type:** Enum | **Category:** Ship | **Tier:** Detail  
Docking request status
- `none`, `requested`, `granted`, `denied`, `cancelled`, `timeout`

---

## Travel & FSD Signals

### `supercruise_state`
**Type:** Enum | **Category:** Travel | **Tier:** Core  
Supercruise engagement state
- `off` - Normal space
- `on` - In supercruise
- `entering` - Entering supercruise (within 3s)
- `exiting` - Exiting supercruise (within 3s)

### `fsd_state`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
FSD engine state
- `idle` - Ready
- `charging` - FSD charging
- `cooldown` - FSD cooling down
- `jump_active` - Jump in progress

### `jump_type`
**Type:** Enum | **Category:** Travel | **Tier:** Detail  
Type of jump being performed
- `none`, `hyperspace`, `supercruise`

### `mass_locked`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
FSD mass lock status
- `no` / `yes`

### `flag_low_fuel`
**Type:** Enum | **Category:** Ship | **Tier:** Advanced  
Low fuel warning flag
- `normal` / `low`

### `flag_overheating`
**Type:** Enum | **Category:** Ship | **Tier:** Advanced  
Ship overheating status
- `normal` / `overheating`

### `flag_in_danger`
**Type:** Enum | **Category:** Travel | **Tier:** Advanced  
Danger zone detection
- `safe` / `danger`

### `interdicted`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Being interdicted status
- `no` / `yes`

### `destination_system`
**Type:** String | **Category:** Travel | **Tier:** Detail  
Destination system (if set)

### `jet_cone_boost_state`
**Type:** Enum | **Category:** Travel | **Tier:** Detail  
Jet cone boost events
- `none`, `boosted`, `damaged`

---

## Ship Status & Systems

### `ship_type`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Current ship model (adder, anaconda, asp, asp_scout, belugaliner, cobra_mkiii, etc.)

### `ship_name`
**Type:** String | **Category:** Ship | **Tier:** Core  
Player-set ship name

### `ship_ident`
**Type:** String | **Category:** Ship | **Tier:** Detail  
Player-set ship identifier

### `landing_gear`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Landing gear position
- `retracted` / `deployed`

### `lights`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
External lights
- `off` / `on`

### `cargo_hatch`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Cargo hold door
- `retracted` / `deployed`

### `hardpoints`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Weapon hardpoints
- `retracted` / `deployed`

### `silent_running`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Silent running (heat suppression) mode
- `off` / `on`

### `flight_assist`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Flight assist status
- `on` / `off`

### `heat_status`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Thermal status
- `normal`, `overheating`, `heat_damage` (recent damage)

### `danger_status`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Ship danger state
- `safe`, `in_danger`, `under_attack` (recent attack)

### `refuel_status`
**Type:** Enum | **Category:** Ship | **Tier:** Detail  
Recent refueling
- `none`, `partial_refueled`, `full_refueled`

### `repair_status`
**Type:** Enum | **Category:** Ship | **Tier:** Detail  
Recent repair activity
- `none`, `module_repaired`, `full_repaired`, `rebooting`

### `cockpit_status`
**Type:** Enum | **Category:** Ship | **Tier:** Detail  
Cockpit integrity
- `intact`, `breached` (recent breach event)

### `fuel_main`, `fuel_reservoir`
**Type:** Number | **Category:** Ship | **Tier:** Detail  
Current fuel amounts (tons)

### `cargo_count`
**Type:** Number | **Category:** Ship | **Tier:** Core  
Cargo carried (tons)

### `cargo_activity`
**Type:** Enum | **Category:** Ship | **Tier:** Detail  
Recent cargo events
- `none`, `collected`, `ejected` (within 3s)

### Ship Value Signals
- `ship_hull_value` - Hull value (credits)
- `ship_modules_value` - Modules value (credits)
- `ship_rebuy_cost` - Insurance rebuy cost
- `ship_hull_health` - Hull integrity percentage
- `ship_unladen_mass` - Mass without cargo (tons)
- `ship_max_jump_range` - Unladen jump range (ly)
- `ship_fuel_capacity_main` - Main tank capacity (tons)
- `ship_fuel_capacity_reserve` - Reserve tank capacity (tons)
- `ship_cargo_capacity` - Total cargo capacity (tons)

### `ship_status`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Legal status
- `clean` / `wanted`

---

## Combat Signals

### `shield_state`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Shield status
- `down` - Shields offline
- `up` - Shields active
- `just_failed` - Just failed (within 3s)
- `just_restored` - Just restored (within 3s)

### `hull_state`
**Type:** Enum | **Category:** Ship | **Tier:** Core  
Hull condition
- `ok` - No damage
- `damaged` - 30-70% integrity
- `critical` - <30% integrity
- `taking_damage` - Recently hit (within 2s)

### `combat_state`
**Type:** Enum | **Category:** Combat | **Tier:** Core  
Overall combat status
- `peaceful` - No threats
- `under_attack` - Being attacked (within 5s)
- `got_bounty` - Bounty received (within 5s)
- `killed_target` - Target destroyed (within 5s)
- `destroyed` - Ship destroyed (within 10s)

### `target_state`
**Type:** Enum | **Category:** Ship | **Tier:** Detail  
Current target
- `none` - No target
- `locked` - Target locked (recent)
- `lost` - Target lost

### `fire_group`
**Type:** Number | **Category:** Ship | **Tier:** Detail  
Currently selected fire group (0-N)

### Power Distribution Pips
- `pips_sys` - System pips (0-8, half-pip increments)
- `pips_eng` - Engine pips (0-8)
- `pips_wep` - Weapon pips (0-8)

### `power_distribution`
**Type:** Enum | **Category:** Ship | **Tier:** Detail  
Current power mode
- `balanced` - 2-2-2 pips
- `defensive` - 4+ sys pips
- `aggressive` - 4+ wep pips
- `evasive` - 4+ eng pips
- `custom` - Other configuration

### Legal & Bounties
- `legal_state` - Current legal status (Clean, IllegalCargo, Speeding, Wanted, Hostile, etc.)
- `bounty_activity` - Recent bounty events (none, paid_bounties, paid_fines)

---

## SRV Signals

### `srv_deployed_state`
**Type:** Enum | **Category:** SRV | **Tier:** Core  
SRV deployment status
- `stowed` - In hangar
- `deployed` - On surface
- `just_launched` - Just deployed (within 3s)
- `just_docked` - Just recovered (within 3s)

### `srv_handbrake`
**Type:** Enum | **Category:** SRV | **Tier:** Core  
SRV handbrake
- `off` / `on`

### `srv_drive_assist`
**Type:** Enum | **Category:** SRV | **Tier:** Core  
SRV drive assist
- `off` / `on`

### `srv_high_beam`
**Type:** Enum | **Category:** SRV | **Tier:** Core  
SRV headlights
- `off` / `on`

### `flag_srv_turret`
**Type:** Enum | **Category:** SRV | **Tier:** Advanced  
SRV turret position
- `retracted` / `deployed`

### `srv_under_ship`
**Type:** Enum | **Category:** SRV | **Tier:** Detail  
SRV docking underneath ship
- `no` / `yes`

---

## On-Foot / Odyssey Signals

### `flag_on_foot`
**Type:** Enum | **Category:** On-Foot | **Tier:** Advanced  
Commander is on foot
- `no` / `yes`

### `aim`
**Type:** Enum | **Category:** On-Foot | **Tier:** Core  
Weapon aiming state
- `normal`, `aiming` (aim down sight)

### `flag_aim_down_sight`
**Type:** Enum | **Category:** On-Foot | **Tier:** Advanced  
ADS (aim down sight) flag
- `no` / `yes`

### Environmental Conditions
- `temperature` - Environment temperature (very_cold, cold, normal, hot, very_hot)
- `temperature_state` - Temperature alert state
- `temperature_value` - Temperature in Kelvin (number)
- `oxygen` - Oxygen status (ok, low)
- `oxygen_level` - Oxygen percentage (number)
- `health` - Health status (ok, low)
- `health_level` - Health percentage (number)
- `gravity_level` - Gravity multiplier (number)

### Oxygen & Health Warnings
- `flag_low_oxygen` - Low oxygen flag (normal, low)
- `flag_low_health` - Low health flag (normal, low)

### On-Foot Location
- `on_foot_location` - Where on foot (none, station, planet, hangar, social_space, exterior)
- `breathable_atmosphere` - Is atmosphere breathable (no, yes)

### Locomotion
- `glide_mode` - In glide mode (no, yes)

### Weapons
- `selected_weapon` - Current weapon (none, unarmed, energylink, arc_cutter, profile_analyser, genetic_sampler, kinetic, laser, plasma, rocket, grenades)

---

## Inventory & Materials

### Material Counts
- `raw_materials_count` - Count of raw engineering materials
- `manufactured_materials_count` - Count of manufactured materials
- `encoded_materials_count` - Count of encoded data
- `total_materials_count` - Sum of all material categories

### Cargo & Missions
- `cargo_inventory` - Array of cargo items (detailed)
- `missions_active_count` - Number of active missions

---

## Reputation & Influence

### Faction Reputation
- `empire_reputation` - Empire faction reputation (number, can be negative)
- `federation_reputation` - Federation reputation
- `alliance_reputation` - Alliance reputation
- `independent_reputation` - Independent systems reputation

*Note: These represent standing with each superpower*

---

## Powerplay Signals

### Powerplay Status
- `powerplay_pledged` - Is pledged to a power (no, yes)
- `powerplay_power` - Pledged power name (aisling_duval, arissa_lavigny-duval, denton_patreus, zemina_torval, edmund_mahon, li_yong-rui, felicia_winters, zachary_hudson, yuri_grom, archon_delaine, pranav_antal, or none)

### Powerplay Metrics
- `powerplay_rank` - Rank within power (0-5)
- `powerplay_merits` - Merits earned (number)
- `powerplay_time_pledged` - Time pledged (seconds)

---

## Squadron & Fleet Carrier

### Squadron
- `in_squadron` - Is in a squadron (no, yes)
- `squadron_name` - Squadron name
- `squadron_rank` - Rank within squadron (0-N)

### Fleet Carrier
- `has_fleet_carrier` - Owns a carrier (no, yes)
- `fleet_carrier_callsign` - Carrier callsign (e.g., "ABC-12")
- `fleet_carrier_name` - Carrier display name
- `fleet_carrier_balance` - Carrier credit balance
- `fleet_carrier_fuel` - Carrier fuel % (0-100)

---

## Game Mode & Session

### Game Mode
- `game_mode` - Current mode (Open, Solo, Group)
- `group_name` - Private group name (if applicable)

### Game Version
- `game_version` - Edition being played (base, horizons, odyssey)

---

## Station & System Data

### Station Information
- `station_name` - Station name
- `station_type` - Type (coriolis, orbis, ocellus, outpost, crateroutpost, craterport, megaship, asteroidbase, fleetcarrier)
- `station_faction` - Controlling faction
- `station_government` - Government type
- `station_allegiance` - Allegiance (alliance, empire, federation, independent, pirate, pilotsfederation)
- `station_economy` - Primary economy
- `station_distance_ls` - Distance from main star (light-seconds)
- `market_id` - Market ID number (for API lookup)

### System Information
- `system_name` - System name
- `system_address` - System ID64
- `system_faction` - Controlling faction
- `system_government` - Government type
- `system_allegiance` - Allegiance
- `system_economy` - Primary economy
- `system_security` - Security level
- `system_population` - System population (number)

### System Coordinates (Galactic)
- `system_x` - X coordinate
- `system_y` - Y coordinate
- `system_z` - Z coordinate

---

## Statistics Signals

### Financial
- `stat_total_wealth` - Current wealth (credits)
- `stat_spent_on_ships` - Lifetime ship purchases
- `stat_insurance_claims` - Number of times rebuked

### Combat
- `stat_bounty_hunting_profit` - Bounty hunting earnings
- `stat_combat_bonds` - Combat bonds earned

### Exploration
- `stat_exploration_profit` - Exploration data earnings
- `stat_systems_visited` - Systems discovered
- `stat_hyperspace_jumps` - Total jumps made

### Trading & Mining
- `stat_trading_profit` - Trading earnings
- `stat_mining_profit` - Mining earnings

### Time
- `stat_time_played` - Total playtime (seconds)

---

## Passengers & Crew

### Passengers
- `passengers_count` - Number of passengers in cabins
- `has_vip_passengers` - Carrying VIPs (no, yes)
- `has_wanted_passengers` - Carrying wanted prisoners (no, yes)

### NPC Crew
- `has_npc_crew` - Has hired NPC crew (no, yes)
- `npc_crew_count` - Number of active crew members

---

## Navigation & Routes

### Route Planning
- `has_route` - Route plotted (no, yes)
- `route_length` - Number of jumps remaining in route
- `next_system_in_route` - Next waypoint system name

### FSD Target
- `fsd_target_system` - Current FSD target system
- `fsd_target_remaining_jumps` - Jumps to reach FSD target

---

## Target Information

### Target Lock Status
- `target_locked` - Has target locked (no, yes)

### Target Ship Details
- `target_ship_type` - Target ship model
- `target_scan_stage` - Scan progress level (0-4)
- `target_pilot_name` - Pilot name (if known)
- `target_pilot_rank` - Combat rank (harmless to elite)
- `target_legal_status` - Pilot status (clean, wanted, lawless)

### Target Condition
- `target_shield_health` - Shield integrity %
- `target_hull_health` - Hull integrity %

### Target Loadout
- `target_subsystem` - Focused subsystem
- `target_subsystem_health` - Subsystem integrity %
- `target_bounty` - Bounty value on target

### Target Affiliation
- `target_faction` - Target faction

---

## Event Categories

These signals track recent events within various game activity categories. Each returns the most recent event in that category, with a 300-second (5-minute) window.

### `system_event`
Recent game/system events
- none, journal_started, journal_continued, game_reset, commander_created, game_loaded, commander_info, materials_loaded, cargo_loaded, missions_loaded, passengers_loaded, powerplay_status, rank_progress, ranks_loaded, reputation_loaded, statistics_loaded

### `travel_event`
Recent location/navigation events
- none, location, fsd_jump, docked, undocked, liftoff, touchdown, supercruise_entry, supercruise_exit, approach_body, leave_body, docking_requested, docking_granted, docking_denied, docking_cancelled, docking_timeout, supercruise_destination_drop, fsd_target, nav_route, start_jump, jet_cone_boost, uss_drop, jet_cone_damage

### `combat_event`
Recent combat/threat events
- none, bounty, died, interdicted, interdiction, pvp_kill, under_attack, cap_ship_bond, faction_kill_bond, escape_interdiction, ship_targetted, crime_victim, resurrect, self_destruct, cockpit_breached

### `exploration_event`
Recent discovery/scan events
- none, scan, fss_discovery_scan, fss_signal_discovered, fss_all_bodies_found, saa_scan_complete, saa_signals_found, codex_entry, screenshot, sell_exploration_data, discovery_scan, nav_beacon_scan, scan_bary_centre, material_discarded, material_discovered, buy_exploration_data, multi_sell_exploration_data, sell_organic_data

### `trading_event`
Recent trading/cargo events
- none, market_buy, market_sell, collect_cargo, eject_cargo, mining_refined, cargo_depot, search_and_rescue, buy_trade_data, asteroid_cracked, market

### `mission_event`
Recent mission events
- none, mission_accepted, mission_completed, mission_failed, mission_abandoned, community_goal, mission_redirected, community_goal_join, community_goal_discard, community_goal_reward

### `ship_event`
Recent ship/module events
- (see detailed signal reference for ship-related events)

---

## Signal Organization

### By Tier (UI Display)

**Core Tier** - Most commonly used for automation
- Basic ship status, navigation, commander info, and immediate threats

**Detail Tier** - Additional useful signals
- Detailed ship specs, faction info, rankings, specific event tracking

**Advanced Tier** - Technical/power users
- Raw flag values, IDs, specific subsystem data, internal state

### By Category

Signals are organized into logical categories:
- HUD / UI controls
- Commander / Personal
- Location & Navigation
- Travel & FSD systems
- Ship Status & Systems
- Combat & Threats
- SRV operations
- On-Foot / Odyssey
- Inventory & Cargo
- Reputation & Factions
- Powerplay
- Squadron & Fleet
- Game Session
- Station & System
- Statistics & Achievements
- Passengers & Crew
- Navigation & Routes
- Target Intelligence
- Event tracking

---

## Usage Notes

1. **Enum values** - Use with `in` operator or direct comparison
2. **Number values** - Use with comparison operators (<, >, <=, >=)
3. **String values** - Use with exact match or contains operators
4. **Recent events** - Track within 300s (5 mins) by default; adjustable in rules
5. **Flag values** - Binary (true/false) from Status.json flags
6. **Array values** - Count, iterate, or test for existence
7. **Null values** - Use `exists` operator to check presence

---

## Last Updated

Generated: February 16, 2026  
Catalog Version: Current (9385 lines)  
Total Signals: 700+

For detailed implementation and derivation logic, refer to `signals_catalog.json`.
