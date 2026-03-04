# CWSTRAT.BAS Modularization Plan

This document proposes how to split the ~5,100-line CWSTRAT.BAS into smaller files using QB64's `$INCLUDE` metacommand. QB64 supports:

```qb64
'$INCLUDE: 'filename.bi'    ' at top - declarations
'$INCLUDE: 'filename.bm'    ' at bottom - SUB/FUNCTION bodies
```

---

## File Structure Overview

| File | Purpose | Approx Lines | SUBs |
|------|---------|--------------|------|
| **cws_globals.bi** | Shared declarations | ~120 | — |
| **CWSTRAT.BAS** | Main entry + loop + menu | ~670 | — |
| **cws_combat.bm** | Battle, capture, retreat | ~350 | battle, capture, retreat, fortify, cannon, surrender, strong, evaluate |
| **cws_army.bm** | Army ops | ~400 | armies, armystat, armyxy, newarmy, placearmy, movefrom, combine, resupply, cutoff, relieve, cancel |
| **cws_navy.bm** | Naval ops | ~750 | navy, ships, ironclad, schooner, chessie, barnacle, shiptype, shipicon, integrity |
| **cws_railroad.bm** | Railroad | ~180 | railroad, traincapacity, tinytrain |
| **cws_recruit.bm** | Recruitment | ~120 | recruit, commander |
| **cws_data.bm** | I/O & occupy | ~260 | filer, occupy |
| **cws_map.bm** | Map display | ~850 | usa, usamap, maptext, showcity, flashcity, icon, image2, snapshot, touchup, tupdate, mountain |
| **cws_ui.bm** | Menus & text | ~350 | menu, choices, topbar, banner, scribe, clrbot, clrrite, center, roman, mxw, blastem |
| **cws_flow.bm** | Game flow & events | ~380 | engine, iterate, victor, endit, events |
| **cws_util.bm** | Utilities | ~220 | TICK, animate, normal, starfin, stax, bub2, bubble |
| **cws_sound.bm** | Sound | ~30 | sndblst, sndfx, shen |
| **cws_report.bm** | Reports | ~350 | report |
| **cws_ai.bm** | AI | ~165 | smarts |
| **cws_misc.bm** | Misc screens | ~150 | capitol, newcity, maxx, void |

---

## 1. cws_globals.bi (include first)

All declarations that must exist before any code runs:

- `DECLARE SUB` for every subroutine (lines 1–88)
- `DEFINT A-Z`
- `COMMON SHARED` blocks (lines 90–102)
- `DIM SHARED` blocks (lines 104–113)
- `$EXEICON` and `_TITLE` (lines 115–116)

---

## 2. CWSTRAT.BAS (main program)

Keep in the main file:

- **Entry**: `replay = 0`, `newgame:`, initialization (lines 119–154)
- **Labels used by GOTO/GOSUB**: `iron:`, `notitle:`, `newmonth:`, `menu0:`, `endrnd:`, `optmen:`, `loader:`, `unionplus:`, `blanken:`, `topbar:`, `rusure:`, `filex:`
- **Main menu** and all `SELECT CASE choose` branches (through ~820)
- **DATA block** for font$ (lines 832–838)

Add includes:

```qb64
'$INCLUDE: 'cws_globals.bi'
' ... main code ...
'$INCLUDE: 'cws_combat.bm'
'$INCLUDE: 'cws_army.bm'
'$INCLUDE: 'cws_navy.bm'
'$INCLUDE: 'cws_railroad.bm'
'$INCLUDE: 'cws_recruit.bm'
'$INCLUDE: 'cws_data.bm'
'$INCLUDE: 'cws_map.bm'
'$INCLUDE: 'cws_ui.bm'
'$INCLUDE: 'cws_flow.bm'
'$INCLUDE: 'cws_util.bm'
'$INCLUDE: 'cws_sound.bm'
'$INCLUDE: 'cws_report.bm'
'$INCLUDE: 'cws_ai.bm'
'$INCLUDE: 'cws_misc.bm'
```

---

## 3. Module Contents (by domain)

### cws_combat.bm
- `battle` – combat resolution
- `capture` – city capture
- `retreat` – retreat logic
- `fortify` – fortification
- `cannon` – cannon graphic
- `surrender` – surrender logic
- `strong` – strength display
- `evaluate` – AI evaluation

**Dependencies**: icon, clrbot, scribe, flashcity, showcity, starfin, void, occupy, stax, menu

### cws_army.bm
- `armies` – army selection/movement
- `armystat` – army stats
- `armyxy` – army icon drawing
- `newarmy` – create army
- `placearmy` – place army
- `movefrom` – move origin
- `combine` – merge armies
- `resupply` – supply
- `cutoff` – cutoff check
- `relieve` – relieve commander
- `cancel` – cancel orders

**Dependencies**: icon, starfin, bubble, menu, stax, clrbot, occupy, bubble, choices

### cws_navy.bm
- `navy` – main navy logic (very large, ~430 lines)
- `ships` – ship display
- `ironclad` – ironclad graphic
- `schooner` – schooner graphic
- `chessie` – chessie graphic
- `barnacle` – barnacle logic
- `shiptype` – ship type
- `shipicon` – ship icon
- `integrity` – integrity check

