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
