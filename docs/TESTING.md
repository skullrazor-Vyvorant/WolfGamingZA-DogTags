# WolfGamingZA Dog Tags — development test guide

This is an unsigned source development build targeting DayZ 1.30. It has not
been compiled or exercised by DayZ. It uses vanilla paper geometry temporarily;
the tag code does not inherit paper's burning, writing or crafting behaviour.

## Install on a disposable test server and client

1. Back up the test server's mission storage and profiles. Use a separate test
   instance with its own profiles and storage, not the live WolfGamingZA server.
2. Extract `WGZA_DogTags-dev.zip` alongside the DayZ server and client executables.
   The resulting folder must be `@WGZA_DogTags/Addons/WGZA_DogTags.pbo`.
3. Load `-mod=@WGZA_DogTags` on **both** server and clients. When adding it to an
   existing mod list, append it to that list using a semicolon. `-serverMod` alone
   cannot load client scripts or the inventory slot.
4. If your test server enforces signatures, sign the PBO with DayZ Tools and
   install the public `.bikey` in the server's `keys` directory. Keep the private
   signing key outside this repository and distribution ZIP.
5. Add the included `server/types_WGZA_DogTags.xml` to the mission's Central
   Economy configuration using the instructions in `server/README.md`. This
   prevents natural loot spawning and supplies a seven-day ground-item lifetime.
6. Start the server with a writable `-profiles` directory. Check the fresh script
   log and RPT for `Can't compile`, config inheritance errors, missing models,
   and messages prefixed `[WGZA DogTags]`. A running process or open port does
   not establish that the mod loaded.
7. Join with a matching mod build on every client. Start with vanilla plus this
   mod; repeat the key cases with your actual server mod list afterwards.

Example Windows server invocation (adapt paths and retain your existing options):

```powershell
.\DayZServer_x64.exe -config=serverDZ.cfg -port=2302 "-profiles=profiles-wgza-test" "-mod=@WGZA_DogTags"
```

## Required gameplay checks

| Case | Procedure | Expected result |
| --- | --- | --- |
| Issuance | Spawn a fresh character; inspect all inventory slots. | Exactly one tag appears in the dedicated slot; other starting items remain. |
| Full inventory | Join with a survivor whose clothing/backpack and hands are full. | Tag uses its own slot and needs no cargo capacity. |
| Duplicate callbacks | Reconnect twice and record both the tag ID and item count. | One tag, identical ID, original owner name and original issue time. |
| Persistence | Cleanly stop/restart the server and reconnect. | Same tag and record; slot remains protected. |
| Living protection | Try drag/drop, quickbar, swaps, ground drop, cargo transfer and removal by a second player, including while restrained/unconscious. | The protected identity tag stays attached. Other gear works normally. |
| Identity integrity | Try placing a collected trophy in an empty identity slot. | It cannot replace the living character's own identity tag. |
| Inspection | Hover the tag, then middle-click it. | Server-authorized name, Steam64, issue time, short number, UUID and status load; native condition display works. |
| Read access | Try inspecting another living player's held/attached tag, then a tag farther than 3 metres away. | No fresh record is supplied. Own inventory and nearby accessible trophies can be inspected. |
| Death | Kill a test character using another connected player. | Tag unlocks; source, UTC death time and post-fatal health appear; identity fields stay unchanged. |
| Unknown source | Test a death with no source supplied by the engine. | Source is explicitly unknown; no previous attacker is guessed. |
| Trophies | Take the corpse's tag into a second player's hands/cargo, then restart. | It remains collectible and retains the dead owner's record. |
| Respawn | Respawn the first player while the second keeps the old tag. | New life gets a new UUID; old tag is unchanged. |
| Archive | Inspect `$profile:WGZA_DogTags/records/<uuid>.json` on the server. | Issuance creates an archive; observed death updates the same file. |
| Cleanup | Put a trophy on the ground, then restart inside its configured lifetime. | It persists according to the mission's Central Economy rules. |

Record the server build, client build, loaded mod list, exact steps and current
log excerpts for failures. Do not treat this table as evidence that tests ran.

## Known boundaries

- `CreatedUTC` means **tag issuance time**. Existing survivors first receive a
  tag when they connect after installation; their earlier spawn time is unknown.
- Eight-character tag numbers are display abbreviations, not globally unique
  identifiers. The full server-generated UUID is the persistent key.
- Health is sampled in the death callback and is normally zero. It is not
  pre-hit health. Kill attribution uses only the callback's source. Deaths not
  observed by the mod cannot acquire a historical death record.
- The item is authoritative persistence. JSON files are server-side archives,
  not an automatic item recovery system or a transactional database. Preserve
  normal mission/profile backups. Collected tags follow normal item/corpse cleanup.
- Admin deletion, force-moving inventory through another mod and restoring
  inconsistent backups are outside normal player inventory protection. After
  external deletion, a later reconnect/restart can issue a replacement tag.
- This storage schema supersedes the earlier, untested Paper-based scaffold.
  No migration from that scaffold's hypothetical saved tags is included.
- Records intentionally expose the original owner's Steam64 ID to authorized
  readers. Other living players' inventory records are not served by the RPC.
- Original model/texture source lives in `assets/`. It must be converted with
  DayZ Tools and integrated before the temporary vanilla model is replaced.
- There are no external script frameworks, runtime web services or API keys.

## Build verification available without DayZ

From the repository root, run:

```sh
python3 -m unittest discover -s tests -v
python3 tools/build.py
```

The Python suite checks packaging, integrity, repeatability and accidental-file
exclusion. It does **not** compile Enforce Script, exercise inventory RPCs or
prove gameplay behaviour. DayZ logs and the checks above are required for that.
