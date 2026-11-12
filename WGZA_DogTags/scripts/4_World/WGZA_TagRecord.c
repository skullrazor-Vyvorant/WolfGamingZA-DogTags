// Original WolfGamingZA record format. Times are real UTC, not world time.
class WGZA_TagRecord
{
    int SchemaVersion = 1;
    string TagId;
    string TagNumber;
    string OwnerName;
    string OwnerSteam64;
    string CreatedUTC;
    bool Released;
    string DeathUTC;
    float HealthAtDeath = -1;
    string DeathSource;

    static string NowUTC()
    {
        int year, month, day, hour, minute, second;
        GetYearMonthDayUTC(year, month, day);
        GetHourMinuteSecondUTC(hour, minute, second);
        return year.ToStringLen(4) + "-" + month.ToStringLen(2) + "-" + day.ToStringLen(2) + "T" + hour.ToStringLen(2) + ":" + minute.ToStringLen(2) + ":" + second.ToStringLen(2) + "Z";
    }

    static string CleanName(string value)
    {
        value.Replace("\n", " ");
        value.Replace("\r", " ");
        value.Replace("\t", " ");
        if (value.LengthUtf8() > 64) value = value.SubstringUtf8(0, 64);
        return value;
    }

    static WGZA_TagRecord Create(PlayerIdentity identity)
    {
        if (!GetGame().IsServer() || !identity || identity.GetPlainId() == "") return null;
        WGZA_TagRecord record = new WGZA_TagRecord;
        int uuid[4];
        UUIDApi.Generate(uuid);
        record.TagId = UUIDApi.FormatString(uuid);
        // A readable abbreviation; TagId is the actual unique key.
        record.TagNumber = record.TagId.Substring(0, 8);
        record.OwnerName = CleanName(identity.GetName());
        record.OwnerSteam64 = identity.GetPlainId();
        record.CreatedUTC = NowUTC();
        return record;
    }

    bool IsValid()
    {
        if (SchemaVersion != 1 || OwnerSteam64 == "" || CreatedUTC == "") return false;
        if (TagId.Length() != 36 || TagNumber != TagId.Substring(0, 8)) return false;
        // Only canonical UUID characters can enter an archive filename.
        string hexCharacters = "0123456789abcdefABCDEF";
        for (int i = 0; i < 36; i++)
        {
            string character = TagId.Substring(i, 1);
            if (i == 8 || i == 13 || i == 18 || i == 23)
            {
                if (character != "-") return false;
            }
            else if (hexCharacters.IndexOf(character) == -1)
            {
                return false;
            }
        }
        if (Released && (DeathUTC == "" || DeathSource == "" || HealthAtDeath < 0)) return false;
        return true;
    }

    string Describe()
    {
        string text = "WolfGamingZA | Survivor identity\n";
        text += "Owner: " + OwnerName + "\nSteam64: " + OwnerSteam64;
        text += "\nIssued (UTC): " + CreatedUTC;
        text += "\nTag number: " + TagNumber + "\nTag ID: " + TagId;
        if (Released)
        {
            text += "\nStatus: Collectible";
            text += "\nDeath (UTC): " + DeathUTC;
            text += "\nHealth at death: " + HealthAtDeath.ToString() + "% (post-fatal sample)";
            text += "\nKiller/source: " + DeathSource;
        }
        else
        {
            text += "\nStatus: Protected while owner is alive";
        }
        return text;
    }
}

class WGZA_TagProtocol
{
    // Private, stable IDs; no framework or globally registered RPC manager needed.
    static const int REQUEST_RECORD = 871201;
    static const int RECEIVE_RECORD = 871202;
    static const int BLANK = 0;
    static const int PROTECTED = 1;
    static const int RELEASED = 2;
    static const string SLOT = "WGZA_DogTag";
}

class WGZA_TagStore
{
    static void Save(WGZA_TagRecord record)
    {
        if (!GetGame().IsServer() || !record || !record.IsValid()) return;
        string directory = "$profile:WGZA_DogTags";
        if (!FileExist(directory) && !MakeDirectory(directory))
        {
            Print("[WGZA DogTags] Cannot create profile directory; item persistence remains active.");
            return;
        }
        directory += "/records";
        if (!FileExist(directory) && !MakeDirectory(directory))
        {
            Print("[WGZA DogTags] Cannot create records directory; item persistence remains active.");
            return;
        }
        string error;
        if (!JsonFileLoader<WGZA_TagRecord>.SaveFile(directory + "/" + record.TagId + ".json", record, error))
            Print("[WGZA DogTags] Archive write failed: " + error);
    }
}
