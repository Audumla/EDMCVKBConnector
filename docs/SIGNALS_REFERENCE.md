# Signals Reference

Comprehensive catalog of rule signals with trigger/source mapping.

- Generated: 2026-02-18
- Catalog file: `signals_catalog.json`
- Total signals: 196
- Signal types: array=1, enum=106, number=73, string=16
- UI tiers: advanced=10, core=73, detail=113
- Sample source: `recordings/recorded_events_YYYYMMDD_HHMMSS.jsonl` (277 records)

For each signal:
- `Trigger/source` lists journal event triggers and/or state/status paths used for derivation.
- `Sample values` are shown for non-enum signals.

## Ship

### `cargo_activity`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: CollectCargo (<= 3s), EjectCargo (<= 3s)
- Enum values: none, collected, ejected

### `cargo_count`
- Type: `number`
- Tier: `core`
- Trigger/source: paths: dashboard.Cargo
- Sample values: 0, 31.0, 30.0, 29.0, 28.0

### `cargo_hatch`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[9]
- Enum values: retracted, deployed

### `cockpit_status`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: CockpitBreached (<= 300s)
- Enum values: intact, breached

### `crew_activity`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: ChangeCrewRole (<= 1s), CrewAssign (<= 1s), CrewFire (<= 1s), CrewHire (<= 1s), CrewLaunchFighter (<= 1s), CrewMemberJoins (<= 1s), CrewMemberQuits (<= 1s), CrewMemberRoleChange (<= 1s), EndCrewSession (<= 1s), JoinACrew (<= 1s), KickCrewMember (<= 1s), NpcCrewPaidWage (<= 1s), NpcCrewRank (<= 1s), QuitACrew (<= 1s)
- Enum values: none, hired, fired, joined_session, left_session, assigned, kicked, session_ended, member_joined, member_left, member_role_changed, launched_fighter, your_role_changed, npc_paid, npc_ranked_up

### `docking_request_state`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: DockingCancelled (<= 5s), DockingDenied (<= 5s), DockingGranted (<= 30s), DockingRequested (<= 5s), DockingTimeout (<= 5s)
- Enum values: none, requested, granted, denied, cancelled, timeout

### `docking_state`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: Docked (<= 3s), Liftoff (<= 3s), Touchdown (<= 3s), Undocked (<= 3s) | flags: ship_flags[0], ship_flags[1]
- Enum values: in_space, landed, docked, just_docked, just_undocked, just_landed, just_lifted_off

### `fighter`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: DockFighter (<= 1s), FighterDestroyed (<= 1s), LaunchFighter (<= 1s)
- Enum values: none, launched, docked, destroyed

### `fire_group`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.FireGroup
- Sample values: 0, 6, 5, 4, 3

### `flight_assist`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[5]
- Enum values: on, off

### `fsd_status`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: foot_flags[15], ship_flags[17], ship_flags[18], ship_flags[30], ship_flags[4]
- Enum values: idle, charging, cooldown, jump_active, supercruise, gliding, jet_cone_boost, jet_cone_damage, off, entering_supercruise, exiting_supercruise, masslocked

### `fuel`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: FuelScoop (<= 1s), RefuelAll (<= 1s), RefuelPartial (<= 1s), ReservoirReplenished (<= 1s) | flags: ship_flags[11], ship_flags[19] | paths: dashboard.Fuel.FuelMain
- Enum values: ok, low, critical, scooping, scooped, full_refuel, partial_refuel, reservoir_filled

### `fuel_main`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Fuel.FuelMain
- Sample values: 0

### `fuel_reservoir`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Fuel.FuelReservoir
- Sample values: 0

### `hardpoints`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[6]
- Enum values: retracted, deployed

### `has_npc_crew`
- Type: `enum`
- Tier: `core`
- Trigger/source: n/a
- Enum values: no, yes

### `has_vip_passengers`
- Type: `enum`
- Tier: `detail`
- Trigger/source: n/a
- Enum values: no, yes

