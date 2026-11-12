# Central Economy configuration

The scripts issue tags; they should not spawn as random loot.

Copy `types_WGZA_DogTags.xml` into your **test** mission's `custom` directory,
for example `mpmissions/dayzOffline.chernarusplus/custom/`.

Add this entry inside the existing `<economycore>` element in that mission's
`cfgeconomycore.xml`, preserving all existing entries:

```xml
<ce folder="custom">
    <file name="types_WGZA_DogTags.xml" type="types" />
</ce>
```

If the mission already has `<ce folder="custom">`, add only the `<file>` child
there. Do not introduce a second declaration for `WGZA_DogTag` in another types
file. The supplied entry has zero nominal/minimum counts and a seven-day
ground-item lifetime. It does not extend the lifetime of the corpse carrying a
tag; take a trophy before the corpse is cleaned up.

The mod's archive is created under the directory selected with `-profiles`:
`WGZA_DogTags/records/<uuid>.json`. These files contain player identity and death
records. Keep them with your server backups; they are not needed on clients and
must not be packed into the mod.
