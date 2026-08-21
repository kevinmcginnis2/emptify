import { Account, EmailThread, ToneData, VoiceState } from "./types";

export const ACCOUNT_LABELS: Record<string, string> = {
  kestrel: "Kestrel Partners",
  northwind: "Northwind Health",
  personal: "Personal Gmail",
};

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

export function initialAccounts(): Account[] {
  return [
    {
      id: "kestrel",
      name: "Kestrel Partners",
      type: "Work",
      email: "mara@kestrelpartners.com",
      status: "connected",
      lastSync: "2 minutes ago",
      internalDomains: "kestrelpartners.com",
    },
    {
      id: "northwind",
      name: "Northwind Health",
      type: "Work · Board seat",
      email: "mara.lindqvist@northwindhealth.org",
      status: "expiring",
      lastSync: "14 minutes ago",
      internalDomains: "northwindhealth.org",
    },
    {
      id: "personal",
      name: "Personal Gmail",
      type: "Personal",
      email: "mara.lindqvist@gmail.com",
      status: "reconnect",
      lastSync: "3 days ago",
      internalDomains: "",
    },
  ];
}

export function initialEmails(): EmailThread[] {
  return [
    {
      id: "e1",
      account: "kestrel",
      accountLabel: "Kestrel Partners",
      accountEmail: "mara@kestrelpartners.com",
      from: "Priya Ementhal",
      fromEmail: "priya@harborview-capital.com",
      subject: "Term sheet redline — need this back today",
      bucket: "today",
      reason: "Counterparty needs the signed redline by 5pm today.",
      voiceMode: "client",
      voiceWhy:
        "Matched to client voice — short paragraphs, no opening small talk, sign-off with first name only.",
      messages: [
        {
          from: "Priya Ementhal",
          at: "Today, 8:42 AM",
          body: "Mara — following up on the term sheet. Legal sent back a redline on the liquidation preference (section 4.2) and the board seat language. Can you look this over and confirm you're good, or flag what needs to change? We're hoping to close this week, so today would help a lot. — Priya",
        },
      ],
      draft:
        "Priya — thanks for the quick turnaround. I've looked at 4.2 and I'm fine with the liquidation preference as redlined. On the board seat language, I'd like one small change: observer rights instead of a full seat for the first 12 months. Can your team turn that around today so we can stay on track to close this week? — Mara",
      draftAuthor: "emptify",
      versionStack: [],
      handoffSuggested: false,
      handoffReason: "",
      status: "board",
      eaNote: "",
      eaChangeSummary: "",
      draftAtHandoff: "",
    },
    {
      id: "e2",
      account: "northwind",
      accountLabel: "Northwind Health",
      accountEmail: "mara.lindqvist@northwindhealth.org",
      from: "Board Secretary",
      fromEmail: "secretary@northwindhealth.org",
      subject: "Proxy needed before 3pm vote",
      bucket: "today",
      reason: "Board votes on the Q3 budget at 3pm today; proxy due by 1pm if absent.",
      voiceMode: "internal",
      voiceWhy: "Matched to internal voice — opens with a greeting to the group, slightly more procedural.",
      messages: [
        {
          from: "Board Secretary",
          at: "Today, 9:10 AM",
          body: "Mara — reminder that the board is voting on the Q3 budget at 3pm today. If you can't join, we need your proxy submitted by 1pm. Let me know either way.",
        },
      ],
      draft:
        "Hi all — I can't make the 3pm session today. Please record my proxy in favor of the Q3 budget as presented, and note that I'd like a follow-up on the facilities line item next meeting.",
      draftAuthor: "emptify",
      versionStack: [],
      handoffSuggested: false,
      handoffReason: "",
      status: "board",
      eaNote: "",
      eaChangeSummary: "",
      draftAtHandoff: "",
    },
    {
      id: "e3",
      account: "kestrel",
      accountLabel: "Kestrel Partners",
      accountEmail: "mara@kestrelpartners.com",
      from: "Dev Malhotra",
      fromEmail: "dev@brightridge.vc",
      subject: "Coffee next week?",
      bucket: "week",
      reason: "No deadline — a scheduling request.",
      voiceMode: "client",
      voiceWhy: "Matched to client voice — direct, ends with a concrete next step.",
      messages: [
        {
          from: "Dev Malhotra",
          at: "Yesterday, 4:05 PM",
          body: "Mara — would love to grab coffee next week if you have 30 minutes. Whatever works on your end.",
        },
      ],
      draft: "Dev — great to hear from you, let's find time next week. I'll have my assistant follow up with a few slots that work.",
      draftAuthor: "emptify",
      versionStack: [],
      handoffSuggested: true,
      handoffReason: "Scheduling request — EA usually handles these.",
      status: "board",
      eaNote: "",
      eaChangeSummary: "",
      draftAtHandoff: "",
    },
    {
      id: "e4",
      account: "northwind",
      accountLabel: "Northwind Health",
      accountEmail: "mara.lindqvist@northwindhealth.org",
      from: "Compliance Office",
      fromEmail: "compliance@northwindhealth.org",
      subject: "Q3 compliance report — review before Friday",
      bucket: "week",
      reason: "Needed before Friday's committee call.",
      voiceMode: "internal",
      voiceWhy: "Matched to internal voice — collegial, slightly longer sentences.",
      messages: [
        {
          from: "Compliance Office",
          at: "Monday, 11:00 AM",
          body: "Attached is the Q3 compliance report for your review ahead of Friday's committee call. Flag anything before Thursday EOD.",
        },
      ],
      draft: "Thanks for sending this over. I've read through it — no concerns on my end. Happy to discuss Friday if others have questions.",
      draftAuthor: "emptify",
      versionStack: [],
      handoffSuggested: false,
      handoffReason: "",
      status: "board",
      eaNote: "",
      eaChangeSummary: "",
      draftAtHandoff: "",
    },
    {
      id: "e5",
      account: "personal",
      accountLabel: "Personal Gmail",
      accountEmail: "mara.lindqvist@gmail.com",
      from: "Alumni Association",
      fromEmail: "no-reply@rivertonalumni.org",
      subject: "Annual dues renewal",
      bucket: "wait",
      reason: "No deadline, informational.",
      voiceMode: "internal",
      voiceWhy: "Matched to internal voice — the closest match for informal, non-client mail.",
      messages: [
        {
          from: "Alumni Association",
          at: "Last week",
          body: "Your annual alumni dues are due for renewal. Renew anytime this year to keep your membership active.",
        },
      ],
      draft: "Thanks for the reminder — I'll take care of this when I get a chance.",
      draftAuthor: "emptify",
      versionStack: [],
      handoffSuggested: false,
      handoffReason: "",
      status: "board",
      eaNote: "",
      eaChangeSummary: "",
      draftAtHandoff: "",
    },
    {
      id: "e6",
      account: "kestrel",
      accountLabel: "Kestrel Partners",
      accountEmail: "mara@kestrelpartners.com",
      from: "Portfolio Updates",
      fromEmail: "updates@kestrelpartners.com",
      subject: "Q2 portfolio roundup",
      bucket: "wait",
      reason: "FYI only, no action needed.",
      voiceMode: "client",
      voiceWhy: "Matched to client voice — short acknowledgement, no action requested.",
      messages: [
        {
          from: "Portfolio Updates",
          at: "Monday, 7:00 AM",
          body: "This quarter's portfolio roundup is ready — three companies raised follow-on rounds, one exited.",
        },
      ],
      draft: "Nice update — thanks for putting this together.",
      draftAuthor: "emptify",
      versionStack: [],
      handoffSuggested: false,
      handoffReason: "",
      status: "board",
      eaNote: "",
      eaChangeSummary: "",
      draftAtHandoff: "",
    },
    {
      id: "e7",
      account: "northwind",
      accountLabel: "Northwind Health",
      accountEmail: "mara.lindqvist@northwindhealth.org",
      from: "Board Secretary",
      fromEmail: "secretary@northwindhealth.org",
      subject: "Reschedule board dinner",
      bucket: "week",
      reason: "Needs a new date — a few members can't make the 14th.",
      voiceMode: "internal",
      voiceWhy: "Matched to internal voice — collegial, coordinating tone.",
      messages: [
        {
          from: "Board Secretary",
          at: "2 days ago",
          body: "A few board members can't make the dinner on the 14th — could we look at alternate dates?",
        },
      ],
      draft: "Happy to look at alternates — could you share which dates work best for the group and I'll coordinate from there?",
      draftAuthor: "emptify",
      versionStack: [],
      handoffSuggested: true,
      handoffReason: "Scheduling request — EA usually handles these.",
      status: "withEA",
      eaNote: "Just find a date that works for most people, keep it simple.",
      eaChangeSummary: "",
      draftAtHandoff: "Happy to look at alternates — could you share which dates work best for the group and I'll coordinate from there?",
    },
    {
      id: "e8",
      account: "kestrel",
      accountLabel: "Kestrel Partners",
      accountEmail: "mara@kestrelpartners.com",
      from: "Sana Whitfield",
      fromEmail: "sana@fernbridge.co",
      subject: "Follow-up call — confirming Thursday",
      bucket: "today",
      reason: "Awaiting confirmation for a call this week.",
      voiceMode: "client",
      voiceWhy: "Matched to client voice — direct, ends with a next step.",
      messages: [
        {
          from: "Sana Whitfield",
          at: "Yesterday, 2:30 PM",
          body: "Following up on our conversation — does Thursday still work for the follow-up call?",
        },
      ],
      draft:
        "Sana — Thursday works. Let's do 2pm ET, I'll send a calendar invite with dial-in details shortly. Looking forward to it. — Mara",
      draftAuthor: "ea",
      versionStack: [],
      handoffSuggested: false,
      handoffReason: "",
      status: "readyToSend",
      eaNote: "Confirm Thursday and lock a time.",
      eaChangeSummary: "Tightened the close and added the specific dial-in time.",
      draftAtHandoff: "Sana — following up, does Thursday still work? — Mara",
    },
  ];
}