### `has_wanted_passengers`
- Type: `enum`
- Tier: `detail`
- Trigger/source: n/a
- Enum values: no, yes

### `heat_status`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: HeatDamage (<= 2s) | flags: ship_flags[20]
- Enum values: normal, overheating, heat_damage

### `hull_state`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: HullDamage (<= 2s) | paths: state.HullHealth
- Enum values: ok, damaged, critical, taking_damage

### `interdiction`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: Interdicted
- Enum values: submitted, escaped, succeeded, failed, is_player, being_interdicted

### `landing_gear`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[2]
- Enum values: retracted, deployed

### `limpets`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: BuyDrones (<= 1s), LaunchDrone (<= 1s), SellDrones (<= 1s)
- Enum values: none, purchased, launched, sold

### `module_activity`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: ModuleBuy (<= 3s), ModuleRetrieve (<= 3s), ModuleSell (<= 3s), ModuleStore (<= 3s), ModuleSwap (<= 3s)
- Enum values: bought, sold, swapped, stored, retrieved, module_sell_remote, mass_module_store, fetch_remote_module, outfitting

### `night_vision`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[28]
- Enum values: off, on

### `npc_crew_count`
- Type: `number`
- Tier: `detail`
- Trigger/source: n/a
- Sample values: 0

### `passengers_count`
- Type: `number`
- Tier: `core`
- Trigger/source: n/a
- Sample values: 0

### `pips_eng`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: dashboard.Pips.1
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8

### `pips_sys`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: dashboard.Pips.0
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8

### `pips_wep`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: dashboard.Pips.2
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8

### `power_distribution`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: dashboard.Pips.0, dashboard.Pips.1, dashboard.Pips.2
- Enum values: balanced, defensive, aggressive, evasive, custom

### `refuel_status`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: RefuelAll (<= 5s), RefuelPartial (<= 5s)
- Enum values: none, partial_refueled, full_refueled

### `repair_status`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: RebootRepair (<= 10s), Repair (<= 5s), RepairAll (<= 5s)
- Enum values: none, module_repaired, full_repaired, rebooting, afmu_repairs

### `shield_state`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: ShieldState (<= 3s) | flags: ship_flags[3]
- Enum values: down, up, just_failed, just_restored

### `ship_cargo_capacity`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.CargoCapacity
- Sample values: 0

### `ship_fuel_capacity_main`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.FuelCapacity.Main
- Sample values: 0

### `ship_fuel_capacity_reserve`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.FuelCapacity.Reserve
- Sample values: 0

### `ship_hull_health`
- Type: `number`
- Tier: `core`
- Trigger/source: paths: state.HullHealth
- Sample values: 100

### `ship_hull_value`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.HullValue
- Sample values: 0

### `ship_ident`
- Type: `string`
- Tier: `detail`
- Trigger/source: paths: state.ShipIdent
- Sample values: "" (default)

### `ship_lights`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[8]
- Enum values: off, on

### `ship_max_jump_range`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.MaxJumpRange
- Sample values: 0

### `ship_modules_value`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.ModulesValue
- Sample values: 0

### `ship_name`
- Type: `string`
- Tier: `core`
- Trigger/source: paths: state.ShipName
- Sample values: "" (default)

### `ship_rebuy_cost`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Rebuy
- Sample values: 0

### `ship_status`
- Type: `enum`
- Tier: `core`
- Trigger/source: paths: state.Hot
- Enum values: clean, wanted

### `ship_type`
- Type: `enum`
- Tier: `core`
- Trigger/source: paths: state.ShipType
- Enum values: unknown, adder, anaconda, asp, asp_scout, belugaliner, cobramkiii, cobramkiv, diamondback, diamondbackxl, dolphin, eagle, empire_courier, empire_eagle, empire_fighter, empire_trader, cutter, federation_corvette, federation_dropship, federation_dropship_mkii, federation_gunship, federation_fighter, ferdelance, hauler, independant_trader, krait_mkii, krait_light, mamba, orca, python, python_nx, sidewinder, type6, type7, type9, type9_military, typex, typex_2, typex_3, viper, viper_mkiv, vulture

