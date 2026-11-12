class WGZA_DogTag: ItemBase
{
    protected ref WGZA_TagRecord m_WGZARecord;
    protected int m_WGZAState;
    protected int m_WGZALastRequestTime = -1000;

    void WGZA_DogTag()
    {
        RegisterNetSyncVariableInt("m_WGZAState", WGZA_TagProtocol.BLANK, WGZA_TagProtocol.RELEASED);
    }

    bool WGZAInitialize(WGZA_TagRecord record)
    {
        if (!GetGame().IsServer() || m_WGZARecord || !record || !record.IsValid() || record.Released) return false;
        m_WGZARecord = record;
        m_WGZAState = WGZA_TagProtocol.PROTECTED;
        SetAllowDamage(false);
        SetSynchDirty();
        WGZA_TagStore.Save(m_WGZARecord);
        return true;
    }

    bool WGZABelongsTo(string ownerId)
    {
        return m_WGZARecord && m_WGZARecord.OwnerSteam64 == ownerId;
    }

    bool WGZAHasRecord()
    {
        return m_WGZARecord && m_WGZARecord.IsValid();
    }

    bool WGZAIsReleased()
    {
        return m_WGZAState == WGZA_TagProtocol.RELEASED;
    }

    bool WGZAIsProtected()
    {
        Man holder = GetHierarchyRootPlayer();
        return !WGZAIsReleased() && holder && holder.IsAlive();
    }

    void WGZARecordDeath(string source, float health)
    {
        if (!GetGame().IsServer() || !WGZAHasRecord() || m_WGZARecord.Released) return;
        m_WGZARecord.DeathUTC = WGZA_TagRecord.NowUTC();
        m_WGZARecord.HealthAtDeath = Math.Clamp(health, 0, 100);
        m_WGZARecord.DeathSource = source;
        if (source == "") m_WGZARecord.DeathSource = "Unknown";
        m_WGZARecord.Released = true;
        m_WGZAState = WGZA_TagProtocol.RELEASED;
        SetAllowDamage(true);
        SetSynchDirty();
        WGZA_TagStore.Save(m_WGZARecord);
    }

    override bool CanDetachAttachment(EntityAI parent)
    {
        if (WGZAIsProtected()) return false;
        return super.CanDetachAttachment(parent);
    }

    override bool CanPutAsAttachment(EntityAI parent)
    {
        PlayerBase player = PlayerBase.Cast(parent);
        // Collected trophies go in cargo/hands, never another character's identity slot.
        if (!player || !player.WGZAIsIssuingTag() || WGZAIsReleased()) return false;
        return super.CanPutAsAttachment(parent);
    }

    override bool CanPutIntoHands(EntityAI parent)
    {
        if (WGZAIsProtected()) return false;
        return super.CanPutIntoHands(parent);
    }

    override bool CanPutInCargo(EntityAI parent)
    {
        if (WGZAIsProtected()) return false;
        return super.CanPutInCargo(parent);
    }

    override bool CanRemoveFromCargo(EntityAI parent)
    {
        if (WGZAIsProtected()) return false;
        return super.CanRemoveFromCargo(parent);
    }

    override bool CanRemoveFromHands(EntityAI parent)
    {
        if (WGZAIsProtected()) return false;
        return super.CanRemoveFromHands(parent);
    }

    override bool CanBeFSwaped()
    {
        if (WGZAIsProtected()) return false;
        return super.CanBeFSwaped();
    }

    override void OnVariablesSynchronized()
    {
        super.OnVariablesSynchronized();
        if (m_WGZARecord && m_WGZARecord.Released != WGZAIsReleased()) m_WGZARecord = null;
    }

    void WGZARequestRecord()
    {
        if (GetGame().IsServer() || WGZAHasRecord() || m_WGZAState == WGZA_TagProtocol.BLANK) return;
        int now = GetGame().GetTime();
        if (now - m_WGZALastRequestTime < 1000) return;
        m_WGZALastRequestTime = now;
        RPCSingleParam(WGZA_TagProtocol.REQUEST_RECORD, new Param1<int>(1), true);
    }

    protected bool WGZACanInspect(PlayerBase requester)
    {
        if (!requester || !requester.IsAlive() || !WGZAHasRecord()) return false;
        Man holder = GetHierarchyRootPlayer();
        if (holder && holder.IsAlive() && holder != requester) return false;
        if (holder == requester) return true;
        return vector.DistanceSq(requester.GetPosition(), GetPosition()) <= 9;
    }

    // Preserve the engine's parameter names: Enforce overrides bind rpc_type.
    override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
    {
        super.OnRPC(sender, rpc_type, ctx);
        if (rpc_type == WGZA_TagProtocol.REQUEST_RECORD && GetGame().IsServer())
        {
            if (!sender) return;
            Param1<int> request;
            if (!ctx.Read(request) || request.param1 != 1) return;
            PlayerBase requester = PlayerBase.Cast(sender.GetPlayer());
            if (!WGZACanInspect(requester) || !requester.WGZATryRecordRequest()) return;
            string json, error;
            if (JsonFileLoader<WGZA_TagRecord>.MakeData(m_WGZARecord, json, error, false))
                RPCSingleParam(WGZA_TagProtocol.RECEIVE_RECORD, new Param1<string>(json), true, sender);
        }
        else if (rpc_type == WGZA_TagProtocol.RECEIVE_RECORD && !GetGame().IsServer())
        {
            Param1<string> response;
            if (!ctx.Read(response) || response.param1.Length() > 4096) return;
            WGZA_TagRecord record = new WGZA_TagRecord;
            string loadError;
            if (!JsonFileLoader<WGZA_TagRecord>.LoadData(response.param1, record, loadError)) return;
            if (!record || !record.IsValid()) return;
            // A pre-death reply may arrive after the release synchronization.
            if (WGZAIsReleased() && !record.Released) return;
            m_WGZARecord = record;
        }
    }

    override bool NameOverride(out string output)
    {
        output = "WolfGamingZA Dog Tag";
        if (WGZAHasRecord()) output += " [" + m_WGZARecord.TagNumber + "]";
        return true;
    }

    override bool DescriptionOverride(out string output)
    {
        WGZARequestRecord();
        if (WGZAHasRecord()) output = m_WGZARecord.Describe();
        else output = "WolfGamingZA survivor identity tag.\nInspect your own tag or a collectible tag within 3 metres to read its record.";
        return true;
    }

    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);
        ctx.Write(1); // Item storage schema; independent of the DayZ version.
        ctx.Write(m_WGZARecord);
    }

    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!super.OnStoreLoad(ctx, version)) return false;
        int schema;
        if (!ctx.Read(schema) || schema != 1) return false;
        m_WGZARecord = new WGZA_TagRecord;
        if (!ctx.Read(m_WGZARecord) || !WGZAHasRecord()) return false;
        m_WGZAState = WGZA_TagProtocol.PROTECTED;
        if (m_WGZARecord.Released) m_WGZAState = WGZA_TagProtocol.RELEASED;
        SetAllowDamage(m_WGZARecord.Released);
        SetSynchDirty();
        return true;
    }
}
