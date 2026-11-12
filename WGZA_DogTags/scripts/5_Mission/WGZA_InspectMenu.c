modded class InspectMenuNew
{
    protected WGZA_DogTag m_WGZAInspectedTag;
    protected float m_WGZARefreshElapsed;

    override void SetItem(EntityAI item)
    {
        m_WGZAInspectedTag = WGZA_DogTag.Cast(item);
        super.SetItem(item);
    }

    override void Update(float timeslice)
    {
        super.Update(timeslice);
        if (!m_WGZAInspectedTag) return;
        m_WGZARefreshElapsed += timeslice;
        if (m_WGZARefreshElapsed < 0.25) return;
        m_WGZARefreshElapsed = 0;
        // Refresh the vanilla description after an asynchronous, authorized reply.
        InspectMenuNew.UpdateItemInfo(layoutRoot, m_WGZAInspectedTag);
    }
}
