package com.mcweapon.mixin;

import com.mcweapon.GunItem;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Player.class)
public class PlayerScopeMixin {
    @Inject(method = "isScoping", at = @At("HEAD"), cancellable = true)
    private void mcweapon$onIsScoping(CallbackInfoReturnable<Boolean> cir) {
        Player self = (Player) (Object) this;
        if (GunItem.isPlayerScopingWithGun(self)) {
            cir.setReturnValue(true);
        }
    }
}
