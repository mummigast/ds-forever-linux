"""THE ROLE INVITE ON THE BOTTOM SCREEN (WowCompanionInteract/Dialogs.lua d36; the user 2026-11-24: "i cannot accept party invites"),
off-device: Dialogs.lua alone under the stub game of test_quest_start.py (test_quit_exit_now.py's way).

    python tools/test_lfg_invite.py

The game (Blizzard_Game Mainline EventImplementation HandlePartyInviteRequest): an invite from a group with roles is LFGInvitePopup
(StaticPopupSpecial_Show), not the StaticPopup PARTY_INVITE; its Accept (LFGInvitePopupAcceptButton) stays disabled until a role check box
is ticked. Checks: the popup is mirrored (which LFG_INVITE) with Accept / Decline on the guild invite's two cells; with no role ticked the
add-on ticks the current spec's role (once: a role the player changes stays); the controller is held with A / B as binding clicks aimed at
the game's own Accept / Decline; the shared cells are aimed at the popup's buttons; hidden popup = gone from the document. Needs lupa."""
import sys

import lupa

from test_quest_start import STUB, SRC
from test_quit_exit_now import POPUPS

TEST = r'''
local out = {}
local function chk(n, c) out[#out + 1] = (c and "PASS " or "FAIL ") .. n end
FIRE("PLAYER_LOGIN")
FIRE("PLAYER_ENTERING_WORLD", true, false)
SPEC_ROLE = "HEALER"
function GetSpecialization() return 2 end
function GetSpecializationRole() return SPEC_ROLE end
local function role(name)
    local rb = CreateFrame("Button", name)
    local cb = CreateFrame("CheckButton", nil)
    cb.checked = false
    cb.GetChecked = function(self) return self.checked end
    cb.SetChecked = function(self, v) self.checked = v and true or false end
    rb.checkButton = cb
    return rb
end
local p = CreateFrame("Frame", "LFGInvitePopup")
p.shown, p.timeOut = false, 120
LFGInvitePopupText = { GetText = function() return "Somebody has invited you to join a group." end }
local acc = CreateFrame("Button", "LFGInvitePopupAcceptButton"); acc.GetText = function() return "Accept" end
local dec = CreateFrame("Button", "LFGInvitePopupDeclineButton"); dec.GetText = function() return "Decline" end
acc.enabled = false
acc.IsEnabled = function(self) return self.enabled end
local t, h, d = role("LFGInvitePopupRoleButtonTank"), role("LFGInvitePopupRoleButtonHealer"), role("LFGInvitePopupRoleButtonDPS")
function LFGInvitePopup_UpdateAcceptButton() acc.enabled = t.checkButton.checked or h.checkButton.checked or d.checkButton.checked end
-- the invite comes
p.shown = true
FIRE("PARTY_INVITE_REQUEST", "Somebody", true, true, true)
local doc = DOC()
local x = doc and FIND(doc, "LFG_INVITE")
chk("the role invite is mirrored", x ~= nil)
chk("no role was ticked: the spec's role (Healer) is ticked, Accept enabled", h.checkButton.checked and not t.checkButton.checked
    and not d.checkButton.checked and acc.enabled == true)
local a, b = x and BTN(x, 1), x and BTN(x, 2)
chk("Accept names the role and is on; Decline shown", a ~= nil and a.on == true and a.label == "Accept as Healer" and b ~= nil)
chk("A / B held by the dialogs, aimed at the game's Accept / Decline",
    CAP.holder == "dialogs" and _G.WowCompanionDlgA and _G.WowCompanionDlgA.attr.clickbutton == acc
    and _G.WowCompanionDlgB.attr.clickbutton == dec)
chk("the mirror carries cells for both buttons", x ~= nil and x.cells ~= nil and x.cells.b1 ~= nil and x.cells.b2 == x.cells.b1 + 1)
-- the player changes the role on the top screen: it stays
h.checkButton.checked, d.checkButton.checked = false, true
doc = DOC(); x = doc and FIND(doc, "LFG_INVITE")
chk("a role the player picks stays (not ticked again)", d.checkButton.checked and not h.checkButton.checked
    and x ~= nil and BTN(x, 1).label == "Accept as Damage")
-- accepted: the popup hides
p.shown = false
doc = DOC()
chk("hidden: gone from the document", doc ~= nil and FIND(doc, "LFG_INVITE") == nil)
-- a second invite, nothing ticked, no spec role: Damage
t.checkButton.checked, h.checkButton.checked, d.checkButton.checked = false, false, false
SPEC_ROLE = nil
p.shown = true
FIRE("PARTY_INVITE_REQUEST", "Other", true, true, true)
DOC()
chk("no spec role: Damage ticked", d.checkButton.checked and not t.checkButton.checked and not h.checkButton.checked)
p.shown = false
DOC()
-- d38: THE BATTLEGROUND ENTRY (PVPReadyDialog: Enter Battle / Leave Queue, no roles)
local pv = CreateFrame("Frame", "PVPReadyDialog"); pv.shown = false
pv.label = { GetText = function() return "Your battle is ready!" end, IsShown = function() return true end }
pv.statusText = { GetText = function() return "Capture the bases" end, IsShown = function() return true end }
PVPReadyDialogInstanceInfoFrameName = { GetText = function() return "Arathi Basin" end, IsShown = function() return true end }
local ent = CreateFrame("Button", "PVPReadyDialogEnterBattleButton"); ent.GetText = function() return "Enter Battle" end
local lv = CreateFrame("Button", "PVPReadyDialogLeaveQueueButton"); lv.GetText = function() return "Leave Queue" end
pv.shown = true
FIRE("UPDATE_BATTLEFIELD_STATUS", 1)
doc = DOC(); x = doc and FIND(doc, "PVP_READY")
chk("battleground entry mirrored with its words", x ~= nil and x.text ~= nil and x.text:find("Arathi Basin", 1, true) ~= nil)
chk("Enter Battle / Leave Queue on the shared cells", x ~= nil and BTN(x, 1).label == "Enter Battle" and BTN(x, 2).label == "Leave Queue"
    and x.cells and x.cells.b1 ~= nil)
chk("A / B aimed at Enter Battle / Leave Queue", _G.WowCompanionDlgA.attr.clickbutton == ent and _G.WowCompanionDlgB.attr.clickbutton == lv)
pv.shown = false
doc = DOC()
chk("entered: gone", FIND(doc, "PVP_READY") == nil)
-- d38: A DUNGEON ROLE CHECK (LFDRoleCheckPopup: roles + its own update function)
local rc = CreateFrame("Frame", "LFDRoleCheckPopup"); rc.shown = false
rc.Text = { GetText = function() return "Confirm your role:" end }
local ra = CreateFrame("Button", "LFDRoleCheckPopupAcceptButton"); ra.GetText = function() return "Accept" end
ra.enabled = false; ra.IsEnabled = function(self) return self.enabled end
CreateFrame("Button", "LFDRoleCheckPopupDeclineButton").GetText = function() return "Decline" end
local rt, rh, rd = role("LFDRoleCheckPopupRoleButtonTank"), role("LFDRoleCheckPopupRoleButtonHealer"), role("LFDRoleCheckPopupRoleButtonDPS")
function LFDRoleCheckPopup_UpdateAcceptButton() ra.enabled = rt.checkButton.checked or rh.checkButton.checked or rd.checkButton.checked end
SPEC_ROLE = "TANK"
rc.shown = true
FIRE("LFG_ROLE_CHECK_SHOW")
doc = DOC(); x = doc and FIND(doc, "LFD_ROLECHECK")
chk("dungeon role check: Tank (the spec's) ticked, Accept as Tank and on", rt.checkButton.checked and x ~= nil
    and BTN(x, 1).label == "Accept as Tank" and BTN(x, 1).on == true)
rc.shown = false
DOC()
-- d39: THE MATCH RESULTS (PVPMatchResults: leaveButton / requeueButton, no words of its own)
local mr = CreateFrame("Frame", "PVPMatchResults"); mr.shown = false
mr.leaveButton = CreateFrame("Button"); mr.leaveButton.GetText = function() return "Leave Battle" end
mr.requeueButton = CreateFrame("Button"); mr.requeueButton.GetText = function() return "Requeue" end
mr.shown = true
FIRE("PVP_MATCH_COMPLETE")
doc = DOC(); x = doc and FIND(doc, "PVP_RESULTS")
chk("match results mirrored: Leave Battle (A) / Requeue, with words", x ~= nil and BTN(x, 1).label == "Leave Battle"
    and BTN(x, 2).label == "Requeue" and x.text == "The battle is over." and _G.WowCompanionDlgA.attr.clickbutton == mr.leaveButton)
mr.shown = false
DOC()
return table.concat(out, "\n")
'''


def main():
    L = lupa.LuaRuntime()
    L.execute(STUB)
    L.execute(POPUPS)
    L.execute(open(SRC, encoding='utf-8').read())
    res = str(L.execute(TEST))
    print(res)
    fails = res.count("FAIL ")
    print("failed: %d" % fails)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