export function initialVoice(): VoiceState {
  return {
    client: {
      sampleSize: "58 of 214 sent emails (last 90 days)",
      rebuilding: false,
      notes: "Keep replies to clients short. Always end with a next step.",
      traits: [
        { label: "Sentence length", value: "Short — averages 14 words per sentence" },
        { label: "Greeting", value: "First name only, no salutation line ('Priya —')" },
        { label: "Sign-off", value: "First name, no closing line ('— Mara')" },
        { label: "Formality", value: "Direct and businesslike, minimal small talk" },
        { label: "Hedging", value: "Rare — states positions plainly" },
        { label: "Characteristic phrases", value: "'happy to', 'let's find a time', 'stay on track'" },
      ],
    },
    internal: {
      sampleSize: "36 of 214 sent emails (last 90 days)",
      rebuilding: false,
      notes: "Fine to be a little less terse with the board and staff than with clients.",
      traits: [
        { label: "Sentence length", value: "Slightly longer — averages 19 words per sentence" },
        { label: "Greeting", value: "Opens with 'Hi all' or 'Hi [name]' for groups" },
        { label: "Sign-off", value: "First name only, occasionally none at all" },
        { label: "Formality", value: "Collegial, slightly more procedural language" },
        { label: "Hedging", value: "Occasional — 'happy to', 'let me know either way'" },
        { label: "Characteristic phrases", value: "'happy to discuss', 'let me know either way', 'no concerns on my end'" },
      ],
    },
  };
}

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