### `ship_unladen_mass`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.UnladenMass
- Sample values: 0

### `shipyard`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: SetUserShipName (<= 5s), ShipyardBuy (<= 5s), ShipyardSell (<= 5s), ShipyardSwap (<= 5s), ShipyardTransfer (<= 10s)
- Enum values: bought, sold, swapped, transferred, renamed, shipyard, sell_ship_on_rebuy

### `silent_running`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[10]
- Enum values: off, on

### `target_bounty`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Target.Bounty
- Sample values: 0

### `target_faction`
- Type: `string`
- Tier: `detail`
- Trigger/source: paths: state.Target.Faction
- Sample values: "" (default)

### `target_hull_health`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Target.HullHealth
- Sample values: 0

### `target_legal_status`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Target.LegalStatus
- Enum values: unknown, clean, wanted, lawless

### `target_locked`
- Type: `enum`
- Tier: `core`
- Trigger/source: n/a
- Enum values: no, yes

### `target_pilot_name`
- Type: `string`
- Tier: `detail`
- Trigger/source: paths: state.Target.PilotName
- Sample values: "" (default)

### `target_pilot_rank`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Target.PilotRank
- Enum values: unknown, harmless, mostly_harmless, novice, competent, expert, master, dangerous, deadly, elite

### `target_scan_stage`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Target.ScanStage
- Sample values: 0

### `target_shield_health`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Target.ShieldHealth
- Sample values: 0

### `target_ship_type`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Target.Ship
- Enum values: unknown, adder, anaconda, asp, asp_scout, belugaliner, cobramkiii, cobramkiv, diamondback, diamondbackxl, dolphin, eagle, empire_courier, empire_eagle, empire_fighter, empire_trader, cutter, federation_corvette, federation_dropship, federation_dropship_mkii, federation_gunship, federation_fighter, ferdelance, hauler, independant_trader, krait_mkii, krait_light, mamba, orca, python, python_nx, sidewinder, type6, type7, type9, type9_military, typex, typex_2, typex_3, viper, viper_mkiv, vulture

### `target_state`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: ShipTargetted
- Enum values: none, locked, lost, killed_target

### `target_subsystem`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Target.SubSystem
- Enum values: none, $int_powerplant;, $int_engine;, $int_hyperdrive;, $int_lifesupport;, $int_powerdistributor;, $int_sensors;, $int_fueltank;, $int_cargohatch;, $hpt_turret;, $ext_drivebay;

### `target_subsystem_health`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Target.SubSystemHealth
- Sample values: 0

## Commander

### `alliance_reputation`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Reputation.Alliance
- Sample values: 0

### `commander_name`
- Type: `string`
- Tier: `core`
- Trigger/source: paths: state.Commander
- Sample values: "" (default)

### `commander_progress.by_faction.empire`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.RankProgress.Empire
- Sample values: 0

### `commander_progress.by_faction.federation`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.RankProgress.Federation
- Sample values: 0

### `commander_progress.by_rank_type.combat`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.RankProgress.Combat
- Sample values: 0

### `commander_progress.by_rank_type.cqc`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.RankProgress.CQC
- Sample values: 0

### `commander_progress.by_rank_type.exobiologist`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.RankProgress.Exobiologist
- Sample values: 0

### `commander_progress.by_rank_type.explore`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.RankProgress.Explore
- Sample values: 0

### `commander_progress.by_rank_type.mercenary`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.RankProgress.Mercenary
- Sample values: 0

### `commander_progress.by_rank_type.soldier`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.RankProgress.Soldier
- Sample values: 0

### `commander_progress.by_rank_type.trade`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.RankProgress.Trade
- Sample values: 0

