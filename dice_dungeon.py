#!/usr/bin/env python3
"""骰子地下城 - Roguelike 賭博地下城"""
import random
import os
import sys
import time


class C:
    R = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[93m"
    BLU = "\033[94m"
    MAG = "\033[95m"
    CYN = "\033[96m"
    BLD = "\033[1m"
    DIM = "\033[2m"


def cls():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def pause(msg="(按 Enter 繼續)"):
    input(f"{C.DIM}{msg}{C.R}")


def choose(prompt, options):
    while True:
        print(prompt)
        for k, label in options:
            print(f"  [{C.YLW}{k}{C.R}] {label}")
        ch = input(f"{C.CYN}>{C.R} ").strip().lower()
        for k, _ in options:
            if ch == k.lower():
                return k
        print(f"{C.RED}無效選擇{C.R}")


DICE_FACES = {
    1: ["+-----+", "|     |", "|  o  |", "|     |", "+-----+"],
    2: ["+-----+", "| o   |", "|     |", "|   o |", "+-----+"],
    3: ["+-----+", "| o   |", "|  o  |", "|   o |", "+-----+"],
    4: ["+-----+", "| o o |", "|     |", "| o o |", "+-----+"],
    5: ["+-----+", "| o o |", "|  o  |", "| o o |", "+-----+"],
    6: ["+-----+", "| o o |", "| o o |", "| o o |", "+-----+"],
}


def render_dice(values):
    rows = ["", "", "", "", ""]
    for v in values:
        if 1 <= v <= 6:
            face = DICE_FACES[v]
        else:
            face = ["+-----+", "|     |", f"| {v:^3} |", "|     |", "+-----+"]
        for i, line in enumerate(face):
            rows[i] += line + " "
    return "\n".join(C.CYN + r + C.R for r in rows)


class Die:
    def __init__(self, sides=6, name="d6"):
        self.sides = sides
        self.name = name

    def roll(self):
        return random.randint(1, self.sides)

    def __repr__(self):
        return self.name


class Relic:
    def __init__(self, name, desc, price, tag):
        self.name = name
        self.desc = desc
        self.price = price
        self.tag = tag


ALL_RELICS = [
    Relic("幸運硬幣", "所有骰子點數+1", 22, "lucky"),
    Relic("吸血獠牙", "攻擊時回1HP", 20, "vampire"),
    Relic("黃金磁鐵", "獲得金幣+50%", 24, "magnet"),
    Relic("作弊骰子", "最低點數變3", 28, "loaded"),
    Relic("玻璃大砲", "傷害+4 但HP上限-4", 18, "glass"),
    Relic("賭徒之心", "賭場贏取翻倍", 25, "gambler"),
    Relic("鳳凰之羽", "死亡時復活一次", 45, "phoenix"),
    Relic("雙重擲骰", "戰鬥擲兩次取較高", 32, "double"),
    Relic("死神鐮刀", "敵人HP低於25%即斬殺", 30, "scythe"),
    Relic("時光沙漏", "戰鬥勝利回3HP", 20, "hourglass"),
]


class Player:
    def __init__(self):
        self.max_hp = 22
        self.hp = 22
        self.gold = 18
        self.dice = [Die(6), Die(6)]
        self.relics = []
        self.floor = 1
        self.kills = 0

    def has(self, tag):
        return any(r.tag == tag for r in self.relics)

    def add_relic(self, relic):
        self.relics.append(relic)
        if relic.tag == "glass":
            self.max_hp -= 4
            self.hp = min(self.hp, self.max_hp)

    def _single_attack(self):
        rolls = []
        for d in self.dice:
            r = d.roll()
            if self.has("lucky"):
                r += 1
            if self.has("loaded") and r < 3:
                r = 3
            rolls.append(r)
        return rolls

    def attack(self):
        rolls = self._single_attack()
        if self.has("double"):
            second = self._single_attack()
            if sum(second) > sum(rolls):
                rolls = second
        total = sum(rolls)
        if self.has("glass"):
            total += 4
        return rolls, total

    def gain_gold(self, amt):
        if self.has("magnet"):
            amt = int(amt * 1.5)
        self.gold += amt
        return amt

    def hurt(self, dmg):
        self.hp -= dmg
        if self.hp <= 0 and self.has("phoenix"):
            self.relics = [r for r in self.relics if r.tag != "phoenix"]
            self.hp = max(self.max_hp // 2, 1)
            return "phoenix"
        return "ok" if self.hp > 0 else "dead"

    def heal(self, amt):
        self.hp = min(self.max_hp, self.hp + amt)


def status(p):
    if p.hp > p.max_hp * 0.6:
        hpc = C.GRN
    elif p.hp > p.max_hp * 0.3:
        hpc = C.YLW
    else:
        hpc = C.RED
    bar = "=" * 60
    print(f"{C.BLD}{bar}{C.R}")
    dice_str = ",".join(d.name for d in p.dice)
    print(
        f"  樓層 {C.MAG}{p.floor}/10{C.R}  "
        f"HP {hpc}{p.hp}/{p.max_hp}{C.R}  "
        f"金幣 {C.YLW}{p.gold}{C.R}  "
        f"骰子 {C.CYN}{dice_str}{C.R}"
    )
    if p.relics:
        rs = " ".join(f"{C.MAG}[{r.name}]{C.R}" for r in p.relics)
        print(f"  寶物 {rs}")
    print(f"{C.BLD}{bar}{C.R}")


# (name, hp, atk, gold)
ENEMIES = [
    ("史萊姆", 9, 3, 6),
    ("哥布林", 13, 4, 8),
    ("骷髏兵", 16, 5, 10),
    ("惡魔狗", 20, 6, 12),
    ("石像鬼", 26, 8, 16),
    ("巫妖", 32, 10, 20),
    ("骨龍", 40, 11, 24),
]

BOSSES = {
    5: ("骰子魔王", 55, 9, 60),
    10: ("命運主宰", 90, 13, 150),
}


class Enemy:
    def __init__(self, name, hp, atk, gold):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.atk = atk
        self.gold = gold


def combat(player, enemy, is_boss=False):
    icon = "[BOSS]" if is_boss else "[戰鬥]"
    color = C.MAG if is_boss else C.RED
    print(f"\n{color}{icon} 遭遇 {C.BLD}{enemy.name}{C.R}{color}!{C.R}")
    print(f"  HP {enemy.hp}  攻擊 {enemy.atk}\n")
    pause()

    while True:
        cls()
        status(player)
        eb_full = 30
        eb_now = max(0, int(eb_full * enemy.hp / enemy.max_hp))
        bar = C.RED + "#" * eb_now + C.DIM + "-" * (eb_full - eb_now) + C.R
        print(f"\n{color}{enemy.name}{C.R} HP {enemy.hp}/{enemy.max_hp}")
        print(f"  [{bar}]")

        ch = choose(
            "\n你的回合:",
            [
                ("a", "攻擊（擲骰）"),
                ("d", "防禦（傷害減半）"),
                ("g", f"全押賭博（押 5 金幣，1d6 倍傷害 / 失敗扣 5 金幣）"),
                ("r", "逃跑（損失一半金幣）"),
            ],
        )

        if ch == "a":
            rolls, total = player.attack()
            print(render_dice(rolls))
            print(f"{C.YLW}傷害 {total}{C.R}")
            enemy.hp -= total
            if player.has("scythe") and enemy.hp > 0 and enemy.hp <= enemy.max_hp * 0.25:
                print(f"{C.MAG}+ 死神鐮刀斬殺!{C.R}")
                enemy.hp = 0
            if player.has("vampire"):
                player.heal(1)
                print(f"{C.GRN}+ 吸血獠牙：回1HP{C.R}")
            if enemy.hp <= 0:
                _victory(player, enemy)
                return True
            time.sleep(0.4)
            print(f"\n{color}{enemy.name} 反擊！{C.R}")
            res = player.hurt(enemy.atk)
            print(f"{C.RED}受到 {enemy.atk} 傷害{C.R}")
            if res == "phoenix":
                print(f"{C.MAG}+++ 鳳凰之羽觸發！復活！{C.R}")
            elif res == "dead":
                return False
            pause()

        elif ch == "d":
            time.sleep(0.3)
            dmg = max(1, enemy.atk // 2)
            res = player.hurt(dmg)
            print(f"{C.BLU}你採取防禦姿態。受到 {dmg} 傷害{C.R}")
            if res == "phoenix":
                print(f"{C.MAG}+++ 鳳凰之羽觸發！{C.R}")
            elif res == "dead":
                return False
            pause()

        elif ch == "g":
            if player.gold < 5:
                print(f"{C.RED}金幣不足{C.R}")
                pause()
                continue
            player.gold -= 5
            mult = random.randint(1, 6)
            rolls, total = player.attack()
            print(render_dice(rolls))
            final = total * mult
            print(f"{C.MAG}基礎傷害 {total} x 賭博倍率 {mult} = {final}{C.R}")
            enemy.hp -= final
            if enemy.hp <= 0:
                _victory(player, enemy)
                return True
            time.sleep(0.4)
            print(f"\n{color}{enemy.name} 反擊！{C.R}")
            res = player.hurt(enemy.atk)
            print(f"{C.RED}受到 {enemy.atk} 傷害{C.R}")
            if res == "phoenix":
                print(f"{C.MAG}+++ 鳳凰之羽觸發！{C.R}")
            elif res == "dead":
                return False
            pause()

        elif ch == "r":
            if is_boss:
                print(f"{C.RED}BOSS 戰無法逃跑！{C.R}")
                pause()
                continue
            lost = player.gold // 2
            player.gold -= lost
            print(f"{C.DIM}你逃跑了，失去 {lost} 金幣{C.R}")
            pause()
            return True


def _victory(player, enemy):
    print(f"\n{C.GRN}*** 擊敗 {enemy.name}! ***{C.R}")
    g = player.gain_gold(enemy.gold)
    print(f"{C.YLW}獲得 {g} 金幣{C.R}")
    player.kills += 1
    if player.has("hourglass"):
        player.heal(3)
        print(f"{C.GRN}+ 時光沙漏：回3HP{C.R}")
    pause()


def slot_machine(player):
    cls()
    status(player)
    print(f"\n{C.MAG}>> 拉霸機 <<{C.R}")
    print("規則：押 6 金幣")
    print(f"  3個一樣  -> 賠 30 倍 (180金)")
    print(f"  2個相同  -> 回本+5  (11金)")
    print(f"  全不同   -> 損失押注")
    if player.gold < 6:
        print(f"{C.RED}金幣不足{C.R}")
        pause()
        return
    if choose("", [("y", "押 6 金幣"), ("n", "離開")]) == "n":
        return
    player.gold -= 6
    syms = ["[7]", "[$]", "[*]", "[#]", "[!]"]
    final = [random.choice(syms) for _ in range(3)]
    for _ in range(8):
        print(
            f"\r {random.choice(syms)} | {random.choice(syms)} | {random.choice(syms)}  ",
            end="",
        )
        sys.stdout.flush()
        time.sleep(0.12)
    print(f"\r {final[0]} | {final[1]} | {final[2]}      ")
    a, b, c = final
    if a == b == c:
        win = 180
        if player.has("gambler"):
            win *= 2
        print(f"{C.GRN}!!! 三連線 !!! 贏得 {win} 金幣！{C.R}")
        player.gain_gold(win)
    elif a == b or b == c or a == c:
        win = 11
        if player.has("gambler"):
            win *= 2
        print(f"{C.YLW}兩個相同，贏得 {win} 金幣{C.R}")
        player.gain_gold(win)
    else:
        print(f"{C.RED}沒中... 損失 6 金幣{C.R}")
    pause()


def coin_flip(player):
    cls()
    status(player)
    print(f"\n{C.MAG}>> 硬幣賭局 <<{C.R}")
    print("猜對：押注翻倍 / 猜錯：歸零")
    if player.gold <= 0:
        print(f"{C.RED}沒金幣{C.R}")
        pause()
        return
    raw = input(f"押多少？(1-{player.gold}): ").strip()
    try:
        bet = int(raw)
    except ValueError:
        return
    if bet <= 0 or bet > player.gold:
        return
    side = choose("選擇:", [("h", "正面"), ("t", "反面")])
    print(f"\n{C.DIM}硬幣旋轉中...{C.R}")
    time.sleep(0.6)
    res = random.choice(["h", "t"])
    print(f"結果是: {C.BLD}{'正面' if res == 'h' else '反面'}{C.R}")
    if side == res:
        win = bet
        if player.has("gambler"):
            win *= 2
        player.gain_gold(win)
        print(f"{C.GRN}贏 {win} 金幣！{C.R}")
    else:
        player.gold -= bet
        print(f"{C.RED}輸 {bet} 金幣{C.R}")
    pause()


def roulette(player):
    cls()
    status(player)
    print(f"\n{C.RED}>> 俄羅斯輪盤 <<{C.R}")
    print("六發彈倉，一發實彈。中彈損 9 HP。")
    rewards = [0, 15, 38, 65, 100, 150]
    print(f"撐 1/2/3/4/5 輪可拿 {rewards[1:]} 金幣")
    if choose("", [("y", "玩"), ("n", "走")]) == "n":
        return
    bullet = random.randint(1, 6)
    pulls = 0
    while True:
        pulls += 1
        time.sleep(0.4)
        if pulls == bullet:
            print(f"\n{C.RED}!!! BANG !!! 中彈！{C.R}")
            res = player.hurt(9)
            if res == "phoenix":
                print(f"{C.MAG}鳳凰之羽觸發！{C.R}")
            pause()
            return res != "dead"
        print(f"{C.GRN}*click* 沒事 ({pulls}/6){C.R}")
        if pulls >= 5:
            r = rewards[5]
            if player.has("gambler"):
                r *= 2
            player.gain_gold(r)
            print(f"{C.YLW}撐過 5 輪！獲得 {r} 金幣{C.R}")
            pause()
            return True
        nxt = rewards[pulls + 1]
        cur = rewards[pulls]
        if choose(
            f"目前可拿 {cur} 金幣",
            [("y", f"再來一輪 (下輪 {nxt})"), ("n", f"拿錢走 (+{cur})")],
        ) == "n":
            r = cur
            if player.has("gambler"):
                r *= 2
            player.gain_gold(r)
            print(f"{C.YLW}帶著 {r} 金幣離開{C.R}")
            pause()
            return True
    return True


def gamble_room(player):
    while True:
        cls()
        status(player)
        print(f"\n{C.MAG}>>> 賭  場 <<<{C.R}")
        ch = choose(
            "選擇遊戲：",
            [
                ("s", "拉霸機 (押6金)"),
                ("c", "硬幣賭局"),
                ("r", "俄羅斯輪盤"),
                ("x", "離開"),
            ],
        )
        if ch == "s":
            slot_machine(player)
        elif ch == "c":
            coin_flip(player)
        elif ch == "r":
            ok = roulette(player)
            if not ok:
                return False
        elif ch == "x":
            return True


def shop(player):
    available_relic = None
    available = [r for r in ALL_RELICS if not player.has(r.tag)]
    if available:
        available_relic = random.choice(available)

    bought = set()
    while True:
        cls()
        status(player)
        print(f"\n{C.YLW}>>> 商  店 <<<{C.R}")
        items = []
        if "h" not in bought:
            items.append(("h", "治療 6HP", 8, "heal"))
        if "H" not in bought:
            items.append(("H", "全滿治療", 22, "fullheal"))
        if "d" not in bought:
            items.append(("d", "新增 d6 骰子", 28, "die"))
        if "u" not in bought:
            items.append(("u", "升級 d6 -> d8", 24, "upgrade"))
        if "U" not in bought:
            items.append(("U", "升級 d8 -> d10", 38, "upgrade2"))
        if "m" not in bought:
            items.append(("m", "+4 最大HP", 14, "maxhp"))
        if available_relic and "r" not in bought:
            items.append(
                ("r", f"寶物：{available_relic.name}（{available_relic.desc}）",
                 available_relic.price, "relic")
            )
        items.append(("x", "離開", 0, "exit"))

        for k, label, price, _ in items:
            if price == 0:
                print(f"  [{C.YLW}{k}{C.R}] {label}")
            else:
                col = C.GRN if player.gold >= price else C.DIM
                print(f"  [{C.YLW}{k}{C.R}] {col}{label} - {price}金{C.R}")

        ch = input(f"{C.CYN}>{C.R} ").strip()
        item = next((i for i in items if i[0] == ch), None)
        if not item:
            continue
        k, label, price, action = item
        if action == "exit":
            return
        if player.gold < price:
            print(f"{C.RED}金幣不足{C.R}")
            pause()
            continue

        if action == "heal":
            player.gold -= price
            player.heal(6)
            bought.add(k)
            print(f"{C.GRN}回6HP{C.R}")
        elif action == "fullheal":
            player.gold -= price
            player.hp = player.max_hp
            bought.add(k)
            print(f"{C.GRN}HP全滿{C.R}")
        elif action == "die":
            player.gold -= price
            player.dice.append(Die(6))
            bought.add(k)
            print(f"{C.GRN}+1顆 d6{C.R}")
        elif action == "upgrade":
            d6 = next((d for d in player.dice if d.sides == 6), None)
            if not d6:
                print(f"{C.RED}沒有 d6 可升級{C.R}")
            else:
                player.gold -= price
                d6.sides = 8
                d6.name = "d8"
                bought.add(k)
                print(f"{C.GRN}d6 -> d8{C.R}")
        elif action == "upgrade2":
            d8 = next((d for d in player.dice if d.sides == 8), None)
            if not d8:
                print(f"{C.RED}沒有 d8 可升級{C.R}")
            else:
                player.gold -= price
                d8.sides = 10
                d8.name = "d10"
                bought.add(k)
                print(f"{C.GRN}d8 -> d10{C.R}")
        elif action == "maxhp":
            player.gold -= price
            player.max_hp += 4
            player.hp += 4
            bought.add(k)
            print(f"{C.GRN}最大HP +4{C.R}")
        elif action == "relic":
            player.gold -= price
            player.add_relic(available_relic)
            bought.add(k)
            print(f"{C.MAG}獲得寶物：{available_relic.name}！{C.R}")
            available_relic = None
        pause()


def treasure(player):
    cls()
    status(player)
    print(f"\n{C.YLW}>>> 你發現一個寶箱 <<<{C.R}")
    pause("(按 Enter 開啟)")
    roll = random.random()
    if roll < 0.35:
        g = random.randint(20, 40)
        got = player.gain_gold(g)
        print(f"{C.YLW}金幣 +{got}{C.R}")
    elif roll < 0.6:
        player.heal(10)
        print(f"{C.GRN}回復 10 HP{C.R}")
    elif roll < 0.85:
        avail = [r for r in ALL_RELICS if not player.has(r.tag)]
        if avail:
            r = random.choice(avail)
            player.add_relic(r)
            print(f"{C.MAG}獲得寶物：{r.name} - {r.desc}{C.R}")
        else:
            got = player.gain_gold(40)
            print(f"{C.YLW}寶物已收集滿，金幣 +{got}{C.R}")
    else:
        player.dice.append(Die(6))
        print(f"{C.CYN}獲得新骰子 d6！{C.R}")
    pause()


def event(player):
    cls()
    status(player)
    print(f"\n{C.BLU}>>> 神祕事件 <<<{C.R}")
    e = random.choice(["fountain", "cursed", "merchant", "shrine"])
    if e == "fountain":
        print("你發現一座生命之泉。")
        if choose("", [("y", "飲水（回滿HP，但失去 5 金幣）"), ("n", "離開")]) == "y":
            if player.gold >= 5:
                player.gold -= 5
                player.hp = player.max_hp
                print(f"{C.GRN}HP全滿{C.R}")
            else:
                print(f"{C.RED}金幣不足{C.R}")
    elif e == "cursed":
        print("一個詛咒祭壇散發黑霧。")
        print("獻祭 5HP 換取 30 金幣？")
        if choose("", [("y", "獻祭"), ("n", "離開")]) == "y":
            if player.hp > 5:
                player.hp -= 5
                got = player.gain_gold(30)
                print(f"{C.MAG}失去5HP，獲得 {got} 金幣{C.R}")
            else:
                print(f"{C.RED}HP不足{C.R}")
    elif e == "merchant":
        print("流浪商人提供秘密交易。")
        print("8 金幣換一顆 d6 骰子？")
        if choose("", [("y", "買"), ("n", "離開")]) == "y":
            if player.gold >= 8:
                player.gold -= 8
                player.dice.append(Die(6))
                print(f"{C.CYN}+1 顆 d6！{C.R}")
            else:
                print(f"{C.RED}金幣不足{C.R}")
    elif e == "shrine":
        print("命運神龕：擲一顆骰子決定獎勵。")
        if choose("", [("y", "祈禱"), ("n", "離開")]) == "y":
            r = random.randint(1, 6)
            print(render_dice([r]))
            if r == 1:
                player.hurt(3)
                print(f"{C.RED}神龕大怒！受3傷害{C.R}")
            elif r <= 3:
                got = player.gain_gold(15)
                print(f"{C.YLW}金幣 +{got}{C.R}")
            elif r <= 5:
                player.heal(10)
                print(f"{C.GRN}回10HP{C.R}")
            else:
                avail = [x for x in ALL_RELICS if not player.has(x.tag)]
                if avail:
                    rel = random.choice(avail)
                    player.add_relic(rel)
                    print(f"{C.MAG}獲得寶物：{rel.name}！{C.R}")
                else:
                    got = player.gain_gold(40)
                    print(f"{C.YLW}金幣 +{got}{C.R}")
    pause()


def make_enemy(floor):
    idx = min(len(ENEMIES) - 1, (floor - 1) // 2)
    name, hp, atk, gold = ENEMIES[idx]
    scale = 1 + (floor - 1) * 0.07
    return Enemy(name, int(hp * scale), int(atk * scale + 0.5), int(gold * scale))


def floor_choice(player):
    """Let player pick a room type"""
    cls()
    status(player)
    print(f"\n{C.CYN}>>> 樓層 {player.floor} - 選擇路線 <<<{C.R}\n")

    if player.floor in BOSSES:
        name, hp, atk, gold = BOSSES[player.floor]
        boss = Enemy(name, hp, atk, gold)
        print(f"{C.MAG}前方是 BOSS：{boss.name}！別無選擇。{C.R}")
        pause()
        return combat(player, boss, is_boss=True)

    pool = ["combat", "combat", "shop", "gamble", "treasure", "event"]
    a, b, c = random.sample(pool, 3)
    icons = {
        "combat": (C.RED, "[戰鬥]", "與怪物戰鬥"),
        "shop": (C.YLW, "[商店]", "購買升級"),
        "gamble": (C.MAG, "[賭場]", "拉霸/輪盤/硬幣"),
        "treasure": (C.YLW, "[寶箱]", "隨機獎勵"),
        "event": (C.BLU, "[事件]", "神秘事件"),
    }
    options = []
    for k, t in zip(["1", "2", "3"], [a, b, c]):
        col, ic, desc = icons[t]
        options.append((k, f"{col}{ic}{C.R} {desc}"))
    ch = choose("", options)
    chosen = {"1": a, "2": b, "3": c}[ch]

    if chosen == "combat":
        enemy = make_enemy(player.floor)
        return combat(player, enemy)
    elif chosen == "shop":
        shop(player)
        return True
    elif chosen == "gamble":
        return gamble_room(player)
    elif chosen == "treasure":
        treasure(player)
        return True
    elif chosen == "event":
        event(player)
        return True


def title():
    cls()
    print(C.MAG + r"""
  +============================================+
  |                                            |
  |     [ ]  骰  子  地  下  城  [ ]           |
  |                                            |
  |       Roguelike  Gambling  Dungeon         |
  |                                            |
  +============================================+
""" + C.R)
    print(f"{C.DIM}擲骰子、賭一把、闖蕩 10 層地下城...{C.R}\n")
    print(f"{C.YLW}玩法：{C.R}")
    print("  - 戰鬥：擲骰累計傷害，可賭博放大倍率")
    print("  - 商店：買骰子、升級點數、寶物、回HP")
    print("  - 賭場：拉霸、硬幣、俄羅斯輪盤")
    print("  - 寶箱/事件：隨機驚喜或陷阱")
    print("  - 5/10 樓有 BOSS")
    print()
    pause("(Enter 開始)")


def game_over(player, won):
    cls()
    if won:
        print(C.GRN + r"""
  +============================================+
  |                                            |
  |    *** 你 征 服 了 命 運 主 宰 ! ***        |
  |                                            |
  +============================================+
""" + C.R)
    else:
        print(C.RED + r"""
  +============================================+
  |                                            |
  |          [X]  G A M E   O V E R  [X]       |
  |                                            |
  +============================================+
""" + C.R)
    print(f"  最終樓層 : {player.floor}")
    print(f"  擊殺數   : {player.kills}")
    print(f"  剩餘金幣 : {player.gold}")
    print(f"  骰子數量 : {len(player.dice)} ({','.join(d.name for d in player.dice)})")
    print(f"  寶物數   : {len(player.relics)}")
    print()


def main():
    title()
    p = Player()
    won = False
    while True:
        result = floor_choice(p)
        if result is False:
            break
        p.floor += 1
        if p.floor > 10:
            won = True
            break
    game_over(p, won)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n\n{C.DIM}遊戲結束。再見！{C.R}")
