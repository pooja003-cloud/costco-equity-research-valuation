# External review packets

Each packet here is the input for one ClaudeFinanceLab skill (claudefinancelab.com/skills). The skills are
instructions pasted into Claude; nothing is installed.

| Packet | ClaudeFinanceLab skill |
|---|---|
| [03_forecast_review_packet.md](03_forecast_review_packet.md) | Three-Statement Model Checker |
| [04_dcf_review_packet.md](04_dcf_review_packet.md) | DCF Model Builder |
| [05_comps_review_packet.md](05_comps_review_packet.md) | Comparable Company Analysis |
| [08_memo_review_packet.md](08_memo_review_packet.md) | Investment Committee Memo Writer |

How to run a review:

1. Open the skill on claudefinancelab.com and copy its SKILL.md text.
2. In Claude, create a new Project and paste that text into the Project Instructions.
3. Start a chat in the Project and paste the packet's **Prompt** and **What to paste** sections
   (attach `outputs/COST_Investment_Memo.pdf` for the memo review).
4. Record every point raised, the response and whether the model changed in [`../model_review_log.md`](../model_review_log.md).

A separate Project keeps the reviewer independent: it has no context from the build.
