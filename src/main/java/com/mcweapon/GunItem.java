package com.mcweapon;

import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.ItemUseAnimation;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.item.component.TooltipDisplay;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

public class GunItem extends Item {
    public static final Identifier SCOPE_SPEED_MODIFIER_ID = Identifier.fromNamespaceAndPath(McWeaponMod.MOD_ID, "scope_zoom_fov");
    public static final DustParticleOptions LASER_DOT_BRIGHT = new DustParticleOptions(0xFF0000, 0.72f);
    public static final DustParticleOptions LASER_DOT_SCOPED = new DustParticleOptions(0xFF1111, 0.50f);
    public static final DustParticleOptions LASER_BEAM_FINE = new DustParticleOptions(0xFF2222, 0.30f);
    public static final DustParticleOptions BULLET_TRACER_GOLD = new DustParticleOptions(0xFFCC33, 0.42f);

    private static final Map<UUID, Long> LAST_FIRE_TICK = new ConcurrentHashMap<>();
    private static final Map<UUID, Boolean> PREV_SCOPE_STATE = new ConcurrentHashMap<>();

    private final WeaponSpec spec;
    private final SoundEvent customFireSound;

    public GunItem(WeaponSpec spec, SoundEvent customFireSound, Item.Properties properties) {
        super(properties);
        this.spec = spec;
        this.customFireSound = customFireSound;
    }

    public WeaponSpec getSpec() {
        return this.spec;
    }

    // === 1. STRICT ZERO BLOCK DESTRUCTION ===
    @Override
    public boolean canDestroyBlock(ItemStack stack, BlockState state, Level level, BlockPos pos, LivingEntity entity) {
        return false;
    }

    @Override
    public float getDestroySpeed(ItemStack stack, BlockState state) {
        return 0.0F;
    }

    @Override
    public boolean mineBlock(ItemStack stack, Level level, BlockState state, BlockPos pos, LivingEntity miningEntity) {
        return false;
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        Player player = context.getPlayer();
        if (player == null) {
            return InteractionResult.PASS;
        }
        return this.use(context.getLevel(), player, context.getHand());
    }

    // === 2. CONTINUOUS FULL-AUTO / SEMI-AUTO SHOOTING ===
    @Override
    public int getUseDuration(ItemStack stack, LivingEntity user) {
        return 72000;
    }

    @Override
    public ItemUseAnimation getUseAnimation(ItemStack stack) {
        return ItemUseAnimation.NONE;
    }