### `commander_promotion.combat`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: Promotion (<= 5s) | paths: Combat
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_promotion.cqc`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: Promotion (<= 5s) | paths: CQC
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8

### `commander_promotion.empire`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: Promotion (<= 5s) | paths: Empire
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14

### `commander_promotion.exobiologist`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: Promotion (<= 5s) | paths: Exobiologist
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_promotion.explore`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: Promotion (<= 5s) | paths: Explore
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_promotion.federation`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: Promotion (<= 5s) | paths: Federation
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14

### `commander_promotion.mercenary`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: Promotion (<= 5s) | paths: Mercenary
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_promotion.soldier`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: Promotion (<= 5s) | paths: Soldier
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_promotion.trade`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: Promotion (<= 5s) | paths: Trade
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_ranks.combat`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Rank.Combat
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_ranks.cqc`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Rank.CQC
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8

### `commander_ranks.empire`
- Type: `enum`
- Tier: `detail`
- Trigger/source: n/a
- Enum values: none, outsider, serf, master, squire, knight, lord, baron, viscount, count, earl, marquis, duke, prince, king

### `commander_ranks.exobiologist`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Rank.Exobiologist
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_ranks.explore`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Rank.Explore
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_ranks.federation`
- Type: `enum`
- Tier: `detail`
- Trigger/source: n/a
- Enum values: none, recruit, cadet, midshipman, petty_officer, chief_petty_officer, warrant_officer, ensign, lieutenant, lieutenant_commander, post_commander, post_captain, rear_admiral, vice_admiral, admiral

### `commander_ranks.mercenary`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Rank.Mercenary
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_ranks.soldier`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Rank.Soldier
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `commander_ranks.trade`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.Rank.Trade
- Enum values: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### `comms_event`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: Friends (<= 300s), Music (<= 300s), ReceiveText (<= 300s), SendText (<= 300s)
- Enum values: receive_text, send_text, music, friends, none

### `credits`
- Type: `number`
- Tier: `core`
- Trigger/source: paths: dashboard.Balance
- Sample values: 0, 2702325380

### `empire_reputation`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Reputation.Empire
- Sample values: 0

### `federation_reputation`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Reputation.Federation
- Sample values: 0

### `financial_activity`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: PayBounties (<= 1s), PayFines (<= 1s), PayLegacyFines (<= 1s), RedeemVoucher (<= 1s)
- Enum values: none, paid_fines, paid_bounties, redeemed_voucher, paid_legacy_fines, got_bounty

### `independent_reputation`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Reputation.Independent
- Sample values: 0

### `legal_state`
- Type: `enum`
- Tier: `core`
- Trigger/source: paths: dashboard.LegalState
- Enum values: Clean, IllegalCargo, Speeding, Wanted, Hostile, PassengerWanted, Warrant, commit_crime, crime_victim

### `mode`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: foot_flags[0], foot_flags[1], foot_flags[2], ship_flags[24], ship_flags[25], ship_flags[26]
- Enum values: ship, srv, fighter, on_foot, in_taxi, in_multicrew, unknown

## Location

### `altitude`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Altitude
- Sample values: 0

### `body_name`
- Type: `string`
- Tier: `core`
- Trigger/source: paths: dashboard.BodyName
- Sample values: "HIP 54530 B 3 B Ring"

### `body_proximity`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: ApproachBody (<= 10s), LeaveBody (<= 5s) | flags: ship_flags[4]
- Enum values: far, approaching, orbital_cruise, leaving

### `breathable_atmosphere`
- Type: `enum`
- Tier: `detail`
- Trigger/source: flags: foot_flags[14]
- Enum values: no, yes

### `gravity_level`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Gravity
- Sample values: 0

### `has_lat_long`
- Type: `enum`
- Tier: `advanced`
- Trigger/source: flags: ship_flags[21]
- Enum values: no, yes

### `heading`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Heading
- Sample values: 0

### `latitude`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Latitude
- Sample values: 0

### `longitude`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Longitude
- Sample values: 0

### `market_id`
- Type: `number`
- Tier: `advanced`
- Trigger/source: paths: state.MarketID
- Sample values: 0

### `oxygen`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: foot_flags[6]
- Enum values: ok, low

### `oxygen_level`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Oxygen
- Sample values: 0