### cws_railroad.bm
- `railroad` – railroad movement
- `traincapacity` – capacity calc
- `tinytrain` – train graphic

### cws_recruit.bm
- `recruit` – recruitment
- `commander` – commander selection

### cws_data.bm
- `filer` – load/save/init (switch 1,2,3)
- `occupy` – city occupation

### cws_map.bm
- `usa` – main map (~330 lines)
- `usamap` – map setup
- `maptext` – map labels
- `showcity` – city display
- `flashcity` – flash city
- `icon` – movement icons
- `image2` – image display
- `snapshot` – screen snapshot
- `touchup` – map touchup
- `tupdate` – turn update display
- `mountain` – mountain graphic

### cws_ui.bm
- `menu` – generic menu (~165 lines)
- `choices` – menu choices
- `topbar` – top bar
- `banner` – banner
- `scribe` – scribe/log
- `clrbot` – clear bottom
- `clrrite` – clear right
- `center` – center text
- `roman` – roman numerals
- `mxw` – max width
- `blastem` – blast effect

### cws_flow.bm
- `engine` – railroad engine display
- `iterate` – turn iteration
- `victor` – victory check (~130 lines)
- `endit` – end conditions
- `events` – random events (~150 lines)

### cws_util.bm
- `TICK` – delay
- `animate` – animation
- `normal` – normal distribution
- `starfin` – army range
- `stax` – stack display
- `bub2` – bubble sort (numeric)
- `bubble` – bubble sort (string)

### cws_sound.bm
- `sndblst` – sound blast
- `sndfx` – sound effects
- `shen` – Shenandoah tune

### cws_report.bm
- `report` – full report (~175 lines)

### cws_ai.bm
- `smarts` – AI logic (~165 lines)

### cws_misc.bm
- `capitol` – capitol screen
- `newcity` – new city
- `maxx` – max display
- `void` – void (adjacent strength)

---

## 4. Important Notes

### GOTO/GOSUB Labels
- Labels like `counter:`, `finix:` inside `cancel` stay in that SUB
- Labels like `unionplus:`, `blanken:` are in the main program and are GOSUB targets
- Keep all GOSUB targets in CWSTRAT.BAS

### SUB Dependencies
SUBs call each other heavily. Include order doesn't matter for SUBs (forward declarations handle it), but all modules must be included before the program ends.

### Include Order
Place all `$INCLUDE` for `.bm` files after the main program (after the last GOSUB target and before `END` if any). QB64 compiles the whole project together.

### Testing Strategy
1. Create cws_globals.bi and verify it compiles
2. Add one module (e.g. cws_util.bm) and move those SUBs
3. Compile and run; repeat for each module
4. Keep git commits small so you can bisect if something breaks

---

## 5. Alternative: Fewer, Larger Modules

If 14 modules is too many, collapse into 5–6:

| File | Contents |
|------|----------|
| cws_globals.bi | Same |
| cws_combat_army.bm | combat + army |
| cws_navy_rail.bm | navy + railroad |
| cws_map_ui.bm | map + ui |
| cws_game.bm | recruit, data, flow, util, sound, report, ai, misc |

---

## 6. Line Ranges for Extraction

Use these to extract SUBs (approximate, check boundaries):

| SUB | Start | End |
|-----|-------|-----|
| animate | 840 | 864 |
| armies | 866 | 891 |
| armystat | 893 | 903 |
| barnacle | 905 | 913 |
| battle | 914 | 1106 |
| ... | ... | ... |

Run `grep -n "^SUB " CWSTRAT.BAS` and `grep -n "^END SUB" CWSTRAT.BAS` to get exact ranges before cutting.

---

## 7. Implementation (Completed)

Modularization has been applied. Files created:

- **cws_globals.bi** - Shared declarations
- **cws_combat.bm** - battle, capture, retreat, fortify, cannon, surrender, strong, evaluate
- **cws_army.bm** - armies, armystat, armyxy, newarmy, placearmy, movefrom, combine, resupply, cutoff, relieve, cancel
- **cws_navy.bm** - barnacle, navy, shiptype, integrity, shipicon, ships, ironclad, schooner
- **cws_railroad.bm** - railroad, tinytrain, traincapacity
- **cws_recruit.bm** - recruit, commander
- **cws_data.bm** - filer, occupy
- **cws_map.bm** - flashcity, icon, showcity, snapshot, tupdate, image2, maptext, touchup, usa
- **cws_ui.bm** - center, clrbot, clrrite, scribe, topbar, flags, roman, choices, menu, mxw
- **cws_flow.bm** - iterate, endit, engine, events, victor, rwin
- **cws_util.bm** - animate, normal, bub2, bubble, starfin, stax, TICK
- **cws_sound.bm** - shen
- **cws_report.bm** - report
- **cws_ai.bm** - smarts
- **cws_misc.bm** - newcity, capitol, maxx, void

Original CWSTRAT.BAS backed up as CWSTRAT.BAS.bak. Compile with QB64 to verify.