    @Override
    public InteractionResult use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        player.startUsingItem(hand);
        if (level instanceof ServerLevel serverLevel) {
            tryShoot(serverLevel, player, stack);
        }
        return InteractionResult.CONSUME;
    }

    @Override
    public void onUseTick(Level level, LivingEntity user, ItemStack stack, int remainingUseDuration) {
        if (level instanceof ServerLevel serverLevel && user instanceof Player player) {
            tryShoot(serverLevel, player, stack);
        }
    }

    // === 3. MAGAZINE & SCOPE NBT HELPERS ===
    public static CompoundTag getTag(ItemStack stack) {
        CustomData data = stack.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY);
        return data.copyTag();
    }

    public static void saveTag(ItemStack stack, CompoundTag tag) {
        stack.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
    }

    public int getAmmo(ItemStack stack) {
        CompoundTag tag = getTag(stack);
        if (!tag.contains("ammo")) {
            return spec.magazineSize();
        }
        return tag.getIntOr("ammo", spec.magazineSize());
    }

    public void setAmmo(ItemStack stack, int ammo) {
        CompoundTag tag = getTag(stack);
        tag.putInt("ammo", Mth.clamp(ammo, 0, spec.magazineSize()));
        saveTag(stack, tag);
    }

    public boolean isReloading(ItemStack stack, long gameTime) {
        CompoundTag tag = getTag(stack);
        long reloadEnd = tag.getLongOr("reloadEnd", 0L);
        return reloadEnd > gameTime;
    }

    public static boolean isScopeToggled(ItemStack stack) {
        if (stack.isEmpty() || !(stack.getItem() instanceof GunItem)) {
            return false;
        }
        return getTag(stack).getBooleanOr("scoped", false);
    }

    public static void toggleScopeLock(ServerLevel level, Player player, ItemStack stack) {
        if (!(stack.getItem() instanceof GunItem gun)) return;
        CompoundTag tag = getTag(stack);
        boolean next = !tag.getBooleanOr("scoped", false);
        tag.putBoolean("scoped", next);
        saveTag(stack, tag);

        level.playSound(null, player.getX(), player.getY(), player.getZ(),
            next ? SoundEvents.SPYGLASS_USE : SoundEvents.SPYGLASS_STOP_USING,
            SoundSource.PLAYERS, 1.0f, next ? 1.15f : 0.95f);

        if (player instanceof ServerPlayer sp) {
            String stateText = next
                ? "§b§l[🔍 光学倍镜已开启 " + String.format("%.1fx", gun.spec.zoomLevel()) + "]"
                : "§7[🎯 光学倍镜已关闭 - 腰射红点模式]";
            sp.sendOverlayMessage(Component.literal(stateText));
        }
    }

    public static boolean isPlayerScopingWithGun(Player player) {
        if (player == null) return false;
        ItemStack main = player.getMainHandItem();
        ItemStack off = player.getOffhandItem();
        ItemStack gunStack = (main.getItem() instanceof GunItem) ? main : ((off.getItem() instanceof GunItem) ? off : ItemStack.EMPTY);
        if (gunStack.isEmpty()) return false;
        return player.isShiftKeyDown() || isScopeToggled(gunStack);
    }

    public void startReload(ServerLevel level, Player player, ItemStack stack) {
        long now = level.getGameTime();
        if (isReloading(stack, now)) return;
        int currentAmmo = getAmmo(stack);
        if (currentAmmo >= spec.magazineSize()) return;

        boolean hasAmmoBox = hasTacticalAmmoBox(player);
        int effectiveReloadTicks = hasAmmoBox ? Math.max(8, spec.reloadTicks() / 2) : spec.reloadTicks();

        CompoundTag tag = getTag(stack);
        tag.putLong("reloadStart", now);
        tag.putLong("reloadEnd", now + effectiveReloadTicks);
        saveTag(stack, tag);

        level.playSound(null, player.getX(), player.getY(), player.getZ(),
            SoundEvents.IRON_DOOR_OPEN, SoundSource.PLAYERS, 0.7f, 1.45f);
        level.playSound(null, player.getX(), player.getY(), player.getZ(),
            SoundEvents.LEVER_CLICK, SoundSource.PLAYERS, 0.8f, 0.85f);

        if (player instanceof ServerPlayer sp) {
            sp.sendOverlayMessage(Component.literal("§e⟳ 正在换弹 [" + spec.zhName() + "] ... " + String.format("%.1fs", effectiveReloadTicks / 20.0f)));
        }
    }

    public static boolean hasTacticalAmmoBox(Player player) {
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack s = player.getInventory().getItem(i);
            if (!s.isEmpty() && s.is(McWeaponMod.TACTICAL_AMMO_BOX)) {
                return true;
            }
        }
        return false;
    }

    // === 4. CORE FIRING & HITSCAN ENTITY-ONLY DAMAGE ===
    public void tryShoot(ServerLevel level, Player player, ItemStack stack) {
        long now = level.getGameTime();

        CompoundTag tag = getTag(stack);
        long reloadEnd = tag.getLongOr("reloadEnd", 0L);
        if (reloadEnd > 0L) {
            if (now < reloadEnd) {
                return;
            } else {
                tag.remove("reloadStart");
                tag.remove("reloadEnd");
                tag.putInt("ammo", spec.magazineSize());
                saveTag(stack, tag);
            }
        }

        long lastFire = LAST_FIRE_TICK.getOrDefault(player.getUUID(), -9999L);
        if (now - lastFire < spec.fireIntervalTicks()) {
            return;
        }

        int ammo = getAmmo(stack);
        if (ammo <= 0) {
            level.playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.DISPENSER_FAIL, SoundSource.PLAYERS, 0.8f, 1.5f);
            startReload(level, player, stack);
            return;
        }

        LAST_FIRE_TICK.put(player.getUUID(), now);
        int remaining = ammo - 1;
        setAmmo(stack, remaining);

        if (spec.fireIntervalTicks() >= 8) {
            player.getCooldowns().addCooldown(stack, spec.fireIntervalTicks());
        }

        boolean scoped = isPlayerScopingWithGun(player);
        boolean hasAmmoBox = hasTacticalAmmoBox(player);
        float damageBonus = hasAmmoBox ? 1.15f : 1.0f;

        playGunshotSound(level, player);

        Vec3 eye = player.getEyePosition();
        Vec3 look = player.getLookAngle();
        Vec3 right = look.cross(new Vec3(0, 1, 0)).normalize();
        Vec3 muzzle = eye.add(look.scale(0.65)).add(right.scale(scoped ? 0.0 : 0.22)).add(0, -0.12, 0);
        if (!spec.silenced()) {
            level.sendParticles(ParticleTypes.SMOKE, muzzle.x, muzzle.y, muzzle.z, 2, 0.03, 0.03, 0.03, 0.01);
            if (spec.damage() >= 18.0f || spec.pellets() > 1) {
                level.sendParticles(ParticleTypes.FLAME, muzzle.x, muzzle.y, muzzle.z, 2, 0.02, 0.02, 0.02, 0.01);
            }
        }

        float spread = scoped ? spec.scopedSpread() : spec.hipSpread();
        boolean anyHit = false;
        boolean anyHeadshot = false;
        LivingEntity lastTargetHit = null;
        float totalDealt = 0.0f;

        for (int p = 0; p < spec.pellets(); p++) {
            Vec3 shotDir = applySpread(look, spread, level);
            ShotOutcome outcome = fireRay(level, player, eye, muzzle, shotDir, damageBonus);
            if (outcome.hitEntity != null) {
                anyHit = true;
                anyHeadshot |= outcome.headshot;
                lastTargetHit = outcome.hitEntity;
                totalDealt += outcome.damageDealt;
            }
        }

        if (anyHit && player instanceof ServerPlayer sp) {
            sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(),
                anyHeadshot ? SoundEvents.ARROW_HIT_PLAYER : SoundEvents.CROSSBOW_HIT,
                SoundSource.PLAYERS, 0.9f, anyHeadshot ? 1.25f : 1.0f);

            float remHp = Math.max(0.0f, lastTargetHit.getHealth());
            String headTag = anyHeadshot ? " §6§l[💥爆头暴击!]" : "";
            sp.sendOverlayMessage(Component.literal(
                "§c✦ 命中 " + lastTargetHit.getName().getString() +
                " §f(-" + String.format("%.1f", totalDealt) + "❤)" + headTag +
                " §7| 剩余生命: §a" + String.format("%.1f", remHp) + "❤" +
                " §7| 弹匣: §e" + remaining + "/" + spec.magazineSize()
            ));
        }

        if (remaining <= 0) {
            startReload(level, player, stack);
        }
    }

    private record ShotOutcome(LivingEntity hitEntity, boolean headshot, float damageDealt) {}

    private record CandidateHit(LivingEntity entity, Vec3 hitPos, double distSqr) {}

    private ShotOutcome fireRay(ServerLevel level, Player shooter, Vec3 start, Vec3 muzzle, Vec3 dir, float damageBonus) {
        Vec3 maxEnd = start.add(dir.scale(spec.range()));

        BlockHitResult blockHit = level.clip(new ClipContext(
            start, maxEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, shooter
        ));

        Vec3 effectiveEnd = maxEnd;
        if (blockHit.getType() != HitResult.Type.MISS) {
            effectiveEnd = blockHit.getLocation();
            Vec3 sparkPos = effectiveEnd.subtract(dir.scale(0.05));
            level.sendParticles(ParticleTypes.CRIT, sparkPos.x, sparkPos.y, sparkPos.z, 2, 0.02, 0.02, 0.02, 0.02);
        }

        AABB searchBox = new AABB(start, effectiveEnd).inflate(1.25);
        List<Entity> candidates = level.getEntities(shooter, searchBox, e ->
            e instanceof LivingEntity &&
            !(e instanceof ArmorStand) &&
            e != shooter &&
            e.isAlive() &&
            !e.isSpectator() &&
            e.isPickable()
        );

        List<CandidateHit> hits = new ArrayList<>();
        for (Entity e : candidates) {
            LivingEntity living = (LivingEntity) e;
            AABB targetBox = living.getBoundingBox().inflate(0.24);
            if (targetBox.contains(start)) {
                hits.add(new CandidateHit(living, start, 0.0));
            } else {
                Optional<Vec3> clipHit = targetBox.clip(start, effectiveEnd);
                if (clipHit.isPresent()) {
                    Vec3 hp = clipHit.get();
                    double d2 = start.distanceToSqr(hp);
                    if (d2 <= start.distanceToSqr(effectiveEnd)) {
                        hits.add(new CandidateHit(living, hp, d2));
                    }
                }
            }
        }

        hits.sort(Comparator.comparingDouble(CandidateHit::distSqr));

        Vec3 tracerEnd = (!hits.isEmpty() && spec.piercing() == 1) ? hits.get(0).hitPos() : effectiveEnd;
        spawnBulletTracer(level, muzzle, tracerEnd);

        if (hits.isEmpty()) {
            return new ShotOutcome(null, false, 0.0f);
        }

        int pierced = 0;
        LivingEntity primaryHit = null;
        boolean anyHead = false;
        float totalDamage = 0.0f;

        DamageSource dmgSource = level.damageSources().playerAttack(shooter);

        for (CandidateHit ch : hits) {
            if (pierced >= spec.piercing()) break;
            LivingEntity target = ch.entity();
            Vec3 hitPos = ch.hitPos();

            boolean isHeadshot = hitPos.y >= (target.getEyeY() - 0.34);
            float dmg = spec.damage() * damageBonus * (isHeadshot ? spec.headshotMultiplier() : 1.0f);
            if (pierced > 0) {
                dmg *= Math.pow(0.8, pierced);
            }

            target.setInvulnerableTime(0);
            boolean hurtOk = target.hurtServer(level, dmgSource, dmg);
            if (hurtOk) {
                Vec3 kb = dir.scale(spec.damage() >= 25.0f ? 0.35 : 0.08);
                target.addDeltaMovement(new Vec3(kb.x, 0.02, kb.z));

                level.sendParticles(
                    isHeadshot ? ParticleTypes.ENCHANTED_HIT : ParticleTypes.DAMAGE_INDICATOR,
                    hitPos.x, hitPos.y, hitPos.z,
                    isHeadshot ? 8 : 3,
                    0.12, 0.12, 0.12, 0.08
                );

                primaryHit = target;
                anyHead |= isHeadshot;
                totalDamage += dmg;
                pierced++;
            }
        }

        return new ShotOutcome(primaryHit, anyHead, totalDamage);
    }

    private void spawnBulletTracer(ServerLevel level, Vec3 from, Vec3 to) {
        double dist = from.distanceTo(to);
        if (dist < 0.5) return;
        Vec3 dir = to.subtract(from).normalize();
        double step = spec.categoryId().equals("SNIPER") ? 1.8 : 3.2;
        double maxDraw = Math.min(dist, 90.0);
        for (double d = 0.8; d < maxDraw; d += step) {
            Vec3 pt = from.add(dir.scale(d));
            if (spec.categoryId().equals("SNIPER")) {
                level.sendParticles(ParticleTypes.CRIT, true, true, pt.x, pt.y, pt.z, 1, 0, 0, 0, 0);
            } else {
                level.sendParticles(BULLET_TRACER_GOLD, true, false, pt.x, pt.y, pt.z, 1, 0, 0, 0, 0);
            }
        }
    }

    private Vec3 applySpread(Vec3 look, float spread, ServerLevel level) {
        if (spread <= 0.0001f) return look;
        double rx = (level.getRandom().nextGaussian()) * spread;
        double ry = (level.getRandom().nextGaussian()) * spread;
        double rz = (level.getRandom().nextGaussian()) * spread;
        return look.add(rx, ry, rz).normalize();
    }

    private void playGunshotSound(ServerLevel level, Player shooter) {
        float pitch = 0.96f + level.getRandom().nextFloat() * 0.08f;
        float volume = spec.silenced() ? 0.8f : (spec.categoryId().equals("SNIPER") ? 2.2f : 1.4f);

        if (this.customFireSound != null) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                this.customFireSound, SoundSource.PLAYERS, volume, pitch);
        }

        if (spec.silenced()) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.SNOWBALL_THROW, SoundSource.PLAYERS, 0.7f, 0.6f);
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.IRON_DOOR_CLOSE, SoundSource.PLAYERS, 0.45f, 1.9f);
        } else if (spec.categoryId().equals("SNIPER")) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.FIREWORK_ROCKET_LARGE_BLAST, SoundSource.PLAYERS, 1.8f, 0.65f);
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.GENERIC_EXPLODE.value(), SoundSource.PLAYERS, 0.7f, 1.55f);
        } else if (spec.categoryId().equals("SHOTGUN")) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.GENERIC_EXPLODE.value(), SoundSource.PLAYERS, 0.85f, 1.35f);
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.FIREWORK_ROCKET_BLAST, SoundSource.PLAYERS, 1.4f, 0.75f);
        } else if (spec.id().equals("desert_eagle") || spec.id().equals("ak47")) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.FIREWORK_ROCKET_BLAST, SoundSource.PLAYERS, 1.3f, 0.85f);
        } else {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.FIREWORK_ROCKET_BLAST, SoundSource.PLAYERS, 0.9f, 1.35f);
        }
    }

    // === 5. LASER SIGHT RED DOT, SCOPE ZOOM & HUD TICK ===
    @Override
    public void inventoryTick(ItemStack stack, ServerLevel level, Entity entity, EquipmentSlot slot) {
        if (!(entity instanceof ServerPlayer player)) return;

        boolean held = (slot == EquipmentSlot.MAINHAND || slot == EquipmentSlot.OFFHAND);
        if (!held) return;

        long now = level.getGameTime();

        CompoundTag tag = getTag(stack);
        long reloadEnd = tag.getLongOr("reloadEnd", 0L);
        if (reloadEnd > 0L && now >= reloadEnd) {
            tag.remove("reloadStart");
            tag.remove("reloadEnd");
            tag.putInt("ammo", spec.magazineSize());
            saveTag(stack, tag);
            level.playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.IRON_DOOR_CLOSE, SoundSource.PLAYERS, 0.8f, 1.5f);
            player.sendOverlayMessage(Component.literal("§a✔ [" + spec.zhName() + "] 弹匣装填完毕! (" + spec.magazineSize() + "/" + spec.magazineSize() + ")"));
        }

        boolean scoped = isPlayerScopingWithGun(player);
        boolean wasScoped = PREV_SCOPE_STATE.getOrDefault(player.getUUID(), false);
        if (scoped != wasScoped) {
            PREV_SCOPE_STATE.put(player.getUUID(), scoped);
            level.playSound(null, player.getX(), player.getY(), player.getZ(),
                scoped ? SoundEvents.SPYGLASS_USE : SoundEvents.SPYGLASS_STOP_USING,
                SoundSource.PLAYERS, 0.8f, scoped ? 1.15f : 0.95f);
        }
        applyScopeAttribute(player, scoped, spec.zoomLevel());

        if (slot == EquipmentSlot.MAINHAND || !(player.getMainHandItem().getItem() instanceof GunItem)) {
            renderLaserSightAndHud(level, player, stack, scoped, now);
        }
    }

    private void renderLaserSightAndHud(ServerLevel level, ServerPlayer player, ItemStack stack, boolean scoped, long now) {
        Vec3 eye = player.getEyePosition();
        Vec3 look = player.getLookAngle();
        double laserRange = Math.min(spec.range(), 100.0);
        Vec3 maxEnd = eye.add(look.scale(laserRange));

        BlockHitResult blockHit = level.clip(new ClipContext(
            eye, maxEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player
        ));
        Vec3 laserEnd = (blockHit.getType() != HitResult.Type.MISS)
            ? blockHit.getLocation().subtract(look.scale(0.06))
            : maxEnd;
        double closestDistSqr = eye.distanceToSqr(laserEnd);

        AABB searchBox = new AABB(eye, laserEnd).inflate(1.0);
        List<Entity> entities = level.getEntities(player, searchBox, e ->
            e instanceof LivingEntity &&
            !(e instanceof ArmorStand) &&
            e != player &&
            e.isAlive() &&
            !e.isSpectator() &&
            e.isPickable()
        );

        LivingEntity lockedTarget = null;
        boolean lockedHeadshot = false;
        for (Entity e : entities) {
            LivingEntity living = (LivingEntity) e;
            Optional<Vec3> hitOpt = living.getBoundingBox().inflate(0.22).clip(eye, laserEnd);
            if (hitOpt.isPresent()) {
                double d2 = eye.distanceToSqr(hitOpt.get());
                if (d2 < closestDistSqr) {
                    closestDistSqr = d2;
                    laserEnd = hitOpt.get();
                    lockedTarget = living;
                    lockedHeadshot = laserEnd.y >= (living.getEyeY() - 0.34);
                }
            }
        }

        DustParticleOptions dotParticle = scoped ? LASER_DOT_SCOPED : LASER_DOT_BRIGHT;
        level.sendParticles(dotParticle, true, true,
            laserEnd.x, laserEnd.y, laserEnd.z,
            lockedTarget != null ? 3 : 2,
            0.01, 0.01, 0.01, 0.0);

        Vec3 right = look.cross(new Vec3(0, 1, 0)).normalize();
        Vec3 barrelStart = eye.add(look.scale(0.8)).add(right.scale(scoped ? 0.08 : 0.24)).add(0, -0.14, 0);
        double totalDist = Math.sqrt(closestDistSqr);
        double beamDrawDist = Math.min(totalDist, 24.0);
        if (beamDrawDist > 1.2) {
            Vec3 beamVec = laserEnd.subtract(barrelStart);
            double beamLen = beamVec.length();
            if (beamLen > 0.5) {
                Vec3 beamDir = beamVec.normalize();
                for (double d = 1.2; d < Math.min(beamLen, 22.0); d += 2.2) {
                    Vec3 bp = barrelStart.add(beamDir.scale(d));
                    level.sendParticles(LASER_BEAM_FINE, true, false, bp.x, bp.y, bp.z, 1, 0, 0, 0, 0);
                }
            }
        }

        if (now % 4 == 0 && !isReloading(stack, now)) {
            int ammo = getAmmo(stack);
            String scopeBadge = scoped
                ? "§b[🔍开镜 " + String.format("%.1fx", spec.zoomLevel()) + "]"
                : "§7[腰射红点]";
            String targetBadge;
            if (lockedTarget != null) {
                String headHint = lockedHeadshot ? " §6[★爆头点]" : "";
                targetBadge = " §c| 🔴锁定: §f" + lockedTarget.getName().getString() +
                    " §c(" + String.format("%.1f", lockedTarget.getHealth()) + "❤ | " +
                    String.format("%.1fm", totalDist) + ")" + headHint;
            } else {
                targetBadge = " §8| 激光测距: " + String.format("%.1fm", totalDist);
            }

            player.sendOverlayMessage(Component.literal(
                "§6[" + spec.zhName() + "] §e弹匣: " + ammo + "/" + spec.magazineSize() + " " +
                scopeBadge + targetBadge
            ));
        }
    }

    public static void applyScopeAttribute(ServerPlayer player, boolean scoped, float zoomLevel) {
        AttributeInstance speedAttr = player.getAttribute(Attributes.MOVEMENT_SPEED);
        if (speedAttr == null) return;
        if (scoped) {
            double amount = -Mth.clamp(0.15 + (zoomLevel / 18.0), 0.20, 0.65);
            speedAttr.addOrUpdateTransientModifier(new AttributeModifier(
                SCOPE_SPEED_MODIFIER_ID, amount, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL
            ));
        } else {
            if (speedAttr.hasModifier(SCOPE_SPEED_MODIFIER_ID)) {
                speedAttr.removeModifier(SCOPE_SPEED_MODIFIER_ID);
            }
        }
    }

    @Override
    public boolean isBarVisible(ItemStack stack) {
        return true;
    }

    @Override
    public int getBarWidth(ItemStack stack) {
        CompoundTag tag = getTag(stack);
        long reloadStart = tag.getLongOr("reloadStart", 0L);
        long reloadEnd = tag.getLongOr("reloadEnd", 0L);
        if (reloadEnd > reloadStart) {
            return 13;
        }
        int ammo = getAmmo(stack);
        return Math.round(13.0f * ammo / Math.max(1, spec.magazineSize()));
    }

    @Override
    public int getBarColor(ItemStack stack) {
        float ratio = (float) getAmmo(stack) / Math.max(1, spec.magazineSize());
        return Mth.hsvToRgb(Math.max(0.0F, ratio) / 3.0F, 1.0F, 1.0F);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, TooltipDisplay display, Consumer<Component> tooltipAdder, TooltipFlag flag) {
        int ammo = getAmmo(stack);
        String dmgStr = spec.pellets() > 1
            ? String.format("%.1f × %d弹丸 (满伤 %.1f)", spec.damage(), spec.pellets(), spec.damage() * spec.pellets())
            : String.format("%.1f (爆头 %.1fx = %.1f)", spec.damage(), spec.headshotMultiplier(), spec.damage() * spec.headshotMultiplier());

        tooltipAdder.accept(Component.literal("§7类型: §b" + spec.zhCategory() + " §8| §7弹匣: §e" + ammo + "/" + spec.magazineSize()));
        tooltipAdder.accept(Component.literal("§7单发伤害: §c" + dmgStr));
        tooltipAdder.accept(Component.literal(String.format("§7射速: §a%.1f 发/秒 §8(理论秒伤 %.0f) §8| §7有效射程: §f%.0fm", spec.shotsPerSecond(), spec.theoreticalDps(), spec.range())));
        tooltipAdder.accept(Component.literal(String.format("§7瞄准系统: §c激光红点瞄准器 §7+ §b%.1fx 光学变焦倍镜", spec.zoomLevel())));
        tooltipAdder.accept(Component.literal("§a✔ 安全弹道: 仅对生物实体产生伤害，绝不破坏世界方块"));
        tooltipAdder.accept(Component.literal("§8操作: [按住右键]射击 | [按住Shift或左键]开镜放大 | [F键]换弹"));
    }
}
