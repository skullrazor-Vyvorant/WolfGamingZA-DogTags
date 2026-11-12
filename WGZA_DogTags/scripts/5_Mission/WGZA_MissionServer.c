modded class MissionServer
{
    override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
    {
        super.InvokeOnConnect(player, identity);
        // Vanilla calls this after new-character setup and after loading a reconnect.
        if (player) player.WGZAEnsureTag();
    }
}