### `station_allegiance`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.StationAllegiance
- Enum values: unknown, alliance, empire, federation, independent, pirate, pilotsfederation

### `station_distance_ls`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.DistFromStarLS
- Sample values: 0

### `station_economy`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.StationEconomy
- Enum values: unknown, $economy_agri;, $economy_colony;, $economy_extraction;, $economy_hightech;, $economy_industrial;, $economy_military;, $economy_refinery;, $economy_service;, $economy_terraforming;, $economy_tourism;, $economy_engineer;, $economy_prison;, $economy_damaged;, $economy_rescue;, $economy_carrier;

### `station_faction`
- Type: `string`
- Tier: `detail`
- Trigger/source: paths: state.StationFaction.Name
- Sample values: "" (default)

### `station_government`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.StationGovernment
- Enum values: unknown, $government_anarchy;, $government_communism;, $government_confederacy;, $government_cooperative;, $government_corporate;, $government_democracy;, $government_dictatorship;, $government_feudal;, $government_patronage;, $government_prison;, $government_prisoncolony;, $government_theocracy;, $government_engineer;, $government_carrier;

### `station_name`
- Type: `string`
- Tier: `core`
- Trigger/source: paths: state.StationName
- Sample values: "" (default)

### `station_type`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.StationType
- Enum values: unknown, coriolis, orbis, ocellus, outpost, crateroutpost, craterport, megaship, asteroidbase, fleetcarrier

### `system_address`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.SystemAddress
- Sample values: 0

### `system_allegiance`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.SystemAllegiance
- Enum values: unknown, alliance, empire, federation, independent, pirate

### `system_economy`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.SystemEconomy
- Enum values: unknown, $economy_agri;, $economy_colony;, $economy_extraction;, $economy_hightech;, $economy_industrial;, $economy_military;, $economy_refinery;, $economy_service;, $economy_terraforming;, $economy_tourism;

### `system_event`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: Cargo (<= 300s), ClearSavedGame (<= 300s), Commander (<= 300s), Continued (<= 300s), FileHeader (<= 300s), LoadGame (<= 300s), Materials (<= 300s), Missions (<= 300s), NewCommander (<= 300s), Passengers (<= 300s), Powerplay (<= 300s), Progress (<= 300s), Rank (<= 300s), Reputation (<= 300s), Shutdown (<= 300s), StartUp (<= 300s), Statistics (<= 300s)
- Enum values: none, journal_started, journal_continued, game_reset, commander_created, game_loaded, commander_info, materials_loaded, cargo_loaded, missions_loaded, passengers_loaded, powerplay_status, rank_progress, ranks_loaded, reputation_loaded, statistics_loaded, startup, shutdown

### `system_faction`
- Type: `string`
- Tier: `detail`
- Trigger/source: paths: state.SystemFaction.Name
- Sample values: "" (default)

### `system_government`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.SystemGovernment
- Enum values: unknown, $government_anarchy;, $government_communism;, $government_confederacy;, $government_cooperative;, $government_corporate;, $government_democracy;, $government_dictatorship;, $government_feudal;, $government_patronage;, $government_theocracy;

### `system_name`
- Type: `string`
- Tier: `core`
- Trigger/source: events: CarrierJump, FSDJump, Location | paths: state.StarSystem
- Sample values: "" (default)

### `system_population`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Population
- Sample values: 0

### `system_security`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: state.SystemSecurity
- Enum values: unknown, $system_security_low;, $system_security_medium;, $system_security_high;, $galaxy_map_info_state_anarchy;, $system_security_lawless;

### `system_x`
- Type: `number`
- Tier: `advanced`
- Trigger/source: paths: state.StarPos.0
- Sample values: 0

### `system_y`
- Type: `number`
- Tier: `advanced`
- Trigger/source: paths: state.StarPos.1
- Sample values: 0

### `system_z`
- Type: `number`
- Tier: `advanced`
- Trigger/source: paths: state.StarPos.2
- Sample values: 0

### `temperature_state`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: foot_flags[10], foot_flags[11], foot_flags[8], foot_flags[9]
- Enum values: ok, cold, hot, very_cold, very_hot

