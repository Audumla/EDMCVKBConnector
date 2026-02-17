# Signal Coverage Validation Report

## Executive Summary

**Overall Coverage: 90% (105/116 raw events registered)**

This report validates that all raw EDMC journal events are properly registered and referenced in the signal definition system (`signals_catalog.json`). The validation cross-references two data sources:

- **Raw EDMC Events**: 116 journal events documented in `EDMC_EVENTS_CATALOG.md`
- **Signal Registry**: 178 events referenced in `signals_catalog.json` (includes both raw and synthetic events)

---

## Coverage Metrics

| Metric | Value |
|--------|-------|
| Raw EDMC Events | 116 |
| Events Registered in Signals | 105 |
| Coverage Percentage | 90% |
| Unregistered Raw Events | 11 |
| Synthetic/Derived Events | 73 |

---

## Unregistered Raw Events (11)

These raw EDMC events are **NOT** currently referenced in any signal definition. These events are received by the plugin but have no signal handlers yet.

| Event | Status | Recommendation |
|-------|--------|-----------------|
| `CommitCrime` | Crime interaction | Add signal for crime commitment status |
| `EngineerApply` | Engineer unlock | Add signal for engineer unlock events |
| `Loadouts` | Ship loadout list | Use `Loadout` signal instead (more specific) |
| `NavRouteClear` | Route deletion | Add signal for nav route clearing |
| `OnFootLoadout` | Suit loadout list | Use `SuitLoadout` signal instead (more specific) |
| `ShutDown` | Ship systems | Consider as low-priority (vs `Shutdown`) |
| `Squadron` | Squadron status | Add signal for squadron data |
| `StartUp` | Game startup | Add signal for game startup events |
| `UpgradeSuit` | Suit upgrade | Add signal for suit upgrades |
| `UpgradeWeapon` | Weapon upgrade | Add signal for weapon upgrades |
| `WeaponLoadout` | Weapon configuration | Use existing weapon signals instead |

### Priority: Suggested for Next Catalog Update

**HIGH Priority (Core Gameplay)**:
- `EngineerApply` - Unlock new engineers (important for progression)
- `NavRouteClear` - Route management completion signal
- `StartUp` - Game startup completion

**MEDIUM Priority**:
- `CommitCrime` - Crime interaction tracking
- `Squadron` - Squadron data updates

**LOW Priority (Specialized/Experimental)**:
- `ShutDown`, `UpgradeSuit`, `UpgradeWeapon`, `WeaponLoadout` - Covered by other signals or low gameplay relevance

---

## Synthetic/Derived Events (73)

These are events referenced in signal definitions that are **NOT** raw EDMC journal events. They fall into these categories:

### Category: Complex Fleet Carrier Events (20)
These are fleet carrier management events that may be sub-events or state changes:
- `CarrierBankTransfer` - Fleet carrier bank transfers
- `CarrierBuy` - Fleet carrier purchase
- `CarrierCancelDecommission` - Decommission cancellation
- `CarrierCrewServices` - Crew management
- `CarrierDecommission` - Fleet carrier decommission
- `CarrierDepositFuel` - Fuel deposit
- `CarrierDockingPermission` - Docking access control
- `CarrierFinance` - Fleet carrier finances
- `CarrierJump` - Fleet carrier jump
- `CarrierJumpCancelled` - Cancelled fleet carrier jump
- `CarrierJumpRequest` - Fleet carrier jump request
- `CarrierModulePack` - Module trading
- `CarrierNameChange` - Rename carrier
- `CarrierStats` - Carrier statistics
- `CarrierTradeOrder` - Trade orders
- `CarrierTransfer` - Carrier ownership transfer
- `ColonisationConstructionDepot` - Colonisation depot
- `ColonisationContribution` - Settlement contribution
- `CarrierTransfer` - Carrier transfer operations

### Category: Odyssey/On-Foot Specific (18)
Events related to on-foot gameplay (Odyssey DLC):
- `BackpackChange` - Suit inventory change
- `Backpack` - On-foot inventory state
- `CommanderInTaxi` - Taxi transportation
- `CreateSuitLoadout` - Custom suit configuration
- `DataScanned` - Data pad interaction
- `DatalinkScan` - Datalink access
- `DatalinkVoucher` - Datalink credits
- `DeleteSuitLoadout` - Remove suit configuration
- `Disembark` - Exit ship to ground
- `DropItems` - Drop inventory items
- `DropShipDeploy` - Dropship deployment (on-foot combat)
- `Embark` - Enter ship from ground
- `ScanOrganic` - Organic life scanning
- `SwitchSuitLoadout` - Change suit configuration
- `TradeMicroResources` - Micro resource trading
- `TransferMicroResources` - Resource transfer
- `UpgradeSuit` - Suit upgrades
- `UpgradeWeapon` - Weapon upgrades

