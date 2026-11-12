modded class PlayerBase
{
    protected bool m_WGZAIssuingTag;
    protected bool m_WGZAIssuedThisSession;
    protected int m_WGZALastRecordRequest = -200;

    bool WGZAIsIssuingTag()
    {
        return GetGame().IsServer() && m_WGZAIssuingTag;
    }

    bool WGZATryRecordRequest()
    {
        int now = GetGame().GetTime();
        if (now - m_WGZALastRecordRequest < 200) return false;
        m_WGZALastRecordRequest = now;
        return true;
    }

    WGZA_DogTag WGZAGetOwnTag()
    {
        return WGZA_DogTag.Cast(FindAttachmentBySlotName(WGZA_TagProtocol.SLOT));
    }

    void WGZAEnsureTag()
    {
        if (!GetGame().IsServer() || !IsAlive() || !GetIdentity()) return;
        int slot = InventorySlots.GetSlotIdFromString(WGZA_TagProtocol.SLOT);
        if (slot == InventorySlots.INVALID)
        {
            Print("[WGZA DogTags] Missing identity slot. Check that the PBO is loaded on server and client.");
            return;
        }

        EntityAI existing = FindAttachmentBySlotName(WGZA_TagProtocol.SLOT);
        if (existing)
        {
            WGZA_DogTag savedTag = WGZA_DogTag.Cast(existing);
            if (!savedTag || !savedTag.WGZAHasRecord() || !savedTag.WGZABelongsTo(GetIdentity().GetPlainId()) || savedTag.WGZAIsReleased())
            {
                // Never overwrite another item or forge/reassign an existing identity.
                Print("[WGZA DogTags] Invalid identity-slot contents; issuance stopped for this character.");
                return;
            }
            m_WGZAIssuedThisSession = true;
            GetInventory().SetSlotLock(slot, true);
            return;
        }

        // A missing tag after successful issuance indicates an admin/other-mod removal.
        // Do not mint another identity in response to repeated connection callbacks.
        if (m_WGZAIssuedThisSession)
        {
            Print("[WGZA DogTags] Issued tag is missing; refusing duplicate issuance in this session.");
            return;
        }
        WGZA_TagRecord record = WGZA_TagRecord.Create(GetIdentity());
        if (!record) return;
        m_WGZAIssuingTag = true;
        WGZA_DogTag tag = WGZA_DogTag.Cast(GetInventory().CreateAttachmentEx("WGZA_DogTag", slot));
        m_WGZAIssuingTag = false;
        if (!tag)
        {
            Print("[WGZA DogTags] Could not create identity-slot attachment; no tag was issued.");
            return;
        }
        if (!tag.WGZAInitialize(record))
        {
            GetGame().ObjectDelete(tag);
            Print("[WGZA DogTags] Identity initialization failed; incomplete item removed.");
            return;
        }
        m_WGZAIssuedThisSession = true;
        GetInventory().SetSlotLock(slot, true);
    }

    override bool CanReceiveAttachment(EntityAI attachment, int slotId)
    {
        if (slotId == InventorySlots.GetSlotIdFromString(WGZA_TagProtocol.SLOT))
        {
            if (!WGZAIsIssuingTag() || !WGZA_DogTag.Cast(attachment)) return false;
        }
        return super.CanReceiveAttachment(attachment, slotId);
    }

    override bool CanReleaseAttachment(EntityAI attachment)
    {
        WGZA_DogTag tag = WGZA_DogTag.Cast(attachment);
        if (tag && tag == WGZAGetOwnTag() && tag.WGZAIsProtected()) return false;
        return super.CanReleaseAttachment(attachment);
    }

    protected string WGZADeathSource(Object killer)
    {
        if (!killer) return "Unknown (no source reported by engine)";
        if (killer == this) return "Self or environment (engine did not distinguish)";
        PlayerBase player = PlayerBase.Cast(killer);
        EntityAI entity = EntityAI.Cast(killer);
        if (!player && entity) player = PlayerBase.Cast(entity.GetHierarchyRootPlayer());
        if (player && player.GetIdentity())
            return WGZA_TagRecord.CleanName(player.GetIdentity().GetName()) + " (" + killer.GetType() + ")";
        return killer.GetType();
    }

    override void EEKilled(Object killer)
    {
        if (GetGame().IsServer())
        {
            WGZA_DogTag tag = WGZAGetOwnTag();
            if (tag)
            {
                tag.WGZARecordDeath(WGZADeathSource(killer), GetHealth01("", "Health") * 100);
                GetInventory().SetSlotLock(InventorySlots.GetSlotIdFromString(WGZA_TagProtocol.SLOT), false);
            }
        }
        // Release before the vanilla death/corpse processing and persistence callbacks.
        super.EEKilled(killer);
    }
}