### `temperature_value`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Temperature
- Sample values: 0

## Statistics

### `stat_bounty_hunting_profit`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Combat.Bounty_Hunting_Profit
- Sample values: 0

### `stat_combat_bonds`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Combat.Combat_Bonds
- Sample values: 0

### `stat_exploration_profit`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Exploration.Exploration_Profits
- Sample values: 0

### `stat_hyperspace_jumps`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Exploration.Total_Hyperspace_Jumps
- Sample values: 0

### `stat_insurance_claims`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Bank_Account.Insurance_Claims
- Sample values: 0

### `stat_mining_profit`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Mining.Mining_Profits
- Sample values: 0

### `stat_spent_on_ships`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Bank_Account.Spent_On_Ships
- Sample values: 0

### `stat_systems_visited`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Exploration.Systems_Visited
- Sample values: 0

### `stat_time_played`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Exploration.Time_Played
- Sample values: 0

### `stat_total_wealth`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Bank_Account.Current_Wealth
- Sample values: 0

### `stat_trading_profit`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Statistics.Trading.Market_Profits
- Sample values: 0

## On-Foot

### `aim`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: foot_flags[5]
- Enum values: normal, aiming

### `flag_aim_down_sight`
- Type: `enum`
- Tier: `advanced`
- Trigger/source: flags: foot_flags[5]
- Enum values: no, yes

### `flag_low_health`
- Type: `enum`
- Tier: `advanced`
- Trigger/source: flags: foot_flags[7]
- Enum values: normal, low

### `flag_low_oxygen`
- Type: `enum`
- Tier: `advanced`
- Trigger/source: flags: foot_flags[6]
- Enum values: normal, low

### `health_level`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: dashboard.Health
- Sample values: 0

### `on_foot_location`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: foot_flags[16], foot_flags[17], foot_flags[18], foot_flags[3], foot_flags[4]
- Enum values: none, station, planet, hangar, social_space, exterior

### `selected_weapon`
- Type: `enum`
- Tier: `detail`
- Trigger/source: paths: dashboard.SelectedWeapon
- Enum values: none, unarmed, energylink, arc_cutter, profile_analyser, genetic_sampler, kinetic, laser, plasma, rocket, grenades

### `suit`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: BuySuit (<= 1s), SellSuit (<= 1s), UpgradeSuit (<= 1s)
- Enum values: none, purchased, sold, upgraded

### `transport_activity`
- Type: `enum`
- Tier: `detail`
- Trigger/source: events: BookDropship (<= 1s), BookTaxi (<= 1s), CancelDropship (<= 1s), CancelTaxi (<= 1s)
- Enum values: none, taxi_booked, taxi_cancelled, dropship_booked, dropship_cancelled

### `weapon`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: BuyWeapon (<= 1s), SellWeapon (<= 1s), UpgradeWeapon (<= 1s)
- Enum values: none, purchased, sold, upgraded

## Travel

### `destination_system`
- Type: `string`
- Tier: `detail`
- Trigger/source: paths: dashboard.Destination.System
- Sample values: "" (default)

### `exploration_event`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: BuyExplorationData (<= 300s), CodexEntry (<= 300s), DiscoveryScan (<= 300s), FSSAllBodiesFound (<= 300s), FSSDiscoveryScan (<= 300s), FSSSignalDiscovered (<= 300s), MaterialDiscarded (<= 300s), MaterialDiscovered (<= 300s), MultiSellExplorationData (<= 300s), NavBeaconScan (<= 300s), SAAScanComplete (<= 300s), SAASignalsFound (<= 300s), Scan (<= 300s), Screenshot (<= 300s), SellExplorationData (<= 300s), SellOrganicData (<= 300s)
- Enum values: scan, f_s_s_discovery_scan, f_s_s_signal_discovered, f_s_s_all_bodies_found, s_a_a_scan_complete, s_a_a_signals_found, codex_entry, screenshot, discovery_scan, nav_beacon_scan, material_discarded, material_discovered, none, buy_exploration_data, multi_sell_exploration_data, sell_organic_data, sell_exploration_data