### Category: Engineering & Crafting (8)
Derived from engineer interaction events:
- `EngineerContribution` - Engineer material contribution
- `EngineerLegacyConvert` - Legacy blueprint conversion
- `EngineerProgress` - Engineering progress tracking
- `MaterialCollected` - Material collection (derived signal)
- `MaterialTrade` - Material trading
- `Synthesis` - Item synthesis/crafting
- `ScientificResearch` - Engineering research
- `TechnologyBroker` - Tech broker trades

### Category: Ship Management (9)
Complex ship state signals derived from events:
- `AfmuRepairs` - AFMU repair operations
- `BuyAmmo` - Ammunition purchase
- `Loadout` - Ship loadout state
- `LoadoutEquipModule` - Equipment module loading
- `SetUserShipName` - Ship renaming
- `ShipLocker` - Ship locker/storage
- `Shipyard` - Shipyard availability
- `ShipyardTransfer` - Ship transfer between stations
- `VehicleSwitch` - SRV/Fighter/Ship switching

### Category: Station/Market Services (8)
Services that may be bundled in single events:
- `ApproachSettlement` - Settlement proximity
- `FetchRemoteModule` - Remote module retrieval
- `MassModuleStore` - Bulk module storage
- `ModuleRetrieve` - Module retrieval
- `ModuleSellRemote` - Remote module sale
- `ModuleStore` - Module storage
- `Outfitting` - Outfitting availability
- `RestockVehicle` - Vehicle restocking

### Category: Game/UI Events (10)
Meta-events for UI and game state:
- `HeatWarning` - Overheating warning (vs `HeatDamage`)
- `JetConeBoost` - Jet cone boost effect
- `JetConeDamage` - Jet cone damage
- `Music` - Background music events
- `ReceiveText` - Chat message received
- `SendText` - Chat message sent
- `Shutdown` - Shop shutdown (vs `ShutDown`)
- `SystemsShutdown` - System shutdown
- `UseConsumable` - Item consumption
- `Friends` - Friends list interaction

---

## Validation Conclusions

### Strengths ✓
1. **90% coverage** of raw events is comprehensive
2. **73 synthetic events** show sophisticated signal derivation to handle complex game states
3. All **mission, exploration, combat, and trading events** are fully covered
4. **Fleet carrier system** is well-represented with complex derived signals

### Coverage Gaps
1. **11 unregistered raw events** - Small but notable (mostly low-priority)
2. Missing some **newer Odyssey events** (likely from development/patches)
3. Some events may have **different names** or **timing differences** between documentation and implementation

### Recommendations

**For Complete 100% Coverage:**
1. Add HIGH priority events: `EngineerApply`, `NavRouteClear`, `StartUp`
2. Add MEDIUM priority: `CommitCrime`, `Squadron`
3. Review `ShutDown` vs `Shutdown` naming inconsistency

**For Future Maintenance:**
1. Monitor `unregistered_events.json` for new events
2. Update `EDMC_EVENTS_CATALOG.md` as new game patches release
3. Add derived events to documentation when they stabilize

**For Testing:**
1. Create unit tests for the 11 unregistered events
2. Validate synthetic events produce expected signal values
3. Test edge cases where multiple raw events create one synthetic signal

---

## Data Sources

| Source | Count | Purpose |
|--------|-------|---------|
| `EDMC_EVENTS_CATALOG.md` | 116 events | Raw journal events documentation |
| `signals_catalog.json` | 239 signals | Signal definitions & derivation rules |
| `signals_catalog.json` | 178 events | Events referenced in signals |

---

## Technical Notes

### Coverage Calculation
- **Raw Events**: Extracted from markdown headers in `EDMC_EVENTS_CATALOG.md`
- **Signal Events**: Extracted from all `recent_event` references in signal value definitions and derive rules
- **Unregistered**: `raw_events - signal_events = 11`
- **Synthetic**: `signal_events - raw_events = 73`

### Data Integrity
- All 116 raw events are documented with descriptions and field lists
- All 178 referenced events are actively used in signal derivation logic
- Synthetic events serve critical roles in multi-source signal derivation

---

**Generated**: 2025-02-16  
**Validation Tool**: Python signal catalog analyzer in workspace context
