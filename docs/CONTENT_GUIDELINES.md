# CONTENT_GUIDELINES.md — Fyndo User-Facing Content & Voice Specification

> **Rule of Thumb**: **If a regular shopkeeper in Nagpur or Dadar wouldn't say it aloud, it doesn't belong in the UI.**

---

## 1. The Terminology Blacklist

Never expose internal development, security, or architecture terms in customer-facing screens.

| Internal Concept / Tech Term | Forbidden in Customer UI | Approved User-Facing Replacement |
|---|---|---|
| **TOTP / HMAC / Rotating Key** | `Dynamic TOTP QR`, `HMAC-SHA1` | `Security code`, `Rotating code`, `Refreshes every minute` |
| **Geofencing / Haversine** | `Geofence armed`, `GPS mismatch` | `Store location`, `Only valid in-store` |
| **RBAC / Permissions** | `RBAC error`, `Unauthorized` | `Only store owners can do this` |
| **API / Endpoint** | `API error`, `API call failed` | `Couldn't connect. Please check your internet.` |
| **Database / Migration** | `Database exception`, `DB write failure` | `We couldn't save your changes. Please try again.` |
| **Backend / Frontend / Server** | `Server error 500`, `Frontend state` | `Something went wrong on our end. Please try again.` |
| **HTTP 401 / 403** | `401 Unauthorized`, `403 Forbidden` | `Please log in to continue`, `You don't have access to this` |
| **HTTP 404** | `Resource 404 not found` | `We couldn't find what you're looking for` |
| **Entity / Record / Row** | `Merchant entity`, `Coupon record` | `Store`, `Shop`, `Coupon`, `Offer` |
| **Workflow State** | `PENDING_REVIEW`, `DRAFT` | `In Review (takes ~2 hrs)`, `Saved as Draft` |
| **JSON / Payload / Token** | `Invalid payload`, `Malformed JSON` | `Please check the details and try again` |
| **PWA / Client-side** | `PWA simulator`, `Native APK` | `Mobile App`, `Open on Phone` |
| **AI / LLM / Model** | `AI-generated`, `LLM prompt failed` | *(Only use if meaningful)* `Smart suggestion` or omit |
| **Validation Failed** | `Regex validation failed` | `Please enter a valid 10-digit phone number` |
| **Null / Undefined** | `null`, `undefined`, `NaN` | `Not provided`, `—`, `0` |

---

## 2. Tone & Voice Guidelines

### A. Cut the Corporate Fluff
Avoid generic AI and SaaS marketing jargon. Speak directly and respect the user's time.

| Avoid (AI / SaaS Slop) | Prefer (Fyndo Voice) |
|---|---|
| *"Welcome to your seamless hyper-local discovery experience."* | *"Welcome back, Ramesh!"* |
| *"Leverage real-time footfall optimization to boost revenue."* | *"Attract nearby customers into your store today."* |
| *"Your transaction submission has been successfully processed."* | *"Coupon redeemed! ₹150 discount applied."* |
| *"Are you sure you want to proceed with this critical deletion action?"* | *"Delete this offer? This cannot be undone."* |
| *"No data entities currently found in this container view."* | *"No offers created yet."* |
| *"Please enter a valid string corresponding to the field definition."* | *"Enter your store name."* |

### B. Action-Oriented Buttons
Button labels must complete the sentence: *"I want to..."*
* Prefer: `Save Offer`, `Publish Video`, `Verify Code`, `Get Directions`.
* Avoid: `Submit`, `Execute`, `Process`, `Send Request`, `Click Here`.

### C. Respectful, Helpful Error Messages
Every error message must answer three questions:
1. What happened?
2. Why did it happen?
3. How can I fix it?

```text
Bad:  "Error: Validation constraint violated on input field 'phone'."
Good: "Enter a valid 10-digit mobile number so we can send your login OTP."

Bad:  "Redemption rejected: expired_token."
Good: "This coupon expired yesterday. Ask the customer for an active offer."
```

---

## 3. Multilingual Parity (English, Hindi, Marathi)

Fyndo operates in Maharashtra (Nagpur & Mumbai). UI copy across Hindi and Marathi must match daily spoken language, not stiff formal translation.

| Concept | English | Natural Hindi (हिंदी) | Natural Marathi (मराठी) |
|---|---|---|---|
| **Merchant Studio** | Store Manager | स्टोर मैनेजर | स्टोअर मॅनेजर |
| **Countertop Scanner** | Counter Scanner | काउंटर स्कैनर | काउंटर स्कॅनर |
| **Claim Offer** | Claim Coupon | कूपन पाएं | कूपन मिळवा |
| **Redeem at Store** | Show at Checkout | बिलिंग काउंटरवर दाखवा | बिलिंग काउंटरवर दाखवा |
| **In-Store Only** | In-Store Deal | सिर्फ दुकान में मान्य | फक्त दुकानात उपलब्ध |
| **Discount Given** | Savings Given | कुल बचत दी गई | एकूण बचत दिली |
| **Verified Walk-in** | In-Store Visit | स्टोर विज़िट | स्टोअर भेट |