### `flag_altitude_from_avg_radius`
- Type: `enum`
- Tier: `advanced`
- Trigger/source: flags: ship_flags[29]
- Enum values: no, yes

### `fsd_target_remaining_jumps`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.FSDTarget.RemainingJumpsInRoute
- Sample values: 0

### `fsd_target_system`
- Type: `string`
- Tier: `core`
- Trigger/source: paths: state.FSDTarget.Name
- Sample values: "" (default)

### `has_route`
- Type: `enum`
- Tier: `core`
- Trigger/source: n/a
- Enum values: no, yes

### `next_system_in_route`
- Type: `string`
- Tier: `core`
- Trigger/source: paths: state.Route.0.StarSystem
- Sample values: "" (default)

### `route_length`
- Type: `number`
- Tier: `core`
- Trigger/source: n/a
- Sample values: 0

## SRV

### `flag_srv_turret`
- Type: `enum`
- Tier: `advanced`
- Trigger/source: flags: ship_flags[13]
- Enum values: retracted, deployed

### `srv`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: DockSRV (<= 1s), LaunchSRV (<= 1s), SRVDestroyed (<= 1s)
- Enum values: none, deployed, docked, destroyed

### `srv_deployed_state`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: DockSRV (<= 3s), LaunchSRV (<= 3s) | flags: ship_flags[26]
- Enum values: stowed, deployed, just_launched, just_docked

### `srv_drive_assist`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[15]
- Enum values: off, on

### `srv_handbrake`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[12]
- Enum values: off, on

### `srv_high_beam`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[31]
- Enum values: off, on

### `srv_under_ship`
- Type: `enum`
- Tier: `detail`
- Trigger/source: flags: ship_flags[14]
- Enum values: no, yes

## Fleet Carrier

### `carrier_event`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: CarrierBankTransfer (<= 300s), CarrierBuy (<= 300s), CarrierCancelDecommission (<= 300s), CarrierCrewServices (<= 300s), CarrierDecommission (<= 300s), CarrierDepositFuel (<= 300s), CarrierDockingPermission (<= 300s), CarrierFinance (<= 300s), CarrierJump (<= 300s), CarrierJumpCancelled (<= 300s), CarrierJumpRequest (<= 300s), CarrierModulePack (<= 300s), CarrierNameChanged (<= 300s), CarrierStats (<= 300s), CarrierTradeOrder (<= 300s)
- Enum values: none, carrier_jump, carrier_buy, carrier_stats, carrier_jump_request, carrier_jump_cancelled, carrier_finance, carrier_bank_transfer, carrier_deposit_fuel, carrier_crew_services, carrier_trade_order, carrier_docking_permission, carrier_name_change, carrier_module_pack, carrier_decommission, carrier_cancel_decommission

### `fleet_carrier_balance`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.FleetCarrier.Balance
- Sample values: 0

### `fleet_carrier_callsign`
- Type: `string`
- Tier: `core`
- Trigger/source: paths: state.FleetCarrier.Callsign
- Sample values: "" (default)

### `fleet_carrier_fuel`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.FleetCarrier.Fuel
- Sample values: 0

### `fleet_carrier_name`
- Type: `string`
- Tier: `core`
- Trigger/source: paths: state.FleetCarrier.Name
- Sample values: "" (default)

### `has_fleet_carrier`
- Type: `enum`
- Tier: `core`
- Trigger/source: n/a
- Enum values: no, yes

## Powerplay

### `powerplay_activity`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: PowerplayCollect (<= 1s), PowerplayDefect (<= 1s), PowerplayDeliver (<= 1s), PowerplayJoin (<= 1s), PowerplayLeave (<= 1s), PowerplaySalary (<= 1s), PowerplayVote (<= 1s), PowerplayVoucher (<= 1s)
- Enum values: none, joined, left, defected, delivered, collected, voted, received_salary, received_voucher

