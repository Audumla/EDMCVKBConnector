# EDMC Event Catalog - Complete Reference

This document catalogs all unique Elite Dangerous Market Connector (EDMC) journal events referenced in the signals catalog, organized by gameplay category for comprehensive test coverage.

## Table of Contents

- [Session Management](#session-management)
- [Navigation & Travel](#navigation--travel)
- [Docking & Station Services](#docking--station-services)
- [Supercruise & FSD](#supercruise--fsd)
- [Exploration & Scanning](#exploration--scanning)
- [Combat](#combat)
- [Trading & Cargo](#trading--cargo)
- [Mining](#mining)
- [Missions](#missions)
- [Ship Management](#ship-management)
- [Outfitting & Modules](#outfitting--modules)
- [Engineering & Crafting](#engineering--crafting)
- [SRV & Fighters](#srv--fighters)
- [Multicrew](#multicrew)
- [Fleet Carrier](#fleet-carrier)
- [Powerplay](#powerplay)
- [Squadron](#squadron)
- [Odyssey - On Foot](#odyssey---on-foot)
- [Odyssey - Equipment](#odyssey---equipment)
- [Odyssey - Settlements](#odyssey---settlements)
- [Financial](#financial)
- [Community Goals](#community-goals)
- [Communications](#communications)
- [Miscellaneous](#miscellaneous)

---

## Session Management

Events related to game session startup, continuation, and save management.

### FileHeader
- **When:** Start of a new journal file
- **Affects Signals:** `event_fileheader`
- **Description:** Logged at the start of each new journal file, contains game version and build info
- **Test Priority:** HIGH - Session initialization

### Continued
- **When:** Journal file continues from a previous session
- **Affects Signals:** `event_continued`
- **Description:** Logged when opening a continuation journal file
- **Test Priority:** MEDIUM

### LoadGame
- **When:** Commander loads into the game
- **Affects Signals:** `event_loadgame`, commander data, ship data
- **Description:** Fired when commander loads, contains comprehensive commander and ship info
- **Test Priority:** HIGH - Session initialization

### ClearSavedGame
- **When:** Save game data is cleared
- **Affects Signals:** `event_clearsavedgame`
- **Description:** Rare event when clearing save data
- **Test Priority:** LOW

### NewCommander
- **When:** New commander is created
- **Affects Signals:** `event_newcommander`
- **Description:** First-time commander creation
- **Test Priority:** LOW

### Commander
- **When:** Commander information update
- **Affects Signals:** `event_commander`, `commander_name`
- **Description:** Updates to commander profile information
- **Test Priority:** MEDIUM

---

## Navigation & Travel

Events related to system/station location and general travel.

### Location
- **When:** Game start or respawn with current location
- **Affects Signals:** `event_location`, `system_name`, `station_name`
- **Description:** Provides current system/station location at startup
- **Test Priority:** HIGH - Core navigation

### FSDJump
- **When:** Hyperspace jump completes
- **Affects Signals:** `event_fsdjump`, `fsd_state`, `system_name`, `body_name`
- **Description:** Fired after successful hyperspace jump to new system
- **Test Priority:** HIGH - Core navigation

### CarrierJump
- **When:** Fleet carrier jumps to new system
- **Affects Signals:** `event_carrierjump`, `system_name`
- **Description:** Fired when aboard a carrier that jumps
- **Test Priority:** MEDIUM

### StartJump
- **When:** FSD jump or supercruise begins charging
- **Affects Signals:** `event_startjump`, `jump_type`, `fsd_state`
- **Description:** Indicates jump type (Hyperspace or Supercruise) when FSD starts charging
- **Test Priority:** HIGH - Jump detection

### ApproachBody
- **When:** Ship approaches a body (planet/moon)
- **Affects Signals:** `event_approachbody`, `body_proximity`, `body_name`
- **Description:** Fired when getting close to a celestial body
- **Test Priority:** MEDIUM

### LeaveBody
- **When:** Ship leaves a body's vicinity
- **Affects Signals:** `event_leavebody`, `body_proximity`
- **Description:** Fired when departing from a celestial body
- **Test Priority:** MEDIUM

### NavRoute
- **When:** Navigation route is calculated or updated
- **Affects Signals:** `event_navroute`
- **Description:** Galaxy map plot route information
- **Test Priority:** LOW

### FSDTarget
- **When:** FSD target is selected
- **Affects Signals:** `event_fsdtarget`
- **Description:** Target system for next jump
- **Test Priority:** LOW

### USSDrop
- **When:** Drop into Unidentified Signal Source
- **Affects Signals:** `event_ussdrop`
- **Description:** Entering a USS in supercruise
- **Test Priority:** MEDIUM

---

## Docking & Station Services

Events related to docking, landing, and station interactions.

### Docked
- **When:** Ship docks at station/outpost/carrier
- **Affects Signals:** `docking_state`, `flag_docked`, `station_name`
- **Description:** Successful docking completion
- **Test Priority:** HIGH - Core station interaction

### Undocked
- **When:** Ship undocks from station
- **Affects Signals:** `docking_state`, `flag_docked`
- **Description:** Departure from docking bay
- **Test Priority:** HIGH - Core station interaction

### DockingRequested
- **When:** Docking permission is requested
- **Affects Signals:** `docking_request_state`
- **Description:** Commander requests docking clearance
- **Test Priority:** HIGH - Docking sequence

### DockingGranted
- **When:** Docking permission granted
- **Affects Signals:** `docking_request_state`
- **Description:** Station grants docking permission with pad assignment
- **Test Priority:** HIGH - Docking sequence

### DockingDenied
- **When:** Docking permission denied
- **Affects Signals:** `docking_request_state`
- **Description:** Docking refused (station full, hostile, etc.)
- **Test Priority:** MEDIUM

### DockingCancelled
- **When:** Docking request cancelled
- **Affects Signals:** `docking_request_state`
- **Description:** Commander or station cancels docking
- **Test Priority:** MEDIUM

### DockingTimeout
- **When:** Docking permission times out
- **Affects Signals:** `docking_request_state`
- **Description:** Failed to dock within time limit
- **Test Priority:** MEDIUM

### Touchdown
- **When:** Ship lands on planet surface
- **Affects Signals:** `docking_state`, `flag_landed`
- **Description:** Planetary landing complete
- **Test Priority:** HIGH - Surface operations

### Liftoff
- **When:** Ship takes off from surface
- **Affects Signals:** `docking_state`, `flag_landed`
- **Description:** Departing from planetary surface
- **Test Priority:** HIGH - Surface operations

---

## Supercruise & FSD

Events related to supercruise and frame shift drive operations.

### SupercruiseEntry
- **When:** Ship enters supercruise
- **Affects Signals:** `supercruise_state`, `fsd_state`
- **Description:** Transition to supercruise mode
- **Test Priority:** HIGH - Core travel

### SupercruiseExit
- **When:** Ship exits supercruise
- **Affects Signals:** `supercruise_state`, `fsd_state`
- **Description:** Dropping from supercruise to normal space
- **Test Priority:** HIGH - Core travel

### SupercruiseDestinationDrop
- **When:** Auto-drop at destination
- **Affects Signals:** `event_supercruisedestinationdrop`
- **Description:** Automatic supercruise exit at targeted destination
- **Test Priority:** MEDIUM

### FuelScoop
- **When:** Fuel scooping from star
- **Affects Signals:** `event_fuelscoop`, `fuel_scoop_activity`, `flag_scooping_fuel`
- **Description:** Refueling from main sequence star
- **Test Priority:** HIGH - Fuel management

### JetConeBoost
- **When:** FSD boost from neutron star/white dwarf
- **Affects Signals:** `event_jetconeboost`, `jet_cone_activity`
- **Description:** Supercharged FSD from jet cone
- **Test Priority:** MEDIUM

### JetConeDamage
- **When:** Ship takes damage from jet cone
- **Affects Signals:** `event_jetconedamage`, `jet_cone_activity`
- **Description:** Hull/module damage from cone supercharging
- **Test Priority:** MEDIUM

---

## Exploration & Scanning

Events related to discovery, scanning, and exploration activities.

### Scan
- **When:** Body is scanned (detailed surface scan)
- **Affects Signals:** `event_scan`, `scan_activity`
- **Description:** Detailed scan of celestial body
- **Test Priority:** HIGH - Core exploration

### FSSDiscoveryScan
- **When:** Full Spectrum System Scanner used
- **Affects Signals:** `event_fssdiscoveryscan`, `scan_activity`
- **Description:** Honking the system scanner
- **Test Priority:** HIGH - Core exploration

### FSSSignalDiscovered
- **When:** Signal discovered in FSS
- **Affects Signals:** `event_fsssignaldiscovered`, `scan_activity`
- **Description:** Finding signals/bodies in FSS mode
- **Test Priority:** MEDIUM

### FSSAllBodiesFound
- **When:** All bodies in system discovered
- **Affects Signals:** `event_fssallbodiesfound`, `scan_activity`
- **Description:** Complete system discovery achievement
- **Test Priority:** LOW

### SAAScanComplete
- **When:** Detailed Surface Scanner probe scan complete
- **Affects Signals:** `event_saascancomplete`, `scan_activity`
- **Description:** Full mapping of body surface
- **Test Priority:** HIGH - Surface mapping

### SAASignalsFound
- **When:** Surface signals found during SAA scan
- **Affects Signals:** `event_saasignalsfound`
- **Description:** POIs discovered on body surface
- **Test Priority:** LOW

### ScanOrganic
- **When:** Organic lifeform scanned (Odyssey)
- **Affects Signals:** `event_scanorganic`, `scan_activity`
- **Description:** Biological scan of exobiology
- **Test Priority:** MEDIUM - Odyssey content

### SellExplorationData
- **When:** Exploration data sold at Universal Cartographics
- **Affects Signals:** `event_sellexplorationdata`, `scan_activity`
- **Description:** Cashing in exploration discoveries
- **Test Priority:** HIGH - Exploration workflow

### SellOrganicData
- **When:** Organic scan data sold
- **Affects Signals:** `event_sellorganicdata`
- **Description:** Selling exobiology discoveries
- **Test Priority:** MEDIUM - Odyssey content

### MultiSellExplorationData
- **When:** Multiple exploration data entries sold
- **Affects Signals:** `event_multisellexplorationdata`
- **Description:** Bulk sell of cartographic data
- **Test Priority:** MEDIUM

### BuyExplorationData
- **When:** System data purchased
- **Affects Signals:** `event_buyexplorationdata`
- **Description:** Purchasing system information
- **Test Priority:** LOW

### CodexEntry
- **When:** New codex entry discovered
- **Affects Signals:** `event_codexentry`
- **Description:** Notable stellar phenomena or other discoveries
- **Test Priority:** LOW

### Screenshot
- **When:** In-game screenshot taken
- **Affects Signals:** `event_screenshot`
- **Description:** Screenshots with location data
- **Test Priority:** LOW

### DiscoveryScan
- **When:** Initial honk scan (old scanner)
- **Affects Signals:** `event_discoveryscan`
- **Description:** Legacy discovery scanner event
- **Test Priority:** LOW - Deprecated

### NavBeaconScan
- **When:** Nav beacon scanned
- **Affects Signals:** `event_navbeaconscan`
- **Description:** Scanning station navigation beacon
- **Test Priority:** LOW

### ScanBaryCentre
- **When:** Barycentre scanned
- **Affects Signals:** `event_scanbarycentre`
- **Description:** Binary star system center of mass
- **Test Priority:** LOW

---

## Combat

Events related to combat, damage, and hostile encounters.

### UnderAttack
- **When:** Ship is under attack
- **Affects Signals:** `event_underattack`, `under_attack_activity`, `combat_state`
- **Description:** Taking hostile fire
- **Test Priority:** HIGH - Combat detection

### Bounty
- **When:** Bounty awarded for kill
- **Affects Signals:** `event_bounty`, `combat_state`
- **Description:** Combat bond payout for NPC kill
- **Test Priority:** HIGH - Combat rewards

### CapShipBond
- **When:** Capital ship combat bond
- **Affects Signals:** `event_capshipbond`
- **Description:** Reward for capital ship combat zone
- **Test Priority:** LOW

### FactionKillBond
- **When:** Faction combat bond awarded
- **Affects Signals:** `event_factionkillbond`
- **Description:** Payment for killing in conflict zone
- **Test Priority:** MEDIUM

### Died
- **When:** Commander dies / ship destroyed
- **Affects Signals:** `event_died`, `combat_state`
- **Description:** Ship destruction and rebuy
- **Test Priority:** HIGH - Critical event

### PVPKill
- **When:** Player kills another player
- **Affects Signals:** `event_pvpkill`, `combat_state`
- **Description:** PvP combat victory
- **Test Priority:** LOW

### Interdicted
- **When:** Interdicted by another ship
- **Affects Signals:** `event_interdicted`, `interdiction_state`
- **Description:** Being pulled from supercruise
- **Test Priority:** HIGH - Combat encounter

### Interdiction
- **When:** Successfully interdicting another ship
- **Affects Signals:** `event_interdiction`, `interdiction_state`
- **Description:** Pulling another ship from supercruise
- **Test Priority:** MEDIUM

### EscapeInterdiction
- **When:** Successfully escaping interdiction
- **Affects Signals:** `event_escapeinterdiction`, `interdiction_state`
- **Description:** Evading interdiction attempt
- **Test Priority:** MEDIUM

### HullDamage
- **When:** Hull takes damage
- **Affects Signals:** `event_hulldamage`, `hull_damage_activity`
- **Description:** Hull integrity reduced
- **Test Priority:** HIGH - Damage tracking

### ShieldState
- **When:** Shield state changes (up/down)
- **Affects Signals:** `event_shieldstate`, `shields_state`
- **Description:** Shields going up or collapsing
- **Test Priority:** HIGH - Combat state

### ShipTargetted
- **When:** Target lock on ship
- **Affects Signals:** `event_shiptargetted`, `target_state`
- **Description:** Targeting another vessel
- **Test Priority:** MEDIUM

### FighterDestroyed
- **When:** Fighter craft destroyed
- **Affects Signals:** `event_fighterdestroyed`
- **Description:** Ship-launched fighter destroyed
- **Test Priority:** LOW

### SRVDestroyed
- **When:** SRV destroyed
- **Affects Signals:** `event_srvdestroyed`
- **Description:** Surface Recon Vehicle destroyed
- **Test Priority:** LOW

### CrimeVictim
- **When:** Crime committed against you
- **Affects Signals:** `event_crimevictim`
- **Description:** Another commander's crime affecting you
- **Test Priority:** LOW

### CockpitBreached
- **When:** Canopy breached
- **Affects Signals:** `event_cockpitbreached`, `life_support_activity`
- **Description:** Canopy damage causing life support emergency
- **Test Priority:** MEDIUM

### SelfDestruct
- **When:** Self destruct initiated
- **Affects Signals:** `event_selfdestruct`
- **Description:** Commander triggers self destruct
- **Test Priority:** LOW

### Resurrect
- **When:** Commander respawns after death
- **Affects Signals:** `event_resurrect`
- **Description:** Post-death respawn at station
- **Test Priority:** MEDIUM

---

## Trading & Cargo

Events related to commodity trading and cargo management.

### MarketBuy
- **When:** Commodities purchased from market
- **Affects Signals:** `event_marketbuy`, `commodity_activity`
- **Description:** Buying goods at commodity market
- **Test Priority:** HIGH - Core trading

### MarketSell
- **When:** Commodities sold to market
- **Affects Signals:** `event_marketsell`, `commodity_activity`
- **Description:** Selling goods at commodity market
- **Test Priority:** HIGH - Core trading

### Market
- **When:** Market data accessed
- **Affects Signals:** `event_market`
- **Description:** Opening commodity market interface
- **Test Priority:** LOW

### CollectCargo
- **When:** Cargo scooped
- **Affects Signals:** `event_collectcargo`, `cargo_activity`
- **Description:** Collecting cargo from space
- **Test Priority:** HIGH - Cargo operations

### EjectCargo
- **When:** Cargo jettisoned
- **Affects Signals:** `event_ejectcargo`, `cargo_activity`
- **Description:** Dropping cargo from hold
- **Test Priority:** MEDIUM

### Cargo
- **When:** Cargo inventory state
- **Affects Signals:** `event_cargo`
- **Description:** Current cargo manifest
- **Test Priority:** MEDIUM

### CargoDepot
- **When:** Wing mission cargo delivery
- **Affects Signals:** `event_cargodepot`
- **Description:** Delivering cargo for wing missions
- **Test Priority:** LOW

### SearchAndRescue
- **When:** Search and rescue goods delivered
- **Affects Signals:** `event_searchandrescue`
- **Description:** Turning in damaged pods/black boxes
- **Test Priority:** MEDIUM

### BuyTradeData
- **When:** Trade data purchased
- **Affects Signals:** `event_buytradedata`
- **Description:** Buying market intelligence
- **Test Priority:** LOW

---

## Mining

Events related to mining operations.

### MiningRefined
- **When:** Refined ore collected
- **Affects Signals:** `event_miningrefined`, `commodity_activity`
- **Description:** Refinery processes asteroid fragments
- **Test Priority:** HIGH - Mining workflow

### AsteroidCracked
- **When:** Motherlode asteroid cracked
- **Affects Signals:** `event_asteroidcracked`
- **Description:** Deep core mining explosion successful
- **Test Priority:** MEDIUM - Mining mechanics

---

## Missions

Events related to mission lifecycle.

### MissionAccepted
- **When:** Mission accepted from mission board
- **Affects Signals:** `event_missionaccepted`, `mission_activity`
- **Description:** Commander takes on new mission
- **Test Priority:** HIGH - Mission workflow

### MissionCompleted
- **When:** Mission successfully completed
- **Affects Signals:** `event_missioncompleted`, `mission_activity`
- **Description:** Mission objectives fulfilled and rewards claimed
- **Test Priority:** HIGH - Mission workflow

### MissionFailed
- **When:** Mission failed
- **Affects Signals:** `event_missionfailed`, `mission_activity`
- **Description:** Mission objectives not met within time
- **Test Priority:** MEDIUM

### MissionAbandoned
- **When:** Mission abandoned by commander
- **Affects Signals:** `event_missionabandoned`, `mission_activity`
- **Description:** Commander abandons active mission
- **Test Priority:** MEDIUM

### MissionRedirected
- **When:** Mission destination changed
- **Affects Signals:** `event_missionredirected`, `mission_activity`
- **Description:** Mission target station/system redirected
- **Test Priority:** LOW

### Missions
- **When:** Mission state update
- **Affects Signals:** `event_missions`
- **Description:** Current active missions list
- **Test Priority:** MEDIUM

### Passengers
- **When:** Passenger mission state
- **Affects Signals:** `event_passengers`
- **Description:** Current passenger mission details
- **Test Priority:** LOW

---

## Ship Management

Events related to ship purchase, sale, and naming.

### ShipyardBuy
- **When:** Ship purchased from shipyard
- **Affects Signals:** `event_shipyardbuy`, `shipyard_activity`
- **Description:** Buying new ship
- **Test Priority:** HIGH - Ship management

### ShipyardSell
- **When:** Ship sold at shipyard
- **Affects Signals:** `event_shipyardsell`, `shipyard_activity`
- **Description:** Selling stored ship
- **Test Priority:** MEDIUM

### ShipyardSwap
- **When:** Swap to different ship
- **Affects Signals:** `event_shipyardswap`, `shipyard_activity`
- **Description:** Switching to another owned ship
- **Test Priority:** HIGH - Ship management

### ShipyardTransfer
- **When:** Ship transfer initiated
- **Affects Signals:** `event_shipyardtransfer`, `shipyard_activity`
- **Description:** Moving ship to current station
- **Test Priority:** MEDIUM

### Shipyard
- **When:** Shipyard accessed
- **Affects Signals:** `event_shipyard`
- **Description:** Opening shipyard interface
- **Test Priority:** LOW

### SetUserShipName
- **When:** Ship renamed
- **Affects Signals:** `event_setusershipname`, `shipyard_activity`
- **Description:** Changing ship name and ID
- **Test Priority:** LOW

### SellShipOnRebuy
- **When:** Ship sold to cover rebuy cost
- **Affects Signals:** `event_sellshiponrebuy`
- **Description:** Emergency ship sale during rebuy
- **Test Priority:** LOW

### Loadout
- **When:** Ship loadout updated
- **Affects Signals:** `event_loadout`
- **Description:** Complete ship module configuration
- **Test Priority:** HIGH - Ship state tracking

### RefuelAll
- **When:** Ship fully refueled at station
- **Affects Signals:** `event_refuelall`, `refuel_activity`
- **Description:** Topping up fuel tank
- **Test Priority:** MEDIUM

### RefuelPartial
- **When:** Partial refuel purchased
- **Affects Signals:** `event_refuelpartial`, `refuel_activity`
- **Description:** Buying specific fuel amount
- **Test Priority:** LOW

### Repair
- **When:** Ship repairs purchased (specific module/hull)
- **Affects Signals:** `event_repair`, `repair_activity`
- **Description:** Individual module or hull repair
- **Test Priority:** MEDIUM

### RepairAll
- **When:** All ship damage repaired
- **Affects Signals:** `event_repairall`, `repair_activity`
- **Description:** Complete ship restoration
- **Test Priority:** HIGH - Ship maintenance

### RebootRepair
- **When:** Emergency reboot/repair initiated
- **Affects Signals:** `event_rebootrepair`, `repair_activity`
- **Description:** Emergency system reboot for basic repairs
- **Test Priority:** HIGH - Emergency procedures

### RestockVehicle
- **When:** SRV/Fighter restocked
- **Affects Signals:** `event_restockvehicle`
- **Description:** Replenishing vehicle bay
- **Test Priority:** LOW

### HeatDamage
- **When:** Ship takes heat damage
- **Affects Signals:** `event_heatdamage`, `heat_damage_activity`
- **Description:** Overheating causing module damage
- **Test Priority:** MEDIUM

### HeatWarning
- **When:** Heat warning threshold
- **Affects Signals:** `event_heatwarning`
- **Description:** Ship approaching critical temperature
- **Test Priority:** LOW

### LaunchDrone
- **When:** Limpet controller launches drone
- **Affects Signals:** `event_launchdrone`
- **Description:** Deploying limpet drone
- **Test Priority:** LOW

### AfmuRepairs
- **When:** AFMU repairing module
- **Affects Signals:** `event_afmurepairs`
- **Description:** Auto Field-Maintenance Unit in operation
- **Test Priority:** LOW

### ReservoirReplenished
- **When:** Guardian/Thargoid module reservoir refilled
- **Affects Signals:** `event_reservoirreplenished`
- **Description:** Hybrid fuel reservoir refilled
- **Test Priority:** LOW

### Shutdown
- **When:** Ship systems shut down
- **Affects Signals:** `event_shutdown`
- **Description:** Silent running or emergency shutdown
- **Test Priority:** MEDIUM

### SystemsShutdown
- **When:** Ship systems offline
- **Affects Signals:** `event_systemsshutdown`
- **Description:** All systems powered down
- **Test Priority:** LOW

---

## Outfitting & Modules

Events related to ship module purchases, sales, and modifications.

### ModuleBuy
- **When:** Module purchased and installed
- **Affects Signals:** `event_modulebuy`, `outfitting_activity`
- **Description:** Buying ship module from outfitting
- **Test Priority:** HIGH - Outfitting workflow

### ModuleSell
- **When:** Module sold
- **Affects Signals:** `event_modulesell`, `outfitting_activity`
- **Description:** Selling installed or stored module
- **Test Priority:** MEDIUM

### ModuleSwap
- **When:** Modules swapped between slots
- **Affects Signals:** `event_moduleswap`, `outfitting_activity`
- **Description:** Moving modules to different slots
- **Test Priority:** MEDIUM

### ModuleStore
- **When:** Module stored at station
- **Affects Signals:** `event_modulestore`, `outfitting_activity`
- **Description:** Removing and storing module
- **Test Priority:** MEDIUM

### ModuleRetrieve
- **When:** Module retrieved from storage
- **Affects Signals:** `event_moduleretrieve`, `outfitting_activity`
- **Description:** Installing previously stored module
- **Test Priority:** MEDIUM

### ModuleSellRemote
- **When:** Remote stored module sold
- **Affects Signals:** `event_modulesellremote`
- **Description:** Selling module stored at another station
- **Test Priority:** LOW

### FetchRemoteModule
- **When:** Remote module transfer initiated
- **Affects Signals:** `event_fetchremotemodule`
- **Description:** Shipping module from remote storage
- **Test Priority:** LOW

### MassModuleStore
- **When:** Multiple modules stored at once
- **Affects Signals:** `event_massmodulestore`
- **Description:** Bulk module storage operation
- **Test Priority:** LOW

### Outfitting
- **When:** Outfitting accessed
- **Affects Signals:** `event_outfitting`
- **Description:** Opening outfitting interface
- **Test Priority:** LOW

### BuyAmmo
- **When:** Ammunition purchased
- **Affects Signals:** `event_buyammo`
- **Description:** Restocking weapon ammunition
- **Test Priority:** LOW

### BuyDrones
- **When:** Limpets purchased
- **Affects Signals:** `event_buydrones`
- **Description:** Buying limpet drones
- **Test Priority:** LOW

### SellDrones
- **When:** Limpets sold
- **Affects Signals:** `event_selldrones`
- **Description:** Selling excess limpets
- **Test Priority:** LOW

---

## Engineering & Crafting

Events related to engineering, synthesis, and material management.

### EngineerCraft
- **When:** Module engineered/modified
- **Affects Signals:** `event_engineercraft`, `engineering_activity`
- **Description:** Applying engineering blueprint
- **Test Priority:** HIGH - Engineering workflow

### EngineerProgress
- **When:** Engineer reputation/access updated
- **Affects Signals:** `event_engineerprogress`, `engineering_activity`
- **Description:** Progress with engineer unlocking/ranking
- **Test Priority:** MEDIUM

### EngineerContribution
- **When:** Contribution made to engineer
- **Affects Signals:** `event_engineercontribution`
- **Description:** Donating materials/commodities to engineer
- **Test Priority:** LOW

### EngineerLegacyConvert
- **When:** Legacy engineered module converted
- **Affects Signals:** `event_engineerlegacyconvert`
- **Description:** Converting pre-3.0 modules to new system
- **Test Priority:** LOW

### Synthesis
- **When:** Module synthesis performed
- **Affects Signals:** `event_synthesis`, `engineering_activity`
- **Description:** Crafting consumables (ammo, limpets, etc.)
- **Test Priority:** MEDIUM

### MaterialCollected
- **When:** Raw/manufactured/data material collected
- **Affects Signals:** `event_materialcollected`, `engineering_activity`
- **Description:** Picking up engineering materials
- **Test Priority:** HIGH - Material gathering

### MaterialTrade
- **When:** Materials traded at material trader
- **Affects Signals:** `event_materialtrade`, `engineering_activity`
- **Description:** Exchanging materials between categories
- **Test Priority:** MEDIUM

### MaterialDiscarded
- **When:** Material discarded from inventory
- **Affects Signals:** `event_materialdiscarded`
- **Description:** Dropping materials to make space
- **Test Priority:** LOW

### MaterialDiscovered
- **When:** New material type discovered
- **Affects Signals:** `event_materialdiscovered`
- **Description:** First encounter with material type
- **Test Priority:** LOW

### Materials
- **When:** Materials inventory state
- **Affects Signals:** `event_materials`
- **Description:** Current materials manifest
- **Test Priority:** MEDIUM

### TechnologyBroker
- **When:** Technology unlocked at broker
- **Affects Signals:** `event_technologybroker`
- **Description:** Unlocking Guardian/human tech
- **Test Priority:** MEDIUM

### ScientificResearch
- **When:** Research contribution made
- **Affects Signals:** `event_scientificresearch`
- **Description:** Donating materials for research
- **Test Priority:** LOW

---

## SRV & Fighters

Events related to surface recon vehicles and ship-launched fighters.

### LaunchSRV
- **When:** SRV deployed to surface
- **Affects Signals:** `event_launchsrv`, `vehicle_activity`
- **Description:** Launching Surface Recon Vehicle
- **Test Priority:** HIGH - Vehicle operations

### DockSRV
- **When:** SRV docked back to ship
- **Affects Signals:** `event_docksrv`, `vehicle_activity`
- **Description:** Recalling SRV to ship bay
- **Test Priority:** HIGH - Vehicle operations

### LaunchFighter
- **When:** Fighter launched from ship
- **Affects Signals:** `event_launchfighter`
- **Description:** Deploying ship-launched fighter
- **Test Priority:** MEDIUM

### DockFighter
- **When:** Fighter docked to mothership
- **Affects Signals:** `event_dockfighter`
- **Description:** Recalling fighter to bay
- **Test Priority:** MEDIUM

### VehicleSwitch
- **When:** Switching between ship/SRV/fighter
- **Affects Signals:** `event_vehicleswitch`
- **Description:** Changing active vehicle control
- **Test Priority:** MEDIUM

---

## Multicrew

Events related to multicrew sessions and NPC crew.

### CrewHire
- **When:** NPC crew member hired
- **Affects Signals:** `event_crewhire`
- **Description:** Hiring NPC crew for fighter bay
- **Test Priority:** LOW

### CrewFire
- **When:** NPC crew member fired
- **Affects Signals:** `event_crewfire`
- **Description:** Dismissing NPC crew
- **Test Priority:** LOW

### CrewAssign
- **When:** Crew assigned to role
- **Affects Signals:** `event_crewassign`
- **Description:** Assigning crew to fighter/turret
- **Test Priority:** LOW

### NpcCrewPaidWage
- **When:** NPC crew paid their wage
- **Affects Signals:** `event_npccrewpaidwage`
- **Description:** Weekly crew salary payment
- **Test Priority:** LOW

### NpcCrewRank
- **When:** NPC crew ranks up
- **Affects Signals:** `event_npccrewrank`
- **Description:** Crew gains combat rank
- **Test Priority:** LOW

### JoinACrew
- **When:** Join another player's crew
- **Affects Signals:** `event_joinacrew`
- **Description:** Entering multicrew as crew
- **Test Priority:** LOW

### QuitACrew
- **When:** Leave multicrew session
- **Affects Signals:** `event_quitacrew`
- **Description:** Exiting multicrew
- **Test Priority:** LOW

### KickCrewMember
- **When:** Crew member kicked from session
- **Affects Signals:** `event_kickcrewmember`
- **Description:** Removing player from your multicrew
- **Test Priority:** LOW

### EndCrewSession
- **When:** Multicrew session ended
- **Affects Signals:** `event_endcrewsession`
- **Description:** Multicrew session terminated
- **Test Priority:** LOW

### CrewMemberJoins
- **When:** Player joins your crew
- **Affects Signals:** `event_crewmemberjoins`
- **Description:** Another commander joins multicrew
- **Test Priority:** LOW

### CrewMemberQuits
- **When:** Crew member leaves
- **Affects Signals:** `event_crewmemberquits`
- **Description:** Crew member exits session
- **Test Priority:** LOW

### CrewMemberRoleChange
- **When:** Crew role changed
- **Affects Signals:** `event_crewmemberrolechange`
- **Description:** Crew switches role in session
- **Test Priority:** LOW

### CrewLaunchFighter
- **When:** Crew deploys in fighter
- **Affects Signals:** `event_crewlaunchfighter`
- **Description:** Crew member takes fighter
- **Test Priority:** LOW

### ChangeCrewRole
- **When:** Your role changes in multicrew
- **Affects Signals:** `event_changecrewrole`
- **Description:** Switching your own crew role
- **Test Priority:** LOW

---

## Fleet Carrier

Events related to fleet carrier ownership and operations.

### CarrierBuy
- **When:** Fleet carrier purchased
- **Affects Signals:** `event_carrierbuy`
- **Description:** Buying a fleet carrier
- **Test Priority:** LOW - Expensive feature

### CarrierStats
- **When:** Carrier statistics updated
- **Affects Signals:** `event_carrierstats`
- **Description:** Fleet carrier operational data
- **Test Priority:** LOW

### CarrierJumpRequest
- **When:** Carrier jump scheduled
- **Affects Signals:** `event_carrierjumprequest`
- **Description:** Requesting carrier to jump
- **Test Priority:** LOW

### CarrierJumpCancelled
- **When:** Scheduled carrier jump cancelled
- **Affects Signals:** `event_carrierjumpcancelled`
- **Description:** Canceling carrier jump
- **Test Priority:** LOW

### CarrierFinance
- **When:** Carrier financial report
- **Affects Signals:** `event_carrierfinance`
- **Description:** Weekly carrier costs and income
- **Test Priority:** LOW

### CarrierBankTransfer
- **When:** Credits transferred to/from carrier
- **Affects Signals:** `event_carrierbanktransfer`
- **Description:** Moving credits between bank and carrier
- **Test Priority:** LOW

### CarrierDepositFuel
- **When:** Tritium deposited to carrier
- **Affects Signals:** `event_carrierdepositfuel`
- **Description:** Fueling the carrier
- **Test Priority:** LOW

### CarrierCrewServices
- **When:** Carrier services modified
- **Affects Signals:** `event_carriercrewservices`
- **Description:** Managing carrier services
- **Test Priority:** LOW

### CarrierTradeOrder
- **When:** Carrier trade order created/modified
- **Affects Signals:** `event_carriertradeorder`
- **Description:** Setting buy/sell orders
- **Test Priority:** LOW

### CarrierDockingPermission
- **When:** Carrier docking permissions changed
- **Affects Signals:** `event_carrierdockingpermission`
- **Description:** Access control settings
- **Test Priority:** LOW

### CarrierNameChange
- **When:** Carrier renamed
- **Affects Signals:** `event_carriernamechange`
- **Description:** Changing carrier name
- **Test Priority:** LOW

### CarrierModulePack
- **When:** Carrier module pack installed/removed
- **Affects Signals:** `event_carriermodulepack`
- **Description:** Adding/removing carrier services
- **Test Priority:** LOW

### CarrierDecommission
- **When:** Carrier decommission scheduled
- **Affects Signals:** `event_carrierdecommission`
- **Description:** Scrapping fleet carrier
- **Test Priority:** LOW

### CarrierCancelDecommission
- **When:** Carrier decommission cancelled
- **Affects Signals:** `event_carriercanceldecommission`
- **Description:** Canceling carrier scrapping
- **Test Priority:** LOW

### CarrierTransfer
- **When:** Cargo transferred to/from carrier
- **Affects Signals:** `event_carriertransfer`
- **Description:** Moving cargo with carrier
- **Test Priority:** LOW

---

## Powerplay

Events related to powerplay activities.

### PowerplayJoin
- **When:** Pledge to a power
- **Affects Signals:** `event_powerplayjoin`
- **Description:** Joining a powerplay faction
- **Test Priority:** LOW

### PowerplayLeave
- **When:** Leave a power
- **Affects Signals:** `event_powerplayleave`
- **Description:** Defecting from power
- **Test Priority:** LOW

### PowerplayDefect
- **When:** Switch to different power
- **Affects Signals:** `event_powerplaydefect`
- **Description:** Pledging to new power
- **Test Priority:** LOW

### PowerplayDeliver
- **When:** Deliver powerplay commodities
- **Affects Signals:** `event_powerplaydeliver`
- **Description:** Completing powerplay task
- **Test Priority:** LOW

### PowerplayCollect
- **When:** Collect powerplay commodities
- **Affects Signals:** `event_powerplaycollect`
- **Description:** Obtaining preparation/expansion materials
- **Test Priority:** LOW

### PowerplaySalary
- **When:** Weekly powerplay salary
- **Affects Signals:** `event_powerplaysalary`
- **Description:** Merits converted to credits
- **Test Priority:** LOW

### PowerplayVote
- **When:** Vote on powerplay action
- **Affects Signals:** `event_powerplayvote`
- **Description:** Voting for power's next action
- **Test Priority:** LOW

### PowerplayVoucher
- **When:** Powerplay voucher redeemed
- **Affects Signals:** `event_powerplayvoucher`
- **Description:** Cashing in merits
- **Test Priority:** LOW

### Powerplay
- **When:** Powerplay state update
- **Affects Signals:** `event_powerplay`
- **Description:** Current powerplay status
- **Test Priority:** LOW

---

## Squadron

Events related to squadron (player faction) activities.

### SquadronCreated
- **When:** Squadron created
- **Affects Signals:** `event_squadroncreated`
- **Description:** Founding a new squadron
- **Test Priority:** LOW

### JoinedSquadron
- **When:** Join a squadron
- **Affects Signals:** `event_joinedsquadron`
- **Description:** Accepted into squadron
- **Test Priority:** LOW

### LeftSquadron
- **When:** Leave squadron
- **Affects Signals:** `event_leftsquadron`
- **Description:** Departing from squadron
- **Test Priority:** LOW

### AppliedToSquadron
- **When:** Application submitted to squadron
- **Affects Signals:** `event_appliedtosquadron`
- **Description:** Requesting to join
- **Test Priority:** LOW

### InvitedToSquadron
- **When:** Invited to join squadron
- **Affects Signals:** `event_invitedtosquadron`
- **Description:** Receiving invitation
- **Test Priority:** LOW

### KickedFromSquadron
- **When:** Removed from squadron
- **Affects Signals:** `event_kickedfromsquadron`
- **Description:** Expelled from squadron
- **Test Priority:** LOW

### DisbandedSquadron
- **When:** Squadron disbanded
- **Affects Signals:** `event_disbandedsquadron`
- **Description:** Squadron shut down
- **Test Priority:** LOW

### SquadronPromotion
- **When:** Promoted in squadron
- **Affects Signals:** `event_squadronpromotion`
- **Description:** Rank increase in squadron
- **Test Priority:** LOW

### SquadronDemotion
- **When:** Demoted in squadron
- **Affects Signals:** `event_squadrondemotion`
- **Description:** Rank decrease in squadron
- **Test Priority:** LOW

### SharedBookmarkToSquadron
- **When:** Bookmark shared with squadron
- **Affects Signals:** `event_sharedbookmarktosquadron`
- **Description:** Sharing location with squadron
- **Test Priority:** LOW

### SquadronStartup
- **When:** Squadron info on login
- **Affects Signals:** `event_squadronstartup`
- **Description:** Current squadron membership status
- **Test Priority:** LOW

### WonATrophyForSquadron
- **When:** Squadron trophy earned
- **Affects Signals:** `event_wonatrophyforsquadron`
- **Description:** Squadron achievement unlocked
- **Test Priority:** LOW

---

## Odyssey - On Foot

Events specific to Odyssey on-foot gameplay.

### Disembark
- **When:** Exit ship on foot
- **Affects Signals:** `event_disembark`
- **Description:** Leaving ship to walk around
- **Test Priority:** MEDIUM - Odyssey core

### Embark
- **When:** Board ship from on foot
- **Affects Signals:** `event_embark`
- **Description:** Entering ship while on foot
- **Test Priority:** MEDIUM - Odyssey core

### CommanderInTaxi
- **When:** Riding as passenger in Apex taxi
- **Affects Signals:** `event_commanderintaxi`
- **Description:** Using Apex Interstellar transport
- **Test Priority:** LOW

### BookTaxi
- **When:** Apex taxi booked
- **Affects Signals:** `event_booktaxi`
- **Description:** Calling for a ride
- **Test Priority:** LOW

### CancelTaxi
- **When:** Taxi booking cancelled
- **Affects Signals:** `event_canceltaxi`
- **Description:** Canceling Apex request
- **Test Priority:** LOW

### BookDropship
- **When:** Dropship booked for ground CZ
- **Affects Signals:** `event_bookdropship`
- **Description:** Calling dropship transport
- **Test Priority:** LOW

### CancelDropship
- **When:** Dropship cancelled
- **Affects Signals:** `event_canceldropship`
- **Description:** Canceling dropship
- **Test Priority:** LOW

### DropshipDeploy
- **When:** Deployed from dropship
- **Affects Signals:** `event_dropshipdeploy`
- **Description:** Ground conflict zone insertion
- **Test Priority:** LOW

### Backpack
- **When:** Backpack inventory state
- **Affects Signals:** `event_backpack`
- **Description:** On-foot item inventory
- **Test Priority:** LOW

### BackpackChange
- **When:** Backpack contents changed
- **Affects Signals:** `event_backpackchange`
- **Description:** Items added/removed from backpack
- **Test Priority:** LOW

### CollectItems
- **When:** Items picked up on foot
- **Affects Signals:** `event_collectitems`
- **Description:** Gathering items while on foot
- **Test Priority:** LOW

### DropItems
- **When:** Items dropped on foot
- **Affects Signals:** `event_dropitems`
- **Description:** Dropping items from backpack
- **Test Priority:** LOW

### ShipLocker
- **When:** Ship locker accessed
- **Affects Signals:** `event_shiplocker`
- **Description:** Storage locker in ship
- **Test Priority:** LOW

### TransferMicroResources
- **When:** Micro resources moved
- **Affects Signals:** `event_transfermicroresources`
- **Description:** Moving items between storage
- **Test Priority:** LOW

### TradeMicroResources
- **When:** Micro resources traded
- **Affects Signals:** `event_trademicroresources`
- **Description:** Trading on-foot materials
- **Test Priority:** LOW

### FCMaterials
- **When:** Carrier materials manifest
- **Affects Signals:** `event_fcmaterials`
- **Description:** Fleet carrier material storage
- **Test Priority:** LOW

### UseConsumable
- **When:** Consumable item used
- **Affects Signals:** `event_useconsumable`
- **Description:** Using health pack, battery, etc.
- **Test Priority:** LOW

---

## Odyssey - Equipment

Events for Odyssey suit and weapon management.

### BuySuit
- **When:** Suit purchased
- **Affects Signals:** `event_buysuit`
- **Description:** Buying new suit
- **Test Priority:** LOW

### SellSuit
- **When:** Suit sold
- **Affects Signals:** `event_sellsuit`
- **Description:** Selling owned suit
- **Test Priority:** LOW

### UpgradeSuit
- **When:** Suit upgraded
- **Affects Signals:** `event_upgradesuit`
- **Description:** Upgrading suit grade
- **Test Priority:** LOW

### SuitLoadout
- **When:** Suit loadout information
- **Affects Signals:** `event_suitloadout`
- **Description:** Current suit configuration
- **Test Priority:** LOW

### CreateSuitLoadout
- **When:** New suit loadout created
- **Affects Signals:** `event_createsuitloadout`
- **Description:** Creating loadout preset
- **Test Priority:** LOW

### DeleteSuitLoadout
- **When:** Suit loadout deleted
- **Affects Signals:** `event_deletesuitloadout`
- **Description:** Removing loadout preset
- **Test Priority:** LOW

### SwitchSuitLoadout
- **When:** Switch to different suit loadout
- **Affects Signals:** `event_switchsuitloadout`
- **Description:** Changing active loadout
- **Test Priority:** LOW

### LoadoutEquipModule
- **When:** Module added to suit
- **Affects Signals:** `event_loadoutequipmodule`
- **Description:** Equipping suit modification
- **Test Priority:** LOW

### BuyWeapon
- **When:** Weapon purchased
- **Affects Signals:** `event_buyweapon`
- **Description:** Buying new weapon
- **Test Priority:** LOW

### SellWeapon
- **When:** Weapon sold
- **Affects Signals:** `event_sellweapon`
- **Description:** Selling owned weapon
- **Test Priority:** LOW

### UpgradeWeapon
- **When:** Weapon upgraded
- **Affects Signals:** `event_upgradeweapon`
- **Description:** Upgrading weapon grade
- **Test Priority:** LOW

---

## Odyssey - Settlements

Events related to settlements and on-foot locations.

### ApproachSettlement
- **When:** Approaching ground settlement
- **Affects Signals:** `event_approachsettlement`
- **Description:** Getting close to settlement
- **Test Priority:** LOW

### DataScanned
- **When:** Data port scanned
- **Affects Signals:** `event_datascanned`
- **Description:** Panel/terminal data extraction
- **Test Priority:** LOW

### DatalinkScan
- **When:** Datalink scanned
- **Affects Signals:** `event_datalinkscan`
- **Description:** Scanning datalink for information
- **Test Priority:** LOW

### DatalinkVoucher
- **When:** Datalink voucher obtained
- **Affects Signals:** `event_datalinkvoucher`
- **Description:** Reward for datalink scan
- **Test Priority:** LOW

### ColonisationConstructionDepot
- **When:** Construction depot interaction
- **Affects Signals:** `event_colonisationconstructiondepot`
- **Description:** Colonization project depot
- **Test Priority:** LOW

### ColonisationContribution
- **When:** Contribution to colonization
- **Affects Signals:** `event_colonisationcontribution`
- **Description:** Donating to colonization effort
- **Test Priority:** LOW

---

## Financial

Events related to financial transactions not covered in other categories.

### PayFines
- **When:** Fines paid at authority contact
- **Affects Signals:** `event_payfines`, `legal_activity`
- **Description:** Paying off accumulated fines
- **Test Priority:** MEDIUM

### PayBounties
- **When:** Bounties cleared
- **Affects Signals:** `event_paybounties`, `legal_activity`
- **Description:** Paying off bounties on head
- **Test Priority:** MEDIUM

### PayLegacyFines
- **When:** Legacy fine system cleared
- **Affects Signals:** `event_paylegacyfines`
- **Description:** Clearing old-format fines
- **Test Priority:** LOW

### RedeemVoucher
- **When:** Voucher redeemed for credits
- **Affects Signals:** `event_redeemvoucher`
- **Description:** Cashing in combat bonds, exploration data, etc.
- **Test Priority:** HIGH - Income tracking

### ClearImpound
- **When:** Impounded ship recovered
- **Affects Signals:** `event_clearimpound`
- **Description:** Paying to retrieve impounded ship
- **Test Priority:** LOW

---

## Community Goals

Events related to community goal participation.

### CommunityGoal
- **When:** Community goal status update
- **Affects Signals:** `event_communitygoal`
- **Description:** Progress on active CG
- **Test Priority:** LOW

### CommunityGoalJoin
- **When:** Sign up for community goal
- **Affects Signals:** `event_communitygoaljoin`
- **Description:** Joining a CG
- **Test Priority:** LOW

### CommunityGoalDiscard
- **When:** Abandon community goal
- **Affects Signals:** `event_communitygoaldiscard`
- **Description:** Leaving a CG
- **Test Priority:** LOW

### CommunityGoalReward
- **When:** CG reward received
- **Affects Signals:** `event_communitygoalreward`
- **Description:** Payout for CG participation
- **Test Priority:** LOW

---

## Communications

Events related to communication and social features.

### ReceiveText
- **When:** Text message received
- **Affects Signals:** `event_receivetext`
- **Description:** Chat message from NPC or player
- **Test Priority:** LOW

### SendText
- **When:** Text message sent
- **Affects Signals:** `event_sendtext`
- **Description:** Outgoing chat message
- **Test Priority:** LOW

### Friends
- **When:** Friends list updated
- **Affects Signals:** `event_friends`
- **Description:** Current friends online status
- **Test Priority:** LOW

---

## Miscellaneous

Other events that don't fit cleanly into above categories.

### Promotion
- **When:** Commander promoted in rank
- **Affects Signals:** `event_promotion`
- **Description:** Combat, Trade, Explore, Empire, or Federation rank up
- **Test Priority:** MEDIUM

### Rank
- **When:** Rank information state
- **Affects Signals:** `event_rank`
- **Description:** Current ranks across all categories
- **Test Priority:** MEDIUM

### Progress
- **When:** Rank progress state
- **Affects Signals:** `event_progress`
- **Description:** Progress toward next rank
- **Test Priority:** LOW

### Reputation
- **When:** Reputation state update
- **Affects Signals:** `event_reputation`
- **Description:** Standing with major and minor factions
- **Test Priority:** LOW

### Statistics
- **When:** Statistics state
- **Affects Signals:** `event_statistics`
- **Description:** Career statistics summary
- **Test Priority:** LOW

### Music
- **When:** In-game music track changes
- **Affects Signals:** `event_music`
- **Description:** Background music state tracking
- **Test Priority:** LOW

---

## Summary Statistics

**Total Unique Events:** 220+

### Events by Priority for Testing

- **HIGH Priority (Core Gameplay):** 39 events
  - Session management, navigation, docking, FSD, exploration, combat, trading, ship management
  
- **MEDIUM Priority (Common Features):** 52 events
  - Specialized gameplay loops, damage tracking, missions, engineering
  
- **LOW Priority (Edge Cases/Rare):** 129+ events
  - Fleet carrier, powerplay, squadron, Odyssey content, specialized features

### Events by Category Count

1. **Odyssey Features:** 60+ events
2. **Combat & Damage:** 22 events
3. **Ship Management:** 21 events
4. **Navigation & Travel:** 14 events
5. **Exploration & Scanning:** 14 events
6. **Engineering & Crafting:** 13 events
7. **Outfitting & Modules:** 13 events
8. **Trading & Cargo:** 10 events
9. **Missions:** 9 events
10. **Fleet Carrier:** 16 events
11. **Docking & Stations:** 9 events
12. **Multicrew:** 14 events
13. **Squadron:** 12 events
14. **Powerplay:** 9 events
15. **Financial:** 6 events
16. **SRV & Fighters:** 5 events
17. **Community Goals:** 4 events
18. **Communications:** 3 events
19. **Miscellaneous:** 7 events

---

## Test Coverage Recommendations

### Phase 1: Core Functionality (HIGH Priority)
Focus testing on events marked HIGH priority, especially:
- Session startup (LoadGame, FileHeader)
- Basic navigation (FSDJump, Location, SupercruiseEntry/Exit)
- Station operations (Docked, Undocked, DockingGranted)
- Core activities (Scan, MarketBuy/Sell, MissionAccepted/Completed)

### Phase 2: Common Gameplay (MEDIUM Priority)
Test specialized but commonly-used features:
- Combat scenarios (all combat events)
- Mission workflows (full mission lifecycle)
- Engineering (EngineerCraft, MaterialCollected)
- Ship maintenance (Repair, Refuel, Outfitting)

### Phase 3: Edge Cases (LOW Priority)
Cover rare or specialized content:
- Fleet carrier operations
- Powerplay activities
- Squadron management
- Odyssey on-foot gameplay
- Multicrew sessions

### Phase 4: Comprehensive Coverage
Create test journal files covering:
- Each event at least once
- Common event combinations (e.g., DockingRequested → DockingGranted → Docked)
- Edge cases (DockingDenied, DockingTimeout, mission failures)
- State transitions (shield up/down, interdiction scenarios)

---

## Notes

- Events listed affect multiple signals through the derivation system
- Many "activity" signals trigger on multiple related events (e.g., `scan_activity` triggers on Scan, FSSDiscoveryScan, SAAScanComplete, etc.)
- Dashboard flags and journal events work together - some signals combine both sources
- Recent event detection (within N seconds) creates transient state signals like "just_docked"
- Some events are state snapshots (Loadout, Materials, Cargo) logged periodically or on login

---

**Document Version:** 1.0  
**Generated:** 2026-02-16  
**Source:** signals_catalog.json v1
