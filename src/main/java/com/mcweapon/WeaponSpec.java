package com.mcweapon;

import net.minecraft.world.item.Rarity;

public record WeaponSpec(
    String id,
    String zhName,
    String enName,
    String categoryId,
    String zhCategory,
    float damage,
    int pellets,
    int fireIntervalTicks,
    int magazineSize,
    int reloadTicks,
    double range,
    float hipSpread,
    float scopedSpread,
    float zoomLevel,
    float headshotMultiplier,
    int piercing,
    boolean silenced,
    String soundKey,
    Rarity rarity
) {
    public float shotsPerSecond() {
        return 20.0f / Math.max(1, fireIntervalTicks);
    }

    public float theoreticalDps() {
        return damage * pellets * shotsPerSecond();
    }
}