### `powerplay_merits`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Powerplay.Merits
- Sample values: 0

### `powerplay_pledged`
- Type: `enum`
- Tier: `core`
- Trigger/source: n/a
- Enum values: no, yes

### `powerplay_power`
- Type: `enum`
- Tier: `core`
- Trigger/source: paths: state.Powerplay.Power
- Enum values: none, aisling_duval, arissa_lavigny-duval, denton_patreus, zemina_torval, edmund_mahon, li_yong-rui, felicia_winters, zachary_hudson, yuri_grom, archon_delaine, pranav_antal

### `powerplay_rank`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Powerplay.Rank
- Sample values: 0

### `powerplay_time_pledged`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Powerplay.TimePledged
- Sample values: 0

## Inventory

### `cargo_inventory`
- Type: `array`
- Tier: `detail`
- Trigger/source: paths: state.Cargo
- Sample values: []

### `encoded_materials_count`
- Type: `number`
- Tier: `core`
- Trigger/source: n/a
- Sample values: 0

### `manufactured_materials_count`
- Type: `number`
- Tier: `core`
- Trigger/source: n/a
- Sample values: 0

### `raw_materials_count`
- Type: `number`
- Tier: `core`
- Trigger/source: n/a
- Sample values: 0

### `total_materials_count`
- Type: `number`
- Tier: `core`
- Trigger/source: n/a
- Sample values: 0

## Squadron

### `in_squadron`
- Type: `enum`
- Tier: `core`
- Trigger/source: n/a
- Enum values: no, yes

### `squadron_activity`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: AppliedToSquadron (<= 1s), DisbandedSquadron (<= 1s), InvitedToSquadron (<= 1s), JoinedSquadron (<= 1s), KickedFromSquadron (<= 1s), LeftSquadron (<= 1s), SharedBookmarkToSquadron (<= 1s), SquadronCreated (<= 1s), SquadronDemotion (<= 1s), SquadronPromotion (<= 1s), SquadronStartup (<= 1s), WonATrophyForSquadron (<= 1s)
- Enum values: none, created, joined, left, applied, disbanded, invited, kicked, shared_bookmark, demoted, promoted, startup, won_trophy

### `squadron_name`
- Type: `string`
- Tier: `core`
- Trigger/source: paths: state.Squadron.Name
- Sample values: "" (default)

### `squadron_rank`
- Type: `number`
- Tier: `detail`
- Trigger/source: paths: state.Squadron.Rank
- Sample values: 0

## HUD

### `gui_focus`
- Type: `enum`
- Tier: `core`
- Trigger/source: paths: dashboard.GuiFocus
- Enum values: NoFocus, InternalPanel, ExternalPanel, CommsPanel, RolePanel, StationServices, GalaxyMap, SystemMap, Orrery, FSS, SAA, Codex

### `hud_mode`
- Type: `enum`
- Tier: `core`
- Trigger/source: flags: ship_flags[27]
- Enum values: combat, analysis

## Missions

### `mission_event`
- Type: `enum`
- Tier: `core`
- Trigger/source: events: CommunityGoal (<= 300s), CommunityGoalDiscard (<= 300s), CommunityGoalJoin (<= 300s), CommunityGoalReward (<= 300s), MissionAbandoned (<= 300s), MissionAccepted (<= 300s), MissionCompleted (<= 300s), MissionFailed (<= 300s), MissionRedirected (<= 300s)
- Enum values: none, mission_accepted, mission_completed, mission_failed, mission_abandoned, mission_redirected, community_goal, community_goal_join, community_goal_discard, community_goal_reward

### `missions_active_count`
- Type: `number`
- Tier: `core`
- Trigger/source: n/a
- Sample values: 0

## Session

### `game_mode`
- Type: `enum`
- Tier: `core`
- Trigger/source: paths: state.GameMode
- Enum values: Open, Solo, Group, shutdown

### `game_version`
- Type: `enum`
- Tier: `core`
- Trigger/source: paths: state.Horizons, state.Odyssey
- Enum values: base, horizons, odyssey
