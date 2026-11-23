"""i180 / i181 (2026-11-21, the user: "AH in the bottom screen should go ... we will be using WoW's own interface"; "we could use the
screen below just for typing in AH"). Under tools/wowstub.py with the real Interact.lua. Proves: the auction house is the game's own
window (no doc.auction, never hidden); its search box is lent to the Chat keyboard (WC.chatField "ahsearch") and Done writes the words
into the GAME'S box (SetText only, no search started by us); doc.ahinfo carries the box's text and your auctions, read only; a commodity
bought through the game's own calls is listed under "bought"; the field goes with the window.

    python -B tools/test_ah_game_window.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wowstub import boot_world, docs  # noqa: E402

fails = passes = 0


def check(ok, name, got=''):
    global fails, passes
    print(('PASS ' if ok else 'FAIL ') + name + ((' -> ' + str(got)) if got != '' and not ok else ''))
    if ok:
        passes += 1
    else:
        fails += 1


PRE = """
local A = {}
A.GetNumOwnedAuctions = function() return 1 end
A.GetOwnedAuctionInfo = function(i) return { itemKey = { itemID = 2589 }, quantity = 20, buyoutAmount = 5000, timeLeft = 2, status = 0 } end
A.GetItemKeyInfo = function(k) return { itemName = "Linen Cloth", quality = 1 } end
A.QueryOwnedAuctions = function() end
A.ConfirmCommoditiesPurchase = function() end
A.PlaceBid = function() end
ORIG_CONFIRM, ORIG_BID = A.ConfirmCommoditiesPurchase, A.PlaceBid
C_AuctionHouse = setmetatable(A, { __index = function() return function() end end })
"""
L, errs = boot_world(pre=PRE)
check(not [e for e in errs if e.startswith('interact')], "0: the world loads (interact)", errs)
L.execute('''
BOX = { text = "", SetText = function(self, t) self.text = t end, GetText = function(self) return self.text end }
SEARCHED = 0
AuctionHouseFrame = { SearchBar = { SearchBox = BOX, StartSearch = function() SEARCHED = SEARCHED + 1 end },
                      IsShown = function() return true end, Show = function() end, Hide = function() end }
rawset(C_Item, "GetItemNameByID", function(id) return "Copper Ore" end)
AH_T = { spec = false }
WowCompanion.chatField = { open = function(spec) AH_T.spec = spec; return true end, close = function() AH_T.spec = false end,
                           name = function() return AH_T.spec and AH_T.spec.name or nil end }
''')
L.execute('fire("AUCTION_HOUSE_SHOW"); runTimers(NOW + 1)')
d = [x for x in docs(L) if x.get('type') == 'interact']
last = d[-1] if d else {}
check(last.get('auction') is None, "1: no mirror document (the game's own window)", list(last.keys())[:12])
info = last.get('ahinfo') or {}
check(info.get('kbd') == 'ahsearch', "2: doc.ahinfo says the search box is lent to the keyboard", info)
check(info.get('owned') and info['owned'][0].get('name') == 'Linen Cloth' and info['owned'][0].get('n') == 20,
      "3: your auctions, read only", info.get('owned'))
ok = L.eval('AH_T.spec and AH_T.spec.done("linen")')
check(ok is True and L.eval('BOX.text') == 'linen', "4: Done writes the words into the game's search box", L.eval('BOX.text'))
check(L.eval('SEARCHED') == 0, "5: ... and starts no search itself (the player's own press does)", L.eval('SEARCHED'))
# i185: the game's buy calls are never hooked (a hook made OK do nothing on WoW Forever): still the very functions the game had
check(L.eval('rawequal(C_AuctionHouse.ConfirmCommoditiesPurchase, ORIG_CONFIRM) and rawequal(C_AuctionHouse.PlaceBid, ORIG_BID)') == True,
      "6a: C_AuctionHouse.ConfirmCommoditiesPurchase / PlaceBid are not hooked")
L.execute('AuctionHouseFrame.CommoditiesBuyFrame = { GetItemID = function() return 2770 end, GetQuantity = function() return 20 end }')
L.execute('fire("COMMODITY_PRICE_UPDATED", 12, 240); C_AuctionHouse.ConfirmCommoditiesPurchase(2770, 20); fire("COMMODITY_PURCHASE_SUCCEEDED"); runTimers(NOW + 2)')
d = [x for x in docs(L) if x.get('type') == 'interact']
b = ((d[-1] if d else {}).get('ahinfo') or {}).get('bought') or []
check(b and b[0].get('name') == 'Copper Ore' and b[0].get('n') == 20 and b[0].get('price') == 240, "6: a commodity bought is listed", b)
L.execute('AuctionHouseFrame.IsShown = function() return false end; fire("AUCTION_HOUSE_CLOSED"); runTimers(NOW + 3)')
check(L.eval('AH_T.spec == false'), "7: the field goes with the window", L.eval('tostring(AH_T.spec and AH_T.spec.name)'))

print("%d passed, %d failed" % (passes, fails))
sys.exit(1 if fails else 0)
