import { ToneData } from "./types";

export const BUCKET_LABELS: Record<string, string> = {
  today: "Today",
  week: "This Week",
  wait: "Can Wait",
};

export const STATUS_TAG_CLASS: Record<string, string> = {
  connected: "tag-accent",
  expiring: "tag-outline",
  reconnect: "tag-neutral",
};

export const STATUS_LABEL: Record<string, string> = {
  connected: "Connected",
  expiring: "Expires in 6 days",
  reconnect: "Reconnect needed",
};

export function toneData(): ToneData {
  return {
    e1: {
      shorter:
        "Priya — 4.2 works as redlined. On the board seat: observer rights for the first 12 months instead of a full seat. If your team can turn that around today, we're still on track to close this week. — Mara",
      warmer:
        "Priya — thanks so much for pushing this through so quickly, I know it's been a lot of back and forth. I'm fine with 4.2 as redlined. One ask on the board seat language: could we do observer rights for the first 12 months instead of a full seat? Totally understand if that needs another look — just let me know what your team needs from us today. — Mara",
      firmer:
        "Priya — 4.2 is approved as redlined. The board seat language needs to change to observer rights for the first 12 months, not a full seat. Please have your team turn this around today — we need it back to stay on track to close this week. — Mara",
    },
    e2: {
      shorter: "Hi all — please record my proxy in favor of the Q3 budget. I'd like a follow-up on the facilities line item next meeting.",
      warmer:
        "Hi all — sorry to miss today's session. Please record my proxy in favor of the Q3 budget as presented — thank you for handling this. I'd also love a quick follow-up on the facilities line item at the next meeting.",
      firmer:
        "Hi all — I cannot attend at 3pm. Record my proxy in favor of the Q3 budget as presented. Add the facilities line item to the next meeting's agenda.",
    },
    e3: {
      shorter: "Dev — let's find time next week, my assistant will follow up with slots.",
      warmer:
        "Dev — so great to hear from you! Let's absolutely find time next week — I'll have my assistant follow up with a few slots that work for both of us.",
      firmer: "Dev — my assistant will follow up with available slots next week.",
    },
    e4: {
      shorter: "No concerns from me. Happy to discuss Friday if needed.",
      warmer:
        "Thanks so much for putting this together — I've read through it and don't have any concerns. Happy to jump on Friday if anyone has questions!",
      firmer: "Reviewed — no concerns. I'll be on the Friday call if questions come up.",
    },
    e5: {
      shorter: "Noted, will renew soon.",
      warmer: "Thanks for the reminder — I'll take care of this soon, appreciate you flagging it!",
      firmer: "Noted. I'll renew this within the week.",
    },
    e6: {
      shorter: "Thanks for the update.",
      warmer: "Really nice update, thanks so much for putting this together!",
      firmer: "Thanks for the update — no action needed on my end.",
    },
    e7: {
      shorter: "Send me a few dates that work for the group and I'll coordinate.",
      warmer:
        "Happy to help find a new date — could you share a few options that work best for the group? I'll take it from there.",
      firmer: "Send the dates that work for the group by end of week — I'll finalize from there.",
    },
    e8: {
      shorter: "Sana — Thursday, 2pm ET works. Invite to follow. — Mara",
      warmer:
        "Sana — Thursday works great, so glad we found time! Let's do 2pm ET — I'll send the invite with dial-in shortly. Looking forward to catching up. — Mara",
      firmer: "Sana — Thursday, 2pm ET. I'll send the invite with dial-in details today. — Mara",
    },
  };
}
