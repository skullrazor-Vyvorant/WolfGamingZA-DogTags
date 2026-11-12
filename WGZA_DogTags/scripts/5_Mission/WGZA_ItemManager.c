modded class ItemManager
{
    protected ref Timer m_WGZATooltipRefresh;

    override void PrepareTooltip(EntityAI item, int x = 0, int y = 0)
    {
        super.PrepareTooltip(item, x, y);
        if (WGZA_DogTag.Cast(m_HoveredItem))
        {
            m_WGZATooltipRefresh = new Timer(CALL_CATEGORY_GUI);
            m_WGZATooltipRefresh.Run(0.25, this, "WGZARefreshTooltip", null, true);
        }
    }

    override void HideTooltip()
    {
        delete m_WGZATooltipRefresh;
        super.HideTooltip();
    }

    void WGZARefreshTooltip()
    {
        WGZA_DogTag tag = WGZA_DogTag.Cast(m_HoveredItem);
        if (tag) InspectMenuNew.UpdateItemInfo(m_TooltipWidget, tag);
    }
}
