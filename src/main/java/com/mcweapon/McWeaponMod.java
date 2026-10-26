package com.mcweapon;

import com.mojang.brigadier.arguments.StringArgumentType;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.creativetab.v1.CreativeModeTabEvents;
import net.fabricmc.fabric.api.creativetab.v1.FabricCreativeModeTab;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.AttackBlockCallback;
import net.fabricmc.fabric.api.event.player.AttackEntityCallback;
import net.minecraft.commands.Commands;
import net.minecraft.core.Registry;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.component.UseEffects;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class McWeaponMod implements ModInitializer {
    public static final String MOD_ID = "mcweapon";
    public static final Map<String, GunItem> GUN_ITEMS = new LinkedHashMap<>();
    public static final List<Item> ALL_ITEMS = new ArrayList<>();
    public static final Map<String, SoundEvent> SOUND_EVENTS = new LinkedHashMap<>();

    public static Item TACTICAL_AMMO_BOX;

    @Override
    public void onInitialize() {
        // 1. Register Custom Gunshot SoundEvents
        String[] soundKeys = {
            "sniper_heavy", "sniper_awp", "smg_fast", "smg_shot",
            "pistol_heavy", "pistol_shot", "silenced_shot", "rifle_heavy", "shotgun_blast"
        };
        for (String sk : soundKeys) {
            Identifier sid = Identifier.fromNamespaceAndPath(MOD_ID, "gun." + sk);
            SoundEvent se = SoundEvent.createVariableRangeEvent(sid);
            Registry.register(BuiltInRegistries.SOUND_EVENT, sid, se);
            SOUND_EVENTS.put(sk, se);
        }

        // 2. Register All 13 Iconic Firearms
        List<WeaponSpec> specs = List.of(
            // Snipers
            new WeaponSpec("awp", "AWP 极地狙击步枪", "AWP Sniper Rifle", "SNIPER", "狙击步枪", 38.0f, 1, 30, 10, 46, 120.0, 0.035f, 0.0005f, 8.0f, 1.8f, 2, false, "sniper_awp", Rarity.EPIC),
            new WeaponSpec("barrett_m82", "巴雷特 M82A1 重型反器材狙击枪", "Barrett M82A1 .50 BMG", "SNIPER", "反器材重狙", 55.0f, 1, 40, 10, 56, 140.0, 0.045f, 0.0005f, 10.0f, 1.8f, 4, false, "sniper_heavy", Rarity.EPIC),
            new WeaponSpec("kar98k", "Kar98k 经典毛瑟狙击步枪", "Karabiner 98k Sniper", "SNIPER", "栓动狙击枪", 28.0f, 1, 22, 5, 38, 105.0, 0.025f, 0.0008f, 6.0f, 2.0f, 2, false, "sniper_awp", Rarity.RARE),

            // SMGs
            new WeaponSpec("kriss_vector", "KRISS Vector 维克托短剑冲锋枪", "KRISS Vector .45 ACP", "SMG", "高射速冲锋枪", 5.5f, 1, 1, 33, 26, 48.0, 0.032f, 0.005f, 1.6f, 1.5f, 1, false, "smg_fast", Rarity.RARE),
            new WeaponSpec("mp5", "HK MP5A5 战术冲锋枪", "HK MP5A5 Tactical SMG", "SMG", "战术冲锋枪", 7.0f, 1, 2, 30, 28, 56.0, 0.024f, 0.004f, 2.0f, 1.5f, 1, false, "smg_shot", Rarity.RARE),
            new WeaponSpec("p90", "FN P90 突击冲锋枪", "FN P90 PDW", "SMG", "大弹匣冲锋枪", 6.5f, 1, 2, 50, 34, 58.0, 0.028f, 0.0045f, 2.0f, 1.5f, 2, false, "smg_shot", Rarity.RARE),
            new WeaponSpec("uzi", "Micro UZI 乌兹微型冲锋枪", "Micro UZI SMG", "SMG", "微型冲锋枪", 5.0f, 1, 1, 32, 24, 42.0, 0.038f, 0.007f, 1.5f, 1.4f, 1, false, "smg_fast", Rarity.UNCOMMON),

            // Pistols
            new WeaponSpec("desert_eagle", "沙漠之鹰 .50 AE 重型手枪", "Desert Eagle .50 AE", "PISTOL", "重型手枪", 19.0f, 1, 9, 7, 26, 68.0, 0.022f, 0.002f, 2.2f, 1.75f, 2, false, "pistol_heavy", Rarity.RARE),
            new WeaponSpec("glock_18", "格洛克 18C 全自动战术手枪", "Glock-18C Auto Pistol", "PISTOL", "全自动手枪", 6.0f, 1, 2, 20, 22, 46.0, 0.030f, 0.005f, 1.5f, 1.5f, 1, false, "pistol_shot", Rarity.UNCOMMON),
            new WeaponSpec("usp_s", "USP-S 消音特战手枪", "USP-S Tactical Silenced", "PISTOL", "消音手枪", 11.0f, 1, 5, 12, 22, 58.0, 0.015f, 0.0015f, 1.8f, 1.65f, 1, true, "silenced_shot", Rarity.RARE),

            // Assault Rifles & Shotgun
            new WeaponSpec("ak47", "AK-47 黄金卡拉什尼科夫步枪", "AK-47 Assault Rifle", "RIFLE", "突击步枪", 12.5f, 1, 3, 30, 34, 85.0, 0.028f, 0.003f, 3.0f, 1.65f, 2, false, "rifle_heavy", Rarity.RARE),
            new WeaponSpec("m4a1", "M4A1-S 消音战术卡宾步枪", "M4A1-S Tactical Carbine", "RIFLE", "战术步枪", 10.5f, 1, 2, 30, 30, 88.0, 0.018f, 0.002f, 3.0f, 1.6f, 1, true, "silenced_shot", Rarity.RARE),
            new WeaponSpec("spas_12", "SPAS-12 战术泵动霰弹枪", "Franchi SPAS-12 Shotgun", "SHOTGUN", "战术霰弹枪", 4.5f, 8, 16, 8, 36, 32.0, 0.068f, 0.022f, 1.6f, 1.4f, 1, false, "shotgun_blast", Rarity.RARE)
        );

        for (WeaponSpec spec : specs) {
            registerGun(spec);
        }

        // Register Tactical Ammo Box
        ResourceKey<Item> ammoKey = ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(MOD_ID, "tactical_ammo_box"));
        TACTICAL_AMMO_BOX = new Item(new Item.Properties().setId(ammoKey).stacksTo(1).rarity(Rarity.EPIC));
        Registry.register(BuiltInRegistries.ITEM, ammoKey, TACTICAL_AMMO_BOX);
        ALL_ITEMS.add(TACTICAL_AMMO_BOX);

        // 3. Creative Mode Tab
        ResourceKey<CreativeModeTab> tabKey = ResourceKey.create(
            Registries.CREATIVE_MODE_TAB,
            Identifier.fromNamespaceAndPath(MOD_ID, "main")
        );
        CreativeModeTab tab = FabricCreativeModeTab.builder()
            .title(Component.translatable("itemGroup.mcweapon.tab"))
            .icon(() -> new ItemStack(GUN_ITEMS.get("awp")))
            .build();
        Registry.register(BuiltInRegistries.CREATIVE_MODE_TAB, tabKey, tab);

        CreativeModeTabEvents.modifyOutputEvent(tabKey).register(output -> {
            for (Item item : ALL_ITEMS) {
                output.accept(item);
            }
        });

        CreativeModeTabEvents.modifyOutputEvent(
            ResourceKey.create(Registries.CREATIVE_MODE_TAB, Identifier.withDefaultNamespace("combat"))
        ).register(output -> {
            for (Item item : ALL_ITEMS) {
                output.accept(item);
            }
        });

        // 4. Prevent Block Breaking & Support Left-Click Scope Toggle
        AttackBlockCallback.EVENT.register((player, level, hand, pos, direction) -> {
            ItemStack stack = player.getItemInHand(hand);
            if (stack.getItem() instanceof GunItem gun) {
                if (level instanceof ServerLevel serverLevel) {
                    if (player.isShiftKeyDown() && gun.getAmmo(stack) < gun.getSpec().magazineSize()) {
                        gun.startReload(serverLevel, player, stack);
                    } else {
                        GunItem.toggleScopeLock(serverLevel, player, stack);
                    }
                }
                return InteractionResult.FAIL;
            }
            return InteractionResult.PASS;
        });

        // 5. Prevent Left-Click Breaking Non-Living Entities
        AttackEntityCallback.EVENT.register((player, level, hand, entity, hitResult) -> {
            ItemStack stack = player.getItemInHand(hand);
            if (stack.getItem() instanceof GunItem) {
                if (!(entity instanceof LivingEntity) || (entity instanceof ArmorStand)) {
                    return InteractionResult.FAIL;
                }
            }
            return InteractionResult.PASS;
        });

        // 6. Server Tick: Clean up scope speed attribute when not holding a gun + F-key quick reload detection
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            for (ServerPlayer player : server.getPlayerList().getPlayers()) {
                ItemStack main = player.getMainHandItem();
                ItemStack off = player.getOffhandItem();

                if (main.isEmpty() && off.getItem() instanceof GunItem offGun) {
                    long now = player.level().getGameTime();
                    if (!offGun.isReloading(off, now) && offGun.getAmmo(off) < offGun.getSpec().magazineSize()) {
                        player.setItemInHand(InteractionHand.MAIN_HAND, off.copy());
                        player.setItemInHand(InteractionHand.OFF_HAND, ItemStack.EMPTY);
                        ItemStack restoredMain = player.getMainHandItem();
                        if (player.level() instanceof ServerLevel sl) {
                            offGun.startReload(sl, player, restoredMain);
                        }
                        continue;
                    }
                }

                boolean holdingGun = (main.getItem() instanceof GunItem) || (off.getItem() instanceof GunItem);
                if (!holdingGun) {
                    GunItem.applyScopeAttribute(player, false, 1.0f);
                }
            }
        });

        // 7. Register /weapon command
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            dispatcher.register(Commands.literal("weapon")
                .executes(ctx -> {
                    ServerPlayer sp = ctx.getSource().getPlayerOrException();
                    sendWeaponHelp(sp);
                    return 1;
                })
                .then(Commands.literal("all")
                    .executes(ctx -> {
                        ServerPlayer sp = ctx.getSource().getPlayerOrException();
                        for (Item item : ALL_ITEMS) {
                            sp.getInventory().add(new ItemStack(item));
                        }
                        sp.sendSystemMessage(Component.literal("§a[MCWeapon] 已向您的背包发放全套 13 款热门现代枪械与战术弹药箱！"));
                        return 1;
                    }))
                .then(Commands.literal("scope")
                    .executes(ctx -> {
                        ServerPlayer sp = ctx.getSource().getPlayerOrException();
                        ItemStack main = sp.getMainHandItem();
                        if (main.getItem() instanceof GunItem && sp.level() instanceof ServerLevel sl) {
                            GunItem.toggleScopeLock(sl, sp, main);
                        }
                        return 1;
                    }))
                .then(Commands.literal("reload")
                    .executes(ctx -> {
                        ServerPlayer sp = ctx.getSource().getPlayerOrException();
                        ItemStack main = sp.getMainHandItem();
                        if (main.getItem() instanceof GunItem gun && sp.level() instanceof ServerLevel sl) {
                            gun.startReload(sl, sp, main);
                        }
                        return 1;
                    }))
                .then(Commands.literal("give")
                    .then(Commands.argument("model", StringArgumentType.word())
                        .executes(ctx -> {
                            ServerPlayer sp = ctx.getSource().getPlayerOrException();
                            String model = StringArgumentType.getString(ctx, "model").toLowerCase();
                            GunItem gun = GUN_ITEMS.get(model);
                            if (gun == null) {
                                sp.sendSystemMessage(Component.literal("§c未知枪械型号: " + model + "。可用型号: " + String.join(", ", GUN_ITEMS.keySet())));
                                return 0;
                            }
                            sp.getInventory().add(new ItemStack(gun));
                            sp.sendSystemMessage(Component.literal("§a[MCWeapon] 已发放: §e" + gun.getSpec().zhName()));
                            return 1;
                        })))
            );
        });
    }

    private static void sendWeaponHelp(ServerPlayer player) {
        player.sendSystemMessage(Component.literal("§6========== [MCWeapon 现代战术武器库] =========="));
        player.sendSystemMessage(Component.literal("§e• 狙击枪: §fawp (38伤害/8x镜), barrett_m82 (55伤害/10x镜/4穿), kar98k (28伤害/6x镜)"));
        player.sendSystemMessage(Component.literal("§e• 冲锋枪: §fkriss_vector (20发/秒), mp5 (10发/秒), p90 (50发大弹匣), uzi (20发/秒)"));
        player.sendSystemMessage(Component.literal("§e• 手枪: §fdesert_eagle (19伤害), glock_18 (全自动手枪), usp_s (消音高精)"));
        player.sendSystemMessage(Component.literal("§e• 步枪/霰弹: §fak47, m4a1, spas_12 (8弹丸霰弹)"));
        player.sendSystemMessage(Component.literal("§b• 快捷指令: §f/weapon all §7(领取全部武器) | §f/weapon give <型号> §7| §f/weapon scope §7(切换倍镜) | §f/weapon reload §7(换弹)"));
        player.sendSystemMessage(Component.literal("§a• 操作说明: §f[按住右键] 开火 | [按住Shift 或 左键方块] 开镜放大 | [按F键] 快速换弹"));
    }

    private static GunItem registerGun(WeaponSpec spec) {
        ResourceKey<Item> key = ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(MOD_ID, spec.id()));
        Item.Properties props = new Item.Properties()
            .setId(key)
            .stacksTo(1)
            .rarity(spec.rarity())
            .component(DataComponents.USE_EFFECTS, new UseEffects(true, false, 1.0f));
        GunItem item = new GunItem(spec, SOUND_EVENTS.get(spec.soundKey()), props);
        Registry.register(BuiltInRegistries.ITEM, key, item);
        GUN_ITEMS.put(spec.id(), item);
        ALL_ITEMS.add(item);
        return item;
    }
}
