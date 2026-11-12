class CfgPatches
{
    class WGZA_DogTags
    {
        units[] = {"WGZA_DogTag"};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data", "DZ_Scripts", "DZ_Gear_Consumables", "DZ_Characters"};
    };
};
class CfgMods
{
    class WGZA_DogTags
    {
        dir = "WGZA_DogTags";
        name = "WolfGamingZA Dog Tags";
        author = "WolfGamingZA";
        type = "mod";
        dependencies[] = {"World", "Mission"};
        class defs
        {
            class worldScriptModule
            {
                value = "";
                files[] = {"WGZA_DogTags/scripts/4_World"};
            };
            class missionScriptModule
            {
                value = "";
                files[] = {"WGZA_DogTags/scripts/5_Mission"};
            };
        };
    };
};
class CfgSlots
{
    class Slot_WGZA_DogTag
    {
        name = "WGZA_DogTag";
        displayName = "WolfGamingZA Dog Tag";
        ghostIcon = "set:dayz_inventory image:missing";
        show = "true";
    };
};
class CfgVehicles
{
    class SurvivorBase
    {
        attachments[] += {"WGZA_DogTag"};
        class InventoryEquipment
        {
            playerSlots[] += {"Slot_WGZA_DogTag"};
        };
    };
    class Inventory_Base;
    class WGZA_DogTag: Inventory_Base
    {
        scope = 2;
        displayName = "WolfGamingZA Dog Tag (Prototype)";
        descriptionShort = "A survivor identity record. Inspect it to read its history.";
        // Temporary vanilla geometry; no Workshop assets are redistributed.
        model = "\dz\gear\consumables\Paper.p3d";
        inventorySlot[] = {"WGZA_DogTag"};
        simulation = "inventoryItem";
        physLayer = "item_small";
        rotationFlags = 16;
        weight = 15;
        itemSize[] = {1, 1};
        canBeSplit = 0;
        varQuantityInit = 0;
        varQuantityMin = 0;
        varQuantityMax = 0;
        stackedUnit = "";
        quantityBar = 0;
        absorbency = 0;
        class DamageSystem
        {
            class GlobalHealth
            {
                class Health
                {
                    hitpoints = 100;
                    healthLevels[] = {{1, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0, {}}};
                };
            };
        };
    };
};
