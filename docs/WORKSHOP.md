# Build, sign and upload with the official DayZ tools

The cloud machine has no DayZ Tools or authenticated Steam session. This guide
and the accompanying script prepare publishing on your Windows PC. Nothing has
been uploaded to Steam by the cloud agent. Steam distribution does not fix
unresolved script or gameplay defects.

## 1. Install the official tools

In the Steam desktop client, enable **Tools** in the Library filter and install
**DayZ Tools**. Launch it once and complete its normal setup. Use the Steam
account that will own the Workshop item. Accept Steam's Workshop agreement if
Steam requests it. Enter passwords and Steam Guard codes only in Steam's own
local prompts; they do not belong in scripts, GitHub or chat.

## 2. Pack and sign

Extract the **Workshop kit**, which contains addon source and the build script.
It is different from the earlier unsigned development mod ZIP.

Open PowerShell in the extracted kit folder and run, adapting the installed
DayZ Tools path:

```powershell
& .\tools\Prepare-Workshop.ps1 -DayZToolsPath 'C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools'
```

If Windows blocks the downloaded script, inspect it, then use the file's
Properties **Unblock** option if available, according to your PC's policy.

The script requires `AddonBuilder.exe`, `DSCreateKey.exe` and `DSSignFile.exe`.
It creates a signing identity in `%LOCALAPPDATA%\WolfGamingZA\Signing` only when
both keys are absent. It keeps existing keys for subsequent updates. Back up
the `.biprivatekey` securely; never include it in a mod, Workshop item or GitHub.
The public `.bikey` is meant to be distributed to server operators.

Each run creates a new `dist\workshop\<build-id>` directory. Official Addon Builder
packs/binarizes the source and DSSignFile signs the resulting PBO. The upload
`content` folder contains only runtime files, the `.bisign`, public key and
server economy instructions. The script fails on tool errors or missing output.
It has not been executed on Windows in this cloud environment; check all native
tool output and do not upload a failed build.

## 3. Validate the same signed build on both ends

Copy the generated `content` folder to `@WGZA_DogTags` on your test server and
client. Remove the older locally loaded dog-tag mod entry so it does not also
load an older PBO. Keep the `.bisign` beside the PBO in `Addons`.

Copy the generated public `.bikey` from the mod's `Keys` folder into the server's
main `keys` folder. Load this mod through regular `-mod` on both ends. Keep
`verifySignatures=2`; signing replaces the need for an unsigned test exception.
Restart the server and client and complete `docs/TESTING.md`, including fresh
character, reconnect, server restart, protected inventory and death/collection.
The private key must remain on the build PC, never the server or clients.

## 4. Publish through Steam

**DayZ Tools Publisher (GUI):** launch the Publisher from DayZ Tools. Create a
new Workshop item, choose the generated `content` directory as the item content
and the generated `preview.png` as its preview. Use a development title and
description; the preview is a concept and the runtime still uses placeholder
geometry. Start with **Private** visibility until the gameplay checks pass.
The Publisher's successful result and real item URL establish that it uploaded.

**Optional SteamCMD route:** the generated `workshop_build_item.vdf` uses DayZ
app ID `221100` and defaults to private visibility. Run in your local SteamCMD
installation with your own account, not an anonymous login:

```text
steamcmd +login YOUR_STEAM_USERNAME +workshop_build_item "C:\full\path\to\workshop_build_item.vdf" +quit
```

Use interactive authentication; do not put a password in that command. Steam
may require additional account/Workshop setup. Do not interpret a prepared VDF
as a completed upload. Record the returned **published file ID** and item URL.

For subsequent builds, pass `-PublishedFileId YOUR_EXISTING_ITEM_ID` when running
the preparation script, or update the existing item in Publisher. Reusing the
ID preserves subscriptions; creating a new item each time does not.
The script also writes `meta.cpp` with that real ID when supplied. After the
first upload, ensure the uploaded content has metadata with the correct ID:
retain the Publisher-generated metadata if provided, or prepare/update the same
item with `-PublishedFileId` set to the newly returned ID. No ID is invented for
an item that has not yet been uploaded.

## 5. Switch the server and clients to the Workshop item

After validation, set the Workshop item's visibility to **Public** in Steam so
your server manager and players can retrieve it. In Architect, add its real
Workshop ID under regular **Client Mods**. Remove the old local dog-tag entry.
On the PC, subscribe and load the Workshop version and unload the old local
version. Ensure the server's main `keys` directory has the matching public key,
then restart and verify that both ends downloaded the same build.

The upload script defaults to private staging and never signs into Steam,
uploads, changes server settings or claims a gameplay test passed.
